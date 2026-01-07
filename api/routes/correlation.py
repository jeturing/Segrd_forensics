"""
MCP v4.1 - Correlation Routes
Rutas API para el motor de correlación (Sigma + Heuristics).
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
import logging

from api.middleware.auth import verify_api_key
from api.database import get_db_context
from api.models.tools import (
    CorrelationRule, CorrelationEvent
)
from api.services.correlation_engine import correlation_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v41/correlation", tags=["Correlation v4.1"])


# =============================================================================
# SCHEMAS
# =============================================================================

class IngestEventRequest(BaseModel):
    """Request para ingestar evento"""
    event: Dict[str, Any] = Field(..., description="Evento a procesar")
    source: str = Field(default="api", description="Fuente del evento")
    case_id: Optional[str] = Field(None, description="Caso asociado")
    
    class Config:
        json_schema_extra = {
            "example": {
                "event": {
                    "event_type": "process_creation",
                    "Image": "C:\\Windows\\System32\\powershell.exe",
                    "CommandLine": "powershell -enc SGVsbG8gV29ybGQ=",
                    "User": "DOMAIN\\user",
                    "hostname": "WORKSTATION01"
                },
                "source": "sysmon",
                "case_id": "CASE-001"
            }
        }


class IngestBatchRequest(BaseModel):
    """Request para ingestar batch de eventos"""
    events: List[Dict[str, Any]]
    source: str = "api"
    case_id: Optional[str] = None


class CreateRuleRequest(BaseModel):
    """Request para crear regla de correlación"""
    name: str
    description: str
    rule_type: str = Field(..., description="sigma o heuristic")
    severity: str = Field(default="medium")
    logsource: Optional[Dict] = None
    detection: Dict = Field(..., description="Lógica de detección")
    mitre_tactics: List[str] = []
    mitre_techniques: List[str] = []
    tags: List[str] = []


class AlertUpdateRequest(BaseModel):
    """Request para actualizar alerta"""
    status: str = Field(..., description="new, investigating, resolved, false_positive")
    notes: Optional[str] = None


# =============================================================================
# INITIALIZATION
# =============================================================================

@router.on_event("startup")
async def startup():
    """Inicializa el motor de correlación"""
    await correlation_engine.initialize()


@router.post("/initialize", summary="Inicializar motor")
async def initialize_engine(
    _: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Inicializa/reinicializa el motor de correlación.
    Carga reglas builtin a la BD.
    """
    await correlation_engine.initialize()
    
    rules = correlation_engine.get_rules()
    
    return {
        "success": True,
        "sigma_rules_loaded": len([r for r in rules if r["type"] == "sigma"]),
        "heuristics_loaded": len([r for r in rules if r["type"] == "heuristic"])
    }


# =============================================================================
# EVENT INGESTION
# =============================================================================

