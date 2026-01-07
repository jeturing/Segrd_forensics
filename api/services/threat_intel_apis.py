"""
🔍 Threat Intelligence APIs - Servicios de enriquecimiento externos
Implementaciones reales de:
- AbuseIPDB: Reportes de IPs maliciosas
- OTX AlienVault: Open Threat Exchange
- URLScan.io: Análisis de URLs
"""

import os
import asyncio
import aiohttp
import logging
from typing import Dict, Any
from datetime import datetime

from api.services.redis_cache import cache_result

logger = logging.getLogger(__name__)

# =============================================================================
# API Configuration
# =============================================================================

ABUSEIPDB_API_KEY = os.getenv("ABUSEIPDB_API_KEY")
OTX_API_KEY = os.getenv("OTX_API_KEY")
URLSCAN_API_KEY = os.getenv("URLSCAN_API_KEY")

# Rate limiting globals
_last_request_times = {
    "abuseipdb": 0,
    "otx": 0,
    "urlscan": 0,
}
_rate_limits = {
    "abuseipdb": 1.0,  # 1 segundo entre requests
    "otx": 0.5,        # 500ms entre requests
    "urlscan": 2.0,    # 2 segundos entre requests (rate limit estricto)
}


async def _rate_limit(service: str):
    """Aplica rate limiting entre requests"""
    import time
    current = time.time()
    last = _last_request_times.get(service, 0)
    limit = _rate_limits.get(service, 1.0)
    
    if current - last < limit:
        await asyncio.sleep(limit - (current - last))
    
    _last_request_times[service] = time.time()


# =============================================================================
# AbuseIPDB - IP Reputation and Abuse Reports
# https://docs.abuseipdb.com/
# =============================================================================

ABUSEIPDB_BASE_URL = "https://api.abuseipdb.com/api/v2"

# Categorías de abuso de AbuseIPDB
ABUSEIPDB_CATEGORIES = {
    1: "DNS Compromise",
    2: "DNS Poisoning", 
    3: "Fraud Orders",
    4: "DDoS Attack",
    5: "FTP Brute-Force",
    6: "Ping of Death",
    7: "Phishing",
    8: "Fraud VoIP",
    9: "Open Proxy",
    10: "Web Spam",
    11: "Email Spam",
    12: "Blog Spam",
    13: "VPN IP",
    14: "Port Scan",
    15: "Hacking",
    16: "SQL Injection",
    17: "Spoofing",
    18: "Brute-Force",
    19: "Bad Web Bot",
    20: "Exploited Host",
    21: "Web App Attack",
    22: "SSH",
    23: "IoT Targeted",
}


