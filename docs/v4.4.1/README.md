# 📦 v4.4.1 Documentation

> **Release**: Platform Architecture Upgrade + Case-Centric + Analysis Model + Streaming Layer  
> **Date**: December 2025

---

## 📋 Documentos

| Documento | Descripción | Estado |
|-----------|-------------|--------|
| [CHANGELOG.md](./CHANGELOG.md) | Lista completa de cambios y nuevas features | ✅ Completa |
| [BREAKING_CHANGES.md](./BREAKING_CHANGES.md) | Cambios incompatibles y guía de migración | ✅ Completa |
| [RBAC_GUIDE.md](./RBAC_GUIDE.md) | Guía de permisos, roles y rate limiting | ✅ Completa |
| [STREAMING_ARCHITECTURE.md](./STREAMING_ARCHITECTURE.md) | WebSocket streaming y logs en tiempo real | ✅ Completa |

---

## 🎯 Highlights

### Case-Centric Architecture
Todo debe estar asociado a un `case_id`:
```python
POST /forensics/m365/analyze
{
    "case_id": "IR-2025-001",  # OBLIGATORIO
    "tenant_id": "xxx",
    "scope": ["sparrow"]
}
```

### RBAC Hardening
5 niveles de permisos:
- `mcp:read` - Lectura de casos y análisis
- `mcp:write` - Crear/modificar casos
- `mcp:run-tools` - Ejecutar herramientas forenses
- `mcp:manage-agents` - Gestionar agentes Blue/Red/Purple
- `mcp:admin` - Acceso total

### WebSocket Streaming
Logs en tiempo real:
```javascript
const ws = new WebSocket('ws://localhost:8888/ws/analysis/FA-2025-00001');
ws.onmessage = (e) => console.log(JSON.parse(e.data));
```

### ForensicAnalysis Model
Nuevo modelo con ID formato `FA-YYYY-XXXXX`:
```json
{
    "id": "FA-2025-00001",
    "case_id": "IR-2025-001",
    "analysis_type": "m365_compromise",
    "status": "running",
    "tools_executed": ["sparrow", "hawk"]
}
```

### OpenTelemetry
Observabilidad completa:
- Traces → Jaeger
- Metrics → Prometheus
- Structured Logging

### Docker Microservices
Nuevos servicios:
- `ws-router` - WebSocket escalable
- `llm-provider` - Proxy LLM
- `logging-worker` - Agregación de logs
- `executor` - Ejecución sandboxed

---

## 🔄 Migración

Ver [BREAKING_CHANGES.md](./BREAKING_CHANGES.md) para guía completa.

### Quick Migration
```bash
# 1. Backup
cp -r forensics-evidence/ forensics-evidence.backup/

# 2. Update
git pull origin main
pip install -r requirements.txt

# 3. Configure
cp .env.example .env
# Edit with new RBAC variables

# 4. Start
./start.sh
```

---

## 📁 Nuevos Archivos v4.4.1

```
/home/hack/mcp-kali-forensics/
├── core/
│   ├── logging_queue.py          # Cola de logs
│   ├── rbac_config.py            # Configuración RBAC
│   └── telemetry.py              # OpenTelemetry
├── api/
│   ├── middleware/rbac.py        # Middleware RBAC
│   └── routes/ws_streaming.py    # WebSocket endpoints
├── docker/
│   ├── docker-compose.v4.4.1.yml
│   ├── Dockerfile.ws-router
│   ├── Dockerfile.llm-provider
│   ├── Dockerfile.logging-worker
│   └── Dockerfile.executor
├── migrations/
│   ├── postgresql_prep.py
│   └── init_postgresql.sql
├── frontend-react/src/components/
│   ├── AnalysisViewer.jsx
│   ├── LiveLogsPanel.jsx
│   ├── EvidenceTree.jsx
│   └── AgentActivity.jsx
└── tests/
    ├── test_rbac.py
    ├── test_logging_queue.py
    └── test_ws_streaming.py
```

---

## 🧪 Testing

```bash
# All tests
pytest tests/ -v

# Specific suites
pytest tests/test_rbac.py -v
pytest tests/test_logging_queue.py -v
pytest tests/test_ws_streaming.py -v
```

---

## 📚 Referencias

- [Main README](../README.md)
- [Backend API](../backend/API.md)
- [Frontend Guide](../frontend/)
- [Deployment](../deployment/)

---

**Última actualización**: December 2025
