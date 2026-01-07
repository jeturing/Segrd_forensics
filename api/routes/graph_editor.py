"""
Router para editar y agregar nodos personalizados al grafo
Permite que los investigadores agreguen evidencia manual y creen conexiones
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime
import logging
import json
from api.config import settings

router = APIRouter(prefix="/forensics/graph", tags=["Graph Editor"])
logger = logging.getLogger(__name__)

EVIDENCE_DIR = settings.EVIDENCE_DIR


class CustomNode(BaseModel):
    """Nodo personalizado para el grafo"""
    id: str = Field(..., description="ID único del nodo")
    type: Literal[
        "user", "ip", "device", "ioc", "mailbox_rule", "oauth_app",
        "process", "file", "risk_event", "custom_indicator", "memo"
    ] = Field(..., description="Tipo de nodo")
    label: str = Field(..., description="Etiqueta/nombre del nodo")
    severity: Literal["critical", "high", "medium", "low", "none"] = Field(
        default="medium", description="Nivel de severidad"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Metadatos adicionales"
    )
    source: str = Field(default="manual", description="Fuente del nodo (manual, sparrow, hawk, etc.)")
    linked_users: Optional[List[str]] = Field(
        default=None, description="Usuarios M365 vinculados a este nodo"
    )
    linked_devices: Optional[List[str]] = Field(
        default=None, description="Dispositivos vinculados a este nodo"
    )
    notes: Optional[str] = Field(default=None, description="Notas del investigador")


class CustomEdge(BaseModel):
    """Arista personalizada para el grafo"""
    source: str = Field(..., description="ID del nodo origen")
    target: str = Field(..., description="ID del nodo destino")
    relation: str = Field(..., description="Tipo de relación")
    strength: Literal["strong", "medium", "weak"] = Field(
        default="medium", description="Fuerza de la relación"
    )
    evidence: Optional[str] = Field(default=None, description="Evidencia que respalda la relación")
    source_field: str = Field(default="manual", description="Fuente de la relación")


@router.post("/nodes/add")
async def add_custom_node(case_id: str, node: CustomNode):
    """
    Agrega un nodo personalizado al grafo de un caso
    
    Ejemplos de nodos personalizados:
    - Custom Indicator: Indicador de compromiso agregado manualmente
    - Memo: Nota del investigador vinculada a entidades
    - IP listada manualmente como de un APT conocido
    - Usuario identificado como potencial insider threat
    """
    try:
        logger.info(f"➕ Agregando nodo personalizado {node.id} al caso {case_id}")
        
        # Crear directorio de caso si no existe
        case_evidence_path = EVIDENCE_DIR / case_id
        case_evidence_path.mkdir(parents=True, exist_ok=True)
        
        # Ruta del archivo de nodos personalizados
        custom_nodes_file = case_evidence_path / "custom_nodes.json"
        
        # Cargar nodos existentes
        custom_nodes = {}
        if custom_nodes_file.exists():
            with open(custom_nodes_file, 'r') as f:
                custom_nodes = json.load(f)
        
        # Agregar nuevo nodo
        custom_nodes[node.id] = {
            **node.dict(),
            "added_at": datetime.utcnow().isoformat()
        }
        
        # Guardar nodos actualizados
        with open(custom_nodes_file, 'w') as f:
            json.dump(custom_nodes, f, indent=2)
        
        logger.info(f"✅ Nodo {node.id} agregado exitosamente")
        
        return {
            "status": "success",
            "message": f"Nodo {node.id} agregado",
            "node_id": node.id,
            "total_custom_nodes": len(custom_nodes)
        }
        
    except Exception as e:
        logger.error(f"❌ Error al agregar nodo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/edges/add")
async def add_custom_edge(case_id: str, edge: CustomEdge):
    """
    Agrega una relación personalizada entre nodos
    
    Ejemplos:
    - Conectar una IP a un usuario (LOGON_FROM)
    - Vincular un IOC a un proceso (DETECTED_IN)
    - Conectar un usuario a una aplicación OAuth (CONSENTED)
    """
    try:
        logger.info(f"🔗 Agregando arista personalizada {edge.source}->{edge.target}")
        
        # Crear directorio de caso
        case_evidence_path = EVIDENCE_DIR / case_id
        case_evidence_path.mkdir(parents=True, exist_ok=True)
        
        # Ruta del archivo de aristas personalizadas
        custom_edges_file = case_evidence_path / "custom_edges.json"
        
        # Cargar aristas existentes
        custom_edges = []
        if custom_edges_file.exists():
            with open(custom_edges_file, 'r') as f:
                custom_edges = json.load(f)
        
        # Agregar nueva arista
        edge_data = {
            **edge.dict(),
            "id": f"{edge.source}-{edge.target}-{len(custom_edges)}",
            "added_at": datetime.utcnow().isoformat()
        }
        custom_edges.append(edge_data)
        
        # Guardar aristas actualizadas
        with open(custom_edges_file, 'w') as f:
            json.dump(custom_edges, f, indent=2)
        
        logger.info("✅ Arista agregada exitosamente")
        
        return {
            "status": "success",
            "message": f"Relación {edge.relation} agregada",
            "total_custom_edges": len(custom_edges)
        }
        
    except Exception as e:
        logger.error(f"❌ Error al agregar arista: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/nodes/custom")
async def get_custom_nodes(case_id: str):
    """Obtiene todos los nodos personalizados de un caso"""
    try:
        custom_nodes_file = EVIDENCE_DIR / case_id / "custom_nodes.json"
        
        if not custom_nodes_file.exists():
            return {"custom_nodes": []}
        
        with open(custom_nodes_file, 'r') as f:
            custom_nodes = json.load(f)
        
        return {
            "custom_nodes": list(custom_nodes.values()),
            "total": len(custom_nodes)
        }
        
    except Exception as e:
        logger.error(f"❌ Error al obtener nodos personalizados: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/edges/custom")
async def get_custom_edges(case_id: str):
    """Obtiene todas las aristas personalizadas de un caso"""
    try:
        custom_edges_file = EVIDENCE_DIR / case_id / "custom_edges.json"
        
        if not custom_edges_file.exists():
            return {"custom_edges": []}
        
        with open(custom_edges_file, 'r') as f:
            custom_edges = json.load(f)
        
        return {
            "custom_edges": custom_edges,
            "total": len(custom_edges)
        }
        
    except Exception as e:
        logger.error(f"❌ Error al obtener aristas personalizadas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/nodes/{node_id}")
async def update_custom_node(case_id: str, node_id: str, node: CustomNode):
    """Actualiza un nodo personalizado existente"""
    try:
        custom_nodes_file = EVIDENCE_DIR / case_id / "custom_nodes.json"
        
        if not custom_nodes_file.exists():
            raise HTTPException(status_code=404, detail=f"Nodo {node_id} no encontrado")
        
        with open(custom_nodes_file, 'r') as f:
            custom_nodes = json.load(f)
        
        if node_id not in custom_nodes:
            raise HTTPException(status_code=404, detail=f"Nodo {node_id} no encontrado")
        
        # Actualizar nodo preservando timestamp de creación
        created_at = custom_nodes[node_id].get("added_at")
        custom_nodes[node_id] = {
            **node.dict(),
            "added_at": created_at,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        with open(custom_nodes_file, 'w') as f:
            json.dump(custom_nodes, f, indent=2)
        
        logger.info(f"✅ Nodo {node_id} actualizado")
        
        return {
            "status": "success",
            "message": f"Nodo {node_id} actualizado"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error al actualizar nodo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/nodes/{node_id}")
async def delete_custom_node(case_id: str, node_id: str):
    """Elimina un nodo personalizado"""
    try:
        custom_nodes_file = EVIDENCE_DIR / case_id / "custom_nodes.json"
        
        if not custom_nodes_file.exists():
            raise HTTPException(status_code=404, detail=f"Nodo {node_id} no encontrado")
        
        with open(custom_nodes_file, 'r') as f:
            custom_nodes = json.load(f)
        
        if node_id not in custom_nodes:
            raise HTTPException(status_code=404, detail=f"Nodo {node_id} no encontrado")
        
        del custom_nodes[node_id]
        
        with open(custom_nodes_file, 'w') as f:
            json.dump(custom_nodes, f, indent=2)
        
        logger.info(f"✅ Nodo {node_id} eliminado")
        
        return {
            "status": "success",
            "message": f"Nodo {node_id} eliminado"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error al eliminar nodo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/nodes/link-to-users")
async def link_node_to_users(
    case_id: str,
    node_id: str,
    user_ids: List[str]
):
    """Vincula un nodo personalizado a usuarios M365"""
    try:
        custom_nodes_file = EVIDENCE_DIR / case_id / "custom_nodes.json"
        
        if not custom_nodes_file.exists():
            raise HTTPException(status_code=404, detail="Caso no encontrado")
        
        with open(custom_nodes_file, 'r') as f:
            custom_nodes = json.load(f)
        
        if node_id not in custom_nodes:
            raise HTTPException(status_code=404, detail=f"Nodo {node_id} no encontrado")
        
        custom_nodes[node_id]["linked_users"] = user_ids
        custom_nodes[node_id]["updated_at"] = datetime.utcnow().isoformat()
        
        with open(custom_nodes_file, 'w') as f:
            json.dump(custom_nodes, f, indent=2)
        
        logger.info(f"✅ Nodo {node_id} vinculado a {len(user_ids)} usuario(s)")
        
        return {
            "status": "success",
            "message": f"Nodo vinculado a {len(user_ids)} usuario(s)",
            "linked_users": user_ids
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error al vincular nodo a usuarios: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/nodes/link-to-devices")
async def link_node_to_devices(
    case_id: str,
    node_id: str,
    device_ids: List[str]
):
    """Vincula un nodo personalizado a dispositivos"""
    try:
        custom_nodes_file = EVIDENCE_DIR / case_id / "custom_nodes.json"
        
        if not custom_nodes_file.exists():
            raise HTTPException(status_code=404, detail="Caso no encontrado")
        
        with open(custom_nodes_file, 'r') as f:
            custom_nodes = json.load(f)
        
        if node_id not in custom_nodes:
            raise HTTPException(status_code=404, detail=f"Nodo {node_id} no encontrado")
        
        custom_nodes[node_id]["linked_devices"] = device_ids
        custom_nodes[node_id]["updated_at"] = datetime.utcnow().isoformat()
        
        with open(custom_nodes_file, 'w') as f:
            json.dump(custom_nodes, f, indent=2)
        
        logger.info(f"✅ Nodo {node_id} vinculado a {len(device_ids)} dispositivo(s)")
        
        return {
            "status": "success",
            "message": f"Nodo vinculado a {len(device_ids)} dispositivo(s)",
            "linked_devices": device_ids
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error al vincular nodo a dispositivos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
