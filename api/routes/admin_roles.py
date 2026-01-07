"""
Admin Roles Routes v4.6
=======================
Endpoints para gestión de roles por Tenant Admin.
Permite crear roles custom, asignar permisos, gestionar usuarios.

Permisos requeridos: tenant:roles, tenant:users
Accesible por: TENANT_ADMIN o usuarios con permiso tenant:roles
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query, Path
from pydantic import BaseModel, Field

from api.middleware.auth import get_current_user, require_permission
from api.services import roles_service
from core.rbac_config import Role, Permission

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/admin/roles",
    tags=["Role Management"]
)


# ============================================================================
# SCHEMAS
# ============================================================================

class CreateCustomRoleRequest(BaseModel):
    """Crear un rol personalizado."""
    name: str = Field(..., min_length=3, max_length=50, pattern="^[a-z][a-z0-9_]*$")
    display_name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    permissions: List[str] = Field(..., min_items=1)


class UpdateCustomRoleRequest(BaseModel):
    """Actualizar un rol personalizado."""
    display_name: Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    permissions: Optional[List[str]] = None


class AssignRoleRequest(BaseModel):
    """Asignar rol a usuario."""
    user_id: str
    role_name: str


class BulkAssignRolesRequest(BaseModel):
    """Asignar múltiples roles a múltiples usuarios."""
    assignments: List[AssignRoleRequest]


class RoleResponse(BaseModel):
    """Respuesta con información de rol."""
    id: int
    name: str
    display_name: str
    description: Optional[str] = None
    is_system_role: bool
    permissions: List[str] = []
    users_count: int = 0


# ============================================================================
# ROLE LISTING
# ============================================================================

@router.get("", response_model=List[RoleResponse])
async def list_tenant_roles(
    include_system: bool = Query(True, description="Incluir roles de sistema"),
    current_user: dict = Depends(get_current_user)
):
    """
    📋 Listar todos los roles disponibles para el tenant.
    Incluye roles de sistema y roles custom del tenant.
    """
    tenant_id = current_user.get('tenant_id')
    
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant no identificado")
    
    # Verificar permiso
    has_perm = await roles_service.validate_permission(
        current_user['user_id'], 
        Permission.TENANT_ROLES.value, 
        tenant_id
    )
    
    if not has_perm:
        raise HTTPException(status_code=403, detail="Permiso denegado: tenant:roles")
    
    roles = await roles_service.get_tenant_roles(tenant_id)
    
    if not include_system:
        roles = [r for r in roles if not r.get('is_system_role')]
    
    return roles


@router.get("/{role_name}")
async def get_role_details(
    role_name: str = Path(..., description="Nombre del rol"),
    current_user: dict = Depends(get_current_user)
):
    """
    🔍 Obtener detalles de un rol específico.
    """
    tenant_id = current_user.get('tenant_id')
    
    role = await roles_service.get_role_by_name(role_name)
    
    if not role:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    
    # Si es rol custom, verificar que pertenece al tenant
    if not role.get('is_system_role') and role.get('tenant_id') != tenant_id:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    
    return role


# ============================================================================
# CUSTOM ROLE MANAGEMENT
# ============================================================================

@router.post("", status_code=201)
async def create_custom_role(
    request: CreateCustomRoleRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    ➕ Crear un nuevo rol personalizado para el tenant.
    
    Restricciones:
    - Nombre debe ser snake_case único
    - Solo permisos válidos pueden asignarse
    - No puede duplicar nombres de roles de sistema
    """
    tenant_id = current_user.get('tenant_id')
    user_id = current_user['user_id']
    
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant no identificado")
    
    # Verificar permiso
    has_perm = await roles_service.validate_permission(
        user_id, 
        Permission.TENANT_ROLES.value, 
        tenant_id
    )
    
    if not has_perm:
        raise HTTPException(status_code=403, detail="Permiso denegado: tenant:roles")
    
    # No permitir crear roles con nombres de sistema
    system_role_names = [r.value for r in Role]
    if request.name in system_role_names:
        raise HTTPException(
            status_code=400, 
            detail=f"No se puede usar nombre de rol de sistema: {request.name}"
        )
    
    result = await roles_service.create_custom_role(
        tenant_id=tenant_id,
        role_name=request.name,
        display_name=request.display_name,
        description=request.description or "",
        permissions=request.permissions,
        created_by=user_id
    )
    
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    
    logger.info(f"✅ Rol custom creado: {request.name} en tenant {tenant_id}")
    
    return {
        "success": True,
        "role": result['role']
    }


