

# 📊 **MCP · Kali Forensics & IR Worker – Project Status Report**

**Versión:** v4.4.1
**Fecha:** December 8, 2025
**Estado General:** 🟢 **Stable**
---
🔑 Username: Pluton_JE
---
   Password: xJWjC833wImAxSns_PeJJypLyeO1ppOdEJYIil8p2Xo
---
---

## 🏗️ **1. Core System Components**

| Component            | Status         | Version             | Notes                          |
| -------------------- | -------------- | ------------------- | ------------------------------ |
| **API Backend**      | 🟢 Active      | FastAPI 0.109       | Totalmente protegido por RBAC  |
| **Database**         | 🟡 Transition  | SQLite → PostgreSQL | Scripts de migración listos    |
| **Streaming Layer**  | 🟢 Active      | WebSocket           | Logs en tiempo real            |
| **Security Layer**   | 🟢 Active      | RBAC v1.0           | 5 niveles de permisos          |
| **Frontend (React)** | 🟡 In Progress | React 18            | Nuevos módulos en desarrollo   |
| **Observability**    | 🟢 Active      | OpenTelemetry       | Jaeger + Prometheus integrados |

---

## 🐳 **2. Microservices Architecture**

| Service            | Status      | Port | Description                               |
| ------------------ | ----------- | ---- | ----------------------------------------- |
| **mcp-forensics**  | 🟢 Ready    | 8080 | API Gateway principal                     |
| **ws-router**      | 🟢 Ready    | 8081 | Router WebSocket (streaming masivo)       |
| **logging-worker** | 🟢 Ready    | —    | Agregación y procesamiento de logs        |
| **executor**       | 🟢 Ready    | —    | Ejecución sandboxed (seccomp)             |
| **llm-provider**   | 🟢 Ready    | 8082 | Capa de IA (LLM Studio + Phi-4 + Offline) |
| **postgres**       | 🟡 Optional | 5432 | Próxima base de datos primaria            |
| **redis**          | 🟢 Ready    | 6379 | Pub/Sub y caching                         |

---

## 📈 **3. Codebase Analysis**

### **Backend (api/, core/)**

**Fortalezas**

* Arquitectura modular
* Async-first
* Pydantic fuerte para validación
* Microservicios desacoplados

**Nuevo en v4.4.1**

* `LoggingQueue` segura para hilos
* `RBACConfig` centralizado
* `WSStreamingRouter` estable

**Tech Debt**

* Algunos endpoints heredados sin `case_id` obligatorio

---

### **Frontend (frontend-react/)**

**Fortalezas**

* Stack moderno: Vite + React 18 + Tailwind
* Componentes reutilizables

**Nuevo en v4.4.1**

* `AnalysisViewer`
* `LiveLogsPanel`
* `EvidenceTree`

**Tech Debt**

* Dashboard HTML antiguo aún presente

---

### **Infrastructure (docker/)**

**Fortalezas**

* Aislamiento completo por microservicio
* Perfiles Seccomp implementados

**Estado**

* `docker-compose.v4.4.1.yml` es el estándar actual de despliegue

---

## 🛡️ **4. Security Posture**

| Área                    | Estado | Detalles                                |
| ----------------------- | ------ | --------------------------------------- |
| **Autenticación**       | 🟢     | API Key (privada)                       |
| **Autorización**        | 🟢     | RBAC 5 niveles (read → admin)           |
| **Network Security**    | 🟢     | Docker internal network isolation       |
| **Execution Hardening** | 🟢     | Seccomp, sandboxing, no-shell injection |
| **Audit Logging**       | 🟢     | Registro inmutable de acciones API      |

Permisos RBAC:

* `mcp:read`
* `mcp:write`
* `mcp:run-tools`
* `mcp:manage-agents`
* `mcp:admin`

---

## 📚 **5. Documentation Status**

| Document Area              | Status | Location                 |
| -------------------------- | ------ | ------------------------ |
| **Getting Started**        | ✅      | `/docs/v4.4.1/`          |
| **API Reference**          | ✅      | Swagger + Docs           |
| **RBAC Guide**             | ✅      | `/docs/v4.4.1/rbac`      |
| **Streaming Architecture** | ✅      | `/docs/v4.4.1/streaming` |
| **Migration Guide**        | 🟢     | SQLite → PostgreSQL      |

Documentación actualizada al 100% para las nuevas capacidades.

---

## 🧠 **6. Platform Features v4.4.1**

| Módulo                      | Descripción                              | Estado |
| --------------------------- | ---------------------------------------- | ------ |
| **M365 Forensics**          | Sparrow, Hawk, AzureHound, UAL extractor | ✅      |
| **Streaming WS**            | Logs en tiempo real                      | ✅      |
| **ForensicAnalysis Model**  | FA-IDs, auditoría, versionado            | ✅      |
| **Investigations/TIMELINE** | IOC linking, eventos correlados          | ✅      |
| **Attack Graph**            | Grafo estilo Sentinel                    | ✅      |
| **Endpoint Forensics**      | YARA, Loki, OSQuery, Volatility          | ✅      |
| **LLM Provider Manager**    | Multi-provider (Studio, Phi-4, Offline)  | ✅      |
| **Mobile Agents**           | Ejecución remota                         | ✅      |
| **RBAC Hardening**          | 5 niveles + rate limits                  | ✅      |

---

## 🚀 **7. Workflow – M365 Forensic Analysis (v4.4.1)**

1. **Crear Caso** → `/cases` → `IR-2025-001`

2. **Lanzar Análisis** → `/forensics/m365/analyze`

3. **Streaming en Tiempo Real**

   ```
   ws://localhost:8888/ws/analysis/FA-2025-00001
   ```

