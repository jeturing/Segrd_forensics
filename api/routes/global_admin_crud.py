"""
Global Admin CRUD Routes v4.7
=============================
Endpoints CRUD completos para administración global de la plataforma.
Usa PostgreSQL directamente con psycopg2.

Endpoints disponibles:
- /api/admin/global/users - CRUD usuarios
- /api/admin/global/tenants - CRUD tenants  
- /api/admin/global/subscriptions - Suscripciones
- /api/admin/global/invoices - Facturas
- /api/admin/global/billing-stats - Estadísticas de billing
"""

import logging
import os
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from uuid import uuid4
import bcrypt

from fastapi import APIRouter, HTTPException, Depends, Query, Body
from pydantic import BaseModel, Field, EmailStr
import psycopg2
from psycopg2.extras import RealDictCursor

from api.middleware.auth import get_current_user, require_global_admin

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/admin/global",
    tags=["Global Admin CRUD"],
    dependencies=[Depends(require_global_admin)]
)

# ============================================================================
# DATABASE CONNECTION
# ============================================================================

def get_pg_connection():
    """Get PostgreSQL connection from environment or defaults."""
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        database=os.getenv("POSTGRES_DB", "forensics"),
        user=os.getenv("POSTGRES_USER", "forensics"),
        password=os.getenv("POSTGRES_PASSWORD", "change-me-please")
    )


# ============================================================================
# SCHEMAS
# ============================================================================

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    tenant_id: Optional[str] = None
    is_global_admin: bool = False

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    department: Optional[str] = None
    title: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None
    is_global_admin: Optional[bool] = None

class TenantCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    subdomain: str = Field(..., min_length=2, max_length=63)
    contact_email: Optional[EmailStr] = None
    plan: str = "free_trial"
    max_users: int = 5
    max_cases: int = 100
    max_storage_gb: int = 10

class TenantUpdate(BaseModel):
    name: Optional[str] = None
    contact_email: Optional[str] = None
    plan: Optional[str] = None
    is_active: Optional[bool] = None
    is_suspended: Optional[bool] = None
    suspension_reason: Optional[str] = None
    max_users: Optional[int] = None
    max_cases: Optional[int] = None
    max_storage_gb: Optional[int] = None


# ============================================================================
# USERS CRUD
# ============================================================================

@router.get("/users")
async def list_users(
    search: Optional[str] = None,
    tenant_id: Optional[str] = None,
    is_active: Optional[bool] = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    current_user: dict = Depends(get_current_user)
):
    """
    📋 Listar todos los usuarios de la plataforma.
    """
    try:
        conn = get_pg_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = """
                SELECT 
                    u.id::text,
                    u.username,
                    u.email,
                    u.full_name,
                    u.department,
                    u.title,
                    u.phone,
                    u.is_active,
                    u.is_verified,
                    u.is_global_admin,
                    u.created_at,
                    u.last_login,
                    t.name as tenant,
                    t.id::text as tenant_id
                FROM users u
                LEFT JOIN user_tenants ut ON u.id = ut.user_id
                LEFT JOIN tenants t ON ut.tenant_id = t.id
                WHERE 1=1
            """
            params = []
            
            if search:
                query += """ AND (
                    u.username ILIKE %s OR 
                    u.email ILIKE %s OR 
                    u.full_name ILIKE %s
                )"""
                search_param = f"%{search}%"
                params.extend([search_param, search_param, search_param])
            
            if tenant_id:
                query += " AND t.id::text = %s"
                params.append(tenant_id)
            
            if is_active is not None:
                query += " AND u.is_active = %s"
                params.append(is_active)
            
            query += " ORDER BY u.created_at DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            cur.execute(query, params)
            users = cur.fetchall()
            
            # Get total count
            cur.execute("SELECT COUNT(*) FROM users")
            total = cur.fetchone()['count']
        
        conn.close()
        
        return {
            "users": [dict(u) for u in users],
            "total": total,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"❌ Error listing users: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}")
