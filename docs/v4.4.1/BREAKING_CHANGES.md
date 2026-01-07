# 🚨 Breaking Changes - v4.4.1

> **Release Date**: December 2025  
> **Migration Required**: Yes  
> **Backwards Compatible**: No (major architectural changes)

---

## Resumen Ejecutivo

La versión 4.4.1 introduce cambios arquitectónicos significativos que **requieren migración**. Los cambios principales son:

1. **Case-Centric Architecture**: Todo debe estar asociado a un `case_id`
2. **RBAC Hardening**: Nuevo sistema de permisos granulares
3. **WebSocket Streaming**: Nuevo protocolo de logs en tiempo real
4. **PostgreSQL-Ready**: Preparación para migración de SQLite a PostgreSQL

---

## 1. Case-Centric Architecture (CRÍTICO)

### Antes (v4.3.x)
```python
# Los análisis podían ejecutarse sin case_id
POST /forensics/m365/analyze
{
    "tenant_id": "xxx",
    "scope": ["sparrow"]
}
```

### Ahora (v4.4.1)
```python
# OBLIGATORIO: case_id en todas las operaciones forenses
POST /forensics/m365/analyze
{
    "case_id": "IR-2025-001",      # ← REQUERIDO
    "tenant_id": "xxx",
    "scope": ["sparrow"]
}
```

### Impacto
- ❌ Requests sin `case_id` retornan `400 Bad Request`
- ❌ APIs legacy que no incluyan case_id fallarán
- ✅ Nuevo modelo `ForensicAnalysis` con ID formato `FA-YYYY-XXXXX`

### Migración
```python
# Agregar case_id a todas las llamadas API
headers = {"X-API-Key": "your-key", "Content-Type": "application/json"}
data = {
    "case_id": "IR-2025-001",  # Agregar esta línea
    # ... resto de parámetros
}
requests.post(f"{API_URL}/forensics/m365/analyze", json=data, headers=headers)
```

---

## 2. RBAC Hardening (CRÍTICO)

### Antes (v4.3.x)
```python
# Solo validación de API key
X-API-Key: your-api-key
```

### Ahora (v4.4.1)
```python
# API Key + Permisos granulares
X-API-Key: your-api-key
# El key debe tener permisos específicos asignados
```

