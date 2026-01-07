# 📋 CHANGELOG v4.4.1

> **Release**: Platform Architecture Upgrade + Case-Centric + Analysis Model + Streaming Layer  
> **Date**: December 2025  
> **Type**: Major Release

---

## 🎯 Highlights

Esta versión representa una **actualización arquitectónica mayor** del MCP Kali Forensics, estableciendo las bases para escalabilidad enterprise y mejorando significativamente la trazabilidad de investigaciones forenses.

### Principales Mejoras
- 🔒 **RBAC Hardening**: Sistema de permisos granulares con rate limiting
- 📡 **WebSocket Streaming**: Logs en tiempo real via WebSocket
- 🗂️ **Case-Centric**: Todo asociado obligatoriamente a un case_id
- 📊 **OpenTelemetry**: Observabilidad completa con traces y métricas
- 🐳 **Docker Microservices**: Arquitectura de microservicios preparada

---

## ✨ New Features

### 1. Modelo ForensicAnalysis
**Archivos**: `api/models/forensic_analysis.py`

- Nuevo modelo para análisis forenses con ID formato `FA-YYYY-XXXXX`
- Vinculación obligatoria a casos (`case_id`)
- Tracking de herramientas ejecutadas, hallazgos y evidencia
- Estados: `pending`, `running`, `completed`, `failed`, `cancelled`

```python
from api.models.forensic_analysis import ForensicAnalysis

analysis = ForensicAnalysis(
    case_id="IR-2025-001",
    analysis_type="m365_compromise",
    tools=["sparrow", "hawk"]
)
# ID generado: FA-2025-00001
```

### 2. Logging Queue + WebSocket Streaming
**Archivos**: `core/logging_queue.py`, `api/routes/ws_streaming.py`

- Cola de logs thread-safe con patrón singleton
- Streaming en tiempo real via WebSocket
- Endpoints:
  - `/ws/analysis/{analysis_id}` - Logs de análisis específico
  - `/ws/case/{case_id}/live` - Eventos de caso
  - `/ws/global/logs` - Stream global (admin)
- Heartbeat automático cada 30 segundos
- Gestión de conexiones multi-cliente

```javascript
// Frontend
const ws = new WebSocket('ws://localhost:8888/ws/analysis/FA-2025-00001');
ws.onmessage = (e) => {
    const log = JSON.parse(e.data);
    appendLog(log);
};
```

### 3. RBAC Hardening
**Archivos**: `core/rbac_config.py`, `api/middleware/rbac.py`

- 5 niveles de permisos: `mcp:read`, `mcp:write`, `mcp:run-tools`, `mcp:manage-agents`, `mcp:admin`
- 4 roles predefinidos: `viewer`, `analyst`, `operator`, `admin`
- Rate limiting por rol
- Audit logging de operaciones
- IP whitelist para bypass
- Integración con middleware FastAPI

### 4. PostgreSQL Migration Prep
**Archivos**: `migrations/postgresql_prep.py`, `migrations/init_postgresql.sql`

- Schema completo para PostgreSQL
- Soporte para JSONB en campos de metadata
- Particionamiento por fecha
- Índices optimizados para queries forenses
- Utilidades de migración SQLite → PostgreSQL

### 5. Docker Microservices
**Archivos**: `docker-compose.v4.4.1.yml`, `docker/Dockerfile.*`

Nuevos servicios:
- **ws-router**: Enrutador WebSocket escalable
- **llm-provider**: Proxy para LM Studio/Ollama
- **logging-worker**: Agregación de logs
- **executor**: Ejecución sandboxed de herramientas

Configuración de seguridad:
- AppArmor profiles
- Seccomp filters (`docker/seccomp-executor.json`)
- Network isolation
- Read-only filesystems

### 6. OpenTelemetry Integration
**Archivo**: `core/telemetry.py`

- TracerProvider con exportación a Jaeger
- MeterProvider con exportación a Prometheus
- Decoradores para tracing automático
- Métricas de histograma para latencia
- Logging estructurado

```python
from core.telemetry import trace_function, get_meter

@trace_function("analyze_tenant")
async def analyze_tenant(tenant_id: str):
    # Automáticamente traceado
    pass
```

### 7. Frontend Components (React)
**Archivos**: `frontend-react/src/components/`

Nuevos componentes:
- **AnalysisViewer.jsx**: Visor de análisis con tabs (Summary/Logs/Findings/Raw)
- **LiveLogsPanel.jsx**: Panel de logs en tiempo real con filtros
- **EvidenceTree.jsx**: Árbol jerárquico de evidencia
- **AgentActivity.jsx**: Monitor de agentes Blue/Red/Purple

---

## 🔧 Improvements

### Backend
- Refactorización de servicios para soportar case_id obligatorio
- Mejor manejo de errores con contexto
- Logging con emojis para facilitar grep (🔍, ✅, ❌, 🦅)
- Timeouts configurables para herramientas
- Validación de inputs mejorada

### API
- Responses estandarizados con `analysis_id` y `case_id`
- `202 Accepted` para operaciones async
- Health check mejorado con status de dependencias
- Documentación OpenAPI actualizada

### Security
- Rate limiting por IP y API key
- Audit trail de todas las operaciones
- Sanitización de paths de evidencia
- Validación de WebSocket origins

