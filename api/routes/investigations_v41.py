"""
🔍 Investigations Routes v4.1 - Real Data with Demo Fallback
Endpoints para gestión de investigaciones usando datos reales de DB.
Fallback a datos demo cuando la DB está vacía.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from api.services.dashboard_data import dashboard_data
from api.services.graph_builder import graph_builder
from api.config import settings
from api.config_data.demo_data import (
    get_demo_investigations,
    get_demo_iocs,
    get_demo_timeline,
    get_demo_graph
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v41/investigations", tags=["Investigations v4.1"])

# ============================================================================
# SCHEMAS
# ============================================================================

class Investigation(BaseModel):
    """Información de investigación/caso"""
    id: str
    name: str
    severity: str
    status: str
    created_at: str
    updated_at: Optional[str] = None
    assigned_to: Optional[str] = None
    description: Optional[str] = None
    iocs_count: int = 0
    evidence_count: int = 0
    case_type: Optional[str] = None
    is_demo: bool = False

class IOCModel(BaseModel):
    """Indicador de Compromiso"""
    id: str
    type: str
    value: str
    severity: Optional[str] = None
    source: Optional[str] = None
    created_at: Optional[str] = None

class CreateInvestigationRequest(BaseModel):
    """Solicitud para crear investigación"""
    name: str
    description: Optional[str] = None
    severity: str = "medium"
    case_type: Optional[str] = None
    assigned_to: Optional[str] = None

class AddIOCRequest(BaseModel):
    """Solicitud para agregar IOC"""
    type: str  # ip, domain, hash, email, etc.
    value: str
    severity: str = "medium"
    source: Optional[str] = None
    description: Optional[str] = None

# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/", summary="Listar todas las investigaciones")
async def list_investigations(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = Query(50, le=100)
) -> Dict[str, Any]:
    """
    📋 Listar todas las investigaciones/casos
    
    Response incluye `data_source: "real"` o `"demo"` para indicar origen.
    """
    try:
        # Intentar obtener datos reales
        cases = dashboard_data.get_all_cases()
        
        if cases:
            # Filtrar si es necesario
            if status:
                cases = [c for c in cases if c.get("status") == status]
            if severity:
                cases = [c for c in cases if c.get("priority") == severity]
            
            investigations = [
                {
                    "id": c.get("case_id"),
                    "name": c.get("title"),
                    "severity": c.get("priority", "medium"),
                    "status": c.get("status", "open"),
                    "created_at": c.get("created_at"),
                    "updated_at": c.get("updated_at"),
                    "assigned_to": c.get("assigned_to"),
                    "description": c.get("description"),
                    "iocs_count": c.get("iocs_count", 0),
                    "evidence_count": c.get("evidence_count", 0),
                    "case_type": c.get("threat_type"),
                    "is_demo": False
                }
                for c in cases[:limit]
            ]
            data_source = "real"
            logger.info(f"📋 Retornando {len(investigations)} investigaciones reales")
        else:
            if settings.DEMO_DATA_ENABLED:
                # Fallback a demo solo si está habilitado explícitamente
                demo_investigations = get_demo_investigations()
                
                if status:
                    demo_investigations = [i for i in demo_investigations if i.get("status") == status]
                if severity:
                    demo_investigations = [i for i in demo_investigations if i.get("severity") == severity]
                
                investigations = demo_investigations[:limit]
                data_source = "demo"
                logger.info(f"📋 Retornando {len(investigations)} investigaciones demo (DB vacía)")
            else:
                investigations = []
                data_source = "empty"
                logger.info("📋 Sin investigaciones reales y fallback demo deshabilitado")
        
        return {
            "total": len(investigations),
            "investigations": investigations,
            "data_source": data_source
        }
    
    except Exception as e:
        logger.error(f"❌ Error al listar investigaciones: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{investigation_id}", summary="Obtener detalles de investigación")
async def get_investigation(investigation_id: str) -> Dict[str, Any]:
    """
    🔍 Obtener detalles completos de una investigación
    """
    try:
        # Buscar en datos reales
        cases = dashboard_data.get_all_cases()
        case = next((c for c in cases if c.get("case_id") == investigation_id), None)
        
        if case:
            # Obtener IOCs reales
            iocs = dashboard_data.get_iocs_by_case(investigation_id)
            
            return {
                "investigation": {
                    "id": case.get("case_id"),
                    "name": case.get("title"),
                    "severity": case.get("priority"),
                    "status": case.get("status"),
                    "created_at": case.get("created_at"),
                    "updated_at": case.get("updated_at"),
                    "assigned_to": case.get("assigned_to"),
                    "description": case.get("description"),
                    "case_type": case.get("threat_type"),
                    "iocs_count": len(iocs),
                    "is_demo": False
                },
                "iocs": iocs,
                "data_source": "real"
            }
        
        # Buscar en demo solo si está habilitado
        if settings.DEMO_DATA_ENABLED:
            demo_investigations = get_demo_investigations()
            demo_inv = next((i for i in demo_investigations if i.get("id") == investigation_id), None)
            
            if demo_inv:
                demo_iocs = get_demo_iocs(investigation_id)
                return {
                    "investigation": demo_inv,
                    "iocs": demo_iocs,
                    "data_source": "demo"
                }
        
        raise HTTPException(status_code=404, detail=f"Investigación {investigation_id} no encontrada")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error al obtener investigación: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", summary="Crear nueva investigación")
async def create_investigation(request: CreateInvestigationRequest) -> Dict[str, Any]:
    """
    ➕ Crear una nueva investigación
    
    Crea datos REALES en la base de datos, no usa demo.
    """
    try:
        # Generar ID
        case_id = f"IR-{datetime.now().strftime('%Y')}-{datetime.now().strftime('%m%d%H%M')}"
        
        # Crear en DB real
        result = dashboard_data.create_case(
            case_id=case_id,
            title=request.name,
            priority=request.severity,
            threat_type=request.case_type,
            description=request.description
        )
        
        if result.get("success"):
            logger.info(f"➕ Investigación {case_id} creada")
            return {
                "success": True,
                "investigation_id": case_id,
                "message": f"Investigación '{request.name}' creada exitosamente",
                "data_source": "real"
            }
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Error al crear"))
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error al crear investigación: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{investigation_id}/iocs", summary="Listar IOCs de investigación")
async def get_investigation_iocs(investigation_id: str) -> Dict[str, Any]:
    """
    🔍 Obtener IOCs de una investigación
    """
    try:
        # Buscar IOCs reales
        iocs = dashboard_data.get_iocs_by_case(investigation_id)
        
        if iocs:
            return {
                "investigation_id": investigation_id,
                "total": len(iocs),
                "iocs": iocs,
                "data_source": "real"
            }
        
        # Fallback a demo solo si está habilitado
        if settings.DEMO_DATA_ENABLED:
            demo_iocs = get_demo_iocs(investigation_id)
            if demo_iocs:
                return {
                    "investigation_id": investigation_id,
                    "total": len(demo_iocs),
                    "iocs": demo_iocs,
                    "data_source": "demo"
                }
        
        return {
            "investigation_id": investigation_id,
            "total": 0,
            "iocs": [],
            "data_source": "empty"
        }
    
    except Exception as e:
        logger.error(f"❌ Error al obtener IOCs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{investigation_id}/iocs", summary="Agregar IOC a investigación")
async def add_ioc(investigation_id: str, request: AddIOCRequest) -> Dict[str, Any]:
    """
    ➕ Agregar un IOC a una investigación
    
    Crea datos REALES en la base de datos.
    """
    try:
        result = dashboard_data.add_ioc(
            case_id=investigation_id,
            ioc_type=request.type,
            value=request.value,
            severity=request.severity,
            source=request.source or "Manual entry",
            description=request.description
        )
        
        if result.get("success"):
            logger.info(f"➕ IOC agregado a {investigation_id}: {request.type}={request.value}")
            return {
                "success": True,
                "ioc_id": result.get("ioc_id"),
                "message": f"IOC {request.type} agregado exitosamente",
                "data_source": "real"
            }
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Error al agregar IOC"))
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error al agregar IOC: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{investigation_id}/timeline", summary="Obtener timeline de investigación")
async def get_investigation_timeline(investigation_id: str) -> Dict[str, Any]:
    """
    📅 Obtener timeline de eventos de una investigación
    """
    try:
        # Intentar obtener timeline real
        timeline = dashboard_data.get_case_timeline(investigation_id)
        
        if timeline:
            return {
                "investigation_id": investigation_id,
                "total": len(timeline),
                "events": timeline,
                "data_source": "real"
            }
        
        # Fallback a demo solo si está habilitado
        if settings.DEMO_DATA_ENABLED:
            demo_timeline = get_demo_timeline(investigation_id)
            if demo_timeline:
                return {
                    "investigation_id": investigation_id,
                    "total": len(demo_timeline),
                    "events": demo_timeline,
                    "data_source": "demo"
                }
        
        return {
            "investigation_id": investigation_id,
            "total": 0,
            "events": [],
            "data_source": "empty"
        }
    
    except Exception as e:
        logger.error(f"❌ Error al obtener timeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{investigation_id}/graph", summary="Obtener attack graph de investigación")
async def get_investigation_graph(investigation_id: str) -> Dict[str, Any]:
    """
    🕸️ Obtener attack graph de una investigación
    """
    try:
        # Intentar obtener grafo real
        graph = await graph_builder.build_graph_for_case(investigation_id)
        
        if graph and (graph.get("nodes") or graph.get("edges")):
            return {
                "investigation_id": investigation_id,
                "nodes_count": len(graph.get("nodes", [])),
                "edges_count": len(graph.get("edges", [])),
                "graph": graph,
                "data_source": "real"
            }
        
        # Fallback a demo solo si está habilitado
        if settings.DEMO_DATA_ENABLED:
            demo_graph = get_demo_graph(investigation_id)
            if demo_graph.get("nodes"):
                return {
                    "investigation_id": investigation_id,
                    "nodes_count": len(demo_graph.get("nodes", [])),
                    "edges_count": len(demo_graph.get("edges", [])),
                    "graph": demo_graph,
                    "data_source": "demo"
                }
        
        return {
            "investigation_id": investigation_id,
            "nodes_count": 0,
            "edges_count": 0,
            "graph": {"nodes": [], "edges": []},
            "data_source": "empty"
        }
    
    except Exception as e:
        logger.error(f"❌ Error al obtener graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/summary", summary="Estadísticas de investigaciones")
async def get_investigation_stats() -> Dict[str, Any]:
    """
    📊 Obtener estadísticas de investigaciones
    """
    try:
        stats = dashboard_data.get_cases_stats()
        
        if stats and stats.get("total", 0) > 0:
            return {
                "total": stats.get("total", 0),
                "active": stats.get("active", 0),
                "closed": stats.get("closed", 0),
                "by_priority": stats.get("by_priority", {}),
                "by_status": stats.get("by_status", {}),
                "by_threat_type": stats.get("by_threat", {}),
                "data_source": "real"
            }
        
        if settings.DEMO_DATA_ENABLED:
            # Demo stats
            demo_investigations = get_demo_investigations()
            return {
                "total": len(demo_investigations),
                "active": len([i for i in demo_investigations if i["status"] != "closed"]),
                "closed": len([i for i in demo_investigations if i["status"] == "closed"]),
                "by_priority": {
                    "critical": len([i for i in demo_investigations if i.get("severity") == "critical"]),
                    "high": len([i for i in demo_investigations if i.get("severity") == "high"]),
                    "medium": len([i for i in demo_investigations if i.get("severity") == "medium"]),
                    "low": len([i for i in demo_investigations if i.get("severity") == "low"])
                },
                "by_status": {
                    "open": len([i for i in demo_investigations if i.get("status") == "open"]),
                    "in-progress": len([i for i in demo_investigations if i.get("status") == "in-progress"]),
                    "closed": len([i for i in demo_investigations if i.get("status") == "closed"])
                },
                "data_source": "demo"
            }
        
        return {
            "total": 0,
            "active": 0,
            "closed": 0,
            "by_priority": {},
            "by_status": {},
            "data_source": "empty"
        }
    
    except Exception as e:
        logger.error(f"❌ Error al obtener stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{investigation_id}/status", summary="Actualizar estado de investigación")
async def update_investigation_status(
    investigation_id: str,
    status: str = Query(..., description="Nuevo estado: open, in-progress, on-hold, resolved, closed")
) -> Dict[str, Any]:
    """
    🔄 Actualizar el estado de una investigación
    """
    try:
        valid_statuses = ["open", "in-progress", "on-hold", "resolved", "closed"]
        if status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Estado inválido. Use: {valid_statuses}")
        
        result = dashboard_data.update_case_status(investigation_id, status)
        
        if result.get("success"):
            logger.info(f"🔄 Investigación {investigation_id} actualizada a {status}")
            return {
                "success": True,
                "investigation_id": investigation_id,
                "new_status": status,
                "data_source": "real"
            }
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Error al actualizar"))
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error al actualizar estado: {e}")
        raise HTTPException(status_code=500, detail=str(e))
