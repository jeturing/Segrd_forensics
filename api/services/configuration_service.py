"""
MCP Kali Forensics - Configuration Service
Servicio para gestionar configuraciones de APIs
"""

import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
import httpx

from api.models.configuration import ApiConfiguration, ConfigCategory

logger = logging.getLogger(__name__)

# ============================================================================
# DEFINICIÓN DE CONFIGURACIONES DE API
# ============================================================================

# Configuraciones REQUERIDAS (del .env, no se guardan en BD)
REQUIRED_CONFIGS = {
    "API_KEY",
    "DATABASE_URL", 
}

# Definición de todas las APIs soportadas
API_DEFINITIONS = [
    # Threat Intelligence
    {
        "key": "SHODAN_API_KEY",
        "display_name": "Shodan API Key",
        "description": "Network intelligence and device discovery",
        "category": ConfigCategory.NETWORK,
        "service_name": "Shodan",
        "service_url": "https://developer.shodan.io/api",
        "is_secret": True,
        "validation_endpoint": "https://api.shodan.io/api-info?key={key}"
    },
    {
        "key": "VT_API_KEY",
        "display_name": "VirusTotal API Key",
        "description": "File, URL, and domain malware analysis",
        "category": ConfigCategory.MALWARE,
        "service_name": "VirusTotal",
        "service_url": "https://developers.virustotal.com/reference",
        "is_secret": True,
        "validation_endpoint": "https://www.virustotal.com/api/v3/users/{key}"
    },
    {
        "key": "HIBP_API_KEY",
        "display_name": "HaveIBeenPwned API Key",
        "description": "Credential breach database lookups",
        "category": ConfigCategory.CREDENTIALS,
        "service_name": "HaveIBeenPwned",
        "service_url": "https://haveibeenpwned.com/API/v3",
        "is_secret": True,
    },
    {
        "key": "INTELX_API_KEY",
        "display_name": "Intelligence X API Key",
        "description": "Dark web and data breach intelligence",
        "category": ConfigCategory.THREAT_INTEL,
        "service_name": "IntelligenceX",
        "service_url": "https://intelx.io/developers",
        "is_secret": True,
    },
    {
        "key": "SECURITYTRAILS_API_KEY",
        "display_name": "SecurityTrails API Key",
        "description": "DNS and domain intelligence",
        "category": ConfigCategory.NETWORK,
        "service_name": "SecurityTrails",
        "service_url": "https://securitytrails.com/corp/api",
        "is_secret": True,
    },
    {
        "key": "HUNTER_API_KEY",
        "display_name": "Hunter.io API Key",
        "description": "Email discovery and verification",
        "category": ConfigCategory.IDENTITY,
        "service_name": "Hunter",
        "service_url": "https://hunter.io/api-documentation",
        "is_secret": True,
    },
    {
        "key": "FULLCONTACT_API_KEY",
        "display_name": "FullContact API Key",
        "description": "Identity resolution and enrichment",
        "category": ConfigCategory.IDENTITY,
        "service_name": "FullContact",
        "service_url": "https://docs.fullcontact.com/",
        "is_secret": True,
    },
    {
        "key": "CENSYS_API_ID",
        "display_name": "Censys API ID",
        "description": "Internet-wide scanning (ID)",
        "category": ConfigCategory.NETWORK,
        "service_name": "Censys",
        "service_url": "https://search.censys.io/api",
        "is_secret": True,
    },
    {
        "key": "CENSYS_API_SECRET",
        "display_name": "Censys API Secret",
        "description": "Internet-wide scanning (Secret)",
        "category": ConfigCategory.NETWORK,
        "service_name": "Censys",
        "service_url": "https://search.censys.io/api",
        "is_secret": True,
    },
    {
        "key": "XFORCE_API_KEY",
        "display_name": "IBM X-Force API Key",
        "description": "IBM threat intelligence platform",
        "category": ConfigCategory.THREAT_INTEL,
        "service_name": "X-Force",
        "service_url": "https://exchange.xforce.ibmcloud.com/api",
        "is_secret": True,
    },
    {
        "key": "XFORCE_API_SECRET",
        "display_name": "IBM X-Force API Secret",
        "description": "IBM threat intelligence platform (Secret)",
        "category": ConfigCategory.THREAT_INTEL,
        "service_name": "X-Force",
        "service_url": "https://exchange.xforce.ibmcloud.com/api",
        "is_secret": True,
    },
    {
        "key": "HYBRID_ANALYSIS_KEY",
        "display_name": "Hybrid Analysis API Key",
        "description": "Malware sandbox analysis",
        "category": ConfigCategory.MALWARE,
        "service_name": "Hybrid Analysis",
        "service_url": "https://www.hybrid-analysis.com/docs/api/v2",
        "is_secret": True,
    },
    {
        "key": "FRAUDGUARD_USER",
        "display_name": "FraudGuard Username",
        "description": "IP and proxy detection (User)",
        "category": ConfigCategory.NETWORK,
        "service_name": "FraudGuard",
        "service_url": "https://fraudguard.io/api-documentation",
        "is_secret": True,
    },
    {
        "key": "FRAUDGUARD_PASS",
        "display_name": "FraudGuard Password",
        "description": "IP and proxy detection (Password)",
        "category": ConfigCategory.NETWORK,
        "service_name": "FraudGuard",
        "service_url": "https://fraudguard.io/api-documentation",
        "is_secret": True,
    },
    {
        "key": "HONEYPOT_API_KEY",
        "display_name": "Honeypot Checker API Key",
        "description": "IP reputation checking",
        "category": ConfigCategory.NETWORK,
        "service_name": "Honeypot Checker",
        "service_url": "https://www.projecthoneypot.org/httpbl_api.php",
        "is_secret": True,
    },
    {
        "key": "MALWAREPATROL_API_KEY",
        "display_name": "Malware Patrol API Key",
        "description": "Malware intelligence feeds",
        "category": ConfigCategory.MALWARE,
        "service_name": "Malware Patrol",
        "service_url": "https://www.malwarepatrol.net/",
        "is_secret": True,
    },
    # Cloud / M365
    {
        "key": "M365_TENANT_ID",
        "display_name": "Microsoft 365 Tenant ID",
        "description": "Azure AD Tenant ID for M365",
        "category": ConfigCategory.CLOUD,
        "service_name": "Microsoft 365",
        "service_url": "https://portal.azure.com",
        "is_secret": False,
    },
    {
        "key": "M365_CLIENT_ID",
        "display_name": "Microsoft 365 Client ID",
        "description": "App Registration Client ID",
        "category": ConfigCategory.CLOUD,
        "service_name": "Microsoft 365",
        "service_url": "https://portal.azure.com",
        "is_secret": False,
    },
    {
        "key": "M365_CLIENT_SECRET",
        "display_name": "Microsoft 365 Client Secret",
        "description": "App Registration Client Secret",
        "category": ConfigCategory.CLOUD,
        "service_name": "Microsoft 365",
        "service_url": "https://portal.azure.com",
        "is_secret": True,
    },
    # MISP
    {
        "key": "MISP_URL",
        "display_name": "MISP Server URL",
        "description": "URL del servidor MISP",
        "category": ConfigCategory.THREAT_INTEL,
        "service_name": "MISP",
        "service_url": "https://www.misp-project.org/documentation/",
        "is_secret": False,
    },
    {
        "key": "MISP_API_KEY",
        "display_name": "MISP API Key",
        "description": "API Key de autenticación MISP",
        "category": ConfigCategory.THREAT_INTEL,
        "service_name": "MISP",
        "service_url": "https://www.misp-project.org/documentation/",
        "is_secret": True,
    },
    {
        "key": "MISP_VERIFY_SSL",
        "display_name": "MISP Verify SSL",
        "description": "Verificar certificado SSL de MISP",
        "category": ConfigCategory.THREAT_INTEL,
        "service_name": "MISP",
        "service_url": "https://www.misp-project.org/documentation/",
        "is_secret": False,
    },
    # Notifications
    {
        "key": "SLACK_WEBHOOK_URL",
        "display_name": "Slack Webhook URL",
        "description": "Webhook para alertas en Slack",
        "category": ConfigCategory.NOTIFICATION,
        "service_name": "Slack",
        "service_url": "https://api.slack.com/messaging/webhooks",
        "is_secret": True,
    },
    {
        "key": "DISCORD_WEBHOOK_URL",
        "display_name": "Discord Webhook URL",
        "description": "Webhook para alertas en Discord",
        "category": ConfigCategory.NOTIFICATION,
        "service_name": "Discord",
        "service_url": "https://discord.com/developers/docs/resources/webhook",
        "is_secret": True,
    },
    # Google
    {
        "key": "GOOGLE_API_KEY",
        "display_name": "Google API Key",
        "description": "API Key general de Google",
        "category": ConfigCategory.INTEGRATION,
        "service_name": "Google",
        "service_url": "https://console.cloud.google.com/apis",
        "is_secret": True,
    },
    # Redis
    {
        "key": "REDIS_HOST",
        "display_name": "Redis Host",
        "description": "Servidor Redis para caché",
        "category": ConfigCategory.GENERAL,
        "service_name": "Redis",
        "service_url": "https://redis.io/documentation",
        "is_secret": False,
    },
    {
        "key": "REDIS_PORT",
        "display_name": "Redis Port",
        "description": "Puerto del servidor Redis",
        "category": ConfigCategory.GENERAL,
        "service_name": "Redis",
        "service_url": "https://redis.io/documentation",
        "is_secret": False,
    },
    {
        "key": "REDIS_PASSWORD",
        "display_name": "Redis Password",
        "description": "Contraseña de Redis (si aplica)",
        "category": ConfigCategory.GENERAL,
        "service_name": "Redis",
        "service_url": "https://redis.io/documentation",
        "is_secret": True,
    },
    # System URLs - Configuración del Sistema
    {
        "key": "API_BASE_URL",
        "display_name": "API Base URL",
        "description": "URL base del backend API (ej: http://localhost:9000)",
        "category": ConfigCategory.GENERAL,
        "service_name": "Sistema",
        "service_url": None,
        "is_secret": False,
    },
    {
        "key": "API_PORT",
        "display_name": "API Port",
        "description": "Puerto del backend API (default: 9000)",
        "category": ConfigCategory.GENERAL,
        "service_name": "Sistema",
        "service_url": None,
        "is_secret": False,
    },
    {
        "key": "FRONTEND_URL",
        "display_name": "Frontend URL",
        "description": "URL del frontend React (ej: http://localhost:3000)",
        "category": ConfigCategory.GENERAL,
        "service_name": "Sistema",
        "service_url": None,
        "is_secret": False,
    },
    {
        "key": "FRONTEND_PORT",
        "display_name": "Frontend Port",
        "description": "Puerto del frontend (default: 3000)",
        "category": ConfigCategory.GENERAL,
        "service_name": "Sistema",
        "service_url": None,
        "is_secret": False,
    },
    {
        "key": "WS_URL",
        "display_name": "WebSocket URL",
        "description": "URL del WebSocket (ej: ws://localhost:9000/ws)",
        "category": ConfigCategory.GENERAL,
        "service_name": "Sistema",
        "service_url": None,
        "is_secret": False,
    },
    {
        "key": "CORS_ORIGINS",
        "display_name": "CORS Origins",
        "description": "Orígenes permitidos para CORS (separados por coma)",
        "category": ConfigCategory.GENERAL,
        "service_name": "Sistema",
        "service_url": None,
        "is_secret": False,
    },
]