@router.put("/{role_id}")
async def update_custom_role(
    role_id: int = Path(..., description="ID del rol"),
    request: UpdateCustomRoleRequest = ...,
    current_user: dict = Depends(get_current_user)
):
    """
    ✏️ Actualizar un rol personalizado.
    Solo roles custom del tenant pueden ser modificados.
    """
    tenant_id = current_user.get('tenant_id')
    
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant no identificado")
    
    # Verificar permiso
    has_perm = await roles_service.validate_permission(
        current_user['user_id'], 
        Permission.TENANT_ROLES.value, 
        tenant_id
    )
    
    if not has_perm:
        raise HTTPException(status_code=403, detail="Permiso denegado: tenant:roles")
    
    updates = request.dict(exclude_unset=True)
    
    if not updates:
        raise HTTPException(status_code=400, detail="No hay campos para actualizar")
    
    result = await roles_service.update_custom_role(
        role_id=role_id,
        tenant_id=tenant_id,
        updates=updates
    )
    
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    
    return {
        "success": True,
        "message": "Rol actualizado"
    }


@router.delete("/{role_id}")
async def delete_custom_role(
    role_id: int = Path(..., description="ID del rol"),
    current_user: dict = Depends(get_current_user)
):
    """
    🗑️ Eliminar un rol personalizado.
    El rol no debe tener usuarios asignados.
    """
    tenant_id = current_user.get('tenant_id')
    
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant no identificado")
    
    # Verificar permiso
    has_perm = await roles_service.validate_permission(
        current_user['user_id'], 
        Permission.TENANT_ROLES.value, 
        tenant_id
    )
    
    if not has_perm:
        raise HTTPException(status_code=403, detail="Permiso denegado: tenant:roles")
    
    result = await roles_service.delete_custom_role(role_id, tenant_id)
    
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    
    return {
        "success": True,
        "message": result['message']
    }


# ============================================================================
# USER ROLE ASSIGNMENT
# ============================================================================