@cache_result("abuseipdb_check", ttl=3600)  # Cache 1 hora
async def abuseipdb_check_ip(ip: str, max_age_days: int = 90) -> Dict[str, Any]:
    """
    Verifica reputación de una IP en AbuseIPDB.
    
    Args:
        ip: Dirección IP a verificar
        max_age_days: Días hacia atrás para buscar reportes (máx 365)
    
    Returns:
        - abuseConfidenceScore: 0-100 (qué tan probable es que sea maliciosa)
        - countryCode: País de origen
        - usageType: Tipo de uso (ISP, Hosting, etc.)
        - isp: Proveedor de servicios
        - domain: Dominio asociado
        - totalReports: Número total de reportes
        - lastReportedAt: Última vez reportada
    """
    if not ABUSEIPDB_API_KEY:
        return {
            "success": False,
            "error": "AbuseIPDB API key not configured",
            "hint": "Set ABUSEIPDB_API_KEY in .env"
        }
    
    await _rate_limit("abuseipdb")
    
    url = f"{ABUSEIPDB_BASE_URL}/check"
    params = {
        "ipAddress": ip,
        "maxAgeInDays": str(min(max_age_days, 365)),
        "verbose": ""  # Incluye comentarios de reportes
    }
    headers = {
        "Accept": "application/json",
        "Key": ABUSEIPDB_API_KEY
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, 
                params=params, 
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    data = result.get("data", {})
                    
                    # Procesar categorías de los reportes
                    reports = data.get("reports", [])
                    categories_found = set()
                    for report in reports[:10]:  # Últimos 10 reportes
                        for cat_id in report.get("categories", []):
                            categories_found.add(ABUSEIPDB_CATEGORIES.get(cat_id, f"Unknown ({cat_id})"))
                    
                    logger.info(f"✅ AbuseIPDB check: {ip} - Score: {data.get('abuseConfidenceScore')}")
                    
                    return {
                        "success": True,
                        "ip": data.get("ipAddress"),
                        "abuseConfidenceScore": data.get("abuseConfidenceScore", 0),
                        "isPublic": data.get("isPublic"),
                        "ipVersion": data.get("ipVersion"),
                        "isWhitelisted": data.get("isWhitelisted"),
                        "countryCode": data.get("countryCode"),
                        "countryName": data.get("countryName"),
                        "usageType": data.get("usageType"),
                        "isp": data.get("isp"),
                        "domain": data.get("domain"),
                        "hostnames": data.get("hostnames", []),
                        "totalReports": data.get("totalReports", 0),
                        "numDistinctUsers": data.get("numDistinctUsers", 0),
                        "lastReportedAt": data.get("lastReportedAt"),
                        "categories": list(categories_found),
                        "isTor": data.get("isTor", False),
                        "recentReports": [
                            {
                                "reportedAt": r.get("reportedAt"),
                                "comment": r.get("comment", "")[:200],
                                "categories": [ABUSEIPDB_CATEGORIES.get(c, str(c)) for c in r.get("categories", [])]
                            }
                            for r in reports[:5]
                        ],
                        "riskLevel": _calculate_risk_level(data.get("abuseConfidenceScore", 0)),
                        "enriched_at": datetime.utcnow().isoformat()
                    }
                elif resp.status == 401:
                    return {"success": False, "error": "Invalid API key", "status_code": 401}
                elif resp.status == 429:
                    return {"success": False, "error": "Rate limit exceeded", "status_code": 429}
                else:
                    error_text = await resp.text()
                    return {"success": False, "error": f"API error: {error_text}", "status_code": resp.status}
                    
    except asyncio.TimeoutError:
        return {"success": False, "error": "Request timeout"}
    except Exception as e:
        logger.error(f"❌ AbuseIPDB error: {e}")
        return {"success": False, "error": str(e)}


def _calculate_risk_level(score: int) -> str:
    """Calcula nivel de riesgo basado en score de AbuseIPDB"""
    if score >= 90:
        return "critical"
    elif score >= 70:
        return "high"
    elif score >= 40:
        return "medium"
    elif score >= 10:
        return "low"
    else:
        return "safe"


@cache_result("abuseipdb_check_block", ttl=3600)
async def abuseipdb_check_block(network: str, max_age_days: int = 15) -> Dict[str, Any]:
    """
    Verifica un bloque CIDR en AbuseIPDB.
    
    Args:
        network: Bloque CIDR (ej: "192.168.1.0/24")
        max_age_days: Días hacia atrás (máx 365)
    """
    if not ABUSEIPDB_API_KEY:
        return {"success": False, "error": "AbuseIPDB API key not configured"}
    
    await _rate_limit("abuseipdb")
    
    url = f"{ABUSEIPDB_BASE_URL}/check-block"
    params = {
        "network": network,
        "maxAgeInDays": str(min(max_age_days, 365))
    }
    headers = {
        "Accept": "application/json",
        "Key": ABUSEIPDB_API_KEY
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    data = result.get("data", {})
                    
                    reported_ips = data.get("reportedAddress", [])
                    
                    return {
                        "success": True,
                        "network": data.get("networkAddress"),
                        "netmask": data.get("netmask"),
                        "minAddress": data.get("minAddress"),
                        "maxAddress": data.get("maxAddress"),
                        "numPossibleHosts": data.get("numPossibleHosts"),
                        "addressSpaceDesc": data.get("addressSpaceDesc"),
                        "reportedCount": len(reported_ips),
                        "reportedAddresses": [
                            {
                                "ip": addr.get("ipAddress"),
                                "abuseScore": addr.get("abuseConfidenceScore"),
                                "countryCode": addr.get("countryCode"),
                                "numReports": addr.get("numReports")
                            }
                            for addr in reported_ips[:20]  # Limitar a 20
                        ],
                        "enriched_at": datetime.utcnow().isoformat()
                    }
                else:
                    return {"success": False, "error": await resp.text(), "status_code": resp.status}
                    
    except Exception as e:
        logger.error(f"❌ AbuseIPDB check-block error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# OTX AlienVault - Open Threat Exchange
# https://otx.alienvault.com/api
# =============================================================================

OTX_BASE_URL = "https://otx.alienvault.com/api/v1"


@cache_result("otx_indicator", ttl=3600)
async def otx_get_indicator(indicator_type: str, indicator: str) -> Dict[str, Any]:
    """
    Obtiene información de un indicador en OTX AlienVault.
    
    Args:
        indicator_type: Tipo de indicador (IPv4, IPv6, domain, hostname, url, FileHash-MD5, FileHash-SHA1, FileHash-SHA256, CVE)
        indicator: Valor del indicador
    
    Returns:
        - pulses: Pulsos asociados al indicador
        - general: Información general
        - geo: Información geográfica (para IPs)
        - malware: Muestras de malware asociadas
        - url_list: URLs asociadas
    """
    if not OTX_API_KEY:
        return {
            "success": False,
            "error": "OTX API key not configured",
            "hint": "Set OTX_API_KEY in .env. Get free key at https://otx.alienvault.com/"
        }
    
    # Mapear tipos de indicadores
    type_map = {
        "ip": "IPv4",
        "ipv4": "IPv4",
        "ipv6": "IPv6",
        "domain": "domain",
        "hostname": "hostname",
        "url": "url",
        "hash_md5": "FileHash-MD5",
        "hash_sha1": "FileHash-SHA1",
        "hash_sha256": "FileHash-SHA256",
        "cve": "CVE"
    }
    
    otx_type = type_map.get(indicator_type.lower(), indicator_type)
    
    await _rate_limit("otx")
    
    # Obtener información general del indicador
    sections = ["general", "geo", "malware", "url_list", "passive_dns"]
    results = {}
    
    headers = {
        "X-OTX-API-KEY": OTX_API_KEY,
        "Accept": "application/json"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            # Consultar sección general primero
            general_url = f"{OTX_BASE_URL}/indicators/{otx_type}/{indicator}/general"
            
            async with session.get(general_url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    results["general"] = await resp.json()
                elif resp.status == 404:
                    return {
                        "success": True,
                        "found": False,
                        "indicator": indicator,
                        "type": otx_type,
                        "message": "Indicator not found in OTX"
                    }
                elif resp.status == 403:
                    return {"success": False, "error": "Invalid API key or access denied"}
                else:
                    return {"success": False, "error": f"API error: {resp.status}"}
            
            # Consultar otras secciones si está disponible
            if otx_type in ["IPv4", "IPv6", "domain", "hostname"]:
                for section in ["geo", "malware", "url_list"]:
                    await _rate_limit("otx")
                    section_url = f"{OTX_BASE_URL}/indicators/{otx_type}/{indicator}/{section}"
                    try:
                        async with session.get(section_url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                            if resp.status == 200:
                                results[section] = await resp.json()
                    except:
                        pass
        
        general = results.get("general", {})
        geo = results.get("geo", {})
        malware = results.get("malware", {})
        url_list = results.get("url_list", {})
        
        # Procesar pulsos asociados
        pulses = general.get("pulse_info", {}).get("pulses", [])
        
        logger.info(f"✅ OTX lookup: {indicator} - {len(pulses)} pulses found")
        
        return {
            "success": True,
            "found": True,
            "indicator": indicator,
            "type": otx_type,
            "pulse_count": len(pulses),
            "pulses": [
                {
                    "id": p.get("id"),
                    "name": p.get("name"),
                    "description": p.get("description", "")[:300],
                    "author": p.get("author_name"),
                    "created": p.get("created"),
                    "modified": p.get("modified"),
                    "tags": p.get("tags", [])[:10],
                    "targeted_countries": p.get("targeted_countries", []),
                    "malware_families": p.get("malware_families", []),
                    "attack_ids": p.get("attack_ids", [])[:5],
                    "references": p.get("references", [])[:5]
                }
                for p in pulses[:10]  # Limitar a 10 pulsos
            ],
            "validation": general.get("validation", []),
            "asn": general.get("asn"),
            "country_code": general.get("country_code") or geo.get("country_code"),
            "country_name": general.get("country_name") or geo.get("country_name"),
            "city": geo.get("city"),
            "region": geo.get("region"),
            "latitude": geo.get("latitude"),
            "longitude": geo.get("longitude"),
            "malware_samples": [
                {
                    "hash": m.get("hash"),
                    "detections": m.get("detections", {})
                }
                for m in malware.get("data", [])[:5]
            ],
            "related_urls": [
                {
                    "url": u.get("url"),
                    "domain": u.get("domain"),
                    "result": u.get("result", {})
                }
                for u in url_list.get("url_list", [])[:10]
            ],
            "is_malicious": len(pulses) > 0,
            "threat_score": min(100, len(pulses) * 10),  # Score simple basado en pulsos
            "enriched_at": datetime.utcnow().isoformat()
        }
        
    except asyncio.TimeoutError:
        return {"success": False, "error": "Request timeout"}
    except Exception as e:
        logger.error(f"❌ OTX error: {e}")
        return {"success": False, "error": str(e)}


@cache_result("otx_pulses", ttl=1800)  # Cache 30 min
async def otx_get_subscribed_pulses(limit: int = 50) -> Dict[str, Any]:
    """
    Obtiene los últimos pulsos de las subscripciones del usuario.
    """
    if not OTX_API_KEY:
        return {"success": False, "error": "OTX API key not configured"}
    
    await _rate_limit("otx")
    
    url = f"{OTX_BASE_URL}/pulses/subscribed"
    params = {"limit": limit}
    headers = {
        "X-OTX-API-KEY": OTX_API_KEY,
        "Accept": "application/json"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    pulses = data.get("results", [])
                    
                    return {
                        "success": True,
                        "count": len(pulses),
                        "pulses": [
                            {
                                "id": p.get("id"),
                                "name": p.get("name"),
                                "description": p.get("description", "")[:200],
                                "author": p.get("author_name"),
                                "created": p.get("created"),
                                "indicator_count": len(p.get("indicators", [])),
                                "tags": p.get("tags", [])[:5]
                            }
                            for p in pulses
                        ]
                    }
                else:
                    return {"success": False, "error": await resp.text()}
                    
    except Exception as e:
        logger.error(f"❌ OTX pulses error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# URLScan.io - URL Analysis
# https://urlscan.io/docs/api/
# =============================================================================

URLSCAN_BASE_URL = "https://urlscan.io/api/v1"


async def urlscan_submit(url: str, visibility: str = "unlisted") -> Dict[str, Any]:
    """
    Envía una URL para análisis en URLScan.io.
    
    Args:
        url: URL a analizar
        visibility: Visibilidad del scan (public, unlisted, private)
    
    Returns:
        - uuid: ID del scan para consultar resultados
        - result: URL de resultados
        - api: URL de API para resultados
    """
    if not URLSCAN_API_KEY:
        return {
            "success": False,
            "error": "URLScan API key not configured",
            "hint": "Set URLSCAN_API_KEY in .env. Get free key at https://urlscan.io/"
        }
    
    await _rate_limit("urlscan")
    
    endpoint = f"{URLSCAN_BASE_URL}/scan/"
    headers = {
        "API-Key": URLSCAN_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "url": url,
        "visibility": visibility
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                endpoint, 
                headers=headers, 
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.info(f"✅ URLScan submitted: {url} -> {data.get('uuid')}")
                    
                    return {
                        "success": True,
                        "message": data.get("message"),
                        "uuid": data.get("uuid"),
                        "url": url,
                        "result_url": data.get("result"),
                        "api_url": data.get("api"),
                        "visibility": data.get("visibility"),
                        "submitted_at": datetime.utcnow().isoformat()
                    }
                elif resp.status == 400:
                    error_data = await resp.json()
                    return {
                        "success": False,
                        "error": error_data.get("message", "Bad request"),
                        "description": error_data.get("description", "")
                    }
                elif resp.status == 401:
                    return {"success": False, "error": "Invalid API key"}
                elif resp.status == 429:
                    return {"success": False, "error": "Rate limit exceeded. Wait before retrying."}
                else:
                    return {"success": False, "error": f"API error: {resp.status}"}
                    
    except Exception as e:
        logger.error(f"❌ URLScan submit error: {e}")
        return {"success": False, "error": str(e)}


@cache_result("urlscan_result", ttl=3600)
async def urlscan_get_result(uuid: str) -> Dict[str, Any]:
    """
    Obtiene los resultados de un scan de URLScan.io.
    
    Args:
        uuid: ID del scan obtenido al enviar
    
    Returns:
        - verdicts: Veredictos de seguridad
        - page: Información de la página
        - lists: Listas de IPs, dominios, URLs, etc.
    """
    if not URLSCAN_API_KEY:
        return {"success": False, "error": "URLScan API key not configured"}
    
    endpoint = f"{URLSCAN_BASE_URL}/result/{uuid}/"
    headers = {
        "API-Key": URLSCAN_API_KEY,
        "Accept": "application/json"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(endpoint, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    task = data.get("task", {})
                    page = data.get("page", {})
                    verdicts = data.get("verdicts", {})
                    lists = data.get("lists", {})
                    stats = data.get("stats", {})
                    
                    return {
                        "success": True,
                        "uuid": uuid,
                        "url": task.get("url"),
                        "domain": task.get("domain"),
                        "time": task.get("time"),
                        "page": {
                            "url": page.get("url"),
                            "domain": page.get("domain"),
                            "ip": page.get("ip"),
                            "country": page.get("country"),
                            "city": page.get("city"),
                            "server": page.get("server"),
                            "asn": page.get("asn"),
                            "asnname": page.get("asnname"),
                            "title": page.get("title"),
                            "status": page.get("status")
                        },
                        "verdicts": {
                            "overall": verdicts.get("overall", {}),
                            "urlscan": verdicts.get("urlscan", {}),
                            "engines": verdicts.get("engines", {}),
                            "community": verdicts.get("community", {})
                        },
                        "is_malicious": verdicts.get("overall", {}).get("malicious", False),
                        "malicious_score": verdicts.get("overall", {}).get("score", 0),
                        "categories": verdicts.get("overall", {}).get("categories", []),
                        "brands": verdicts.get("overall", {}).get("brands", []),
                        "stats": {
                            "requests": stats.get("uniqCountries", 0),
                            "ips": stats.get("uniqIPs", 0),
                            "countries": stats.get("uniqCountries", 0),
                            "data_length": stats.get("dataLength", 0)
                        },
                        "lists": {
                            "ips": lists.get("ips", [])[:20],
                            "domains": lists.get("domains", [])[:20],
                            "urls": lists.get("urls", [])[:10],
                            "certificates": lists.get("certificates", [])[:5],
                            "hashes": lists.get("hashes", [])[:10]
                        },
                        "screenshot_url": f"https://urlscan.io/screenshots/{uuid}.png",
                        "result_url": f"https://urlscan.io/result/{uuid}/",
                        "enriched_at": datetime.utcnow().isoformat()
                    }
                elif resp.status == 404:
                    return {
                        "success": False,
                        "error": "Scan not found or still processing",
                        "hint": "Wait 30+ seconds after submission and retry"
                    }
                elif resp.status == 410:
                    return {"success": False, "error": "Scan result has been deleted"}
                else:
                    return {"success": False, "error": f"API error: {resp.status}"}
                    
    except Exception as e:
        logger.error(f"❌ URLScan result error: {e}")
        return {"success": False, "error": str(e)}


async def urlscan_scan_and_wait(url: str, visibility: str = "unlisted", timeout: int = 60) -> Dict[str, Any]:
    """
    Envía URL para análisis y espera los resultados.
    
    Args:
        url: URL a analizar
        visibility: Visibilidad del scan
        timeout: Tiempo máximo de espera en segundos
    
    Returns:
        Resultados completos del scan
    """
    # Primero enviar la URL
    submit_result = await urlscan_submit(url, visibility)
    
    if not submit_result.get("success"):
        return submit_result
    
    uuid = submit_result.get("uuid")
    
    # Esperar mínimo 15 segundos
    await asyncio.sleep(15)
    
    # Intentar obtener resultados con reintentos
    start_time = datetime.utcnow()
    max_attempts = timeout // 5
    
    for attempt in range(max_attempts):
        result = await urlscan_get_result(uuid)
        
        if result.get("success"):
            return result
        
        if "still processing" in str(result.get("error", "")):
            await asyncio.sleep(5)
        else:
            return result
    
    return {
        "success": False,
        "error": "Timeout waiting for scan results",
        "uuid": uuid,
        "hint": f"Check results later at https://urlscan.io/result/{uuid}/"
    }


@cache_result("urlscan_search", ttl=1800)
async def urlscan_search(query: str, size: int = 50) -> Dict[str, Any]:
    """
    Busca scans existentes en URLScan.io.
    
    Args:
        query: Query ElasticSearch (ej: "domain:example.com", "ip:1.2.3.4")
        size: Número de resultados (máx 10000)
    
    Returns:
        Lista de scans que coinciden con la búsqueda
    """
    if not URLSCAN_API_KEY:
        return {"success": False, "error": "URLScan API key not configured"}
    
    await _rate_limit("urlscan")
    
    endpoint = f"{URLSCAN_BASE_URL}/search/"
    params = {
        "q": query,
        "size": min(size, 100)
    }
    headers = {
        "API-Key": URLSCAN_API_KEY,
        "Accept": "application/json"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(endpoint, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results = data.get("results", [])
                    
                    logger.info(f"✅ URLScan search: {query} - {len(results)} results")
                    
                    return {
                        "success": True,
                        "total": data.get("total", len(results)),
                        "took": data.get("took"),
                        "has_more": data.get("has_more", False),
                        "results": [
                            {
                                "uuid": r.get("_id"),
                                "url": r.get("page", {}).get("url"),
                                "domain": r.get("page", {}).get("domain"),
                                "ip": r.get("page", {}).get("ip"),
                                "country": r.get("page", {}).get("country"),
                                "server": r.get("page", {}).get("server"),
                                "title": r.get("page", {}).get("title"),
                                "status": r.get("page", {}).get("status"),
                                "is_malicious": r.get("verdicts", {}).get("overall", {}).get("malicious", False),
                                "score": r.get("verdicts", {}).get("overall", {}).get("score", 0),
                                "task_time": r.get("task", {}).get("time"),
                                "result_url": f"https://urlscan.io/result/{r.get('_id')}/"
                            }
                            for r in results
                        ]
                    }
                elif resp.status == 400:
                    return {"success": False, "error": "Invalid search query"}
                else:
                    return {"success": False, "error": f"API error: {resp.status}"}
                    
    except Exception as e:
        logger.error(f"❌ URLScan search error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# API Status Checks
# =============================================================================

async def check_all_api_status() -> Dict[str, Any]:
    """Verifica el estado de todas las APIs"""
    status = {}
    
    # AbuseIPDB
    status["abuseipdb"] = {
        "configured": bool(ABUSEIPDB_API_KEY),
        "service_url": "https://www.abuseipdb.com/account/api"
    }
    
    # OTX AlienVault
    status["otx"] = {
        "configured": bool(OTX_API_KEY),
        "service_url": "https://otx.alienvault.com/api"
    }
    
    # URLScan
    status["urlscan"] = {
        "configured": bool(URLSCAN_API_KEY),
        "service_url": "https://urlscan.io/user/apikeys"
    }
    
    return status


# =============================================================================
# Service Class for easy import
# =============================================================================

class ThreatIntelAPIs:
    """Clase singleton para acceso fácil a todas las APIs"""
    
    # AbuseIPDB
    @staticmethod
    async def check_ip_abuse(ip: str, max_age_days: int = 90):
        return await abuseipdb_check_ip(ip, max_age_days)
    
    @staticmethod
    async def check_block_abuse(network: str, max_age_days: int = 15):
        return await abuseipdb_check_block(network, max_age_days)
    
    # OTX AlienVault
    @staticmethod
    async def get_otx_indicator(indicator_type: str, indicator: str):
        return await otx_get_indicator(indicator_type, indicator)
    
    @staticmethod
    async def get_otx_pulses(limit: int = 50):
        return await otx_get_subscribed_pulses(limit)
    
    # URLScan
    @staticmethod
    async def scan_url(url: str, visibility: str = "unlisted"):
        return await urlscan_submit(url, visibility)
    
    @staticmethod
    async def scan_url_and_wait(url: str, visibility: str = "unlisted", timeout: int = 60):
        return await urlscan_scan_and_wait(url, visibility, timeout)
    
    @staticmethod
    async def get_url_result(uuid: str):
        return await urlscan_get_result(uuid)
    
    @staticmethod
    async def search_urls(query: str, size: int = 50):
        return await urlscan_search(query, size)
    
    # Status
    @staticmethod
    async def get_status():
        return await check_all_api_status()


threat_intel_apis = ThreatIntelAPIs()
