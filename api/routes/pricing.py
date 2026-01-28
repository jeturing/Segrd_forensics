"""
Pricing Routes v4.6
====================
Endpoints para gestión de precios/bundles de la plataforma
"""

import logging
import os
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
import psycopg2
from psycopg2.extras import RealDictCursor

from api.middleware.auth import get_current_user, require_global_admin
from api.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def get_pg_connection():
    """Get PostgreSQL connection from environment or defaults."""
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        database=os.getenv("POSTGRES_DB", "forensics"),
        user=os.getenv("POSTGRES_USER", "forensics"),
        password=os.getenv("POSTGRES_PASSWORD", "change-me-please")
    )

# Routers
router = APIRouter(
    prefix="/api/admin/pricing",
    tags=["Pricing Admin"],
    dependencies=[Depends(require_global_admin)]
)

# Public (sin auth) - solo lectura
public_router = APIRouter(
    prefix="/api/pricing",
    tags=["Pricing Public"],
)

# Default pricing configuration
DEFAULT_PRICING = {
    "bundles": [
        {
            "id": "bundle_essential",
            "name": "Protección Esencial",
            "bundle": "Bundle I",
            "price": 2500,
            "description": "Cobertura base para empresas que inician su programa de ciberseguridad.",
            "targetCompanies": "Hasta 100 empleados",
            "color": "blue",
            "recommended": False,
            "active": True,
            "features": [
                {"name": "Evaluación Anual de Seguridad", "included": True},
                {"name": "EDR (Endpoint Detection & Response)", "included": True},
                {"name": "Protección DNS", "included": True},
                {"name": "v-CISO Lite (2h/mes)", "included": True},
                {"name": "Backup Cloud Básico (500GB)", "included": True},
                {"name": "MDR 24x7", "included": False},
                {"name": "SIEM Gestionado", "included": False}
            ]
        },
        {
            "id": "bundle_professional",
            "name": "Resiliencia Profesional",
            "bundle": "Bundle II",
            "price": 4500,
            "description": "Protección robusta con monitoreo activo y capacidad de respuesta rápida.",
            "targetCompanies": "100-300 empleados",
            "color": "purple",
            "recommended": True,
            "active": True,
            "features": [
                {"name": "Todo de Esencial +", "included": True, "highlight": True},
                {"name": "MDR 24x7 (SOC gestionado)", "included": True},
                {"name": "SIEM Gestionado", "included": True},
                {"name": "v-CISO Activo (4h/mes)", "included": True},
                {"name": "SEGRD™ Análisis Forense", "included": True},
                {"name": "Protección M365 Avanzada", "included": True}
            ]
        },
        {
            "id": "bundle_critical",
            "name": "Blindaje Misión Crítica",
            "bundle": "Bundle III",
            "price": 6500,
            "description": "Máxima protección para operaciones críticas. Cero tolerancia al downtime.",
            "targetCompanies": "300+ empleados / Infraestructura crítica",
            "color": "amber",
            "recommended": False,
            "active": True,
            "features": [
                {"name": "Todo de Profesional +", "included": True, "highlight": True},
                {"name": "v-CISO Dedicado (8h/mes)", "included": True},
                {"name": "SOC 24/7 con Analista Asignado", "included": True},
                {"name": "SEGRD™ con IA Forense Avanzada", "included": True},
                {"name": "BCDR Garantizado (RTO 4h)", "included": True}
            ]
        }
    ],
    "addons": [
        {"id": "dns", "name": "Escudo DNS", "price": 150, "unit": "/mes", "description": "Filtrado DNS avanzado contra malware y phishing", "active": True},
        {"id": "mdr", "name": "MDR 24x7", "price": 500, "unit": "/mes", "description": "Monitoreo y respuesta gestionada por analistas SOC", "active": True},
        {"id": "siem", "name": "SIEM Cloud", "price": 750, "unit": "/mes", "description": "Correlación de eventos y logs (12 meses retención)", "active": True},
        {"id": "forensics", "name": "SEGRD™ Forense", "price": 1200, "unit": "/mes", "description": "Plataforma forense con análisis M365 y endpoints", "active": True},
        {"id": "m365", "name": "Protección M365", "price": 350, "unit": "/mes", "description": "Backup, DLP y protección avanzada para Microsoft 365", "active": True}
    ],
    "vciso_plans": [
        {"id": "vciso_lite", "name": "v-CISO Lite", "hours": 2, "price": 400, "description": "Consultoría básica mensual", "active": True},
        {"id": "vciso_active", "name": "v-CISO Activo", "hours": 4, "price": 750, "description": "Soporte proactivo y reuniones quincenales", "active": True},
        {"id": "vciso_dedicated", "name": "v-CISO Dedicado", "hours": 8, "price": 1400, "description": "Integración completa como líder de seguridad", "active": True}
    ],
    "currency": "USD",
    "tax_rate": 0.16,
    "discount_codes": []
}