### Nuevos Permisos
| Permiso | Descripción | Endpoints |
|---------|-------------|-----------|
| `mcp:read` | Lectura de casos y análisis | GET /cases/*, GET /forensics/* |
| `mcp:write` | Crear/modificar casos | POST /cases/*, PUT /cases/* |
| `mcp:run-tools` | Ejecutar herramientas forenses | POST /forensics/*/analyze |
| `mcp:manage-agents` | Gestionar agentes Blue/Red/Purple | POST /agents/* |
| `mcp:admin` | Acceso total (superuser) | Todos los endpoints |

### Rate Limiting
```yaml
# Nuevos límites por rol
viewer: 100 requests/minute
analyst: 500 requests/minute  
operator: 1000 requests/minute
admin: 5000 requests/minute
```

### Impacto
- ❌ API keys sin permisos asignados fallarán con `403 Forbidden`
- ❌ Endpoints sensibles requieren permisos específicos
- ✅ Audit logging automático de todas las operaciones

### Migración
```bash
# 1. Actualizar configuración de API keys
# En .env o config:
API_KEY_PERMISSIONS=mcp:read,mcp:write,mcp:run-tools

# 2. Para múltiples usuarios, configurar en RBAC
# Ver docs/v4.4.1/RBAC_GUIDE.md
```

---

## 3. WebSocket Streaming (NUEVO)

### Antes (v4.3.x)
```python
# Polling para obtener logs
while True:
    response = requests.get(f"/cases/{case_id}/logs")
    time.sleep(5)
```

### Ahora (v4.4.1)
```javascript
// WebSocket para streaming en tiempo real
const ws = new WebSocket('ws://localhost:8888/ws/analysis/FA-2025-00001');

ws.onmessage = (event) => {
    const log = JSON.parse(event.data);
    console.log(`[${log.level}] ${log.message}`);
};
```

### Nuevos Endpoints WebSocket
| Endpoint | Descripción |
|----------|-------------|
| `/ws/analysis/{analysis_id}` | Logs de un análisis específico |
| `/ws/case/{case_id}/live` | Todos los eventos de un caso |
| `/ws/global/logs` | Stream global (admin only) |

### Formato de Mensajes
```json
{
    "type": "log",
    "level": "INFO",
    "message": "Scanning Azure AD sign-ins...",
    "timestamp": "2025-12-08T10:30:00Z",
    "analysis_id": "FA-2025-00001",
    "case_id": "IR-2025-001",
    "context": {
        "tool": "sparrow",
        "step": 3,
        "total_steps": 10
    }
}
```

### Impacto
- ⚠️ El polling tradicional sigue funcionando pero está **deprecated**
- ✅ Menor latencia en UI
- ✅ Menor carga en servidor

---

## 4. Nuevo Modelo ForensicAnalysis

### Antes (v4.3.x)
```python
# Análisis sin estructura formal
{
    "case_id": "IR-001",
    "status": "completed",
    "results": {...}
}
```

### Ahora (v4.4.1)
```python
# Modelo ForensicAnalysis completo
{
    "id": "FA-2025-00001",           # Nuevo formato de ID
    "case_id": "IR-2025-001",
    "analysis_type": "m365_compromise",
    "status": "running",
    "created_at": "2025-12-08T10:00:00Z",
    "started_at": "2025-12-08T10:01:00Z",
    "completed_at": null,
    "tools_executed": ["sparrow", "hawk"],
    "findings": [...],
    "evidence_paths": [...],
    "metadata": {...}
}
```

### Nuevos Campos
| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | string | FA-YYYY-XXXXX format |
| `analysis_type` | enum | Tipo de análisis |
| `started_at` | datetime | Inicio de ejecución |
| `completed_at` | datetime | Fin de ejecución |
| `tools_executed` | list | Herramientas ejecutadas |
| `findings` | list | Hallazgos estructurados |
| `evidence_paths` | list | Rutas a evidencia recolectada |

---

## 5. Estructura de Directorios

### Antes (v4.3.x)
```
/var/evidence/
├── case-001/
│   ├── sparrow/
│   └── hawk/
```

### Ahora (v4.4.1)
```
~/forensics-evidence/           # Movido a home del usuario
├── cases-data/
│   └── IR-2025-001/
│       ├── analyses/
│       │   ├── FA-2025-00001/  # Nuevo: por análisis
│       │   │   ├── sparrow/
│       │   │   ├── hawk/
│       │   │   └── metadata.json
│       │   └── FA-2025-00002/
│       ├── evidence/
│       └── reports/
└── tool_outputs/
```

### Migración
```bash
# Script de migración incluido
./scripts/migrate_evidence_v4.4.1.sh
```

---

## 6. API Responses

### Cambios en Respuestas HTTP

#### Status Codes
| Antes | Ahora | Descripción |
|-------|-------|-------------|
| `200 OK` | `202 Accepted` | Para operaciones async |
| `500 Internal Error` | `422 Unprocessable` | Para errores de validación |

#### Response Format
```json
// v4.3.x
{
    "status": "success",
    "data": {...}
}

// v4.4.1
{
    "success": true,
    "data": {...},
    "analysis_id": "FA-2025-00001",  // Nuevo
    "case_id": "IR-2025-001",         // Nuevo
    "timestamp": "2025-12-08T10:30:00Z"
}
```

---

## 7. Docker Compose

### Antes (v4.3.x)
```yaml
# docker-compose.yml simple
services:
  mcp-forensics:
    # ...
```

### Ahora (v4.4.1)
```yaml
# docker-compose.v4.4.1.yml con microservicios
services:
  mcp-forensics:      # API principal
  postgres:           # Base de datos (nuevo)
  redis:              # Cache/queue (nuevo)
  ws-router:          # WebSocket router (nuevo)
  llm-provider:       # LLM integration (nuevo)
  logging-worker:     # Log aggregation (nuevo)
  executor:           # Sandboxed execution (nuevo)
```

### Migración
```bash
# Usar el nuevo compose file
docker-compose -f docker-compose.v4.4.1.yml up -d
```

---

## 8. Environment Variables

### Nuevas Variables
```bash
# RBAC
RBAC_ENABLED=true
RBAC_DEFAULT_ROLE=viewer
RBAC_RATE_LIMIT_ENABLED=true

# WebSocket
WS_HEARTBEAT_INTERVAL=30
WS_MAX_CONNECTIONS=100

# PostgreSQL (opcional, preparación)
DATABASE_URL=postgresql://user:pass@localhost:5432/forensics
USE_POSTGRESQL=false  # Activar cuando esté listo

# OpenTelemetry
OTEL_ENABLED=true
OTEL_SERVICE_NAME=mcp-forensics
OTEL_EXPORTER_JAEGER_ENDPOINT=http://localhost:14268/api/traces
```

### Variables Deprecated
```bash
# Ya no se usan
SIMPLE_AUTH=true          # Reemplazado por RBAC
LEGACY_EVIDENCE_PATH=...  # Usar EVIDENCE_DIR
```

---

## 9. Checklist de Migración

### Pre-Migración
- [ ] Backup de base de datos SQLite
- [ ] Backup de directorio de evidencia
- [ ] Documentar API keys actuales
- [ ] Revisar integraciones externas

### Migración
- [ ] Actualizar código a v4.4.1
- [ ] Ejecutar `./scripts/migrate_evidence_v4.4.1.sh`
- [ ] Configurar nuevas variables de entorno
- [ ] Asignar permisos RBAC a API keys
- [ ] Actualizar clientes para incluir `case_id`

### Post-Migración
- [ ] Verificar WebSocket streaming
- [ ] Probar endpoints con nuevos permisos
- [ ] Validar estructura de evidencia
- [ ] Actualizar dashboards/integraciones

---

## 10. Soporte y Rollback

### Rollback
```bash
# Si necesita volver a v4.3.x
git checkout v4.3.x
./scripts/rollback_evidence.sh
```

### Soporte
- Issues: GitHub Issues
- Docs: `/docs/v4.4.1/`
- Logs: `tail -f logs/mcp-forensics.log`

---

## Timeline de Deprecación

| Feature | Status en v4.4.1 | Removido en |
|---------|------------------|-------------|
| API sin case_id | ❌ Error | v4.4.1 |
| Polling de logs | ⚠️ Deprecated | v4.5.0 |
| SQLite exclusivo | ⚠️ Deprecated | v4.5.0 |
| Simple Auth | ❌ Removido | v4.4.1 |

---

**Última actualización**: December 2025  
**Versión del documento**: 1.0
