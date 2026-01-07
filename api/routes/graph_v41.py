"""
MCP v4.1 - Graph Routes
Rutas API para el grafo de ataque enriquecido.
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
import logging

from api.middleware.auth import verify_api_key
from api.database import get_db_context
from api.models.tools import GraphNode, GraphEdge, NodeType, EdgeType
from api.services.graph_enricher import graph_enricher

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v41/graph", tags=["Attack Graph v4.1"])


# =============================================================================
# SCHEMAS
# =============================================================================

class CreateNodeRequest(BaseModel):
    """Request para crear nodo"""
    value: str = Field(..., description="Valor del nodo")
    node_type: str = Field(..., description="Tipo de nodo")
    label: Optional[str] = Field(None, description="Etiqueta")
    properties: Dict[str, Any] = Field(default={})
    case_id: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "value": "192.168.1.100",
                "node_type": "ip_address",
                "label": "C2 Server",
                "case_id": "CASE-001"
            }
        }


class CreateEdgeRequest(BaseModel):
    """Request para crear arista"""
    source_id: str = Field(..., description="ID nodo origen")
    target_id: str = Field(..., description="ID nodo destino")
    edge_type: str = Field(..., description="Tipo de relación")
    label: Optional[str] = None
    properties: Dict[str, Any] = Field(default={})
    weight: float = Field(default=1.0)
    case_id: Optional[str] = None


class SearchNodesRequest(BaseModel):
    """Request para búsqueda"""
    query: str
    node_type: Optional[str] = None
    limit: int = Field(default=20, le=100)


class FindPathRequest(BaseModel):
    """Request para encontrar caminos"""
    source_id: str
    target_id: str
    max_depth: int = Field(default=5, le=10)


# =============================================================================
# GRAPH DATA
# =============================================================================

@router.get("/data", summary="Obtener datos del grafo")
async def get_graph_data(
    case_id: Optional[str] = Query(None),
    node_types: Optional[str] = Query(None, description="Tipos separados por coma"),
    limit_nodes: int = Query(200, le=500),
    limit_edges: int = Query(500, le=1000),
    _: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Obtiene datos del grafo para visualización.
    Formato compatible con D3.js y Cytoscape.
    """
    types_list = node_types.split(",") if node_types else None
    
    data = graph_enricher.get_graph_data(
        case_id=case_id,
        node_types=types_list,
        limit_nodes=limit_nodes,
        limit_edges=limit_edges
    )
    
    return data


