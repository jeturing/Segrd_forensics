"""
MCP Kali Forensics - RBAC Configuration v4.6
Sistema de Control de Acceso Basado en Roles (RBAC) Jerárquico

JERARQUÍA DE ROLES:
───────────────────
Nivel 0  - GLOBAL_ADMIN   → Acceso total a la plataforma (Pluton_JE)
Nivel 10 - TENANT_ADMIN   → Administrador del tenant (creado en onboarding)
Nivel 20 - PURPLE_TEAM    → Combinación Red + Blue Team
Nivel 30 - RED_TEAM       → Herramientas ofensivas/pentesting
Nivel 30 - BLUE_TEAM      → Herramientas defensivas/forenses
Nivel 40 - CUSTOM         → Rol con permisos configurables por admin
Nivel 50 - AUDIT          → Solo lectura (auditoría)

CATEGORÍAS DE PERMISOS:
───────────────────────
- platform: Gestión de plataforma (solo Global Admin)
- tenant: Gestión de tenant
- users: Gestión de usuarios
- roles: Gestión de roles
- cases: Gestión de casos
- tools: Herramientas forenses y de seguridad
- agents: Agentes LLM
- audit: Logs de auditoría
- reports: Generación de reportes
- billing: Facturación
"""

from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field
from enum import Enum


class Permission(str, Enum):
    """Permisos granulares del sistema v4.6"""
    
    # === LEGACY (compatibilidad hacia atrás) ===
    READ = "mcp:read"
    WRITE = "mcp:write"
    DELETE = "mcp:delete"
    RUN_TOOLS = "mcp:run-tools"
    MANAGE_AGENTS = "mcp:manage-agents"
    ADMIN = "mcp:admin"
    VIEW_LOGS = "mcp:view-logs"
    EXPORT = "mcp:export"
    PENTEST = "mcp:pentest"
    
    # === PLATAFORMA (Global Admin) ===
    PLATFORM_MANAGE = "platform:manage"
    PLATFORM_VIEW_ALL_TENANTS = "platform:view-all-tenants"
    PLATFORM_MANAGE_PLANS = "platform:manage-plans"
    PLATFORM_VIEW_METRICS = "platform:view-metrics"
    PLATFORM_IMPERSONATE = "platform:impersonate"
    
    # === TENANT ===
    TENANT_MANAGE = "tenant:manage"
    TENANT_VIEW = "tenant:view"
    TENANT_BILLING = "tenant:billing"
    TENANT_INTEGRATIONS = "tenant:integrations"
    
    # === USUARIOS ===
    USERS_MANAGE = "users:manage"
    USERS_VIEW = "users:view"
    USERS_INVITE = "users:invite"
    USERS_DEACTIVATE = "users:deactivate"
    
    # === ROLES ===
    ROLES_MANAGE = "roles:manage"
    ROLES_ASSIGN = "roles:assign"
    ROLES_VIEW = "roles:view"
    
    # === CASOS ===
    CASES_READ = "cases:read"
    CASES_WRITE = "cases:write"
    CASES_DELETE = "cases:delete"
    CASES_ASSIGN = "cases:assign"
    CASES_CLOSE = "cases:close"
    
    # === HERRAMIENTAS M365 ===
    TOOLS_M365 = "tools:m365"
    TOOLS_M365_SPARROW = "tools:m365-sparrow"
    TOOLS_M365_HAWK = "tools:m365-hawk"
    TOOLS_M365_EXTRACTOR = "tools:m365-extractor"
    
    # === HERRAMIENTAS ENDPOINT ===
    TOOLS_ENDPOINT = "tools:endpoint"
    TOOLS_ENDPOINT_LOKI = "tools:endpoint-loki"
    TOOLS_ENDPOINT_YARA = "tools:endpoint-yara"
    TOOLS_ENDPOINT_OSQUERY = "tools:endpoint-osquery"
    TOOLS_ENDPOINT_VOLATILITY = "tools:endpoint-volatility"
    
    # === HERRAMIENTAS CREDENCIALES ===
    TOOLS_CREDENTIALS = "tools:credentials"
    TOOLS_CREDENTIALS_HIBP = "tools:credentials-hibp"
    TOOLS_CREDENTIALS_DEHASHED = "tools:credentials-dehashed"
    
    # === HERRAMIENTAS RED TEAM ===
    TOOLS_PENTEST = "tools:pentest"
    TOOLS_REDTEAM = "tools:redteam"
    TOOLS_REDTEAM_HEXSTRIKE = "tools:redteam-hexstrike"
    TOOLS_REDTEAM_C2 = "tools:redteam-c2"
    
    # === AGENTES LLM ===
    AGENTS_MANAGE = "agents:manage"
    AGENTS_VIEW = "agents:view"
    AGENTS_QUERY = "agents:query"
    AGENTS_CONFIGURE = "agents:configure"
    
    # === AUDITORÍA ===
    AUDIT_READ = "audit:read"
    AUDIT_EXPORT = "audit:export"
    AUDIT_SEARCH = "audit:search"
    
    # === REPORTES ===
    REPORTS_GENERATE = "reports:generate"
    REPORTS_VIEW = "reports:view"
    REPORTS_EXPORT = "reports:export"
    REPORTS_SCHEDULE = "reports:schedule"
    
    # === FACTURACIÓN ===
    BILLING_VIEW = "billing:view"
    BILLING_MANAGE_PAYMENT = "billing:manage-payment"
    BILLING_DOWNLOAD_INVOICES = "billing:download-invoices"


