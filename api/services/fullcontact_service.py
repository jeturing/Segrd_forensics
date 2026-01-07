"""
🔍 FullContact API Service - Enriquecimiento de Personas y Empresas
Documentación: https://docs.fullcontact.com/docs/multi-field-request

Endpoints:
- Person Enrich: POST https://api.fullcontact.com/v3/person.enrich
- Company Enrich: POST https://api.fullcontact.com/v3/company.enrich
"""

import os
import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import hashlib

# Importar cache service
from api.services.redis_cache import cache_result

logger = logging.getLogger(__name__)

# =============================================================================
# Configuration
# =============================================================================

FULLCONTACT_API_KEY = os.getenv("FULLCONTACT_API_KEY")
FULLCONTACT_BASE_URL = "https://api.fullcontact.com/v3"

# Rate limiting: 60 segundos window
_last_request_time = 0
_rate_limit_window = 1.0  # 1 segundo entre requests para ser conservador


# =============================================================================
# Helper Functions
# =============================================================================

async def _rate_limit():
    """Aplica rate limiting entre requests"""
    global _last_request_time
    import time
    current = time.time()
    if current - _last_request_time < _rate_limit_window:
        await asyncio.sleep(_rate_limit_window - (current - _last_request_time))
    _last_request_time = time.time()


def _get_headers() -> Dict[str, str]:
    """Genera headers para FullContact API"""
    return {
        "Authorization": f"Bearer {FULLCONTACT_API_KEY}",
        "Content-Type": "application/json"
    }


def _hash_email(email: str) -> str:
    """Genera hash MD5 de email para cache key"""
    return hashlib.md5(email.lower().strip().encode()).hexdigest()


# =============================================================================
# Person Enrichment API
# =============================================================================

@cache_result("fullcontact_person", ttl=86400)  # Cache 24 horas
async def enrich_person_by_email(email: str) -> Dict[str, Any]:
    """
    Enriquece información de una persona por email.
    
    Retorna:
    - fullName: Nombre completo
    - ageRange: Rango de edad
    - gender: Género
    - location: Ubicación
    - title: Cargo actual
    - organization: Empresa actual
    - twitter: URL de Twitter
    - linkedin: URL de LinkedIn
    - bio: Biografía
    - avatar: URL de foto
    - details: Información adicional según bundle habilitado
    """
    if not FULLCONTACT_API_KEY:
        return {
            "success": False,
            "error": "FullContact API key not configured",
            "hint": "Configure FULLCONTACT_API_KEY en .env"
        }
    
    await _rate_limit()
    
    url = f"{FULLCONTACT_BASE_URL}/person.enrich"
    payload = {"email": email.lower().strip()}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers=_get_headers(),
                json=payload,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.info(f"✅ FullContact Person enrichment: {email}")
                    return {
                        "success": True,
                        "email": email,
                        "fullName": data.get("fullName"),
                        "ageRange": data.get("ageRange"),
                        "gender": data.get("gender"),
                        "location": data.get("location"),
                        "title": data.get("title"),
                        "organization": data.get("organization"),
                        "twitter": data.get("twitter"),
                        "linkedin": data.get("linkedin"),
                        "bio": data.get("bio"),
                        "avatar": data.get("avatar"),
                        "details": data.get("details", {}),
                        "enriched_at": datetime.utcnow().isoformat()
                    }
                elif resp.status == 404:
                    return {
                        "success": True,
                        "email": email,
                        "found": False,
                        "message": "No data found for this email"
                    }
                elif resp.status == 401:
                    return {
                        "success": False,
                        "error": "Invalid FullContact API key",
                        "status_code": 401
                    }
                elif resp.status == 429:
                    return {
                        "success": False,
                        "error": "Rate limit exceeded",
                        "status_code": 429,
                        "hint": "Wait before retrying"
                    }
                else:
                    error_text = await resp.text()
                    return {
                        "success": False,
                        "error": f"API error: {error_text}",
                        "status_code": resp.status
                    }
    except asyncio.TimeoutError:
        logger.warning(f"⏱️ FullContact timeout for {email}")
        return {"success": False, "error": "Request timeout"}
    except Exception as e:
        logger.error(f"❌ FullContact error: {e}")
        return {"success": False, "error": str(e)}


