"""
Global Admin Routes v4.6
========================
Endpoints exclusivos para GLOBAL_ADMIN (Pluton_JE).
Gestión a nivel de plataforma: tenants, planes, facturación, configuración global.

Permisos requeridos: platform:manage, platform:billing, platform:settings
Solo accesible por usuarios con is_global_admin=True
"""

import logging
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from api.middleware.auth import get_current_user, require_global_admin
from api.services import roles_service
from api.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(
    prefix="/api/global-admin",
    tags=["Global Admin"],
    dependencies=[Depends(require_global_admin)]
)


# ============================================================================
# SCHEMAS
# ============================================================================

class TenantOverview(BaseModel):
    """Vista resumida de un tenant."""
    id: str
    name: str
    plan_name: Optional[str] = None
    users_count: int = 0
    cases_count: int = 0
    subscription_status: Optional[str] = None
    created_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None


class PlatformStats(BaseModel):
    """Estadísticas globales de la plataforma."""
    total_tenants: int = 0
    active_tenants: int = 0
    total_users: int = 0
    total_cases: int = 0
    total_analyses: int = 0
    revenue_mtd: float = 0.0
    storage_used_gb: float = 0.0


class GlobalSettingUpdate(BaseModel):
    """Actualización de configuración global."""
    key: str
    value: str
    description: Optional[str] = None


class TenantPlanUpdate(BaseModel):
    """Actualización del plan de un tenant."""
    tenant_id: str
    plan_id: int
    reason: Optional[str] = None


class UserGlobalAdminUpdate(BaseModel):
    """Asignar/remover global admin."""
    user_id: str
    is_global_admin: bool
    reason: Optional[str] = None


# ============================================================================
# PLATFORM OVERVIEW
# ============================================================================

@router.get("/stats", response_model=PlatformStats)
async def get_platform_stats(current_user: dict = Depends(get_current_user)):
    """
    📊 Obtener estadísticas globales de la plataforma.
    Solo Global Admin.
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD
        )
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Contar tenants
            cur.execute("SELECT COUNT(*) as count FROM tenants")
            total_tenants = cur.fetchone()['count']
            
            cur.execute("""
                SELECT COUNT(*) as count FROM tenants 
                WHERE subscription_status = 'active' OR subscription_status IS NULL
            """)
            active_tenants = cur.fetchone()['count']
            
            # Contar usuarios
            cur.execute("SELECT COUNT(*) as count FROM users")
            total_users = cur.fetchone()['count']
            
            # Contar casos
            cur.execute("SELECT COUNT(*) as count FROM cases")
            total_cases = cur.fetchone()['count']
            
            # Contar análisis (si existe la tabla)
            try:
                cur.execute("SELECT COUNT(*) as count FROM forensic_analyses")
                total_analyses = cur.fetchone()['count']
            except:
                total_analyses = 0
        
        conn.close()
        
        return PlatformStats(
            total_tenants=total_tenants,
            active_tenants=active_tenants,
            total_users=total_users,
            total_cases=total_cases,
            total_analyses=total_analyses,
            revenue_mtd=0.0,  # TODO: Integrar con Stripe
            storage_used_gb=0.0  # TODO: Calcular storage
        )
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo stats de plataforma: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tenants", response_model=List[TenantOverview])
async def list_all_tenants(
    status: Optional[str] = Query(None, description="Filtrar por estado de suscripción"),
    plan_id: Optional[int] = Query(None, description="Filtrar por plan"),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    current_user: dict = Depends(get_current_user)
):
    """
    📋 Listar todos los tenants de la plataforma.
    Solo Global Admin.
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD
        )
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = """
                SELECT 
                    t.id,
                    t.name,
                    sp.name as plan_name,
                    t.subscription_status,
                    t.created_at,
                    (SELECT COUNT(*) FROM users u WHERE u.tenant_id = t.id) as users_count,
                    (SELECT COUNT(*) FROM cases c WHERE c.tenant_id = t.id) as cases_count,
                    (SELECT MAX(last_activity) FROM users u WHERE u.tenant_id = t.id) as last_activity
                FROM tenants t
                LEFT JOIN service_plans sp ON t.plan_id = sp.id
                WHERE 1=1
            """
            params = []
            
            if status:
                query += " AND t.subscription_status = %s"
                params.append(status)
            
            if plan_id:
                query += " AND t.plan_id = %s"
                params.append(plan_id)
            
            query += " ORDER BY t.created_at DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            cur.execute(query, params)
            tenants = cur.fetchall()
        
        conn.close()
        
        return [TenantOverview(**dict(t)) for t in tenants]
        
    except Exception as e:
        logger.error(f"❌ Error listando tenants: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tenants/{tenant_id}")
