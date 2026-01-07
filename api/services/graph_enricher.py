"""
MCP v4.1 - Graph Enricher
Motor de enriquecimiento automático del grafo de ataque.
Crea nodos y aristas basados en outputs de herramientas, IOCs y eventos.
"""

import hashlib
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
import logging

from api.database import get_db_context
from api.models.tools import (
    GraphNode, GraphEdge, NodeType, EdgeType, NodeStatus
)

logger = logging.getLogger(__name__)


# =============================================================================
# NODE TYPE INFERENCE
# =============================================================================

NODE_TYPE_PATTERNS = {
    NodeType.IP_ADDRESS: [
        r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
    ],
    NodeType.DOMAIN: [
        r'\b[a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,}\b'
    ],
    NodeType.URL: [
        r'https?://[^\s<>"{}|\\^`\[\]]+'
    ],
    NodeType.EMAIL: [
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    ],
    NodeType.HASH_MD5: [
        r'\b[a-fA-F0-9]{32}\b'
    ],
    NodeType.HASH_SHA1: [
        r'\b[a-fA-F0-9]{40}\b'
    ],
    NodeType.HASH_SHA256: [
        r'\b[a-fA-F0-9]{64}\b'
    ],
    NodeType.FILE_PATH: [
        r'(?:/[a-zA-Z0-9._-]+)+/?',
        r'[A-Za-z]:\\[^\s:*?"<>|]+'
    ],
    NodeType.PROCESS: [
        r'\b[a-zA-Z0-9_-]+\.(exe|dll|sys|ps1|bat|cmd|sh)\b'
    ],
    NodeType.CVE: [
        r'CVE-\d{4}-\d{4,}'
    ],
    NodeType.REGISTRY_KEY: [
        r'HKEY_[A-Z_]+\\[^\s]+'
    ]
}

# Relaciones entre tipos de nodos
EDGE_INFERENCE_RULES = [
    # (source_type, target_type, edge_type, conditions)
    (NodeType.IP_ADDRESS, NodeType.DOMAIN, EdgeType.RESOLVES_TO, {}),
    (NodeType.DOMAIN, NodeType.IP_ADDRESS, EdgeType.RESOLVED_FROM, {}),
    (NodeType.IP_ADDRESS, NodeType.IP_ADDRESS, EdgeType.CONNECTS_TO, {}),
    (NodeType.PROCESS, NodeType.FILE_PATH, EdgeType.CREATES, {"verb": "creates"}),
    (NodeType.PROCESS, NodeType.FILE_PATH, EdgeType.MODIFIES, {"verb": "modifies"}),
    (NodeType.PROCESS, NodeType.FILE_PATH, EdgeType.DELETES, {"verb": "deletes"}),
    (NodeType.PROCESS, NodeType.PROCESS, EdgeType.SPAWNS, {}),
    (NodeType.PROCESS, NodeType.IP_ADDRESS, EdgeType.CONNECTS_TO, {}),
    (NodeType.PROCESS, NodeType.DOMAIN, EdgeType.CONNECTS_TO, {}),
    (NodeType.FILE_PATH, NodeType.HASH_SHA256, EdgeType.HAS_HASH, {}),
    (NodeType.URL, NodeType.DOMAIN, EdgeType.CONTAINS, {}),
    (NodeType.EMAIL, NodeType.DOMAIN, EdgeType.BELONGS_TO, {}),
    (NodeType.USER, NodeType.IP_ADDRESS, EdgeType.LOGGED_IN_FROM, {}),
    (NodeType.USER, NodeType.PROCESS, EdgeType.EXECUTES, {}),
    (NodeType.HOST, NodeType.IP_ADDRESS, EdgeType.HAS_IP, {}),
    (NodeType.MALWARE, NodeType.FILE_PATH, EdgeType.DROPPED, {}),
    (NodeType.MALWARE, NodeType.CVE, EdgeType.EXPLOITS, {}),
    (NodeType.THREAT_ACTOR, NodeType.MALWARE, EdgeType.USES, {}),
    (NodeType.CAMPAIGN, NodeType.THREAT_ACTOR, EdgeType.ATTRIBUTED_TO, {}),
]


# =============================================================================
# GRAPH ENRICHER
# =============================================================================