class Role(str, Enum):
    """Roles del sistema v4.6 con jerarquía"""
    
    # Roles legacy (compatibilidad)
    VIEWER = "viewer"
    ANALYST = "analyst"
    SENIOR_ANALYST = "senior_analyst"
    ADMIN = "admin"
    
    # Nuevos roles v4.6
    GLOBAL_ADMIN = "global_admin"
    TENANT_ADMIN = "tenant_admin"
    AUDIT = "audit"
    RED_TEAM = "red_team"
    BLUE_TEAM = "blue_team"
    PURPLE_TEAM = "purple_team"
    CUSTOM = "custom"


# Niveles de jerarquía (menor = más privilegios)
ROLE_HIERARCHY: Dict[Role, int] = {
    Role.GLOBAL_ADMIN: 0,
    Role.TENANT_ADMIN: 10,
    Role.PURPLE_TEAM: 20,
    Role.RED_TEAM: 30,
    Role.BLUE_TEAM: 30,
    Role.CUSTOM: 40,
    Role.AUDIT: 50,
    # Legacy roles
    Role.ADMIN: 10,
    Role.SENIOR_ANALYST: 25,
    Role.ANALYST: 35,
    Role.VIEWER: 50,
}


# Permisos por rol (incluye legacy + nuevos)
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    # === LEGACY ROLES (compatibilidad) ===
    Role.VIEWER: {
        Permission.READ,
        Permission.CASES_READ,
        Permission.AUDIT_READ,
        Permission.REPORTS_VIEW,
    },
    
    Role.ANALYST: {
        Permission.READ,
        Permission.WRITE,
        Permission.RUN_TOOLS,
        Permission.VIEW_LOGS,
        Permission.CASES_READ,
        Permission.CASES_WRITE,
        Permission.TOOLS_M365,
        Permission.TOOLS_ENDPOINT,
        Permission.TOOLS_CREDENTIALS,
        Permission.AGENTS_VIEW,
        Permission.AGENTS_QUERY,
        Permission.REPORTS_VIEW,
        Permission.REPORTS_GENERATE,
    },
    
    Role.SENIOR_ANALYST: {
        Permission.READ,
        Permission.WRITE,
        Permission.DELETE,
        Permission.RUN_TOOLS,
        Permission.MANAGE_AGENTS,
        Permission.VIEW_LOGS,
        Permission.EXPORT,
        Permission.PENTEST,
        Permission.CASES_READ,
        Permission.CASES_WRITE,
        Permission.CASES_DELETE,
        Permission.CASES_ASSIGN,
        Permission.TOOLS_M365,
        Permission.TOOLS_ENDPOINT,
        Permission.TOOLS_CREDENTIALS,
        Permission.TOOLS_PENTEST,
        Permission.AGENTS_VIEW,
        Permission.AGENTS_QUERY,
        Permission.AGENTS_CONFIGURE,
        Permission.AUDIT_READ,
        Permission.REPORTS_GENERATE,
        Permission.REPORTS_VIEW,
        Permission.REPORTS_EXPORT,
    },
    
    Role.ADMIN: {
        Permission.READ,
        Permission.WRITE,
        Permission.DELETE,
        Permission.RUN_TOOLS,
        Permission.MANAGE_AGENTS,
        Permission.ADMIN,
        Permission.VIEW_LOGS,
        Permission.EXPORT,
        Permission.PENTEST,
        Permission.TENANT_MANAGE,
        Permission.TENANT_VIEW,
        Permission.USERS_MANAGE,
        Permission.USERS_VIEW,
        Permission.ROLES_MANAGE,
        Permission.ROLES_ASSIGN,
        Permission.ROLES_VIEW,
        Permission.CASES_READ,
        Permission.CASES_WRITE,
        Permission.CASES_DELETE,
        Permission.CASES_ASSIGN,
        Permission.CASES_CLOSE,
        Permission.TOOLS_M365,
        Permission.TOOLS_ENDPOINT,
        Permission.TOOLS_CREDENTIALS,
        Permission.TOOLS_PENTEST,
        Permission.TOOLS_REDTEAM,
        Permission.AGENTS_MANAGE,
        Permission.AGENTS_VIEW,
        Permission.AGENTS_QUERY,
        Permission.AGENTS_CONFIGURE,
        Permission.AUDIT_READ,
        Permission.AUDIT_EXPORT,
        Permission.AUDIT_SEARCH,
        Permission.REPORTS_GENERATE,
        Permission.REPORTS_VIEW,
        Permission.REPORTS_EXPORT,
        Permission.REPORTS_SCHEDULE,
        Permission.BILLING_VIEW,
    },
    
    # === NUEVOS ROLES v4.6 ===
    
    Role.GLOBAL_ADMIN: set(Permission),  # Todos los permisos
    
    Role.TENANT_ADMIN: {
        Permission.READ,
        Permission.WRITE,
        Permission.DELETE,
        Permission.RUN_TOOLS,
        Permission.MANAGE_AGENTS,
        Permission.ADMIN,
        Permission.VIEW_LOGS,
        Permission.EXPORT,
        Permission.PENTEST,
        Permission.TENANT_MANAGE,
        Permission.TENANT_VIEW,
        Permission.TENANT_BILLING,
        Permission.TENANT_INTEGRATIONS,
        Permission.USERS_MANAGE,
        Permission.USERS_VIEW,
        Permission.USERS_INVITE,
        Permission.USERS_DEACTIVATE,
        Permission.ROLES_MANAGE,
        Permission.ROLES_ASSIGN,
        Permission.ROLES_VIEW,
        Permission.CASES_READ,
        Permission.CASES_WRITE,
        Permission.CASES_DELETE,
        Permission.CASES_ASSIGN,
        Permission.CASES_CLOSE,
        Permission.TOOLS_M365,
        Permission.TOOLS_M365_SPARROW,
        Permission.TOOLS_M365_HAWK,
        Permission.TOOLS_M365_EXTRACTOR,
        Permission.TOOLS_ENDPOINT,
        Permission.TOOLS_ENDPOINT_LOKI,
        Permission.TOOLS_ENDPOINT_YARA,
        Permission.TOOLS_ENDPOINT_OSQUERY,
        Permission.TOOLS_ENDPOINT_VOLATILITY,
        Permission.TOOLS_CREDENTIALS,
        Permission.TOOLS_CREDENTIALS_HIBP,
        Permission.TOOLS_CREDENTIALS_DEHASHED,
        Permission.TOOLS_PENTEST,
        Permission.TOOLS_REDTEAM,
        Permission.AGENTS_MANAGE,
        Permission.AGENTS_VIEW,
        Permission.AGENTS_QUERY,
        Permission.AGENTS_CONFIGURE,
        Permission.AUDIT_READ,
        Permission.AUDIT_EXPORT,
        Permission.AUDIT_SEARCH,
        Permission.REPORTS_GENERATE,
        Permission.REPORTS_VIEW,
        Permission.REPORTS_EXPORT,
        Permission.REPORTS_SCHEDULE,
        Permission.BILLING_VIEW,
        Permission.BILLING_MANAGE_PAYMENT,
        Permission.BILLING_DOWNLOAD_INVOICES,
    },
    
    Role.AUDIT: {
        Permission.READ,
        Permission.VIEW_LOGS,
        Permission.TENANT_VIEW,
        Permission.USERS_VIEW,
        Permission.ROLES_VIEW,
        Permission.CASES_READ,
        Permission.AGENTS_VIEW,
        Permission.AUDIT_READ,
        Permission.AUDIT_EXPORT,
        Permission.AUDIT_SEARCH,
        Permission.REPORTS_VIEW,
        Permission.REPORTS_EXPORT,
        Permission.BILLING_VIEW,
        Permission.BILLING_DOWNLOAD_INVOICES,
    },
    
    Role.RED_TEAM: {
        Permission.READ,
        Permission.WRITE,
        Permission.RUN_TOOLS,
        Permission.PENTEST,
        Permission.VIEW_LOGS,
        Permission.EXPORT,
        Permission.CASES_READ,
        Permission.CASES_WRITE,
        Permission.TOOLS_PENTEST,
        Permission.TOOLS_REDTEAM,
        Permission.TOOLS_REDTEAM_HEXSTRIKE,
        Permission.TOOLS_REDTEAM_C2,
        Permission.TOOLS_CREDENTIALS,
        Permission.TOOLS_CREDENTIALS_HIBP,
        Permission.TOOLS_CREDENTIALS_DEHASHED,
        Permission.AGENTS_VIEW,
        Permission.AGENTS_QUERY,
        Permission.REPORTS_GENERATE,
        Permission.REPORTS_VIEW,
        Permission.REPORTS_EXPORT,
    },
    
    Role.BLUE_TEAM: {
        Permission.READ,
        Permission.WRITE,
        Permission.RUN_TOOLS,
        Permission.VIEW_LOGS,
        Permission.EXPORT,
        Permission.CASES_READ,
        Permission.CASES_WRITE,
        Permission.CASES_ASSIGN,
        Permission.TOOLS_M365,
        Permission.TOOLS_M365_SPARROW,
        Permission.TOOLS_M365_HAWK,
        Permission.TOOLS_M365_EXTRACTOR,
        Permission.TOOLS_ENDPOINT,
        Permission.TOOLS_ENDPOINT_LOKI,
        Permission.TOOLS_ENDPOINT_YARA,
        Permission.TOOLS_ENDPOINT_OSQUERY,
        Permission.TOOLS_ENDPOINT_VOLATILITY,
        Permission.TOOLS_CREDENTIALS,
        Permission.TOOLS_CREDENTIALS_HIBP,
        Permission.TOOLS_CREDENTIALS_DEHASHED,
        Permission.AGENTS_VIEW,
        Permission.AGENTS_QUERY,
        Permission.AUDIT_READ,
        Permission.AUDIT_SEARCH,
        Permission.REPORTS_GENERATE,
        Permission.REPORTS_VIEW,
        Permission.REPORTS_EXPORT,
    },
    
    Role.PURPLE_TEAM: {
        Permission.READ,
        Permission.WRITE,
        Permission.RUN_TOOLS,
        Permission.PENTEST,
        Permission.VIEW_LOGS,
        Permission.EXPORT,
        Permission.CASES_READ,
        Permission.CASES_WRITE,
        Permission.CASES_ASSIGN,
        Permission.TOOLS_M365,
        Permission.TOOLS_M365_SPARROW,
        Permission.TOOLS_M365_HAWK,
        Permission.TOOLS_M365_EXTRACTOR,
        Permission.TOOLS_ENDPOINT,
        Permission.TOOLS_ENDPOINT_LOKI,
        Permission.TOOLS_ENDPOINT_YARA,
        Permission.TOOLS_ENDPOINT_OSQUERY,
        Permission.TOOLS_ENDPOINT_VOLATILITY,
        Permission.TOOLS_CREDENTIALS,
        Permission.TOOLS_CREDENTIALS_HIBP,
        Permission.TOOLS_CREDENTIALS_DEHASHED,
        Permission.TOOLS_PENTEST,
        Permission.TOOLS_REDTEAM,
        Permission.TOOLS_REDTEAM_HEXSTRIKE,
        Permission.AGENTS_VIEW,
        Permission.AGENTS_QUERY,
        Permission.AGENTS_CONFIGURE,
        Permission.AUDIT_READ,
        Permission.AUDIT_SEARCH,
        Permission.REPORTS_GENERATE,
        Permission.REPORTS_VIEW,
        Permission.REPORTS_EXPORT,
    },
    
    Role.CUSTOM: set(),  # Sin permisos por defecto, configurables por admin
}