async def get_tenant_details(
    tenant_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    🔍 Obtener detalles completos de un tenant.
    Incluye usuarios, roles, uso, facturación.
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD
        )
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Info del tenant
            cur.execute("""
                SELECT 
                    t.*,
                    sp.name as plan_name,
                    sp.max_users,
                    sp.max_storage_gb,
                    sp.max_cases_per_month
                FROM tenants t
                LEFT JOIN service_plans sp ON t.plan_id = sp.id
                WHERE t.id = %s
            """, (tenant_id,))
            
            tenant = cur.fetchone()
            
            if not tenant:
                raise HTTPException(status_code=404, detail="Tenant no encontrado")
            
            # Usuarios del tenant
            cur.execute("""
                SELECT 
                    u.id, u.email, u.full_name, u.is_active, u.last_activity,
                    array_agg(r.name) as roles
                FROM users u
                LEFT JOIN user_roles ur ON u.id = ur.user_id AND ur.tenant_id = %s
                LEFT JOIN roles r ON ur.role_id = r.id
                WHERE u.tenant_id = %s
                GROUP BY u.id
            """, (tenant_id, tenant_id))
            users = cur.fetchall()
            
            # Contadores
            cur.execute("SELECT COUNT(*) as count FROM cases WHERE tenant_id = %s", (tenant_id,))
            cases_count = cur.fetchone()['count']
        
        conn.close()
        
        return {
            "tenant": dict(tenant),
            "users": [dict(u) for u in users],
            "stats": {
                "users_count": len(users),
                "cases_count": cases_count
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error obteniendo tenant: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# TENANT MANAGEMENT
# ============================================================================

@router.put("/tenants/{tenant_id}/plan")
async def update_tenant_plan(
    tenant_id: str,
    update: TenantPlanUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    💳 Cambiar el plan de un tenant.
    Solo Global Admin.
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD
        )
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Verificar que el plan existe
            cur.execute("SELECT id, name FROM service_plans WHERE id = %s", (update.plan_id,))
            plan = cur.fetchone()
            
            if not plan:
                raise HTTPException(status_code=404, detail="Plan no encontrado")
            
            # Actualizar tenant
            cur.execute("""
                UPDATE tenants 
                SET plan_id = %s, updated_at = NOW()
                WHERE id = %s
                RETURNING id
            """, (update.plan_id, tenant_id))
            
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Tenant no encontrado")
            
            # Registrar en audit log
            cur.execute("""
                INSERT INTO audit_logs (user_id, action, resource_type, resource_id, details, created_at)
                VALUES (%s, 'update_tenant_plan', 'tenant', %s, %s, NOW())
            """, (
                current_user['user_id'],
                tenant_id,
                f'{{"plan_id": {update.plan_id}, "plan_name": "{plan["name"]}", "reason": "{update.reason or ""}"}}'
            ))
            
            conn.commit()
        
        conn.close()
        
        logger.info(f"✅ Plan de tenant {tenant_id} actualizado a {plan['name']}")
        
        return {
            "success": True,
            "message": f"Plan actualizado a '{plan['name']}'"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error actualizando plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/tenants/{tenant_id}/status")
async def update_tenant_status(
    tenant_id: str,
    status: str = Query(..., regex="^(active|suspended|cancelled)$"),
    reason: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    🔄 Cambiar estado de suscripción de un tenant.
    Estados: active, suspended, cancelled
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD
        )
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                UPDATE tenants 
                SET subscription_status = %s, updated_at = NOW()
                WHERE id = %s
                RETURNING id, name
            """, (status, tenant_id))
            
            tenant = cur.fetchone()
            
            if not tenant:
                raise HTTPException(status_code=404, detail="Tenant no encontrado")
            
            # Audit log
            cur.execute("""
                INSERT INTO audit_logs (user_id, action, resource_type, resource_id, details, created_at)
                VALUES (%s, 'update_tenant_status', 'tenant', %s, %s, NOW())
            """, (
                current_user['user_id'],
                tenant_id,
                f'{{"status": "{status}", "reason": "{reason or ""}"}}'
            ))
            
            conn.commit()
        
        conn.close()
        
        logger.info(f"✅ Estado de tenant {tenant['name']} cambiado a {status}")
        
        return {
            "success": True,
            "message": f"Estado actualizado a '{status}'"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error actualizando estado: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# GLOBAL ADMIN MANAGEMENT
# ============================================================================

@router.get("/global-admins")
async def list_global_admins(current_user: dict = Depends(get_current_user)):
    """
    👑 Listar todos los usuarios con rol Global Admin.
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD
        )
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, email, full_name, is_active, created_at, last_activity
                FROM users
                WHERE is_global_admin = true
                ORDER BY created_at
            """)
            admins = cur.fetchall()
        
        conn.close()
        
        return {
            "global_admins": [dict(a) for a in admins],
            "count": len(admins)
        }
        
    except Exception as e:
        logger.error(f"❌ Error listando global admins: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/global-admins")
async def manage_global_admin(
    update: UserGlobalAdminUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    👑 Asignar o remover rol Global Admin de un usuario.
    ⚠️ Operación crítica - requiere auditoría completa.
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD
        )
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # No permitir auto-remoción
            if update.user_id == current_user['user_id'] and not update.is_global_admin:
                raise HTTPException(
                    status_code=400, 
                    detail="No puedes remover tu propio rol de Global Admin"
                )
            
            # Verificar que el usuario existe
            cur.execute("SELECT id, email FROM users WHERE id = %s", (update.user_id,))
            user = cur.fetchone()
            
            if not user:
                raise HTTPException(status_code=404, detail="Usuario no encontrado")
            
            # Actualizar
            cur.execute("""
                UPDATE users 
                SET is_global_admin = %s, updated_at = NOW()
                WHERE id = %s
            """, (update.is_global_admin, update.user_id))
            
            # Si se asigna global admin, también asignar rol GLOBAL_ADMIN
            if update.is_global_admin:
                cur.execute("""
                    INSERT INTO user_roles (user_id, role_id, assigned_by, assigned_at)
                    SELECT %s, id, %s, NOW()
                    FROM roles WHERE name = 'global_admin'
                    ON CONFLICT DO NOTHING
                """, (update.user_id, current_user['user_id']))
            
            # Audit log crítico
            cur.execute("""
                INSERT INTO audit_logs (user_id, action, resource_type, resource_id, details, severity, created_at)
                VALUES (%s, 'manage_global_admin', 'user', %s, %s, 'critical', NOW())
            """, (
                current_user['user_id'],
                update.user_id,
                f'{{"is_global_admin": {str(update.is_global_admin).lower()}, "target_email": "{user["email"]}", "reason": "{update.reason or ""}"}}'
            ))
            
            conn.commit()
        
        conn.close()
        
        action = "asignado" if update.is_global_admin else "removido"
        logger.warning(f"👑 Global Admin {action} para {user['email']} por {current_user.get('email', 'unknown')}")
        
        return {
            "success": True,
            "message": f"Global Admin {action} para {user['email']}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error gestionando global admin: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SYSTEM ROLES
# ============================================================================

@router.get("/roles")
async def get_all_system_roles(current_user: dict = Depends(get_current_user)):
    """
    📋 Obtener todos los roles de sistema con sus permisos.
    """
    roles = await roles_service.get_all_system_roles()
    
    return {
        "roles": roles,
        "count": len(roles)
    }


@router.get("/permissions")
async def get_all_permissions(current_user: dict = Depends(get_current_user)):
    """
    🔐 Obtener todos los permisos disponibles agrupados por categoría.
    """
    permissions = await roles_service.get_all_permissions()
    
    return {
        "permissions": permissions
    }


# ============================================================================
# PLATFORM SETTINGS
# ============================================================================

# Mapeo de keys del frontend a keys de la base de datos
SETTING_KEY_MAP = {
    # Frontend key -> DB key
    'siteName': 'site_name',
    'siteUrl': 'site_url',
    'supportEmail': 'support_email',
    'allowPublicRegistration': 'allow_public_registration',
    'requireEmailVerification': 'require_email_verification',
    'defaultTrialDays': 'default_trial_days',
    'stripeEnabled': 'stripe_enabled',
    'stripeMode': 'stripe_mode',
    'stripePublicKey': 'stripe_public_key',
    'smtpHost': 'smtp_host',
    'smtpPort': 'smtp_port',
    'smtpUser': 'smtp_user',
    'fromEmail': 'from_email',
    'sessionTimeout': 'session_timeout',
    'maxLoginAttempts': 'max_login_attempts',
    'lockoutDuration': 'lockout_duration',
    'requireMFA': 'require_mfa',
    'maintenanceMode': 'maintenance_mode',
    'debugMode': 'debug_mode',
    'logLevel': 'log_level'
}

# Mapeo inverso para respuestas
SETTING_KEY_MAP_REVERSE = {v: k for k, v in SETTING_KEY_MAP.items()}

# Categorías de settings
SETTING_CATEGORIES = {
    'site_name': 'general', 'site_url': 'general', 'support_email': 'general',
    'allow_public_registration': 'registration', 'require_email_verification': 'registration',
    'default_trial_days': 'registration',
    'stripe_enabled': 'billing', 'stripe_mode': 'billing', 'stripe_public_key': 'billing',
    'smtp_host': 'email', 'smtp_port': 'email', 'smtp_user': 'email', 'from_email': 'email',
    'session_timeout': 'security', 'max_login_attempts': 'security',
    'lockout_duration': 'security', 'require_mfa': 'security',
    'maintenance_mode': 'system', 'debug_mode': 'system', 'log_level': 'system'
}


def _convert_value_from_db(value: str, key: str) -> any:
    """Convierte valor de string DB a tipo Python apropiado."""
    if value is None:
        return None
    # Booleans
    if key in ['allow_public_registration', 'require_email_verification', 'stripe_enabled',
               'require_mfa', 'maintenance_mode', 'debug_mode']:
        return value.lower() == 'true'
    # Numbers
    if key in ['default_trial_days', 'smtp_port', 'session_timeout', 
               'max_login_attempts', 'lockout_duration']:
        try:
            return int(value)
        except:
            return value
    return value


def _convert_value_to_db(value: any) -> str:
    """Convierte valor Python a string para DB."""
    if isinstance(value, bool):
        return 'true' if value else 'false'
    return str(value)


@router.get("/settings")
async def get_platform_settings(current_user: dict = Depends(get_current_user)):
    """
    ⚙️ Obtener configuración global de la plataforma.
    Devuelve formato compatible con frontend (camelCase keys).
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD
        )
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT key, value, value_type, category, description, is_secret, updated_at
                FROM platform_settings
                WHERE is_secret = FALSE
                ORDER BY category, key
            """)
            settings_list = cur.fetchall()
        
        conn.close()
        
        # Convertir a formato de objeto para frontend
        settings_obj = {}
        settings_raw = []
        
        for s in settings_list:
            db_key = s['key']
            frontend_key = SETTING_KEY_MAP_REVERSE.get(db_key, db_key)
            converted_value = _convert_value_from_db(s['value'], db_key)
            settings_obj[frontend_key] = converted_value
            settings_raw.append({
                'key': db_key,
                'frontendKey': frontend_key,
                'value': converted_value,
                'category': s['category'],
                'description': s['description'],
                'updatedAt': s['updated_at'].isoformat() if s['updated_at'] else None
            })
        
        return {
            "settings": settings_obj,
            "raw": settings_raw,
            "categories": list(set(SETTING_CATEGORIES.values()))
        }
        
    except Exception as e:
        # Tabla puede no existir aún - devolver defaults
        logger.warning(f"⚠️ Error obteniendo settings (puede no existir tabla): {e}")
        return {
            "settings": {
                "siteName": "JETURING Forensics",
                "siteUrl": "https://forensics.jeturing.com",
                "supportEmail": "support@jeturing.com",
                "allowPublicRegistration": True,
                "requireEmailVerification": True,
                "defaultTrialDays": 15,
                "stripeEnabled": True,
                "stripeMode": "test",
                "stripePublicKey": "pk_test_...",
                "smtpHost": "smtp.sendgrid.net",
                "smtpPort": 587,
                "smtpUser": "apikey",
                "fromEmail": "noreply@jeturing.com",
                "sessionTimeout": 3600,
                "maxLoginAttempts": 5,
                "lockoutDuration": 900,
                "requireMFA": False,
                "maintenanceMode": False,
                "debugMode": False,
                "logLevel": "INFO"
            },
            "raw": [],
            "note": "Using defaults - platform_settings table not initialized"
        }


@router.put("/settings")
async def update_platform_setting(
    update: GlobalSettingUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    ⚙️ Actualizar un setting individual.
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        # Convertir key de frontend a DB si es necesario
        db_key = SETTING_KEY_MAP.get(update.key, update.key)
        db_value = _convert_value_to_db(update.value)
        category = SETTING_CATEGORIES.get(db_key, 'general')
        
        conn = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD
        )
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO platform_settings (key, value, category, description, updated_at, updated_by)
                VALUES (%s, %s, %s, %s, NOW(), %s)
                ON CONFLICT (key) DO UPDATE 
                SET value = EXCLUDED.value, 
                    description = COALESCE(EXCLUDED.description, platform_settings.description),
                    updated_at = NOW(),
                    updated_by = EXCLUDED.updated_by
                RETURNING key, value
            """, (db_key, db_value, category, update.description, current_user['user_id']))
            
            result = cur.fetchone()
            conn.commit()
        
        conn.close()
        
        logger.info(f"⚙️ Setting '{db_key}' actualizado a '{db_value}'")
        
        return {
            "success": True,
            "setting": dict(result)
        }
        
    except Exception as e:
        logger.error(f"❌ Error actualizando setting: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/settings/bulk")