### Performance
- Connection pooling para base de datos
- Caché de configuración RBAC
- Lazy loading de componentes frontend
- Compresión de logs antiguos

---

## 🐛 Bug Fixes

- Fix: Race condition en escritura de evidencia concurrente
- Fix: Memory leak en conexiones WebSocket no cerradas
- Fix: Timeout de PowerShell no respetado en Sparrow
- Fix: Paths relativos en configuración de herramientas
- Fix: Estado de caso no actualizado tras error de herramienta

---

## 📁 New Files

```
/home/hack/mcp-kali-forensics/
├── core/
│   ├── logging_queue.py          # Cola de logs thread-safe
│   ├── rbac_config.py            # Configuración RBAC
│   └── telemetry.py              # OpenTelemetry integration
├── api/
│   ├── middleware/
│   │   └── rbac.py               # Middleware RBAC
│   └── routes/
│       └── ws_streaming.py       # WebSocket endpoints
├── docker/
│   ├── docker-compose.v4.4.1.yml
│   ├── Dockerfile.ws-router
│   ├── Dockerfile.llm-provider
│   ├── Dockerfile.logging-worker
│   ├── Dockerfile.executor
│   ├── ws_router_main.py
│   ├── llm_provider_main.py
│   ├── logging_worker_main.py
│   └── seccomp-executor.json
├── migrations/
│   ├── postgresql_prep.py
│   └── init_postgresql.sql
├── frontend-react/src/components/
│   ├── AnalysisViewer.jsx
│   ├── LiveLogsPanel.jsx
│   ├── EvidenceTree.jsx
│   └── AgentActivity.jsx
├── tests/
│   ├── test_rbac.py
│   ├── test_logging_queue.py
│   └── test_ws_streaming.py
└── docs/v4.4.1/
    ├── BREAKING_CHANGES.md
    ├── CHANGELOG.md
    ├── RBAC_GUIDE.md
    └── STREAMING_ARCHITECTURE.md
```

---

## ⚙️ Configuration Changes

### New Environment Variables
```bash
# RBAC
RBAC_ENABLED=true
RBAC_DEFAULT_ROLE=viewer
RBAC_RATE_LIMIT_ENABLED=true

# WebSocket
WS_HEARTBEAT_INTERVAL=30
WS_MAX_CONNECTIONS=100

# OpenTelemetry
OTEL_ENABLED=true
OTEL_SERVICE_NAME=mcp-forensics
OTEL_EXPORTER_JAEGER_ENDPOINT=http://localhost:14268/api/traces

# PostgreSQL (preparación)
USE_POSTGRESQL=false
DATABASE_URL=postgresql://user:pass@localhost:5432/forensics
```

### Updated config.py
```python
# Nuevos campos en Settings
class Settings(BaseSettings):
    # RBAC
    RBAC_ENABLED: bool = True
    RBAC_DEFAULT_ROLE: str = "viewer"
    
    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_MAX_CONNECTIONS: int = 100
    
    # Telemetry
    OTEL_ENABLED: bool = False
    OTEL_SERVICE_NAME: str = "mcp-forensics"
```

---

## 📊 Database Schema Changes

### Nuevas Tablas (PostgreSQL)
- `forensic_analyses` - Análisis forenses
- `analysis_logs` - Logs de análisis
- `analysis_findings` - Hallazgos
- `analysis_evidence` - Paths de evidencia
- `api_audit_log` - Audit trail
- `rbac_permissions` - Permisos RBAC

### Índices
```sql
CREATE INDEX idx_analyses_case_id ON forensic_analyses(case_id);
CREATE INDEX idx_analyses_status ON forensic_analyses(status);
CREATE INDEX idx_logs_analysis_id ON analysis_logs(analysis_id);
CREATE INDEX idx_audit_timestamp ON api_audit_log(timestamp);
```

---

## 🔄 Migration Guide

Ver [BREAKING_CHANGES.md](./BREAKING_CHANGES.md) para guía completa de migración.

### Quick Migration
```bash
# 1. Backup
cp -r forensics-evidence/ forensics-evidence.backup/
cp forensics.db forensics.db.backup

# 2. Update code
git pull origin main

# 3. Update dependencies
pip install -r requirements.txt

# 4. Migrate evidence structure
./scripts/migrate_evidence_v4.4.1.sh

# 5. Configure environment
cp .env.example .env
# Edit .env with new variables

# 6. Start services
./start.sh
```

---

## 📚 Documentation

- [BREAKING_CHANGES.md](./BREAKING_CHANGES.md) - Cambios incompatibles
- [RBAC_GUIDE.md](./RBAC_GUIDE.md) - Guía de RBAC
- [STREAMING_ARCHITECTURE.md](./STREAMING_ARCHITECTURE.md) - Arquitectura de streaming

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test suites
pytest tests/test_rbac.py -v
pytest tests/test_logging_queue.py -v
pytest tests/test_ws_streaming.py -v
```

---

## 🙏 Contributors

- Architecture & Backend: Development Team
- Frontend Components: UI Team
- Security Review: Security Team
- Documentation: All contributors

---

## 📅 What's Next (v4.5.0 Preview)

- Full PostgreSQL migration
- Kubernetes deployment manifests
- Agent orchestration improvements
- Enhanced reporting engine
- Multi-tenant support

---

**Full Changelog**: v4.3.x...v4.4.1
