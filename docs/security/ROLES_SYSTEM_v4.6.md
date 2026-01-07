# Sistema de Roles y Permisos v4.6

## 📋 Resumen

El sistema de roles v4.6 implementa una arquitectura de permisos jerárquica con 7 roles predefinidos y 30+ permisos granulares, diseñada para soportar multi-tenancy y equipos especializados de seguridad.

## 🔐 Roles Disponibles

| Rol | Descripción | Asignación |
|-----|-------------|------------|
| **GLOBAL_ADMIN** | Control total de la plataforma | Manual (solo Pluton_JE por defecto) |
| **TENANT_ADMIN** | Administrador del tenant | Automático después de Stripe |
| **AUDIT** | Solo lectura, auditoría | Manual por Tenant Admin |
| **RED_TEAM** | Herramientas ofensivas | Manual por Tenant Admin |
| **BLUE_TEAM** | Herramientas defensivas/forenses | Manual por Tenant Admin |
| **PURPLE_TEAM** | Red + Blue combinado | Manual por Tenant Admin |
| **CUSTOM** | Permisos personalizados | Manual por Tenant Admin |

## 📦 Permisos por Categoría

### Platform (Solo Global Admin)
- `platform:manage` - Gestión completa de la plataforma
- `platform:billing` - Gestión de facturación
- `platform:settings` - Configuración global

### Tenant
- `tenant:manage` - Gestión completa del tenant
- `tenant:users` - Gestión de usuarios
- `tenant:roles` - Gestión de roles
- `tenant:settings` - Configuración del tenant

### Tools
- `tools:m365` - Herramientas Microsoft 365
- `tools:endpoint` - Herramientas de endpoint
- `tools:credentials` - Herramientas de credenciales
- `tools:pentest` - Herramientas de pentesting (Red Team)
- `tools:redteam` - Herramientas Red Team
- `tools:osint` - Herramientas OSINT

### Cases
- `cases:read` - Lectura de casos
- `cases:write` - Creación y edición
- `cases:delete` - Eliminación
- `cases:export` - Exportación

### Audit
- `audit:read` - Lectura de logs
- `audit:export` - Exportación de auditoría
- `audit:full` - Acceso completo

## 🚀 Instalación

### 1. Ejecutar Migración SQL

```bash
# Modo automático
./scripts/run_roles_migration.sh

# Modo dry-run (ver SQL sin ejecutar)
./scripts/run_roles_migration.sh --dry-run
```

### 2. Verificar

```sql
-- Verificar roles
SELECT * FROM roles;

-- Verificar permisos
SELECT * FROM permissions;

-- Verificar Pluton_JE
SELECT email, is_global_admin FROM users WHERE email = 'pluton_je@jeturing.com';
```

## 📡 API Endpoints

### Global Admin (`/api/global-admin/*`)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/stats` | GET | Estadísticas de la plataforma |
| `/tenants` | GET | Listar todos los tenants |
| `/tenants/{id}` | GET | Detalles de un tenant |
| `/tenants/{id}/plan` | PUT | Cambiar plan de tenant |
| `/tenants/{id}/status` | PUT | Cambiar estado de suscripción |
| `/global-admins` | GET | Listar global admins |
| `/global-admins` | POST | Asignar/remover global admin |
| `/roles` | GET | Roles de sistema |
| `/permissions` | GET | Todos los permisos |
| `/settings` | GET/PUT | Configuración global |
| `/audit-logs` | GET | Logs de auditoría |

### Role Management (`/api/admin/roles/*`)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/` | GET | Listar roles del tenant |
| `/` | POST | Crear rol custom |
| `/{id}` | GET | Detalles de un rol |
| `/{id}` | PUT | Actualizar rol custom |
| `/{id}` | DELETE | Eliminar rol custom |
| `/assign` | POST | Asignar rol a usuario |
| `/assign` | DELETE | Remover rol de usuario |
| `/assign/bulk` | POST | Asignación masiva |
| `/users/{id}` | GET | Roles de un usuario |
| `/permissions/list` | GET | Permisos disponibles |
| `/teams/red-team` | POST | Configurar como Red Team |
| `/teams/blue-team` | POST | Configurar como Blue Team |
| `/teams/purple-team` | POST | Configurar como Purple Team |
| `/teams/auditor` | POST | Configurar como Auditor |