@router.post("/assign")
async def assign_role_to_user(
    request: AssignRoleRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    👤 Asignar un rol a un usuario.
    
    El usuario que asigna debe tener permiso tenant:roles.
    No se puede asignar GLOBAL_ADMIN mediante este endpoint.
    """
    tenant_id = current_user.get('tenant_id')
    user_id = current_user['user_id']
    
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant no identificado")
    
    # Verificar permiso
    has_perm = await roles_service.validate_permission(
        user_id, 
        Permission.TENANT_ROLES.value, 
        tenant_id
    )
    
    if not has_perm:
        raise HTTPException(status_code=403, detail="Permiso denegado: tenant:roles")
    
    result = await roles_service.assign_role_to_user(
        user_id=request.user_id,
        role_name=request.role_name,
        tenant_id=tenant_id,
        assigned_by=user_id
    )
    
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    
    logger.info(f"✅ Rol {request.role_name} asignado a {request.user_id}")
    
    return result


@router.post("/assign/bulk")
async def bulk_assign_roles(
    request: BulkAssignRolesRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    👥 Asignar múltiples roles a múltiples usuarios.
    Útil para configuración inicial de equipos.
    """
    tenant_id = current_user.get('tenant_id')
    user_id = current_user['user_id']
    
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant no identificado")
    
    # Verificar permiso
    has_perm = await roles_service.validate_permission(
        user_id, 
        Permission.TENANT_ROLES.value, 
        tenant_id
    )
    
    if not has_perm:
        raise HTTPException(status_code=403, detail="Permiso denegado: tenant:roles")
    
    results = []
    for assignment in request.assignments:
        result = await roles_service.assign_role_to_user(
            user_id=assignment.user_id,
            role_name=assignment.role_name,
            tenant_id=tenant_id,
            assigned_by=user_id
        )
        results.append({
            "user_id": assignment.user_id,
            "role_name": assignment.role_name,
            **result
        })
    
    successful = sum(1 for r in results if r['success'])
    
    return {
        "total": len(results),
        "successful": successful,
        "failed": len(results) - successful,
        "details": results
    }


@router.delete("/assign")
async def remove_role_from_user(
    request: AssignRoleRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    ❌ Remover un rol de un usuario.
    """
    tenant_id = current_user.get('tenant_id')
    
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant no identificado")
    
    # Verificar permiso
    has_perm = await roles_service.validate_permission(
        current_user['user_id'], 
        Permission.TENANT_ROLES.value, 
        tenant_id
    )
    
    if not has_perm:
        raise HTTPException(status_code=403, detail="Permiso denegado: tenant:roles")
    
    result = await roles_service.remove_role_from_user(
        user_id=request.user_id,
        role_name=request.role_name,
        tenant_id=tenant_id
    )
    
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    
    return result


# ============================================================================
# USER ROLES QUERY
# ============================================================================

@router.get("/users/{user_id}")
async def get_user_roles(
    user_id: str = Path(..., description="ID del usuario"),
    current_user: dict = Depends(get_current_user)
):
    """
    👤 Obtener todos los roles de un usuario.
    """
    tenant_id = current_user.get('tenant_id')
    
    if not tenant_id:
        raise HTTPException(status_code=400, detail="Tenant no identificado")
    
    # Verificar permiso (tenant:users o tenant:roles)
    has_perm = await roles_service.check_multiple_permissions(
        current_user['user_id'],
        [Permission.TENANT_USERS.value, Permission.TENANT_ROLES.value],
        tenant_id,
        require_all=False
    )
    
    if not has_perm:
        raise HTTPException(status_code=403, detail="Permiso denegado")
    
    roles = await roles_service.get_user_roles(user_id, tenant_id)
    permissions = await roles_service.get_user_permissions(user_id, tenant_id)
    
    return {
        "user_id": user_id,
        "roles": roles,
        "permissions": list(permissions)
    }


@router.get("/permissions/list")
async def list_available_permissions(
    current_user: dict = Depends(get_current_user)
):
    """
    🔐 Listar todos los permisos disponibles para asignar.
    Agrupados por categoría.
    """
    permissions = await roles_service.get_all_permissions()
    
    return {
        "permissions": permissions
    }


# ============================================================================
# TEAM SHORTCUTS
# ============================================================================

@router.post("/teams/red-team")
async def setup_red_team_user(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    🔴 Configurar rápidamente un usuario como Red Team.
    Asigna rol RED_TEAM con permisos de pentesting.
    """
    tenant_id = current_user.get('tenant_id')
    
    result = await roles_service.assign_role_to_user(
        user_id=user_id,
        role_name=Role.RED_TEAM.value,
        tenant_id=tenant_id,
        assigned_by=current_user['user_id']
    )
    
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    
    return {
        "success": True,
        "message": f"Usuario configurado como Red Team",
        "role": Role.RED_TEAM.value
    }


@router.post("/teams/blue-team")
async def setup_blue_team_user(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    🔵 Configurar rápidamente un usuario como Blue Team.
    Asigna rol BLUE_TEAM con permisos de forensics/DFIR.
    """
    tenant_id = current_user.get('tenant_id')
    
    result = await roles_service.assign_role_to_user(
        user_id=user_id,
        role_name=Role.BLUE_TEAM.value,
        tenant_id=tenant_id,
        assigned_by=current_user['user_id']
    )
    
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    
    return {
        "success": True,
        "message": f"Usuario configurado como Blue Team",
        "role": Role.BLUE_TEAM.value
    }


@router.post("/teams/purple-team")
async def setup_purple_team_user(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    🟣 Configurar rápidamente un usuario como Purple Team.
    Asigna rol PURPLE_TEAM con permisos combinados Red+Blue.
    """
    tenant_id = current_user.get('tenant_id')
    
    result = await roles_service.assign_role_to_user(
        user_id=user_id,
        role_name=Role.PURPLE_TEAM.value,
        tenant_id=tenant_id,
        assigned_by=current_user['user_id']
    )
    
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    
    return {
        "success": True,
        "message": f"Usuario configurado como Purple Team",
        "role": Role.PURPLE_TEAM.value
    }


@router.post("/teams/auditor")
async def setup_auditor_user(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    📊 Configurar rápidamente un usuario como Auditor.
    Asigna rol AUDIT con permisos de solo lectura.
    """
    tenant_id = current_user.get('tenant_id')
    
    result = await roles_service.assign_role_to_user(
        user_id=user_id,
        role_name=Role.AUDIT.value,
        tenant_id=tenant_id,
        assigned_by=current_user['user_id']
    )
    
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    
    return {
        "success": True,
        "message": f"Usuario configurado como Auditor",
        "role": Role.AUDIT.value
    }
