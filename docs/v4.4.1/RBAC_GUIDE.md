# 🔐 RBAC Guide - v4.4.1

> **Role-Based Access Control para MCP Kali Forensics**  
> Guía completa de configuración y uso del sistema de permisos

---

## 📋 Tabla de Contenidos

1. [Introducción](#introducción)
2. [Arquitectura RBAC](#arquitectura-rbac)
3. [Permisos](#permisos)
4. [Roles Predefinidos](#roles-predefinidos)
5. [Configuración](#configuración)
6. [API Key Management](#api-key-management)
7. [Rate Limiting](#rate-limiting)
8. [Audit Logging](#audit-logging)
9. [Troubleshooting](#troubleshooting)

---

## Introducción

El sistema RBAC de v4.4.1 proporciona control granular sobre quién puede acceder a qué recursos en el MCP. Está diseñado para:

- **Seguridad**: Principio de mínimo privilegio
- **Auditoría**: Trazabilidad completa de acciones
- **Escalabilidad**: Soporte para múltiples usuarios/equipos
- **Flexibilidad**: Roles personalizables

---

## Arquitectura RBAC

```
┌─────────────────────────────────────────────────────────────┐
│                      Request Flow                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   Client Request                                             │
│        │                                                     │
│        ▼                                                     │
│   ┌─────────────┐                                           │
│   │ API Gateway │                                           │
│   └──────┬──────┘                                           │
│          │                                                   │
│          ▼                                                   │
│   ┌─────────────────┐     ┌─────────────────┐              │
│   │  RBAC Middleware │────▶│  RBACConfig     │              │
│   └────────┬────────┘     │  (Singleton)    │              │
│            │              └─────────────────┘              │
│            │                                                │
│            ▼                                                │
│   ┌─────────────────┐                                      │
│   │ Permission Check │                                      │
│   │ ├─ API Key Valid?│                                      │
│   │ ├─ Has Permission?│                                     │
│   │ └─ Rate Limit OK?│                                      │
│   └────────┬────────┘                                      │
│            │                                                │
│     ┌──────┴──────┐                                        │
│     │             │                                        │
│     ▼             ▼                                        │
│  ✅ Allow      ❌ Deny                                     │
│  (continue)    (403/429)                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Permisos

### Lista de Permisos

| Permiso | Código | Descripción |
|---------|--------|-------------|
| **Read** | `mcp:read` | Lectura de casos, análisis y logs |
| **Write** | `mcp:write` | Crear/modificar casos y análisis |
| **Run Tools** | `mcp:run-tools` | Ejecutar herramientas forenses |
| **Manage Agents** | `mcp:manage-agents` | Gestionar agentes Blue/Red/Purple |
| **Admin** | `mcp:admin` | Acceso total (superuser) |

### Jerarquía de Permisos

```
mcp:admin (Superuser - incluye todos)
    │
    ├── mcp:manage-agents
    │       │
    ├───────┤
    │       │
    ├── mcp:run-tools
    │       │
    ├───────┤
    │       │
    ├── mcp:write
    │       │
    └───────┴── mcp:read (Base)
```

### Endpoints por Permiso

#### `mcp:read`
```
GET  /health
GET  /api/docs
GET  /cases
GET  /cases/{case_id}
GET  /cases/{case_id}/analyses
GET  /forensics/status/{analysis_id}
GET  /forensics/results/{analysis_id}
```

#### `mcp:write`
```
POST   /cases
PUT    /cases/{case_id}
DELETE /cases/{case_id}
POST   /cases/{case_id}/notes
PUT    /cases/{case_id}/status
```

#### `mcp:run-tools`
```
POST /forensics/m365/analyze
POST /forensics/endpoint/scan
POST /forensics/credentials/check
POST /forensics/memory/analyze
```

#### `mcp:manage-agents`
```
GET    /agents
POST   /agents/blue/task
POST   /agents/red/task
POST   /agents/purple/task
PUT    /agents/{agent_id}/config
DELETE /agents/{agent_id}
```

#### `mcp:admin`
```
*    /* (Todos los endpoints)
GET  /ws/global/logs
POST /admin/config
POST /admin/users
DELETE /admin/*
```

---

## Roles Predefinidos

### Viewer
**Caso de uso**: SOC Tier 1, stakeholders, reportes

```python
viewer = {
    "permissions": ["mcp:read"],
    "rate_limit": 100,  # requests/minute
    "description": "Read-only access to cases and analyses"
}
```

### Analyst
**Caso de uso**: SOC Tier 2, analistas de seguridad

```python
analyst = {
    "permissions": ["mcp:read", "mcp:write"],
    "rate_limit": 500,
    "description": "Can create and modify cases"
}
```

### Operator
**Caso de uso**: SOC Tier 3, IR team, threat hunters

```python
operator = {
    "permissions": ["mcp:read", "mcp:write", "mcp:run-tools"],
    "rate_limit": 1000,
    "description": "Can execute forensic tools"
}
```

### Admin
**Caso de uso**: Team leads, system administrators

```python
admin = {
    "permissions": ["mcp:admin"],  # Incluye todos
    "rate_limit": 5000,
    "description": "Full system access"
}
```

---

## Configuración

### Variables de Entorno

```bash
# Habilitar RBAC (default: true)
RBAC_ENABLED=true

# Rol por defecto para API keys sin rol asignado
RBAC_DEFAULT_ROLE=viewer

# Habilitar rate limiting
RBAC_RATE_LIMIT_ENABLED=true

# IPs que bypasean RBAC (desarrollo/testing)
RBAC_WHITELIST_IPS=127.0.0.1,::1

# Modo estricto (rechazar requests sin API key válida)
RBAC_STRICT_MODE=true
```

### Archivo de Configuración

```python
# core/rbac_config.py

RBAC_CONFIG = {
    "enabled": True,
    "default_role": "viewer",
    "strict_mode": True,
    
    "roles": {
        "viewer": {
            "permissions": ["mcp:read"],
            "rate_limit": 100,
            "allowed_ips": ["*"]
        },
        "analyst": {
            "permissions": ["mcp:read", "mcp:write"],
            "rate_limit": 500,
            "allowed_ips": ["10.0.0.0/8", "192.168.0.0/16"]
        },
        "operator": {
            "permissions": ["mcp:read", "mcp:write", "mcp:run-tools"],
            "rate_limit": 1000,
            "allowed_ips": ["10.0.0.0/8"]
        },
        "admin": {
            "permissions": ["mcp:admin"],
            "rate_limit": 5000,
            "allowed_ips": ["10.0.1.0/24"]  # Solo red de admins
        }
    },
    
    "route_permissions": {
        "/forensics/*": ["mcp:run-tools"],
        "/cases/*": ["mcp:write"],
        "/agents/*": ["mcp:manage-agents"],
        "/admin/*": ["mcp:admin"]
    }
}
```

---

## API Key Management

### Estructura de API Key

```json
{
    "key": "mcp_live_abc123def456...",
    "name": "SOC-Team-Key",
    "role": "operator",
    "permissions": ["mcp:read", "mcp:write", "mcp:run-tools"],
    "created_at": "2025-12-08T10:00:00Z",
    "expires_at": "2026-12-08T10:00:00Z",
    "last_used": "2025-12-08T15:30:00Z",
    "metadata": {
        "team": "SOC",
        "environment": "production"
    }
}
```

### Crear API Key (Admin)

```bash
# Via API
curl -X POST http://localhost:8888/admin/api-keys \
  -H "X-API-Key: admin-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "New-Analyst-Key",
    "role": "analyst",
    "expires_in_days": 365
  }'

# Response
{
    "key": "mcp_live_xyz789...",
    "role": "analyst",
    "expires_at": "2026-12-08T10:00:00Z"
}
```

### Revocar API Key

```bash
curl -X DELETE http://localhost:8888/admin/api-keys/mcp_live_xyz789 \
  -H "X-API-Key: admin-key"
```

### Listar API Keys

```bash
curl http://localhost:8888/admin/api-keys \
  -H "X-API-Key: admin-key"
```

---

## Rate Limiting

### Configuración por Rol

| Rol | Límite | Ventana | Burst |
|-----|--------|---------|-------|
| viewer | 100 req | 1 min | 10 |
| analyst | 500 req | 1 min | 50 |
| operator | 1000 req | 1 min | 100 |
| admin | 5000 req | 1 min | 500 |

### Headers de Rate Limit

```http
X-RateLimit-Limit: 500
X-RateLimit-Remaining: 423
X-RateLimit-Reset: 1733667600
```

### Respuesta cuando excede límite

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 45

{
    "error": "rate_limit_exceeded",
    "message": "Rate limit exceeded. Try again in 45 seconds.",
    "retry_after": 45
}
```

### Bypass de Rate Limit

```python
# Para IPs de confianza (testing, internal services)
RBAC_WHITELIST_IPS=127.0.0.1,10.0.1.100
```

---

## Audit Logging

### Eventos Registrados

| Evento | Nivel | Descripción |
|--------|-------|-------------|
| `auth.success` | INFO | Autenticación exitosa |
| `auth.failure` | WARNING | Intento fallido |
| `permission.denied` | WARNING | Permiso denegado |
| `rate_limit.exceeded` | WARNING | Rate limit excedido |
| `api.request` | DEBUG | Request procesado |
| `admin.action` | INFO | Acción administrativa |

### Formato de Log

```json
{
    "timestamp": "2025-12-08T15:30:00.123Z",
    "event": "permission.denied",
    "level": "WARNING",
    "api_key": "mcp_live_abc...def",
    "api_key_name": "SOC-Team-Key",
    "role": "analyst",
    "endpoint": "POST /forensics/m365/analyze",
    "required_permission": "mcp:run-tools",
    "user_permissions": ["mcp:read", "mcp:write"],
    "ip_address": "10.0.1.50",
    "user_agent": "Python/requests",
    "request_id": "req_abc123"
}
```

### Consultar Audit Log

```bash
# Últimos eventos de permisos denegados
curl "http://localhost:8888/admin/audit?event=permission.denied&limit=100" \
  -H "X-API-Key: admin-key"

# Eventos por API key
curl "http://localhost:8888/admin/audit?api_key=mcp_live_abc123&limit=50" \
  -H "X-API-Key: admin-key"
```

---

## Troubleshooting

### Problema: 403 Forbidden

**Síntoma**: Request rechazado con 403

**Diagnóstico**:
```bash
# Verificar permisos de la API key
curl http://localhost:8888/admin/api-keys/mcp_live_abc123 \
  -H "X-API-Key: admin-key"
```

**Soluciones**:
1. Verificar que la API key tiene el permiso requerido
2. Verificar que el rol tiene acceso al endpoint
3. Verificar IP whitelist si aplica

### Problema: 429 Too Many Requests

**Síntoma**: Rate limit excedido

**Diagnóstico**:
```bash
# Ver headers de rate limit
curl -I http://localhost:8888/health \
  -H "X-API-Key: your-key"
```

**Soluciones**:
1. Esperar el tiempo indicado en `Retry-After`
2. Solicitar upgrade de rol si es legítimo
3. Revisar si hay requests duplicados

### Problema: RBAC no se aplica

**Síntoma**: Todos los requests pasan sin verificación

**Diagnóstico**:
```bash
# Verificar configuración
grep RBAC .env
```

**Soluciones**:
1. Verificar `RBAC_ENABLED=true`
2. Verificar que el middleware está registrado en `main.py`
3. Reiniciar el servicio

### Problema: API Key expirada

**Síntoma**: 401 Unauthorized con mensaje de expiración

**Solución**:
```bash
# Generar nueva API key
curl -X POST http://localhost:8888/admin/api-keys/rotate/mcp_live_abc123 \
  -H "X-API-Key: admin-key"
```

---

## Best Practices

### 1. Principio de Mínimo Privilegio
```
✅ Asignar el rol más restrictivo que permita hacer el trabajo
❌ Dar admin a todos "por si acaso"
```

### 2. Rotación de API Keys
```
✅ Rotar keys cada 90 días
✅ Revocar keys de empleados que salen
❌ Compartir keys entre múltiples usuarios
```

### 3. Monitoreo
```
✅ Alertar en permission.denied repetidos
✅ Revisar audit logs semanalmente
❌ Ignorar rate limit warnings
```

### 4. Segmentación
```
✅ Keys diferentes por ambiente (dev/staging/prod)
✅ Keys diferentes por equipo
❌ Una key para todo
```

---

## Integración con SIEM

### Exportar logs a Splunk/ELK

```bash
# Configurar exportación de audit logs
AUDIT_LOG_EXPORT=true
AUDIT_LOG_SYSLOG_HOST=siem.empresa.com
AUDIT_LOG_SYSLOG_PORT=514
AUDIT_LOG_FORMAT=json
```

### Alertas recomendadas

```yaml
# Ejemplo para Splunk
alerts:
  - name: "Multiple Auth Failures"
    query: 'source="mcp-forensics" event="auth.failure" | stats count by api_key | where count > 10'
    threshold: 10
    window: 5m
    
  - name: "Permission Denied Spike"
    query: 'source="mcp-forensics" event="permission.denied" | timechart count'
    threshold: 50
    window: 1h
    
  - name: "Admin Action Outside Hours"
    query: 'source="mcp-forensics" event="admin.action" date_hour<8 OR date_hour>20'
    immediate: true
```

---

## Referencias

- [BREAKING_CHANGES.md](./BREAKING_CHANGES.md) - Cambios de migración
- [core/rbac_config.py](/core/rbac_config.py) - Configuración de roles
- [api/middleware/rbac.py](/api/middleware/rbac.py) - Implementación del middleware

---

**Última actualización**: December 2025  
**Versión**: 1.0