class GraphEnricher:
    """
    Enriquecedor automático del grafo de ataque.
    Extrae entidades de outputs y crea nodos/aristas.
    """
    
    def __init__(self):
        self.node_cache: Dict[str, str] = {}  # value -> node_id
        self.pending_edges: List[Tuple[str, str, str]] = []
    
    # -------------------------------------------------------------------------
    # NODE CREATION
    # -------------------------------------------------------------------------
    
    async def create_node(
        self,
        value: str,
        node_type: NodeType,
        label: Optional[str] = None,
        properties: Optional[Dict] = None,
        case_id: Optional[str] = None,
        source: str = "auto",
        status: NodeStatus = NodeStatus.ACTIVE
    ) -> str:
        """
        Crea un nodo en el grafo.
        
        Args:
            value: Valor del nodo (IP, hash, dominio, etc.)
            node_type: Tipo de nodo
            label: Etiqueta opcional
            properties: Propiedades adicionales
            case_id: ID del caso
            source: Fuente del nodo
            status: Estado del nodo
        
        Returns:
            ID del nodo creado o existente
        """
        # Generar ID único basado en tipo y valor
        node_id = self._generate_node_id(node_type, value)
        
        # Verificar cache
        cache_key = f"{node_type.value}:{value}"
        if cache_key in self.node_cache:
            return self.node_cache[cache_key]
        
        with get_db_context() as db:
            # Verificar si existe
            existing = db.query(GraphNode).filter(
                GraphNode.id == node_id
            ).first()
            
            if existing:
                # Actualizar si es necesario
                if case_id and case_id not in (existing.case_ids or []):
                    existing.case_ids = (existing.case_ids or []) + [case_id]
                    existing.updated_at = datetime.utcnow()
                    db.commit()
                
                self.node_cache[cache_key] = node_id
                return node_id
            
            # Crear nuevo nodo
            node = GraphNode(
                id=node_id,
                node_type=node_type.value,
                value=value,
                label=label or value[:50],
                properties=properties or {},
                source=source,
                status=status.value,
                case_ids=[case_id] if case_id else [],
                first_seen=datetime.utcnow(),
                last_seen=datetime.utcnow()
            )
            db.add(node)
            db.commit()
            
            logger.info(f"📍 Created node: {node_type.value} - {value[:30]}...")
            
            self.node_cache[cache_key] = node_id
            return node_id
    
    def _generate_node_id(self, node_type: NodeType, value: str) -> str:
        """Genera ID único para nodo basado en tipo y valor"""
        hash_input = f"{node_type.value}:{value}".lower()
        return f"N-{hashlib.md5(hash_input.encode()).hexdigest()[:12].upper()}"
    
    # -------------------------------------------------------------------------
    # EDGE CREATION
    # -------------------------------------------------------------------------
    
    async def create_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: EdgeType,
        label: Optional[str] = None,
        properties: Optional[Dict] = None,
        weight: float = 1.0,
        case_id: Optional[str] = None
    ) -> str:
        """
        Crea una arista entre dos nodos.
        
        Args:
            source_id: ID del nodo origen
            target_id: ID del nodo destino
            edge_type: Tipo de relación
            label: Etiqueta opcional
            properties: Propiedades adicionales
            weight: Peso de la relación
            case_id: ID del caso
        
        Returns:
            ID de la arista
        """
        edge_id = f"E-{uuid.uuid4().hex[:12].upper()}"
        
        with get_db_context() as db:
            # Verificar si existe arista similar
            existing = db.query(GraphEdge).filter(
                GraphEdge.source_id == source_id,
                GraphEdge.target_id == target_id,
                GraphEdge.edge_type == edge_type.value
            ).first()
            
            if existing:
                # Incrementar peso
                existing.weight += 0.1
                existing.last_seen = datetime.utcnow()
                if case_id and case_id not in (existing.case_ids or []):
                    existing.case_ids = (existing.case_ids or []) + [case_id]
                db.commit()
                return existing.id
            
            # Crear nueva arista
            edge = GraphEdge(
                id=edge_id,
                source_id=source_id,
                target_id=target_id,
                edge_type=edge_type.value,
                label=label or edge_type.value.replace("_", " ").title(),
                properties=properties or {},
                weight=weight,
                case_ids=[case_id] if case_id else [],
                first_seen=datetime.utcnow(),
                last_seen=datetime.utcnow()
            )
            db.add(edge)
            db.commit()
            
            logger.info(f"🔗 Created edge: {source_id} --[{edge_type.value}]--> {target_id}")
            
            return edge_id
    
    # -------------------------------------------------------------------------
    # AUTOMATIC ENRICHMENT
    # -------------------------------------------------------------------------
    
    async def enrich_from_tool_output(
        self,
        output: str,
        tool_id: str,
        execution_id: str,
        case_id: Optional[str] = None
    ) -> int:
        """
        Enriquece grafo automáticamente desde output de herramienta.
        
        Args:
            output: Output de la herramienta
            tool_id: ID de la herramienta
            execution_id: ID de ejecución
            case_id: ID del caso
        
        Returns:
            Número de nodos creados
        """
        nodes_created = 0
        extracted_nodes: List[Tuple[str, NodeType]] = []
        
        # 1. Extraer entidades por patrones
        for node_type, patterns in NODE_TYPE_PATTERNS.items():
            for pattern in patterns:
                matches = re.findall(pattern, output, re.IGNORECASE)
                for match in matches:
                    # Limpiar valor
                    value = match.strip()
                    if self._is_valid_value(value, node_type):
                        extracted_nodes.append((value, node_type))
        
        # 2. Extraer entidades específicas por herramienta
        tool_nodes = self._extract_tool_specific(output, tool_id)
        extracted_nodes.extend(tool_nodes)
        
        # 3. Deduplicar
        seen = set()
        unique_nodes = []
        for value, node_type in extracted_nodes:
            key = f"{node_type.value}:{value.lower()}"
            if key not in seen:
                seen.add(key)
                unique_nodes.append((value, node_type))
        
        # 4. Crear nodos
        created_node_ids: List[Tuple[str, NodeType, str]] = []  # (id, type, value)
        
        for value, node_type in unique_nodes[:100]:  # Limitar
            try:
                node_id = await self.create_node(
                    value=value,
                    node_type=node_type,
                    properties={
                        "source_tool": tool_id,
                        "execution_id": execution_id
                    },
                    case_id=case_id,
                    source=f"tool:{tool_id}"
                )
                created_node_ids.append((node_id, node_type, value))
                nodes_created += 1
            except Exception as e:
                logger.warning(f"Failed to create node {value}: {e}")
        
        # 5. Crear aristas entre nodos relacionados
        await self._create_inferred_edges(created_node_ids, case_id)
        
        # 6. Crear nodo de ejecución y conectar
        if created_node_ids:
            exec_node_id = await self.create_node(
                value=execution_id,
                node_type=NodeType.TOOL_EXECUTION,
                label=f"Execution: {tool_id}",
                properties={
                    "tool_id": tool_id,
                    "nodes_created": len(created_node_ids)
                },
                case_id=case_id,
                source="system"
            )
            
            # Conectar ejecución con nodos descubiertos
            for node_id, node_type, _ in created_node_ids[:20]:  # Limitar conexiones
                await self.create_edge(
                    source_id=exec_node_id,
                    target_id=node_id,
                    edge_type=EdgeType.DISCOVERED,
                    case_id=case_id
                )
        
        logger.info(f"📊 Graph enriched: {nodes_created} nodes from {tool_id}")
        
        return nodes_created
    
    def _is_valid_value(self, value: str, node_type: NodeType) -> bool:
        """Valida si un valor es válido para el tipo de nodo"""
        if not value or len(value) < 3:
            return False
        
        # Filtrar IPs privadas/localhost
        if node_type == NodeType.IP_ADDRESS:
            if value.startswith(('10.', '172.16.', '172.17.', '172.18.', '172.19.',
                                 '172.20.', '172.21.', '172.22.', '172.23.', '172.24.',
                                 '172.25.', '172.26.', '172.27.', '172.28.', '172.29.',
                                 '172.30.', '172.31.', '192.168.', '127.', '0.', '255.')):
                return False
        
        # Filtrar dominios comunes/genéricos
        if node_type == NodeType.DOMAIN:
            common_domains = {'localhost', 'example.com', 'test.com', 'domain.com'}
            if value.lower() in common_domains:
                return False
        
        # Filtrar rutas del sistema
        if node_type == NodeType.FILE_PATH:
            system_paths = ['/usr', '/bin', '/lib', '/etc', 'C:\\Windows\\System32']
            if any(value.lower().startswith(p.lower()) for p in system_paths):
                return False
        
        return True
    
    def _extract_tool_specific(
        self,
        output: str,
        tool_id: str
    ) -> List[Tuple[str, NodeType]]:
        """Extrae entidades específicas según la herramienta"""
        nodes = []
        
        if tool_id == "nmap":
            # Extraer hosts y servicios
            for line in output.split("\n"):
                if "Nmap scan report for" in line:
                    parts = line.split(" ")
                    hostname = parts[-1].strip("()")
                    nodes.append((hostname, NodeType.HOST))
                elif "open" in line and ("/tcp" in line or "/udp" in line):
                    parts = line.split()
                    if len(parts) >= 3:
                        service = parts[2]
                        nodes.append((service, NodeType.SERVICE))
        
        elif tool_id == "loki":
            # Extraer malware detectado
            for line in output.split("\n"):
                if "[ALERT]" in line:
                    # Extraer nombre de regla/malware
                    match = re.search(r'REASON: ([^\n]+)', line)
                    if match:
                        nodes.append((match.group(1), NodeType.MALWARE))
        
        elif tool_id == "yara":
            # Extraer reglas que matchearon
            for line in output.split("\n"):
                if line.strip() and not line.startswith("0x"):
                    parts = line.split(" ", 1)
                    if parts:
                        nodes.append((parts[0], NodeType.YARA_RULE))
        
        elif tool_id in ["sparrow", "hawk"]:
            # Extraer usuarios y IPs
            user_pattern = r'User:\s*([^\s,]+)'
            ip_pattern = r'IP:\s*([^\s,]+)'
            
            for match in re.finditer(user_pattern, output):
                nodes.append((match.group(1), NodeType.USER))
            
            for match in re.finditer(ip_pattern, output):
                nodes.append((match.group(1), NodeType.IP_ADDRESS))
        
        elif tool_id == "osqueryi":
            # Extraer procesos
            if "processes" in output.lower():
                process_pattern = r'"name":\s*"([^"]+)"'
                for match in re.finditer(process_pattern, output):
                    nodes.append((match.group(1), NodeType.PROCESS))
        
        elif tool_id == "volatility":
            # Extraer procesos de memoria
            lines = output.split("\n")
            for line in lines[1:]:  # Skip header
                parts = line.split()
                if len(parts) >= 2 and parts[0].isdigit():
                    # PID y nombre de proceso
                    nodes.append((parts[1], NodeType.PROCESS))
        
        return nodes
    
    async def _create_inferred_edges(
        self,
        nodes: List[Tuple[str, NodeType, str]],
        case_id: Optional[str]
    ):
        """Crea aristas inferidas entre nodos basado en reglas"""
        # Agrupar por tipo
        nodes_by_type: Dict[NodeType, List[Tuple[str, str]]] = {}
        for node_id, node_type, value in nodes:
            if node_type not in nodes_by_type:
                nodes_by_type[node_type] = []
            nodes_by_type[node_type].append((node_id, value))
        
        # Aplicar reglas de inferencia
        for source_type, target_type, edge_type, conditions in EDGE_INFERENCE_RULES:
            if source_type in nodes_by_type and target_type in nodes_by_type:
                source_nodes = nodes_by_type[source_type]
                target_nodes = nodes_by_type[target_type]
                
                # Crear aristas basadas en proximidad/contexto
                for source_id, source_val in source_nodes[:10]:
                    for target_id, target_val in target_nodes[:10]:
                        if source_id != target_id:
                            # Verificar si tiene sentido la relación
                            if self._should_create_edge(
                                source_type, target_type, source_val, target_val
                            ):
                                await self.create_edge(
                                    source_id=source_id,
                                    target_id=target_id,
                                    edge_type=edge_type,
                                    weight=0.5,
                                    case_id=case_id
                                )
    
    def _should_create_edge(
        self,
        source_type: NodeType,
        target_type: NodeType,
        source_val: str,
        target_val: str
    ) -> bool:
        """Determina si tiene sentido crear una arista entre dos nodos"""
        # URL contiene dominio
        if source_type == NodeType.URL and target_type == NodeType.DOMAIN:
            return target_val.lower() in source_val.lower()
        
        # Email pertenece a dominio
        if source_type == NodeType.EMAIL and target_type == NodeType.DOMAIN:
            return source_val.lower().endswith(f"@{target_val.lower()}")
        
        # Por defecto, crear si están en el mismo contexto
        return True
    
    # -------------------------------------------------------------------------
    # IOC NODE CREATION
    # -------------------------------------------------------------------------
    
    async def create_ioc_node(
        self,
        ioc_id: str,
        case_id: Optional[str] = None
    ) -> str:
        """Crea nodo para un IOC existente"""
        from api.models import IocItem
        
        with get_db_context() as db:
            ioc = db.query(IocItem).filter(IocItem.id == ioc_id).first()
            if not ioc:
                raise ValueError(f"IOC {ioc_id} not found")
            
            # Mapear tipo de IOC a tipo de nodo
            type_mapping = {
                "ip": NodeType.IP_ADDRESS,
                "domain": NodeType.DOMAIN,
                "url": NodeType.URL,
                "email": NodeType.EMAIL,
                "hash_md5": NodeType.HASH_MD5,
                "hash_sha1": NodeType.HASH_SHA1,
                "hash_sha256": NodeType.HASH_SHA256,
                "file_path": NodeType.FILE_PATH
            }
            
            node_type = type_mapping.get(ioc.ioc_type, NodeType.INDICATOR)
        
        node_id = await self.create_node(
            value=ioc.value,
            node_type=node_type,
            label=ioc.value[:50],
            properties={
                "ioc_id": ioc_id,
                "severity": ioc.severity,
                "confidence": ioc.confidence,
                "source": ioc.source
            },
            case_id=case_id,
            source="ioc_store",
            status=NodeStatus.ACTIVE if ioc.is_active else NodeStatus.INACTIVE
        )
        
        return node_id
    
    # -------------------------------------------------------------------------
    # GRAPH QUERIES
    # -------------------------------------------------------------------------
    
    def get_graph_data(
        self,
        case_id: Optional[str] = None,
        node_types: Optional[List[str]] = None,
        limit_nodes: int = 200,
        limit_edges: int = 500
    ) -> Dict[str, Any]:
        """
        Obtiene datos del grafo para visualización.
        
        Returns:
            Dict con nodos y aristas en formato para D3.js/Cytoscape
        """
        with get_db_context() as db:
            # Query nodos
            nodes_query = db.query(GraphNode)
            
            if case_id:
                nodes_query = nodes_query.filter(
                    GraphNode.case_ids.contains([case_id])
                )
            
            if node_types:
                nodes_query = nodes_query.filter(
                    GraphNode.node_type.in_(node_types)
                )
            
            nodes = nodes_query.limit(limit_nodes).all()
            node_ids = [n.id for n in nodes]
            
            # Query aristas
            edges = db.query(GraphEdge).filter(
                GraphEdge.source_id.in_(node_ids),
                GraphEdge.target_id.in_(node_ids)
            ).limit(limit_edges).all()
        
        return {
            "nodes": [
                {
                    "id": n.id,
                    "label": n.label,
                    "type": n.node_type,
                    "value": n.value,
                    "status": n.status,
                    "properties": n.properties,
                    "first_seen": n.first_seen.isoformat() if n.first_seen else None,
                    "last_seen": n.last_seen.isoformat() if n.last_seen else None
                }
                for n in nodes
            ],
            "edges": [
                {
                    "id": e.id,
                    "source": e.source_id,
                    "target": e.target_id,
                    "type": e.edge_type,
                    "label": e.label,
                    "weight": e.weight
                }
                for e in edges
            ],
            "stats": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "node_types": list(set(n.node_type for n in nodes))
            }
        }
    
    def get_node_neighborhood(
        self,
        node_id: str,
        depth: int = 2,
        max_nodes: int = 50
    ) -> Dict[str, Any]:
        """
        Obtiene vecindario de un nodo hasta cierta profundidad.
        
        Args:
            node_id: ID del nodo central
            depth: Profundidad de búsqueda
            max_nodes: Máximo de nodos a retornar
        """
        visited_nodes: Set[str] = {node_id}
        nodes_to_return = []
        edges_to_return = []
        
        with get_db_context() as db:
            # BFS para encontrar vecinos
            current_level = [node_id]
            
            for _ in range(depth):
                next_level = []
                
                for current_id in current_level:
                    # Aristas salientes
                    outgoing = db.query(GraphEdge).filter(
                        GraphEdge.source_id == current_id
                    ).all()
                    
                    for edge in outgoing:
                        edges_to_return.append(edge)
                        if edge.target_id not in visited_nodes:
                            visited_nodes.add(edge.target_id)
                            next_level.append(edge.target_id)
                    
                    # Aristas entrantes
                    incoming = db.query(GraphEdge).filter(
                        GraphEdge.target_id == current_id
                    ).all()
                    
                    for edge in incoming:
                        edges_to_return.append(edge)
                        if edge.source_id not in visited_nodes:
                            visited_nodes.add(edge.source_id)
                            next_level.append(edge.source_id)
                
                current_level = next_level[:max_nodes - len(visited_nodes)]
                
                if len(visited_nodes) >= max_nodes:
                    break
            
            # Obtener datos de nodos
            nodes = db.query(GraphNode).filter(
                GraphNode.id.in_(list(visited_nodes))
            ).all()
        
        return {
            "center_node": node_id,
            "nodes": [
                {
                    "id": n.id,
                    "label": n.label,
                    "type": n.node_type,
                    "value": n.value,
                    "is_center": n.id == node_id
                }
                for n in nodes
            ],
            "edges": [
                {
                    "id": e.id,
                    "source": e.source_id,
                    "target": e.target_id,
                    "type": e.edge_type,
                    "weight": e.weight
                }
                for e in edges_to_return
            ]
        }
    
    def search_nodes(
        self,
        query: str,
        node_type: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict]:
        """Busca nodos por valor o label"""
        with get_db_context() as db:
            q = db.query(GraphNode).filter(
                (GraphNode.value.ilike(f"%{query}%")) |
                (GraphNode.label.ilike(f"%{query}%"))
            )
            
            if node_type:
                q = q.filter(GraphNode.node_type == node_type)
            
            nodes = q.limit(limit).all()
        
        return [
            {
                "id": n.id,
                "label": n.label,
                "type": n.node_type,
                "value": n.value,
                "status": n.status
            }
            for n in nodes
        ]
    
    # -------------------------------------------------------------------------
    # GRAPH ANALYSIS
    # -------------------------------------------------------------------------
    
    def get_graph_stats(self, case_id: Optional[str] = None) -> Dict[str, Any]:
        """Obtiene estadísticas del grafo"""
        with get_db_context() as db:
            nodes_query = db.query(GraphNode)
            edges_query = db.query(GraphEdge)
            
            if case_id:
                nodes_query = nodes_query.filter(
                    GraphNode.case_ids.contains([case_id])
                )
            
            total_nodes = nodes_query.count()
            total_edges = edges_query.count()
            
            # Contar por tipo
            node_types = {}
            for node in nodes_query.all():
                t = node.node_type
                node_types[t] = node_types.get(t, 0) + 1
            
            edge_types = {}
            for edge in edges_query.all():
                t = edge.edge_type
                edge_types[t] = edge_types.get(t, 0) + 1
        
        return {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "node_types": node_types,
            "edge_types": edge_types,
            "density": total_edges / max(total_nodes * (total_nodes - 1), 1)
        }
    
    async def find_attack_paths(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 5
    ) -> List[List[Dict]]:
        """
        Encuentra caminos de ataque entre dos nodos.
        Usa BFS para encontrar todos los caminos.
        """
        paths = []
        visited = set()
        queue = [([source_id], [])]  # (node_path, edge_path)
        
        with get_db_context() as db:
            while queue and len(paths) < 10:  # Limitar a 10 caminos
                current_path, edge_path = queue.pop(0)
                current_node = current_path[-1]
                
                if len(current_path) > max_depth:
                    continue
                
                if current_node == target_id:
                    paths.append({
                        "nodes": current_path,
                        "edges": edge_path,
                        "length": len(current_path) - 1
                    })
                    continue
                
                if current_node in visited:
                    continue
                visited.add(current_node)
                
                # Obtener vecinos
                edges = db.query(GraphEdge).filter(
                    GraphEdge.source_id == current_node
                ).all()
                
                for edge in edges:
                    if edge.target_id not in current_path:
                        queue.append((
                            current_path + [edge.target_id],
                            edge_path + [edge.id]
                        ))
        
        return paths


# =============================================================================
# SINGLETON
# =============================================================================

graph_enricher = GraphEnricher()
