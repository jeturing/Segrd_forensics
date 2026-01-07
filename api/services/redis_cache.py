"""
💾 Redis Cache Service - Rate Limit Protection & Performance
Cache de resultados de APIs externas para evitar rate limits
"""

import os
import json
import hashlib
import logging
from typing import Optional, Any, Dict
from functools import wraps

logger = logging.getLogger(__name__)

# =============================================================================
# Redis Configuration
# =============================================================================

REDIS_ENABLED = os.getenv("REDIS_ENABLED", "false").lower() == "true"
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# Cache TTL por tipo de consulta (en segundos)
CACHE_TTL = {
    "ip_lookup": 3600,        # 1 hora
    "email_check": 86400,     # 24 horas
    "domain_info": 7200,      # 2 horas
    "url_scan": 1800,         # 30 minutos
    "shodan_search": 3600,    # 1 hora
    "virustotal": 3600,       # 1 hora
    "hibp": 86400,            # 24 horas
    "xforce": 3600,           # 1 hora
    "default": 3600           # 1 hora por defecto
}

# =============================================================================
# Redis Client (con fallback si no está disponible)
# =============================================================================

redis_client = None

if REDIS_ENABLED:
    try:
        import redis.asyncio as redis
        
        redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
        
        logger.info(f"✅ Redis cache enabled: {REDIS_HOST}:{REDIS_PORT}")
    except ImportError:
        logger.warning("⚠️ redis package not installed. Install with: pip install redis[hiredis]")
        REDIS_ENABLED = False
    except Exception as e:
        logger.error(f"❌ Redis connection error: {e}")
        REDIS_ENABLED = False
else:
    logger.info("ℹ️ Redis cache disabled (set REDIS_ENABLED=true to enable)")


# =============================================================================
# Cache Key Generation
# =============================================================================

def generate_cache_key(prefix: str, **params) -> str:
    """
    Genera una clave de cache determinística basada en parámetros
    
    Args:
        prefix: Prefijo del tipo de consulta (ip, email, domain, etc.)
        **params: Parámetros de la consulta
    
    Returns:
        Cache key (ej: "threat_intel:ip:8.8.8.8:shodan:vt")
    """
    # Ordenar parámetros para consistencia
    sorted_params = sorted(params.items())
    param_str = json.dumps(sorted_params, sort_keys=True)
    
    # Hash de parámetros para keys más cortas
    param_hash = hashlib.md5(param_str.encode()).hexdigest()[:12]
    
    return f"threat_intel:{prefix}:{param_hash}"


# =============================================================================
# Cache Decorator
# =============================================================================

