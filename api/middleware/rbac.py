"""
MCP Kali Forensics - RBAC Middleware v4.4.1
Middleware de Role-Based Access Control

Implementa verificación de permisos granular por ruta y método HTTP.
"""

import time
import logging
from typing import Optional, Set, Dict, Any
from collections import defaultdict

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from core.rbac_config import (
    Permission, 
    Role, 
    get_route_permissions, 
    check_permission,
    get_user_permissions,
    PUBLIC_ROUTES
)
from api.config import settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter simple en memoria"""
    
    def __init__(self):
        self.requests: Dict[str, list] = defaultdict(list)
        self.cleanup_interval = 60  # segundos
        self.last_cleanup = time.time()
    
    def is_allowed(self, key: str, limit: int, window: int = 60) -> bool:
        """
        Verificar si la request está permitida
        
        Args:
            key: Identificador único (IP + path)
            limit: Número máximo de requests
            window: Ventana de tiempo en segundos
        
        Returns:
            True si está permitido
        """
        now = time.time()
        
        # Limpiar requests antiguas periódicamente
        if now - self.last_cleanup > self.cleanup_interval:
            self._cleanup(now, window)
        
        # Filtrar requests dentro de la ventana
        self.requests[key] = [
            t for t in self.requests[key] 
            if now - t < window
        ]
        
        if len(self.requests[key]) >= limit:
            return False
        
        self.requests[key].append(now)
        return True
    
    def _cleanup(self, now: float, window: int):
        """Limpiar entradas antiguas"""
        for key in list(self.requests.keys()):
            self.requests[key] = [
                t for t in self.requests[key] 
                if now - t < window
            ]
            if not self.requests[key]:
                del self.requests[key]
        self.last_cleanup = now


# Instancia global del rate limiter
rate_limiter = RateLimiter()


class RBACMiddleware(BaseHTTPMiddleware):
    """
    Middleware de RBAC para verificación de permisos
    
    Características:
    - Verificación de permisos por ruta y método
    - Rate limiting por endpoint
    - Logging de accesos
    - Soporte para rutas públicas
    """
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method
        
        # Permitir solicitudes OPTIONS (CORS preflight) sin autenticación
        if method == "OPTIONS":
            return await call_next(request)

        # Bypass explícito para pricing público (landing/calculadora)
        if path.startswith("/api/pricing"):
            logger.info(f"🔓 RBAC Public pricing route: {path}")
            return await call_next(request)
        
        # Bypass explícito para agentes remotos (descarga de script y WebSocket)
        # Necesario para permitir que endpoints remotos sin credenciales se conecten usando token
        if path.startswith("/api/remote-agents/download") or path.startswith("/api/remote-agents/ws") or path.startswith("/api/remote-agents/status"):
            logger.info(f"🔓 RBAC Bypass for remote agent: {path}")
            return await call_next(request)
        
        # Permitir rutas públicas
        for public_path in PUBLIC_ROUTES:
            if path.startswith(public_path):
                logger.info(f"🔓 RBAC Public route: {path} (matched {public_path})")
                return await call_next(request)
        
        # Obtener configuración de permisos para la ruta
        route_config = get_route_permissions(path, method)
        
        # Si no hay configuración, aplicar política por defecto
        if route_config is None:
            # Por defecto, requerir al menos READ
            route_config = type('DefaultRoute', (), {
                'permissions': {Permission.READ},
                'public': False,
                'rate_limit': 100
            })()
        
        # Verificar si es ruta pública
        if getattr(route_config, 'public', False):
            return await call_next(request)
        
        # Obtener usuario y sus permisos
        try:
            user_info = await self._get_user_info(request)
            user_permissions = user_info.get('permissions', set())
            user_id = user_info.get('user_id', 'anonymous')
        except HTTPException as e:
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail}
            )
        
        # Rate limiting
        rate_key = f"{request.client.host}:{path}:{method}"
        if not rate_limiter.is_allowed(rate_key, route_config.rate_limit):
            logger.warning(
                f"⚠️ Rate limit exceeded: {rate_key} "
                f"(limit: {route_config.rate_limit}/min)"
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after": 60
                }
            )
        
        # Verificar permisos
        required_permissions = route_config.permissions
        if not check_permission(user_permissions, required_permissions):
            logger.warning(
                f"🚫 Access denied: user={user_id}, path={path}, "
                f"method={method}, required={required_permissions}, "
                f"has={user_permissions}"
            )
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "detail": "Insufficient permissions",
                    "required": [p.value for p in required_permissions],
                    "path": path
                }
            )
        
        # Logging de acceso exitoso
        logger.debug(
            f"✅ Access granted: user={user_id}, path={path}, method={method}"
        )
        
        # Agregar info del usuario al request state
        request.state.user_id = user_id
        request.state.user_permissions = user_permissions
        
        return await call_next(request)
    
    async def _get_user_info(self, request: Request) -> Dict[str, Any]:
        """
        Obtener información del usuario desde el request
        
        Soporta múltiples métodos de autenticación:
        1. API Key (X-API-Key header)
        2. Bearer Token (Authorization header)
        3. Session Cookie
        """
        # 1. Verificar API Key
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return await self._validate_api_key(api_key)
        
        # 2. Verificar Bearer Token
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            return await self._validate_bearer_token(token)
        
        # 3. Verificar Session Cookie
        session_id = request.cookies.get("session_id")
        if session_id:
            return await self._validate_session(session_id)
        
        # Sin autenticación
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    async def _validate_api_key(self, api_key: str) -> Dict[str, Any]:
        """Validar API Key y retornar info del usuario"""
        # API Key maestra = Admin
        if api_key == settings.API_KEY:
            return {
                "user_id": "api_key_admin",
                "role": Role.ADMIN,
                "permissions": get_user_permissions(Role.ADMIN)
            }
        
        # TODO: Implementar lookup de API keys en base de datos
        # Por ahora, keys que empiezan con "analyst_" tienen rol analyst
        if api_key.startswith("analyst_"):
            return {
                "user_id": f"api_key_{api_key[:16]}",
                "role": Role.ANALYST,
                "permissions": get_user_permissions(Role.ANALYST)
            }
        
        if api_key.startswith("viewer_"):
            return {
                "user_id": f"api_key_{api_key[:16]}",
                "role": Role.VIEWER,
                "permissions": get_user_permissions(Role.VIEWER)
            }
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key"
        )
    
    async def _validate_bearer_token(self, token: str) -> Dict[str, Any]:
        """Validar Bearer Token (JWT) y extraer permisos del usuario"""
        import jwt
        from api.config import settings
        
        try:
            # Decodificar JWT (usando PyJWT que es compatible con Python 3.13)
            payload = jwt.decode(
                token, 
                settings.JWT_SECRET_KEY, 
                algorithms=[settings.JWT_ALGORITHM]
            )
            
            user_id = payload.get("sub")
            username = payload.get("username", "unknown")
            is_global_admin = payload.get("is_global_admin", False)
            roles_from_token = payload.get("roles", [])
            permissions_from_token = payload.get("permissions", [])
            
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: missing user ID"
                )
            
            # Si es Global Admin, tiene TODOS los permisos
            if is_global_admin:
                logger.info(f"👑 Global Admin access: {username}")
                return {
                    "user_id": user_id,
                    "username": username,
                    "role": Role.GLOBAL_ADMIN,
                    "permissions": get_user_permissions(Role.GLOBAL_ADMIN),
                    "is_global_admin": True
                }
            
            # Construir permisos desde roles
            user_permissions = set()
            
            for role_name in roles_from_token:
                try:
                    role = Role(role_name)
                    user_permissions.update(get_user_permissions(role))
                except ValueError:
                    logger.warning(f"Unknown role in token: {role_name}")
            
            # Agregar permisos directos del token
            for perm_name in permissions_from_token:
                try:
                    user_permissions.add(Permission(perm_name))
                except ValueError:
                    pass  # Ignorar permisos desconocidos
            
            # Si no hay roles ni permisos, dar al menos READ
            if not user_permissions:
                user_permissions = {Permission.READ}
            
            # Determinar rol principal
            primary_role = Role.VIEWER
            if roles_from_token:
                try:
                    primary_role = Role(roles_from_token[0])
                except ValueError:
                    pass
            
            return {
                "user_id": user_id,
                "username": username,
                "role": primary_role,
                "permissions": user_permissions,
                "is_global_admin": False
            }
            
        except jwt.PyJWTError as e:
            logger.warning(f"⚠️ JWT validation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid or expired token"
            )
    
    async def _validate_session(self, session_id: str) -> Dict[str, Any]:
        """Validar Session Cookie"""
        # TODO: Implementar validación de sesión
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session validation not implemented"
        )


def require_permissions(*permissions: Permission):
    """
    Decorator para requerir permisos específicos en una ruta
    
    Uso:
        @router.get("/admin-only")
        @require_permissions(Permission.ADMIN)
        async def admin_endpoint():
            ...
    """
    from functools import wraps
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Obtener request del contexto
            request = kwargs.get('request')
            if not request:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            
            if not request:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Request not found in handler"
                )
            
            user_permissions = getattr(request.state, 'user_permissions', set())
            required = set(permissions)
            
            if not check_permission(user_permissions, required):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Requires permissions: {[p.value for p in required]}"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def get_current_user_permissions(request: Request) -> Set[Permission]:
    """Helper para obtener permisos del usuario actual"""
    return getattr(request.state, 'user_permissions', set())


def get_current_user_id(request: Request) -> Optional[str]:
    """Helper para obtener ID del usuario actual"""
    return getattr(request.state, 'user_id', None)