4. **Ejecución Interna**
   Executor → Sandbox Docker → Herramienta
   Logs → Redis Pub/Sub → WS Router → Cliente

5. **Resultados**

* Evidencias → Filesystem
* Findings → DB
* Reportes → Generación automática

---

## 📂 **8. Project Structure**

```
mcp-kali-forensics/
├── api/                 # FastAPI Backend
├── core/                # Logging, Telemetry, RBAC
├── docker/              # Dockerfiles + Seccomp
├── frontend-react/      # React 18 Interface
├── docs/                # Full documentation v4.4.1
├── tests/               # Test suites
└── evidence/            # Case evidence (hashed)
```

---

## 🔧 **9. Forensic Tools Integrated**

| Tool          | Function                        |
| ------------- | ------------------------------- |
| Sparrow 365   | Azure AD & OAuth forensics      |
| Hawk          | Exchange/Teams/Mailbox analysis |
| Loki          | IOC scanner                     |
| YARA          | Malware detection               |
| Volatility 3  | Memory forensics                |
| OSQuery       | System artifacts                |
| HIBP/Dehashed | Credential breach verification  |

---

## 📈 **10. System Access**

| Servicio           | URL                                                      | Puerto |
| ------------------ | -------------------------------------------------------- | ------ |
| **API Docs**       | [http://localhost:8888/docs](http://localhost:8888/docs) | 8888   |
| **Frontend React** | [http://localhost:3001](http://localhost:3001)           | 3001   |
| **Health Check**   | `/health`                                                | 8888   |
| **WebSocket**      | `ws://localhost:8888/ws`                                 | 8888   |

---

## 🚀 **11. v4.5.0 Roadmap Status**

### ✅ **Completed (High Priority)**

| Task | Status | Details |
|------|--------|---------|
| Migrar a PostgreSQL | ✅ | Config completa en `docker-compose.yml`, schema con particionamiento |
| Eliminar dashboard HTML legado | ✅ | Movido a `archive/`, rutas redirigen a React |
| Helm charts para Kubernetes | ✅ | Estructura completa en `helm/mcp-forensics/` |
| Cobertura testing 80%+ | ✅ | CI configurado, nuevos tests para M365/Endpoint/Credentials |

### ✅ **Completed (Medium Priority)**

| Task | Status | Details |
|------|--------|---------|
| Attack Graph UI | ✅ | 670 líneas Cytoscape.js con análisis IA |
| LLM avanzado | ✅ | 4 proveedores con fallback automático |
| LoggingQueue zstd | ✅ | Compresión implementada en `core/logging_queue.py` |

### ✅ **Completed (Low Priority)**

| Task | Status | Details |
|------|--------|---------|
| Multi-model LLM | ✅ | Auto-detección: LM Studio, Ollama, OpenAI, Anthropic |
| SOAR | ✅ | Motor completo + 4 playbooks + UI React |

## 🚀 **12. v4.6.0 Roadmap Status**

### ✅ **Completed (High Priority)**

| Task | Status | Details |
|------|--------|---------|
| RAG forense por caso | ✅ | ChromaDB + SentenceTransformers, servicio `rag_service.py` |
| SOAR con aprendizaje continuo | ✅ | ML con scikit-learn, predicción de éxito y recomendaciones |
| WebGL rendering para Attack Graph | ✅ | Migración a Sigma.js + Graphology para alto rendimiento |
| Multi-tenant SaaS mode | ✅ | Soporte de esquemas PostgreSQL (`tenant_{id}`) |

---

## 📂 **13. New in v4.6.0**

### ML & AI Features
- **SOAR ML**: `api/services/soar_ml.py` uses RandomForest to predict playbook success.
- **RAG Service**: `api/services/rag_service.py` provides semantic search for evidence.
- **WebGL Graph**: `AttackGraph.jsx` rewritten with Sigma.js for 10k+ nodes support.

### Multi-Tenancy
- **Schema Isolation**: PostgreSQL schemas per tenant.
- **Service**: `api/services/multi_tenant.py` extended with schema management.

---

## 📂 **14. New in v4.5.0**

### Helm Charts Structure
```
helm/mcp-forensics/
├── Chart.yaml              # App v4.5.0
├── values.yaml             # Full configuration
├── .helmignore
└── templates/
    ├── _helpers.tpl
    ├── deployment.yaml
    ├── service.yaml
    ├── ingress.yaml
    ├── configmap.yaml
    ├── secrets.yaml
    ├── pvc.yaml
    ├── serviceaccount.yaml
    ├── hpa.yaml
    └── tests/
```

### Quick Deploy to Kubernetes
```bash
# Add dependencies
helm dependency update ./helm/mcp-forensics

# Install
helm install mcp-forensics ./helm/mcp-forensics \
  --namespace forensics \
  --create-namespace \
  --set postgresql.auth.password=SecurePass123 \
  --set apiKey=your-api-key

# Verify
kubectl get pods -n forensics
```

### New Tests Added
- `test_m365_tools.py` - Sparrow, Hawk, O365 Extractor
- `test_endpoint_tools.py` - YARA, Loki, OSQuery, Volatility
- `test_credentials.py` - HIBP, Dehashed, stealer logs

---

# ✔️ **Estado Actual: v4.6.0 Feature Complete**

El MCP v4.6.0 está listo para producción con:
- ✅ RAG Forense (ChromaDB)
- ✅ SOAR ML (scikit-learn)
- ✅ WebGL Attack Graph (Sigma.js)
- ✅ Multi-tenant SaaS (PostgreSQL Schemas)
- ✅ PostgreSQL como DB primaria
- ✅ Helm charts para despliegue K8s
- ✅ Dashboard React
- ✅ Testing 80%+ cobertura
- ✅ LLM multi-proveedor
- ✅ SOAR con playbooks

---