## 🔄 Flujo de Asignación Automática

```
Usuario completa Stripe → complete_onboarding() 
    → _provision_tenant() 
    → auto_assign_tenant_admin() 
    → Usuario tiene rol TENANT_ADMIN
```

## 🛡️ Uso en Código

### Middleware de Permisos

```python
from api.middleware.auth import (
    get_current_user,
    require_global_admin,
    require_permission,
    require_any_permission,
    require_tenant_admin
)

# Solo global admin
@router.get("/admin-only", dependencies=[Depends(require_global_admin)])
async def admin_endpoint():
    pass

# Requiere permiso específico
@router.get("/cases", dependencies=[Depends(require_permission("cases:read"))])
async def list_cases():
    pass

# Requiere al menos uno de los permisos
@router.get("/audit", dependencies=[Depends(require_any_permission(["audit:read", "cases:read"]))])
async def view_audit():
    pass
```

### Servicio de Roles

```python
from api.services.roles_service import (
    get_user_permissions,
    assign_role_to_user,
    create_custom_role,
    validate_permission
)

# Obtener permisos
perms = await get_user_permissions(user_id, tenant_id)

# Validar permiso
has_access = await validate_permission(user_id, "cases:write", tenant_id)

# Asignar rol
result = await assign_role_to_user(
    user_id="123",
    role_name="blue_team",
    tenant_id="tenant-456",
    assigned_by="admin-789"
)

# Crear rol custom
result = await create_custom_role(
    tenant_id="tenant-456",
    role_name="investigator",
    display_name="Investigador",
    description="Rol de investigación personalizado",
    permissions=["cases:read", "cases:write", "tools:m365"],
    created_by="admin-789"
)
```

## 📊 Matriz de Permisos por Rol

| Permiso | Global | Tenant | Audit | Red | Blue | Purple |
|---------|--------|--------|-------|-----|------|--------|
| platform:* | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| tenant:* | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| tools:m365 | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ |
| tools:endpoint | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ |
| tools:pentest | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ |
| tools:redteam | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ |
| cases:read | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| cases:write | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ |
| audit:read | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |

## 🔧 Configuración

### Variables de Entorno

```bash
# JWT (requerido para auth)
JWT_SECRET_KEY=tu-clave-secreta-muy-larga
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# RBAC
RBAC_ENABLED=true
RBAC_DEFAULT_ROLE=viewer
```

## 📁 Archivos del Sistema

```
api/
├── config.py                    # JWT y RBAC settings
├── middleware/
│   └── auth.py                  # Dependencias de autenticación
├── routes/
│   ├── global_admin.py          # Endpoints Global Admin
│   └── admin_roles.py           # Endpoints Role Management
└── services/
    ├── roles_service.py         # Lógica de negocio de roles
    └── onboarding_service.py    # Auto-asignación en onboarding

core/
└── rbac_config.py               # Definición de roles y permisos

migrations/
└── add_roles_system.sql         # Migración de base de datos

scripts/
└── run_roles_migration.sh       # Script de ejecución
```

## ✅ Checklist de Implementación

- [x] Migración SQL creada (`add_roles_system.sql`)
- [x] RBAC config actualizado con 7 roles
- [x] Servicio de roles (`roles_service.py`)
- [x] Endpoints Global Admin (`global_admin.py`)
- [x] Endpoints Role Management (`admin_roles.py`)
- [x] Middleware de auth extendido
- [x] Auto-asignación en onboarding
- [x] Script de migración
- [x] Documentación

---

**Versión**: 4.6.0  
**Fecha**: Enero 2025  
**Autor**: MCP-Forensics Expert Agent