@router.post("/ingest", summary="Ingestar evento")
async def ingest_event(
    request: IngestEventRequest,
    _: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Ingesta un evento y ejecuta correlación.
    Retorna alertas generadas si hay matches.
    """
    alerts = await correlation_engine.ingest_event(
        event=request.event,
        source=request.source,
        case_id=request.case_id
    )
    
    return {
        "processed": True,
        "alerts_generated": len(alerts),
        "alerts": alerts
    }


@router.post("/ingest/batch", summary="Ingestar batch")
async def ingest_batch(
    request: IngestBatchRequest,
    _: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Ingesta batch de eventos.
    """
    result = await correlation_engine.ingest_batch(
        events=request.events,
        source=request.source,
        case_id=request.case_id
    )
    
    return result


# =============================================================================
# RULES MANAGEMENT
# =============================================================================

@router.get("/rules", summary="Listar reglas")
async def list_rules(
    rule_type: Optional[str] = Query(None, description="sigma o heuristic"),
    is_enabled: bool = Query(True),
    _: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Lista reglas de correlación.
    """
    rules = correlation_engine.get_rules(
        rule_type=rule_type,
        is_enabled=is_enabled
    )
    
    # Agrupar por tipo
    by_type = {"sigma": [], "heuristic": []}
    for r in rules:
        t = r.get("type", "sigma")
        if t in by_type:
            by_type[t].append(r)
    
    return {
        "total": len(rules),
        "by_type": {k: len(v) for k, v in by_type.items()},
        "rules": rules
    }


@router.get("/rules/{rule_id}", summary="Obtener regla")
async def get_rule(
    rule_id: str,
    _: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Obtiene detalles de una regla.
    """
    with get_db_context() as db:
        rule = db.query(CorrelationRule).filter(
            CorrelationRule.id == rule_id
        ).first()
        
        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found")
    
    return {
        "id": rule.id,
        "name": rule.name,
        "description": rule.description,
        "rule_type": rule.rule_type,
        "severity": rule.severity,
        "logsource": rule.logsource,
        "detection": rule.detection,
        "mitre_tactics": rule.mitre_tactics,
        "mitre_techniques": rule.mitre_techniques,
        "tags": rule.tags,
        "is_enabled": rule.is_enabled,
        "is_builtin": rule.is_builtin,
        "match_count": rule.match_count,
        "last_match_at": rule.last_match_at.isoformat() if rule.last_match_at else None,
        "created_at": rule.created_at.isoformat()
    }


@router.post("/rules", summary="Crear regla")
async def create_rule(
    request: CreateRuleRequest,
    user_id: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Crea una regla de correlación personalizada.
    """
    import uuid
    
    rule_type = request.rule_type.lower()
    if rule_type not in ["sigma", "heuristic"]:
        raise HTTPException(
            status_code=400,
            detail="rule_type must be 'sigma' or 'heuristic'"
        )
    
    prefix = "SIGMA" if rule_type == "sigma" else "HEUR"
    rule_id = f"{prefix}-CUSTOM-{uuid.uuid4().hex[:6].upper()}"
    
    with get_db_context() as db:
        rule = CorrelationRule(
            id=rule_id,
            name=request.name,
            description=request.description,
            rule_type=rule_type,
            severity=request.severity,
            logsource=request.logsource,
            detection=request.detection,
            mitre_tactics=request.mitre_tactics,
            mitre_techniques=request.mitre_techniques,
            tags=request.tags,
            is_enabled=True,
            is_builtin=False,
            created_by=user_id
        )
        db.add(rule)
        db.commit()
    
    # Recargar cache
    await correlation_engine._load_rules_to_cache()
    
    logger.info(f"📜 Created custom rule: {rule_id}")
    
    return {
        "id": rule_id,
        "name": request.name,
        "message": "Rule created and enabled"
    }


@router.patch("/rules/{rule_id}/enable", summary="Habilitar regla")
async def enable_rule(
    rule_id: str,
    _: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Habilita una regla.
    """
    success = await correlation_engine.toggle_rule(rule_id, enabled=True)
    
    if success:
        return {"success": True, "is_enabled": True}
    else:
        raise HTTPException(status_code=404, detail="Rule not found")


@router.patch("/rules/{rule_id}/disable", summary="Deshabilitar regla")
async def disable_rule(
    rule_id: str,
    _: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Deshabilita una regla.
    """
    success = await correlation_engine.toggle_rule(rule_id, enabled=False)
    
    if success:
        return {"success": True, "is_enabled": False}
    else:
        raise HTTPException(status_code=404, detail="Rule not found")


@router.delete("/rules/{rule_id}", summary="Eliminar regla")
async def delete_rule(
    rule_id: str,
    _: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Elimina una regla (solo custom).
    """
    with get_db_context() as db:
        rule = db.query(CorrelationRule).filter(
            CorrelationRule.id == rule_id
        ).first()
        
        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        if rule.is_builtin:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete builtin rules"
            )
        
        db.delete(rule)
        db.commit()
    
    await correlation_engine._load_rules_to_cache()
    
    return {"success": True, "message": "Rule deleted"}


# =============================================================================
# ALERTS
# =============================================================================

@router.get("/alerts", summary="Listar alertas")
async def list_alerts(
    case_id: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    _: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Lista alertas de correlación.
    """
    alerts = correlation_engine.get_alerts(
        case_id=case_id,
        severity=severity,
        status=status,
        limit=limit
    )
    
    # Agrupar por severidad
    by_severity = {}
    for a in alerts:
        s = a.get("severity", "medium")
        by_severity[s] = by_severity.get(s, 0) + 1
    
    return {
        "total": len(alerts),
        "by_severity": by_severity,
        "alerts": alerts
    }


@router.get("/alerts/{alert_id}", summary="Obtener alerta")
async def get_alert(
    alert_id: str,
    _: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Obtiene detalles de una alerta (usando CorrelationEvent como modelo).
    """
    with get_db_context() as db:
        # CorrelationEvent sirve como modelo de alertas
        alert = db.query(CorrelationEvent).filter(
            CorrelationEvent.id == alert_id
        ).first()
        
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        # Obtener regla asociada
        rule = db.query(CorrelationRule).filter(
            CorrelationRule.id == alert.rule_id
        ).first()
    
        return {
            "id": alert.id,
            "rule_id": alert.rule_id,
            "rule_name": rule.name if rule else None,
            "severity": alert.severity,
            "title": alert.title,
            "description": alert.description,
            "matched_data": alert.matched_data,
            "status": alert.status,
            "case_id": alert.case_id,
            "confidence": alert.confidence,
            "source_type": alert.source_type,
            "related_iocs": alert.related_iocs or [],
            "detected_at": alert.detected_at.isoformat() if alert.detected_at else None,
            "created_at": alert.created_at.isoformat() if alert.created_at else None,
            "resolution_notes": alert.resolution_notes
        }


@router.patch("/alerts/{alert_id}", summary="Actualizar alerta")
async def update_alert(
    alert_id: str,
    request: AlertUpdateRequest,
    user_id: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Actualiza estado de una alerta.
    """
    valid_statuses = ["new", "investigating", "resolved", "false_positive"]
    if request.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {valid_statuses}"
        )
    
    with get_db_context() as db:
        alert = db.query(CorrelationEvent).filter(
            CorrelationEvent.id == alert_id
        ).first()
        
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        alert.status = request.status
        if request.notes:
            alert.resolution_notes = request.notes
        if request.status == "resolved":
            alert.resolved_at = datetime.utcnow()
        alert.assigned_to = user_id
        
        db.commit()
    
    return {
        "success": True,
        "alert_id": alert_id,
        "status": request.status
    }


@router.post("/alerts/{alert_id}/escalate", summary="Escalar alerta")
async def escalate_alert(
    alert_id: str,
    case_id: str = Query(..., description="ID del caso al que escalar"),
    _: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Escala una alerta a un caso.
    """
    with get_db_context() as db:
        alert = db.query(CorrelationEvent).filter(
            CorrelationEvent.id == alert_id
        ).first()
        
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        alert.case_id = case_id
        alert.status = "investigating"
        
        db.commit()
    
    return {
        "success": True,
        "alert_id": alert_id,
        "case_id": case_id
    }


# =============================================================================
# EVENTS
# =============================================================================

@router.get("/events", summary="Listar eventos")
async def list_events(
    case_id: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    _: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Lista eventos ingestados.
    """
    with get_db_context() as db:
        query = db.query(CorrelationEvent)
        
        if case_id:
            query = query.filter(CorrelationEvent.case_id == case_id)
        if event_type:
            query = query.filter(CorrelationEvent.event_type == event_type)
        if source:
            query = query.filter(CorrelationEvent.source == source)
        
        events = query.order_by(
            CorrelationEvent.timestamp.desc()
        ).limit(limit).all()
    
    return {
        "total": len(events),
        "events": [
            {
                "id": e.id,
                "timestamp": e.timestamp.isoformat(),
                "source": e.source,
                "event_type": e.event_type,
                "severity": e.severity,
                "host_name": e.host_name,
                "user_name": e.user_name,
                "process_name": e.process_name
            }
            for e in events
        ]
    }


# =============================================================================
# STATS
# =============================================================================

@router.get("/stats", summary="Estadísticas de correlación")
async def get_correlation_stats(
    days: int = Query(7, le=30),
    _: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Obtiene estadísticas del motor de correlación.
    """
    from datetime import timedelta
    
    with get_db_context() as db:
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # Contar eventos/alertas (CorrelationEvent sirve como alertas)
        alerts = db.query(CorrelationEvent).filter(
            CorrelationEvent.detected_at >= cutoff
        ).all()
        
        total_events = len(alerts)
        
        # Reglas con más matches
        rules = db.query(CorrelationRule).order_by(
            CorrelationRule.match_count.desc()
        ).limit(10).all()
        
        # Por severidad
        by_severity = {}
        for a in alerts:
            sev = a.severity or "medium"
            by_severity[sev] = by_severity.get(sev, 0) + 1
        
        # Por status
        by_status = {}
        for a in alerts:
            st = a.status or "new"
            by_status[st] = by_status.get(st, 0) + 1
    
    return {
        "period_days": days,
        "total_events_processed": total_events,
        "total_alerts": len(alerts),
        "by_severity": by_severity,
        "by_status": by_status,
        "top_rules": [
            {
                "id": r.id,
                "name": r.name,
                "match_count": r.match_count or 0
            }
            for r in rules
        ]
    }
