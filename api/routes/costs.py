"""
Cost Management API Routes
Gestión de precios, planes y costos de recursos
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime, date
import uuid
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
import json

from api.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/costs", tags=["Cost Management"])

# ============================================================================
# DATABASE CONNECTION HELPER
# ============================================================================

def get_db_connection():
    """Obtiene conexión a PostgreSQL"""
    try:
        return psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD
        )
    except Exception as e:
        logger.error(f"❌ Database connection error: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")

# ============================================================================
# MODELS
# ============================================================================

class ServicePlanBase(BaseModel):
    plan_code: str = Field(..., max_length=50)
    plan_name: str = Field(..., max_length=100)
    plan_description: Optional[str] = None
    price_monthly_cents: int = Field(ge=0)
    price_annually_cents: int = Field(ge=0)
    max_users: int = Field(default=-1)
    max_cases_monthly: int = Field(default=-1)
    max_analyses_monthly: int = Field(default=-1)
    max_storage_gb: int = Field(default=-1)
    max_api_calls_daily: int = Field(default=-1)
    features: dict = Field(default_factory=dict)
    is_active: bool = True
    is_visible: bool = True
    sort_order: int = 0

class ServicePlanResponse(ServicePlanBase):
    id: int
    stripe_product_id: Optional[str]
    stripe_price_monthly_id: Optional[str]
    stripe_price_annually_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    price_monthly_usd: float
    price_annually_usd: float
    annual_savings_percentage: float
    
    class Config:
        from_attributes = True

class ResourceCostBase(BaseModel):
    resource_type: str = Field(..., max_length=50)
    resource_name: str = Field(..., max_length=100)
    resource_description: Optional[str] = None
    cost_per_unit_cents: int = Field(ge=0)
    billing_unit: str = Field(default="unit")
    tool_name: Optional[str] = None
    is_billable: bool = True
    min_billable_units: int = Field(default=1, ge=1)

class ResourceCostResponse(ResourceCostBase):
    id: int
    effective_from: datetime
    effective_until: Optional[datetime]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    cost_per_unit_usd: float
    
    class Config:
        from_attributes = True

class ResourceUsageBase(BaseModel):
    tenant_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    case_id: Optional[uuid.UUID] = None
    resource_type: str
    resource_name: str
    units_consumed: Decimal = Field(gt=0)
    tool_name: Optional[str] = None
    execution_time_seconds: Optional[int] = None

class ResourceUsageResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: Optional[uuid.UUID]
    case_id: Optional[uuid.UUID]
    resource_type: str
    resource_name: str
    units_consumed: Decimal
    cost_per_unit_cents: int
    total_cost_cents: int
    total_cost_usd: float
    tool_name: Optional[str]
    billing_period: str
    is_billed: bool
    consumed_at: datetime
    
    class Config:
        from_attributes = True

class TenantCostSummary(BaseModel):
    tenant_id: uuid.UUID
    billing_period: str
    total_operations: int
    total_units: Decimal
    total_cost_cents: int
    total_cost_usd: float
    cases_count: int
    users_count: int
    period_start: datetime
    period_end: datetime

class ToolCostSummary(BaseModel):
    tenant_id: uuid.UUID
    tool_name: str
    billing_period: str
    execution_count: int
    total_units: Decimal
    total_cost_cents: int
    total_cost_usd: float
    avg_execution_seconds: Optional[float]
    last_used: datetime

class CostCalculationRequest(BaseModel):
    resource_type: str
    units: Decimal = Field(gt=0)
    tool_name: Optional[str] = None

class CostCalculationResponse(BaseModel):
    resource_type: str
    units: float
    tool_name: Optional[str]
    cost_per_unit_cents: int
    total_cost_cents: int
    total_cost_usd: float

# ============================================================================
# SERVICE PLANS ENDPOINTS
# ============================================================================

@router.get("/plans", response_model=List[ServicePlanResponse])
async def list_service_plans(
    include_hidden: bool = Query(False, description="Incluir planes no visibles"),
    active_only: bool = Query(True, description="Solo planes activos")
):
    """
    Lista todos los planes de servicio disponibles.
    Los planes incluyen precios, límites y features.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = "SELECT * FROM service_plans"
        conditions = []
        
        if active_only:
            conditions.append("is_active = TRUE")
        if not include_hidden:
            conditions.append("is_visible = TRUE")
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY sort_order ASC, plan_code ASC"
        
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()
        
        plans = []
        for row in rows:
            plan = ServicePlanResponse(
                id=row['id'],
                plan_code=row['plan_code'],
                plan_name=row['plan_name'],
                plan_description=row['plan_description'],
                price_monthly_cents=row['price_monthly_cents'],
                price_annually_cents=row['price_annually_cents'],
                max_users=row['max_users'],
                max_cases_monthly=row['max_cases_monthly'],
                max_analyses_monthly=row['max_analyses_monthly'],
                max_storage_gb=row['max_storage_gb'],
                max_api_calls_daily=row['max_api_calls_daily'],
                features=row['features'] or {},
                is_active=row['is_active'],
                is_visible=row['is_visible'],
                sort_order=row['sort_order'],
                stripe_product_id=row['stripe_product_id'],
                stripe_price_monthly_id=row['stripe_price_monthly_id'],
                stripe_price_annually_id=row['stripe_price_annually_id'],
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                price_monthly_usd=row['price_monthly_cents'] / 100,
                price_annually_usd=row['price_annually_cents'] / 100,
                annual_savings_percentage=20 if row['price_monthly_cents'] > 0 else 0
            )
            plans.append(plan)
        
        logger.info(f"✅ Listed {len(plans)} service plans")
        return plans
        
    except Exception as e:
        logger.error(f"❌ Error listing plans: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()

@router.get("/plans/{plan_code}", response_model=ServicePlanResponse)
async def get_service_plan(plan_code: str):
    """Obtiene detalles de un plan específico por código."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute(
            "SELECT * FROM service_plans WHERE plan_code = %s",
            (plan_code,)
        )
        row = cursor.fetchone()
        cursor.close()
        
        if not row:
            raise HTTPException(status_code=404, detail=f"Plan '{plan_code}' not found")
        
        plan = ServicePlanResponse(
            id=row['id'],
            plan_code=row['plan_code'],
            plan_name=row['plan_name'],
            plan_description=row['plan_description'],
            price_monthly_cents=row['price_monthly_cents'],
            price_annually_cents=row['price_annually_cents'],
            max_users=row['max_users'],
            max_cases_monthly=row['max_cases_monthly'],
            max_analyses_monthly=row['max_analyses_monthly'],
            max_storage_gb=row['max_storage_gb'],
            max_api_calls_daily=row['max_api_calls_daily'],
            features=row['features'] or {},
            is_active=row['is_active'],
            is_visible=row['is_visible'],
            sort_order=row['sort_order'],
            stripe_product_id=row['stripe_product_id'],
            stripe_price_monthly_id=row['stripe_price_monthly_id'],
            stripe_price_annually_id=row['stripe_price_annually_id'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            price_monthly_usd=row['price_monthly_cents'] / 100,
            price_annually_usd=row['price_annually_cents'] / 100,
            annual_savings_percentage=20 if row['price_monthly_cents'] > 0 else 0
        )
        return plan
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()

@router.post("/plans", response_model=ServicePlanResponse)
async def create_service_plan(plan: ServicePlanBase):
    """Crea un nuevo plan de servicio. Requiere permisos de administrador."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            INSERT INTO service_plans (
                plan_code, plan_name, plan_description, 
                price_monthly_cents, price_annually_cents,
                max_users, max_cases_monthly, max_analyses_monthly,
                max_storage_gb, max_api_calls_daily, features,
                is_active, is_visible, sort_order
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING *
        """, (
            plan.plan_code, plan.plan_name, plan.plan_description,
            plan.price_monthly_cents, plan.price_annually_cents,
            plan.max_users, plan.max_cases_monthly, plan.max_analyses_monthly,
            plan.max_storage_gb, plan.max_api_calls_daily,
            json.dumps(plan.features) if plan.features else None,
            plan.is_active, plan.is_visible, plan.sort_order
        ))
        
        row = cursor.fetchone()
        conn.commit()
        cursor.close()
        
        result = ServicePlanResponse(
            id=row['id'],
            plan_code=row['plan_code'],
            plan_name=row['plan_name'],
            plan_description=row['plan_description'],
            price_monthly_cents=row['price_monthly_cents'],
            price_annually_cents=row['price_annually_cents'],
            max_users=row['max_users'],
            max_cases_monthly=row['max_cases_monthly'],
            max_analyses_monthly=row['max_analyses_monthly'],
            max_storage_gb=row['max_storage_gb'],
            max_api_calls_daily=row['max_api_calls_daily'],
            features=row['features'] or {},
            is_active=row['is_active'],
            is_visible=row['is_visible'],
            sort_order=row['sort_order'],
            stripe_product_id=row['stripe_product_id'],
            stripe_price_monthly_id=row['stripe_price_monthly_id'],
            stripe_price_annually_id=row['stripe_price_annually_id'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            price_monthly_usd=row['price_monthly_cents'] / 100,
            price_annually_usd=row['price_annually_cents'] / 100,
            annual_savings_percentage=20 if row['price_monthly_cents'] > 0 else 0
        )
        
        logger.info(f"✅ Created plan: {plan.plan_code}")
        return result
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"❌ Error creating plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()

@router.put("/plans/{plan_id}", response_model=ServicePlanResponse)
async def update_service_plan(plan_id: int, plan: ServicePlanBase):
    """Actualiza un plan de servicio existente."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            UPDATE service_plans
            SET 
                plan_code = %s,
                plan_name = %s,
                plan_description = %s,
                price_monthly_cents = %s,
                price_annually_cents = %s,
                max_users = %s,
                max_cases_monthly = %s,
                max_analyses_monthly = %s,
                max_storage_gb = %s,
                max_api_calls_daily = %s,
                features = %s,
                is_active = %s,
                is_visible = %s,
                sort_order = %s,
                updated_at = NOW()
            WHERE id = %s
            RETURNING *
        """, (
            plan.plan_code, plan.plan_name, plan.plan_description,
            plan.price_monthly_cents, plan.price_annually_cents,
            plan.max_users, plan.max_cases_monthly, plan.max_analyses_monthly,
            plan.max_storage_gb, plan.max_api_calls_daily,
            json.dumps(plan.features) if plan.features else None,
            plan.is_active, plan.is_visible, plan.sort_order,
            plan_id
        ))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Plan not found")
        
        conn.commit()
        cursor.close()
        
        result = ServicePlanResponse(
            id=row['id'],
            plan_code=row['plan_code'],
            plan_name=row['plan_name'],
            plan_description=row['plan_description'],
            price_monthly_cents=row['price_monthly_cents'],
            price_annually_cents=row['price_annually_cents'],
            max_users=row['max_users'],
            max_cases_monthly=row['max_cases_monthly'],
            max_analyses_monthly=row['max_analyses_monthly'],
            max_storage_gb=row['max_storage_gb'],
            max_api_calls_daily=row['max_api_calls_daily'],
            features=row['features'] or {},
            is_active=row['is_active'],
            is_visible=row['is_visible'],
            sort_order=row['sort_order'],
            stripe_product_id=row['stripe_product_id'],
            stripe_price_monthly_id=row['stripe_price_monthly_id'],
            stripe_price_annually_id=row['stripe_price_annually_id'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            price_monthly_usd=row['price_monthly_cents'] / 100,
            price_annually_usd=row['price_annually_cents'] / 100,
            annual_savings_percentage=20 if row['price_monthly_cents'] > 0 else 0
        )
        
        logger.info(f"✅ Updated plan: {plan.plan_code}")
        return result
        
    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"❌ Error updating plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()

# ============================================================================
# RESOURCE COSTS ENDPOINTS
# ============================================================================

@router.get("/resources", response_model=List[ResourceCostResponse])
async def list_resource_costs(
    resource_type: Optional[str] = Query(None, description="Filtrar por tipo"),
    tool_name: Optional[str] = Query(None, description="Filtrar por herramienta"),
    active_only: bool = Query(True, description="Solo costos activos")
):
    """Lista todos los costos de recursos configurados."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = "SELECT * FROM resource_costs"
        conditions = ["effective_until IS NULL OR effective_until > NOW()"]
        
        if active_only:
            conditions.append("is_active = TRUE")
        if resource_type:
            conditions.append("resource_type = %s")
        if tool_name:
            conditions.append("tool_name = %s")
        
        query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY tool_name, resource_type"
        
        params = []
        if resource_type:
            params.append(resource_type)
        if tool_name:
            params.append(tool_name)
        
        cursor.execute(query, params if params else None)
        rows = cursor.fetchall()
        cursor.close()
        
        costs = []
        for row in rows:
            cost = ResourceCostResponse(
                id=row['id'],
                resource_type=row['resource_type'],
                resource_name=row['resource_name'],
                resource_description=row['resource_description'],
                cost_per_unit_cents=row['cost_per_unit_cents'],
                billing_unit=row['billing_unit'],
                tool_name=row['tool_name'],
                is_billable=row['is_billable'],
                min_billable_units=row['min_billable_units'],
                effective_from=row['effective_from'],
                effective_until=row['effective_until'],
                is_active=row['is_active'],
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                cost_per_unit_usd=row['cost_per_unit_cents'] / 100
            )
            costs.append(cost)
        
        logger.info(f"✅ Listed {len(costs)} resource costs")
        return costs
        
    except Exception as e:
        logger.error(f"❌ Error listing resource costs: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()

@router.get("/resources/{resource_id}", response_model=ResourceCostResponse)
async def get_resource_cost(resource_id: int):
    """Obtiene detalles de un costo de recurso específico."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("SELECT * FROM resource_costs WHERE id = %s", (resource_id,))
        row = cursor.fetchone()
        cursor.close()
        
        if not row:
            raise HTTPException(status_code=404, detail="Resource cost not found")
        
        cost = ResourceCostResponse(
            id=row['id'],
            resource_type=row['resource_type'],
            resource_name=row['resource_name'],
            resource_description=row['resource_description'],
            cost_per_unit_cents=row['cost_per_unit_cents'],
            billing_unit=row['billing_unit'],
            tool_name=row['tool_name'],
            is_billable=row['is_billable'],
            min_billable_units=row['min_billable_units'],
            effective_from=row['effective_from'],
            effective_until=row['effective_until'],
            is_active=row['is_active'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            cost_per_unit_usd=row['cost_per_unit_cents'] / 100
        )
        return cost
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting resource cost: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()

@router.post("/resources", response_model=ResourceCostResponse)
async def create_resource_cost(cost: ResourceCostBase):
    """Crea una nueva configuración de costo de recurso."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            INSERT INTO resource_costs (
                resource_type, resource_name, resource_description,
                cost_per_unit_cents, billing_unit, tool_name,
                is_billable, min_billable_units, effective_from
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
            RETURNING *
        """, (
            cost.resource_type, cost.resource_name, cost.resource_description,
            cost.cost_per_unit_cents, cost.billing_unit, cost.tool_name,
            cost.is_billable, cost.min_billable_units
        ))
        
        row = cursor.fetchone()
        conn.commit()
        cursor.close()
        
        result = ResourceCostResponse(
            id=row['id'],
            resource_type=row['resource_type'],
            resource_name=row['resource_name'],
            resource_description=row['resource_description'],
            cost_per_unit_cents=row['cost_per_unit_cents'],
            billing_unit=row['billing_unit'],
            tool_name=row['tool_name'],
            is_billable=row['is_billable'],
            min_billable_units=row['min_billable_units'],
            effective_from=row['effective_from'],
            effective_until=row['effective_until'],
            is_active=row['is_active'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            cost_per_unit_usd=row['cost_per_unit_cents'] / 100
        )
        
        logger.info(f"✅ Created resource cost: {cost.resource_type}")
        return result
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"❌ Error creating resource cost: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()

@router.put("/resources/{resource_id}", response_model=ResourceCostResponse)
async def update_resource_cost(resource_id: int, cost: ResourceCostBase):
    """Actualiza una configuración de costo existente."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            UPDATE resource_costs
            SET 
                resource_type = %s,
                resource_name = %s,
                resource_description = %s,
                cost_per_unit_cents = %s,
                billing_unit = %s,
                tool_name = %s,
                is_billable = %s,
                min_billable_units = %s,
                updated_at = NOW()
            WHERE id = %s
            RETURNING *
        """, (
            cost.resource_type, cost.resource_name, cost.resource_description,
            cost.cost_per_unit_cents, cost.billing_unit, cost.tool_name,
            cost.is_billable, cost.min_billable_units,
            resource_id
        ))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Resource cost not found")
        
        conn.commit()
        cursor.close()
        
        result = ResourceCostResponse(
            id=row['id'],
            resource_type=row['resource_type'],
            resource_name=row['resource_name'],
            resource_description=row['resource_description'],
            cost_per_unit_cents=row['cost_per_unit_cents'],
            billing_unit=row['billing_unit'],
            tool_name=row['tool_name'],
            is_billable=row['is_billable'],
            min_billable_units=row['min_billable_units'],
            effective_from=row['effective_from'],
            effective_until=row['effective_until'],
            is_active=row['is_active'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            cost_per_unit_usd=row['cost_per_unit_cents'] / 100
        )
        
        logger.info(f"✅ Updated resource cost: {cost.resource_type}")
        return result
        
    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"❌ Error updating resource cost: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()

# ============================================================================
# USAGE TRACKING ENDPOINTS
# ============================================================================

@router.post("/usage", response_model=Dict[str, Any])
async def register_usage(usage: ResourceUsageBase):
    """
    Registra consumo de un recurso.
    Se calcula automáticamente el costo basado en la configuración actual.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Llamar función SQL que calcula el costo automáticamente
        cursor.execute("""
            SELECT register_resource_usage(
                %s::UUID, 'analysis', %s, %s,
                %s::UUID, %s::UUID, NULL, %s, %s
            ) as usage_id
        """, (
            usage.tenant_id, usage.resource_name, float(usage.units_consumed),
            usage.user_id, usage.case_id, usage.tool_name, 
            usage.execution_time_seconds or 0
        ))
        
        row = cursor.fetchone()
        conn.commit()
        cursor.close()
        
        logger.info(f"✅ Registered usage: {usage.resource_type} - {usage.units_consumed} units")
        
        return {
            "status": "success",
            "usage_id": str(row['usage_id']) if row else None,
            "resource_type": usage.resource_type,
            "units_consumed": float(usage.units_consumed),
            "tool_name": usage.tool_name
        }
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"❌ Error registering usage: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()

@router.get("/usage/tenant/{tenant_id}")
async def get_tenant_costs(
    tenant_id: uuid.UUID,
    billing_period: Optional[str] = Query(None, description="YYYY-MM")
):
    """
    Obtiene resumen de costos de un tenant.
    Si no se especifica período, usa el mes actual.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        if not billing_period:
            from datetime import datetime
            billing_period = datetime.now().strftime("%Y-%m")
        
        cursor.execute("""
            SELECT 
                tenant_id,
                billing_period,
                COUNT(*) as total_operations,
                SUM(units_consumed) as total_units,
                SUM(total_cost_cents) as total_cost_cents,
                (SELECT COUNT(DISTINCT case_id) FROM resource_usage 
                 WHERE tenant_id = %s AND billing_period = %s) as cases_count
            FROM resource_usage
            WHERE tenant_id = %s AND billing_period = %s
            GROUP BY tenant_id, billing_period
        """, (tenant_id, billing_period, tenant_id, billing_period))
        
        row = cursor.fetchone()
        cursor.close()
        
        if not row:
            raise HTTPException(status_code=404, detail="No costs found for this period")
        
        return {
            "tenant_id": str(row['tenant_id']),
            "billing_period": row['billing_period'],
            "total_operations": row['total_operations'],
            "total_units": float(row['total_units'] or 0),
            "total_cost_cents": row['total_cost_cents'] or 0,
            "total_cost_usd": (row['total_cost_cents'] or 0) / 100,
            "cases_count": row['cases_count'] or 0,
            "users_count": 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting tenant costs: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()

@router.get("/usage/tenant/{tenant_id}/by-tool")
async def get_tenant_costs_by_tool(
    tenant_id: uuid.UUID,
    billing_period: Optional[str] = Query(None, description="YYYY-MM")
):
    """Obtiene resumen de costos por herramienta de un tenant."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        if not billing_period:
            from datetime import datetime
            billing_period = datetime.now().strftime("%Y-%m")
        
        cursor.execute("""
            SELECT 
                tool_name,
                COUNT(*) as execution_count,
                SUM(units_consumed) as total_units,
                SUM(total_cost_cents) as total_cost_cents,
                AVG(EXTRACT(EPOCH FROM (consumed_at - consumed_at))) as avg_execution_seconds,
                MAX(consumed_at) as last_used
            FROM resource_usage
            WHERE tenant_id = %s AND billing_period = %s AND tool_name IS NOT NULL
            GROUP BY tool_name
            ORDER BY total_cost_cents DESC
        """, (tenant_id, billing_period))
        
        rows = cursor.fetchall()
        cursor.close()
        
        tools = []
        for row in rows:
            tools.append({
                "tenant_id": str(tenant_id),
                "tool_name": row['tool_name'],
                "billing_period": billing_period,
                "execution_count": row['execution_count'],
                "total_units": float(row['total_units'] or 0),
                "total_cost_cents": row['total_cost_cents'] or 0,
                "total_cost_usd": (row['total_cost_cents'] or 0) / 100,
                "avg_execution_seconds": row['avg_execution_seconds'],
                "last_used": row['last_used'].isoformat() if row['last_used'] else None
            })
        
        return tools
        
    except Exception as e:
        logger.error(f"❌ Error getting tenant costs by tool: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()

@router.get("/usage/case/{case_id}")
async def get_case_costs(case_id: uuid.UUID):
    """Obtiene costos acumulados de un caso específico."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT 
                case_id,
                COUNT(*) as operation_count,
                SUM(units_consumed) as total_units,
                SUM(total_cost_cents) as total_cost_cents,
                MIN(consumed_at) as started_at,
                MAX(consumed_at) as ended_at
            FROM resource_usage
            WHERE case_id = %s
            GROUP BY case_id
        """, (case_id,))
        
        row = cursor.fetchone()
        cursor.close()
        
        if not row:
            raise HTTPException(status_code=404, detail="No costs found for this case")
        
        return {
            "case_id": str(row['case_id']),
            "operation_count": row['operation_count'],
            "total_units": float(row['total_units'] or 0),
            "total_cost_cents": row['total_cost_cents'] or 0,
            "total_cost_usd": (row['total_cost_cents'] or 0) / 100,
            "started_at": row['started_at'].isoformat() if row['started_at'] else None,
            "ended_at": row['ended_at'].isoformat() if row['ended_at'] else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting case costs: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()

# ============================================================================
# PRICING CALCULATOR ENDPOINT
# ============================================================================

@router.post("/calculate", response_model=CostCalculationResponse)
async def calculate_estimated_cost(request: CostCalculationRequest):
    """
    Calcula costo estimado para una operación.
    Útil para mostrar precios antes de ejecutar análisis.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Buscar costo según tipo de recurso y herramienta
        query = """
            SELECT cost_per_unit_cents
            FROM resource_costs
            WHERE is_active = TRUE
              AND (effective_until IS NULL OR effective_until > NOW())
              AND resource_type = %s
        """
        params = [request.resource_type]
        
        if request.tool_name:
            query += " AND tool_name = %s"
            params.append(request.tool_name)
        
        query += " ORDER BY effective_from DESC LIMIT 1"
        
        cursor.execute(query, params)
        row = cursor.fetchone()
        cursor.close()
        
        if not row:
            raise HTTPException(status_code=404, detail=f"No pricing found for {request.resource_type}")
        
        cost_per_unit_cents = row['cost_per_unit_cents']
        total_cost_cents = int(float(request.units) * cost_per_unit_cents)
        
        logger.info(f"✅ Calculated cost: {total_cost_cents} cents")
        
        return CostCalculationResponse(
            resource_type=request.resource_type,
            units=float(request.units),
            tool_name=request.tool_name,
            cost_per_unit_cents=cost_per_unit_cents,
            total_cost_cents=total_cost_cents,
            total_cost_usd=total_cost_cents / 100
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error calculating cost: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()

# ============================================================================
# ADMIN ENDPOINTS
# ============================================================================

@router.post("/admin/bulk-update-costs")
async def bulk_update_costs(updates: List[Dict[str, Any]]):
    """Actualiza múltiples costos de recursos en batch. Útil para ajustes anuales."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        updated_count = 0
        for update in updates:
            cursor.execute("""
                UPDATE resource_costs
                SET cost_per_unit_cents = %s, updated_at = NOW()
                WHERE id = %s
            """, (update['cost_per_unit_cents'], update['id']))
            updated_count += cursor.rowcount
        
        conn.commit()
        cursor.close()
        
        logger.info(f"✅ Bulk updated {updated_count} resource costs")
        
        return {
            "status": "success",
            "updated_count": updated_count
        }
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"❌ Error bulk updating costs: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()

@router.get("/admin/revenue-report")
async def get_revenue_report(
    start_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="YYYY-MM-DD")
):
    """Genera reporte de ingresos por período."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Query base para ingresos totales
        query = "SELECT SUM(total_cost_cents) as total FROM resource_usage WHERE is_billed = TRUE"
        params = []
        
        if start_date:
            query += " AND consumed_at::date >= %s"
            params.append(start_date)
        if end_date:
            query += " AND consumed_at::date <= %s"
            params.append(end_date)
        
        cursor.execute(query, params if params else None)
        row = cursor.fetchone()
        total_revenue_cents = row['total'] or 0 if row else 0
        
        # Revenue by plan
        cursor.execute("""
            SELECT sp.plan_code, sp.plan_name, COUNT(*) as tenant_count
            FROM service_plans sp
            GROUP BY sp.plan_code, sp.plan_name
        """)
        by_plan = [dict(row) for row in cursor.fetchall()]
        
        cursor.close()
        
        return {
            "period": {
                "start": start_date or "all",
                "end": end_date or "all"
            },
            "total_revenue_cents": total_revenue_cents,
            "total_revenue_usd": total_revenue_cents / 100,
            "by_plan": by_plan,
            "by_resource_type": []
        }
        
    except Exception as e:
        logger.error(f"❌ Error generating revenue report: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()