async def update_platform_settings_bulk(
    settings_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    ⚙️ Actualizar múltiples settings a la vez.
    Recibe un objeto con todos los settings del frontend.
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD
        )
        
        updated_count = 0
        errors = []
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            for frontend_key, value in settings_data.items():
                try:
                    # Convertir key y value
                    db_key = SETTING_KEY_MAP.get(frontend_key, frontend_key)
                    db_value = _convert_value_to_db(value)
                    category = SETTING_CATEGORIES.get(db_key, 'general')
                    
                    cur.execute("""
                        INSERT INTO platform_settings (key, value, category, updated_at, updated_by)
                        VALUES (%s, %s, %s, NOW(), %s)
                        ON CONFLICT (key) DO UPDATE 
                        SET value = EXCLUDED.value, 
                            updated_at = NOW(),
                            updated_by = EXCLUDED.updated_by
                    """, (db_key, db_value, category, current_user['user_id']))
                    
                    updated_count += 1
                    
                except Exception as e:
                    errors.append({"key": frontend_key, "error": str(e)})
            
            conn.commit()
        
        conn.close()
        
        logger.info(f"⚙️ {updated_count} settings actualizados")
        
        return {
            "success": True,
            "updated_count": updated_count,
            "errors": errors if errors else None,
            "message": f"{updated_count} configuraciones guardadas exitosamente"
        }
        
    except Exception as e:
        logger.error(f"❌ Error actualizando settings bulk: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# AUDIT & MONITORING
# ============================================================================

@router.get("/audit-logs")
async def get_platform_audit_logs(
    severity: Optional[str] = Query(None, regex="^(info|warning|critical)$"),
    action: Optional[str] = None,
    limit: int = Query(100, le=500),
    offset: int = Query(0),
    current_user: dict = Depends(get_current_user)
):
    """
    📜 Obtener logs de auditoría de toda la plataforma.
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD
        )
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = """
                SELECT 
                    al.*,
                    u.email as user_email
                FROM audit_logs al
                LEFT JOIN users u ON al.user_id = u.id
                WHERE 1=1
            """
            params = []
            
            if severity:
                query += " AND al.severity = %s"
                params.append(severity)
            
            if action:
                query += " AND al.action ILIKE %s"
                params.append(f"%{action}%")
            
            query += " ORDER BY al.created_at DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            cur.execute(query, params)
            logs = cur.fetchall()
        
        conn.close()
        
        return {
            "logs": [dict(l) for l in logs],
            "count": len(logs)
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo audit logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SYSTEM SETTINGS - CONFIGURACIÓN DINÁMICA DESDE BD
# ============================================================================

class SystemSettingCreate(BaseModel):
    """Crear configuración del sistema."""
    key: str = Field(..., description="Clave única de la configuración")
    value: str = Field(..., description="Valor de la configuración")
    value_type: str = Field("string", description="Tipo: string, int, bool, json")
    description: Optional[str] = None
    category: str = Field("general", description="Categoría: llm, smtp, minio, database, security")


class SystemSettingUpdate(BaseModel):
    """Actualizar configuración del sistema."""
    value: str
    description: Optional[str] = None


class SystemSettingBulkUpdate(BaseModel):
    """Actualización masiva de configuraciones."""
    settings: List[dict] = Field(..., description="Lista de {key, value}")


@router.get("/system-settings")
async def get_system_settings(
    category: Optional[str] = Query(None, description="Filtrar por categoría"),
    current_user: dict = Depends(get_current_user)
):
    """
    ⚙️ Obtener todas las configuraciones del sistema desde BD.
    Retorna configuraciones editables desde el panel de admin.
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD
        )
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Crear tabla si no existe
            cur.execute("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    id SERIAL PRIMARY KEY,
                    key VARCHAR(100) UNIQUE NOT NULL,
                    value TEXT,
                    value_type VARCHAR(20) DEFAULT 'string',
                    description TEXT,
                    category VARCHAR(50) DEFAULT 'general',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            conn.commit()
            
            # Insertar valores por defecto si la tabla está vacía
            cur.execute("SELECT COUNT(*) as cnt FROM system_settings")
            count = cur.fetchone()['cnt']
            
            if count == 0:
                # Insertar configuraciones por defecto desde env/config
                default_settings = [
                    # LLM
                    ("LLM_PROVIDER", "ollama", "string", "Proveedor LLM activo", "llm"),
                    ("OLLAMA_URL", "http://ollama:11434", "string", "URL del servidor Ollama", "llm"),
                    ("OLLAMA_MODEL", "llama3.2", "string", "Modelo Ollama por defecto", "llm"),
                    ("OLLAMA_ENABLED", "true", "bool", "Habilitar Ollama", "llm"),
                    ("LLM_STUDIO_URL", "http://100.101.115.5:2714/v1", "string", "URL de LM Studio", "llm"),
                    ("LLM_STUDIO_TIMEOUT", "120", "int", "Timeout LLM en segundos", "llm"),
                    # SMTP
                    ("SMTP_HOST", settings.SMTP_HOST, "string", "Servidor SMTP", "smtp"),
                    ("SMTP_PORT", str(settings.SMTP_PORT), "int", "Puerto SMTP", "smtp"),
                    ("SMTP_USER", settings.SMTP_USER or "", "string", "Usuario SMTP", "smtp"),
                    ("SMTP_FROM_EMAIL", settings.SMTP_FROM_EMAIL, "string", "Email remitente", "smtp"),
                    ("SMTP_CONTACT_TO", settings.SMTP_CONTACT_TO, "string", "Email destino contacto", "smtp"),
                    ("SMTP_CHECKLIST_CC_EMAILS", settings.SMTP_CHECKLIST_CC_EMAILS, "string", "Emails CC checklist", "smtp"),
                    # MINIO
                    ("MINIO_ENABLED", "true", "bool", "Habilitar MinIO", "minio"),
                    ("MINIO_ENDPOINT", settings.MINIO_ENDPOINT, "string", "Endpoint MinIO", "minio"),
                    ("MINIO_BUCKET", settings.MINIO_BUCKET, "string", "Bucket por defecto", "minio"),
                    # Security
                    ("JWT_EXPIRATION_HOURS", str(settings.JWT_EXPIRATION_HOURS), "int", "Expiración JWT en horas", "security"),
                    ("RBAC_ENABLED", "true", "bool", "Habilitar RBAC", "security"),
                ]
                
                for key, value, vtype, desc, cat in default_settings:
                    cur.execute("""
                        INSERT INTO system_settings (key, value, value_type, description, category)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (key) DO NOTHING
                    """, (key, value, vtype, desc, cat))
                conn.commit()
            
            # Obtener settings
            query = "SELECT * FROM system_settings"
            params = []
            if category:
                query += " WHERE category = %s"
                params.append(category)
            query += " ORDER BY category, key"
            
            cur.execute(query, params)
            rows = cur.fetchall()
        
        conn.close()
        
        # Agrupar por categoría
        grouped = {}
        for row in rows:
            cat = row['category'] or 'general'
            if cat not in grouped:
                grouped[cat] = []
            grouped[cat].append(dict(row))
        
        return {
            "success": True,
            "settings": grouped,
            "total": len(rows)
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo system settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/system-settings/{key}")
async def update_system_setting(
    key: str,
    update: SystemSettingUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    ⚙️ Actualizar una configuración del sistema.
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD
        )
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                UPDATE system_settings 
                SET value = %s, 
                    description = COALESCE(%s, description),
                    updated_at = NOW()
                WHERE key = %s
                RETURNING *
            """, (update.value, update.description, key))
            
            row = cur.fetchone()
            
            if not row:
                # Insertar si no existe
                cur.execute("""
                    INSERT INTO system_settings (key, value, description)
                    VALUES (%s, %s, %s)
                    RETURNING *
                """, (key, update.value, update.description))
                row = cur.fetchone()
            
            conn.commit()
        
        conn.close()
        
        logger.info(f"⚙️ Setting actualizado: {key} = {update.value[:50]}...")
        
        return {
            "success": True,
            "setting": dict(row) if row else None
        }
        
    except Exception as e:
        logger.error(f"❌ Error actualizando setting {key}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/system-settings")
async def update_system_settings_bulk_v2(
    update: SystemSettingBulkUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    ⚙️ Actualizar múltiples configuraciones del sistema.
    """
    try:
        import psycopg2
        
        conn = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD
        )
        
        updated = 0
        with conn.cursor() as cur:
            for item in update.settings:
                key = item.get('key')
                value = item.get('value')
                if key and value is not None:
                    cur.execute("""
                        INSERT INTO system_settings (key, value, updated_at)
                        VALUES (%s, %s, NOW())
                        ON CONFLICT (key) DO UPDATE SET
                            value = EXCLUDED.value,
                            updated_at = NOW()
                    """, (key, str(value)))
                    updated += 1
            conn.commit()
        
        conn.close()
        
        logger.info(f"⚙️ {updated} settings actualizados en bulk")
        
        return {
            "success": True,
            "updated": updated
        }
        
    except Exception as e:
        logger.error(f"❌ Error en bulk update de settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system-settings/llm-status")
async def get_llm_status(current_user: dict = Depends(get_current_user)):
    """
    🤖 Obtener estado de los proveedores LLM.
    """
    try:
        import aiohttp
        import asyncio
        
        providers_status = {}
        
        # Verificar Ollama
        ollama_url = "http://ollama:11434"
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(f"{ollama_url}/api/tags") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        models = [m.get('name') for m in data.get('models', [])]
                        providers_status['ollama'] = {
                            "status": "online",
                            "url": ollama_url,
                            "models": models
                        }
                    else:
                        providers_status['ollama'] = {"status": "error", "url": ollama_url}
        except Exception as e:
            providers_status['ollama'] = {"status": "offline", "url": ollama_url, "error": str(e)}
        
        # Verificar LM Studio
        lm_studio_url = "http://100.101.115.5:2714"
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(f"{lm_studio_url}/v1/models") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        models = [m.get('id') for m in data.get('data', [])]
                        providers_status['lm_studio'] = {
                            "status": "online",
                            "url": lm_studio_url,
                            "models": models
                        }
                    else:
                        providers_status['lm_studio'] = {"status": "error", "url": lm_studio_url}
        except Exception as e:
            providers_status['lm_studio'] = {"status": "offline", "url": lm_studio_url, "error": str(e)}
        
        return {
            "success": True,
            "providers": providers_status,
            "active_provider": "ollama"  # TODO: leer de BD
        }
        
    except Exception as e:
        logger.error(f"❌ Error verificando LLM status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
