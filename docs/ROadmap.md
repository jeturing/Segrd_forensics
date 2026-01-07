# MCP Kali Forensics – Roadmap & Arquitectura v4.4.1

> **Estado**: v4.4.1 (Stable) - December 2025
> **Enfoque**: Enterprise Architecture, Streaming, RBAC, Case-Centric

Documento vivo que describe la arquitectura actual, el estado de los componentes y el roadmap de desarrollo.

## 1) Arquitectura v4.4.1 (Microservicios + Streaming)

La versión 4.4.1 introduce una arquitectura de microservicios orquestada con Docker Compose, centrada en el streaming de datos en tiempo real y seguridad granular.

```
┌─────────────────────────────────────────────────────────────┐
│                   Frontend (React + Vite)                   │
│  - Components: AnalysisViewer, LiveLogsPanel, EvidenceTree  │
│  - WebSocket Client (useAnalysisStream hook)                │
└───────────────▲───────────────────────────▲─────────────────┘
                │ HTTP (REST)               │ WebSocket (Logs)
┌───────────────▼───────────────────────────▼─────────────────┐
│                   API Gateway / WS Router                   │
│  - Sticky Sessions                                          │
│  - Load Balancing                                           │
└───────────────┬───────────────────────────┬─────────────────┘
                │                           │
┌───────────────▼──────────┐      ┌─────────▼──────────────┐
│    MCP Core (FastAPI)    │      │    Logging Worker      │
│  - RBAC Middleware       │      │  - Log Aggregation     │
│  - Case Management       │      │  - Persistence         │
│  - Tool Orchestration    │      │  - Broadcasting        │
└──────┬─────────┬─────────┘      └─────────┬──────────────┘
       │         │                          │
       │         │    ┌─────────────────────┘
       │         ▼    ▼
       │    ┌──────────────┐
       │    │  Redis/PubSub│
       │    └──────────────┘
       │
┌──────▼──────────────────────────────────────────────────────┐
│                     Data Layer                              │
│  - PostgreSQL (Metadata, Analyses, Findings)                │
│  - Filesystem (Evidence Artifacts)                          │
└─────────────────────────────────────────────────────────────┘
```

## 2) Modelo de API y Módulos (Case-Centric)

Todo recurso debe estar asociado a un `case_id`.

- **Core**: `cases` (gestión), `tenants` (M365), `rbac` (permisos).
- **Forensics**: 
  - `m365` (Sparrow, Hawk, O365 Extractor)
  - `endpoint` (Loki, YARA, OSQuery)
  - `credentials` (HIBP, Dehashed)
- **Streaming**: `/ws/analysis/{id}`, `/ws/case/{id}/live`.
- **Observabilidad**: OpenTelemetry (Traces/Metrics).

## 3) Servicios Backend (FastAPI + Core)

- **LoggingQueue** (`core/logging_queue.py`): Cola thread-safe singleton para streaming.
- **RBAC System** (`core/rbac_config.py`): Control de acceso granular (`mcp:read`, `mcp:write`, etc.).
- **Telemetry** (`core/telemetry.py`): trazas distribuidas y métricas Prometheus.
- **Executor Engine**: Ejecución sandboxed de herramientas (Docker/Seccomp).
- **WS Router**: Gestión de conexiones WebSocket y broadcast.

## 4) Modelo de Datos (PostgreSQL Ready)

- **ForensicAnalysis** (`FA-YYYY-XXXXX`):
  - `id`: PK
  - `case_id`: FK -> cases
  - `status`: pending, running, completed, failed
  - `tools_executed`: JSONB
  - `findings`: JSONB
  - `evidence_paths`: JSONB
  - `metadata`: JSONB (telemetry, execution stats)

- **Tablas de Soporte**: `cases`, `audit_logs`, `rbac_permissions`.

## 5) Infraestructura y Despliegue

- **Docker Compose v4.4.1**:
  - `mcp-forensics`: API Principal
  - `ws-router`: Enrutador WebSocket
  - `logging-worker`: Procesamiento de logs
  - `executor`: Ejecución segura
  - `postgres`: Base de datos
  - `redis`: Cola y Pub/Sub
  - `llm-provider`: Gateway AI

- **Seguridad**:
  - AppArmor profiles
  - Seccomp filters (`docker/seccomp-executor.json`)
  - Read-only filesystems donde aplica

