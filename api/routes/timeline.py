"""
Timeline Routes
===============
Endpoints para gestionar eventos de timeline forense
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from api.services.timeline import timeline_service

router = APIRouter(tags=["timeline"])


# ==================== ENUMS ====================

class EventType(str, Enum):
    AUTHENTICATION = "authentication"
    FILE_ACCESS = "file_access"
    EMAIL = "email"
    NETWORK = "network"
    PROCESS = "process"
    REGISTRY = "registry"
    LATERAL_MOVEMENT = "lateral_movement"
    DATA_EXFIL = "data_exfiltration"
    PERSISTENCE = "persistence"
    INDICATOR = "indicator"
    CUSTOM = "custom"


class EventSource(str, Enum):
    M365_AUDIT = "m365_audit"
    AZURE_AD = "azure_ad"
    ENDPOINT_LOKI = "endpoint_loki"
    ENDPOINT_YARA = "endpoint_yara"
    ENDPOINT_OSQUERY = "endpoint_osquery"
    MEMORY_VOLATILITY = "memory_volatility"
    NETWORK_PCAP = "network_pcap"
    THREAT_INTEL = "threat_intel"
    MANUAL = "manual"


class Severity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ==================== REQUEST MODELS ====================

class AddEventRequest(BaseModel):
    """Request para agregar evento a timeline"""
    case_id: str = Field(..., description="ID del caso")
    event_time: datetime = Field(..., description="Timestamp del evento")
    event_type: EventType
    source: EventSource
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    severity: Severity = Severity.INFO
    entities: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Entidades relacionadas (users, IPs, files)")
    indicators: Optional[List[str]] = Field(default_factory=list, description="IOCs asociados")
    raw_data: Optional[Dict[str, Any]] = None
    correlation_ids: Optional[List[str]] = Field(default_factory=list, description="IDs para correlación")


class BulkAddEventsRequest(BaseModel):
    """Request para agregar múltiples eventos"""
    case_id: str
    events: List[AddEventRequest]


class UpdateEventRequest(BaseModel):
    """Request para actualizar evento"""
    title: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[Severity] = None
    entities: Optional[Dict[str, Any]] = None
    indicators: Optional[List[str]] = None
    correlation_ids: Optional[List[str]] = None
    is_key_event: Optional[bool] = None


class CorrelateEventsRequest(BaseModel):
    """Request para correlacionar eventos"""
    case_id: str
    event_ids: List[str] = Field(..., min_items=2)
    correlation_name: str = Field(..., min_length=3)
    correlation_type: str = Field("manual", description="Tipo: manual, temporal, entity, indicator")


# ==================== RESPONSE MODELS ====================

class TimelineEventResponse(BaseModel):
    """Respuesta de evento de timeline"""
    event_id: str
    case_id: str
    event_time: datetime
    event_type: str
    source: str
    title: str
    description: Optional[str]
    severity: str
    entities: Dict[str, Any]
    indicators: List[str]
    correlation_ids: List[str]
    is_key_event: bool
    created_at: datetime


# ==================== ENDPOINTS ====================

@router.get("/")
async def get_timeline_status():
    """Estado del servicio de timeline"""
    stats = await timeline_service.get_stats()
    return {
        "service": "timeline",
        "status": "operational",
        "event_types": [e.value for e in EventType],
        "sources": [s.value for s in EventSource],
        "statistics": stats
    }


@router.get("/{case_id}")
async def get_case_timeline(
    case_id: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    event_types: Optional[List[EventType]] = Query(None),
    sources: Optional[List[EventSource]] = Query(None),
    severity: Optional[Severity] = None,
    key_events_only: bool = False,
    limit: int = Query(500, ge=1, le=5000),
    offset: int = Query(0, ge=0)
):
    """
    Obtener timeline completo de un caso
    
    Soporta filtros por:
    - Rango de tiempo
    - Tipo de evento
    - Fuente del evento
    - Severidad
    - Solo eventos clave
    """
    filters = {
        "start_time": start_time,
        "end_time": end_time,
        "event_types": [e.value for e in event_types] if event_types else None,
        "sources": [s.value for s in sources] if sources else None,
        "severity": severity.value if severity else None,
        "key_events_only": key_events_only
    }
    
    timeline = await timeline_service.get_timeline(
        case_id=case_id,
        filters=filters,
        limit=limit,
        offset=offset
    )
    
    return {
        "case_id": case_id,
        "total_events": timeline["total"],
        "returned_events": len(timeline["events"]),
        "has_more": timeline["total"] > offset + len(timeline["events"]),
        "filters_applied": {k: v for k, v in filters.items() if v is not None},
        "events": timeline["events"]
    }


@router.post("/events")
async def add_timeline_event(request: AddEventRequest):
    """
    Agregar un evento al timeline
    """
    event = await timeline_service.add_event(
        case_id=request.case_id,
        event_time=request.event_time,
        event_type=request.event_type.value,
        source=request.source.value,
        title=request.title,
        description=request.description,
        severity=request.severity.value,
        entities=request.entities,
        indicators=request.indicators,
        raw_data=request.raw_data,
        correlation_ids=request.correlation_ids
    )
    
    return {
        "created": True,
        "event_id": event["event_id"],
        "case_id": request.case_id,
        "event_time": request.event_time.isoformat()
    }


@router.post("/events/bulk")
async def bulk_add_events(request: BulkAddEventsRequest):
    """
    Agregar múltiples eventos al timeline
    
    Útil para importar eventos de herramientas forenses
    """
    results = await timeline_service.bulk_add_events(
        case_id=request.case_id,
        events=[{
            "event_time": e.event_time,
            "event_type": e.event_type.value,
            "source": e.source.value,
            "title": e.title,
            "description": e.description,
            "severity": e.severity.value,
            "entities": e.entities,
            "indicators": e.indicators,
            "raw_data": e.raw_data,
            "correlation_ids": e.correlation_ids
        } for e in request.events]
    )
    
    return {
        "case_id": request.case_id,
        "events_added": results["added"],
        "events_failed": results["failed"],
        "event_ids": results["event_ids"]
    }


@router.get("/events/{event_id}")
async def get_event(event_id: str):
    """Obtener detalles de un evento específico"""
    event = await timeline_service.get_event(event_id)
    
    if not event:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    
    return event


@router.put("/events/{event_id}")
async def update_event(event_id: str, request: UpdateEventRequest):
    """Actualizar un evento existente"""
    updates = request.dict(exclude_unset=True, exclude_none=True)
    
    if not updates:
        raise HTTPException(status_code=400, detail="No hay campos para actualizar")
    
    # Convertir enums a strings
    if "severity" in updates:
        updates["severity"] = updates["severity"].value
    
    updated = await timeline_service.update_event(event_id, updates)
    
    if not updated:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    
    return {"updated": True, "event_id": event_id}


@router.delete("/events/{event_id}")
async def delete_event(event_id: str):
    """Eliminar un evento del timeline"""
    deleted = await timeline_service.delete_event(event_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    
    return {"deleted": True, "event_id": event_id}


@router.post("/events/{event_id}/key")
async def mark_as_key_event(event_id: str, is_key: bool = True):
    """Marcar/desmarcar un evento como evento clave"""
    updated = await timeline_service.update_event(
        event_id, 
        {"is_key_event": is_key}
    )
    
    if not updated:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    
    return {
        "event_id": event_id,
        "is_key_event": is_key
    }


@router.post("/correlate")
async def correlate_events(request: CorrelateEventsRequest):
    """
    Correlacionar múltiples eventos
    
    Tipos de correlación:
    - manual: Correlación manual por analista
    - temporal: Eventos cercanos en tiempo
    - entity: Comparten entidad (usuario, IP, etc)
    - indicator: Comparten IOC
    """
    correlation = await timeline_service.correlate_events(
        case_id=request.case_id,
        event_ids=request.event_ids,
        correlation_name=request.correlation_name,
        correlation_type=request.correlation_type
    )
    
    return {
        "correlation_id": correlation["id"],
        "case_id": request.case_id,
        "events_correlated": len(request.event_ids),
        "correlation_name": request.correlation_name,
        "correlation_type": request.correlation_type
    }


@router.get("/{case_id}/correlations")
async def get_correlations(case_id: str):
    """Obtener todas las correlaciones de un caso"""
    correlations = await timeline_service.get_correlations(case_id)
    
    return {
        "case_id": case_id,
        "total_correlations": len(correlations),
        "correlations": correlations
    }


@router.get("/{case_id}/summary")
async def get_timeline_summary(case_id: str):
    """
    Obtener resumen del timeline de un caso
    
    Incluye:
    - Estadísticas por tipo de evento
    - Eventos clave
    - Rango de tiempo
    - Entidades más frecuentes
    """
    summary = await timeline_service.get_summary(case_id)
    
    return {
        "case_id": case_id,
        **summary
    }


@router.get("/{case_id}/graph")
async def get_timeline_graph(
    case_id: str,
    resolution: str = Query("hour", pattern="^(minute|hour|day)$")
):
    """
    Obtener datos para gráfico de timeline
    
    Resolución:
    - minute: Granularidad por minuto (últimas 24h)
    - hour: Granularidad por hora (últimos 7 días)
    - day: Granularidad por día (últimos 30 días)
    """
    graph_data = await timeline_service.get_graph_data(
        case_id=case_id,
        resolution=resolution
    )
    
    return {
        "case_id": case_id,
        "resolution": resolution,
        "data_points": graph_data["data_points"],
        "series": graph_data["series"]
    }


@router.post("/{case_id}/import/{source}")
async def import_from_source(
    case_id: str,
    source: EventSource,
    data: Dict[str, Any]
):
    """
    Importar eventos desde una fuente específica
    
    El formato de data varía según la fuente:
    - m365_audit: {"audit_logs": [...]}
    - endpoint_loki: {"loki_output": "..."}
    - endpoint_yara: {"yara_matches": [...]}
    """
    imported = await timeline_service.import_from_source(
        case_id=case_id,
        source=source.value,
        data=data
    )
    
    return {
        "case_id": case_id,
        "source": source.value,
        "events_imported": imported["count"],
        "event_ids": imported["event_ids"]
    }


@router.get("/{case_id}/export")
async def export_timeline(
    case_id: str,
    format: str = Query("json", pattern="^(json|csv|html)$")
):
    """
    Exportar timeline en diferentes formatos
    """
    export_data = await timeline_service.export_timeline(
        case_id=case_id,
        format=format
    )
    
    return {
        "case_id": case_id,
        "format": format,
        "export_path": export_data.get("path"),
        "download_url": export_data.get("url")
    }
