"""
MCP Kali Forensics - Configuration Routes
Endpoints para gestión de configuraciones de API
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
import logging

from api.database import get_db
from api.services.configuration_service import ConfigurationService, API_DEFINITIONS
from api.models.configuration import ApiConfiguration, ConfigCategory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/configuration", tags=["Configuration"])


# ============================================================================
# Pydantic Models
# ============================================================================

class ConfigurationUpdate(BaseModel):
    """Modelo para actualizar una configuración"""
    value: str = Field(..., description="Nuevo valor de la configuración")
    enabled: Optional[bool] = Field(None, description="Habilitar/deshabilitar")


class ConfigurationBulkUpdate(BaseModel):
    """Modelo para actualizar múltiples configuraciones"""
    configurations: Dict[str, str] = Field(
        ..., 
        description="Diccionario key: value de configuraciones"
    )


class ValidationRequest(BaseModel):
    """Modelo para validar configuraciones"""
    keys: List[str] = Field(..., description="Lista de keys a validar")


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/")
async def list_configurations(
    category: Optional[str] = Query(None, description="Filtrar por categoría"),
    db: Session = Depends(get_db)
):
    """
    Listar todas las configuraciones de API.
    
    Categorías disponibles: threat_intel, identity, malware, network, 
    credentials, cloud, notification, integration, general
    """
    try:
        configs = ConfigurationService.get_all_configurations(db, category)
        
        return {
            "success": True,
            "total": len(configs),
            "configurations": configs
        }
    except Exception as e:
        logger.error(f"❌ Error listando configuraciones: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_configuration_summary(db: Session = Depends(get_db)):
    """
    Obtener resumen de configuraciones por categoría y servicio.
    Útil para dashboards y estadísticas.
    """
    try:
        summary = ConfigurationService.get_configuration_summary(db)
        return {
            "success": True,
            **summary
        }
    except Exception as e:
        logger.error(f"❌ Error obteniendo resumen: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories")
async def list_categories():
    """Listar todas las categorías disponibles"""
    return {
        "categories": [
            {"id": c.value, "name": c.name.replace("_", " ").title()}
            for c in ConfigCategory
        ]
    }


@router.get("/definitions")
async def get_api_definitions():
    """
    Obtener definiciones de todas las APIs soportadas.
    Incluye información sobre cada API sin valores configurados.
    """
    definitions = []
    for api_def in API_DEFINITIONS:
        definitions.append({
            "key": api_def["key"],
            "display_name": api_def["display_name"],
            "description": api_def.get("description"),
            "category": api_def.get("category", ConfigCategory.GENERAL).value,
            "service_name": api_def.get("service_name"),
            "service_url": api_def.get("service_url"),
            "is_secret": api_def.get("is_secret", True)
        })
    
    return {
        "total": len(definitions),
        "definitions": definitions
    }


@router.get("/system")
async def get_system_configuration(db: Session = Depends(get_db)):
    """
    Obtener configuración del sistema para el frontend.
    Devuelve URLs y puertos configurados.
    Este endpoint NO requiere autenticación para que el frontend pueda obtenerlo.
    """
    import os
    
    # Obtener de BD o usar defaults
    def get_config_value(key: str, default: str) -> str:
        config = db.query(ApiConfiguration).filter(
            ApiConfiguration.key == key
        ).first()
        if config and config.value:
            return config.value
        return os.getenv(key, default)
    
    return {
        "success": True,
        "config": {
            "api_url": get_config_value("API_BASE_URL", "http://localhost:9000"),
            "api_port": get_config_value("API_PORT", "9000"),
            "frontend_url": get_config_value("FRONTEND_URL", "http://localhost:3000"),
            "frontend_port": get_config_value("FRONTEND_PORT", "3000"),
            "ws_url": get_config_value("WS_URL", "ws://localhost:9000/ws"),
            "cors_origins": get_config_value("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001"),
        }
    }


@router.post("/initialize")
async def initialize_configurations(db: Session = Depends(get_db)):
    """
    Inicializar configuraciones desde variables de entorno.
    Crea entradas en BD para todas las APIs definidas.
    Solo para configuraciones OPCIONALES (no las requeridas del sistema).
    """
    try:
        result = ConfigurationService.initialize_configurations(db)
        logger.info(f"✅ Configuraciones inicializadas: {result}")
        return {
            "success": True,
            "message": "Configurations initialized",
            **result
        }
    except Exception as e:
        logger.error(f"❌ Error inicializando configuraciones: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{key}")
async def get_configuration(key: str, db: Session = Depends(get_db)):
    """Obtener una configuración específica por key"""
    config = ConfigurationService.get_configuration(db, key)
    
    if not config:
        raise HTTPException(status_code=404, detail=f"Configuration '{key}' not found")
    
    return {
        "success": True,
        "configuration": config
    }


@router.put("/{key}")
async def update_configuration(
    key: str,
    update: ConfigurationUpdate,
    db: Session = Depends(get_db)
):
    """
    Actualizar una configuración.
    El valor se guarda en BD y también se actualiza la variable de entorno en runtime.
    """
    try:
        result = ConfigurationService.update_configuration(
            db, 
            key, 
            update.value,
            enabled=update.enabled
        )
        
        if not result:
            raise HTTPException(status_code=404, detail=f"Configuration '{key}' not found")
        
        logger.info(f"✅ Configuración actualizada: {key}")
        return {
            "success": True,
            "message": f"Configuration '{key}' updated",
            "configuration": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error actualizando {key}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{key}")
async def delete_configuration_value(key: str, db: Session = Depends(get_db)):
    """
    Eliminar el valor de una configuración (no la configuración en sí).
    La entrada permanece en BD pero sin valor.
    """
    try:
        success = ConfigurationService.delete_configuration_value(db, key)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Configuration '{key}' not found")
        
        return {
            "success": True,
            "message": f"Configuration value for '{key}' deleted"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error eliminando {key}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bulk-update")
async def bulk_update_configurations(
    update: ConfigurationBulkUpdate,
    db: Session = Depends(get_db)
):
    """
    Actualizar múltiples configuraciones a la vez.
    Útil para importar desde archivo o formulario completo.
    """
    results = {"updated": [], "failed": [], "not_found": []}
    
    for key, value in update.configurations.items():
        try:
            result = ConfigurationService.update_configuration(db, key, value)
            if result:
                results["updated"].append(key)
            else:
                results["not_found"].append(key)
        except Exception as e:
            results["failed"].append({"key": key, "error": str(e)})
    
    return {
        "success": len(results["failed"]) == 0,
        "message": f"Updated {len(results['updated'])} configurations",
        **results
    }


@router.post("/{key}/validate")
async def validate_configuration(key: str, db: Session = Depends(get_db)):
    """
    Validar una configuración de API.
    Realiza una petición de prueba al servicio para verificar que la key es válida.
    """
    try:
        result = await ConfigurationService.validate_configuration(db, key)
        
        return {
            "success": result.get("valid", False),
            **result
        }
    except Exception as e:
        logger.error(f"❌ Error validando {key}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate-all")
async def validate_all_configurations(
    request: Optional[ValidationRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Validar múltiples configuraciones.
    Si no se especifican keys, valida todas las configuradas.
    """
    try:
        if request and request.keys:
            keys_to_validate = request.keys
        else:
            # Obtener todas las configuraciones con valor
            configs = db.query(ApiConfiguration).filter(
                ApiConfiguration.is_configured.is_(True)
            ).all()
            keys_to_validate = [c.key for c in configs]
        
        results = []
        for key in keys_to_validate:
            result = await ConfigurationService.validate_configuration(db, key)
            results.append(result)
        
        valid_count = sum(1 for r in results if r.get("valid"))
        
        return {
            "success": True,
            "total": len(results),
            "valid": valid_count,
            "invalid": len(results) - valid_count,
            "results": results
        }
    except Exception as e:
        logger.error(f"❌ Error validando configuraciones: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/env")