@cache_result("fullcontact_person_multi", ttl=86400)  # Cache 24 horas
async def enrich_person_multi_field(
    emails: Optional[List[str]] = None,
    phones: Optional[List[str]] = None,
    name: Optional[Dict[str, str]] = None,
    location: Optional[Dict[str, str]] = None,
    profiles: Optional[List[Dict[str, str]]] = None,
    maids: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Enriquece persona usando múltiples identificadores.
    
    Args:
        emails: Lista de emails (cleartext, MD5 o SHA-256)
        phones: Lista de teléfonos (incluir código país para internacionales)
        name: {"full": "...", "given": "...", "family": "..."}
        location: {"addressLine1": "...", "city": "...", "region": "...", "postalCode": "..."}
        profiles: [{"service": "twitter", "username": "..."}, {"service": "linkedin", "url": "..."}]
        maids: Mobile Advertising IDs
    
    Note: Para usar name/location, ambos deben estar presentes.
    """
    if not FULLCONTACT_API_KEY:
        return {
            "success": False,
            "error": "FullContact API key not configured"
        }
    
    # Construir payload con campos disponibles
    payload = {}
    
    if emails:
        payload["emails"] = [e.lower().strip() for e in emails]
    
    if phones:
        payload["phones"] = phones
    
    if name:
        payload["name"] = name
    
    if location:
        payload["location"] = location
    
    if profiles:
        payload["profiles"] = profiles
    
    if maids:
        payload["maids"] = maids
    
    if not payload:
        return {
            "success": False,
            "error": "At least one identifier is required"
        }
    
    await _rate_limit()
    
    url = f"{FULLCONTACT_BASE_URL}/person.enrich"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers=_get_headers(),
                json=payload,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.info("✅ FullContact Multi-field enrichment successful")
                    return {
                        "success": True,
                        "input": payload,
                        "fullName": data.get("fullName"),
                        "ageRange": data.get("ageRange"),
                        "gender": data.get("gender"),
                        "location": data.get("location"),
                        "title": data.get("title"),
                        "organization": data.get("organization"),
                        "twitter": data.get("twitter"),
                        "linkedin": data.get("linkedin"),
                        "bio": data.get("bio"),
                        "avatar": data.get("avatar"),
                        "details": data.get("details", {}),
                        "enriched_at": datetime.utcnow().isoformat()
                    }
                elif resp.status == 404:
                    return {
                        "success": True,
                        "found": False,
                        "message": "No matching person found"
                    }
                elif resp.status == 400:
                    error_data = await resp.json()
                    return {
                        "success": False,
                        "error": "Invalid request",
                        "details": error_data
                    }
                else:
                    error_text = await resp.text()
                    return {
                        "success": False,
                        "error": f"API error: {error_text}",
                        "status_code": resp.status
                    }
    except Exception as e:
        logger.error(f"❌ FullContact multi-field error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# Company Enrichment API
# =============================================================================

@cache_result("fullcontact_company", ttl=86400)  # Cache 24 horas
async def enrich_company_by_domain(domain: str) -> Dict[str, Any]:
    """
    Enriquece información de una empresa por dominio.
    
    Args:
        domain: Dominio de la empresa (ej: "fullcontact.com")
    
    Retorna:
    - name: Nombre de la empresa
    - location: Ubicación
    - description: Descripción
    - founded: Año de fundación
    - employees: Número de empleados
    - industry: Industria
    - website: Sitio web
    - social: Redes sociales
    - logo: URL del logo
    - keywords: Palabras clave
    """
    if not FULLCONTACT_API_KEY:
        return {
            "success": False,
            "error": "FullContact API key not configured"
        }
    
    # Limpiar dominio
    clean_domain = domain.lower().strip()
    if clean_domain.startswith("http"):
        from urllib.parse import urlparse
        clean_domain = urlparse(clean_domain).netloc
    if clean_domain.startswith("www."):
        clean_domain = clean_domain[4:]
    
    await _rate_limit()
    
    url = f"{FULLCONTACT_BASE_URL}/company.enrich"
    payload = {"domain": clean_domain}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers=_get_headers(),
                json=payload,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.info(f"✅ FullContact Company enrichment: {domain}")
                    return {
                        "success": True,
                        "domain": clean_domain,
                        "name": data.get("name"),
                        "location": data.get("location"),
                        "description": data.get("description") or data.get("bio"),
                        "founded": data.get("founded"),
                        "employees": data.get("employees"),
                        "employeesRange": data.get("employeesRange"),
                        "industry": data.get("category", {}).get("name") if data.get("category") else None,
                        "industries": data.get("industries", []),
                        "website": data.get("website"),
                        "social": {
                            "twitter": data.get("twitter"),
                            "linkedin": data.get("linkedin"),
                            "facebook": data.get("facebook")
                        },
                        "logo": data.get("logo"),
                        "keywords": data.get("keywords", []),
                        "details": data.get("details", {}),
                        "enriched_at": datetime.utcnow().isoformat()
                    }
                elif resp.status == 404:
                    return {
                        "success": True,
                        "domain": clean_domain,
                        "found": False,
                        "message": "No company data found for this domain"
                    }
                else:
                    error_text = await resp.text()
                    return {
                        "success": False,
                        "error": f"API error: {error_text}",
                        "status_code": resp.status
                    }
    except Exception as e:
        logger.error(f"❌ FullContact company error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# Batch Enrichment (para múltiples emails/dominios)
# =============================================================================

async def batch_enrich_persons(emails: List[str], max_concurrent: int = 5) -> Dict[str, Any]:
    """
    Enriquece múltiples emails en batch con concurrencia controlada.
    
    Args:
        emails: Lista de emails a enriquecer
        max_concurrent: Máximo de requests concurrentes
    
    Returns:
        Dict con resultados por email y estadísticas
    """
    if not FULLCONTACT_API_KEY:
        return {
            "success": False,
            "error": "FullContact API key not configured"
        }
    
    logger.info(f"🔄 Starting batch enrichment for {len(emails)} emails")
    
    results = {}
    successful = 0
    failed = 0
    not_found = 0
    
    # Usar semáforo para limitar concurrencia
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def enrich_with_semaphore(email: str):
        async with semaphore:
            return await enrich_person_by_email(email)
    
    # Ejecutar en paralelo con límite
    tasks = [enrich_with_semaphore(email) for email in emails]
    enrichments = await asyncio.gather(*tasks, return_exceptions=True)
    
    for email, result in zip(emails, enrichments):
        if isinstance(result, Exception):
            results[email] = {"success": False, "error": str(result)}
            failed += 1
        elif result.get("success"):
            results[email] = result
            if result.get("found", True):
                successful += 1
            else:
                not_found += 1
        else:
            results[email] = result
            failed += 1
    
    logger.info(f"✅ Batch complete: {successful} enriched, {not_found} not found, {failed} failed")
    
    return {
        "success": True,
        "total": len(emails),
        "enriched": successful,
        "not_found": not_found,
        "failed": failed,
        "results": results,
        "completed_at": datetime.utcnow().isoformat()
    }


async def batch_enrich_companies(domains: List[str], max_concurrent: int = 5) -> Dict[str, Any]:
    """
    Enriquece múltiples dominios de empresas en batch.
    """
    if not FULLCONTACT_API_KEY:
        return {
            "success": False,
            "error": "FullContact API key not configured"
        }
    
    logger.info(f"🔄 Starting batch company enrichment for {len(domains)} domains")
    
    results = {}
    successful = 0
    failed = 0
    not_found = 0
    
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def enrich_with_semaphore(domain: str):
        async with semaphore:
            return await enrich_company_by_domain(domain)
    
    tasks = [enrich_with_semaphore(domain) for domain in domains]
    enrichments = await asyncio.gather(*tasks, return_exceptions=True)
    
    for domain, result in zip(domains, enrichments):
        if isinstance(result, Exception):
            results[domain] = {"success": False, "error": str(result)}
            failed += 1
        elif result.get("success"):
            results[domain] = result
            if result.get("found", True):
                successful += 1
            else:
                not_found += 1
        else:
            results[domain] = result
            failed += 1
    
    return {
        "success": True,
        "total": len(domains),
        "enriched": successful,
        "not_found": not_found,
        "failed": failed,
        "results": results,
        "completed_at": datetime.utcnow().isoformat()
    }


# =============================================================================
# Utility Functions
# =============================================================================

async def check_api_status() -> Dict[str, Any]:
    """Verifica el estado de la API de FullContact"""
    if not FULLCONTACT_API_KEY:
        return {
            "configured": False,
            "status": "not_configured",
            "message": "API key not set"
        }
    
    try:
        # Hacer request de prueba con email conocido
        result = await enrich_person_by_email("test@fullcontact.com")
        if result.get("success") or result.get("found") is not None:
            return {
                "configured": True,
                "status": "operational",
                "message": "FullContact API is working"
            }
        elif "401" in str(result.get("status_code", "")):
            return {
                "configured": True,
                "status": "invalid_key",
                "message": "API key is invalid"
            }
        elif "429" in str(result.get("status_code", "")):
            return {
                "configured": True,
                "status": "rate_limited",
                "message": "Rate limit reached"
            }
        else:
            return {
                "configured": True,
                "status": "unknown",
                "message": result.get("error", "Unknown status")
            }
    except Exception as e:
        return {
            "configured": True,
            "status": "error",
            "message": str(e)
        }


def extract_emails_from_text(text: str) -> List[str]:
    """Extrae emails de un texto para enriquecimiento"""
    import re
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    return list(set(re.findall(email_pattern, text)))


def extract_domains_from_text(text: str) -> List[str]:
    """Extrae dominios de un texto para enriquecimiento"""
    import re
    # Buscar URLs completas y dominios
    url_pattern = r'(?:https?://)?(?:www\.)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
    domains = list(set(re.findall(url_pattern, text)))
    # Filtrar dominios comunes de email que no son empresas
    exclude = {'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'protonmail.com'}
    return [d for d in domains if d.lower() not in exclude]


# =============================================================================
# Forensics Integration
# =============================================================================

async def enrich_investigation_emails(case_id: str, emails: List[str]) -> Dict[str, Any]:
    """
    Enriquece emails encontrados en una investigación forense.
    Útil para identificar a actores de amenazas o víctimas.
    """
    logger.info(f"🔍 Enriching {len(emails)} emails for case {case_id}")
    
    results = await batch_enrich_persons(emails)
    
    # Agregar contexto forense
    enriched_profiles = []
    for email, data in results.get("results", {}).items():
        if data.get("success") and data.get("fullName"):
            enriched_profiles.append({
                "email": email,
                "name": data.get("fullName"),
                "organization": data.get("organization"),
                "title": data.get("title"),
                "location": data.get("location"),
                "social_profiles": {
                    "twitter": data.get("twitter"),
                    "linkedin": data.get("linkedin")
                },
                "risk_indicators": []  # Para futura integración con threat intel
            })
    
    return {
        "case_id": case_id,
        "total_emails": len(emails),
        "enriched_count": len(enriched_profiles),
        "profiles": enriched_profiles,
        "raw_results": results
    }


async def enrich_domains_from_logs(case_id: str, log_text: str) -> Dict[str, Any]:
    """
    Extrae y enriquece dominios de logs de una investigación.
    Útil para identificar C2 servers o infraestructura maliciosa.
    """
    domains = extract_domains_from_text(log_text)
    
    if not domains:
        return {
            "case_id": case_id,
            "message": "No domains found in logs",
            "domains_found": 0
        }
    
    logger.info(f"🔍 Enriching {len(domains)} domains for case {case_id}")
    
    results = await batch_enrich_companies(domains)
    
    return {
        "case_id": case_id,
        "domains_found": len(domains),
        "enriched_count": results.get("enriched", 0),
        "results": results
    }


# =============================================================================
# Export singleton for easy import
# =============================================================================

class FullContactService:
    """Clase singleton para acceso fácil al servicio"""
    
    @staticmethod
    async def enrich_person(email: str) -> Dict[str, Any]:
        return await enrich_person_by_email(email)
    
    @staticmethod
    async def enrich_person_advanced(
        emails: List[str] = None,
        phones: List[str] = None,
        name: Dict[str, str] = None,
        location: Dict[str, str] = None,
        profiles: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        return await enrich_person_multi_field(
            emails=emails,
            phones=phones,
            name=name,
            location=location,
            profiles=profiles
        )
    
    @staticmethod
    async def enrich_company(domain: str) -> Dict[str, Any]:
        return await enrich_company_by_domain(domain)
    
    @staticmethod
    async def batch_persons(emails: List[str]) -> Dict[str, Any]:
        return await batch_enrich_persons(emails)
    
    @staticmethod
    async def batch_companies(domains: List[str]) -> Dict[str, Any]:
        return await batch_enrich_companies(domains)
    
    @staticmethod
    async def check_status() -> Dict[str, Any]:
        return await check_api_status()


fullcontact = FullContactService()
