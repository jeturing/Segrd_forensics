"""
🔍 Investigaciones - Case Management & Attack Graph
Endpoints para gestionar casos forenses y análisis de amenazas
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/investigations", tags=["Investigations"])

# ============================================================================
# MODELOS PYDANTIC
# ============================================================================

class Investigation(BaseModel):
    """Información de investigación/caso"""
    id: str
    name: str
    severity: str  # critical, high, medium, low
    status: str  # open, in-progress, on-hold, resolved, closed
    created_at: str
    updated_at: str
    assigned_to: str
    description: str
    iocs_count: int
    evidence_count: int
    case_type: Optional[str] = None
    created_by: Optional[str] = None

class IOC(BaseModel):
    """Indicador de Compromiso"""
    id: str
    type: str  # email, ip, domain, file_hash, user
    value: str
    severity: Optional[str] = None
    source: Optional[str] = None
    created_at: Optional[str] = None

class Evidence(BaseModel):
    """Evidencia en una investigación"""
    id: str
    type: str  # m365_log, oauth, network, endpoint, credential
    source: str  # Sparrow, Hawk, Loki, YARA, etc
    count: int
    data_size: Optional[str] = None
    collected_at: Optional[str] = None

class TimelineEvent(BaseModel):
    """Evento en timeline de investigación"""
    timestamp: str
    event_type: str
    description: str
    severity: str
    source: str

class AttackGraphNode(BaseModel):
    """Nodo en grafo de ataque"""
    id: str
    label: str
    type: str  # user, mailbox, ip, domain, application
    severity: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class AttackGraphEdge(BaseModel):
    """Arista en grafo de ataque"""
    source: str
    target: str
    relationship: str  # compromised, communicates_with, authenticates_to
    evidence_count: Optional[int] = None

# ============================================================================
# SIMULATED DATA
# ============================================================================

SIMULATED_INVESTIGATIONS = [
    {
        "id": "IR-2025-001",
        "name": "Email Abuse Investigation",
        "severity": "critical",
        "status": "in-progress",
        "created_at": "2025-12-01T10:30:00Z",
        "updated_at": "2025-12-05T14:32:00Z",
        "assigned_to": "John Doe",
        "description": "Unusual email forwarding rules and OAuth app grants detected",
        "iocs_count": 12,
        "evidence_count": 8,
        "case_type": "m365_compromise",
        "created_by": "SIEM Alert"
    },
    {
        "id": "IR-2025-002",
        "name": "Ransomware Deployment",
        "severity": "high",
        "status": "open",
        "created_at": "2025-12-04T09:15:00Z",
        "updated_at": "2025-12-05T08:00:00Z",
        "assigned_to": "Jane Smith",
        "description": "Suspicious executable detected on file server",
        "iocs_count": 5,
        "evidence_count": 4,
        "case_type": "endpoint_threat",
        "created_by": "Antivirus Alert"
    },
    {
        "id": "IR-2024-999",
        "name": "Credential Exposure Analysis",
        "severity": "high",
        "status": "resolved",
        "created_at": "2024-11-15T15:00:00Z",
        "updated_at": "2024-12-02T12:00:00Z",
        "assigned_to": "Bob Wilson",
        "description": "Domain credentials found in breach database",
        "iocs_count": 8,
        "evidence_count": 6,
        "case_type": "credential_leak",
        "created_by": "HIBP Check"
    },
    {
        "id": "IR-2025-003",
        "name": "Suspicious Network Activity",
        "severity": "critical",
        "status": "on-hold",
        "created_at": "2025-12-03T11:45:00Z",
        "updated_at": "2025-12-04T16:20:00Z",
        "assigned_to": "Alice Johnson",
        "description": "Command & Control traffic detected from endpoint",
        "iocs_count": 15,
        "evidence_count": 10,
        "case_type": "network_c2",
        "created_by": "IDS Alert"
    }
]

SIMULATED_IOCS = {
    "IR-2025-001": [
        {"id": "ioc-001", "type": "email", "value": "attacker@external.com", "severity": "critical", "source": "Sparrow"},
        {"id": "ioc-002", "type": "ip", "value": "203.0.113.45", "severity": "high", "source": "Hawk"},
        {"id": "ioc-003", "type": "domain", "value": "malicious-command.com", "severity": "critical", "source": "O365 UAL"},
    ]
}

SIMULATED_EVIDENCE = {
    "IR-2025-001": [
        {"id": "ev-001", "type": "m365_log", "source": "Sparrow", "count": 156, "data_size": "45 MB"},
        {"id": "ev-002", "type": "oauth", "source": "Hawk", "count": 8, "data_size": "2 MB"},
        {"id": "ev-003", "type": "network", "source": "Network capture", "count": 1234, "data_size": "180 MB"},
    ]
}

SIMULATED_TIMELINE = {
    "IR-2025-001": [
        {
            "timestamp": "2025-12-01T10:30:00Z",
            "event_type": "investigation_created",
            "description": "Investigation IR-2025-001 opened",
            "severity": "info",
            "source": "SIEM"
        },
        {
            "timestamp": "2025-12-01T11:15:00Z",
            "event_type": "suspicious_sign_in",
            "description": "Sign-in from 203.0.113.45 (Nigeria)",
            "severity": "critical",
            "source": "Azure AD"
        },
        {
            "timestamp": "2025-12-01T12:30:00Z",
            "event_type": "oauth_grant",
            "description": "Suspicious OAuth app granted access to Calendar",
            "severity": "high",
            "source": "O365 UAL"
        },
        {
            "timestamp": "2025-12-01T14:00:00Z",
            "event_type": "email_rule_created",
            "description": "Email forwarding rule created to external domain",
            "severity": "critical",
            "source": "Exchange"
        }
    ]
}

SIMULATED_GRAPH = {
    "IR-2025-001": {
        "nodes": [
            {"data": {"id": "user1", "label": "user@empresa.com"}},
            {"data": {"id": "mailbox1", "label": "Mailbox Comprometido"}},
            {"data": {"id": "ip1", "label": "203.0.113.45"}},
            {"data": {"id": "app1", "label": "OAuth App - Calendar"}},
            {"data": {"id": "external", "label": "attacker@external.com"}},
        ],
        "edges": [
            {"data": {"source": "ip1", "target": "user1", "label": "sign-in"}},
            {"data": {"source": "user1", "target": "app1", "label": "granted"}},
            {"data": {"source": "mailbox1", "target": "external", "label": "forward"}},
            {"data": {"source": "app1", "target": "mailbox1", "label": "accessed"}},
        ]
    }
}

# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/", response_model=Dict[str, Any])
async def get_investigations(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = None,
    severity: Optional[str] = None,
    search: Optional[str] = None
):
    """
    📋 Listar investigaciones con paginación
    
    Query Parameters:
    - page: Número de página (default: 1)
    - limit: Resultados por página (default: 50, max: 100)
    - status: Filtrar por estado (open, in-progress, on-hold, resolved, closed)
    - severity: Filtrar por severidad (critical, high, medium, low)
    - search: Buscar por ID o nombre
    """
    try:
        items = SIMULATED_INVESTIGATIONS.copy()
        
        # Aplicar filtros
        if status:
            items = [i for i in items if i["status"] == status]
        
        if severity:
            items = [i for i in items if i["severity"] == severity]
        
        if search:
            search_lower = search.lower()
            items = [
                i for i in items 
                if search_lower in i["id"].lower() or search_lower in i["name"].lower()
            ]
        
        # Paginación
        total = len(items)
        start = (page - 1) * limit
        end = start + limit
        paginated = items[start:end]
        
        logger.info(f"📋 Retornando {len(paginated)} investigaciones (página {page})")
        
        return {
            "items": paginated,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }
    
    except Exception as e:
        logger.error(f"❌ Error al listar investigaciones: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{inv_id}", response_model=Investigation)
async def get_investigation(inv_id: str):
    """
    🔍 Obtener detalles de una investigación específica
    
    Path Parameters:
    - inv_id: ID de investigación (ej: IR-2025-001)
    """
    try:
        investigation = next(
            (i for i in SIMULATED_INVESTIGATIONS if i["id"] == inv_id),
            None
        )
        
        if not investigation:
            raise HTTPException(status_code=404, detail=f"Investigación {inv_id} no encontrada")
        
        logger.info(f"🔍 Detalles de {inv_id}")
        return investigation
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error al obtener investigación: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=Investigation)
async def create_investigation(investigation: Investigation):
    """
    ✨ Crear nueva investigación
    
    Body:
    {
        "id": "IR-2025-004",
        "name": "New Investigation",
        "severity": "high",
        "status": "open",
        "assigned_to": "Analyst Name",
        "description": "Investigation description",
        "iocs_count": 0,
        "evidence_count": 0
    }
    """
    try:
        # Asignar timestamps
        now = datetime.now().isoformat() + "Z"
        investigation.created_at = now
        investigation.updated_at = now
        
        logger.info(f"✨ Nueva investigación creada: {investigation.id}")
        return investigation
    
    except Exception as e:
        logger.error(f"❌ Error al crear investigación: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{inv_id}")
async def update_investigation(inv_id: str, updates: dict):
    """
    📝 Actualizar investigación
    
    Path Parameters:
    - inv_id: ID de investigación
    
    Body: Campo a actualizar (status, severity, assigned_to, etc)
    """
    try:
        investigation = next(
            (i for i in SIMULATED_INVESTIGATIONS if i["id"] == inv_id),
            None
        )
        
        if not investigation:
            raise HTTPException(status_code=404, detail=f"Investigación {inv_id} no encontrada")
        
        # Actualizar
        investigation.update(updates)
        investigation["updated_at"] = datetime.now().isoformat() + "Z"
        
        logger.info(f"📝 Investigación {inv_id} actualizada")
        return investigation
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error al actualizar investigación: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{inv_id}/evidence")
async def get_evidence(inv_id: str):
    """
    📦 Obtener evidencias de investigación
    
    Path Parameters:
    - inv_id: ID de investigación
    """
    try:
        investigation = next(
            (i for i in SIMULATED_INVESTIGATIONS if i["id"] == inv_id),
            None
        )
        
        if not investigation:
            raise HTTPException(status_code=404, detail=f"Investigación {inv_id} no encontrada")
        
        evidence = SIMULATED_EVIDENCE.get(inv_id, [])
        logger.info(f"📦 Evidencias de {inv_id}: {len(evidence)} items")
        
        return {
            "investigation_id": inv_id,
            "evidence_count": len(evidence),
            "evidence": evidence,
            "total_size": sum(
                float(e.get("data_size", "0 MB").split()[0]) 
                for e in evidence
            ),
            "collected_at": datetime.now().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error al obtener evidencias: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{inv_id}/iocs")
async def get_iocs(inv_id: str):
    """
    🔗 Obtener IOCs de investigación
    
    Path Parameters:
    - inv_id: ID de investigación
    """
    try:
        investigation = next(
            (i for i in SIMULATED_INVESTIGATIONS if i["id"] == inv_id),
            None
        )
        
        if not investigation:
            raise HTTPException(status_code=404, detail=f"Investigación {inv_id} no encontrada")
        
        iocs = SIMULATED_IOCS.get(inv_id, [])
        logger.info(f"🔗 IOCs de {inv_id}: {len(iocs)} items")
        
        return {
            "investigation_id": inv_id,
            "iocs_count": len(iocs),
            "iocs": iocs,
            "by_type": {
                "email": len([i for i in iocs if i["type"] == "email"]),
                "ip": len([i for i in iocs if i["type"] == "ip"]),
                "domain": len([i for i in iocs if i["type"] == "domain"]),
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error al obtener IOCs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{inv_id}/iocs")
async def add_ioc(inv_id: str, ioc: IOC):
    """
    ➕ Agregar IOC a investigación
    
    Path Parameters:
    - inv_id: ID de investigación
    
    Body:
    {
        "type": "email|ip|domain|file_hash|user",
        "value": "attacker@example.com",
        "severity": "critical|high|medium|low"
    }
    """
    try:
        investigation = next(
            (i for i in SIMULATED_INVESTIGATIONS if i["id"] == inv_id),
            None
        )
        
        if not investigation:
            raise HTTPException(status_code=404, detail=f"Investigación {inv_id} no encontrada")
        
        ioc.created_at = datetime.now().isoformat() + "Z"
        ioc.id = f"ioc-new-{datetime.now().timestamp()}"
        
        if inv_id not in SIMULATED_IOCS:
            SIMULATED_IOCS[inv_id] = []
        
        SIMULATED_IOCS[inv_id].append(ioc.dict())
        investigation["iocs_count"] += 1
        
        logger.info(f"➕ IOC agregado a {inv_id}: {ioc.type}={ioc.value}")
        
        return {
            "status": "created",
            "ioc_id": ioc.id,
            "investigation_id": inv_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error al agregar IOC: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{inv_id}/graph")
async def get_investigation_graph(inv_id: str):
    """
    📊 Obtener grafo de ataque (Cytoscape compatible)
    
    Path Parameters:
    - inv_id: ID de investigación
    
    Returns: nodes[] y edges[] para visualización en Cytoscape
    """
    try:
        investigation = next(
            (i for i in SIMULATED_INVESTIGATIONS if i["id"] == inv_id),
            None
        )
        
        if not investigation:
            raise HTTPException(status_code=404, detail=f"Investigación {inv_id} no encontrada")
        
        graph_data = SIMULATED_GRAPH.get(inv_id, {"nodes": [], "edges": []})
        logger.info(f"📊 Grafo de {inv_id}: {len(graph_data['nodes'])} nodos, {len(graph_data['edges'])} aristas")
        
        return graph_data
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error al obtener grafo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{inv_id}/timeline")
async def get_timeline(inv_id: str):
    """
    ⏱️ Obtener timeline de eventos de investigación
    
    Path Parameters:
    - inv_id: ID de investigación
    """
    try:
        investigation = next(
            (i for i in SIMULATED_INVESTIGATIONS if i["id"] == inv_id),
            None
        )
        
        if not investigation:
            raise HTTPException(status_code=404, detail=f"Investigación {inv_id} no encontrada")
        
        timeline = SIMULATED_TIMELINE.get(inv_id, [])
        logger.info(f"⏱️ Timeline de {inv_id}: {len(timeline)} eventos")
        
        return {
            "investigation_id": inv_id,
            "events": sorted(timeline, key=lambda e: e["timestamp"], reverse=True),
            "total_events": len(timeline)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error al obtener timeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{inv_id}/report")
async def generate_report(inv_id: str, format: str = Query("pdf", regex="^(pdf|json|html)$")):
    """
    📄 Generar reporte de investigación
    
    Path Parameters:
    - inv_id: ID de investigación
    
    Query Parameters:
    - format: Formato del reporte (pdf, json, html)
    """
    try:
        investigation = next(
            (i for i in SIMULATED_INVESTIGATIONS if i["id"] == inv_id),
            None
        )
        
        if not investigation:
            raise HTTPException(status_code=404, detail=f"Investigación {inv_id} no encontrada")
        
        logger.info(f"📄 Generando reporte de {inv_id} en formato {format}")
        
        return {
            "status": "generated",
            "investigation_id": inv_id,
            "format": format,
            "filename": f"Report-{inv_id}-{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}",
            "download_url": f"/api/investigations/{inv_id}/report/download?format={format}",
            "generated_at": datetime.now().isoformat(),
            "pages": 12,
            "sections": [
                "Executive Summary",
                "Investigation Timeline",
                "Indicators of Compromise",
                "Attack Graph Analysis",
                "Evidence Collection",
                "Recommendations"
            ]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error al generar reporte: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{inv_id}/close")
async def close_investigation(inv_id: str, reason: Optional[str] = None):
    """
    🔒 Cerrar investigación
    
    Path Parameters:
    - inv_id: ID de investigación
    
    Query Parameters:
    - reason: Motivo del cierre (opcional)
    """
    try:
        investigation = next(
            (i for i in SIMULATED_INVESTIGATIONS if i["id"] == inv_id),
            None
        )
        
        if not investigation:
            raise HTTPException(status_code=404, detail=f"Investigación {inv_id} no encontrada")
        
        investigation["status"] = "closed"
        investigation["updated_at"] = datetime.now().isoformat() + "Z"
        
        logger.info(f"🔒 Investigación {inv_id} cerrada: {reason or 'Sin motivo'}")
        
        return {
            "status": "success",
            "investigation_id": inv_id,
            "new_status": "closed",
            "closed_at": datetime.now().isoformat(),
            "reason": reason
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error al cerrar investigación: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# IOC INTEGRATION - v3 Database-backed
# ============================================================================

from sqlalchemy.orm import Session
from api.database import get_db
from api.models.investigation import InvestigationIocLink, InvestigationTimeline
from api.models.ioc import IocItem
from api.services.websocket_manager import notify_ioc_linked, notify_ioc_unlinked
from fastapi import Depends, BackgroundTasks


class LinkIocRequest(BaseModel):
    """Request para vincular IOC a investigación"""
    reason: Optional[str] = None
    context: Optional[str] = None
    relevance: str = "high"  # high, medium, low


@router.get("/{inv_id}/iocs")
async def get_investigation_iocs(
    inv_id: str,
    db: Session = Depends(get_db)
):
    """
    🔗 Obtener IOCs vinculados a una investigación
    
    Retorna todos los IOCs asociados a esta investigación
    con información del vínculo (razón, relevancia, fecha).
    """
    try:
        # Obtener links
        links = db.query(InvestigationIocLink).filter(
            InvestigationIocLink.investigation_id == inv_id
        ).all()
        
        iocs_data = []
        for link in links:
            if link.ioc:
                ioc_dict = link.ioc.to_dict()
                ioc_dict["link_info"] = {
                    "reason": link.reason,
                    "relevance": link.relevance,
                    "linked_by": link.linked_by,
                    "linked_at": link.created_at.isoformat() if link.created_at else None
                }
                iocs_data.append(ioc_dict)
        
        return {
            "investigation_id": inv_id,
            "iocs": iocs_data,
            "total": len(iocs_data)
        }
    
    except Exception as e:
        logger.error(f"❌ Error obteniendo IOCs de investigación {inv_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{inv_id}/iocs/{ioc_id}", status_code=201)
async def link_ioc_to_investigation(
    inv_id: str,
    ioc_id: str,
    link_data: LinkIocRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    🔗 Vincular un IOC a una investigación
    
    Crea un enlace entre un IOC existente y una investigación,
    incluyendo contexto y razón del vínculo.
    """
    try:
        # Verificar que el IOC existe
        ioc = db.query(IocItem).filter(IocItem.id == ioc_id).first()
        if not ioc:
            raise HTTPException(status_code=404, detail=f"IOC {ioc_id} no encontrado")
        
        # Verificar si ya existe el link
        existing = db.query(InvestigationIocLink).filter(
            InvestigationIocLink.investigation_id == inv_id,
            InvestigationIocLink.ioc_id == ioc_id
        ).first()
        
        if existing:
            raise HTTPException(status_code=409, detail="IOC ya está vinculado a esta investigación")
        
        # Crear link
        link = InvestigationIocLink(
            investigation_id=inv_id,
            ioc_id=ioc_id,
            reason=link_data.reason,
            context=link_data.context,
            relevance=link_data.relevance,
            linked_by="analyst"  # TODO: obtener de auth
        )
        db.add(link)
        
        # Agregar evento a timeline
        timeline_event = InvestigationTimeline(
            investigation_id=inv_id,
            event_type="ioc_added",
            title=f"IOC vinculado: {ioc.value[:50]}",
            description=link_data.reason or f"Se vinculó IOC tipo {ioc.ioc_type}",
            source="IOC Store",
            ioc_id=ioc_id
        )
        db.add(timeline_event)
        
        db.commit()
        
        # Notificar por WebSocket
        link_info = {
            "investigation_id": inv_id,
            "ioc_id": ioc_id,
            "ioc": ioc.to_dict(),
            "reason": link_data.reason,
            "relevance": link_data.relevance
        }
        background_tasks.add_task(notify_ioc_linked, inv_id, ioc_id, link_info)
        
        logger.info(f"🔗 IOC {ioc_id} vinculado a investigación {inv_id}")
        
        return {
            "status": "linked",
            "investigation_id": inv_id,
            "ioc_id": ioc_id,
            "link_id": link.id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error vinculando IOC: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{inv_id}/iocs/{ioc_id}", status_code=204)
async def unlink_ioc_from_investigation(
    inv_id: str,
    ioc_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    🔗 Desvincular un IOC de una investigación
    """
    try:
        # Buscar y eliminar link
        link = db.query(InvestigationIocLink).filter(
            InvestigationIocLink.investigation_id == inv_id,
            InvestigationIocLink.ioc_id == ioc_id
        ).first()
        
        if not link:
            raise HTTPException(status_code=404, detail="Vínculo no encontrado")
        
        db.delete(link)
        
        # Agregar evento a timeline
        timeline_event = InvestigationTimeline(
            investigation_id=inv_id,
            event_type="ioc_removed",
            title=f"IOC desvinculado: {ioc_id}",
            description="IOC removido de la investigación",
            source="IOC Store",
            ioc_id=ioc_id
        )
        db.add(timeline_event)
        
        db.commit()
        
        # Notificar por WebSocket
        background_tasks.add_task(notify_ioc_unlinked, inv_id, ioc_id)
        
        logger.info(f"🔗 IOC {ioc_id} desvinculado de investigación {inv_id}")
        
        return None
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error desvinculando IOC: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{inv_id}/timeline-db")
async def get_investigation_timeline_db(
    inv_id: str,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    📋 Obtener timeline de una investigación (desde BD)
    """
    try:
        events = db.query(InvestigationTimeline).filter(
            InvestigationTimeline.investigation_id == inv_id
        ).order_by(InvestigationTimeline.timestamp.desc()).limit(limit).all()
        
        return {
            "investigation_id": inv_id,
            "events": [e.to_dict() for e in events],
            "total": len(events)
        }
    
    except Exception as e:
        logger.error(f"❌ Error obteniendo timeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{inv_id}/timeline-db")
async def add_timeline_event(
    inv_id: str,
    event_type: str,
    title: str,
    description: Optional[str] = None,
    source: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    📋 Agregar evento al timeline de una investigación
    """
    try:
        event = InvestigationTimeline(
            investigation_id=inv_id,
            event_type=event_type,
            title=title,
            description=description,
            source=source or "manual"
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        
        logger.info(f"📋 Evento agregado a timeline de {inv_id}: {title}")
        
        return event.to_dict()
    
    except Exception as e:
        logger.error(f"❌ Error agregando evento: {e}")
        raise HTTPException(status_code=500, detail=str(e))
