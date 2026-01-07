"""
🔍 MISP API Routes - Malware Information Sharing Platform Integration
=====================================================================
Endpoints para integración con MISP como fuente de Threat Intelligence.

Endpoints:
- GET  /api/misp/status          - Estado de conexión
- GET  /api/misp/statistics      - Estadísticas de MISP
- POST /api/misp/search          - Buscar IOC
- GET  /api/misp/events          - Listar eventos
- GET  /api/misp/events/{id}     - Obtener evento específico
- GET  /api/misp/feeds           - Listar feeds
- GET  /api/misp/taxonomies      - Listar taxonomías
- GET  /api/misp/galaxies        - Listar galaxies (ATT&CK, etc)
- POST /api/misp/export-case     - Exportar caso a MISP
- POST /api/misp/import-event    - Importar evento a caso
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from api.services.misp_client import (
    get_misp_client
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/misp", tags=["MISP - Threat Intelligence"])


# =============================================================================
# Pydantic Models
# =============================================================================

class MISPSearchRequest(BaseModel):
    """Request para búsqueda de IOC en MISP"""
    value: str = Field(..., description="Valor del IOC a buscar")
    type: Optional[str] = Field(None, description="Tipo de IOC: ip-src, ip-dst, domain, md5, sha256, email, url")
    limit: int = Field(50, ge=1, le=500)


class MISPExportCaseRequest(BaseModel):
    """Request para exportar caso a MISP"""
    case_id: str = Field(..., description="ID del caso a exportar")
    iocs: List[dict] = Field(..., description="Lista de IOCs [{type, value, comment}]")
    event_info: Optional[str] = Field(None, description="Descripción del evento")
    threat_level: int = Field(2, ge=1, le=4, description="1=High, 2=Medium, 3=Low, 4=Undefined")
    tags: Optional[List[str]] = Field(None, description="Tags adicionales")


class MISPImportEventRequest(BaseModel):
    """Request para importar evento MISP a caso"""
    event_id: str = Field(..., description="ID del evento MISP")
    case_id: str = Field(..., description="ID del caso destino")


# =============================================================================
# Status & Statistics
# =============================================================================

@router.get("/status")
async def get_misp_status():
    """
    Verificar estado de conexión con MISP
    
    Retorna información de versión y estado de conexión.
    """
    client = get_misp_client()
    
    if not client.is_configured():
        return {
            "configured": False,
            "connected": False,
            "message": "MISP no configurado. Establece MISP_URL y MISP_API_KEY en variables de entorno",
            "required_env_vars": ["MISP_URL", "MISP_API_KEY"]
        }
    
    result = await client.test_connection()
    
    return {
        "configured": True,
        "connected": result.get("connected", False),
        "version": result.get("version"),
        "url": result.get("url"),
        "error": result.get("error") if not result.get("connected") else None
    }


@router.get("/statistics")
async def get_statistics():
    """
    Obtener estadísticas de MISP
    
    Retorna conteos de eventos, atributos, usuarios, etc.
    """
    client = get_misp_client()
    
    if not client.is_configured():
        raise HTTPException(status_code=503, detail="MISP no configurado")
    
    result = await client.get_statistics()
    
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error", "Error obteniendo estadísticas"))
    
    return result


# =============================================================================
# IOC Search
# =============================================================================

@router.post("/search")
async def search_ioc(request: MISPSearchRequest):
    """
    Buscar un IOC en MISP
    
    Soporta: IP, domain, hash (MD5/SHA1/SHA256), email, URL
    
    Retorna eventos y atributos que contienen el IOC.
    """
    client = get_misp_client()
    
    if not client.is_configured():
        raise HTTPException(status_code=503, detail="MISP no configurado")
    
    logger.info(f"🔍 MISP search: {request.value} (type={request.type})")
    
    result = await client.search_ioc(
        value=request.value,
        ioc_type=request.type,
        limit=request.limit
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error", "Error en búsqueda"))
    
    return result


@router.get("/search/ip/{ip}")
async def search_ip(ip: str, limit: int = Query(50, ge=1, le=200)):
    """Buscar IP en MISP (source y destination)"""
    client = get_misp_client()
    
    if not client.is_configured():
        raise HTTPException(status_code=503, detail="MISP no configurado")
    
    result = await client.search_ip(ip, limit)
    return result


@router.get("/search/domain/{domain}")
async def search_domain(domain: str, limit: int = Query(50, ge=1, le=200)):
    """Buscar dominio en MISP"""
    client = get_misp_client()
    
    if not client.is_configured():
        raise HTTPException(status_code=503, detail="MISP no configurado")
    
    result = await client.search_domain(domain, limit)
    return result


@router.get("/search/hash/{hash_value}")
async def search_hash(hash_value: str, limit: int = Query(50, ge=1, le=200)):
    """Buscar hash (MD5/SHA1/SHA256) en MISP"""
    client = get_misp_client()
    
    if not client.is_configured():
        raise HTTPException(status_code=503, detail="MISP no configurado")
    
    result = await client.search_hash(hash_value, limit)
    return result


@router.get("/search/email/{email}")
async def search_email(email: str, limit: int = Query(50, ge=1, le=200)):
    """Buscar email en MISP"""
    client = get_misp_client()
    
    if not client.is_configured():
        raise HTTPException(status_code=503, detail="MISP no configurado")
    
    result = await client.search_email(email, limit)
    return result


# =============================================================================
# Events
# =============================================================================

@router.get("/events")
async def list_events(
    limit: int = Query(50, ge=1, le=200),
    page: int = Query(1, ge=1),
    from_date: Optional[str] = Query(None, description="Fecha inicio YYYY-MM-DD"),
    to_date: Optional[str] = Query(None, description="Fecha fin YYYY-MM-DD"),
    threat_level: Optional[int] = Query(None, ge=1, le=4, description="1=High, 2=Medium, 3=Low, 4=Undefined"),
    tags: Optional[str] = Query(None, description="Tags separados por coma"),
    published: Optional[bool] = Query(None, description="Solo eventos publicados")
):
    """
    Listar eventos de MISP
    
    Soporta filtros por fecha, nivel de amenaza, tags y estado de publicación.
    """
    client = get_misp_client()
    
    if not client.is_configured():
        raise HTTPException(status_code=503, detail="MISP no configurado")
    
    tags_list = tags.split(",") if tags else None
    
    result = await client.get_events(
        limit=limit,
        page=page,
        from_date=from_date,
        to_date=to_date,
        threat_level=threat_level,
        tags=tags_list,
        published=published
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error", "Error obteniendo eventos"))
    
    return result


@router.get("/events/{event_id}")
async def get_event(event_id: str):
    """
    Obtener evento específico por ID
    
    Incluye todos los atributos y objetos del evento.
    """
    client = get_misp_client()
    
    if not client.is_configured():
        raise HTTPException(status_code=503, detail="MISP no configurado")
    
    result = await client.get_event(event_id)
    
    if not result.get("success"):
        raise HTTPException(status_code=404 if "no encontrado" in str(result.get("error", "")).lower() else 502, 
                          detail=result.get("error", "Error obteniendo evento"))
    
    return result


# =============================================================================
# Feeds
# =============================================================================

@router.get("/feeds")
async def list_feeds():
    """
    Listar feeds configurados en MISP
    
    Retorna información sobre feeds habilitados y su estado.
    """
    client = get_misp_client()
    
    if not client.is_configured():
        raise HTTPException(status_code=503, detail="MISP no configurado")
    
    result = await client.get_feeds()
    
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error", "Error obteniendo feeds"))
    
    return result


@router.post("/feeds/{feed_id}/fetch")
async def fetch_feed(feed_id: int):
    """
    Forzar actualización de un feed específico
    """
    client = get_misp_client()
    
    if not client.is_configured():
        raise HTTPException(status_code=503, detail="MISP no configurado")
    
    result = await client.fetch_feed(feed_id)
    
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error", "Error actualizando feed"))
    
    return {"success": True, "message": f"Feed {feed_id} actualización iniciada"}


# =============================================================================
# Taxonomies & Galaxies
# =============================================================================

@router.get("/taxonomies")
async def list_taxonomies():
    """
    Listar taxonomías disponibles en MISP
    
    Las taxonomías categorizan eventos y atributos.
    """
    client = get_misp_client()
    
    if not client.is_configured():
        raise HTTPException(status_code=503, detail="MISP no configurado")
    
    result = await client.get_taxonomies()
    
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error", "Error obteniendo taxonomías"))
    
    return result


@router.get("/galaxies")
async def list_galaxies():
    """
    Listar galaxies disponibles en MISP
    
    Incluye MITRE ATT&CK, threat actors, malware families, etc.
    """
    client = get_misp_client()
    
    if not client.is_configured():
        raise HTTPException(status_code=503, detail="MISP no configurado")
    
    result = await client.get_galaxies()
    
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error", "Error obteniendo galaxies"))
    
    return result


# =============================================================================
# Case Integration
# =============================================================================

@router.post("/export-case")
async def export_case_to_misp(request: MISPExportCaseRequest):
    """
    Exportar IOCs de un caso a MISP
    
    Crea un nuevo evento en MISP con los IOCs del caso.
    """
    client = get_misp_client()
    
    if not client.is_configured():
        raise HTTPException(status_code=503, detail="MISP no configurado")
    
    logger.info(f"📤 Exportando caso {request.case_id} a MISP ({len(request.iocs)} IOCs)")
    
    result = await client.export_case_to_misp(
        case_id=request.case_id,
        iocs=request.iocs,
        event_info=request.event_info,
        threat_level=request.threat_level,
        tags=request.tags
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error", "Error exportando a MISP"))
    
    logger.info(f"✅ Caso {request.case_id} exportado a MISP: evento {result.get('event_id')}")
    
    return result


@router.post("/import-event")
async def import_event_to_case(request: MISPImportEventRequest):
    """
    Importar atributos de un evento MISP a un caso
    
    Retorna lista de IOCs para agregar al caso.
    """
    client = get_misp_client()
    
    if not client.is_configured():
        raise HTTPException(status_code=503, detail="MISP no configurado")
    
    logger.info(f"📥 Importando evento MISP {request.event_id} a caso {request.case_id}")
    
    result = await client.import_event_to_case(
        event_id=request.event_id,
        case_id=request.case_id
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error", "Error importando de MISP"))
    
    logger.info(f"✅ Evento {request.event_id} importado: {result.get('iocs_count')} IOCs")
    
    return result


# =============================================================================
# Quick Lookups (para integración con otros módulos)
# =============================================================================

@router.get("/lookup/ip/{ip}")
async def quick_lookup_ip(ip: str):
    """
    Búsqueda rápida de IP para integración con otros módulos
    
    Retorna formato simplificado para uso en Attack Graph, Timeline, etc.
    """
    client = get_misp_client()
    
    if not client.is_configured():
        return {
            "found": False,
            "source": "misp",
            "configured": False,
            "ip": ip
        }
    
    result = await client.search_ip(ip, limit=10)
    
    if result.get("success") and result.get("found"):
        # Extraer información más relevante
        events = set()
        tags = set()
        threat_levels = []
        
        for r in result.get("results", []):
            if r.get("event_info"):
                events.add(r["event_info"])
            for tag in r.get("tags", []):
                tags.add(tag)
            if r.get("event_threat_level"):
                threat_levels.append(int(r["event_threat_level"]))
        
        # Calcular nivel de amenaza máximo
        max_threat = min(threat_levels) if threat_levels else 4  # 1=High es el más grave
        
        return {
            "found": True,
            "source": "misp",
            "ip": ip,
            "hits": result.get("count", 0),
            "threat_level": ["", "high", "medium", "low", "undefined"][max_threat],
            "events_summary": list(events)[:5],
            "tags": list(tags)[:10],
            "malicious": max_threat <= 2  # High o Medium = malicious
        }
    
    return {
        "found": False,
        "source": "misp",
        "ip": ip
    }


@router.get("/lookup/domain/{domain}")
async def quick_lookup_domain(domain: str):
    """Búsqueda rápida de dominio para integración"""
    client = get_misp_client()
    
    if not client.is_configured():
        return {"found": False, "source": "misp", "configured": False, "domain": domain}
    
    result = await client.search_domain(domain, limit=10)
    
    if result.get("success") and result.get("found"):
        tags = set()
        for r in result.get("results", []):
            for tag in r.get("tags", []):
                tags.add(tag)
        
        return {
            "found": True,
            "source": "misp",
            "domain": domain,
            "hits": result.get("count", 0),
            "tags": list(tags)[:10],
            "malicious": result.get("count", 0) > 0
        }
    
    return {"found": False, "source": "misp", "domain": domain}
