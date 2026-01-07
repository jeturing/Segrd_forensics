"""
🔍 MISP Integration Service - Malware Information Sharing Platform
===================================================================
Integración completa con MISP para compartir y consumir Threat Intelligence.

Funcionalidades:
- Consulta de eventos y atributos
- Búsqueda de IOCs (IPs, dominios, hashes, emails)
- Sincronización de feeds
- Exportación de casos a MISP
- Importación de eventos a casos
"""

import os
import aiohttp
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pathlib import Path

# Importar cache service
try:
    from api.services.redis_cache import cache_result
except ImportError:
    # Fallback si no hay Redis
    def cache_result(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

logger = logging.getLogger(__name__)

# =============================================================================
# MISP Configuration
# =============================================================================

MISP_URL = os.getenv("MISP_URL", "")
MISP_API_KEY = os.getenv("MISP_API_KEY", "")
MISP_VERIFY_SSL = os.getenv("MISP_VERIFY_SSL", "true").lower() == "true"

# Directorio para caché local de MISP
PROJECT_ROOT = Path(__file__).parent.parent.parent
MISP_CACHE_DIR = PROJECT_ROOT / "forensics-evidence" / "misp_cache"
MISP_CACHE_DIR.mkdir(parents=True, exist_ok=True)


class MISPClient:
    """Cliente asíncrono para MISP API"""
    
    def __init__(self, url: str = None, api_key: str = None, verify_ssl: bool = True):
        self.base_url = (url or MISP_URL).rstrip('/')
        self.api_key = api_key or MISP_API_KEY
        self.verify_ssl = verify_ssl if verify_ssl is not None else MISP_VERIFY_SSL
        self._session: Optional[aiohttp.ClientSession] = None
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Obtener o crear sesión HTTP"""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(ssl=self.verify_ssl)
            self._session = aiohttp.ClientSession(
                connector=connector,
                headers={
                    "Authorization": self.api_key,
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                },
                timeout=aiohttp.ClientTimeout(total=60)
            )
        return self._session
    
    async def close(self):
        """Cerrar sesión HTTP"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    def is_configured(self) -> bool:
        """Verificar si MISP está configurado"""
        return bool(self.base_url and self.api_key)
    
    async def _request(
        self, 
        method: str, 
        endpoint: str, 
        data: dict = None,
        params: dict = None
    ) -> Dict[str, Any]:
        """Realizar petición a MISP API"""
        if not self.is_configured():
            return {
                "success": False, 
                "error": "MISP no configurado. Establece MISP_URL y MISP_API_KEY"
            }
        
        url = f"{self.base_url}{endpoint}"
        session = await self._get_session()
        
        try:
            async with session.request(
                method, 
                url, 
                json=data, 
                params=params
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return {"success": True, "data": result}
                elif resp.status == 403:
                    return {"success": False, "error": "Acceso denegado. Verifica API key"}
                elif resp.status == 404:
                    return {"success": False, "error": "Recurso no encontrado"}
                else:
                    text = await resp.text()
                    return {"success": False, "error": f"Error {resp.status}: {text[:200]}"}
        except aiohttp.ClientError as e:
            logger.error(f"MISP connection error: {e}")
            return {"success": False, "error": f"Error de conexión: {str(e)}"}
        except Exception as e:
            logger.error(f"MISP request error: {e}")
            return {"success": False, "error": str(e)}
    
    # =========================================================================
    # Métodos de conexión y estado
    # =========================================================================
    
    async def test_connection(self) -> Dict[str, Any]:
        """Probar conexión con MISP"""
        result = await self._request("GET", "/servers/getVersion")
        if result.get("success"):
            version = result["data"]
            return {
                "success": True,
                "connected": True,
                "version": version.get("version"),
                "pymisp_recommended": version.get("perm_sync"),
                "url": self.base_url
            }
        return {
            "success": False,
            "connected": False,
            "error": result.get("error"),
            "url": self.base_url
        }
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Obtener estadísticas de MISP"""
        result = await self._request("GET", "/users/statistics")
        if result.get("success"):
            stats = result["data"]
            return {
                "success": True,
                "events_count": stats.get("stats", {}).get("event_count", 0),
                "attributes_count": stats.get("stats", {}).get("attribute_count", 0),
                "users_count": stats.get("stats", {}).get("user_count", 0),
                "orgs_count": stats.get("stats", {}).get("org_count", 0),
                "correlation_count": stats.get("stats", {}).get("correlation_count", 0)
            }
        return result
    
    # =========================================================================
    # Búsqueda de IOCs
    # =========================================================================
    
    @cache_result("misp_search_ioc", ttl=1800)  # Cache 30 min
    async def search_ioc(
        self, 
        value: str, 
        ioc_type: str = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Buscar un IOC específico en MISP
        
        Args:
            value: Valor del IOC (IP, hash, domain, email, etc)
            ioc_type: Tipo de IOC (ip-src, ip-dst, domain, md5, sha256, email, url)
            limit: Número máximo de resultados
        """
        search_body = {
            "returnFormat": "json",
            "value": value,
            "limit": limit,
            "includeEventTags": True,
            "includeContext": True
        }
        
        if ioc_type:
            search_body["type"] = ioc_type
        
        result = await self._request("POST", "/attributes/restSearch", data=search_body)
        
        if result.get("success"):
            attributes = result["data"].get("response", {}).get("Attribute", [])
            return {
                "success": True,
                "found": len(attributes) > 0,
                "count": len(attributes),
                "query": value,
                "type": ioc_type,
                "results": [
                    {
                        "id": attr.get("id"),
                        "event_id": attr.get("event_id"),
                        "type": attr.get("type"),
                        "category": attr.get("category"),
                        "value": attr.get("value"),
                        "comment": attr.get("comment"),
                        "to_ids": attr.get("to_ids"),
                        "timestamp": datetime.fromtimestamp(
                            int(attr.get("timestamp", 0))
                        ).isoformat() if attr.get("timestamp") else None,
                        "event_info": attr.get("Event", {}).get("info"),
                        "event_threat_level": attr.get("Event", {}).get("threat_level_id"),
                        "tags": [t.get("name") for t in attr.get("Tag", [])]
                    }
                    for attr in attributes[:limit]
                ]
            }
        return result
    
    async def search_ip(self, ip: str, limit: int = 50) -> Dict[str, Any]:
        """Buscar IP en MISP"""
        # Buscar como source y destination
        results_src = await self.search_ioc(ip, "ip-src", limit // 2)
        results_dst = await self.search_ioc(ip, "ip-dst", limit // 2)
        
        combined = []
        if results_src.get("success"):
            combined.extend(results_src.get("results", []))
        if results_dst.get("success"):
            combined.extend(results_dst.get("results", []))
        
        # Deduplicar por ID
        seen = set()
        unique = []
        for r in combined:
            if r["id"] not in seen:
                seen.add(r["id"])
                unique.append(r)
        
        return {
            "success": True,
            "found": len(unique) > 0,
            "count": len(unique),
            "query": ip,
            "type": "ip",
            "results": unique
        }
    
    async def search_domain(self, domain: str, limit: int = 50) -> Dict[str, Any]:
        """Buscar dominio en MISP"""
        return await self.search_ioc(domain, "domain", limit)
    
    async def search_hash(self, hash_value: str, limit: int = 50) -> Dict[str, Any]:
        """Buscar hash (MD5/SHA1/SHA256) en MISP"""
        hash_len = len(hash_value)
        if hash_len == 32:
            ioc_type = "md5"
        elif hash_len == 40:
            ioc_type = "sha1"
        elif hash_len == 64:
            ioc_type = "sha256"
        else:
            ioc_type = None
        
        return await self.search_ioc(hash_value, ioc_type, limit)
    
    async def search_email(self, email: str, limit: int = 50) -> Dict[str, Any]:
        """Buscar email en MISP"""
        return await self.search_ioc(email, "email", limit)
    
    async def search_url(self, url: str, limit: int = 50) -> Dict[str, Any]:
        """Buscar URL en MISP"""
        return await self.search_ioc(url, "url", limit)
    
    # =========================================================================
    # Eventos
    # =========================================================================
    
    async def get_events(
        self,
        limit: int = 50,
        page: int = 1,
        from_date: str = None,
        to_date: str = None,
        threat_level: int = None,
        tags: List[str] = None,
        published: bool = None
    ) -> Dict[str, Any]:
        """
        Obtener lista de eventos
        
        Args:
            limit: Número máximo de eventos
            page: Página para paginación
            from_date: Fecha inicio (YYYY-MM-DD)
            to_date: Fecha fin (YYYY-MM-DD)
            threat_level: 1=High, 2=Medium, 3=Low, 4=Undefined
            tags: Lista de tags para filtrar
            published: Solo eventos publicados
        """
        search_body = {
            "returnFormat": "json",
            "limit": limit,
            "page": page,
            "metadata": False
        }
        
        if from_date:
            search_body["from"] = from_date
        if to_date:
            search_body["to"] = to_date
        if threat_level:
            search_body["threat_level_id"] = threat_level
        if tags:
            search_body["tags"] = tags
        if published is not None:
            search_body["published"] = published
        
        result = await self._request("POST", "/events/restSearch", data=search_body)
        
        if result.get("success"):
            events = result["data"].get("response", [])
            return {
                "success": True,
                "count": len(events),
                "page": page,
                "limit": limit,
                "events": [
                    self._parse_event(e.get("Event", {}))
                    for e in events
                ]
            }
        return result
    
    async def get_event(self, event_id: Union[int, str]) -> Dict[str, Any]:
        """Obtener evento específico por ID"""
        result = await self._request("GET", f"/events/view/{event_id}")
        
        if result.get("success"):
            event = result["data"].get("Event", {})
            return {
                "success": True,
                "event": self._parse_event(event, include_attributes=True)
            }
        return result
    
    def _parse_event(self, event: dict, include_attributes: bool = False) -> dict:
        """Parsear evento de MISP a formato simplificado"""
        parsed = {
            "id": event.get("id"),
            "uuid": event.get("uuid"),
            "info": event.get("info"),
            "date": event.get("date"),
            "threat_level": self._get_threat_level_name(event.get("threat_level_id")),
            "threat_level_id": event.get("threat_level_id"),
            "analysis": self._get_analysis_name(event.get("analysis")),
            "published": event.get("published"),
            "org": event.get("Org", {}).get("name"),
            "orgc": event.get("Orgc", {}).get("name"),
            "attribute_count": event.get("attribute_count", 0),
            "timestamp": datetime.fromtimestamp(
                int(event.get("timestamp", 0))
            ).isoformat() if event.get("timestamp") else None,
            "tags": [t.get("name") for t in event.get("Tag", [])],
            "galaxies": [
                {
                    "name": g.get("name"),
                    "type": g.get("type"),
                    "description": g.get("description")
                }
                for g in event.get("Galaxy", [])
            ]
        }
        
        if include_attributes:
            parsed["attributes"] = [
                {
                    "id": attr.get("id"),
                    "type": attr.get("type"),
                    "category": attr.get("category"),
                    "value": attr.get("value"),
                    "comment": attr.get("comment"),
                    "to_ids": attr.get("to_ids"),
                    "tags": [t.get("name") for t in attr.get("Tag", [])]
                }
                for attr in event.get("Attribute", [])
            ]
            parsed["objects"] = [
                {
                    "id": obj.get("id"),
                    "name": obj.get("name"),
                    "description": obj.get("description"),
                    "meta_category": obj.get("meta-category"),
                    "attributes_count": len(obj.get("Attribute", []))
                }
                for obj in event.get("Object", [])
            ]
        
        return parsed
    
    def _get_threat_level_name(self, level_id: str) -> str:
        """Convertir threat_level_id a nombre"""
        levels = {
            "1": "high",
            "2": "medium", 
            "3": "low",
            "4": "undefined"
        }
        return levels.get(str(level_id), "unknown")
    
    def _get_analysis_name(self, analysis_id: str) -> str:
        """Convertir analysis a nombre"""
        analysis = {
            "0": "initial",
            "1": "ongoing",
            "2": "completed"
        }
        return analysis.get(str(analysis_id), "unknown")
    
    # =========================================================================
    # Feeds
    # =========================================================================
    
    async def get_feeds(self) -> Dict[str, Any]:
        """Obtener lista de feeds configurados"""
        result = await self._request("GET", "/feeds")
        
        if result.get("success"):
            feeds = result["data"]
            return {
                "success": True,
                "count": len(feeds),
                "feeds": [
                    {
                        "id": f.get("Feed", {}).get("id"),
                        "name": f.get("Feed", {}).get("name"),
                        "provider": f.get("Feed", {}).get("provider"),
                        "url": f.get("Feed", {}).get("url"),
                        "enabled": f.get("Feed", {}).get("enabled"),
                        "caching_enabled": f.get("Feed", {}).get("caching_enabled"),
                        "source_format": f.get("Feed", {}).get("source_format")
                    }
                    for f in feeds if isinstance(f, dict)
                ]
            }
        return result
    
    async def fetch_feed(self, feed_id: int) -> Dict[str, Any]:
        """Forzar actualización de un feed"""
        result = await self._request("GET", f"/feeds/fetchFromFeed/{feed_id}")
        return result
    
    # =========================================================================
    # Taxonomies y Galaxy
    # =========================================================================
    
    async def get_taxonomies(self) -> Dict[str, Any]:
        """Obtener taxonomías disponibles"""
        result = await self._request("GET", "/taxonomies")
        
        if result.get("success"):
            taxonomies = result["data"]
            return {
                "success": True,
                "count": len(taxonomies),
                "taxonomies": [
                    {
                        "id": t.get("Taxonomy", {}).get("id"),
                        "namespace": t.get("Taxonomy", {}).get("namespace"),
                        "description": t.get("Taxonomy", {}).get("description"),
                        "version": t.get("Taxonomy", {}).get("version"),
                        "enabled": t.get("Taxonomy", {}).get("enabled")
                    }
                    for t in taxonomies if isinstance(t, dict)
                ]
            }
        return result
    
    async def get_galaxies(self) -> Dict[str, Any]:
        """Obtener galaxies disponibles (ATT&CK, etc)"""
        result = await self._request("GET", "/galaxies")
        
        if result.get("success"):
            galaxies = result["data"]
            return {
                "success": True,
                "count": len(galaxies),
                "galaxies": [
                    {
                        "id": g.get("Galaxy", {}).get("id"),
                        "name": g.get("Galaxy", {}).get("name"),
                        "type": g.get("Galaxy", {}).get("type"),
                        "description": g.get("Galaxy", {}).get("description"),
                        "namespace": g.get("Galaxy", {}).get("namespace")
                    }
                    for g in galaxies if isinstance(g, dict)
                ]
            }
        return result
    
    # =========================================================================
    # Exportar/Importar para casos
    # =========================================================================
    
    async def export_case_to_misp(
        self,
        case_id: str,
        iocs: List[Dict],
        event_info: str = None,
        threat_level: int = 2,
        analysis: int = 1,
        distribution: int = 0,
        tags: List[str] = None
    ) -> Dict[str, Any]:
        """
        Exportar IOCs de un caso a un evento MISP
        
        Args:
            case_id: ID del caso
            iocs: Lista de IOCs con {type, value, comment}
            event_info: Descripción del evento
            threat_level: 1=High, 2=Medium, 3=Low, 4=Undefined
            analysis: 0=Initial, 1=Ongoing, 2=Completed
            distribution: 0=Org only, 1=Community, 2=Connected, 3=All
            tags: Tags adicionales
        """
        event_data = {
            "Event": {
                "info": event_info or f"Case {case_id} - Forensic Investigation",
                "threat_level_id": str(threat_level),
                "analysis": str(analysis),
                "distribution": str(distribution),
                "date": datetime.now().strftime("%Y-%m-%d"),
                "Attribute": [],
                "Tag": [{"name": t} for t in (tags or [])]
            }
        }
        
        # Mapear tipos de IOC
        type_mapping = {
            "ip": "ip-dst",
            "ip_src": "ip-src",
            "ip_dst": "ip-dst",
            "domain": "domain",
            "url": "url",
            "email": "email",
            "md5": "md5",
            "sha1": "sha1", 
            "sha256": "sha256",
            "filename": "filename",
            "hostname": "hostname",
            "user_agent": "user-agent"
        }
        
        for ioc in iocs:
            ioc_type = type_mapping.get(ioc.get("type", "").lower(), "text")
            attr = {
                "type": ioc_type,
                "category": self._get_category_for_type(ioc_type),
                "value": ioc["value"],
                "comment": ioc.get("comment", f"From case {case_id}"),
                "to_ids": True
            }
            event_data["Event"]["Attribute"].append(attr)
        
        result = await self._request("POST", "/events/add", data=event_data)
        
        if result.get("success"):
            event = result["data"].get("Event", {})
            return {
                "success": True,
                "event_id": event.get("id"),
                "uuid": event.get("uuid"),
                "info": event.get("info"),
                "url": f"{self.base_url}/events/view/{event.get('id')}"
            }
        return result
    
    def _get_category_for_type(self, attr_type: str) -> str:
        """Obtener categoría MISP para un tipo de atributo"""
        categories = {
            "ip-src": "Network activity",
            "ip-dst": "Network activity",
            "domain": "Network activity",
            "url": "Network activity",
            "hostname": "Network activity",
            "email": "Payload delivery",
            "md5": "Payload delivery",
            "sha1": "Payload delivery",
            "sha256": "Payload delivery",
            "filename": "Payload delivery",
            "user-agent": "Network activity",
            "text": "External analysis"
        }
        return categories.get(attr_type, "External analysis")
    
    async def import_event_to_case(
        self,
        event_id: Union[int, str],
        case_id: str
    ) -> Dict[str, Any]:
        """
        Importar atributos de un evento MISP a un caso
        
        Retorna lista de IOCs para agregar al caso
        """
        event_result = await self.get_event(event_id)
        
        if not event_result.get("success"):
            return event_result
        
        event = event_result["event"]
        iocs = []
        
        for attr in event.get("attributes", []):
            iocs.append({
                "type": attr["type"],
                "value": attr["value"],
                "category": attr["category"],
                "comment": attr.get("comment", ""),
                "source": "misp",
                "source_event": event_id,
                "source_event_info": event["info"],
                "threat_level": event["threat_level"],
                "tags": attr.get("tags", []),
                "to_ids": attr.get("to_ids", False)
            })
        
        return {
            "success": True,
            "case_id": case_id,
            "event_id": event_id,
            "event_info": event["info"],
            "iocs_count": len(iocs),
            "iocs": iocs
        }


# =============================================================================
# Singleton instance
# =============================================================================

_misp_client: Optional[MISPClient] = None

def get_misp_client() -> MISPClient:
    """Obtener instancia singleton del cliente MISP"""
    global _misp_client
    if _misp_client is None:
        _misp_client = MISPClient()
    return _misp_client


# =============================================================================
# Helper functions para uso directo
# =============================================================================

async def misp_search_ioc(value: str, ioc_type: str = None) -> Dict[str, Any]:
    """Buscar IOC en MISP"""
    client = get_misp_client()
    return await client.search_ioc(value, ioc_type)

async def misp_get_events(limit: int = 50, **kwargs) -> Dict[str, Any]:
    """Obtener eventos de MISP"""
    client = get_misp_client()
    return await client.get_events(limit=limit, **kwargs)

async def misp_test_connection() -> Dict[str, Any]:
    """Probar conexión con MISP"""
    client = get_misp_client()
    return await client.test_connection()

async def misp_get_statistics() -> Dict[str, Any]:
    """Obtener estadísticas de MISP"""
    client = get_misp_client()
    return await client.get_statistics()
