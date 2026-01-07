"""
Servicios para análisis de credenciales filtradas
Integra HIBP, Dehashed, Intelligence X, LeakCheck y dumps locales
"""

import httpx
from typing import Dict, List
import logging
import asyncio
from pathlib import Path

from api.config import settings

logger = logging.getLogger(__name__)

# Rate limiter global para HIBP
_last_hibp_request = 0
_hibp_rate_limit = 1.5  # segundos entre requests


async def check_dehashed(query: str, query_type: str = "email") -> Dict:
    """
    Busca en Dehashed API (base de datos de credenciales filtradas)
    
    Requiere API key de pago: https://www.dehashed.com/
    """
    if not settings.DEHASHED_API_KEY or not settings.DEHASHED_ENABLED:
        logger.warning("⚠️ Dehashed no configurado")
        return {"found": False, "entries": [], "error": "Dehashed not configured"}
    
    try:
        logger.info(f"🔍 Consultando Dehashed para: {query}")
        
        # Mapear tipo de query a campo de Dehashed
        field_map = {
            "email": "email",
            "domain": "domain",
            "username": "username",
            "phone": "phone",
            "ip": "ip_address"
        }
        field = field_map.get(query_type, "email")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.dehashed.com/search",
                params={"query": f"{field}:{query}"},
                headers={
                    "Accept": "application/json"
                },
                auth=(settings.DEHASHED_API_KEY, ""),
                timeout=30.0
            )
            
            if response.status_code == 401:
                return {"found": False, "entries": [], "error": "Invalid API key"}
            
            if response.status_code == 429:
                return {"found": False, "entries": [], "error": "Rate limit exceeded"}
            
            response.raise_for_status()
            data = response.json()
            
            entries = data.get("entries", [])
            
            if entries:
                logger.warning(f"⚠️ {query} encontrado en {len(entries)} registros de Dehashed")
                
                processed_entries = []
                for entry in entries[:20]:  # Limitar a 20 resultados
                    processed_entries.append({
                        "database_name": entry.get("database_name", "Unknown"),
                        "email": entry.get("email"),
                        "username": entry.get("username"),
                        "password": "[REDACTED]" if entry.get("password") else None,
                        "hashed_password": bool(entry.get("hashed_password")),
                        "ip_address": entry.get("ip_address"),
                        "phone": entry.get("phone"),
                        "obtained_from": entry.get("obtained_from"),
                        "credentials": [{"email": entry.get("email"), "password": "[FOUND]"}] if entry.get("password") else []
                    })
                
                return {
                    "found": True,
                    "entries": processed_entries,
                    "total": data.get("total", len(entries))
                }
            
            return {"found": False, "entries": [], "total": 0}
    
    except Exception as e:
        logger.error(f"❌ Error consultando Dehashed: {e}")
        return {"found": False, "entries": [], "error": str(e)}


