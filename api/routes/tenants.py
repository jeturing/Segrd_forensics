"""
Multi-Tenant Routes - Gestión de tenants y onboarding
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from api.services.multi_tenant import multi_tenant
from api.services.forensic_tools import forensic_tools

# Router sin prefix - el main.py agrega /tenants
router = APIRouter(tags=["tenants"])


# ==================== MODELS ====================

class TenantOnboardRequest(BaseModel):
    name: Optional[str] = Field(None, description="Nombre personalizado para el tenant")
    tenant_id: str = Field(..., description="Azure AD Tenant ID")
    client_id: str = Field(..., description="App Registration Client ID")
    client_secret: str = Field(..., description="App Registration Client Secret")
    notes: Optional[str] = None
    created_by: Optional[str] = None


class TenantUpdateRequest(BaseModel):
    tenant_name: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class RunAnalysisRequest(BaseModel):
    case_id: str
    tools: List[str] = ["sparrow", "hawk"]
    user_upn: Optional[str] = None


# ==================== TENANT MANAGEMENT ====================

@router.get("/")
async def list_tenants(include_inactive: bool = False):
    """Listar todos los tenants registrados"""
    tenants = multi_tenant.get_all_tenants(include_inactive=include_inactive)
    return {
        "count": len(tenants),
        "tenants": tenants
    }


@router.get("/active")
async def get_active_tenant():
    """Obtener el tenant actualmente activo"""
    tenant = multi_tenant.get_active_tenant()
    if not tenant:
        return {"active": False, "tenant": None}
    
    # Agregar estadísticas
    stats = multi_tenant.get_tenant_stats(tenant['tenant_id'])
    tenant["stats"] = stats
    
    return {"active": True, "tenant": tenant}


@router.get("/{tenant_id}")
async def get_tenant(tenant_id: str):
    """Obtener información de un tenant específico"""
    tenant = multi_tenant.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")
    
    # Agregar estadísticas
    stats = multi_tenant.get_tenant_stats(tenant_id)
    tenant["stats"] = stats
    
    return tenant


@router.post("/onboard")
async def onboard_tenant(request: TenantOnboardRequest):
    """
    Onboarding de un nuevo tenant M365
    
    Requiere:
    - Tenant ID de Azure AD
    - Client ID de una App Registration
    - Client Secret de la App
    
    La App debe tener los siguientes permisos (Application):
    - User.Read.All
    - Directory.Read.All
    - AuditLog.Read.All
    - Organization.Read.All
    """
    result = await multi_tenant.onboard_tenant(
        tenant_id=request.tenant_id,
        client_id=request.client_id,
        client_secret=request.client_secret,
        notes=request.notes,
        created_by=request.created_by
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.put("/{tenant_id}")
async def update_tenant(tenant_id: str, request: TenantUpdateRequest):
    """Actualizar información de un tenant"""
    result = multi_tenant.update_tenant(
        tenant_id=tenant_id,
        **request.dict(exclude_none=True)
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.delete("/{tenant_id}")
async def delete_tenant(tenant_id: str, hard_delete: bool = False):
    """
    Eliminar un tenant
    
    - Sin hard_delete: Solo desactiva el tenant
    - Con hard_delete=true: Elimina permanentemente todo
    """
    result = multi_tenant.delete_tenant(tenant_id, hard_delete=hard_delete)
    return result


@router.post("/{tenant_id}/switch")
async def switch_active_tenant(tenant_id: str):
    """Cambiar el tenant activo"""
    result = multi_tenant.set_active_tenant(tenant_id)
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


# ==================== SYNC OPERATIONS ====================

@router.post("/{tenant_id}/sync")
class SyncTenantRequest(BaseModel):
    access_token: Optional[str] = None

@router.post("/{tenant_id}/sync")
async def sync_tenant(tenant_id: str, request: Optional[SyncTenantRequest] = None):
    """Sincronizar usuarios y datos de un tenant"""
    tenant = multi_tenant.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")
    
    token = request.access_token if request else None
    
    # Ejecutar sincronización
    result = await multi_tenant.sync_tenant_users(tenant_id, access_token=token)
    
    return {
        "tenant_id": tenant_id,
        "sync_result": result,
        "timestamp": datetime.now().isoformat()
    }


@router.post("/sync-all")
async def sync_all_tenants():
    """Sincronizar todos los tenants activos"""
    tenants = multi_tenant.get_all_tenants()
    results = []
    
    for tenant in tenants:
        result = await multi_tenant.sync_tenant_users(tenant['tenant_id'])
        results.append({
            "tenant_id": tenant['tenant_id'],
            "tenant_name": tenant['tenant_name'],
            "result": result
        })
    
    return {
        "tenants_synced": len(results),
        "results": results
    }


# ==================== TENANT-SCOPED DATA ====================

@router.get("/{tenant_id}/stats")
async def get_tenant_stats(tenant_id: str):
    """Obtener estadísticas de un tenant"""
    tenant = multi_tenant.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")
    
    return multi_tenant.get_tenant_stats(tenant_id)


@router.get("/{tenant_id}/cases")
async def get_tenant_cases(tenant_id: str, status: Optional[str] = None):
    """Obtener casos de un tenant"""
    return multi_tenant.get_tenant_cases(tenant_id, status)


@router.get("/{tenant_id}/users")
async def get_tenant_users(tenant_id: str):
    """Obtener usuarios de un tenant"""
    users = multi_tenant.get_tenant_users(tenant_id)
    return {
        "count": len(users),
        "users": users
    }


@router.get("/{tenant_id}/activity")
async def get_tenant_activity(tenant_id: str, limit: int = 50):
    """Obtener actividad de un tenant"""
    return multi_tenant.get_tenant_activity(tenant_id, limit)


# ==================== FORENSIC ANALYSIS ====================

@router.post("/{tenant_id}/analyze")
async def run_tenant_analysis(
    tenant_id: str, 
    request: RunAnalysisRequest,
    background_tasks: BackgroundTasks
):
    """
    Ejecutar análisis forense en un tenant
    
    Tools disponibles:
    - sparrow: Detección de compromisos M365
    - hawk: Investigación forense Exchange Online
    - loki: Scanner de IOCs (solo para endpoints locales)
    - yara: Escaneo con reglas YARA
    """
    tenant = multi_tenant._get_tenant_with_secret(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")
    
    # Crear registro de análisis
    
    # Ejecutar análisis en background
    if "sparrow" in request.tools and "hawk" in request.tools:
        # Análisis completo
        background_tasks.add_task(
            run_full_analysis_task,
            tenant_id,
            tenant['client_id'],
            tenant['client_secret'],
            request.case_id
        )
        return {
            "status": "queued",
            "case_id": request.case_id,
            "tools": request.tools,
            "message": "Análisis completo M365 iniciado en background"
        }
    
    results = {}
    
    if "sparrow" in request.tools:
        background_tasks.add_task(
            run_sparrow_task,
            tenant_id,
            tenant['client_id'],
            tenant['client_secret'],
            request.case_id
        )
        results["sparrow"] = "queued"
    
    if "hawk" in request.tools:
        background_tasks.add_task(
            run_hawk_task,
            tenant_id,
            tenant['client_id'],
            tenant['client_secret'],
            request.case_id,
            request.user_upn
        )
        results["hawk"] = "queued"
    
    return {
        "status": "queued",
        "case_id": request.case_id,
        "tools": results,
        "message": "Análisis iniciado en background"
    }


# ==================== BACKGROUND TASKS ====================

async def run_sparrow_task(tenant_id: str, client_id: str, client_secret: str, case_id: str):
    """Task para ejecutar Sparrow"""
    try:
        result = await forensic_tools.run_sparrow(
            tenant_id, client_id, client_secret, case_id
        )
        
        # Guardar IOCs detectados
        if result.get("success") and result.get("findings"):
            from api.services.dashboard_data import dashboard_data
            for item in result["findings"].get("suspicious_items", []):
                dashboard_data.add_ioc(
                    case_id=case_id,
                    ioc_type=item.get("type", "unknown"),
                    value=str(item.get("details", {}))[:500],
                    severity=item.get("severity", "medium"),
                    source="Sparrow",
                    description="Detectado automáticamente por Sparrow"
                )
    except Exception as e:
        import logging
        logging.error(f"Error en Sparrow task: {e}")


async def run_hawk_task(tenant_id: str, client_id: str, client_secret: str, 
                       case_id: str, user_upn: str = None):
    """Task para ejecutar Hawk"""
    try:
        result = await forensic_tools.run_hawk(
            tenant_id, client_id, client_secret, case_id, user_upn
        )
        
        if result.get("success") and result.get("findings"):
            from api.services.dashboard_data import dashboard_data
            for item in result["findings"].get("suspicious_activities", []):
                dashboard_data.add_ioc(
                    case_id=case_id,
                    ioc_type="activity",
                    value=str(item)[:500],
                    severity="high",
                    source="Hawk",
                    description="Detectado automáticamente por Hawk"
                )
    except Exception as e:
        import logging
        logging.error(f"Error en Hawk task: {e}")


async def run_full_analysis_task(tenant_id: str, client_id: str, client_secret: str, case_id: str):
    """Task para análisis completo"""
    try:
        await forensic_tools.run_full_m365_analysis(
            tenant_id, client_id, client_secret, case_id
        )
    except Exception as e:
        import logging
        logging.error(f"Error en análisis completo: {e}")


# ==================== DEVICE CODE AUTH ====================

class DeviceCodeInitRequest(BaseModel):
    tenant_id: str

class DeviceCodePollRequest(BaseModel):
    tenant_id: str
    device_code: str

@router.post("/device-code/init")
async def init_device_code(request: DeviceCodeInitRequest):
    """Iniciar flujo de autenticación Device Code"""
    try:
        result = await multi_tenant.initiate_device_auth(request.tenant_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/device-code/poll")
async def poll_device_code(request: DeviceCodePollRequest):
    """Consultar estado del token"""
    try:
        result = await multi_tenant.poll_device_token(request.tenant_id, request.device_code)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class DeviceCodeOnboardRequest(BaseModel):
    tenant_id: str
    access_token: str
    name: Optional[str] = None

@router.post("/device-code/onboard")
async def onboard_tenant_device_code(request: DeviceCodeOnboardRequest):
    """Onboarding de tenant usando token obtenido via Device Code"""
    try:
        result = await multi_tenant.onboard_tenant_with_token(
            tenant_id=request.tenant_id,
            access_token=request.access_token,
            name=request.name
        )
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
