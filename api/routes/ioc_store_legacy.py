"""
IOC Store Router - Gestión centralizada de Indicadores de Compromiso
Proporciona CRUD, importación/exportación, scoring y búsqueda de IOCs
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, UploadFile, File
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
import json
import csv
import io
import hashlib
import asyncio
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/iocs", tags=["IOC Store"])


# ============================================================================
# ENUMS Y MODELOS
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


# ============================================================================
# MODELOS PYDANTIC
# ============================================================================

class IOCCreate(BaseModel):
    value: str = Field(..., min_length=1, max_length=2000)
    ioc_type: IOCType
    threat_level: ThreatLevel = ThreatLevel.MEDIUM
    source: IOCSource = IOCSource.MANUAL
    case_id: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = []
    ttl_days: Optional[int] = Field(None, ge=1, le=365)
    metadata: Dict[str, Any] = {}


class IOCUpdate(BaseModel):
    threat_level: Optional[ThreatLevel] = None
    status: Optional[IOCStatus] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    ttl_days: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class IOCResponse(BaseModel):
    id: str
    value: str
    ioc_type: IOCType
    threat_level: ThreatLevel
    status: IOCStatus
    source: IOCSource
    confidence_score: float
    case_id: Optional[str]
    description: Optional[str]
    tags: List[str]
    first_seen: datetime
    last_seen: datetime
    expires_at: Optional[datetime]
    hit_count: int
    enrichment: Dict[str, Any]
    metadata: Dict[str, Any]
    created_by: str
    updated_at: datetime


class IOCBulkCreate(BaseModel):
    iocs: List[IOCCreate]
    deduplicate: bool = True


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


class IOCEnrichmentRequest(BaseModel):
    ioc_ids: List[str]
    sources: List[str] = ["virustotal", "abuseipdb", "shodan"]


class IOCExportRequest(BaseModel):
    format: str = Field(..., pattern="^(csv|json|stix|misp|openioc)$")
    ioc_ids: Optional[List[str]] = None
    filters: Optional[IOCSearchQuery] = None


# ============================================================================
# ALMACENAMIENTO EN MEMORIA (Simulado - en producción usar DB)
# ============================================================================

_ioc_store: Dict[str, Dict] = {}
_ioc_counter = 0


def _generate_ioc_id() -> str:
    global _ioc_counter
    _ioc_counter += 1
    return f"IOC-{datetime.now().strftime('%Y%m%d')}-{_ioc_counter:05d}"


def _calculate_confidence(ioc_data: dict) -> float:
    """Calcula score de confianza basado en múltiples factores"""
    score = 50.0  # Base score
    
    # Factor: Fuente
    source_scores = {
        IOCSource.VIRUSTOTAL: 25,
        IOCSource.ABUSEIPDB: 20,
        IOCSource.THREAT_INTEL: 20,
        IOCSource.INVESTIGATION: 15,
        IOCSource.HIBP: 15,
        IOCSource.MANUAL: 10,
        IOCSource.OSINT: 10,
        IOCSource.IMPORT: 5
    }
    score += source_scores.get(ioc_data.get("source"), 0)
    
    # Factor: Tags (más tags = más contexto)
    tags = ioc_data.get("tags", [])
    score += min(len(tags) * 2, 10)
    
    # Factor: Descripción
    if ioc_data.get("description"):
        score += 5
    
    # Factor: Metadata
    if ioc_data.get("metadata"):
        score += min(len(ioc_data["metadata"]) * 2, 10)
    
    # Factor: Hit count
    hit_count = ioc_data.get("hit_count", 0)
    if hit_count > 0:
        score += min(hit_count * 0.5, 10)
    
    return min(score, 100.0)


def _hash_ioc_value(value: str, ioc_type: IOCType) -> str:
    """Genera hash único para deduplicación"""
    normalized = value.lower().strip()
    return hashlib.sha256(f"{ioc_type}:{normalized}".encode()).hexdigest()[:16]


# ============================================================================
# ENDPOINTS - CRUD
# ============================================================================

@router.get("/")
async def list_iocs(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    ioc_type: Optional[IOCType] = None,
    threat_level: Optional[ThreatLevel] = None,
    status: Optional[IOCStatus] = None,
    source: Optional[IOCSource] = None,
    tag: Optional[str] = None,
    case_id: Optional[str] = None,
    search: Optional[str] = None
):
    """Lista IOCs con paginación y filtros"""
    
    # Filtrar
    filtered = list(_ioc_store.values())
    
    if ioc_type:
        filtered = [i for i in filtered if i["ioc_type"] == ioc_type]
    if threat_level:
        filtered = [i for i in filtered if i["threat_level"] == threat_level]
    if status:
        filtered = [i for i in filtered if i["status"] == status]
    if source:
        filtered = [i for i in filtered if i["source"] == source]
    if tag:
        filtered = [i for i in filtered if tag in i.get("tags", [])]
    if case_id:
        filtered = [i for i in filtered if i.get("case_id") == case_id]
    if search:
        search_lower = search.lower()
        filtered = [i for i in filtered if search_lower in i["value"].lower() or 
                   search_lower in (i.get("description") or "").lower()]
    
    # Ordenar por última vez visto
    filtered.sort(key=lambda x: x.get("last_seen", datetime.min), reverse=True)
    
    # Paginar
    total = len(filtered)
    start = (page - 1) * limit
    end = start + limit
    items = filtered[start:end]
    
    return {
        "items": items,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        },
        "summary": {
            "total_iocs": len(_ioc_store),
            "critical": len([i for i in _ioc_store.values() if i["threat_level"] == ThreatLevel.CRITICAL]),
            "high": len([i for i in _ioc_store.values() if i["threat_level"] == ThreatLevel.HIGH]),
            "active": len([i for i in _ioc_store.values() if i["status"] == IOCStatus.ACTIVE])
        }
    }


@router.get("/stats")
async def get_ioc_stats():
    """Estadísticas del IOC Store"""
    
    iocs = list(_ioc_store.values())
    
    # Por tipo
    by_type = {}
    for ioc_type in IOCType:
        count = len([i for i in iocs if i["ioc_type"] == ioc_type])
        if count > 0:
            by_type[ioc_type.value] = count
    
    # Por nivel de amenaza
    by_threat = {}
    for level in ThreatLevel:
        count = len([i for i in iocs if i["threat_level"] == level])
        by_threat[level.value] = count
    
    # Por fuente
    by_source = {}
    for source in IOCSource:
        count = len([i for i in iocs if i["source"] == source])
        if count > 0:
            by_source[source.value] = count
    
    # Por estado
    by_status = {}
    for status in IOCStatus:
        count = len([i for i in iocs if i["status"] == status])
        by_status[status.value] = count
    
    # Tags más usados
    all_tags = []
    for ioc in iocs:
        all_tags.extend(ioc.get("tags", []))
    top_tags = {}
    for tag in set(all_tags):
        top_tags[tag] = all_tags.count(tag)
    top_tags = dict(sorted(top_tags.items(), key=lambda x: x[1], reverse=True)[:10])
    
    # Confianza promedio
    avg_confidence = sum(i.get("confidence_score", 0) for i in iocs) / len(iocs) if iocs else 0
    
    return {
        "total": len(iocs),
        "by_type": by_type,
        "by_threat_level": by_threat,
        "by_source": by_source,
        "by_status": by_status,
        "top_tags": top_tags,
        "average_confidence": round(avg_confidence, 2),
        "last_updated": datetime.utcnow().isoformat()
    }


@router.get("/{ioc_id}")
async def get_ioc(ioc_id: str):
    """Obtiene un IOC por ID"""
    
    if ioc_id not in _ioc_store:
        raise HTTPException(status_code=404, detail=f"IOC {ioc_id} not found")
    
    ioc = _ioc_store[ioc_id].copy()
    
    # Incrementar hit count
    _ioc_store[ioc_id]["hit_count"] = _ioc_store[ioc_id].get("hit_count", 0) + 1
    _ioc_store[ioc_id]["last_seen"] = datetime.utcnow()
    
    return ioc


@router.post("/", status_code=201)
async def create_ioc(ioc: IOCCreate):
    """Crea un nuevo IOC"""
    
    # Verificar duplicado
    value_hash = _hash_ioc_value(ioc.value, ioc.ioc_type)
    for existing in _ioc_store.values():
        if existing.get("value_hash") == value_hash:
            # Actualizar last_seen y hit_count en lugar de crear duplicado
            existing["last_seen"] = datetime.utcnow()
            existing["hit_count"] = existing.get("hit_count", 0) + 1
            return {
                "status": "duplicate",
                "message": "IOC already exists, updated last_seen",
                "ioc": existing
            }
    
    # Crear nuevo
    ioc_id = _generate_ioc_id()
    now = datetime.utcnow()
    
    expires_at = None
    if ioc.ttl_days:
        expires_at = now + timedelta(days=ioc.ttl_days)
    
    ioc_data = {
        "id": ioc_id,
        "value": ioc.value,
        "value_hash": value_hash,
        "ioc_type": ioc.ioc_type,
        "threat_level": ioc.threat_level,
        "status": IOCStatus.ACTIVE,
        "source": ioc.source,
        "case_id": ioc.case_id,
        "description": ioc.description,
        "tags": ioc.tags,
        "first_seen": now,
        "last_seen": now,
        "expires_at": expires_at,
        "hit_count": 0,
        "enrichment": {},
        "metadata": ioc.metadata,
        "created_by": "system",
        "updated_at": now
    }
    
    # Calcular confianza
    ioc_data["confidence_score"] = _calculate_confidence(ioc_data)
    
    _ioc_store[ioc_id] = ioc_data
    
    logger.info(f"✅ IOC creado: {ioc_id} ({ioc.ioc_type}: {ioc.value[:50]}...)")
    
    return {
        "status": "created",
        "ioc": ioc_data
    }


@router.put("/{ioc_id}")
async def update_ioc(ioc_id: str, update: IOCUpdate):
    """Actualiza un IOC existente"""
    
    if ioc_id not in _ioc_store:
        raise HTTPException(status_code=404, detail=f"IOC {ioc_id} not found")
    
    ioc = _ioc_store[ioc_id]
    
    if update.threat_level:
        ioc["threat_level"] = update.threat_level
    if update.status:
        ioc["status"] = update.status
    if update.description is not None:
        ioc["description"] = update.description
    if update.tags is not None:
        ioc["tags"] = update.tags
    if update.ttl_days:
        ioc["expires_at"] = datetime.utcnow() + timedelta(days=update.ttl_days)
    if update.metadata is not None:
        ioc["metadata"].update(update.metadata)
    
    ioc["updated_at"] = datetime.utcnow()
    ioc["confidence_score"] = _calculate_confidence(ioc)
    
    return {"status": "updated", "ioc": ioc}


@router.delete("/{ioc_id}")
async def delete_ioc(ioc_id: str):
    """Elimina un IOC"""
    
    if ioc_id not in _ioc_store:
        raise HTTPException(status_code=404, detail=f"IOC {ioc_id} not found")
    
    deleted = _ioc_store.pop(ioc_id)
    
    logger.info(f"🗑️ IOC eliminado: {ioc_id}")
    
    return {"status": "deleted", "ioc_id": ioc_id, "value": deleted["value"]}


# ============================================================================
# ENDPOINTS - BULK OPERATIONS
# ============================================================================

@router.post("/bulk")
async def create_iocs_bulk(bulk: IOCBulkCreate, background_tasks: BackgroundTasks):
    """Crea múltiples IOCs en lote"""
    
    results = {
        "created": 0,
        "duplicates": 0,
        "errors": 0,
        "iocs": []
    }
    
    for ioc_create in bulk.iocs:
        try:
            result = await create_ioc(ioc_create)
            if result["status"] == "created":
                results["created"] += 1
            else:
                results["duplicates"] += 1
            results["iocs"].append(result["ioc"]["id"])
        except Exception as e:
            results["errors"] += 1
            logger.error(f"Error creating IOC: {e}")
    
    return results


@router.post("/import")
async def import_iocs(
    file: UploadFile = File(...),
    ioc_type: Optional[IOCType] = None,
    source: IOCSource = IOCSource.IMPORT,
    case_id: Optional[str] = None,
    threat_level: ThreatLevel = ThreatLevel.MEDIUM
):
    """Importa IOCs desde archivo CSV o JSON"""
    
    content = await file.read()
    filename = file.filename.lower()
    
    iocs_to_create = []
    
    try:
        if filename.endswith(".csv"):
            # Parsear CSV
            csv_content = content.decode("utf-8")
            reader = csv.DictReader(io.StringIO(csv_content))
            
            for row in reader:
                value = row.get("value") or row.get("indicator") or row.get("ioc")
                if not value:
                    continue
                
                detected_type = ioc_type or _detect_ioc_type(value)
                
                iocs_to_create.append(IOCCreate(
                    value=value.strip(),
                    ioc_type=detected_type,
                    threat_level=ThreatLevel(row.get("threat_level", threat_level)),
                    source=source,
                    case_id=case_id,
                    description=row.get("description"),
                    tags=row.get("tags", "").split(",") if row.get("tags") else []
                ))
        
        elif filename.endswith(".json"):
            # Parsear JSON
            data = json.loads(content.decode("utf-8"))
            
            if isinstance(data, list):
                items = data
            elif "iocs" in data:
                items = data["iocs"]
            elif "indicators" in data:
                items = data["indicators"]
            else:
                items = [data]
            
            for item in items:
                if isinstance(item, str):
                    value = item
                    detected_type = ioc_type or _detect_ioc_type(value)
                    iocs_to_create.append(IOCCreate(
                        value=value,
                        ioc_type=detected_type,
                        threat_level=threat_level,
                        source=source,
                        case_id=case_id
                    ))
                elif isinstance(item, dict):
                    value = item.get("value") or item.get("indicator")
                    if value:
                        detected_type = ioc_type or IOCType(item.get("type", "ip"))
                        iocs_to_create.append(IOCCreate(
                            value=value,
                            ioc_type=detected_type,
                            threat_level=ThreatLevel(item.get("threat_level", threat_level)),
                            source=source,
                            case_id=case_id,
                            description=item.get("description"),
                            tags=item.get("tags", [])
                        ))
        
        else:
            # Texto plano - una línea por IOC
            lines = content.decode("utf-8").strip().split("\n")
            for line in lines:
                value = line.strip()
                if value and not value.startswith("#"):
                    detected_type = ioc_type or _detect_ioc_type(value)
                    iocs_to_create.append(IOCCreate(
                        value=value,
                        ioc_type=detected_type,
                        threat_level=threat_level,
                        source=source,
                        case_id=case_id
                    ))
        
        # Crear IOCs
        bulk = IOCBulkCreate(iocs=iocs_to_create)
        result = await create_iocs_bulk(bulk, BackgroundTasks())
        
        return {
            "status": "success",
            "filename": file.filename,
            "parsed": len(iocs_to_create),
            **result
        }
    
    except Exception as e:
        logger.error(f"Error importing IOCs: {e}")
        raise HTTPException(status_code=400, detail=f"Import error: {str(e)}")


def _detect_ioc_type(value: str) -> IOCType:
    """Detecta automáticamente el tipo de IOC"""
    import re
    
    value = value.strip().lower()
    
    # IP (IPv4)
    if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", value):
        return IOCType.IP
    
    # Email
    if re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", value):
        return IOCType.EMAIL
    
    # URL
    if value.startswith(("http://", "https://", "ftp://")):
        return IOCType.URL
    
    # SHA256
    if re.match(r"^[a-f0-9]{64}$", value):
        return IOCType.HASH_SHA256
    
    # SHA1
    if re.match(r"^[a-f0-9]{40}$", value):
        return IOCType.HASH_SHA1
    
    # MD5
    if re.match(r"^[a-f0-9]{32}$", value):
        return IOCType.HASH_MD5
    
    # CVE
    if re.match(r"^cve-\d{4}-\d+$", value):
        return IOCType.CVE
    
    # Domain (fallback)
    if re.match(r"^[a-zA-Z0-9][a-zA-Z0-9-]*\.[a-zA-Z]{2,}$", value):
        return IOCType.DOMAIN
    
    # Default
    return IOCType.DOMAIN


@router.get("/export")
async def export_iocs(
    format: str = Query("json", pattern="^(csv|json|stix|misp)$"),
    ioc_type: Optional[IOCType] = None,
    threat_level: Optional[ThreatLevel] = None,
    case_id: Optional[str] = None
):
    """Exporta IOCs en diferentes formatos"""
    
    # Filtrar
    iocs = list(_ioc_store.values())
    
    if ioc_type:
        iocs = [i for i in iocs if i["ioc_type"] == ioc_type]
    if threat_level:
        iocs = [i for i in iocs if i["threat_level"] == threat_level]
    if case_id:
        iocs = [i for i in iocs if i.get("case_id") == case_id]
    
    if format == "json":
        return {
            "format": "json",
            "count": len(iocs),
            "exported_at": datetime.utcnow().isoformat(),
            "iocs": iocs
        }
    
    elif format == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "id", "value", "ioc_type", "threat_level", "status",
            "source", "confidence_score", "first_seen", "tags", "description"
        ])
        writer.writeheader()
        
        for ioc in iocs:
            writer.writerow({
                "id": ioc["id"],
                "value": ioc["value"],
                "ioc_type": ioc["ioc_type"],
                "threat_level": ioc["threat_level"],
                "status": ioc["status"],
                "source": ioc["source"],
                "confidence_score": ioc["confidence_score"],
                "first_seen": ioc["first_seen"].isoformat() if isinstance(ioc["first_seen"], datetime) else ioc["first_seen"],
                "tags": ",".join(ioc.get("tags", [])),
                "description": ioc.get("description", "")
            })
        
        return {
            "format": "csv",
            "count": len(iocs),
            "content": output.getvalue()
        }
    
    elif format == "stix":
        # STIX 2.1 format
        stix_bundle = {
            "type": "bundle",
            "id": f"bundle--{hashlib.uuid4().hex}",
            "objects": []
        }
        
        for ioc in iocs:
            stix_object = {
                "type": "indicator",
                "id": f"indicator--{hashlib.md5(ioc['id'].encode()).hexdigest()}",
                "created": ioc["first_seen"].isoformat() if isinstance(ioc["first_seen"], datetime) else ioc["first_seen"],
                "modified": ioc["updated_at"].isoformat() if isinstance(ioc["updated_at"], datetime) else ioc["updated_at"],
                "name": f"{ioc['ioc_type']}: {ioc['value'][:50]}",
                "description": ioc.get("description", ""),
                "pattern": f"[{ioc['ioc_type']}:value = '{ioc['value']}']",
                "pattern_type": "stix",
                "valid_from": ioc["first_seen"].isoformat() if isinstance(ioc["first_seen"], datetime) else ioc["first_seen"],
                "labels": ioc.get("tags", []),
                "confidence": int(ioc["confidence_score"])
            }
            stix_bundle["objects"].append(stix_object)
        
        return {
            "format": "stix",
            "version": "2.1",
            "count": len(iocs),
            "bundle": stix_bundle
        }
    
    elif format == "misp":
        # MISP format
        misp_event = {
            "Event": {
                "info": f"IOC Export - {datetime.utcnow().strftime('%Y-%m-%d')}",
                "date": datetime.utcnow().strftime("%Y-%m-%d"),
                "threat_level_id": "2",
                "analysis": "2",
                "Attribute": []
            }
        }
        
        type_mapping = {
            IOCType.IP: "ip-dst",
            IOCType.DOMAIN: "domain",
            IOCType.URL: "url",
            IOCType.EMAIL: "email-src",
            IOCType.HASH_MD5: "md5",
            IOCType.HASH_SHA1: "sha1",
            IOCType.HASH_SHA256: "sha256",
            IOCType.FILE_NAME: "filename"
        }
        
        for ioc in iocs:
            misp_type = type_mapping.get(IOCType(ioc["ioc_type"]), "text")
            misp_event["Event"]["Attribute"].append({
                "type": misp_type,
                "value": ioc["value"],
                "comment": ioc.get("description", ""),
                "to_ids": True,
                "Tag": [{"name": tag} for tag in ioc.get("tags", [])]
            })
        
        return {
            "format": "misp",
            "count": len(iocs),
            "event": misp_event
        }


# ============================================================================
# ENDPOINTS - ENRICHMENT
# ============================================================================

@router.post("/{ioc_id}/enrich")
async def enrich_ioc(
    ioc_id: str,
    sources: List[str] = Query(["virustotal", "abuseipdb"])
):
    """Enriquece un IOC con fuentes externas"""
    
    if ioc_id not in _ioc_store:
        raise HTTPException(status_code=404, detail=f"IOC {ioc_id} not found")
    
    ioc = _ioc_store[ioc_id]
    enrichment = {}
    
    # Simular enriquecimiento (en producción usar APIs reales)
    if "virustotal" in sources and ioc["ioc_type"] in [IOCType.IP, IOCType.DOMAIN, IOCType.HASH_SHA256]:
        enrichment["virustotal"] = {
            "status": "enriched",
            "malicious": 5,
            "suspicious": 2,
            "harmless": 60,
            "undetected": 10,
            "reputation": -45,
            "last_analysis_date": datetime.utcnow().isoformat()
        }
    
    if "abuseipdb" in sources and ioc["ioc_type"] == IOCType.IP:
        enrichment["abuseipdb"] = {
            "status": "enriched",
            "abuse_confidence_score": 75,
            "total_reports": 128,
            "last_reported_at": datetime.utcnow().isoformat(),
            "isp": "Example ISP",
            "country_code": "RU",
            "is_tor": False
        }
    
    if "shodan" in sources and ioc["ioc_type"] == IOCType.IP:
        enrichment["shodan"] = {
            "status": "enriched",
            "ports": [22, 80, 443, 8080],
            "hostnames": ["example.com"],
            "org": "Example Org",
            "os": "Linux"
        }
    
    # Actualizar IOC
    ioc["enrichment"].update(enrichment)
    ioc["updated_at"] = datetime.utcnow()
    ioc["confidence_score"] = _calculate_confidence(ioc)
    
    # Ajustar threat level basado en enrichment
    if enrichment.get("virustotal", {}).get("malicious", 0) > 10:
        ioc["threat_level"] = ThreatLevel.CRITICAL
    elif enrichment.get("abuseipdb", {}).get("abuse_confidence_score", 0) > 80:
        ioc["threat_level"] = ThreatLevel.HIGH
    
    return {
        "status": "enriched",
        "ioc_id": ioc_id,
        "sources_used": sources,
        "enrichment": enrichment,
        "new_confidence_score": ioc["confidence_score"],
        "new_threat_level": ioc["threat_level"]
    }


@router.post("/enrich/bulk")
async def enrich_iocs_bulk(request: IOCEnrichmentRequest, background_tasks: BackgroundTasks):
    """Enriquece múltiples IOCs en background"""
    
    async def _enrich_batch():
        for ioc_id in request.ioc_ids:
            try:
                await enrich_ioc(ioc_id, request.sources)
            except Exception as e:
                logger.error(f"Error enriching {ioc_id}: {e}")
    
    background_tasks.add_task(_enrich_batch)
    
    return {
        "status": "queued",
        "iocs_count": len(request.ioc_ids),
        "sources": request.sources,
        "message": "Enrichment started in background"
    }


# ============================================================================
# ENDPOINTS - SEARCH & MATCH
# ============================================================================

@router.post("/search")
async def search_iocs(query: IOCSearchQuery):
    """Búsqueda avanzada de IOCs"""
    
    results = list(_ioc_store.values())
    
    if query.query:
        q = query.query.lower()
        results = [i for i in results if 
                  q in i["value"].lower() or 
                  q in (i.get("description") or "").lower() or
                  any(q in tag.lower() for tag in i.get("tags", []))]
    
    if query.ioc_types:
        results = [i for i in results if i["ioc_type"] in query.ioc_types]
    
    if query.threat_levels:
        results = [i for i in results if i["threat_level"] in query.threat_levels]
    
    if query.sources:
        results = [i for i in results if i["source"] in query.sources]
    
    if query.statuses:
        results = [i for i in results if i["status"] in query.statuses]
    
    if query.tags:
        results = [i for i in results if any(tag in i.get("tags", []) for tag in query.tags)]
    
    if query.case_id:
        results = [i for i in results if i.get("case_id") == query.case_id]
    
    if query.min_confidence:
        results = [i for i in results if i.get("confidence_score", 0) >= query.min_confidence]
    
    if query.date_from:
        results = [i for i in results if i.get("first_seen", datetime.min) >= query.date_from]
    
    if query.date_to:
        results = [i for i in results if i.get("first_seen", datetime.max) <= query.date_to]
    
    # Ordenar por confianza
    results.sort(key=lambda x: x.get("confidence_score", 0), reverse=True)
    
    return {
        "count": len(results),
        "query": query.dict(exclude_none=True),
        "results": results[:100]  # Limitar a 100
    }


@router.post("/match")
async def match_iocs(values: List[str]):
    """Verifica si una lista de valores coincide con IOCs existentes"""
    
    matches = []
    
    for value in values:
        detected_type = _detect_ioc_type(value)
        value_hash = _hash_ioc_value(value, detected_type)
        
        for ioc in _ioc_store.values():
            if ioc.get("value_hash") == value_hash:
                matches.append({
                    "input": value,
                    "matched_ioc": ioc,
                    "match_type": "exact"
                })
                # Actualizar hit count
                ioc["hit_count"] = ioc.get("hit_count", 0) + 1
                ioc["last_seen"] = datetime.utcnow()
                break
    
    return {
        "total_input": len(values),
        "total_matches": len(matches),
        "match_rate": len(matches) / len(values) * 100 if values else 0,
        "matches": matches
    }


# ============================================================================
# ENDPOINTS - HOUSEKEEPING
# ============================================================================

@router.post("/cleanup")
async def cleanup_expired_iocs():
    """Limpia IOCs expirados"""
    
    now = datetime.utcnow()
    expired_ids = []
    
    for ioc_id, ioc in list(_ioc_store.items()):
        expires_at = ioc.get("expires_at")
        if expires_at and expires_at < now:
            expired_ids.append(ioc_id)
            _ioc_store[ioc_id]["status"] = IOCStatus.EXPIRED
    
    return {
        "status": "completed",
        "expired_count": len(expired_ids),
        "expired_ids": expired_ids
    }


@router.delete("/bulk")
async def delete_iocs_bulk(ioc_ids: List[str]):
    """Elimina múltiples IOCs"""
    
    deleted = 0
    not_found = 0
    
    for ioc_id in ioc_ids:
        if ioc_id in _ioc_store:
            del _ioc_store[ioc_id]
            deleted += 1
        else:
            not_found += 1
    
    return {
        "deleted": deleted,
        "not_found": not_found
    }


# ============================================================================
# INICIALIZACIÓN CON DATOS DEMO
# ============================================================================

def _init_demo_data():
    """Inicializa datos de demostración"""
    
    demo_iocs = [
        IOCCreate(value="185.234.72.15", ioc_type=IOCType.IP, threat_level=ThreatLevel.CRITICAL,
                 source=IOCSource.INVESTIGATION, case_id="IR-2025-001",
                 description="C2 server detected in BEC investigation",
                 tags=["c2", "apt", "russia"]),
        
        IOCCreate(value="91.234.99.42", ioc_type=IOCType.IP, threat_level=ThreatLevel.HIGH,
                 source=IOCSource.THREAT_INTEL,
                 description="Known malicious infrastructure",
                 tags=["botnet", "emotet"]),
        
        IOCCreate(value="malicious-domain.com", ioc_type=IOCType.DOMAIN, threat_level=ThreatLevel.HIGH,
                 source=IOCSource.INVESTIGATION, case_id="IR-2025-001",
                 description="Phishing domain",
                 tags=["phishing", "credential-theft"]),
        
        IOCCreate(value="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                 ioc_type=IOCType.HASH_SHA256, threat_level=ThreatLevel.CRITICAL,
                 source=IOCSource.VIRUSTOTAL,
                 description="Emotet dropper",
                 tags=["malware", "emotet", "dropper"]),
        
        IOCCreate(value="attacker@malicious.com", ioc_type=IOCType.EMAIL, threat_level=ThreatLevel.MEDIUM,
                 source=IOCSource.INVESTIGATION, case_id="IR-2025-001",
                 description="Sender of phishing emails",
                 tags=["phishing", "bec"]),
        
        IOCCreate(value="https://evil-site.com/payload.exe", ioc_type=IOCType.URL, threat_level=ThreatLevel.HIGH,
                 source=IOCSource.OSINT,
                 description="Malware distribution URL",
                 tags=["malware", "distribution"]),
        
        IOCCreate(value="invoice_final.docm", ioc_type=IOCType.FILE_NAME, threat_level=ThreatLevel.HIGH,
                 source=IOCSource.INVESTIGATION, case_id="IR-2025-002",
                 description="Macro-enabled document used in attack",
                 tags=["macro", "maldoc"]),
        
        IOCCreate(value="CVE-2024-21762", ioc_type=IOCType.CVE, threat_level=ThreatLevel.CRITICAL,
                 source=IOCSource.THREAT_INTEL,
                 description="FortiOS SSL VPN critical vulnerability",
                 tags=["fortinet", "vpn", "rce"])
    ]
    
    for ioc in demo_iocs:
        asyncio.get_event_loop().run_until_complete(create_ioc(ioc)) if asyncio.get_event_loop().is_running() else None


# Inicializar datos demo al cargar el módulo
try:
    import asyncio
    loop = asyncio.new_event_loop()
    for ioc in [
        {"value": "185.234.72.15", "ioc_type": IOCType.IP, "threat_level": ThreatLevel.CRITICAL,
         "source": IOCSource.INVESTIGATION, "case_id": "IR-2025-001",
         "description": "C2 server", "tags": ["c2", "apt"]},
        {"value": "malicious-domain.com", "ioc_type": IOCType.DOMAIN, "threat_level": ThreatLevel.HIGH,
         "source": IOCSource.THREAT_INTEL, "description": "Phishing domain", "tags": ["phishing"]},
        {"value": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
         "ioc_type": IOCType.HASH_SHA256, "threat_level": ThreatLevel.CRITICAL,
         "source": IOCSource.VIRUSTOTAL, "description": "Emotet hash", "tags": ["malware", "emotet"]}
    ]:
        ioc_id = _generate_ioc_id()
        now = datetime.utcnow()
        ioc_data = {
            "id": ioc_id,
            "value": ioc["value"],
            "value_hash": _hash_ioc_value(ioc["value"], ioc["ioc_type"]),
            "ioc_type": ioc["ioc_type"],
            "threat_level": ioc["threat_level"],
            "status": IOCStatus.ACTIVE,
            "source": ioc["source"],
            "case_id": ioc.get("case_id"),
            "description": ioc.get("description"),
            "tags": ioc.get("tags", []),
            "first_seen": now,
            "last_seen": now,
            "expires_at": None,
            "hit_count": 0,
            "enrichment": {},
            "metadata": {},
            "created_by": "system",
            "updated_at": now,
            "confidence_score": 75.0
        }
        _ioc_store[ioc_id] = ioc_data
except:
    pass
