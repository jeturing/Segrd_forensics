"""
Registro del MCP en Jeturing CORE
"""

import httpx
from api.config import settings
import logging

logger = logging.getLogger(__name__)

async def register_with_jeturing_core():
    """
    Registra el MCP en Jeturing CORE AppRegistry
    """
    if not settings.JETURING_CORE_ENABLED:
        logger.info("⏭️ Registro en Jeturing CORE deshabilitado")
        return
    
    registration_data = {
        "app_name": "mcp-kali-forensics",
        "app_type": "mcp",
        "version": "1.0.0",
        "capabilities": [
            "m365_forensics",
            "credential_analysis",
            "endpoint_scanning",
            "ioc_detection"
        ],
        "endpoints": {
            "health": "/health",
            "m365_analyze": "/forensics/m365/analyze",
            "credentials_check": "/forensics/credentials/check",
            "endpoint_scan": "/forensics/endpoint/scan",
            "case_status": "/forensics/case/{case_id}/status"
        },
        "metadata": {
            "tools": [
                "Sparrow 365",
                "Hawk",
                "O365 Extractor",
                "Loki",
                "YARA",
                "Volatility 3",
                "OSQuery"
            ]
        }
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.JETURING_CORE_URL}/api/registry/mcp",
                json=registration_data,
                headers={
                    "X-API-Key": settings.JETURING_CORE_API_KEY
                },
                timeout=10.0
            )
            response.raise_for_status()
            logger.info(f"✅ MCP registrado en Jeturing CORE: {response.json()}")
    except Exception as e:
        logger.error(f"❌ Error al registrar en Jeturing CORE: {e}")
        raise