def get_pricing_from_db() -> Optional[Dict[str, Any]]:
    """Obtener configuración de pricing de la base de datos"""
    try:
        conn = get_pg_connection()
        from psycopg2.extras import RealDictCursor
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT config FROM platform_settings 
                WHERE key = 'pricing_config' AND is_active = TRUE
                LIMIT 1
            """)
            row = cur.fetchone()
            if row and row.get("config"):
                return row["config"]
        return None
    except Exception as e:
        logger.warning(f"⚠️ Could not load pricing from DB: {e}")
        return None


def get_effective_pricing() -> Dict[str, Any]:
    """Resolver pricing usando BD si existe, si no defaults."""
    db_pricing = get_pricing_from_db()
    if db_pricing:
        logger.info("📊 Loaded pricing from database")
        return db_pricing
    logger.info("📊 Returning default pricing configuration")
    return DEFAULT_PRICING


def save_pricing_to_db(pricing_data: Dict[str, Any]) -> bool:
    """Guardar configuración de pricing en la base de datos"""
    try:
        conn = get_pg_connection()
        import json
        
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO platform_settings (key, config, is_active, updated_at)
                VALUES ('pricing_config', %s, TRUE, NOW())
                ON CONFLICT (key) DO UPDATE SET
                    config = EXCLUDED.config,
                    updated_at = NOW()
            """, (json.dumps(pricing_data),))
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"❌ Error saving pricing to DB: {e}")
        return False


@router.get("")
async def get_pricing(_: dict = Depends(require_global_admin)):
    """
    Obtener configuración de pricing actual
    Retorna config de DB si existe, o defaults
    """
    try:
        # Intentar cargar de DB
        db_pricing = get_pricing_from_db()
        if db_pricing:
            logger.info("📊 Loaded pricing from database")
            return db_pricing
        
        # Retornar defaults
        logger.info("📊 Returning default pricing configuration")
        return DEFAULT_PRICING
        
    except Exception as e:
        logger.error(f"❌ Error getting pricing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("")
async def update_pricing(
    pricing_data: Dict[str, Any],
    _: dict = Depends(require_global_admin)
):
    """
    Actualizar configuración de pricing
    """
    try:
        # Validar estructura básica
        if "bundles" not in pricing_data:
            raise HTTPException(status_code=400, detail="Missing 'bundles' in pricing data")
        
        # Guardar en DB
        success = save_pricing_to_db(pricing_data)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save pricing")
        
        logger.info("✅ Pricing configuration updated")
        return {
            "success": True,
            "message": "Pricing configuration updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating pricing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset")
async def reset_pricing(_: dict = Depends(require_global_admin)):
    """
    Restaurar configuración de pricing a valores por defecto
    """
    try:
        success = save_pricing_to_db(DEFAULT_PRICING)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to reset pricing")
        
        logger.info("🔄 Pricing configuration reset to defaults")
        return {
            "success": True,
            "message": "Pricing reset to defaults",
            "pricing": DEFAULT_PRICING
        }
        
    except Exception as e:
        logger.error(f"❌ Error resetting pricing: {e}")
        raise HTTPException(status_code=500, detail=str(e))
