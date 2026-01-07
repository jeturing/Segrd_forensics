"""
🔍 Threat Intelligence Services - Integración con APIs externas
Soporta: Shodan, Censys, VirusTotal, HIBP, X-Force, SecurityTrails, etc.
"""

import os
import asyncio
import aiohttp
import logging
from typing import Dict, Any
from datetime import datetime
import base64
import hashlib

# Importar cache service
from api.services.redis_cache import cache_result

logger = logging.getLogger(__name__)

# =============================================================================
# API Configuration
# =============================================================================

SHODAN_API_KEY = os.getenv("SHODAN_API_KEY")
CENSYS_API_ID = os.getenv("CENSYS_API_ID")
CENSYS_API_SECRET = os.getenv("CENSYS_API_SECRET")
VT_API_KEY = os.getenv("VT_API_KEY")
HIBP_API_KEY = os.getenv("HIBP_API_KEY")
XFORCE_API_KEY = os.getenv("XFORCE_API_KEY")
XFORCE_API_SECRET = os.getenv("XFORCE_API_SECRET")
SECURITYTRAILS_API_KEY = os.getenv("SECURITYTRAILS_API_KEY")
HUNTER_API_KEY = os.getenv("HUNTER_API_KEY")
INTELX_API_KEY = os.getenv("INTELX_API_KEY")
HYBRID_ANALYSIS_KEY = os.getenv("HYBRID_ANALYSIS_KEY")


# =============================================================================
# Shodan - Network Intelligence
# =============================================================================

@cache_result("ip_lookup", ttl=3600)  # Cache 1 hora
async def shodan_ip_lookup(ip: str) -> Dict[str, Any]:
    """
    Consulta información de una IP en Shodan
    
    Retorna:
    - Puertos abiertos
    - Servicios detectados
    - Vulnerabilidades
    - Geolocalización
    - ISP/Organización
    """
    if not SHODAN_API_KEY:
        return {"error": "Shodan API key not configured"}
    
    url = f"https://api.shodan.io/shodan/host/{ip}"
    params = {"key": SHODAN_API_KEY}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        "success": True,
                        "ip": data.get("ip_str"),
                        "organization": data.get("org"),
                        "isp": data.get("isp"),
                        "country": data.get("country_name"),
                        "city": data.get("city"),
                        "ports": data.get("ports", []),
                        "hostnames": data.get("hostnames", []),
                        "vulns": data.get("vulns", []),
                        "services": [
                            {
                                "port": svc.get("port"),
                                "protocol": svc.get("transport"),
                                "product": svc.get("product"),
                                "version": svc.get("version")
                            }
                            for svc in data.get("data", [])
                        ],
                        "last_update": data.get("last_update"),
                        "tags": data.get("tags", [])
                    }
                else:
                    error_data = await resp.text()
                    return {"success": False, "error": f"Shodan error: {error_data}"}
    except Exception as e:
        logger.error(f"Shodan lookup error: {e}")
        return {"success": False, "error": str(e)}


