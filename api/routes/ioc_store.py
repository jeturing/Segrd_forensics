"""
IOC Store Router v3 - Gestión centralizada de Indicadores de Compromiso
Con persistencia real en BD SQLAlchemy y notificaciones WebSocket
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
import json
import csv
import io
import logging

from api.database import get_db
from api.models.ioc import IocItem, IocTag, IocItemTag, IocEnrichment, IocSighting
from api.services.websocket_manager import (
    notify_ioc_created,
    notify_ioc_updated,
    notify_ioc_deleted,
    notify_ioc_enriched,
    notify_import_completed
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/iocs", tags=["IOC Store"])


# ============================================================================
# ENUMS Y MODELOS PYDANTIC
# ============================================================================

class IOCType(str, Enum):
    IP = "ip"
    DOMAIN = "domain"
    URL = "url"
    EMAIL = "email"
    HASH_MD5 = "hash_md5"
    HASH_SHA1 = "hash_sha1"
    HASH_SHA256 = "hash_sha256"
    FILE_NAME = "file_name"
    FILE_PATH = "file_path"
    REGISTRY_KEY = "registry_key"
    PROCESS_NAME = "process_name"
    USER_ACCOUNT = "user_account"
    YARA_RULE = "yara_rule"
    CVE = "cve"
    MUTEX = "mutex"
    USER_AGENT = "user_agent"


class ThreatLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class IOCStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    WHITELISTED = "whitelisted"
    FALSE_POSITIVE = "false_positive"
    UNDER_REVIEW = "under_review"


class IOCSource(str, Enum):
    MANUAL = "manual"
    INVESTIGATION = "investigation"
    THREAT_INTEL = "threat_intel"
    HIBP = "hibp"
    VIRUSTOTAL = "virustotal"
    ABUSEIPDB = "abuseipdb"
    OSINT = "osint"
    IMPORT = "import"
    MISP = "misp"
    STIX = "stix"


class IOCCreate(BaseModel):
    value: str = Field(..., min_length=1, max_length=2000)
    ioc_type: IOCType
    threat_level: ThreatLevel = ThreatLevel.MEDIUM
    source: IOCSource = IOCSource.MANUAL
    case_id: Optional[str] = None
    description: Optional[str] = None
    context: Optional[str] = None
    tags: List[str] = []
    ttl_days: Optional[int] = Field(None, ge=1, le=365)


class IOCUpdate(BaseModel):
    threat_level: Optional[ThreatLevel] = None
    status: Optional[IOCStatus] = None
    description: Optional[str] = None
    context: Optional[str] = None
    tags: Optional[List[str]] = None
    ttl_days: Optional[int] = None
    confidence_score: Optional[float] = Field(None, ge=0, le=100)


class IOCResponse(BaseModel):
    id: str
    value: str
    ioc_type: str
    threat_level: str
    confidence_score: float
    status: str
    source: str
    description: Optional[str]
    case_id: Optional[str]
    first_seen: Optional[str]
    last_seen: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]
    hit_count: int
    tags: List[str]
    enrichment: Dict[str, Any]

    class Config:
        from_attributes = True


class IOCListResponse(BaseModel):
    items: List[IOCResponse]
    total: int
    page: int
    limit: int
    pages: int


class IOCBulkCreate(BaseModel):
    iocs: List[IOCCreate]


class IOCSearchQuery(BaseModel):
    query: Optional[str] = None
    ioc_types: Optional[List[IOCType]] = None
    threat_levels: Optional[List[ThreatLevel]] = None
    sources: Optional[List[IOCSource]] = None
    statuses: Optional[List[IOCStatus]] = None
    tags: Optional[List[str]] = None
    case_id: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    min_confidence: Optional[float] = None


class MISPImport(BaseModel):
    misp_json: Dict[str, Any]
    default_threat_level: ThreatLevel = ThreatLevel.MEDIUM


class STIXImport(BaseModel):
    stix_json: Dict[str, Any]
    default_threat_level: ThreatLevel = ThreatLevel.MEDIUM


class LinkToCaseRequest(BaseModel):
    case_id: str
    reason: Optional[str] = None


# ============================================================================
# HELPERS
# ============================================================================

def get_or_create_tag(db: Session, tag_name: str) -> IocTag:
    """Obtiene o crea un tag"""
    tag = db.query(IocTag).filter(IocTag.name == tag_name.lower()).first()
    if not tag:
        tag = IocTag(name=tag_name.lower())
        db.add(tag)
        db.flush()
    return tag


def ioc_to_response(ioc: IocItem) -> Dict:
    """Convierte un IOC de BD a formato de respuesta"""
    return {
        "id": ioc.id,
        "value": ioc.value,
        "ioc_type": ioc.ioc_type,
        "threat_level": ioc.threat_level,
        "confidence_score": ioc.confidence_score or 50.0,
        "status": ioc.status,
        "source": ioc.source,
        "description": ioc.description,
        "case_id": ioc.case_id,
        "first_seen": ioc.first_seen.isoformat() if ioc.first_seen else None,
        "last_seen": ioc.last_seen.isoformat() if ioc.last_seen else None,
        "created_at": ioc.created_at.isoformat() if ioc.created_at else None,
        "updated_at": ioc.updated_at.isoformat() if ioc.updated_at else None,
        "hit_count": ioc.hit_count or 0,
        "tags": [it.tag.name for it in ioc.tags] if ioc.tags else [],
        "enrichment": ioc.enrichment_data or {}
    }


# ============================================================================
# CRUD ENDPOINTS
# ============================================================================

@router.get("/", response_model=IOCListResponse)
async def list_iocs(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    ioc_type: Optional[str] = None,
    threat_level: Optional[str] = None,
    status: Optional[str] = None,
    source: Optional[str] = None,
    case_id: Optional[str] = None,
    tags: Optional[List[str]] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Lista IOCs con paginación y filtros.
    """
    query = db.query(IocItem)
    
    # Aplicar filtros
    if search:
        query = query.filter(
            or_(
                IocItem.value.ilike(f"%{search}%"),
                IocItem.description.ilike(f"%{search}%")
            )
        )
    
    if ioc_type:
        query = query.filter(IocItem.ioc_type == ioc_type)
    
    if threat_level:
        query = query.filter(IocItem.threat_level == threat_level)
    
    if status:
        query = query.filter(IocItem.status == status)
    
    if source:
        query = query.filter(IocItem.source == source)
    
    if case_id:
        query = query.filter(IocItem.case_id == case_id)
    
    if tags:
        # Filtrar por tags (IOC debe tener al menos uno de los tags)
        query = query.join(IocItemTag).join(IocTag).filter(IocTag.name.in_(tags))
    
    # Contar total
    total = query.count()
    
    # Paginación
    offset = (page - 1) * limit
    iocs = query.order_by(IocItem.created_at.desc()).offset(offset).limit(limit).all()
    
    pages = (total + limit - 1) // limit
    
    return {
        "items": [ioc_to_response(ioc) for ioc in iocs],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": pages
    }