async def get_user(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    🔍 Obtener detalles de un usuario específico.
    """
    try:
        conn = get_pg_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    u.*,
                    t.name as tenant_name,
                    t.id::text as tenant_id
                FROM users u
                LEFT JOIN user_tenants ut ON u.id = ut.user_id
                LEFT JOIN tenants t ON ut.tenant_id = t.id
                WHERE u.id::text = %s
            """, (user_id,))
            user = cur.fetchone()
            
            if not user:
                raise HTTPException(status_code=404, detail="Usuario no encontrado")
            
            # Get roles
            cur.execute("""
                SELECT r.name, r.display_name
                FROM user_roles ur
                JOIN roles r ON ur.role_id = r.id
                WHERE ur.user_id::text = %s
            """, (user_id,))
            roles = cur.fetchall()
        
        conn.close()
        
        user_dict = dict(user)
        user_dict['id'] = str(user_dict['id'])
        user_dict['roles'] = [dict(r) for r in roles]
        # Remove sensitive data
        user_dict.pop('password_hash', None)
        
        return {"user": user_dict}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting user: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users")
async def create_user(
    user_data: UserCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    ➕ Crear nuevo usuario.
    """
    try:
        conn = get_pg_connection()
        user_id = str(uuid4())
        
        # Hash password
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(user_data.password.encode('utf-8'), salt).decode('utf-8')
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Check if username or email exists
            cur.execute(
                "SELECT id FROM users WHERE username = %s OR email = %s",
                (user_data.username, user_data.email)
            )
            if cur.fetchone():
                raise HTTPException(status_code=400, detail="Username o email ya existe")
            
            # Create user
            cur.execute("""
                INSERT INTO users (
                    id, username, email, password_hash, full_name,
                    is_active, is_verified, is_global_admin, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                RETURNING id::text, username, email, full_name, is_active, created_at
            """, (
                user_id, user_data.username, user_data.email, password_hash,
                user_data.full_name, True, False, user_data.is_global_admin
            ))
            new_user = cur.fetchone()
            
            # Associate with tenant if provided
            if user_data.tenant_id:
                cur.execute("""
                    INSERT INTO user_tenants (user_id, tenant_id, created_at)
                    VALUES (%s, %s, NOW())
                """, (user_id, user_data.tenant_id))
            
            conn.commit()
        
        conn.close()
        
        logger.info(f"✅ Usuario creado: {user_data.username}")
        
        return {"success": True, "user": dict(new_user)}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error creating user: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    ✏️ Actualizar usuario existente.
    """
    try:
        conn = get_pg_connection()
        
        # Build dynamic update
        updates = []
        params = []
        
        if user_data.full_name is not None:
            updates.append("full_name = %s")
            params.append(user_data.full_name)
        if user_data.email is not None:
            updates.append("email = %s")
            params.append(user_data.email)
        if user_data.department is not None:
            updates.append("department = %s")
            params.append(user_data.department)
        if user_data.title is not None:
            updates.append("title = %s")
            params.append(user_data.title)
        if user_data.phone is not None:
            updates.append("phone = %s")
            params.append(user_data.phone)
        if user_data.is_active is not None:
            updates.append("is_active = %s")
            params.append(user_data.is_active)
        if user_data.is_global_admin is not None:
            updates.append("is_global_admin = %s")
            params.append(user_data.is_global_admin)
        
        if not updates:
            raise HTTPException(status_code=400, detail="No hay campos para actualizar")
        
        updates.append("updated_at = NOW()")
        params.append(user_id)
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = f"""
                UPDATE users 
                SET {', '.join(updates)}
                WHERE id::text = %s
                RETURNING id::text, username, email, full_name, is_active, is_global_admin
            """
            cur.execute(query, params)
            updated_user = cur.fetchone()
            
            if not updated_user:
                raise HTTPException(status_code=404, detail="Usuario no encontrado")
            
            conn.commit()
        
        conn.close()
        
        logger.info(f"✅ Usuario actualizado: {user_id}")
        
        return {"success": True, "user": dict(updated_user)}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating user: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    🗑️ Eliminar usuario.
    """
    try:
        # Prevent self-deletion
        if user_id == current_user.get('user_id'):
            raise HTTPException(status_code=400, detail="No puedes eliminarte a ti mismo")
        
        conn = get_pg_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE id::text = %s RETURNING username", (user_id,))
            deleted = cur.fetchone()
            
            if not deleted:
                raise HTTPException(status_code=404, detail="Usuario no encontrado")
            
            conn.commit()
        
        conn.close()
        
        logger.info(f"✅ Usuario eliminado: {deleted[0]}")
        
        return {"success": True, "message": f"Usuario {deleted[0]} eliminado"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting user: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# TENANTS CRUD
# ============================================================================

@router.get("/tenants")
async def list_tenants(
    search: Optional[str] = None,
    plan: Optional[str] = None,
    is_active: Optional[bool] = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    current_user: dict = Depends(get_current_user)
):
    """
    📋 Listar todos los tenants de la plataforma.
    """
    try:
        conn = get_pg_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = """
                SELECT 
                    t.id::text,
                    t.tenant_id,
                    t.name,
                    t.subdomain,
                    t.contact_email,
                    t.plan,
                    t.is_active,
                    t.is_suspended,
                    t.max_users,
                    t.max_cases,
                    t.max_storage_gb,
                    t.created_at,
                    t.updated_at,
                    s.status as subscription_status,
                    s.trial_end,
                    s.is_trial,
                    sp.name as plan_name,
                    sp.price_monthly as monthly_revenue,
                    (SELECT COUNT(*) FROM user_tenants ut WHERE ut.tenant_id = t.id) as users_count,
                    0 as cases_count -- TODO: cases table has no tenant_id
                FROM tenants t
                LEFT JOIN subscriptions s ON s.tenant_id = t.id
                LEFT JOIN subscription_plans sp ON s.plan_id = sp.id
                WHERE 1=1
            """
            params = []
            
            if search:
                query += """ AND (
                    t.name ILIKE %s OR 
                    t.tenant_id ILIKE %s OR 
                    t.contact_email ILIKE %s
                )"""
                search_param = f"%{search}%"
                params.extend([search_param, search_param, search_param])
            
            if plan:
                query += " AND t.plan = %s"
                params.append(plan)
            
            if is_active is not None:
                query += " AND t.is_active = %s"
                params.append(is_active)
            
            query += " ORDER BY t.created_at DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            cur.execute(query, params)
            tenants = cur.fetchall()
            
            # Get total count
            cur.execute("SELECT COUNT(*) FROM tenants")
            total = cur.fetchone()['count']
        
        conn.close()
        
        return {
            "tenants": [dict(t) for t in tenants],
            "total": total,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"❌ Error listing tenants: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tenants/{tenant_id}")
async def get_tenant(
    tenant_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    🔍 Obtener detalles de un tenant específico.
    """
    try:
        conn = get_pg_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    t.*,
                    s.status as subscription_status,
                    s.trial_end,
                    s.is_trial,
                    sp.name as plan_name,
                    sp.price_monthly
                FROM tenants t
                LEFT JOIN subscriptions s ON s.tenant_id = t.id
                LEFT JOIN subscription_plans sp ON s.plan_id = sp.id
                WHERE t.id::text = %s OR t.tenant_id = %s
            """, (tenant_id, tenant_id))
            tenant = cur.fetchone()
            
            if not tenant:
                raise HTTPException(status_code=404, detail="Tenant no encontrado")
            
            # Get users
            cur.execute("""
                SELECT u.id::text, u.username, u.email, u.full_name, u.is_active, u.is_global_admin
                FROM users u
                JOIN user_tenants ut ON u.id = ut.user_id
                WHERE ut.tenant_id::text = %s
            """, (str(tenant['id']),))
            users = cur.fetchall()
            
            # Get cases count
            cur.execute("""
                SELECT COUNT(*) as count FROM cases WHERE tenant_id = %s
            """, (str(tenant['id']),))
            cases_count = cur.fetchone()['count']
        
        conn.close()
        
        tenant_dict = dict(tenant)
        tenant_dict['id'] = str(tenant_dict['id'])
        tenant_dict['users'] = [dict(u) for u in users]
        tenant_dict['users_count'] = len(users)
        tenant_dict['cases_count'] = cases_count
        
        return {"tenant": tenant_dict}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting tenant: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tenants")
async def create_tenant(
    tenant_data: TenantCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    ➕ Crear nuevo tenant.
    """
    try:
        conn = get_pg_connection()
        tenant_uuid = str(uuid4())
        tenant_id = f"Jeturing_{tenant_uuid[:8]}"
        schema_name = f"tenant_{tenant_data.subdomain.lower().replace('-', '_')}"
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Check if subdomain exists
            cur.execute("SELECT id FROM tenants WHERE subdomain = %s", (tenant_data.subdomain,))
            if cur.fetchone():
                raise HTTPException(status_code=400, detail="Subdomain ya existe")
            
            # Create tenant
            cur.execute("""
                INSERT INTO tenants (
                    id, tenant_id, name, subdomain, schema_name,
                    contact_email, plan, max_users, max_cases, max_storage_gb,
                    is_active, is_suspended, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                RETURNING id::text, tenant_id, name, subdomain, plan, is_active, created_at
            """, (
                tenant_uuid, tenant_id, tenant_data.name, tenant_data.subdomain, schema_name,
                tenant_data.contact_email, tenant_data.plan, tenant_data.max_users,
                tenant_data.max_cases, tenant_data.max_storage_gb, True, False
            ))
            new_tenant = cur.fetchone()
            
            # Create default subscription (trial)
            subscription_id = str(uuid4())
            trial_end = datetime.utcnow() + timedelta(days=15)
            
            # Get free trial plan
            cur.execute("SELECT id FROM subscription_plans WHERE name ILIKE '%trial%' OR price_monthly = 0 LIMIT 1")
            plan_row = cur.fetchone()
            
            if plan_row:
                cur.execute("""
                    INSERT INTO subscriptions (
                        id, tenant_id, plan_id, status, is_trial, trial_end, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, NOW())
                """, (subscription_id, tenant_uuid, plan_row['id'], 'trialing', True, trial_end))
            
            conn.commit()
        
        conn.close()
        
        logger.info(f"✅ Tenant creado: {tenant_data.name}")
        
        return {"success": True, "tenant": dict(new_tenant)}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error creating tenant: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/tenants/{tenant_id}")
async def update_tenant(
    tenant_id: str,
    tenant_data: TenantUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    ✏️ Actualizar tenant existente.
    """
    try:
        conn = get_pg_connection()
        
        # Build dynamic update
        updates = []
        params = []
        
        for field, value in tenant_data.dict(exclude_unset=True).items():
            if value is not None:
                updates.append(f"{field} = %s")
                params.append(value)
        
        if not updates:
            raise HTTPException(status_code=400, detail="No hay campos para actualizar")
        
        updates.append("updated_at = NOW()")
        params.append(tenant_id)
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = f"""
                UPDATE tenants 
                SET {', '.join(updates)}
                WHERE id::text = %s OR tenant_id = %s
                RETURNING id::text, tenant_id, name, plan, is_active, is_suspended
            """
            params.append(tenant_id)
            cur.execute(query, params)
            updated_tenant = cur.fetchone()
            
            if not updated_tenant:
                raise HTTPException(status_code=404, detail="Tenant no encontrado")
            
            conn.commit()
        
        conn.close()
        
        logger.info(f"✅ Tenant actualizado: {tenant_id}")
        
        return {"success": True, "tenant": dict(updated_tenant)}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating tenant: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/tenants/{tenant_id}")
async def delete_tenant(
    tenant_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    🗑️ Eliminar tenant (soft delete - marks as suspended).
    """
    try:
        conn = get_pg_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                UPDATE tenants 
                SET is_active = false, is_suspended = true, 
                    suspension_reason = 'Deleted by global admin',
                    updated_at = NOW()
                WHERE id::text = %s OR tenant_id = %s
                RETURNING name
            """, (tenant_id, tenant_id))
            deleted = cur.fetchone()
            
            if not deleted:
                raise HTTPException(status_code=404, detail="Tenant no encontrado")
            
            conn.commit()
        
        conn.close()
        
        logger.info(f"✅ Tenant eliminado (soft): {deleted['name']}")
        
        return {"success": True, "message": f"Tenant {deleted['name']} suspendido"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting tenant: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# BILLING / SUBSCRIPTIONS
# ============================================================================

@router.get("/subscriptions")
async def list_subscriptions(
    status: Optional[str] = None,
    limit: int = Query(50, le=200),
    current_user: dict = Depends(get_current_user)
):
    """
    💳 Listar todas las suscripciones.
    """
    try:
        conn = get_pg_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = """
                SELECT 
                    s.id::text,
                    t.name as tenant,
                    t.tenant_id,
                    sp.name as plan,
                    s.status,
                    s.is_trial,
                    s.trial_end,
                    s.billing_period,
                    s.current_period_end as next_billing,
                    s.stripe_subscription_id as stripe_id,
                    sp.price_monthly as amount,
                    s.created_at
                FROM subscriptions s
                JOIN tenants t ON s.tenant_id = t.id
                JOIN subscription_plans sp ON s.plan_id = sp.id
                WHERE 1=1
            """
            params = []
            
            if status:
                query += " AND s.status = %s"
                params.append(status)
            
            query += " ORDER BY s.created_at DESC LIMIT %s"
            params.append(limit)
            
            cur.execute(query, params)
            subscriptions = cur.fetchall()
        
        conn.close()
        
        return {"subscriptions": [dict(s) for s in subscriptions]}
        
    except Exception as e:
        logger.error(f"❌ Error listing subscriptions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/invoices")
async def list_invoices(
    status: Optional[str] = None,
    limit: int = Query(50, le=200),
    current_user: dict = Depends(get_current_user)
):
    """
    📄 Listar todas las facturas.
    """
    try:
        conn = get_pg_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = """
                SELECT 
                    bi.id::text,
                    bi.invoice_number as id,
                    t.name as tenant,
                    bi.amount_due as amount,
                    bi.status,
                    bi.invoice_date as date,
                    bi.due_date,
                    bi.paid_at as paid_date,
                    bi.stripe_invoice_id
                FROM billing_invoices bi
                JOIN tenants t ON bi.tenant_id = t.id
                WHERE 1=1
            """
            params = []
            
            if status:
                query += " AND bi.status = %s"
                params.append(status)
            
            query += " ORDER BY bi.invoice_date DESC LIMIT %s"
            params.append(limit)
            
            cur.execute(query, params)
            invoices = cur.fetchall()
        
        conn.close()
        
        return {"invoices": [dict(i) for i in invoices]}
        
    except Exception as e:
        logger.error(f"❌ Error listing invoices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/billing-stats")
async def get_billing_stats(
    current_user: dict = Depends(get_current_user)
):
    """
    📊 Obtener estadísticas de billing.
    """
    try:
        conn = get_pg_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # MRR (Monthly Recurring Revenue)
            cur.execute("""
                SELECT COALESCE(SUM(sp.price_monthly), 0) as total_mrr
                FROM subscriptions s
                JOIN subscription_plans sp ON s.plan_id = sp.id
                WHERE s.status = 'active'
            """)
            mrr = cur.fetchone()['total_mrr'] or 0
            
            # Active subscriptions
            cur.execute("SELECT COUNT(*) FROM subscriptions WHERE status = 'active'")
            active_subs = cur.fetchone()['count']
            
            # Trial subscriptions
            cur.execute("SELECT COUNT(*) FROM subscriptions WHERE status = 'trialing' OR is_trial = true")
            trial_subs = cur.fetchone()['count']
            
            # Pending invoices
            cur.execute("SELECT COUNT(*) FROM billing_invoices WHERE status = 'pending'")
            pending_inv = cur.fetchone()['count']
            
            # Overdue amount
            cur.execute("""
                SELECT COALESCE(SUM(amount_due), 0) as total
                FROM billing_invoices 
                WHERE status = 'overdue' OR (status = 'pending' AND due_date < NOW())
            """)
            overdue = cur.fetchone()['total'] or 0
        
        conn.close()
        
        return {
            "totalMRR": float(mrr),
            "activeSubscriptions": active_subs,
            "trialSubscriptions": trial_subs,
            "pendingInvoices": pending_inv,
            "overdueAmount": float(overdue)
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting billing stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PLATFORM STATS (for global admin dashboard)
# ============================================================================

@router.get("/stats")
async def get_platform_stats(
    current_user: dict = Depends(get_current_user)
):
    """
    📊 Obtener estadísticas globales de la plataforma.
    """
    try:
        conn = get_pg_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Total tenants
            cur.execute("SELECT COUNT(*) FROM tenants")
            total_tenants = cur.fetchone()['count']
            
            # Active tenants
            cur.execute("SELECT COUNT(*) FROM tenants WHERE is_active = true AND is_suspended = false")
            active_tenants = cur.fetchone()['count']
            
            # Total users
            cur.execute("SELECT COUNT(*) FROM users")
            total_users = cur.fetchone()['count']
            
            # Total cases
            cur.execute("SELECT COUNT(*) FROM cases")
            total_cases = cur.fetchone()['count']
            
            # Total analyses (investigations)
            cur.execute("SELECT COUNT(*) FROM investigations")
            total_analyses = cur.fetchone()['count']
            
            # MRR
            cur.execute("""
                SELECT COALESCE(SUM(sp.price_monthly), 0) as total
                FROM subscriptions s
                JOIN subscription_plans sp ON s.plan_id = sp.id
                WHERE s.status = 'active'
            """)
            revenue_mtd = cur.fetchone()['total'] or 0
        
        conn.close()
        
        return {
            "total_tenants": total_tenants,
            "active_tenants": active_tenants,
            "total_users": total_users,
            "total_cases": total_cases,
            "total_analyses": total_analyses,
            "revenue_mtd": float(revenue_mtd),
            "storage_used_gb": 0.0  # TODO: Calculate from MinIO
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting platform stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ACTIVITY LOG
# ============================================================================

@router.get("/activity")
async def get_platform_activity(
    limit: int = 20,
    _: dict = Depends(require_global_admin)
):
    """
    Obtener actividad reciente de la plataforma
    """
    try:
        conn = get_pg_connection()
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get recent logins - usando user_tenants para la relación
            cur.execute("""
                SELECT 
                    u.id,
                    u.username,
                    u.email,
                    u.last_login,
                    t.name as tenant_name,
                    'login' as action_type
                FROM users u
                LEFT JOIN user_tenants ut ON u.id = ut.user_id
                LEFT JOIN tenants t ON ut.tenant_id = t.id
                WHERE u.last_login IS NOT NULL
                ORDER BY u.last_login DESC
                LIMIT %s
            """, (limit,))
            activities = cur.fetchall()
        
        conn.close()
        
        result = []
        for a in activities:
            result.append({
                "id": str(a['id']),
                "user": a['username'],
                "email": a['email'],
                "tenant": a['tenant_name'],
                "action": a['action_type'],
                "timestamp": a['last_login'].isoformat() if a['last_login'] else None,
                "details": f"User {a['username']} logged in"
            })
        
        return {"activities": result, "total": len(result)}
        
    except Exception as e:
        logger.error(f"❌ Error getting activity: {e}")
        raise HTTPException(status_code=500, detail=str(e))