@cache_result("shodan_search", ttl=3600)  # Cache 1 hora
async def shodan_search(query: str, limit: int = 100) -> Dict[str, Any]:
    """Búsqueda en Shodan con query personalizada"""
    if not SHODAN_API_KEY:
        return {"error": "Shodan API key not configured"}
    
    url = "https://api.shodan.io/shodan/host/search"
    params = {"key": SHODAN_API_KEY, "query": query, "limit": limit}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        "success": True,
                        "total": data.get("total"),
                        "results": [
                            {
                                "ip": r.get("ip_str"),
                                "port": r.get("port"),
                                "organization": r.get("org"),
                                "hostnames": r.get("hostnames", []),
                                "location": f"{r.get('location', {}).get('city')}, {r.get('location', {}).get('country_name')}"
                            }
                            for r in data.get("matches", [])
                        ]
                    }
                else:
                    return {"success": False, "error": await resp.text()}
    except Exception as e:
        logger.error(f"Shodan search error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# Censys - Internet-wide Scanning
# =============================================================================

@cache_result("ip_lookup", ttl=3600)  # Cache 1 hora
async def censys_ip_lookup(ip: str) -> Dict[str, Any]:
    """Consulta IP en Censys"""
    if not CENSYS_API_ID or not CENSYS_API_SECRET:
        return {"error": "Censys credentials not configured"}
    
    url = f"https://search.censys.io/api/v2/hosts/{ip}"
    auth = aiohttp.BasicAuth(CENSYS_API_ID, CENSYS_API_SECRET)
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, auth=auth, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    result = data.get("result", {})
                    return {
                        "success": True,
                        "ip": result.get("ip"),
                        "services": result.get("services", []),
                        "autonomous_system": result.get("autonomous_system", {}),
                        "location": result.get("location", {}),
                        "last_updated": result.get("last_updated_at")
                    }
                else:
                    return {"success": False, "error": await resp.text()}
    except Exception as e:
        logger.error(f"Censys lookup error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# VirusTotal - File/URL/Domain Analysis
# =============================================================================

@cache_result("virustotal", ttl=3600)  # Cache 1 hora
async def virustotal_ip_report(ip: str) -> Dict[str, Any]:
    """Consulta reputación de IP en VirusTotal"""
    if not VT_API_KEY:
        return {"error": "VirusTotal API key not configured"}
    
    url = f"https://www.virustotal.com/api/v3/ip_addresses/{ip}"
    headers = {"x-apikey": VT_API_KEY}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    attributes = data.get("data", {}).get("attributes", {})
                    last_analysis = attributes.get("last_analysis_stats", {})
                    
                    return {
                        "success": True,
                        "ip": ip,
                        "reputation": attributes.get("reputation", 0),
                        "malicious": last_analysis.get("malicious", 0),
                        "suspicious": last_analysis.get("suspicious", 0),
                        "harmless": last_analysis.get("harmless", 0),
                        "undetected": last_analysis.get("undetected", 0),
                        "country": attributes.get("country"),
                        "as_owner": attributes.get("as_owner"),
                        "network": attributes.get("network")
                    }
                else:
                    return {"success": False, "error": await resp.text()}
    except Exception as e:
        logger.error(f"VirusTotal error: {e}")
        return {"success": False, "error": str(e)}


@cache_result("url_scan", ttl=1800)  # Cache 30 minutos
async def virustotal_url_scan(url_to_scan: str) -> Dict[str, Any]:
    """Escanea una URL en VirusTotal"""
    if not VT_API_KEY:
        return {"error": "VirusTotal API key not configured"}
    
    # Step 1: Submit URL
    submit_url = "https://www.virustotal.com/api/v3/urls"
    headers = {"x-apikey": VT_API_KEY}
    data = {"url": url_to_scan}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(submit_url, headers=headers, data=data) as resp:
                if resp.status == 200:
                    submit_data = await resp.json()
                    analysis_id = submit_data.get("data", {}).get("id")
                    
                    # Step 2: Get analysis results (may need to wait)
                    await asyncio.sleep(5)  # Wait for analysis
                    
                    analysis_url = f"https://www.virustotal.com/api/v3/analyses/{analysis_id}"
                    async with session.get(analysis_url, headers=headers) as analysis_resp:
                        if analysis_resp.status == 200:
                            analysis_data = await analysis_resp.json()
                            attributes = analysis_data.get("data", {}).get("attributes", {})
                            stats = attributes.get("stats", {})
                            
                            return {
                                "success": True,
                                "url": url_to_scan,
                                "status": attributes.get("status"),
                                "malicious": stats.get("malicious", 0),
                                "suspicious": stats.get("suspicious", 0),
                                "harmless": stats.get("harmless", 0),
                                "undetected": stats.get("undetected", 0)
                            }
                        else:
                            return {"success": False, "error": "Analysis not ready"}
                else:
                    return {"success": False, "error": await resp.text()}
    except Exception as e:
        logger.error(f"VirusTotal URL scan error: {e}")
        return {"success": False, "error": str(e)}


async def virustotal_file_scan(file_path: str) -> Dict[str, Any]:
    """Escanea un archivo en VirusTotal"""
    if not VT_API_KEY:
        return {"error": "VirusTotal API key not configured"}
    
    url = "https://www.virustotal.com/api/v3/files"
    headers = {"x-apikey": VT_API_KEY}
    
    try:
        async with aiohttp.ClientSession() as session:
            with open(file_path, "rb") as f:
                data = aiohttp.FormData()
                data.add_field("file", f, filename=os.path.basename(file_path))
                
                async with session.post(url, headers=headers, data=data) as resp:
                    if resp.status == 200:
                        submit_data = await resp.json()
                        analysis_id = submit_data.get("data", {}).get("id")
                        
                        return {
                            "success": True,
                            "analysis_id": analysis_id,
                            "message": "File submitted for analysis"
                        }
                    else:
                        return {"success": False, "error": await resp.text()}
    except Exception as e:
        logger.error(f"VirusTotal file scan error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# HaveIBeenPwned - Credential Breach Database
# =============================================================================

async def hibp_check_email(email: str) -> Dict[str, Any]:
    """Verifica si un email está en brechas de seguridad"""
    if not HIBP_API_KEY:
        return {"error": "HIBP API key not configured"}
    
    url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}"
    headers = {"hibp-api-key": HIBP_API_KEY, "user-agent": "MCP-Kali-Forensics"}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    breaches = await resp.json()
                    return {
                        "success": True,
                        "email": email,
                        "breached": True,
                        "breach_count": len(breaches),
                        "breaches": [
                            {
                                "name": b.get("Name"),
                                "title": b.get("Title"),
                                "domain": b.get("Domain"),
                                "breach_date": b.get("BreachDate"),
                                "added_date": b.get("AddedDate"),
                                "pwn_count": b.get("PwnCount"),
                                "description": b.get("Description"),
                                "data_classes": b.get("DataClasses", [])
                            }
                            for b in breaches
                        ]
                    }
                elif resp.status == 404:
                    return {
                        "success": True,
                        "email": email,
                        "breached": False,
                        "message": "Email not found in breaches"
                    }
                else:
                    return {"success": False, "error": f"HIBP error: {resp.status}"}
    except Exception as e:
        logger.error(f"HIBP error: {e}")
        return {"success": False, "error": str(e)}


async def hibp_check_password(password: str) -> Dict[str, Any]:
    """Verifica si una contraseña está comprometida usando k-Anonymity"""
    url = "https://api.pwnedpasswords.com/range/"
    
    # Hash SHA1 de la contraseña
    sha1_hash = hashlib.sha1(password.encode()).hexdigest().upper()
    prefix = sha1_hash[:5]
    suffix = sha1_hash[5:]
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{url}{prefix}", timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    hashes = await resp.text()
                    for line in hashes.split("\n"):
                        hash_suffix, count = line.split(":")
                        if hash_suffix == suffix:
                            return {
                                "success": True,
                                "compromised": True,
                                "count": int(count),
                                "message": f"Password found in {count} breaches"
                            }
                    
                    return {
                        "success": True,
                        "compromised": False,
                        "message": "Password not found in breaches"
                    }
                else:
                    return {"success": False, "error": f"HIBP error: {resp.status}"}
    except Exception as e:
        logger.error(f"HIBP password check error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# IBM X-Force Exchange - Threat Intelligence
# =============================================================================

async def xforce_ip_report(ip: str) -> Dict[str, Any]:
    """Consulta IP en IBM X-Force Exchange"""
    if not XFORCE_API_KEY or not XFORCE_API_SECRET:
        return {"error": "X-Force credentials not configured"}
    
    url = f"https://api.xforce.ibmcloud.com/ipr/{ip}"
    
    # Basic Auth con API Key:Secret
    credentials = f"{XFORCE_API_KEY}:{XFORCE_API_SECRET}"
    encoded = base64.b64encode(credentials.encode()).decode()
    headers = {"Authorization": f"Basic {encoded}"}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        "success": True,
                        "ip": data.get("ip"),
                        "score": data.get("score"),
                        "reason": data.get("reason"),
                        "reasonDescription": data.get("reasonDescription"),
                        "country": data.get("geo", {}).get("country"),
                        "cats": data.get("cats", {}),
                        "history": data.get("history", [])
                    }
                else:
                    return {"success": False, "error": await resp.text()}
    except Exception as e:
        logger.error(f"X-Force error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# SecurityTrails - DNS & Domain Intelligence
# =============================================================================

async def securitytrails_domain_info(domain: str) -> Dict[str, Any]:
    """Consulta información de dominio en SecurityTrails"""
    if not SECURITYTRAILS_API_KEY:
        return {"error": "SecurityTrails API key not configured"}
    
    url = f"https://api.securitytrails.com/v1/domain/{domain}"
    headers = {"APIKEY": SECURITYTRAILS_API_KEY}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        "success": True,
                        "domain": domain,
                        "current_dns": data.get("current_dns", {}),
                        "alexa_rank": data.get("alexa_rank"),
                        "apex_domain": data.get("apex_domain")
                    }
                else:
                    return {"success": False, "error": await resp.text()}
    except Exception as e:
        logger.error(f"SecurityTrails error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# Hunter.io - Email Discovery
# =============================================================================

async def hunter_domain_search(domain: str) -> Dict[str, Any]:
    """Busca emails asociados a un dominio"""
    if not HUNTER_API_KEY:
        return {"error": "Hunter API key not configured"}
    
    url = "https://api.hunter.io/v2/domain-search"
    params = {"domain": domain, "api_key": HUNTER_API_KEY}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    domain_data = data.get("data", {})
                    
                    return {
                        "success": True,
                        "domain": domain,
                        "organization": domain_data.get("organization"),
                        "email_count": domain_data.get("emails"),
                        "emails": [
                            {
                                "value": e.get("value"),
                                "type": e.get("type"),
                                "confidence": e.get("confidence"),
                                "first_name": e.get("first_name"),
                                "last_name": e.get("last_name"),
                                "position": e.get("position")
                            }
                            for e in domain_data.get("emails", [])
                        ]
                    }
                else:
                    return {"success": False, "error": await resp.text()}
    except Exception as e:
        logger.error(f"Hunter error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# Hybrid Analysis - Malware Sandbox
# =============================================================================

async def hybrid_analysis_submit_file(file_path: str, environment_id: int = 100) -> Dict[str, Any]:
    """
    Envía archivo a Hybrid Analysis para análisis
    
    environment_id:
    - 100: Windows 7 32-bit
    - 110: Windows 7 64-bit
    - 120: Windows 10 64-bit
    - 300: Android Static Analysis
    """
    if not HYBRID_ANALYSIS_KEY:
        return {"error": "Hybrid Analysis API key not configured"}
    
    url = "https://www.hybrid-analysis.com/api/v2/submit/file"
    headers = {"api-key": HYBRID_ANALYSIS_KEY, "user-agent": "Falcon Sandbox"}
    
    try:
        async with aiohttp.ClientSession() as session:
            with open(file_path, "rb") as f:
                data = aiohttp.FormData()
                data.add_field("file", f, filename=os.path.basename(file_path))
                data.add_field("environment_id", str(environment_id))
                
                async with session.post(url, headers=headers, data=data) as resp:
                    if resp.status == 201:
                        result = await resp.json()
                        return {
                            "success": True,
                            "job_id": result.get("job_id"),
                            "sha256": result.get("sha256"),
                            "environment_id": result.get("environment_id"),
                            "message": "File submitted successfully"
                        }
                    else:
                        return {"success": False, "error": await resp.text()}
    except Exception as e:
        logger.error(f"Hybrid Analysis error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# Intelligence X - Dark Web & Data Breach Intelligence
# =============================================================================

async def intelx_search(term: str, maxresults: int = 100) -> Dict[str, Any]:
    """Busca en Intelligence X (dark web, data breaches)"""
    if not INTELX_API_KEY:
        return {"error": "Intelligence X API key not configured"}
    
    # Step 1: Initiate search
    url = "https://2.intelx.io/intelligent/search"
    headers = {"x-key": INTELX_API_KEY}
    payload = {
        "term": term,
        "maxresults": maxresults,
        "media": 0,
        "target": 0
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    search_id = data.get("id")
                    
                    # Step 2: Get results (may need to wait)
                    await asyncio.sleep(3)
                    
                    results_url = f"https://2.intelx.io/intelligent/search/result?id={search_id}"
                    async with session.get(results_url, headers=headers) as results_resp:
                        if results_resp.status == 200:
                            results = await results_resp.json()
                            return {
                                "success": True,
                                "term": term,
                                "records": results.get("records", [])
                            }
                        else:
                            return {"success": False, "error": "Results not ready"}
                else:
                    return {"success": False, "error": await resp.text()}
    except Exception as e:
        logger.error(f"Intelligence X error: {e}")
        return {"success": False, "error": str(e)}


# =============================================================================
# Utilidades
# =============================================================================

async def multi_source_ip_enrichment(ip: str) -> Dict[str, Any]:
    """
    Enriquece información de una IP consultando múltiples fuentes
    
    Consulta en paralelo:
    - Shodan
    - Censys
    - VirusTotal
    - X-Force Exchange
    """
    results = await asyncio.gather(
        shodan_ip_lookup(ip),
        censys_ip_lookup(ip),
        virustotal_ip_report(ip),
        xforce_ip_report(ip),
        return_exceptions=True
    )
    
    return {
        "ip": ip,
        "timestamp": datetime.now().isoformat(),
        "sources": {
            "shodan": results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])},
            "censys": results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])},
            "virustotal": results[2] if not isinstance(results[2], Exception) else {"error": str(results[2])},
            "xforce": results[3] if not isinstance(results[3], Exception) else {"error": str(results[3])}
        }
    }
