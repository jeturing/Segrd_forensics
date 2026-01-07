"""
Middleware de autenticación y autorización v4.6
===============================================
Incluye:
- Verificación de API Key
- Autenticación de usuario (JWT)
- Verificación de Global Admin
- Verificación de permisos granulares
"""

from typing import Optional, List
from fastapi import Security, HTTPException, status, Depends, Request
from fastapi.security.api_key import APIKeyHeader
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from datetime import datetime
import logging

from api.config import get_settings
from core.rbac_config import Permission

logger = logging.getLogger(__name__)
settings = get_settings()

# Security schemes
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)):
    """
    Verifica la API key en el header X-API-Key
    """
    if not api_key or api_key != settings.API_KEY:
        logger.warning("❌ Intento de acceso con API key inválida")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key"
        )
    return api_key


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    api_key: Optional[str] = Security(api_key_header)
) -> dict:
    """
    Obtener usuario actual desde JWT o API Key.
    
    Returns:
        dict con: user_id, email, tenant_id, is_global_admin
    """
    # Intentar con Bearer token primero
    if credentials and credentials.credentials:
        try:
            payload = jwt.decode(
                credentials.credentials,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            
            # Verificar expiración
            exp = payload.get('exp')
            if exp and datetime.utcnow().timestamp() > exp:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token expirado"
                )
            
            return {
                "user_id": payload.get('sub') or payload.get('user_id'),
                "email": payload.get('email'),
                "tenant_id": payload.get('tenant_id'),
                "is_global_admin": payload.get('is_global_admin', False)
            }
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expirado"
            )
        except jwt.InvalidTokenError as e:
            logger.warning(f"⚠️ Token JWT inválido: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido"
            )
    
    # Fallback a API Key (para servicios internos)
    if api_key and api_key == settings.API_KEY:
        # API Key válida = acceso de servicio interno
        return {
            "user_id": "system",
            "email": "system@internal",
            "tenant_id": None,
            "is_global_admin": True  # API Key tiene acceso completo
        }
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Autenticación requerida"
    )


async def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    api_key: Optional[str] = Security(api_key_header)
) -> Optional[dict]:
    """
    Obtener usuario si está autenticado, None si no.
    Para endpoints que pueden funcionar sin auth.
    """
    try:
        return await get_current_user(request, credentials, api_key)
    except HTTPException:
        return None


async def require_global_admin(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Verificar que el usuario es Global Admin.
    Usar como dependencia en rutas exclusivas de admin global.
    
    Ejemplo:
        @router.get("/admin-only", dependencies=[Depends(require_global_admin)])
    """
    if not current_user.get('is_global_admin'):
        logger.warning(f"⚠️ Acceso denegado a Global Admin: {current_user.get('email')}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso restringido a Global Admin"
        )
    
    return current_user


def require_permission(permission: str):
    """
    Factory para crear dependencia de verificación de permiso.
    
    Uso:
        @router.get("/endpoint", dependencies=[Depends(require_permission("cases:read"))])
    """
    async def permission_checker(
        current_user: dict = Depends(get_current_user)
    ) -> dict:
        # Global admin tiene todos los permisos
        if current_user.get('is_global_admin'):
            return current_user
        
        # Importar aquí para evitar circular import
        from api.services import roles_service
        
        has_perm = await roles_service.validate_permission(
            user_id=current_user['user_id'],
            permission=permission,
            tenant_id=current_user.get('tenant_id')
        )
        
        if not has_perm:
            logger.warning(
                f"⚠️ Permiso denegado: {current_user.get('email')} -> {permission}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permiso requerido: {permission}"
            )
        
        return current_user
    
    return permission_checker


def require_any_permission(permissions: List[str]):
    """
    Factory para verificar que el usuario tiene AL MENOS UNO de los permisos.
    
    Uso:
        @router.get("/endpoint", dependencies=[Depends(require_any_permission(["cases:read", "audit:read"]))])
    """
    async def permission_checker(
        current_user: dict = Depends(get_current_user)
    ) -> dict:
        if current_user.get('is_global_admin'):
            return current_user
        
        from api.services import roles_service
        
        has_any = await roles_service.check_multiple_permissions(
            user_id=current_user['user_id'],
            required_permissions=permissions,
            tenant_id=current_user.get('tenant_id'),
            require_all=False
        )
        
        if not has_any:
            logger.warning(
                f"⚠️ Permisos denegados: {current_user.get('email')} -> {permissions}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Se requiere uno de: {', '.join(permissions)}"
            )
        
        return current_user
    
    return permission_checker


def require_all_permissions(permissions: List[str]):
    """
    Factory para verificar que el usuario tiene TODOS los permisos.
    
    Uso:
        @router.get("/endpoint", dependencies=[Depends(require_all_permissions(["cases:read", "cases:write"]))])
    """
    async def permission_checker(
        current_user: dict = Depends(get_current_user)
    ) -> dict:
        if current_user.get('is_global_admin'):
            return current_user
        
        from api.services import roles_service
        
        has_all = await roles_service.check_multiple_permissions(
            user_id=current_user['user_id'],
            required_permissions=permissions,
            tenant_id=current_user.get('tenant_id'),
            require_all=True
        )
        
        if not has_all:
            logger.warning(
                f"⚠️ Permisos insuficientes: {current_user.get('email')} -> {permissions}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Se requieren todos: {', '.join(permissions)}"
            )
        
        return current_user
    
    return permission_checker


async def require_tenant_admin(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Verificar que el usuario es Tenant Admin (o Global Admin).
    """
    if current_user.get('is_global_admin'):
        return current_user
    
    from api.services import roles_service
    from core.rbac_config import Role
    
    user_roles = await roles_service.get_user_roles(
        current_user['user_id'], 
        current_user.get('tenant_id')
    )
    
    role_names = [r['name'] for r in user_roles]
    
    if Role.TENANT_ADMIN.value not in role_names:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso restringido a Tenant Admin"
        )
    
    return current_user