## 6) Frontend (React v4.4)

- **Componentes Clave**:
  - `AnalysisViewer`: Tabs para Summary, Logs (Live), Findings, Raw Output.
  - `LiveLogsPanel`: Consola interactiva con filtros y búsqueda.
  - `EvidenceTree`: Explorador de archivos de evidencia.
  - `AgentActivity`: Monitor de agentes Blue/Red/Purple.
- **Hooks**: `useAnalysisStream`, `useCaseEvents`.

## 7) Flujo de Investigación (v4.4.1)

```
1. Crear Caso
   POST /cases -> IR-2025-001

2. Iniciar Análisis
   POST /forensics/m365/analyze
   { "case_id": "IR-2025-001", "scope": ["sparrow"] }
   -> Retorna: FA-2025-00001 (Accepted)

3. Conectar Streaming (Frontend)
   WS /ws/analysis/FA-2025-00001
   <- Recibe logs en tiempo real, status updates, findings

4. Ejecución (Backend)
   Executor -> Docker Sandbox -> Tool (Sparrow)
   Logs -> LoggingQueue -> WS Router -> Client
   Evidence -> Filesystem -> EvidenceTree

5. Finalización
   Status -> Completed
   Findings -> DB
   Report -> Generated
```

## 8) Riesgos y Deuda Técnica

- **Migración de Datos**: La migración de SQLite a PostgreSQL requiere downtime planificado.
- **Documentación Legacy**: Alguna documentación antigua puede referenciar endpoints sin `case_id`.
- **Frontend Legacy**: El dashboard HTML antiguo aún existe pero está deprecated.
- **Testing Coverage**: Aunque se agregaron tests para RBAC y Streaming, la cobertura total debe aumentar.

## 9) Roadmap y Próximos Pasos

### ✅ Completado en v4.4.1
- [x] **Modelado Forense**: `ForensicAnalysis` model y `case_id` obligatorio.
- [x] **Streaming**: WebSocket architecture y `LoggingQueue`.
- [x] **Seguridad**: RBAC Hardening y Rate Limiting.
- [x] **Infraestructura**: Docker Microservices y PostgreSQL prep.
- [x] **Observabilidad**: OpenTelemetry integration.
- [x] **Frontend**: Componentes React para streaming y evidencia.

### 🚀 Próximos Pasos (v4.5.0 - Q1 2026)
1. **Full PostgreSQL Migration**:
   - Ejecutar scripts de migración de datos.
   - Deprecar SQLite completamente.
## 7) Roadmap de Desarrollo (v4.5.0 - v4.7.0)

### 🟡 v4.5.0 - Advanced Visualization & Intelligence (Q1 2026)
Enfoque: UI avanzada para grafos de ataque y optimización de rendimiento.

1.  **Attack Graph UI (Sentinel-like)**:
    - Renderizado WebGL con Cytoscape.js.
    - Nodos dinámicos (User, Host, IP, Process).
    - Relaciones semánticas (Auth, Spawn, Connect).
2.  **Advanced LLM Analysis**:
    - Pipeline de contexto multi-evidencia.
    - Detección de patrones MITRE ATT&CK.
3.  **Logging Optimization**:
    - Compresión Zstd para streaming de logs.
    - Batching adaptativo para alto throughput.

### 🟣 v4.6.0 - AI & Knowledge (Q2 2026)
Enfoque: Inteligencia Artificial contextual y multi-modelo.

1.  **Multi-Model LLM Router**:
    - Enrutamiento de tareas a modelos específicos (phi-4, forensic-xl).
2.  **Forensic RAG**:
    - Base de conocimiento vectorial por caso.
    - Búsqueda semántica sobre evidencias y timeline.

### 🔵 v4.7.0 - Autonomous SOAR (Q3 2026)
Enfoque: Automatización y aprendizaje continuo.

1.  **Adaptive SOAR**:
    - Aprendizaje de outcomes de playbooks.
    - Ajuste dinámico de acciones de respuesta.

## 8) Historial de Versiones

- **v4.4.1 (Dec 2025)**: Architecture Upgrade, Streaming, RBAC, Microservices.
- **v4.3**: Mejoras de estabilidad y bugfixes.
- **v4.2**: Reorganización de documentación y Plotly charts.
- **v4.1**: Release inicial estable.

---

**Documento Maestro**: Mantener actualizado con cada cambio arquitectónico mayor.