@dataclass
class RoutePermission:
    """Configuración de permisos por ruta"""
    path_prefix: str
    method: str = "*"  # GET, POST, PUT, DELETE, o * para todos
    permissions: Set[Permission] = field(default_factory=set)
    public: bool = False
    rate_limit: int = 100  # requests por minuto
    
    def requires(self, permission: Permission) -> bool:
        return permission in self.permissions


# Configuración de rutas protegidas
# CRÍTICO: Rutas que antes tenían auth_required: false ahora están protegidas
PROTECTED_ROUTES: List[RoutePermission] = [
    # === CORE ===
    RoutePermission(
        path_prefix="/tenants",
        permissions={Permission.READ, Permission.WRITE},
        rate_limit=50
    ),
    RoutePermission(
        path_prefix="/tenants",
        method="POST",
        permissions={Permission.WRITE, Permission.ADMIN}
    ),
    RoutePermission(
        path_prefix="/tenants",
        method="DELETE",
        permissions={Permission.DELETE, Permission.ADMIN}
    ),
    
    # === FORENSICS ===
    RoutePermission(
        path_prefix="/forensics/credentials",
        permissions={Permission.RUN_TOOLS}
    ),
    RoutePermission(
        path_prefix="/forensics/case",
        method="GET",
        permissions={Permission.READ}
    ),
    RoutePermission(
        path_prefix="/forensics/case",
        method="POST",
        permissions={Permission.WRITE}
    ),
    RoutePermission(
        path_prefix="/forensics/case",
        method="DELETE",
        permissions={Permission.DELETE}
    ),
    
    # === DETECTION ===
    RoutePermission(
        path_prefix="/hunting",
        permissions={Permission.RUN_TOOLS}
    ),
    RoutePermission(
        path_prefix="/hunting/execute",
        permissions={Permission.RUN_TOOLS},
        rate_limit=20  # Limite más estricto para ejecución
    ),
    
    # === ANALYSIS ===
    RoutePermission(
        path_prefix="/timeline",
        method="GET",
        permissions={Permission.READ}
    ),
    RoutePermission(
        path_prefix="/timeline",
        method="POST",
        permissions={Permission.WRITE}
    ),
    RoutePermission(
        path_prefix="/timeline",
        method="DELETE",
        permissions={Permission.DELETE}
    ),
    
    # === OUTPUT ===
    RoutePermission(
        path_prefix="/reports",
        method="GET",
        permissions={Permission.READ}
    ),
    RoutePermission(
        path_prefix="/reports/generate",
        permissions={Permission.RUN_TOOLS, Permission.WRITE}
    ),
    RoutePermission(
        path_prefix="/reports/download",
        permissions={Permission.READ, Permission.EXPORT}
    ),
    
    # === EXECUTION - CRÍTICO ===
    RoutePermission(
        path_prefix="/api/agents",
        method="GET",
        permissions={Permission.READ, Permission.MANAGE_AGENTS}
    ),

    # === PENTEST AUTÓNOMO ===
    RoutePermission(
        path_prefix="/pentest",
        permissions={Permission.PENTEST, Permission.RUN_TOOLS},
        rate_limit=10
    ),
    RoutePermission(
        path_prefix="/api/agents",
        method="POST",
        permissions={Permission.MANAGE_AGENTS},
        rate_limit=10
    ),
    RoutePermission(
        path_prefix="/api/agents/deploy",
        permissions={Permission.MANAGE_AGENTS, Permission.ADMIN}
    ),
    
    RoutePermission(
        path_prefix="/api/tools/kali",
        permissions={Permission.RUN_TOOLS},
        rate_limit=30
    ),
    RoutePermission(
        path_prefix="/api/tools/kali/execute",
        permissions={Permission.RUN_TOOLS},
        rate_limit=10  # Más restrictivo
    ),
    
    # === IOC STORE ===
    RoutePermission(
        path_prefix="/api/iocs",
        method="GET",
        permissions={Permission.READ}
    ),
    RoutePermission(
        path_prefix="/api/iocs",
        method="POST",
        permissions={Permission.WRITE}
    ),
    RoutePermission(
        path_prefix="/api/iocs",
        method="DELETE",
        permissions={Permission.DELETE}
    ),
    RoutePermission(
        path_prefix="/api/iocs/export",
        permissions={Permission.EXPORT}
    ),
    
    # === THREAT INTEL ===
    RoutePermission(
        path_prefix="/threat-intel",
        method="GET",
        permissions={Permission.READ}
    ),
    RoutePermission(
        path_prefix="/threat-intel",
        method="POST",
        permissions={Permission.WRITE, Permission.RUN_TOOLS}
    ),
    
    # === ACTIVE INVESTIGATION ===
    RoutePermission(
        path_prefix="/active-investigation",
        permissions={Permission.RUN_TOOLS, Permission.MANAGE_AGENTS}
    ),
    RoutePermission(
        path_prefix="/active-investigation/execute",
        permissions={Permission.RUN_TOOLS},
        rate_limit=10
    ),
    RoutePermission(
        path_prefix="/active-investigation/network-capture",
        permissions={Permission.RUN_TOOLS, Permission.ADMIN}
    ),
    RoutePermission(
        path_prefix="/active-investigation/memory-dump",
        permissions={Permission.RUN_TOOLS, Permission.ADMIN}
    ),
    
    # === LLM ===
    RoutePermission(
        path_prefix="/llm",
        method="GET",
        permissions={Permission.READ}
    ),
    RoutePermission(
        path_prefix="/llm/generate",
        permissions={Permission.RUN_TOOLS},
        rate_limit=30
    ),
    RoutePermission(
        path_prefix="/llm/models/active",
        method="POST",
        permissions={Permission.ADMIN}
    ),
    
    # === LOGS & STREAMING ===
    RoutePermission(
        path_prefix="/logs",
        permissions={Permission.VIEW_LOGS}
    ),
    RoutePermission(
        path_prefix="/ws",
        permissions={Permission.VIEW_LOGS}
    ),
    
    # === SYSTEM ===
    RoutePermission(
        path_prefix="/api/v41/system",
        permissions={Permission.ADMIN}
    ),
]