@router.post("/", response_model=IOCResponse, status_code=201)
async def create_ioc(
    ioc_data: IOCCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Crea un nuevo IOC.
    """
    # Verificar si ya existe
    existing = db.query(IocItem).filter(
        and_(IocItem.value == ioc_data.value, IocItem.ioc_type == ioc_data.ioc_type.value)
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"IOC ya existe con ID: {existing.id}"
        )
    
    # Crear IOC
    expires_at = None
    if ioc_data.ttl_days:
        expires_at = datetime.utcnow() + timedelta(days=ioc_data.ttl_days)
    
    ioc = IocItem(
        value=ioc_data.value,
        ioc_type=ioc_data.ioc_type.value,
        threat_level=ioc_data.threat_level.value,
        source=ioc_data.source.value,
        case_id=ioc_data.case_id,
        description=ioc_data.description,
        context=ioc_data.context,
        expires_at=expires_at,
        confidence_score=50.0
    )
    
    db.add(ioc)
    db.flush()
    
    # Agregar tags
    for tag_name in ioc_data.tags:
        tag = get_or_create_tag(db, tag_name)
        ioc_tag = IocItemTag(ioc_id=ioc.id, tag_id=tag.id)
        db.add(ioc_tag)
    
    db.commit()
    db.refresh(ioc)
    
    response = ioc_to_response(ioc)
    
    # Notificar por WebSocket
    background_tasks.add_task(notify_ioc_created, response)
    
    logger.info(f"✅ IOC creado: {ioc.id} ({ioc.ioc_type}: {ioc.value[:50]}...)")
    
    return response


# ==================== RUTAS ESTÁTICAS (DEBEN ir ANTES de /{ioc_id}) ====================

@router.get("/stats")
async def get_ioc_stats(db: Session = Depends(get_db)):
    """
    Obtiene estadísticas del IOC Store.
    """
    total = db.query(IocItem).count()
    
    # Por tipo
    by_type = {}
    type_counts = db.query(
        IocItem.ioc_type, func.count(IocItem.id)
    ).group_by(IocItem.ioc_type).all()
    for ioc_type, count in type_counts:
        by_type[ioc_type] = count
    
    # Por nivel de amenaza
    by_threat_level = {}
    threat_counts = db.query(
        IocItem.threat_level, func.count(IocItem.id)
    ).group_by(IocItem.threat_level).all()
    for level, count in threat_counts:
        by_threat_level[level] = count
    
    # Por fuente
    by_source = {}
    source_counts = db.query(
        IocItem.source, func.count(IocItem.id)
    ).group_by(IocItem.source).all()
    for source, count in source_counts:
        by_source[source] = count
    
    # Por estado
    by_status = {}
    status_counts = db.query(
        IocItem.status, func.count(IocItem.id)
    ).group_by(IocItem.status).all()
    for status, count in status_counts:
        by_status[status] = count
    
    # Promedio de confianza
    avg_confidence = db.query(func.avg(IocItem.confidence_score)).scalar() or 0
    
    # Top tags
    top_tags = {}
    tag_counts = db.query(
        IocTag.name, func.count(IocItemTag.id)
    ).join(IocItemTag).group_by(IocTag.name).order_by(func.count(IocItemTag.id).desc()).limit(10).all()
    for tag_name, count in tag_counts:
        top_tags[tag_name] = count
    
    # IOCs recientes (últimas 24h)
    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_count = db.query(IocItem).filter(IocItem.created_at >= yesterday).count()
    
    return {
        "total": total,
        "by_type": by_type,
        "by_threat_level": by_threat_level,
        "by_source": by_source,
        "by_status": by_status,
        "average_confidence": round(avg_confidence, 2),
        "top_tags": top_tags,
        "recent_24h": recent_count,
        "generated_at": datetime.utcnow().isoformat()
    }


# ==================== RUTAS CON PARÁMETROS DINÁMICOS ====================

@router.get("/{ioc_id}", response_model=IOCResponse)
async def get_ioc(ioc_id: str, db: Session = Depends(get_db)):
    """
    Obtiene un IOC por ID.
    """
    ioc = db.query(IocItem).filter(IocItem.id == ioc_id).first()
    
    if not ioc:
        raise HTTPException(status_code=404, detail="IOC no encontrado")
    
    # Incrementar hit count
    ioc.hit_count = (ioc.hit_count or 0) + 1
    ioc.last_seen = datetime.utcnow()
    db.commit()
    
    return ioc_to_response(ioc)


@router.put("/{ioc_id}", response_model=IOCResponse)
async def update_ioc(
    ioc_id: str,
    updates: IOCUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Actualiza un IOC existente.
    """
    ioc = db.query(IocItem).filter(IocItem.id == ioc_id).first()
    
    if not ioc:
        raise HTTPException(status_code=404, detail="IOC no encontrado")
    
    # Aplicar actualizaciones
    if updates.threat_level is not None:
        ioc.threat_level = updates.threat_level.value
    
    if updates.status is not None:
        ioc.status = updates.status.value
    
    if updates.description is not None:
        ioc.description = updates.description
    
    if updates.context is not None:
        ioc.context = updates.context
    
    if updates.confidence_score is not None:
        ioc.confidence_score = updates.confidence_score
    
    if updates.ttl_days is not None:
        ioc.expires_at = datetime.utcnow() + timedelta(days=updates.ttl_days)
    
    # Actualizar tags si se proporcionan
    if updates.tags is not None:
        # Eliminar tags existentes
        db.query(IocItemTag).filter(IocItemTag.ioc_id == ioc_id).delete()
        
        # Agregar nuevos tags
        for tag_name in updates.tags:
            tag = get_or_create_tag(db, tag_name)
            ioc_tag = IocItemTag(ioc_id=ioc.id, tag_id=tag.id)
            db.add(ioc_tag)
    
    db.commit()
    db.refresh(ioc)
    
    response = ioc_to_response(ioc)
    
    # Notificar por WebSocket
    background_tasks.add_task(notify_ioc_updated, ioc_id, response)
    
    logger.info(f"✏️ IOC actualizado: {ioc_id}")
    
    return response


@router.delete("/{ioc_id}", status_code=204)
async def delete_ioc(
    ioc_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Elimina un IOC.
    """
    ioc = db.query(IocItem).filter(IocItem.id == ioc_id).first()
    
    if not ioc:
        raise HTTPException(status_code=404, detail="IOC no encontrado")
    
    db.delete(ioc)
    db.commit()
    
    # Notificar por WebSocket
    background_tasks.add_task(notify_ioc_deleted, ioc_id)
    
    logger.info(f"🗑️ IOC eliminado: {ioc_id}")
    
    return None


# ============================================================================
# BULK OPERATIONS
# ============================================================================

@router.post("/bulk", status_code=201)
async def bulk_create_iocs(
    bulk_data: IOCBulkCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Crea múltiples IOCs en lote.
    """
    created = []
    errors = []
    
    for ioc_data in bulk_data.iocs:
        try:
            # Verificar si ya existe
            existing = db.query(IocItem).filter(
                and_(IocItem.value == ioc_data.value, IocItem.ioc_type == ioc_data.ioc_type.value)
            ).first()
            
            if existing:
                errors.append({
                    "value": ioc_data.value,
                    "error": f"Ya existe con ID: {existing.id}"
                })
                continue
            
            expires_at = None
            if ioc_data.ttl_days:
                expires_at = datetime.utcnow() + timedelta(days=ioc_data.ttl_days)
            
            ioc = IocItem(
                value=ioc_data.value,
                ioc_type=ioc_data.ioc_type.value,
                threat_level=ioc_data.threat_level.value,
                source=ioc_data.source.value,
                case_id=ioc_data.case_id,
                description=ioc_data.description,
                expires_at=expires_at,
                confidence_score=50.0
            )
            
            db.add(ioc)
            db.flush()
            
            # Agregar tags
            for tag_name in ioc_data.tags:
                tag = get_or_create_tag(db, tag_name)
                ioc_tag = IocItemTag(ioc_id=ioc.id, tag_id=tag.id)
                db.add(ioc_tag)
            
            created.append(ioc_to_response(ioc))
            
        except Exception as e:
            errors.append({
                "value": ioc_data.value,
                "error": str(e)
            })
    
    db.commit()
    
    # Notificar por WebSocket
    if created:
        background_tasks.add_task(
            notify_import_completed,
            "bulk",
            len(created),
            {"created": len(created), "errors": len(errors)}
        )
    
    logger.info(f"📦 Bulk create: {len(created)} creados, {len(errors)} errores")
    
    return {
        "created": len(created),
        "errors": len(errors),
        "items": created,
        "error_details": errors
    }


@router.post("/bulk-delete")
async def bulk_delete_iocs(
    ioc_ids: List[str],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Elimina múltiples IOCs.
    """
    deleted_count = db.query(IocItem).filter(IocItem.id.in_(ioc_ids)).delete(synchronize_session=False)
    db.commit()
    
    # Notificar eliminaciones
    for ioc_id in ioc_ids:
        background_tasks.add_task(notify_ioc_deleted, ioc_id)
    
    logger.info(f"🗑️ Bulk delete: {deleted_count} IOCs eliminados")
    
    return {"deleted": deleted_count}


# ============================================================================
# SEARCH & ANALYTICS
# ============================================================================

@router.post("/search")
async def advanced_search(
    search_query: IOCSearchQuery,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Búsqueda avanzada de IOCs.
    """
    query = db.query(IocItem)
    
    if search_query.query:
        query = query.filter(
            or_(
                IocItem.value.ilike(f"%{search_query.query}%"),
                IocItem.description.ilike(f"%{search_query.query}%"),
                IocItem.context.ilike(f"%{search_query.query}%")
            )
        )
    
    if search_query.ioc_types:
        types = [t.value for t in search_query.ioc_types]
        query = query.filter(IocItem.ioc_type.in_(types))
    
    if search_query.threat_levels:
        levels = [l.value for l in search_query.threat_levels]
        query = query.filter(IocItem.threat_level.in_(levels))
    
    if search_query.sources:
        sources = [s.value for s in search_query.sources]
        query = query.filter(IocItem.source.in_(sources))
    
    if search_query.statuses:
        statuses = [s.value for s in search_query.statuses]
        query = query.filter(IocItem.status.in_(statuses))
    
    if search_query.case_id:
        query = query.filter(IocItem.case_id == search_query.case_id)
    
    if search_query.date_from:
        query = query.filter(IocItem.created_at >= search_query.date_from)
    
    if search_query.date_to:
        query = query.filter(IocItem.created_at <= search_query.date_to)
    
    if search_query.min_confidence:
        query = query.filter(IocItem.confidence_score >= search_query.min_confidence)
    
    if search_query.tags:
        query = query.join(IocItemTag).join(IocTag).filter(IocTag.name.in_(search_query.tags))
    
    total = query.count()
    offset = (page - 1) * limit
    iocs = query.order_by(IocItem.confidence_score.desc()).offset(offset).limit(limit).all()
    
    return {
        "items": [ioc_to_response(ioc) for ioc in iocs],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit
    }


# NOTA: El endpoint /stats fue movido antes de /{ioc_id} para evitar conflictos de rutas


@router.get("/lookup")
async def lookup_ioc(
    value: str = Query(..., min_length=1),
    db: Session = Depends(get_db)
):
    """
    Busca un IOC específico por valor exacto.
    """
    iocs = db.query(IocItem).filter(IocItem.value == value).all()
    
    if not iocs:
        return {"found": False, "value": value, "matches": []}
    
    # Incrementar hit count
    for ioc in iocs:
        ioc.hit_count = (ioc.hit_count or 0) + 1
        ioc.last_seen = datetime.utcnow()
    db.commit()
    
    return {
        "found": True,
        "value": value,
        "matches": [ioc_to_response(ioc) for ioc in iocs]
    }


# ============================================================================
# IMPORT / EXPORT
# ============================================================================

@router.post("/import/misp")
async def import_from_misp(
    misp_data: MISPImport,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Importa IOCs desde formato MISP JSON.
    """
    created = []
    errors = []
    
    try:
        event = misp_data.misp_json.get("Event", misp_data.misp_json)
        attributes = event.get("Attribute", [])
        
        type_mapping = {
            "ip-src": "ip",
            "ip-dst": "ip",
            "domain": "domain",
            "hostname": "domain",
            "url": "url",
            "email-src": "email",
            "email-dst": "email",
            "md5": "hash_md5",
            "sha1": "hash_sha1",
            "sha256": "hash_sha256",
            "filename": "file_name"
        }
        
        for attr in attributes:
            misp_type = attr.get("type", "")
            ioc_type = type_mapping.get(misp_type)
            
            if not ioc_type:
                continue
            
            value = attr.get("value", "")
            if not value:
                continue
            
            # Verificar si ya existe
            existing = db.query(IocItem).filter(
                and_(IocItem.value == value, IocItem.ioc_type == ioc_type)
            ).first()
            
            if existing:
                errors.append({"value": value, "error": "Already exists"})
                continue
            
            ioc = IocItem(
                value=value,
                ioc_type=ioc_type,
                threat_level=misp_data.default_threat_level.value,
                source="misp",
                description=attr.get("comment", ""),
                external_id=attr.get("uuid"),
                external_source="MISP",
                raw_data=attr,
                confidence_score=50.0
            )
            
            db.add(ioc)
            created.append(value)
        
        db.commit()
        
        # Notificar
        background_tasks.add_task(
            notify_import_completed,
            "misp",
            len(created),
            {"event_id": event.get("id"), "event_info": event.get("info", "")}
        )
        
        logger.info(f"📥 MISP import: {len(created)} IOCs importados")
        
    except Exception as e:
        logger.error(f"Error en import MISP: {e}")
        raise HTTPException(status_code=400, detail=f"Error parsing MISP: {str(e)}")
    
    return {
        "success": True,
        "imported": len(created),
        "errors": len(errors),
        "error_details": errors[:10]
    }


@router.post("/import/stix")
async def import_from_stix(
    stix_data: STIXImport,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Importa IOCs desde formato STIX 2.x JSON.
    """
    created = []
    errors = []
    
    try:
        objects = stix_data.stix_json.get("objects", [])
        
        for obj in objects:
            obj_type = obj.get("type", "")
            
            if obj_type != "indicator":
                continue
            
            pattern = obj.get("pattern", "")
            
            # Parsear patrón STIX simple
            ioc_type = None
            value = None
            
            if "ipv4-addr:value" in pattern:
                ioc_type = "ip"
                value = pattern.split("'")[1] if "'" in pattern else None
            elif "domain-name:value" in pattern:
                ioc_type = "domain"
                value = pattern.split("'")[1] if "'" in pattern else None
            elif "url:value" in pattern:
                ioc_type = "url"
                value = pattern.split("'")[1] if "'" in pattern else None
            elif "file:hashes.'SHA-256'" in pattern:
                ioc_type = "hash_sha256"
                value = pattern.split("'")[3] if pattern.count("'") >= 4 else None
            elif "file:hashes.MD5" in pattern:
                ioc_type = "hash_md5"
                value = pattern.split("'")[1] if "'" in pattern else None
            
            if not ioc_type or not value:
                continue
            
            # Verificar duplicado
            existing = db.query(IocItem).filter(
                and_(IocItem.value == value, IocItem.ioc_type == ioc_type)
            ).first()
            
            if existing:
                errors.append({"value": value, "error": "Already exists"})
                continue
            
            ioc = IocItem(
                value=value,
                ioc_type=ioc_type,
                threat_level=stix_data.default_threat_level.value,
                source="stix",
                description=obj.get("name", ""),
                external_id=obj.get("id"),
                external_source="STIX",
                raw_data=obj,
                confidence_score=50.0
            )
            
            db.add(ioc)
            created.append(value)
        
        db.commit()
        
        background_tasks.add_task(
            notify_import_completed,
            "stix",
            len(created),
            {"bundle_id": stix_data.stix_json.get("id")}
        )
        
        logger.info(f"📥 STIX import: {len(created)} IOCs importados")
        
    except Exception as e:
        logger.error(f"Error en import STIX: {e}")
        raise HTTPException(status_code=400, detail=f"Error parsing STIX: {str(e)}")
    
    return {
        "success": True,
        "imported": len(created),
        "errors": len(errors),
        "error_details": errors[:10]
    }


@router.get("/export")
async def export_iocs(
    format: str = Query("json", enum=["json", "csv", "stix", "misp"]),
    ioc_type: Optional[str] = None,
    threat_level: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Exporta IOCs en diferentes formatos.
    """
    query = db.query(IocItem)
    
    if ioc_type:
        query = query.filter(IocItem.ioc_type == ioc_type)
    if threat_level:
        query = query.filter(IocItem.threat_level == threat_level)
    if status:
        query = query.filter(IocItem.status == status)
    
    iocs = query.all()
    
    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "value", "type", "threat_level", "confidence", "status", "source", "description", "created_at"])
        
        for ioc in iocs:
            writer.writerow([
                ioc.id,
                ioc.value,
                ioc.ioc_type,
                ioc.threat_level,
                ioc.confidence_score,
                ioc.status,
                ioc.source,
                ioc.description or "",
                ioc.created_at.isoformat() if ioc.created_at else ""
            ])
        
        return {
            "format": "csv",
            "count": len(iocs),
            "content": output.getvalue()
        }
    
    elif format == "stix":
        stix_objects = []
        for ioc in iocs:
            stix_objects.append({
                "type": "indicator",
                "id": f"indicator--{ioc.id}",
                "created": ioc.created_at.isoformat() if ioc.created_at else datetime.utcnow().isoformat(),
                "name": f"{ioc.ioc_type}: {ioc.value[:50]}",
                "pattern": f"[{ioc.ioc_type}:value = '{ioc.value}']",
                "pattern_type": "stix",
                "valid_from": ioc.first_seen.isoformat() if ioc.first_seen else datetime.utcnow().isoformat()
            })
        
        return {
            "format": "stix",
            "count": len(iocs),
            "stix": {
                "type": "bundle",
                "id": f"bundle--export-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                "objects": stix_objects
            }
        }
    
    elif format == "misp":
        attributes = []
        type_mapping = {
            "ip": "ip-dst",
            "domain": "domain",
            "url": "url",
            "email": "email-dst",
            "hash_md5": "md5",
            "hash_sha1": "sha1",
            "hash_sha256": "sha256",
            "file_name": "filename"
        }
        
        for ioc in iocs:
            misp_type = type_mapping.get(ioc.ioc_type, "text")
            attributes.append({
                "type": misp_type,
                "value": ioc.value,
                "comment": ioc.description or "",
                "uuid": ioc.id,
                "timestamp": str(int(ioc.created_at.timestamp())) if ioc.created_at else ""
            })
        
        return {
            "format": "misp",
            "count": len(iocs),
            "misp": {
                "Event": {
                    "info": f"IOC Export - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
                    "Attribute": attributes
                }
            }
        }
    
    else:  # json
        return {
            "format": "json",
            "count": len(iocs),
            "items": [ioc_to_response(ioc) for ioc in iocs]
        }


# ============================================================================
# ENRICHMENT
# ============================================================================

@router.post("/{ioc_id}/enrich")
async def enrich_ioc(
    ioc_id: str,
    sources: List[str] = Query(["virustotal"]),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    Enriquece un IOC con datos de fuentes externas.
    
    Fuentes soportadas:
    - virustotal: Análisis de malware/reputación
    - abuseipdb: Reportes de abuso de IPs
    - fullcontact_person: Enriquecimiento de emails (nombre, cargo, empresa, redes sociales)
    - fullcontact_company: Enriquecimiento de dominios (empresa, empleados, industria)
    - shodan: Inteligencia de IPs/puertos
    """
    ioc = db.query(IocItem).filter(IocItem.id == ioc_id).first()
    
    if not ioc:
        raise HTTPException(status_code=404, detail="IOC no encontrado")
    
    enrichment_results = {}
    new_confidence = ioc.confidence_score or 50.0
    
    for source in sources:
        try:
            if source == "virustotal":
                # TODO: Integrar con API real de VirusTotal
                enrichment_results["virustotal"] = {
                    "malicious": 15,
                    "suspicious": 3,
                    "harmless": 42,
                    "undetected": 10,
                    "last_analysis_date": datetime.utcnow().isoformat()
                }
                if enrichment_results["virustotal"]["malicious"] > 10:
                    new_confidence = min(95, new_confidence + 20)
            
            elif source == "abuseipdb":
                # TODO: Integrar con API real de AbuseIPDB
                enrichment_results["abuseipdb"] = {
                    "abuse_confidence_score": 85,
                    "total_reports": 45,
                    "country_code": "RU",
                    "isp": "Unknown ISP"
                }
                if enrichment_results["abuseipdb"]["abuse_confidence_score"] > 50:
                    new_confidence = min(95, new_confidence + 15)
            
            elif source == "fullcontact_person" or source == "fullcontact":
                # Enriquecimiento de persona con FullContact (para emails)
                if ioc.type == "email":
                    from api.services.fullcontact_service import enrich_person_by_email
                    fc_result = await enrich_person_by_email(ioc.value)
                    
                    if fc_result.get("success"):
                        enrichment_results["fullcontact_person"] = {
                            "fullName": fc_result.get("fullName"),
                            "title": fc_result.get("title"),
                            "organization": fc_result.get("organization"),
                            "location": fc_result.get("location"),
                            "twitter": fc_result.get("twitter"),
                            "linkedin": fc_result.get("linkedin"),
                            "avatar": fc_result.get("avatar"),
                            "bio": fc_result.get("bio"),
                            "ageRange": fc_result.get("ageRange"),
                            "gender": fc_result.get("gender"),
                            "enriched_at": fc_result.get("enriched_at")
                        }
                        # Si encontramos info de persona, podría indicar cuenta legítima comprometida
                        if fc_result.get("fullName"):
                            new_confidence = max(30, new_confidence - 10)  # Reducir si parece legítimo
                    else:
                        enrichment_results["fullcontact_person"] = {
                            "error": fc_result.get("error", "Unknown error"),
                            "found": False
                        }
                else:
                    enrichment_results["fullcontact_person"] = {
                        "skipped": True,
                        "reason": f"FullContact person only applies to email IOCs, got {ioc.type}"
                    }
            
            elif source == "fullcontact_company":
                # Enriquecimiento de empresa con FullContact (para dominios)
                if ioc.type == "domain":
                    from api.services.fullcontact_service import enrich_company_by_domain
                    fc_result = await enrich_company_by_domain(ioc.value)
                    
                    if fc_result.get("success"):
                        enrichment_results["fullcontact_company"] = {
                            "name": fc_result.get("name"),
                            "description": fc_result.get("description"),
                            "founded": fc_result.get("founded"),
                            "employees": fc_result.get("employees"),
                            "employeesRange": fc_result.get("employeesRange"),
                            "industry": fc_result.get("industry"),
                            "website": fc_result.get("website"),
                            "social": fc_result.get("social"),
                            "logo": fc_result.get("logo"),
                            "location": fc_result.get("location"),
                            "enriched_at": fc_result.get("enriched_at")
                        }
                        # Si es empresa conocida, podría ser dominio legítimo comprometido
                        if fc_result.get("name") and fc_result.get("employees"):
                            new_confidence = max(25, new_confidence - 15)  # Reducir si parece legítimo
                    else:
                        enrichment_results["fullcontact_company"] = {
                            "error": fc_result.get("error", "Unknown error"),
                            "found": False
                        }
                else:
                    enrichment_results["fullcontact_company"] = {
                        "skipped": True,
                        "reason": f"FullContact company only applies to domain IOCs, got {ioc.type}"
                    }
            
            elif source == "shodan":
                # Enriquecimiento con Shodan (para IPs)
                if ioc.type == "ip":
                    from api.services.threat_intel import shodan_ip_lookup
                    shodan_result = await shodan_ip_lookup(ioc.value)
                    
                    if shodan_result.get("success"):
                        enrichment_results["shodan"] = {
                            "organization": shodan_result.get("organization"),
                            "isp": shodan_result.get("isp"),
                            "country": shodan_result.get("country"),
                            "city": shodan_result.get("city"),
                            "ports": shodan_result.get("ports", []),
                            "hostnames": shodan_result.get("hostnames", []),
                            "vulns": shodan_result.get("vulns", []),
                            "tags": shodan_result.get("tags", [])
                        }
                        # Más puertos abiertos = más sospechoso
                        if len(shodan_result.get("ports", [])) > 10:
                            new_confidence = min(90, new_confidence + 10)
                        # Vulnerabilidades conocidas = muy sospechoso
                        if shodan_result.get("vulns"):
                            new_confidence = min(95, new_confidence + 20)
                    else:
                        enrichment_results["shodan"] = {
                            "error": shodan_result.get("error", "Unknown error")
                        }
                else:
                    enrichment_results["shodan"] = {
                        "skipped": True,
                        "reason": f"Shodan only applies to IP IOCs, got {ioc.type}"
                    }
            
            # Guardar enrichment en BD
            enrichment = IocEnrichment(
                ioc_id=ioc.id,
                source=source,
                reputation_score=new_confidence,
                raw_response=enrichment_results.get(source, enrichment_results.get(f"{source}_person", enrichment_results.get(f"{source}_company", {}))),
                status="success" if not enrichment_results.get(source, {}).get("error") else "error"
            )
            db.add(enrichment)
            
        except Exception as e:
            logger.error(f"❌ Error enriching with {source}: {e}")
            enrichment_results[source] = {
                "error": str(e),
                "status": "failed"
            }
    
    # Actualizar IOC
    ioc.enrichment_data = {**ioc.enrichment_data, **enrichment_results} if ioc.enrichment_data else enrichment_results
    ioc.confidence_score = new_confidence
    
    db.commit()
    db.refresh(ioc)
    
    # Notificar por WebSocket
    if background_tasks:
        background_tasks.add_task(
            notify_ioc_enriched,
            ioc_id,
            {"sources": sources, "new_confidence": new_confidence, "results": enrichment_results}
        )
    
    logger.info(f"🔍 IOC {ioc_id} enriquecido con {sources}")
    
    return {
        "ioc_id": ioc_id,
        "enrichment": enrichment_results,
        "new_confidence_score": new_confidence,
        "sources_queried": sources
    }


# ============================================================================
# CASE LINKING
# ============================================================================

@router.post("/{ioc_id}/link-case")
async def link_ioc_to_case(
    ioc_id: str,
    link_data: LinkToCaseRequest,
    db: Session = Depends(get_db)
):
    """
    Vincula un IOC a un caso de investigación.
    """
    ioc = db.query(IocItem).filter(IocItem.id == ioc_id).first()
    
    if not ioc:
        raise HTTPException(status_code=404, detail="IOC no encontrado")
    
    ioc.case_id = link_data.case_id
    
    if link_data.reason:
        context = ioc.context or ""
        ioc.context = f"{context}\n[Link reason: {link_data.reason}]".strip()
    
    db.commit()
    
    logger.info(f"🔗 IOC {ioc_id} vinculado a caso {link_data.case_id}")
    
    return {
        "success": True,
        "ioc_id": ioc_id,
        "case_id": link_data.case_id
    }


# ============================================================================
# TAGS MANAGEMENT
# ============================================================================

@router.get("/tags")
async def list_all_tags(db: Session = Depends(get_db)):
    """
    Lista todos los tags disponibles.
    """
    tags = db.query(IocTag).order_by(IocTag.name).all()
    
    return {
        "tags": [
            {
                "id": tag.id,
                "name": tag.name,
                "description": tag.description,
                "color": tag.color
            }
            for tag in tags
        ]
    }


@router.post("/{ioc_id}/tags")
async def add_tags_to_ioc(
    ioc_id: str,
    tags: List[str],
    db: Session = Depends(get_db)
):
    """
    Agrega tags a un IOC.
    """
    ioc = db.query(IocItem).filter(IocItem.id == ioc_id).first()
    
    if not ioc:
        raise HTTPException(status_code=404, detail="IOC no encontrado")
    
    added = []
    for tag_name in tags:
        tag = get_or_create_tag(db, tag_name)
        
        # Verificar si ya existe la relación
        existing = db.query(IocItemTag).filter(
            and_(IocItemTag.ioc_id == ioc_id, IocItemTag.tag_id == tag.id)
        ).first()
        
        if not existing:
            ioc_tag = IocItemTag(ioc_id=ioc.id, tag_id=tag.id)
            db.add(ioc_tag)
            added.append(tag_name)
    
    db.commit()
    
    return {"added": added, "ioc_id": ioc_id}


@router.delete("/{ioc_id}/tags/{tag_name}")
async def remove_tag_from_ioc(
    ioc_id: str,
    tag_name: str,
    db: Session = Depends(get_db)
):
    """
    Remueve un tag de un IOC.
    """
    tag = db.query(IocTag).filter(IocTag.name == tag_name.lower()).first()
    
    if not tag:
        raise HTTPException(status_code=404, detail="Tag no encontrado")
    
    deleted = db.query(IocItemTag).filter(
        and_(IocItemTag.ioc_id == ioc_id, IocItemTag.tag_id == tag.id)
    ).delete()
    
    db.commit()
    
    return {"removed": tag_name if deleted else None, "ioc_id": ioc_id}


# ============================================================================
# SIGHTINGS
# ============================================================================

@router.get("/{ioc_id}/sightings")
async def get_ioc_sightings(
    ioc_id: str,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Obtiene los avistamientos de un IOC.
    """
    ioc = db.query(IocItem).filter(IocItem.id == ioc_id).first()
    
    if not ioc:
        raise HTTPException(status_code=404, detail="IOC no encontrado")
    
    sightings = db.query(IocSighting).filter(
        IocSighting.ioc_id == ioc_id
    ).order_by(IocSighting.sighted_at.desc()).limit(limit).all()
    
    return {
        "ioc_id": ioc_id,
        "sightings": [
            {
                "id": s.id,
                "source_system": s.source_system,
                "source_host": s.source_host,
                "context": s.context,
                "case_id": s.case_id,
                "sighted_at": s.sighted_at.isoformat() if s.sighted_at else None,
                "reported_by": s.reported_by
            }
            for s in sightings
        ]
    }


@router.post("/{ioc_id}/sighting")
async def record_sighting(
    ioc_id: str,
    source_system: Optional[str] = None,
    source_host: Optional[str] = None,
    context: Optional[str] = None,
    case_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Registra un nuevo avistamiento de IOC.
    """
    ioc = db.query(IocItem).filter(IocItem.id == ioc_id).first()
    
    if not ioc:
        raise HTTPException(status_code=404, detail="IOC no encontrado")
    
    sighting = IocSighting(
        ioc_id=ioc_id,
        source_system=source_system,
        source_host=source_host,
        context=context,
        case_id=case_id
    )
    
    db.add(sighting)
    
    # Actualizar IOC
    ioc.hit_count = (ioc.hit_count or 0) + 1
    ioc.last_seen = datetime.utcnow()
    
    db.commit()
    
    logger.info(f"👁️ Sighting registrado para IOC {ioc_id}")
    
    return {
        "success": True,
        "ioc_id": ioc_id,
        "sighting_id": sighting.id
    }


# ============================================================================
# CLOUD IOC - M365 Integration
# ============================================================================

@router.get("/cloud/cases")
async def list_cloud_ioc_cases(db: Session = Depends(get_db)):
    """
    Lista todos los casos que tienen IOCs de M365/Cloud.
    """
    # Obtener casos únicos con IOCs de fuentes cloud
    cloud_sources = ['investigation', 'threat_intel', 'm365', 'azure', 'graph']
    
    cases = db.query(IocItem.case_id).filter(
        IocItem.case_id.isnot(None),
        or_(*[IocItem.source.ilike(f"%{src}%") for src in cloud_sources])
    ).distinct().all()
    
    case_list = []
    for (case_id,) in cases:
        if case_id:
            count = db.query(IocItem).filter(IocItem.case_id == case_id).count()
            case_list.append({
                "case_id": case_id,
                "ioc_count": count
            })
    
    return {
        "cases": case_list,
        "total": len(case_list)
    }


@router.get("/cloud/by-case/{case_id}")
async def get_cloud_iocs_by_case(
    case_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Obtiene IOCs de Cloud/M365 para un caso específico.
    """
    query = db.query(IocItem).filter(IocItem.case_id == case_id)
    
    total = query.count()
    offset = (page - 1) * limit
    iocs = query.order_by(IocItem.threat_level.desc(), IocItem.created_at.desc()).offset(offset).limit(limit).all()
    
    pages = (total + limit - 1) // limit
    
    return {
        "case_id": case_id,
        "items": [ioc_to_response(ioc) for ioc in iocs],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": pages
    }


@router.post("/cloud/extract-from-investigation/{investigation_id}")
async def extract_iocs_from_investigation(
    investigation_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Extrae IOCs de los resultados de una investigación M365 usando AI.
    Parsea automáticamente los hallazgos y crea IOCs en el store.
    """
    from api.services.soar_intelligence import soar_engine
    from api.config import settings
    
    # Buscar archivos de evidencia de la investigación
    evidence_path = settings.EVIDENCE_DIR / investigation_id
    
    findings = []
    iocs_created = []
    
    # Leer archivos de evidencia si existen
    if evidence_path.exists():
        for file_path in evidence_path.rglob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    findings.append(data)
            except Exception as e:
                logger.warning(f"Error leyendo {file_path}: {e}")
    
    # Si no hay archivos locales, buscar en la base de datos
    if not findings:
        # Buscar en investigations existentes
        pass  # TODO: Implementar query a investigations
    
    # Procesar cada hallazgo con SOAR Intelligence
    for finding in findings:
        try:
            analysis = soar_engine.analyze_findings(finding)
            
            # Crear IOCs extraídos
            for ioc_data in analysis.get("iocs_extracted", []):
                # Verificar si ya existe
                existing = db.query(IocItem).filter(
                    and_(
                        IocItem.value == ioc_data["value"],
                        IocItem.ioc_type == ioc_data["type"]
                    )
                ).first()
                
                if not existing:
                    ioc = IocItem(
                        value=ioc_data["value"],
                        ioc_type=ioc_data["type"],
                        threat_level=analysis.get("severity", "medium"),
                        source="investigation",
                        case_id=investigation_id,
                        description=f"Extraído automáticamente de investigación {investigation_id}",
                        confidence_score=analysis.get("confidence_score", 50.0)
                    )
                    db.add(ioc)
                    db.flush()
                    
                    # Agregar tags
                    for tag_name in analysis.get("tags", []):
                        tag = get_or_create_tag(db, tag_name)
                        ioc_tag = IocItemTag(ioc_id=ioc.id, tag_id=tag.id)
                        db.add(ioc_tag)
                    
                    iocs_created.append(ioc_to_response(ioc))
                    
        except Exception as e:
            logger.error(f"Error procesando hallazgo: {e}")
    
    db.commit()
    
    logger.info(f"🔍 Extraídos {len(iocs_created)} IOCs de investigación {investigation_id}")
    
    return {
        "investigation_id": investigation_id,
        "findings_processed": len(findings),
        "iocs_created": len(iocs_created),
        "iocs": iocs_created
    }


# ============================================================================
# AI ANALYSIS ENDPOINTS
# ============================================================================

@router.post("/{ioc_id}/ai-analyze")
async def ai_analyze_ioc(
    ioc_id: str,
    db: Session = Depends(get_db)
):
    """
    Analiza un IOC con el motor de IA (Phi-4) para obtener:
    - Clasificación de severidad
    - Recomendaciones de respuesta
    - Tags sugeridos
    - Score de confianza actualizado
    """
    from api.services.soar_intelligence import soar_engine
    
    ioc = db.query(IocItem).filter(IocItem.id == ioc_id).first()
    
    if not ioc:
        raise HTTPException(status_code=404, detail="IOC no encontrado")
    
    # Preparar datos para análisis
    ioc_data = {
        "value": ioc.value,
        "type": ioc.ioc_type,
        "current_threat_level": ioc.threat_level,
        "description": ioc.description,
        "source": ioc.source,
        "context": ioc.context,
        "enrichment": ioc.enrichment_data or {}
    }
    
    # Analizar con SOAR Intelligence
    analysis = soar_engine.analyze_findings(ioc_data)
    
    # Actualizar IOC con resultados
    if analysis.get("severity"):
        ioc.threat_level = analysis["severity"]
    
    if analysis.get("confidence_score"):
        ioc.confidence_score = analysis["confidence_score"]
    
    # Agregar nuevos tags sugeridos
    for tag_name in analysis.get("tags", []):
        existing_tag = db.query(IocItemTag).join(IocTag).filter(
            IocItemTag.ioc_id == ioc_id,
            IocTag.name == tag_name.lower()
        ).first()
        
        if not existing_tag:
            tag = get_or_create_tag(db, tag_name)
            ioc_tag = IocItemTag(ioc_id=ioc.id, tag_id=tag.id)
            db.add(ioc_tag)
    
    db.commit()
    db.refresh(ioc)
    
    logger.info(f"🧠 IOC {ioc_id} analizado con AI: severity={analysis.get('severity')}")
    
    return {
        "ioc_id": ioc_id,
        "analysis": analysis,
        "updated_ioc": ioc_to_response(ioc)
    }


@router.post("/ai-bulk-analyze")
async def ai_bulk_analyze_iocs(
    case_id: Optional[str] = None,
    threat_level: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    Analiza múltiples IOCs con AI en lote.
    """
    from api.services.soar_intelligence import soar_engine
    
    query = db.query(IocItem)
    
    if case_id:
        query = query.filter(IocItem.case_id == case_id)
    
    if threat_level:
        query = query.filter(IocItem.threat_level == threat_level)
    
    iocs = query.limit(limit).all()
    
    results = []
    
    for ioc in iocs:
        try:
            ioc_data = {
                "value": ioc.value,
                "type": ioc.ioc_type,
                "current_threat_level": ioc.threat_level,
                "description": ioc.description
            }
            
            analysis = soar_engine.analyze_findings(ioc_data)
            
            # Actualizar IOC
            if analysis.get("severity"):
                ioc.threat_level = analysis["severity"]
            if analysis.get("confidence_score"):
                ioc.confidence_score = analysis["confidence_score"]
            
            results.append({
                "ioc_id": ioc.id,
                "old_threat_level": ioc_data["current_threat_level"],
                "new_threat_level": analysis.get("severity"),
                "confidence_score": analysis.get("confidence_score"),
                "tags": analysis.get("tags", [])
            })
            
        except Exception as e:
            logger.error(f"Error analizando IOC {ioc.id}: {e}")
            results.append({
                "ioc_id": ioc.id,
                "error": str(e)
            })
    
    db.commit()
    
    logger.info(f"🧠 Bulk AI analysis completado: {len(results)} IOCs procesados")
    
    return {
        "iocs_analyzed": len(results),
        "results": results
    }