async def check_intelx(query: str, query_type: str = "email") -> Dict:
    """
    Busca en Intelligence X (darknet search engine)
    
    Requiere API key: https://intelx.io/
    """
    if not settings.INTELX_API_KEY:
        logger.warning("⚠️ IntelX no configurado")
        return {"found": False, "results": [], "error": "IntelX not configured"}
    
    try:
        logger.info(f"🔍 Consultando Intelligence X para: {query}")
        
        async with httpx.AsyncClient() as client:
            # Iniciar búsqueda
            search_response = await client.post(
                "https://2.intelx.io/intelligent/search",
                json={
                    "term": query,
                    "maxresults": 100,
                    "media": 0,
                    "sort": 2,
                    "terminate": []
                },
                headers={
                    "x-key": settings.INTELX_API_KEY,
                    "Content-Type": "application/json"
                },
                timeout=30.0
            )
            
            if search_response.status_code != 200:
                return {"found": False, "results": [], "error": f"Search failed: {search_response.status_code}"}
            
            search_data = search_response.json()
            search_id = search_data.get("id")
            
            if not search_id:
                return {"found": False, "results": [], "error": "No search ID returned"}
            
            # Esperar resultados
            await asyncio.sleep(2)
            
            # Obtener resultados
            results_response = await client.get(
                "https://2.intelx.io/intelligent/search/result",
                params={"id": search_id, "limit": 50},
                headers={"x-key": settings.INTELX_API_KEY},
                timeout=30.0
            )
            
            if results_response.status_code != 200:
                return {"found": False, "results": [], "error": "Failed to get results"}
            
            results_data = results_response.json()
            records = results_data.get("records", [])
            
            if records:
                logger.warning(f"⚠️ {query} encontrado en {len(records)} resultados de IntelX")
                
                processed = []
                for record in records[:20]:
                    processed.append({
                        "name": record.get("name", "IntelX Result"),
                        "type": record.get("type", "unknown"),
                        "date": record.get("date"),
                        "bucket": record.get("bucket"),
                        "size": record.get("size")
                    })
                
                return {
                    "found": True,
                    "results": processed,
                    "total": len(records)
                }
            
            return {"found": False, "results": [], "total": 0}
    
    except Exception as e:
        logger.error(f"❌ Error consultando IntelX: {e}")
        return {"found": False, "results": [], "error": str(e)}


async def check_leakcheck(query: str, query_type: str = "email") -> Dict:
    """
    Busca en LeakCheck API
    
    API: https://leakcheck.io/
    """
    # LeakCheck requiere API key - placeholder por ahora
    logger.info(f"🔍 LeakCheck: búsqueda para {query} (no configurado)")
    
    # Simulación de respuesta cuando no está configurado
    return {
        "found": False,
        "sources": [],
        "error": "LeakCheck not configured - add LEAKCHECK_API_KEY to .env"
    }

async def check_hibp_breach(email: str) -> Dict:
    """
    Verifica si un email ha sido comprometido en HIBP
    
    Rate limit: 1 request per 1.5 seconds (API requirement)
    """
    global _last_hibp_request
    
    if not settings.HIBP_ENABLED or not settings.HIBP_API_KEY:
        logger.warning("⚠️ HIBP no configurado, saltando verificación")
        return {"breached": False, "breaches": [], "error": "HIBP not configured"}
    
    try:
        # Rate limiting estricto
        import time
        current_time = time.time()
        time_since_last = current_time - _last_hibp_request
        
        if time_since_last < _hibp_rate_limit:
            wait_time = _hibp_rate_limit - time_since_last
            logger.info(f"⏳ HIBP rate limit: esperando {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
        
        _last_hibp_request = time.time()
        
        logger.info(f"🔍 Consultando HIBP para: {email}")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}",
                headers={
                    "hibp-api-key": settings.HIBP_API_KEY,
                    "User-Agent": "MCP-Kali-Forensics/1.0"
                },
                params={"truncateResponse": "false"},
                timeout=15.0
            )
            
            if response.status_code == 404:
                logger.info(f"✅ {email} no encontrado en HIBP")
                return {"breached": False, "breaches": [], "breach_count": 0}
            
            if response.status_code == 429:
                logger.error("❌ HIBP rate limit excedido")
                return {"breached": False, "breaches": [], "error": "Rate limit exceeded"}
            
            response.raise_for_status()
            breaches_data = response.json()
            
            # Extraer información detallada
            breaches = []
            for breach in breaches_data:
                breaches.append({
                    "name": breach.get("Name"),
                    "domain": breach.get("Domain"),
                    "breach_date": breach.get("BreachDate"),
                    "added_date": breach.get("AddedDate"),
                    "pwn_count": breach.get("PwnCount"),
                    "description": breach.get("Description", "")[:200],  # Truncar
                    "data_classes": breach.get("DataClasses", [])
                })
            
            logger.info(f"⚠️ {email} encontrado en {len(breaches)} brechas")
            
            return {
                "breached": True,
                "breaches": breaches,
                "breach_count": len(breaches),
                "breach_names": [b["name"] for b in breaches]
            }
    
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {"breached": False, "breaches": [], "breach_count": 0}
        logger.error(f"❌ Error HTTP HIBP ({e.response.status_code}): {e}")
        return {"breached": False, "breaches": [], "error": f"HTTP {e.response.status_code}"}
    except httpx.TimeoutException:
        logger.error("❌ HIBP timeout")
        return {"breached": False, "breaches": [], "error": "Timeout"}
    except Exception as e:
        logger.error(f"❌ Error consultando HIBP: {e}")
        return {"breached": False, "breaches": [], "error": str(e)}

