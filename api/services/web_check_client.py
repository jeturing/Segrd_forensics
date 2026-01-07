"""
Web Check API Client
====================
Cliente para integrar web-check-api (Go-based OSINT API)
con el módulo de Threat Hunting
"""

import httpx
import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

WEB_CHECK_API_BASE_URL = "http://localhost:8080"
WEB_CHECK_API_TIMEOUT = 30
WEB_CHECK_CACHE_TTL = 3600

class WebCheckClient:
    """Cliente para web-check-api"""
    
    def __init__(self, base_url: str = WEB_CHECK_API_BASE_URL, timeout: int = WEB_CHECK_API_TIMEOUT):
        self.base_url = base_url
        self.timeout = timeout
        self._client = None
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Obtener cliente HTTP async"""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client
    
    async def close(self):
        """Cerrar cliente HTTP"""
        if self._client:
            await self._client.aclose()
    
    async def analyze_domain(self, domain: str, categories: Optional[List[str]] = None) -> Dict[str, Any]:
        """Analizar un dominio completo (múltiples checks)"""
        if not categories:
            categories = ["dns", "tls", "headers", "security", "firewall", "dnssec", "blocklists"]
        
        results = {
            "domain": domain,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {}
        }
        
        tasks = []
        for category in categories:
            if category == "dns":
                tasks.append(self.get_dns_records(domain))
            elif category == "tls":
                tasks.append(self.get_tls_certificate(domain))
            elif category == "headers":
                tasks.append(self.get_http_headers(domain))
            elif category == "security":
                tasks.append(self.get_security_headers(domain))
            elif category == "firewall":
                tasks.append(self.get_firewall_detection(domain))
            elif category == "dnssec":
                tasks.append(self.get_dnssec_status(domain))
            elif category == "blocklists":
                tasks.append(self.get_blocklist_status(domain))
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, category in enumerate(categories):
            if i < len(responses):
                response = responses[i]
                if isinstance(response, Exception):
                    results["checks"][category] = {"error": str(response), "status": "failed"}
                else:
                    results["checks"][category] = response
        
        return results
    
    async def get_dns_records(self, domain: str) -> Dict[str, Any]:
        """Obtener registros DNS"""
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/api/dns", params={"url": domain})
            response.raise_for_status()
            data = response.json()
            
            return {
                "status": "success",
                "records": data.get("records", {})
            }
        except Exception as e:
            logger.error(f"Error en DNS check: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    async def get_tls_certificate(self, domain: str) -> Dict[str, Any]:
        """Obtener información del certificado TLS/SSL"""
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/api/tls", params={"url": domain})
            response.raise_for_status()
            data = response.json()
            
            return {
                "status": "success",
                "certificate": data
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def get_http_headers(self, domain: str) -> Dict[str, Any]:
        """Obtener headers HTTP"""
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/api/headers", params={"url": domain})
            response.raise_for_status()
            data = response.json()
            return {"status": "success", "headers": data.get("headers", {})}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def get_security_headers(self, domain: str) -> Dict[str, Any]:
        """Obtener análisis de headers de seguridad"""
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/api/http-security", params={"url": domain})
            response.raise_for_status()
            data = response.json()
            return {"status": "success", "security_headers": data}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def get_firewall_detection(self, domain: str) -> Dict[str, Any]:
        """Detectar WAF/Firewall"""
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/api/firewall", params={"url": domain})
            response.raise_for_status()
            data = response.json()
            return {"status": "success", "firewall": data}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def get_dnssec_status(self, domain: str) -> Dict[str, Any]:
        """Verificar estado de DNSSEC"""
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/api/dnssec", params={"url": domain})
            response.raise_for_status()
            data = response.json()
            return {"status": "success", "dnssec": data}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def get_blocklist_status(self, domain: str) -> Dict[str, Any]:
        """Verificar si el dominio está en listas de bloqueo"""
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/api/block-lists", params={"url": domain})
            response.raise_for_status()
            data = response.json()
            return {"status": "success", "blocklists": data}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def get_ports_scan(self, domain: str, ports: Optional[List[int]] = None) -> Dict[str, Any]:
        """Escanear puertos abiertos"""
        if not ports:
            ports = [20, 21, 22, 23, 25, 53, 80, 443, 3306, 3389, 5432, 8080, 8443]
        
        try:
            client = await self._get_client()
            response = await client.get(
                f"{self.base_url}/api/ports",
                params={"url": domain, "ports": ",".join(map(str, ports))}
            )
            response.raise_for_status()
            data = response.json()
            return {"status": "success", "ports": data}
        except Exception as e:
            return {"status": "error", "error": str(e)}

web_check_client = WebCheckClient()
