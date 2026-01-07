"""
🔍 Threat Intelligence API Routes
Endpoints para consultar APIs externas: Shodan, VirusTotal, HIBP, X-Force, etc.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from api.services import threat_intel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/threat-intel", tags=["Threat Intelligence"])


# =============================================================================
# Request Models
# =============================================================================

class IPLookupRequest(BaseModel):
    ip: str = Field(..., description="Dirección IP a consultar")
    sources: Optional[List[str]] = Field(
        default=["shodan", "virustotal", "xforce"],
        description="Fuentes a consultar: shodan, censys, virustotal, xforce"
    )


class EmailCheckRequest(BaseModel):
    email: EmailStr = Field(..., description="Email a verificar")
    check_breaches: bool = Field(default=True, description="Verificar en HaveIBeenPwned")
    discover_domain: bool = Field(default=False, description="Buscar otros emails del dominio")


class PasswordCheckRequest(BaseModel):
    password: str = Field(..., description="Contraseña a verificar (SHA1 k-anonymity)")


class DomainLookupRequest(BaseModel):
    domain: str = Field(..., description="Dominio a consultar")
    dns_history: bool = Field(default=False, description="Incluir historial DNS")
    email_discovery: bool = Field(default=False, description="Descubrir emails del dominio")


class URLScanRequest(BaseModel):
    url: str = Field(..., description="URL a escanear")
    vendor: Optional[str] = Field(default="virustotal", description="Vendor: virustotal")


class FileScanRequest(BaseModel):
    file_path: str = Field(..., description="Ruta del archivo a escanear")
    vendor: Optional[str] = Field(default="virustotal", description="Vendor: virustotal, hybrid_analysis")
    environment_id: Optional[int] = Field(default=120, description="Environment ID para Hybrid Analysis")


class ShodanSearchRequest(BaseModel):
    query: str = Field(..., description="Query Shodan (ej: apache country:ES)")
    limit: int = Field(default=100, description="Máximo de resultados")


class IntelXSearchRequest(BaseModel):
    term: str = Field(..., description="Término a buscar en dark web / breaches")
    maxresults: int = Field(default=100, description="Máximo de resultados")


# =============================================================================
# IP Intelligence Endpoints
# =============================================================================

@router.post("/ip/lookup")
async def ip_lookup(request: IPLookupRequest):
    """
    🔍 Consulta inteligencia de una IP en múltiples fuentes
    
    Soporta:
    - Shodan: Puertos abiertos, servicios, vulnerabilidades
    - Censys: Certificados SSL, servicios
    - VirusTotal: Reputación, detecciones
    - X-Force: Threat score, categorías
    
    Retorna información consolidada de todas las fuentes
    """
    logger.info(f"🔍 IP Lookup: {request.ip} (sources: {request.sources})")
    
    if "all" in request.sources or len(request.sources) > 1:
        # Multi-source enrichment
        result = await threat_intel.multi_source_ip_enrichment(request.ip)
        return result
    
    # Single source
    source = request.sources[0]
    
    if source == "shodan":
        return await threat_intel.shodan_ip_lookup(request.ip)
    elif source == "censys":
        return await threat_intel.censys_ip_lookup(request.ip)
    elif source == "virustotal":
        return await threat_intel.virustotal_ip_report(request.ip)
    elif source == "xforce":
        return await threat_intel.xforce_ip_report(request.ip)
    else:
        raise HTTPException(400, f"Unsupported source: {source}")


@router.post("/shodan/search")
async def shodan_search(request: ShodanSearchRequest):
    """
    🔎 Búsqueda avanzada en Shodan
    
    Ejemplos de queries:
    - apache country:ES
    - product:MySQL port:3306
    - vuln:CVE-2021-44228
    - ssl.cert.subject.cn:*.example.com
    """
    logger.info(f"🔎 Shodan Search: {request.query}")
    return await threat_intel.shodan_search(request.query, request.limit)


# =============================================================================
# Email & Credentials Intelligence
# =============================================================================

@router.post("/email/check")
async def email_check(request: EmailCheckRequest):
    """
    📧 Verifica email en brechas de seguridad y descubre otros emails del dominio
    
    - HaveIBeenPwned: Brechas conocidas
    - Hunter.io: Otros emails del dominio (opcional)
    """
    logger.info(f"📧 Email Check: {request.email}")
    
    results = {
        "email": request.email,
        "timestamp": datetime.now().isoformat()
    }
    
    if request.check_breaches:
        hibp_result = await threat_intel.hibp_check_email(request.email)
        results["breach_check"] = hibp_result
    
    if request.discover_domain:
        domain = request.email.split("@")[1]
        hunter_result = await threat_intel.hunter_domain_search(domain)
        results["domain_emails"] = hunter_result
    
    return results


@router.post("/password/check")
async def password_check(request: PasswordCheckRequest):
    """
    🔐 Verifica si una contraseña está comprometida
    
    Usa k-Anonymity (HIBP Pwned Passwords) - No envía la contraseña completa
    """
    logger.info("🔐 Password Check (k-anonymity)")
    return await threat_intel.hibp_check_password(request.password)


# =============================================================================
# Domain Intelligence
# =============================================================================

@router.post("/domain/lookup")
async def domain_lookup(request: DomainLookupRequest):
    """
    🌐 Consulta información completa de un dominio
    
    - SecurityTrails: DNS, subdomains, historial
    - Hunter.io: Emails asociados
    """
    logger.info(f"🌐 Domain Lookup: {request.domain}")
    
    results = {
        "domain": request.domain,
        "timestamp": datetime.now().isoformat()
    }
    
    # SecurityTrails DNS info
    if request.dns_history:
        st_result = await threat_intel.securitytrails_domain_info(request.domain)
        results["dns_info"] = st_result
    
    # Hunter email discovery
    if request.email_discovery:
        hunter_result = await threat_intel.hunter_domain_search(request.domain)
        results["emails"] = hunter_result
    
    return results


# =============================================================================
# URL & File Scanning
# =============================================================================

@router.post("/url/scan")
async def url_scan(request: URLScanRequest):
    """
    🔗 Escanea una URL en busca de malware/phishing
    
    - VirusTotal: 70+ motores antivirus
    """
    logger.info(f"🔗 URL Scan: {request.url}")
    
    if request.vendor == "virustotal":
        return await threat_intel.virustotal_url_scan(request.url)
    else:
        raise HTTPException(400, f"Unsupported vendor: {request.vendor}")


@router.post("/file/scan")
async def file_scan(request: FileScanRequest):
    """
    📁 Escanea un archivo en sandbox
    
    - VirusTotal: Análisis estático
    - Hybrid Analysis: Análisis dinámico (sandbox)
    """
    logger.info(f"📁 File Scan: {request.file_path}")
    
    import os
    if not os.path.exists(request.file_path):
        raise HTTPException(404, f"File not found: {request.file_path}")
    
    if request.vendor == "virustotal":
        return await threat_intel.virustotal_file_scan(request.file_path)
    elif request.vendor == "hybrid_analysis":
        return await threat_intel.hybrid_analysis_submit_file(request.file_path, request.environment_id)
    else:
        raise HTTPException(400, f"Unsupported vendor: {request.vendor}")


# =============================================================================
# Dark Web & Data Breach Intelligence
# =============================================================================

@router.post("/intelx/search")
async def intelx_search(request: IntelXSearchRequest):
    """
    🕵️ Búsqueda en dark web y data breaches
    
    Intelligence X indexa:
    - Pastes (Pastebin, etc.)
    - Dark web forums
    - Data breaches
    - Leaks
    """
    logger.info(f"🕵️ IntelX Search: {request.term}")
    return await threat_intel.intelx_search(request.term, request.maxresults)


# =============================================================================
# Health Check
# =============================================================================

@router.get("/status")
async def threat_intel_status():
    """
    📊 Estado de las APIs de Threat Intelligence
    
    Muestra qué servicios están configurados
    """
    import os
    
    services = {
        "shodan": bool(os.getenv("SHODAN_API_KEY")),
        "censys": bool(os.getenv("CENSYS_API_ID") and os.getenv("CENSYS_API_SECRET")),
        "virustotal": bool(os.getenv("VT_API_KEY")),
        "hibp": bool(os.getenv("HIBP_API_KEY")),
        "xforce": bool(os.getenv("XFORCE_API_KEY") and os.getenv("XFORCE_API_SECRET")),
        "securitytrails": bool(os.getenv("SECURITYTRAILS_API_KEY")),
        "hunter": bool(os.getenv("HUNTER_API_KEY")),
        "intelx": bool(os.getenv("INTELX_API_KEY")),
        "hybrid_analysis": bool(os.getenv("HYBRID_ANALYSIS_KEY"))
    }
    
    configured_count = sum(services.values())
    total_count = len(services)
    
    return {
        "status": "operational",
        "services": services,
        "configured": f"{configured_count}/{total_count}",
        "percentage": round((configured_count / total_count) * 100, 2)
    }


# =============================================================================
# SOAR Playbooks - Automated Threat Intel Workflows
# =============================================================================

class PlaybookExecutionRequest(BaseModel):
    playbook_name: str = Field(..., description="Nombre del playbook: ip_reputation_analysis, email_compromise_investigation, phishing_url_analysis")
    target: str = Field(..., description="Objetivo del análisis (IP, email, URL)")
    investigation_id: Optional[str] = Field(default=None, description="ID de investigación (se genera automáticamente si no se proporciona)")
    parameters: Optional[Dict[str, Any]] = Field(default={}, description="Parámetros adicionales del playbook")


@router.post("/playbooks/execute")
async def execute_threat_intel_playbook(request: PlaybookExecutionRequest, background_tasks: BackgroundTasks):
    """
    🤖 Ejecuta un playbook SOAR de Threat Intelligence
    
    Playbooks disponibles:
    
    1. **ip_reputation_analysis**: Análisis completo de reputación de IP
       - Consulta: Shodan, VirusTotal, X-Force, Censys
       - Genera: Risk score, indicadores, recomendaciones
       - Target: Dirección IP
    
    2. **email_compromise_investigation**: Investigación de compromiso de email
       - Consulta: HaveIBeenPwned, Intelligence X, Hunter.io
       - Genera: Exposición de datos, brechas, emails relacionados
       - Target: Email address
    
    3. **phishing_url_analysis**: Análisis de URL sospechosa
       - Consulta: VirusTotal, SecurityTrails
       - Genera: Detecciones de malware, indicadores de phishing
       - Target: URL completa
    
    Los playbooks se ejecutan en background y retornan resultados completos
    """
    from api.services.threat_intel_playbooks import execute_playbook
    import uuid
    
    # Generar investigation_id si no se proporciona
    if not request.investigation_id:
        request.investigation_id = f"TI-{uuid.uuid4().hex[:8].upper()}"
    
    logger.info(f"🤖 Executing playbook: {request.playbook_name} for {request.target}")
    
    try:
        # Ejecutar playbook (puede tardar varios segundos debido a rate limits)
        result = await execute_playbook(
            playbook_name=request.playbook_name,
            target=request.target,
            investigation_id=request.investigation_id,
            **request.parameters
        )
        
        return {
            "success": True,
            "playbook": request.playbook_name,
            "investigation_id": request.investigation_id,
            "target": request.target,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
    
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Playbook execution error: {e}", exc_info=True)
        raise HTTPException(500, f"Playbook execution failed: {str(e)}")


@router.get("/playbooks/available")
async def get_available_playbooks():
    """
    📋 Lista playbooks SOAR disponibles
    
    Retorna información detallada de cada playbook:
    - Nombre y descripción
    - Fuentes de datos consultadas
    - Parámetros requeridos
    - Tiempo estimado de ejecución
    """
    playbooks = [
        {
            "id": "ip_reputation_analysis",
            "name": "IP Reputation Analysis",
            "description": "Análisis multi-fuente de reputación de direcciones IP",
            "category": "network_intelligence",
            "sources": ["Shodan", "VirusTotal", "X-Force", "Censys"],
            "required_params": ["ip"],
            "optional_params": [],
            "estimated_duration_seconds": 10,
            "outputs": [
                "risk_score (0-100)",
                "threat_indicators",
                "open_ports",
                "vulnerabilities",
                "recommendations"
            ]
        },
        {
            "id": "email_compromise_investigation",
            "name": "Email Compromise Investigation",
            "description": "Investigación completa de compromiso de credenciales de email",
            "category": "credential_analysis",
            "sources": ["HaveIBeenPwned", "Intelligence X", "Hunter.io"],
            "required_params": ["email"],
            "optional_params": ["check_domain"],
            "estimated_duration_seconds": 15,
            "outputs": [
                "exposure_level",
                "breaches_found",
                "exposed_data_types",
                "dark_web_mentions",
                "domain_emails_at_risk",
                "recommendations"
            ]
        },
        {
            "id": "phishing_url_analysis",
            "name": "Phishing URL Analysis",
            "description": "Análisis de seguridad de URLs sospechosas",
            "category": "web_threat_analysis",
            "sources": ["VirusTotal", "SecurityTrails"],
            "required_params": ["url"],
            "optional_params": [],
            "estimated_duration_seconds": 12,
            "outputs": [
                "threat_level",
                "malware_detections",
                "phishing_indicators",
                "domain_info",
                "recommendations"
            ]
        }
    ]
    
    return {
        "total": len(playbooks),
        "playbooks": playbooks
    }


@router.get("/cache/stats")
async def get_cache_statistics():
    """
    📊 Estadísticas del sistema de cache Redis
    
    Retorna:
    - Estado del cache (enabled/disabled)
    - Total de keys almacenadas
    - Hit rate (% de consultas cacheadas)
    - Memoria utilizada
    - Clientes conectados
    """
    from api.services.redis_cache import get_cache_stats
    
    try:
        stats = await get_cache_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return {
            "enabled": False,
            "error": str(e)
        }


@router.post("/cache/clear")
async def clear_cache(pattern: Optional[str] = "threat_intel:*"):
    """
    🗑️ Limpia el cache Redis
    
    Args:
        pattern: Patrón de keys a eliminar (default: "threat_intel:*")
    
    Ejemplos:
    - "threat_intel:*" - Elimina todo el cache de threat intel
    - "threat_intel:ip:*" - Solo cache de IPs
    - "threat_intel:email:*" - Solo cache de emails
    """
    from api.services.redis_cache import cache_clear_pattern
    
    try:
        deleted = await cache_clear_pattern(pattern)
        return {
            "success": True,
            "pattern": pattern,
            "keys_deleted": deleted,
            "message": f"Cleared {deleted} cache entries"
        }
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(500, f"Cache clear failed: {str(e)}")


# =============================================================================
# Webhook Management
# =============================================================================

@router.get("/webhooks/status")
async def get_webhook_status():
    """
    📡 Estado de webhooks configurados
    
    Retorna:
    - Webhooks habilitados/deshabilitados
    - Webhooks configurados (Slack, Discord, Custom)
    - Estado de cada uno
    """
    import os
    from api.services.webhooks import WEBHOOK_ENABLED
    
    status = {
        "enabled": WEBHOOK_ENABLED,
        "webhooks": {}
    }
    
    # Slack
    slack_url = os.getenv("SLACK_WEBHOOK_URL")
    status["webhooks"]["slack"] = {
        "configured": bool(slack_url),
        "channel": os.getenv("SLACK_CHANNEL", "#security-alerts")
    }
    
    # Discord
    discord_url = os.getenv("DISCORD_WEBHOOK_URL")
    status["webhooks"]["discord"] = {
        "configured": bool(discord_url)
    }
    
    # Custom
    custom_urls = os.getenv("CUSTOM_WEBHOOK_URLS", "").split(",")
    custom_urls = [url.strip() for url in custom_urls if url.strip()]
    status["webhooks"]["custom"] = {
        "configured": len(custom_urls) > 0,
        "count": len(custom_urls)
    }
    
    return status


@router.post("/webhooks/test")
async def test_webhooks():
    """
    🧪 Prueba de webhooks
    
    Envía un mensaje de prueba a todos los webhooks configurados
    para verificar conectividad
    """
    from api.services.webhooks import test_webhooks as run_test
    
    try:
        result = await run_test()
        return result
    except Exception as e:
        logger.error(f"Webhook test error: {e}")
        raise HTTPException(500, f"Webhook test failed: {str(e)}")


class ManualAlertRequest(BaseModel):
    """Request para enviar alerta manual"""
    title: str
    message: str
    threat_level: str = "medium"  # critical, high, medium, low, info
    target: str
    investigation_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    recommendations: Optional[List[str]] = None


@router.post("/webhooks/alert")
async def send_manual_alert(request: ManualAlertRequest):
    """
    🔔 Envía alerta manual a webhooks
    
    Permite enviar alertas personalizadas a todos los webhooks configurados
    Útil para notificaciones de investigaciones manuales
    """
    from api.services.webhooks import WebhookAlert, ThreatLevel, send_threat_alert
    
    try:
        # Crear alerta
        alert = WebhookAlert(
            title=request.title,
            message=request.message,
            threat_level=ThreatLevel(request.threat_level),
            source="Manual Investigation",
            target=request.target,
            investigation_id=request.investigation_id,
            metadata=request.metadata,
            recommendations=request.recommendations
        )
        
        # Enviar a webhooks
        results = await send_threat_alert(alert)
        
        return {
            "success": True,
            "alert_id": alert.alert_id,
            "timestamp": alert.timestamp,
            "webhook_results": results
        }
    
    except ValueError as e:
        raise HTTPException(400, f"Invalid threat level: {str(e)}")
    except Exception as e:
        logger.error(f"Manual alert error: {e}")
        raise HTTPException(500, f"Alert sending failed: {str(e)}")


# =============================================================================
# FullContact - Person & Company Enrichment
# =============================================================================

class PersonEnrichRequest(BaseModel):
    """Request para enriquecimiento de persona"""
    email: EmailStr = Field(..., description="Email de la persona a enriquecer")


class PersonEnrichMultiRequest(BaseModel):
    """Request para enriquecimiento multi-campo de persona"""
    emails: Optional[List[EmailStr]] = Field(None, description="Lista de emails")
    phones: Optional[List[str]] = Field(None, description="Lista de teléfonos (incluir código país)")
    name: Optional[Dict[str, str]] = Field(
        None, 
        description="Nombre: {'full': '...', 'given': '...', 'family': '...'}"
    )
    location: Optional[Dict[str, str]] = Field(
        None,
        description="Ubicación: {'addressLine1': '...', 'city': '...', 'region': '...', 'postalCode': '...'}"
    )
    profiles: Optional[List[Dict[str, str]]] = Field(
        None,
        description="Perfiles sociales: [{'service': 'twitter', 'username': '...'}]"
    )


class CompanyEnrichRequest(BaseModel):
    """Request para enriquecimiento de empresa"""
    domain: str = Field(..., description="Dominio de la empresa (ej: 'fullcontact.com')")


class BatchPersonEnrichRequest(BaseModel):
    """Request para enriquecimiento batch de personas"""
    emails: List[EmailStr] = Field(..., description="Lista de emails a enriquecer (máximo 100)")
    max_concurrent: int = Field(default=5, description="Requests concurrentes (1-10)")


class BatchCompanyEnrichRequest(BaseModel):
    """Request para enriquecimiento batch de empresas"""
    domains: List[str] = Field(..., description="Lista de dominios a enriquecer (máximo 100)")
    max_concurrent: int = Field(default=5, description="Requests concurrentes (1-10)")


class ForensicsEnrichRequest(BaseModel):
    """Request para enriquecer emails de una investigación"""
    case_id: str = Field(..., description="ID del caso de investigación")
    emails: List[EmailStr] = Field(..., description="Emails encontrados en la investigación")


@router.post("/fullcontact/person")
async def enrich_person(request: PersonEnrichRequest):
    """
    👤 Enriquece información de una persona por email
    
    Usa la API de FullContact para obtener:
    - Nombre completo
    - Rango de edad y género
    - Ubicación
    - Cargo y empresa actual
    - Perfiles de Twitter y LinkedIn
    - Biografía y avatar
    
    Útil para:
    - Identificar actores de amenazas
    - Verificar identidades en phishing
    - Enriquecer reportes de incidentes
    """
    from api.services.fullcontact_service import enrich_person_by_email
    
    logger.info(f"👤 FullContact Person Enrich: {request.email}")
    
    result = await enrich_person_by_email(request.email)
    
    if not result.get("success") and "not configured" in str(result.get("error", "")):
        raise HTTPException(503, "FullContact API not configured. Set FULLCONTACT_API_KEY in .env")
    
    return result


@router.post("/fullcontact/person/advanced")
async def enrich_person_advanced(request: PersonEnrichMultiRequest):
    """
    👤 Enriquecimiento avanzado de persona con múltiples identificadores
    
    Permite buscar usando combinaciones de:
    - Emails (cleartext, MD5 o SHA-256)
    - Teléfonos (con código de país para internacionales)
    - Nombre + Dirección (deben ir juntos)
    - Perfiles sociales (Twitter, LinkedIn, etc.)
    
    Cuantos más identificadores, mejor precisión en los resultados.
    """
    from api.services.fullcontact_service import enrich_person_multi_field
    
    logger.info("👤 FullContact Advanced Enrich")
    
    # Validar que al menos un campo está presente
    if not any([request.emails, request.phones, request.name, request.profiles]):
        raise HTTPException(400, "At least one identifier is required (emails, phones, name, or profiles)")
    
    # Validar que name y location van juntos
    if (request.name and not request.location) or (request.location and not request.name):
        raise HTTPException(400, "Name and location must be provided together")
    
    result = await enrich_person_multi_field(
        emails=request.emails,
        phones=request.phones,
        name=request.name,
        location=request.location,
        profiles=request.profiles
    )
    
    return result


@router.post("/fullcontact/company")
async def enrich_company(request: CompanyEnrichRequest):
    """
    🏢 Enriquece información de una empresa por dominio
    
    Retorna:
    - Nombre de la empresa
    - Ubicación y descripción
    - Año de fundación
    - Número de empleados
    - Industria
    - Redes sociales
    - Logo
    
    Útil para:
    - Investigar dominios C2
    - Identificar infraestructura maliciosa
    - Verificar legitimidad de organizaciones
    """
    from api.services.fullcontact_service import enrich_company_by_domain
    
    logger.info(f"🏢 FullContact Company Enrich: {request.domain}")
    
    result = await enrich_company_by_domain(request.domain)
    
    if not result.get("success") and "not configured" in str(result.get("error", "")):
        raise HTTPException(503, "FullContact API not configured. Set FULLCONTACT_API_KEY in .env")
    
    return result


@router.post("/fullcontact/batch/persons")
async def batch_enrich_persons(request: BatchPersonEnrichRequest):
    """
    👥 Enriquecimiento batch de múltiples personas
    
    Procesa hasta 100 emails en paralelo con rate limiting automático.
    Útil para enriquecer listas de emails de investigaciones.
    
    Retorna estadísticas y resultados individuales.
    """
    from api.services.fullcontact_service import batch_enrich_persons
    
    # Validaciones
    if len(request.emails) > 100:
        raise HTTPException(400, "Maximum 100 emails per batch request")
    
    if request.max_concurrent < 1 or request.max_concurrent > 10:
        raise HTTPException(400, "max_concurrent must be between 1 and 10")
    
    logger.info(f"👥 FullContact Batch Persons: {len(request.emails)} emails")
    
    result = await batch_enrich_persons(
        emails=request.emails,
        max_concurrent=request.max_concurrent
    )
    
    return result


@router.post("/fullcontact/batch/companies")
async def batch_enrich_companies(request: BatchCompanyEnrichRequest):
    """
    🏢 Enriquecimiento batch de múltiples empresas
    
    Procesa hasta 100 dominios en paralelo con rate limiting automático.
    Útil para investigar infraestructura o dominios sospechosos.
    
    Retorna estadísticas y resultados individuales.
    """
    from api.services.fullcontact_service import batch_enrich_companies
    
    # Validaciones
    if len(request.domains) > 100:
        raise HTTPException(400, "Maximum 100 domains per batch request")
    
    if request.max_concurrent < 1 or request.max_concurrent > 10:
        raise HTTPException(400, "max_concurrent must be between 1 and 10")
    
    logger.info(f"🏢 FullContact Batch Companies: {len(request.domains)} domains")
    
    result = await batch_enrich_companies(
        domains=request.domains,
        max_concurrent=request.max_concurrent
    )
    
    return result


@router.post("/fullcontact/forensics/enrich-emails")
async def forensics_enrich_emails(request: ForensicsEnrichRequest):
    """
    🔍 Enriquece emails de una investigación forense
    
    Especializado para casos de IR:
    - Enriquece emails encontrados en logs/evidencias
    - Identifica actores de amenazas
    - Genera perfiles de sospechosos
    - Incluye indicadores de riesgo
    
    Los resultados se pueden vincular al caso de investigación.
    """
    from api.services.fullcontact_service import enrich_investigation_emails
    
    if len(request.emails) > 50:
        raise HTTPException(400, "Maximum 50 emails per forensics request")
    
    logger.info(f"🔍 Forensics Email Enrichment: Case {request.case_id}, {len(request.emails)} emails")
    
    result = await enrich_investigation_emails(
        case_id=request.case_id,
        emails=request.emails
    )
    
    return result


@router.get("/fullcontact/status")
async def fullcontact_status():
    """
    📊 Verifica el estado de la API de FullContact
    
    Retorna:
    - configured: Si la API key está configurada
    - status: Estado de la API (operational, invalid_key, rate_limited, error)
    - message: Mensaje descriptivo
    """
    from api.services.fullcontact_service import check_api_status
    
    return await check_api_status()


# =============================================================================
# AbuseIPDB - IP Reputation & Reporting
# =============================================================================

class AbuseIPDBCheckRequest(BaseModel):
    """Request para verificar IP en AbuseIPDB"""
    ip: str = Field(..., description="Dirección IP a verificar")
    max_age_days: int = Field(default=90, description="Máximo de días de reportes (1-365)")
    verbose: bool = Field(default=True, description="Incluir reportes individuales")


class AbuseIPDBCheckBlockRequest(BaseModel):
    """Request para verificar bloque CIDR en AbuseIPDB"""
    network: str = Field(..., description="Bloque CIDR (ej: '192.168.1.0/24', máximo /24)")
    max_age_days: int = Field(default=30, description="Máximo de días de reportes")


class AbuseIPDBReportRequest(BaseModel):
    """Request para reportar IP maliciosa"""
    ip: str = Field(..., description="IP a reportar")
    categories: List[int] = Field(..., description="Categorías de abuso (ej: [18, 22] para SSH brute force)")
    comment: Optional[str] = Field(None, description="Comentario del reporte (máx 1024 chars)")


class AbuseIPDBBlacklistRequest(BaseModel):
    """Request para obtener blacklist de IPs"""
    confidence_minimum: int = Field(default=90, description="Confianza mínima 25-100")
    limit: int = Field(default=1000, description="Número máximo de IPs (máx 10000)")


@router.post("/abuseipdb/check")
async def abuseipdb_check_ip(request: AbuseIPDBCheckRequest):
    """
    🔍 Verifica reputación de IP en AbuseIPDB
    
    Retorna:
    - Confidence score de abuso (0-100%)
    - País y ISP
    - Número de reportes
    - Último reporte
    - Lista de reportes (si verbose=True)
    
    Útil para:
    - Detectar IPs atacantes
    - Validar IPs sospechosas en logs
    - Investigar fuentes de ataques
    """
    from api.services.threat_intel_apis import AbuseIPDBService
    
    logger.info(f"🔍 AbuseIPDB Check: {request.ip}")
    
    service = AbuseIPDBService()
    result = await service.check_ip(
        ip=request.ip,
        max_age_days=request.max_age_days,
        verbose=request.verbose
    )
    
    if not result.get("success") and "not configured" in str(result.get("error", "")):
        raise HTTPException(503, "AbuseIPDB API not configured. Set ABUSEIPDB_API_KEY in .env")
    
    return result


@router.post("/abuseipdb/check-block")
async def abuseipdb_check_block(request: AbuseIPDBCheckBlockRequest):
    """
    🔍 Verifica reputación de bloque CIDR en AbuseIPDB
    
    Retorna lista de IPs reportadas en el bloque con sus scores.
    Máximo bloque permitido: /24 (256 IPs)
    """
    from api.services.threat_intel_apis import AbuseIPDBService
    
    logger.info(f"🔍 AbuseIPDB Check Block: {request.network}")
    
    service = AbuseIPDBService()
    result = await service.check_block(
        network=request.network,
        max_age_days=request.max_age_days
    )
    
    return result


@router.post("/abuseipdb/report")
async def abuseipdb_report_ip(request: AbuseIPDBReportRequest):
    """
    📝 Reporta IP maliciosa a AbuseIPDB
    
    Categorías comunes:
    - 18: Brute-Force
    - 22: SSH
    - 21: Web App Attack
    - 14: Port Scan
    - 15: Hacking
    - 4: DDoS Attack
    - 10: Email Spam
    
    Ver lista completa: https://www.abuseipdb.com/categories
    """
    from api.services.threat_intel_apis import AbuseIPDBService
    
    logger.info(f"📝 AbuseIPDB Report: {request.ip} categories={request.categories}")
    
    service = AbuseIPDBService()
    result = await service.report_ip(
        ip=request.ip,
        categories=request.categories,
        comment=request.comment
    )
    
    return result


@router.post("/abuseipdb/blacklist")
async def abuseipdb_get_blacklist(request: AbuseIPDBBlacklistRequest):
    """
    📋 Obtiene blacklist de IPs más reportadas
    
    Retorna lista de IPs con alta confianza de abuso.
    Útil para generar reglas de firewall o IOCs.
    
    Nota: Requiere suscripción premium para más de 10k IPs
    """
    from api.services.threat_intel_apis import AbuseIPDBService
    
    logger.info(f"📋 AbuseIPDB Blacklist: min_confidence={request.confidence_minimum}, limit={request.limit}")
    
    service = AbuseIPDBService()
    result = await service.get_blacklist(
        confidence_minimum=request.confidence_minimum,
        limit=request.limit
    )
    
    return result


# =============================================================================
# OTX AlienVault - Open Threat Exchange
# =============================================================================

class OTXIndicatorRequest(BaseModel):
    """Request para buscar indicador en OTX"""
    indicator_type: str = Field(..., description="Tipo: IPv4, IPv6, domain, hostname, url, file, CVE")
    indicator: str = Field(..., description="Valor del indicador")
    section: Optional[str] = Field(
        default="general", 
        description="Sección: general, geo, malware, url_list, passive_dns, analysis"
    )


class OTXPulseRequest(BaseModel):
    """Request para obtener detalles de un pulse"""
    pulse_id: str = Field(..., description="ID del pulse en OTX")


class OTXSearchRequest(BaseModel):
    """Request para buscar pulses"""
    query: str = Field(..., description="Término de búsqueda")
    limit: int = Field(default=10, description="Máximo de resultados (1-50)")


@router.post("/otx/indicator")
async def otx_get_indicator(request: OTXIndicatorRequest):
    """
    🔍 Busca indicador de compromiso en OTX AlienVault
    
    Tipos soportados:
    - IPv4/IPv6: Direcciones IP
    - domain/hostname: Dominios
    - url: URLs completas
    - file: Hashes MD5/SHA1/SHA256
    - CVE: Vulnerabilidades (CVE-YYYY-NNNNN)
    
    Secciones disponibles:
    - general: Info general y pulses relacionados
    - geo: Geolocalización (solo IPs)
    - malware: Malware asociado
    - url_list: URLs relacionadas
    - passive_dns: Registros DNS pasivos
    - analysis: Análisis detallado (archivos)
    """
    from api.services.threat_intel_apis import OTXAlienVaultService
    
    logger.info(f"🔍 OTX Indicator: {request.indicator_type}={request.indicator}")
    
    service = OTXAlienVaultService()
    result = await service.get_indicator(
        indicator_type=request.indicator_type,
        indicator=request.indicator,
        section=request.section
    )
    
    if not result.get("success") and "not configured" in str(result.get("error", "")):
        raise HTTPException(503, "OTX API not configured. Set OTX_API_KEY in .env")
    
    return result


@router.post("/otx/pulse")
async def otx_get_pulse(request: OTXPulseRequest):
    """
    📋 Obtiene detalles de un pulse específico de OTX
    
    Retorna:
    - Indicadores del pulse
    - Descripción y tags
    - Referencias
    - Autor
    """
    from api.services.threat_intel_apis import OTXAlienVaultService
    
    logger.info(f"📋 OTX Pulse: {request.pulse_id}")
    
    service = OTXAlienVaultService()
    result = await service.get_pulse(request.pulse_id)
    
    return result


@router.post("/otx/search")
async def otx_search_pulses(request: OTXSearchRequest):
    """
    🔎 Busca pulses en OTX por término
    
    Busca en títulos, descripciones y tags.
    Útil para encontrar inteligencia sobre amenazas específicas.
    """
    from api.services.threat_intel_apis import OTXAlienVaultService
    
    logger.info(f"🔎 OTX Search: {request.query}")
    
    service = OTXAlienVaultService()
    result = await service.search_pulses(
        query=request.query,
        limit=request.limit
    )
    
    return result


@router.get("/otx/subscribed")
async def otx_get_subscribed_pulses(limit: int = 10, page: int = 1):
    """
    📥 Obtiene pulses suscritos en OTX
    
    Retorna los pulses a los que el usuario está suscrito,
    útil para obtener inteligencia curada.
    """
    from api.services.threat_intel_apis import OTXAlienVaultService
    
    logger.info(f"📥 OTX Subscribed Pulses: page={page}, limit={limit}")
    
    service = OTXAlienVaultService()
    result = await service.get_subscribed_pulses(limit=limit, page=page)
    
    return result


# =============================================================================
# URLScan.io - URL Analysis & Scanning
# =============================================================================

class URLScanSubmitRequest(BaseModel):
    """Request para escanear URL"""
    url: str = Field(..., description="URL a escanear")
    visibility: str = Field(default="public", description="Visibilidad: public, unlisted, private")
    tags: Optional[List[str]] = Field(None, description="Tags para el scan")
    custom_agent: Optional[str] = Field(None, description="User-Agent personalizado")


class URLScanResultRequest(BaseModel):
    """Request para obtener resultado de scan"""
    uuid: str = Field(..., description="UUID del scan")


class URLScanSearchRequest(BaseModel):
    """Request para buscar scans"""
    query: str = Field(..., description="Query de búsqueda (ElasticSearch syntax)")
    size: int = Field(default=100, description="Número de resultados (máx 10000)")


@router.post("/urlscan/scan")
async def urlscan_submit_scan(request: URLScanSubmitRequest):
    """
    🔍 Envía URL para análisis en URLScan.io
    
    Retorna:
    - UUID del scan
    - URLs para ver resultados (API y web)
    
    El scan tarda ~10-30 segundos en completarse.
    Use /urlscan/result para obtener resultados.
    
    Visibilidad:
    - public: Visible para todos
    - unlisted: Solo con enlace directo
    - private: Solo para el usuario (requiere cuenta Pro)
    """
    from api.services.threat_intel_apis import URLScanService
    
    logger.info(f"🔍 URLScan Submit: {request.url}")
    
    service = URLScanService()
    result = await service.submit_scan(
        url=request.url,
        visibility=request.visibility,
        tags=request.tags,
        custom_agent=request.custom_agent
    )
    
    if not result.get("success") and "not configured" in str(result.get("error", "")):
        raise HTTPException(503, "URLScan.io API not configured. Set URLSCAN_API_KEY in .env")
    
    return result


@router.post("/urlscan/result")
async def urlscan_get_result(request: URLScanResultRequest):
    """
    📊 Obtiene resultado de scan de URLScan.io
    
    Retorna análisis completo:
    - Screenshot de la página
    - DOM y recursos cargados
    - Certificados SSL
    - Cookies y headers
    - Veredictos de seguridad
    - IPs y dominios contactados
    """
    from api.services.threat_intel_apis import URLScanService
    
    logger.info(f"📊 URLScan Result: {request.uuid}")
    
    service = URLScanService()
    result = await service.get_result(request.uuid)
    
    return result


@router.post("/urlscan/scan-and-wait")
async def urlscan_scan_and_wait(request: URLScanSubmitRequest):
    """
    🔍 Escanea URL y espera resultados (bloquea hasta completar)
    
    Combina submit + polling automático.
    Útil cuando necesitas resultados inmediatos.
    
    Timeout: 60 segundos
    """
    from api.services.threat_intel_apis import URLScanService
    
    logger.info(f"🔍 URLScan Scan+Wait: {request.url}")
    
    service = URLScanService()
    result = await service.submit_and_wait(
        url=request.url,
        visibility=request.visibility,
        tags=request.tags,
        custom_agent=request.custom_agent,
        timeout=60
    )
    
    return result


@router.post("/urlscan/search")
async def urlscan_search(request: URLScanSearchRequest):
    """
    🔎 Busca scans en URLScan.io
    
    Usa sintaxis ElasticSearch:
    - domain:example.com
    - ip:1.2.3.4
    - page.url:*phishing*
    - filename:malware.exe
    - hash:sha256_hash
    - date:>now-7d
    
    Ejemplos:
    - domain:example.com AND date:>now-30d
    - filename:*.js AND page.domain:suspicious.com
    """
    from api.services.threat_intel_apis import URLScanService
    
    logger.info(f"🔎 URLScan Search: {request.query}")
    
    service = URLScanService()
    result = await service.search_scans(
        query=request.query,
        size=request.size
    )
    
    return result


# =============================================================================
# ThreatCrowd - Crowdsourced Threat Intelligence (No Auth Required)
# =============================================================================

class ThreatCrowdSearchRequest(BaseModel):
    """Request para buscar en ThreatCrowd"""
    search_type: str = Field(..., description="Tipo: ip, domain, email, antivirus, file")
    value: str = Field(..., description="Valor a buscar")


@router.post("/threatcrowd/search")
async def threatcrowd_search(request: ThreatCrowdSearchRequest):
    """
    🔍 Busca inteligencia crowdsourced en ThreatCrowd
    
    NO requiere API key - es público y gratuito.
    
    Tipos de búsqueda:
    - ip: Dominios asociados, resoluciones, malware
    - domain: IPs, subdominios, emails, hashes
    - email: Dominios asociados
    - antivirus: Hashes detectados por AV
    - file: Info de hashes MD5/SHA1
    
    Nota: Rate limit de 1 request por 10 segundos
    """
    from api.services.threat_intel_apis import ThreatCrowdService
    
    logger.info(f"🔍 ThreatCrowd Search: {request.search_type}={request.value}")
    
    service = ThreatCrowdService()
    
    if request.search_type == "ip":
        result = await service.search_ip(request.value)
    elif request.search_type == "domain":
        result = await service.search_domain(request.value)
    elif request.search_type == "email":
        result = await service.search_email(request.value)
    elif request.search_type == "antivirus":
        result = await service.search_antivirus(request.value)
    elif request.search_type == "file":
        result = await service.search_hash(request.value)
    else:
        raise HTTPException(400, f"Invalid search type: {request.search_type}. Use: ip, domain, email, antivirus, file")
    
    return result


@router.post("/threatcrowd/ip")
async def threatcrowd_search_ip(ip: str):
    """
    🔍 Busca IP en ThreatCrowd
    
    Retorna: Dominios resueltos, hashes de malware, votación de la comunidad
    """
    from api.services.threat_intel_apis import ThreatCrowdService
    
    service = ThreatCrowdService()
    return await service.search_ip(ip)


@router.post("/threatcrowd/domain")
async def threatcrowd_search_domain(domain: str):
    """
    🔍 Busca dominio en ThreatCrowd
    
    Retorna: IPs, subdominios, emails, hashes relacionados
    """
    from api.services.threat_intel_apis import ThreatCrowdService
    
    service = ThreatCrowdService()
    return await service.search_domain(domain)


# =============================================================================
# Threat Intel APIs Status
# =============================================================================

@router.get("/apis/status")
async def get_threat_intel_apis_status():
    """
    📊 Estado de todas las APIs de Threat Intelligence
    
    Muestra qué servicios están configurados y operativos
    """
    import os
    
    services = {
        # APIs existentes
        "shodan": bool(os.getenv("SHODAN_API_KEY")),
        "censys": bool(os.getenv("CENSYS_API_ID") and os.getenv("CENSYS_API_SECRET")),
        "virustotal": bool(os.getenv("VT_API_KEY")),
        "hibp": bool(os.getenv("HIBP_API_KEY")),
        "xforce": bool(os.getenv("XFORCE_API_KEY") and os.getenv("XFORCE_API_SECRET")),
        "securitytrails": bool(os.getenv("SECURITYTRAILS_API_KEY")),
        "hunter": bool(os.getenv("HUNTER_API_KEY")),
        "intelx": bool(os.getenv("INTELX_API_KEY")),
        "hybrid_analysis": bool(os.getenv("HYBRID_ANALYSIS_KEY")),
        "fullcontact": bool(os.getenv("FULLCONTACT_API_KEY")),
        # Nuevas APIs
        "abuseipdb": bool(os.getenv("ABUSEIPDB_API_KEY")),
        "otx_alienvault": bool(os.getenv("OTX_API_KEY")),
        "urlscan": bool(os.getenv("URLSCAN_API_KEY")),
        "threatcrowd": True,  # No requiere API key
    }
    
    configured_count = sum(services.values())
    total_count = len(services)
    
    return {
        "status": "operational",
        "services": services,
        "configured": f"{configured_count}/{total_count}",
        "percentage": round((configured_count / total_count) * 100, 2),
        "note": "ThreatCrowd is free and doesn't require an API key"
    }