# Rutas públicas (no requieren autenticación)
PUBLIC_ROUTES = [
    "/health",
    "/api/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/public/landing",   # Landing público (contenido marketing)
    "/api/auth/login",           # BRAC login endpoint
    "/api/auth/register",        # BRAC registration
    "/api/auth/refresh",         # Token refresh
    "/api/auth/select-tenant",   # Tenant selection (multi-tenant flow)
    "/api/auth/forgot-password", # Password reset request
    "/api/context/current",      # Solo lectura de contexto
    "/api/context",              # Context management
    "/api/configuration",        # Configuration panel
    "/api/v41/",                 # v4.1 API endpoints (use API key auth)
    "/tenants",                  # Tenant management
    "/reports",                  # Reports (use API key auth)
    "/api/remote-agents/download",  # v4.5 - Script download (public, token-based auth)
    "/api/remote-agents/ws",        # v4.5 - WebSocket agent connection
    "/api/remote-agents/status",    # v4.5 - Public status check
    # v4.6 - Registration & Onboarding (public)
    "/api/register",             # Self-service registration
    "/api/onboarding",           # Onboarding flow
    "/api/billing/plans",        # Public pricing
    "/api/billing/webhook",      # Stripe webhook
]


def get_route_permissions(path: str, method: str = "GET") -> RoutePermission:
    """
    Obtener configuración de permisos para una ruta
    
    Args:
        path: Path de la ruta
        method: Método HTTP
    
    Returns:
        RoutePermission o None si no está protegida
    """
    # Verificar rutas públicas
    for public_path in PUBLIC_ROUTES:
        if path.startswith(public_path):
            return RoutePermission(path_prefix=public_path, public=True)
    
    # Buscar ruta protegida más específica
    matched = None
    for route in PROTECTED_ROUTES:
        if path.startswith(route.path_prefix):
            if route.method == "*" or route.method == method:
                if matched is None or len(route.path_prefix) > len(matched.path_prefix):
                    matched = route
    
    return matched


def check_permission(
    user_permissions: Set[Permission],
    required_permissions: Set[Permission]
) -> bool:
    """
    Verificar si el usuario tiene los permisos requeridos
    
    Args:
        user_permissions: Permisos del usuario
        required_permissions: Permisos requeridos
    
    Returns:
        True si tiene al menos uno de los permisos requeridos
    """
    # Admin siempre tiene acceso
    if Permission.ADMIN in user_permissions:
        return True
    
    # Verificar si tiene al menos un permiso requerido
    return bool(user_permissions & required_permissions)


def get_user_permissions(role: Role) -> Set[Permission]:
    """Obtener permisos de un rol"""
    return ROLE_PERMISSIONS.get(role, set())


# Módulos que necesitan auth_required: true (actualización pendiente en modules.json)
MODULES_REQUIRING_AUTH_UPDATE = [
    "tenants",      # Actualmente: false -> Debe ser: true
    "ioc_store",    # Actualmente: false -> Debe ser: true
    "agents",       # Actualmente: false -> Debe ser: true
    "kali_tools",   # Actualmente: false -> Debe ser: true
    "threat_intel", # Actualmente: false -> Debe ser: true
]