@router.get("/neighborhood/{node_id}", summary="Obtener vecindario")
async def get_node_neighborhood(
    node_id: str,
    depth: int = Query(2, le=5),
    max_nodes: int = Query(50, le=100),
    _: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Obtiene el vecindario de un nodo hasta cierta profundidad.
    """
    data = graph_enricher.get_node_neighborhood(
        node_id=node_id,
        depth=depth,
        max_nodes=max_nodes
    )
    
    if not data["nodes"]:
        raise HTTPException(status_code=404, detail="Node not found")
    
    return data


@router.get("/stats", summary="Estadísticas del grafo")
async def get_graph_stats(
    case_id: Optional[str] = Query(None),
    _: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Obtiene estadísticas del grafo.
    """
    return graph_enricher.get_graph_stats(case_id=case_id)


# =============================================================================
# NODES
# =============================================================================

@router.get("/nodes", summary="Listar nodos")
async def list_nodes(
    case_id: Optional[str] = Query(None),
    node_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    _: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Lista nodos del grafo.
    """
    with get_db_context() as db:
        query = db.query(GraphNode)
        
        if case_id:
            query = query.filter(GraphNode.case_ids.contains([case_id]))
        if node_type:
            query = query.filter(GraphNode.node_type == node_type)
        if status:
            query = query.filter(GraphNode.status == status)
        
        nodes = query.order_by(GraphNode.last_seen.desc()).limit(limit).all()
    
    return {
        "total": len(nodes),
        "nodes": [
            {
                "id": n.id,
                "type": n.node_type,
                "value": n.value,
                "label": n.label,
                "status": n.status,
                "source": n.source,
                "first_seen": n.first_seen.isoformat() if n.first_seen else None,
                "last_seen": n.last_seen.isoformat() if n.last_seen else None
            }
            for n in nodes
        ]
    }


@router.get("/nodes/{node_id}", summary="Obtener nodo")
async def get_node(
    node_id: str,
    _: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Obtiene detalles de un nodo.
    """
    with get_db_context() as db:
        node = db.query(GraphNode).filter(GraphNode.id == node_id).first()
        
        if not node:
            raise HTTPException(status_code=404, detail="Node not found")
        
        # Contar conexiones
        outgoing = db.query(GraphEdge).filter(
            GraphEdge.source_id == node_id
        ).count()
        
        incoming = db.query(GraphEdge).filter(
            GraphEdge.target_id == node_id
        ).count()
    
    return {
        "id": node.id,
        "type": node.node_type,
        "value": node.value,
        "label": node.label,
        "status": node.status,
        "properties": node.properties,
        "source": node.source,
        "case_ids": node.case_ids,
        "first_seen": node.first_seen.isoformat() if node.first_seen else None,
        "last_seen": node.last_seen.isoformat() if node.last_seen else None,
        "connections": {
            "outgoing": outgoing,
            "incoming": incoming,
            "total": outgoing + incoming
        }
    }


@router.post("/nodes", summary="Crear nodo")
async def create_node(
    request: CreateNodeRequest,
    _: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Crea un nodo en el grafo.
    """
    try:
        node_type = NodeType(request.node_type)
    except ValueError:
        valid_types = [t.value for t in NodeType]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid node_type. Must be one of: {valid_types}"
        )
    
    node_id = await graph_enricher.create_node(
        value=request.value,
        node_type=node_type,
        label=request.label,
        properties=request.properties,
        case_id=request.case_id,
        source="api"
    )
    
    return {
        "id": node_id,
        "value": request.value,
        "type": request.node_type,
        "message": "Node created"
    }


@router.delete("/nodes/{node_id}", summary="Eliminar nodo")
async def delete_node(
    node_id: str,
    _: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Elimina un nodo y sus aristas.
    """
    with get_db_context() as db:
        node = db.query(GraphNode).filter(GraphNode.id == node_id).first()
        
        if not node:
            raise HTTPException(status_code=404, detail="Node not found")
        
        # Eliminar aristas
        db.query(GraphEdge).filter(
            (GraphEdge.source_id == node_id) | (GraphEdge.target_id == node_id)
        ).delete()
        
        db.delete(node)
        db.commit()
    
    return {"success": True, "message": "Node and edges deleted"}


@router.post("/nodes/search", summary="Buscar nodos")
async def search_nodes(
    request: SearchNodesRequest,
    _: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Busca nodos por valor o label.
    """
    results = graph_enricher.search_nodes(
        query=request.query,
        node_type=request.node_type,
        limit=request.limit
    )
    
    return {
        "query": request.query,
        "total": len(results),
        "results": results
    }


# =============================================================================
# EDGES
# =============================================================================

@router.get("/edges", summary="Listar aristas")
async def list_edges(
    case_id: Optional[str] = Query(None),
    edge_type: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    _: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Lista aristas del grafo.
    """
    with get_db_context() as db:
        query = db.query(GraphEdge)
        
        if case_id:
            query = query.filter(GraphEdge.case_ids.contains([case_id]))
        if edge_type:
            query = query.filter(GraphEdge.edge_type == edge_type)
        
        edges = query.order_by(GraphEdge.last_seen.desc()).limit(limit).all()
    
    return {
        "total": len(edges),
        "edges": [
            {
                "id": e.id,
                "source": e.source_id,
                "target": e.target_id,
                "type": e.edge_type,
                "label": e.label,
                "weight": e.weight,
                "first_seen": e.first_seen.isoformat() if e.first_seen else None
            }
            for e in edges
        ]
    }


@router.post("/edges", summary="Crear arista")
async def create_edge(
    request: CreateEdgeRequest,
    _: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Crea una arista entre dos nodos.
    """
    try:
        edge_type = EdgeType(request.edge_type)
    except ValueError:
        valid_types = [t.value for t in EdgeType]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid edge_type. Must be one of: {valid_types}"
        )
    
    # Verificar que existen los nodos
    with get_db_context() as db:
        source = db.query(GraphNode).filter(
            GraphNode.id == request.source_id
        ).first()
        target = db.query(GraphNode).filter(
            GraphNode.id == request.target_id
        ).first()
        
        if not source:
            raise HTTPException(status_code=404, detail="Source node not found")
        if not target:
            raise HTTPException(status_code=404, detail="Target node not found")
    
    edge_id = await graph_enricher.create_edge(
        source_id=request.source_id,
        target_id=request.target_id,
        edge_type=edge_type,
        label=request.label,
        properties=request.properties,
        weight=request.weight,
        case_id=request.case_id
    )
    
    return {
        "id": edge_id,
        "source": request.source_id,
        "target": request.target_id,
        "type": request.edge_type,
        "message": "Edge created"
    }


@router.delete("/edges/{edge_id}", summary="Eliminar arista")
async def delete_edge(
    edge_id: str,
    _: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Elimina una arista.
    """
    with get_db_context() as db:
        edge = db.query(GraphEdge).filter(GraphEdge.id == edge_id).first()
        
        if not edge:
            raise HTTPException(status_code=404, detail="Edge not found")
        
        db.delete(edge)
        db.commit()
    
    return {"success": True, "message": "Edge deleted"}


# =============================================================================
# PATH FINDING
# =============================================================================

@router.post("/paths", summary="Encontrar caminos")
async def find_paths(
    request: FindPathRequest,
    _: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Encuentra caminos de ataque entre dos nodos.
    """
    paths = await graph_enricher.find_attack_paths(
        source_id=request.source_id,
        target_id=request.target_id,
        max_depth=request.max_depth
    )
    
    return {
        "source": request.source_id,
        "target": request.target_id,
        "paths_found": len(paths),
        "paths": paths
    }


# =============================================================================
# NODE TYPES & EDGE TYPES
# =============================================================================

@router.get("/types/nodes", summary="Tipos de nodos")
async def get_node_types(
    _: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Lista tipos de nodos disponibles.
    """
    return {
        "node_types": [
            {"value": t.value, "label": t.value.replace("_", " ").title()}
            for t in NodeType
        ]
    }


@router.get("/types/edges", summary="Tipos de aristas")
async def get_edge_types(
    _: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Lista tipos de aristas disponibles.
    """
    return {
        "edge_types": [
            {"value": t.value, "label": t.value.replace("_", " ").title()}
            for t in EdgeType
        ]
    }


# =============================================================================
# IOC INTEGRATION
# =============================================================================

@router.post("/iocs/{ioc_id}/node", summary="Crear nodo desde IOC")
async def create_node_from_ioc(
    ioc_id: str,
    case_id: Optional[str] = Query(None),
    _: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Crea un nodo en el grafo desde un IOC existente.
    """
    try:
        node_id = await graph_enricher.create_ioc_node(
            ioc_id=ioc_id,
            case_id=case_id
        )
        
        return {
            "node_id": node_id,
            "ioc_id": ioc_id,
            "message": "Node created from IOC"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# =============================================================================
# EXPORT
# =============================================================================

@router.get("/export", summary="Exportar grafo")
async def export_graph(
    case_id: Optional[str] = Query(None),
    format: str = Query("json", description="json o graphml"),
    _: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Exporta el grafo completo en formato JSON o GraphML.
    """
    data = graph_enricher.get_graph_data(
        case_id=case_id,
        limit_nodes=1000,
        limit_edges=5000
    )
    
    if format == "json":
        return data
    elif format == "graphml":
        # Generar GraphML
        graphml = _generate_graphml(data)
        return {"format": "graphml", "content": graphml}
    else:
        raise HTTPException(status_code=400, detail="Format must be 'json' or 'graphml'")


def _generate_graphml(data: Dict) -> str:
    """Genera contenido GraphML"""
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">',
        '  <key id="label" for="node" attr.name="label" attr.type="string"/>',
        '  <key id="type" for="node" attr.name="type" attr.type="string"/>',
        '  <key id="weight" for="edge" attr.name="weight" attr.type="double"/>',
        '  <graph id="G" edgedefault="directed">'
    ]
    
    for node in data.get("nodes", []):
        lines.append(f'    <node id="{node["id"]}">')
        lines.append(f'      <data key="label">{node.get("label", "")}</data>')
        lines.append(f'      <data key="type">{node.get("type", "")}</data>')
        lines.append('    </node>')
    
    for edge in data.get("edges", []):
        lines.append(f'    <edge source="{edge["source"]}" target="{edge["target"]}">')
        lines.append(f'      <data key="weight">{edge.get("weight", 1.0)}</data>')
        lines.append('    </edge>')
    
    lines.append('  </graph>')
    lines.append('</graphml>')
    
    return '\n'.join(lines)