async def export_to_env(
    include_secrets: bool = Query(False, description="Incluir valores secretos"),
    db: Session = Depends(get_db)
):
    """
    Exportar configuraciones en formato .env.
    Por defecto oculta los valores secretos.
    """
    try:
        env_content = ConfigurationService.export_to_env_format(db, include_secrets)
        return {
            "success": True,
            "format": "env",
            "content": env_content
        }
    except Exception as e:
        logger.error(f"❌ Error exportando: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/services/status")
async def get_services_status(db: Session = Depends(get_db)):
    """
    Obtener estado de todos los servicios configurados.
    Agrupa por servicio y muestra qué APIs están configuradas.
    """
    configs = db.query(ApiConfiguration).all()
    
    services = {}
    for config in configs:
        svc = config.service_name or "Other"
        if svc not in services:
            services[svc] = {
                "name": svc,
                "url": config.service_url,
                "keys": [],
                "configured": False,
                "enabled": False
            }
        
        services[svc]["keys"].append({
            "key": config.key,
            "display_name": config.display_name,
            "configured": config.is_configured,
            "enabled": config.is_enabled,
            "validation_status": config.validation_status
        })
        
        if config.is_configured:
            services[svc]["configured"] = True
        if config.is_enabled:
            services[svc]["enabled"] = True
    
    return {
        "success": True,
        "total_services": len(services),
        "services": list(services.values())
    }
