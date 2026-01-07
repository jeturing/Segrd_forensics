"""
MCP Kali Forensics - Tests for RBAC Module v4.4.1
Tests unitarios para Role-Based Access Control
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import Request, HTTPException
from fastapi.testclient import TestClient

# Import modules under test
from core.rbac_config import (
    Permission, Role, 
    ROLE_PERMISSIONS,
    get_route_permissions,
    check_permission,
    get_user_permissions,
    RoutePermission,
    PUBLIC_ROUTES
)


class TestPermissions:
    """Tests para el sistema de permisos"""
    
    def test_permission_enum_values(self):
        """Verificar valores de permisos"""
        assert Permission.READ.value == "mcp:read"
        assert Permission.WRITE.value == "mcp:write"
        assert Permission.RUN_TOOLS.value == "mcp:run-tools"
        assert Permission.ADMIN.value == "mcp:admin"
    
    def test_role_enum_values(self):
        """Verificar valores de roles"""
        assert Role.VIEWER.value == "viewer"
        assert Role.ANALYST.value == "analyst"
        assert Role.SENIOR_ANALYST.value == "senior_analyst"
        assert Role.ADMIN.value == "admin"
    
    def test_viewer_permissions(self):
        """Viewer solo tiene READ"""
        perms = get_user_permissions(Role.VIEWER)
        assert Permission.READ in perms
        assert Permission.WRITE not in perms
        assert Permission.RUN_TOOLS not in perms
        assert Permission.ADMIN not in perms
    
    def test_analyst_permissions(self):
        """Analyst tiene READ, WRITE, RUN_TOOLS, VIEW_LOGS"""
        perms = get_user_permissions(Role.ANALYST)
        assert Permission.READ in perms
        assert Permission.WRITE in perms
        assert Permission.RUN_TOOLS in perms
        assert Permission.VIEW_LOGS in perms
        assert Permission.ADMIN not in perms
        assert Permission.DELETE not in perms
    
    def test_senior_analyst_permissions(self):
        """Senior Analyst tiene permisos extendidos"""
        perms = get_user_permissions(Role.SENIOR_ANALYST)
        assert Permission.READ in perms
        assert Permission.WRITE in perms
        assert Permission.DELETE in perms
        assert Permission.RUN_TOOLS in perms
        assert Permission.MANAGE_AGENTS in perms
        assert Permission.EXPORT in perms
        assert Permission.ADMIN not in perms
    
    def test_admin_permissions(self):
        """Admin tiene todos los permisos"""
        perms = get_user_permissions(Role.ADMIN)
        assert Permission.ADMIN in perms
        assert Permission.READ in perms
        assert Permission.WRITE in perms
        assert Permission.DELETE in perms
        assert Permission.RUN_TOOLS in perms
        assert Permission.MANAGE_AGENTS in perms


class TestPermissionChecks:
    """Tests para verificación de permisos"""
    
    def test_check_permission_exact_match(self):
        """Usuario con permiso exacto"""
        user_perms = {Permission.READ, Permission.WRITE}
        required = {Permission.READ}
        assert check_permission(user_perms, required) is True
    
    def test_check_permission_no_match(self):
        """Usuario sin permiso requerido"""
        user_perms = {Permission.READ}
        required = {Permission.WRITE}
        assert check_permission(user_perms, required) is False
    
    def test_check_permission_admin_bypass(self):
        """Admin puede acceder a todo"""
        user_perms = {Permission.ADMIN}
        required = {Permission.RUN_TOOLS, Permission.MANAGE_AGENTS}
        assert check_permission(user_perms, required) is True
    
    def test_check_permission_partial_match(self):
        """Match parcial es suficiente (OR logic)"""
        user_perms = {Permission.READ}
        required = {Permission.READ, Permission.WRITE}
        assert check_permission(user_perms, required) is True
    
    def test_check_permission_empty_required(self):
        """Sin permisos requeridos"""
        user_perms = {Permission.READ}
        required = set()
        assert check_permission(user_perms, required) is False
    
    def test_check_permission_empty_user(self):
        """Usuario sin permisos"""
        user_perms = set()
        required = {Permission.READ}
        assert check_permission(user_perms, required) is False


class TestRoutePermissions:
    """Tests para configuración de rutas"""
    
    def test_public_routes_are_public(self):
        """Rutas públicas deben ser accesibles"""
        for public_path in PUBLIC_ROUTES:
            route = get_route_permissions(public_path, "GET")
            assert route is not None
            assert route.public is True
    
    def test_health_is_public(self):
        """Health check debe ser público"""
        route = get_route_permissions("/health", "GET")
        assert route.public is True
    
    def test_docs_is_public(self):
        """Documentación debe ser pública"""
        route = get_route_permissions("/docs", "GET")
        assert route.public is True
    
    def test_forensics_requires_auth(self):
        """Rutas forenses requieren autenticación"""
        route = get_route_permissions("/forensics/credentials", "POST")
        assert route is not None
        assert Permission.RUN_TOOLS in route.permissions
    
    def test_agents_requires_manage_agents(self):
        """Gestión de agentes requiere MANAGE_AGENTS"""
        route = get_route_permissions("/api/agents", "POST")
        assert route is not None
        assert Permission.MANAGE_AGENTS in route.permissions
    
    def test_admin_routes_require_admin(self):
        """Rutas de sistema requieren ADMIN"""
        route = get_route_permissions("/api/v41/system", "GET")
        assert route is not None
        assert Permission.ADMIN in route.permissions
    
    def test_read_vs_write_permissions(self):
        """GET y POST tienen permisos diferentes"""
        route_get = get_route_permissions("/api/iocs", "GET")
        route_post = get_route_permissions("/api/iocs", "POST")
        
        assert Permission.READ in route_get.permissions
        assert Permission.WRITE in route_post.permissions
    
    def test_rate_limit_on_execution_routes(self):
        """Rutas de ejecución tienen rate limit bajo"""
        route = get_route_permissions("/hunting/execute", "POST")
        assert route.rate_limit <= 30


class TestRoutePermissionModel:
    """Tests para el modelo RoutePermission"""
    
    def test_route_permission_creation(self):
        """Crear RoutePermission"""
        route = RoutePermission(
            path_prefix="/test",
            method="POST",
            permissions={Permission.WRITE}
        )
        
        assert route.path_prefix == "/test"
        assert route.method == "POST"
        assert Permission.WRITE in route.permissions
        assert route.public is False
        assert route.rate_limit == 100
    
    def test_route_permission_requires(self):
        """Método requires funciona correctamente"""
        route = RoutePermission(
            path_prefix="/test",
            permissions={Permission.READ, Permission.WRITE}
        )
        
        assert route.requires(Permission.READ) is True
        assert route.requires(Permission.WRITE) is True
        assert route.requires(Permission.ADMIN) is False
    
    def test_route_permission_public(self):
        """Rutas públicas"""
        route = RoutePermission(
            path_prefix="/public",
            public=True
        )
        
        assert route.public is True
        assert len(route.permissions) == 0


class TestRolePermissionMapping:
    """Tests para mapeo de roles a permisos"""
    
    def test_role_permissions_complete(self):
        """Todos los roles tienen mapeo"""
        for role in Role:
            assert role in ROLE_PERMISSIONS
    
    def test_role_hierarchy(self):
        """Roles superiores tienen más permisos"""
        viewer_perms = len(ROLE_PERMISSIONS[Role.VIEWER])
        analyst_perms = len(ROLE_PERMISSIONS[Role.ANALYST])
        senior_perms = len(ROLE_PERMISSIONS[Role.SENIOR_ANALYST])
        admin_perms = len(ROLE_PERMISSIONS[Role.ADMIN])
        
        assert viewer_perms < analyst_perms
        assert analyst_perms < senior_perms
        assert senior_perms <= admin_perms
    
    def test_viewer_is_subset_of_analyst(self):
        """Viewer permisos son subset de Analyst"""
        viewer_perms = ROLE_PERMISSIONS[Role.VIEWER]
        analyst_perms = ROLE_PERMISSIONS[Role.ANALYST]
        
        assert viewer_perms.issubset(analyst_perms)


# =============================================================================
# INTEGRATION TESTS (requieren app running)
# =============================================================================

class TestRBACMiddlewareIntegration:
    """Tests de integración para middleware RBAC"""
    
    @pytest.fixture
    def mock_request(self):
        """Request mock para testing"""
        request = Mock(spec=Request)
        request.url.path = "/api/test"
        request.method = "GET"
        request.headers = {}
        request.cookies = {}
        request.client.host = "127.0.0.1"
        request.state = Mock()
        return request
    
    @pytest.mark.asyncio
    async def test_public_route_no_auth_required(self, mock_request):
        """Rutas públicas no requieren autenticación"""
        mock_request.url.path = "/health"
        
        # Should not raise
        route = get_route_permissions("/health", "GET")
        assert route.public is True
    
    @pytest.mark.asyncio
    async def test_protected_route_requires_auth(self, mock_request):
        """Rutas protegidas requieren autenticación"""
        mock_request.url.path = "/forensics/credentials"
        mock_request.method = "POST"
        
        route = get_route_permissions("/forensics/credentials", "POST")
        assert route is not None
        assert not route.public
        assert len(route.permissions) > 0


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