def cache_result(cache_type: str, ttl: Optional[int] = None):
    """
    Decorator para cachear resultados de funciones async
    
    Uso:
        @cache_result("ip_lookup", ttl=3600)
        async def lookup_ip(ip: str):
            # Lógica de consulta
            return result
    
    Args:
        cache_type: Tipo de cache (usado para key prefix y TTL default)
        ttl: Time to live en segundos (opcional, usa default del tipo)
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Si Redis no está habilitado, ejecutar función directamente
            if not REDIS_ENABLED or not redis_client:
                return await func(*args, **kwargs)
            
            # Generar cache key
            cache_key = generate_cache_key(cache_type, args=args, kwargs=kwargs)
            
            try:
                # Intentar obtener del cache
                cached = await redis_client.get(cache_key)
                if cached:
                    logger.debug(f"💾 Cache HIT: {cache_key}")
                    return json.loads(cached)
                
                # Cache miss - ejecutar función
                logger.debug(f"🔍 Cache MISS: {cache_key}")
                result = await func(*args, **kwargs)
                
                # Guardar en cache
                cache_ttl = ttl or CACHE_TTL.get(cache_type, CACHE_TTL["default"])
                await redis_client.setex(
                    cache_key,
                    cache_ttl,
                    json.dumps(result)
                )
                logger.debug(f"💾 Cached for {cache_ttl}s: {cache_key}")
                
                return result
            
            except Exception as e:
                logger.error(f"Cache error for {cache_key}: {e}")
                # Si hay error de cache, ejecutar función de todos modos
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# =============================================================================
# Manual Cache Operations
# =============================================================================

async def cache_get(key: str) -> Optional[Dict]:
    """Obtiene un valor del cache"""
    if not REDIS_ENABLED or not redis_client:
        return None
    
    try:
        cached = await redis_client.get(key)
        if cached:
            return json.loads(cached)
    except Exception as e:
        logger.error(f"Cache get error: {e}")
    
    return None


async def cache_set(key: str, value: Any, ttl: int = 3600) -> bool:
    """Guarda un valor en el cache"""
    if not REDIS_ENABLED or not redis_client:
        return False
    
    try:
        await redis_client.setex(key, ttl, json.dumps(value))
        return True
    except Exception as e:
        logger.error(f"Cache set error: {e}")
        return False


async def cache_delete(key: str) -> bool:
    """Elimina un valor del cache"""
    if not REDIS_ENABLED or not redis_client:
        return False
    
    try:
        await redis_client.delete(key)
        return True
    except Exception as e:
        logger.error(f"Cache delete error: {e}")
        return False


async def cache_clear_pattern(pattern: str) -> int:
    """
    Elimina todas las keys que coincidan con un patrón
    
    Args:
        pattern: Patrón (ej: "threat_intel:ip:*")
    
    Returns:
        Número de keys eliminadas
    """
    if not REDIS_ENABLED or not redis_client:
        return 0
    
    try:
        keys = []
        async for key in redis_client.scan_iter(match=pattern):
            keys.append(key)
        
        if keys:
            deleted = await redis_client.delete(*keys)
            logger.info(f"🗑️ Cleared {deleted} cache keys matching: {pattern}")
            return deleted
        
        return 0
    except Exception as e:
        logger.error(f"Cache clear error: {e}")
        return 0


async def get_cache_stats() -> Dict[str, Any]:
    """
    Obtiene estadísticas del cache Redis
    
    Returns:
        Estadísticas: keys totales, memoria usada, hit rate, etc.
    """
    if not REDIS_ENABLED or not redis_client:
        return {
            "enabled": False,
            "message": "Redis cache is disabled"
        }
    
    try:
        info = await redis_client.info("stats")
        keyspace = await redis_client.info("keyspace")
        
        # Contar keys por tipo
        threat_intel_keys = 0
        async for key in redis_client.scan_iter(match="threat_intel:*"):
            threat_intel_keys += 1
        
        return {
            "enabled": True,
            "host": REDIS_HOST,
            "port": REDIS_PORT,
            "total_keys": sum(keyspace.get(f"db{REDIS_DB}", {}).get("keys", 0) for db in range(16)),
            "threat_intel_keys": threat_intel_keys,
            "hits": info.get("keyspace_hits", 0),
            "misses": info.get("keyspace_misses", 0),
            "hit_rate": round(
                info.get("keyspace_hits", 0) / max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1) * 100,
                2
            ),
            "used_memory_human": info.get("used_memory_human", "N/A"),
            "connected_clients": info.get("connected_clients", 0)
        }
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return {
            "enabled": True,
            "error": str(e)
        }


# =============================================================================
# Rate Limiting Helper
# =============================================================================

async def check_rate_limit(
    identifier: str,
    max_requests: int,
    window_seconds: int
) -> Dict[str, Any]:
    """
    Verifica rate limit usando Redis
    
    Args:
        identifier: Identificador único (API key, IP, user ID)
        max_requests: Máximo de requests permitidos
        window_seconds: Ventana de tiempo en segundos
    
    Returns:
        {
            "allowed": bool,
            "remaining": int,
            "reset_at": timestamp
        }
    """
    if not REDIS_ENABLED or not redis_client:
        return {
            "allowed": True,
            "remaining": max_requests,
            "message": "Rate limiting disabled (Redis not available)"
        }
    
    key = f"ratelimit:{identifier}"
    
    try:
        # Incrementar contador
        current = await redis_client.incr(key)
        
        # Si es la primera request, setear TTL
        if current == 1:
            await redis_client.expire(key, window_seconds)
        
        # Obtener TTL restante
        ttl = await redis_client.ttl(key)
        
        allowed = current <= max_requests
        
        return {
            "allowed": allowed,
            "remaining": max(0, max_requests - current),
            "reset_at": ttl,
            "current": current,
            "limit": max_requests
        }
    
    except Exception as e:
        logger.error(f"Rate limit check error: {e}")
        # En caso de error, permitir la request
        return {
            "allowed": True,
            "error": str(e)
        }


# =============================================================================
# Cache Warming (Pre-carga de datos comunes)
# =============================================================================

async def warm_cache_common_queries():
    """
    Pre-carga el cache con consultas comunes
    
    Útil al iniciar el servicio para tener datos listos
    """
    if not REDIS_ENABLED:
        return
    
    logger.info("🔥 Warming up cache with common queries...")
    
    # Lista de IPs/dominios comunes a pre-cargar
    common_targets = {
        "ips": ["8.8.8.8", "1.1.1.1", "9.9.9.9"],
        "domains": ["google.com", "microsoft.com", "cloudflare.com"]
    }
    
    # Pre-cargar consultas comunes
    from api.services import threat_intel
    
    for ip in common_targets["ips"]:
        try:
            await threat_intel.virustotal_ip_report(ip)
        except:
            pass
    
    logger.info("✅ Cache warming completed")