async def check_local_dumps(email: str) -> Dict:
    """
    Busca email en dumps locales de stealer logs
    
    Usa grep para búsqueda rápida en archivos de texto
    """
    logger.info(f"🗂️ Buscando {email} en dumps locales")
    
    try:
        dumps_dir = settings.EVIDENCE_DIR / "dumps"
        
        # Crear directorio si no existe
        dumps_dir.mkdir(parents=True, exist_ok=True)
        
        # Verificar que hay archivos para buscar
        if not any(dumps_dir.iterdir()):
            logger.info("📂 No hay dumps locales para buscar")
            return {
                "found": False,
                "dumps": [],
                "message": "No local dumps available"
            }
        
        # Usar grep recursivo para búsqueda rápida
        cmd = [
            "grep",
            "-r",           # Recursivo
            "-i",           # Case insensitive
            "-l",           # Solo nombres de archivo
            "-F",           # Fixed string (no regex)
            email,
            str(dumps_dir)
        ]
        
        logger.info(f"🔍 Ejecutando grep en {dumps_dir}")
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=120  # 2 minutos máximo
        )
        
        # Grep retorna 0 si encuentra algo, 1 si no encuentra
        if process.returncode == 0:
            files_found = stdout.decode().strip().split('\n')
            files_found = [f for f in files_found if f]  # Filtrar vacíos
            
            logger.info(f"⚠️ {email} encontrado en {len(files_found)} dumps locales")
            
            # Extraer más contexto de cada archivo
            dumps_details = []
            for filepath in files_found[:10]:  # Limitar a 10 primeros
                try:
                    # Obtener líneas con contexto
                    context_cmd = [
                        "grep",
                        "-i",
                        "-A", "2",  # 2 líneas después
                        "-B", "2",  # 2 líneas antes
                        "-F",
                        email,
                        filepath
                    ]
                    
                    context_proc = await asyncio.create_subprocess_exec(
                        *context_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    context_out, _ = await context_proc.communicate()
                    
                    dumps_details.append({
                        "file": filepath,
                        "context": context_out.decode()[:500]  # Limitar tamaño
                    })
                
                except Exception as e:
                    logger.error(f"❌ Error obteniendo contexto de {filepath}: {e}")
            
            return {
                "found": True,
                "dumps": dumps_details,
                "total_files": len(files_found),
                "message": f"Found in {len(files_found)} local dump files"
            }
        
        else:
            logger.info(f"✅ {email} no encontrado en dumps locales")
            return {
                "found": False,
                "dumps": [],
                "message": "Not found in local dumps"
            }
    
    except asyncio.TimeoutError:
        logger.error("❌ Timeout buscando en dumps locales")
        return {
            "found": False,
            "dumps": [],
            "error": "Search timeout"
        }
    except Exception as e:
        logger.error(f"❌ Error buscando en dumps locales: {e}")
        return {
            "found": False,
            "dumps": [],
            "error": str(e)
        }

async def analyze_stealer_logs(email: str) -> Dict:
    """
    Analiza logs de infostealers en busca del email
    
    Parsea logs conocidos de RedLine, Vidar, Raccoon, etc.
    """
    logger.info(f"🦠 Analizando stealer logs para {email}")
    
    try:
        stealers_dir = settings.EVIDENCE_DIR / "stealers"
        stealers_dir.mkdir(parents=True, exist_ok=True)
        
        if not any(stealers_dir.iterdir()):
            logger.info("📂 No hay logs de stealers para analizar")
            return {
                "found": False,
                "logs": [],
                "message": "No stealer logs available"
            }
        
        findings = []
        
        # Patrones comunes en stealer logs
        patterns = [
            "passwords.txt",      # RedLine, Vidar
            "autofill.txt",       # Formularios guardados
            "cookies.txt",        # Cookies
            "information.txt",    # Info del sistema
            "passwords_*.txt",    # Variantes
            "*.log"               # Logs generales
        ]
        
        for pattern in patterns:
            # Buscar archivos que coincidan con el patrón
            matching_files = list(stealers_dir.glob(f"**/{pattern}"))
            
            for log_file in matching_files:
                try:
                    # Buscar email en el archivo
                    cmd = [
                        "grep",
                        "-i",
                        "-F",
                        "-A", "5",  # 5 líneas de contexto
                        email,
                        str(log_file)
                    ]
                    
                    process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    
                    stdout, _ = await asyncio.wait_for(
                        process.communicate(),
                        timeout=30
                    )
                    
                    if process.returncode == 0:
                        # Encontrado!
                        content = stdout.decode()
                        
                        # Intentar extraer credenciales asociadas
                        credentials = extract_credentials_from_log(content)
                        
                        findings.append({
                            "file": str(log_file),
                            "stealer_type": detect_stealer_type(log_file),
                            "timestamp": log_file.stat().st_mtime,
                            "credentials": credentials,
                            "context": content[:300]  # Primeros 300 chars
                        })
                        
                        logger.warning(f"⚠️ {email} encontrado en {log_file.name}")
                
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.error(f"❌ Error analizando {log_file}: {e}")
                    continue
        
        if findings:
            return {
                "found": True,
                "logs": findings,
                "total_findings": len(findings),
                "message": f"Found in {len(findings)} stealer logs - CRITICAL!"
            }
        else:
            return {
                "found": False,
                "logs": [],
                "message": "Not found in stealer logs"
            }
    
    except Exception as e:
        logger.error(f"❌ Error analizando stealer logs: {e}")
        return {
            "found": False,
            "logs": [],
            "error": str(e)
        }

def detect_stealer_type(log_path: Path) -> str:
    """Detecta el tipo de stealer por la estructura de archivos"""
    parent_dirs = [p.name.lower() for p in log_path.parents]
    
    if any('redline' in d for d in parent_dirs):
        return 'RedLine Stealer'
    elif any('vidar' in d for d in parent_dirs):
        return 'Vidar'
    elif any('raccoon' in d for d in parent_dirs):
        return 'Raccoon Stealer'
    elif any('azorult' in d for d in parent_dirs):
        return 'AZORult'
    elif any('metastealer' in d for d in parent_dirs):
        return 'Meta Stealer'
    else:
        return 'Unknown Stealer'

def extract_credentials_from_log(content: str) -> List[Dict]:
    """Extrae credenciales de logs de stealers"""
    credentials = []
    
    try:
        # Patrón común: URL: xxx\nUsername: xxx\nPassword: xxx
        import re
        
        # Buscar patrones de credenciales
        url_pattern = r'URL:\s*(.+)'
        user_pattern = r'(Username|Login|Email):\s*(.+)'
        pass_pattern = r'Password:\s*(.+)'
        
        urls = re.findall(url_pattern, content, re.IGNORECASE)
        users = re.findall(user_pattern, content, re.IGNORECASE)
        passwords = re.findall(pass_pattern, content, re.IGNORECASE)
        
        # Intentar emparejar
        for i in range(min(len(urls), len(users), len(passwords), 5)):  # Máximo 5
            credentials.append({
                "url": urls[i] if i < len(urls) else "Unknown",
                "username": users[i][1] if i < len(users) else "Unknown",
                "password": "[REDACTED]"  # No exponer passwords en logs
            })
    
    except Exception as e:
        logger.error(f"❌ Error extrayendo credenciales: {e}")
    
    return credentials