class ConfigurationService:
    """Servicio para gestionar configuraciones de API"""

    @staticmethod
    def initialize_configurations(db: Session) -> Dict[str, Any]:
        """
        Inicializar configuraciones desde .env a la base de datos
        Solo para APIs OPCIONALES
        """
        created = 0
        updated = 0
        skipped = 0

        for api_def in API_DEFINITIONS:
            key = api_def["key"]
            
            # Saltar configuraciones requeridas
            if key in REQUIRED_CONFIGS:
                skipped += 1
                continue

            # Buscar si ya existe
            existing = db.query(ApiConfiguration).filter(
                ApiConfiguration.key == key
            ).first()

            # Obtener valor del .env
            env_value = os.getenv(key, "")

            if existing:
                # Actualizar solo si no tiene valor y hay uno en .env
                if not existing.value and env_value:
                    existing.value = env_value
                    existing.is_configured = bool(env_value)
                    existing.updated_at = datetime.utcnow()
                    updated += 1
            else:
                # Crear nueva entrada
                config = ApiConfiguration(
                    key=key,
                    display_name=api_def["display_name"],
                    description=api_def.get("description"),
                    category=api_def.get("category", ConfigCategory.GENERAL),
                    service_name=api_def.get("service_name"),
                    service_url=api_def.get("service_url"),
                    is_secret=api_def.get("is_secret", True),
                    value=env_value if env_value else None,
                    is_configured=bool(env_value),
                    is_enabled=True
                )
                db.add(config)
                created += 1

        db.commit()
        
        return {
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "total": len(API_DEFINITIONS)
        }

    @staticmethod
    def get_all_configurations(db: Session, category: Optional[str] = None) -> List[Dict]:
        """Obtener todas las configuraciones"""
        query = db.query(ApiConfiguration)
        
        if category:
            try:
                cat_enum = ConfigCategory(category)
                query = query.filter(ApiConfiguration.category == cat_enum)
            except ValueError:
                pass

        configs = query.order_by(
            ApiConfiguration.category,
            ApiConfiguration.service_name,
            ApiConfiguration.key
        ).all()

        return [c.to_dict(include_value=True) for c in configs]

    @staticmethod
    def get_configuration(db: Session, key: str) -> Optional[Dict]:
        """Obtener una configuración específica"""
        config = db.query(ApiConfiguration).filter(
            ApiConfiguration.key == key
        ).first()
        
        if config:
            return config.to_dict(include_value=True)
        return None

    @staticmethod
    def update_configuration(
        db: Session, 
        key: str, 
        value: str,
        enabled: Optional[bool] = None,
        updated_by: Optional[str] = None
    ) -> Optional[Dict]:
        """Actualizar una configuración"""
        config = db.query(ApiConfiguration).filter(
            ApiConfiguration.key == key
        ).first()

        if not config:
            return None

        config.value = value
        config.is_configured = bool(value)
        config.updated_at = datetime.utcnow()
        
        if updated_by:
            config.updated_by = updated_by
        if enabled is not None:
            config.is_enabled = enabled

        db.commit()
        db.refresh(config)

        # También actualizar variable de entorno en runtime
        if value:
            os.environ[key] = value

        logger.info(f"✅ Configuración actualizada: {key}")
        return config.to_dict(include_value=True)

    @staticmethod
    def delete_configuration_value(db: Session, key: str) -> bool:
        """Eliminar valor de una configuración (no la configuración en sí)"""
        config = db.query(ApiConfiguration).filter(
            ApiConfiguration.key == key
        ).first()

        if not config:
            return False

        config.value = None
        config.is_configured = False
        config.validation_status = None
        config.last_validated = None
        config.updated_at = datetime.utcnow()

        db.commit()
        
        # Remover de variables de entorno
        if key in os.environ:
            del os.environ[key]

        logger.info(f"🗑️ Valor eliminado: {key}")
        return True

    @staticmethod
    async def validate_configuration(db: Session, key: str) -> Dict[str, Any]:
        """Validar una configuración de API"""
        config = db.query(ApiConfiguration).filter(
            ApiConfiguration.key == key
        ).first()

        if not config:
            return {"valid": False, "error": "Configuration not found"}

        if not config.value:
            return {"valid": False, "error": "No value configured"}

        # Buscar definición con endpoint de validación
        api_def = next(
            (d for d in API_DEFINITIONS if d["key"] == key),
            None
        )

        validation_result = {
            "key": key,
            "valid": False,
            "message": "Validation not available for this API",
            "timestamp": datetime.utcnow().isoformat()
        }

        try:
            if key == "SHODAN_API_KEY":
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.get(
                        f"https://api.shodan.io/api-info?key={config.value}"
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        validation_result["valid"] = True
                        validation_result["message"] = f"Valid - Plan: {data.get('plan', 'unknown')}, Credits: {data.get('query_credits', 0)}"
                    else:
                        validation_result["message"] = f"Invalid - HTTP {resp.status_code}"

            elif key == "VT_API_KEY":
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.get(
                        "https://www.virustotal.com/api/v3/users/me",
                        headers={"x-apikey": config.value}
                    )
                    if resp.status_code == 200:
                        validation_result["valid"] = True
                        validation_result["message"] = "Valid API Key"
                    else:
                        validation_result["message"] = f"Invalid - HTTP {resp.status_code}"

            elif key == "SECURITYTRAILS_API_KEY":
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.get(
                        "https://api.securitytrails.com/v1/ping",
                        headers={"APIKEY": config.value}
                    )
                    if resp.status_code == 200:
                        validation_result["valid"] = True
                        validation_result["message"] = "Valid API Key"
                    else:
                        validation_result["message"] = f"Invalid - HTTP {resp.status_code}"

            elif key == "HUNTER_API_KEY":
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.get(
                        f"https://api.hunter.io/v2/account?api_key={config.value}"
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        searches = data.get("data", {}).get("requests", {}).get("searches", {})
                        validation_result["valid"] = True
                        validation_result["message"] = f"Valid - Searches: {searches.get('available', 0)}/{searches.get('used', 0)}"
                    else:
                        validation_result["message"] = f"Invalid - HTTP {resp.status_code}"

            elif key == "INTELX_API_KEY":
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.get(
                        "https://2.intelx.io/authenticate/info",
                        headers={"x-key": config.value}
                    )
                    if resp.status_code == 200:
                        validation_result["valid"] = True
                        validation_result["message"] = "Valid API Key"
                    else:
                        validation_result["message"] = f"Invalid - HTTP {resp.status_code}"

            else:
                validation_result["message"] = "Manual validation required - no automated check available"

        except httpx.TimeoutException:
            validation_result["message"] = "Validation timeout - API unreachable"
        except Exception as e:
            validation_result["message"] = f"Validation error: {str(e)}"

        # Guardar resultado
        config.last_validated = datetime.utcnow()
        config.validation_status = "valid" if validation_result["valid"] else "invalid"
        db.commit()

        return validation_result

    @staticmethod
    def get_configuration_summary(db: Session) -> Dict[str, Any]:
        """Obtener resumen de configuraciones por categoría"""
        configs = db.query(ApiConfiguration).all()

        summary = {
            "total": len(configs),
            "configured": sum(1 for c in configs if c.is_configured),
            "enabled": sum(1 for c in configs if c.is_enabled),
            "by_category": {},
            "by_service": {}
        }

        for config in configs:
            # Por categoría
            cat = config.category.value if config.category else "general"
            if cat not in summary["by_category"]:
                summary["by_category"][cat] = {"total": 0, "configured": 0}
            summary["by_category"][cat]["total"] += 1
            if config.is_configured:
                summary["by_category"][cat]["configured"] += 1

            # Por servicio
            svc = config.service_name or "Other"
            if svc not in summary["by_service"]:
                summary["by_service"][svc] = {"total": 0, "configured": 0}
            summary["by_service"][svc]["total"] += 1
            if config.is_configured:
                summary["by_service"][svc]["configured"] += 1

        return summary

    @staticmethod
    def export_to_env_format(db: Session, include_secrets: bool = False) -> str:
        """Exportar configuraciones en formato .env"""
        configs = db.query(ApiConfiguration).filter(
            ApiConfiguration.is_configured == True
        ).all()

        lines = ["# MCP Kali Forensics - Exported Configuration", ""]
        
        current_category = None
        for config in configs:
            if config.category != current_category:
                current_category = config.category
                lines.append(f"\n# {current_category.value.upper() if current_category else 'GENERAL'}")
            
            if config.is_secret and not include_secrets:
                lines.append(f"# {config.key}=<configured but hidden>")
            else:
                lines.append(f"{config.key}={config.value or ''}")

        return "\n".join(lines)


# Singleton para acceso rápido
config_service = ConfigurationService()
