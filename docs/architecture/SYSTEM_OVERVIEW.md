# 🏗️ MCP v4.1 - Arquitectura del Sistema

## Visión General

MCP Kali Forensics v4.1 es una plataforma de respuesta a incidentes (DFIR) y seguridad ofensiva/defensiva que integra:

- **Ejecutor Híbrido**: Ejecución de herramientas localmente (MCP) o en agentes remotos
- **SOAR Engine**: Orquestación y automatización de playbooks
- **Correlation Engine**: Detección basada en Sigma rules y ML
- **Graph Engine**: Visualización y enriquecimiento de attack graphs
- **Agent Manager**: Gestión de agentes Red/Blue/Purple

---

## 📊 Diagrama de Arquitectura

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MCP KALI FORENSICS v4.1                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│  │   React     │    │   FastAPI   │    │   SQLite    │    │  Evidence   │ │
│  │  Frontend   │◄──►│   Backend   │◄──►│  Database   │    │   Storage   │ │
│  └─────────────┘    └──────┬──────┘    └─────────────┘    └─────────────┘ │
│         │                  │                                      ▲        │
│         │ WebSocket        │                                      │        │
│         ▼                  ▼                                      │        │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                         SERVICE LAYER                               │  │
│  ├─────────────┬─────────────┬─────────────┬─────────────┬────────────┤  │
│  │  Executor   │    SOAR     │ Correlation │   Graph     │   Agent    │  │
│  │   Engine    │   Engine    │   Engine    │  Enricher   │  Manager   │  │
│  └──────┬──────┴──────┬──────┴──────┬──────┴──────┬──────┴─────┬──────┘  │
│         │             │             │             │            │         │
│         ▼             ▼             ▼             ▼            ▼         │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                        TOOL LAYER                                   │  │
│  ├─────────────┬─────────────┬─────────────┬─────────────┬────────────┤  │
│  │    Kali     │    M365     │    YARA     │   Graph     │   Agent    │  │
│  │   Tools     │   Graph     │    Loki     │    APIs     │   Comm     │  │
│  └──────┬──────┴──────┬──────┴──────┬──────┴──────┬──────┴─────┬──────┘  │
│         │             │             │             │            │         │
└─────────┼─────────────┼─────────────┼─────────────┼────────────┼─────────┘
          │             │             │             │            │
          ▼             ▼             ▼             ▼            ▼
    ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐
    │   Kali    │ │ Microsoft │ │  Threat   │ │  Attack   │ │  Remote   │
    │   Linux   │ │   Cloud   │ │   Intel   │ │   Graph   │ │  Agents   │
    └───────────┘ └───────────┘ └───────────┘ └───────────┘ └───────────┘
```

---

## 🔧 Componentes Principales

### 1. FastAPI Backend

**Ubicación**: `api/`

**Responsabilidades**:
- API REST para todas las operaciones
- WebSocket para streaming en tiempo real
- Autenticación y autorización
- Gestión de casos e investigaciones

**Endpoints Principales**:
| Prefijo | Descripción |
|---------|-------------|
| `/api/cases` | Gestión de casos |
| `/api/investigations` | Investigaciones activas |
| `/api/agents` | Gestión de agentes |
| `/v41/tools` | Ejecución de herramientas v4.1 |
| `/v41/playbooks` | SOAR playbooks |
| `/v41/correlation` | Correlation engine |
| `/ws/` | WebSocket channels |

### 2. Executor Engine

**Ubicación**: `api/services/executor_engine.py`

**Responsabilidades**:
- Validación y sanitización de comandos
- Ejecución segura en sandbox
- Streaming de output en tiempo real
- Auditoría de ejecuciones

**Flujo de Ejecución**:
```
Request → Validate → Sandbox → Execute → Stream → Store → Return
```

### 3. SOAR Engine

**Ubicación**: `api/services/soar_engine.py`

**Responsabilidades**:
- Ejecutar playbooks Red/Blue/Purple
- Gestionar triggers y condiciones
- Orquestar pasos de playbooks
- Integrar con otros motores

**Playbooks Soportados**:
- RED-01 a RED-05: Reconocimiento y evaluación
- BLUE-01 a BLUE-07: Respuesta a incidentes
- PURPLE-01 a PURPLE-05: Coordinación y validación

### 4. Correlation Engine

**Ubicación**: `api/services/correlation_engine.py`

**Responsabilidades**:
- Matching de reglas Sigma
- Detección de anomalías con ML
- Generación de alertas
- Correlación de eventos

**Métodos de Detección**:
| Método | Descripción |
|--------|-------------|
| Sigma Rules | Reglas declarativas YAML |
| ML Heuristics | Isolation Forest, clustering |
| Pattern Matching | Regex, secuencias |
| Threshold | Conteo de eventos |

### 5. Graph Enricher

**Ubicación**: `api/services/graph_enricher.py`

**Responsabilidades**:
- Extracción automática de entidades
- Creación de nodos y aristas
- Enriquecimiento con Threat Intel
- Cálculo de rutas de ataque

**Tipos de Nodos**:
- IP, Domain, URL, Email
- User, Host, Process
- File, Hash, Registry
- Malware, CVE, Threat Actor

### 6. Agent Manager

**Ubicación**: `api/services/agent_manager.py`

**Responsabilidades**:
- Registro de agentes
- Autenticación y heartbeat
- Asignación de tareas
- Telemetría y métricas

**Tipos de Agentes**:
| Tipo | Color | Rol |
|------|-------|-----|
| `red` | 🔴 | Ofensivo (recon, assessment) |
| `blue` | 🔵 | Defensivo (DFIR, containment) |
| `purple` | 🟣 | Coordinación (validation) |
| `generic` | ⚪ | Propósito general |

---

## 📁 Estructura de Directorios

```
mcp-kali-forensics/
├── api/
│   ├── main.py                 # FastAPI application
│   ├── config.py               # Configuración
│   ├── database.py             # SQLAlchemy setup
│   ├── middleware/
│   │   └── auth.py             # Autenticación
│   ├── models/
│   │   ├── case.py             # Modelo de casos
│   │   ├── investigation.py    # Investigaciones
│   │   ├── ioc.py              # IOCs
│   │   └── tools.py            # Modelos v4.1
│   ├── routes/
│   │   ├── cases.py
│   │   ├── investigations.py
│   │   ├── agents.py
│   │   ├── tools_v41.py
│   │   ├── playbooks.py
│   │   └── correlation.py
│   └── services/
│       ├── executor_engine.py
│       ├── soar_engine.py
│       ├── correlation_engine.py
│       ├── graph_enricher.py
│       ├── agent_manager.py
│       └── dashboard_data.py
├── docs/
│   ├── architecture/
│   ├── agents/
│   ├── playbooks/
│   └── api/
├── frontend-react/
│   └── src/
│       ├── components/
│       ├── pages/
│       └── services/
├── scripts/
│   ├── setup_native.sh
│   └── install.sh
├── migrations/
│   └── v4.1_schema.sql
└── evidence/                   # Almacenamiento de evidencia
```

---

## 🔄 Flujos de Datos

### Flujo de Investigación

```
1. Alerta/Trigger
       │
       ▼
2. Crear Caso ───────────► SQLite (cases)
       │
       ▼
3. SOAR evalúa triggers
       │
       ▼
4. Ejecutar Playbook
       │
       ├──► Executor Engine ──► Tools ──► Output
       │
       ▼
5. Correlation Engine procesa eventos
       │
       ▼
6. Graph Enricher crea nodos/aristas
       │
       ▼
7. Actualizar Timeline
       │
       ▼
8. Notificar via WebSocket
```

### Flujo de Ejecución de Herramientas

```
1. POST /v41/tools/execute
       │
       ▼
2. Validar parámetros
       │
       ├── ✗ Error → 400 Bad Request
       │
       ▼
3. Verificar permisos
       │
       ├── ✗ Error → 403 Forbidden
       │
       ▼
4. Crear registro de ejecución
       │
       ▼
5. ¿Dónde ejecutar?
       │
       ├── mcp_local ──► Sandbox local
       │
       └── agent_remote ──► Agent Task Queue
       │
       ▼
6. Ejecutar comando
       │
       ├──► Stream output via WebSocket
       │
       ▼
7. Procesar output
       │
       ├──► Extraer IOCs ──► Graph Enricher
       │
       ▼
8. Actualizar estado
       │
       ▼
9. Almacenar evidencia
```

---

## 🔐 Modelo de Seguridad

### Capas de Seguridad

1. **Autenticación**
   - API Key para llamadas REST
   - Token JWT para sesiones
   - Certificados para agentes

2. **Autorización (RBAC)**
   - `ADMIN`: Acceso total
   - `IR_LEAD`: Gestión de casos, aprobaciones
   - `ANALYST`: Investigación, ejecución de herramientas
   - `RED_OPERATOR`: Herramientas ofensivas (aprobadas)
   - `BLUE_OPERATOR`: Herramientas defensivas
   - `PURPLE_OPERATOR`: Validación y coordinación
   - `VIEWER`: Solo lectura

3. **Validación de Comandos**
   - Blacklist de patrones peligrosos
   - Whitelist de herramientas permitidas
   - Sanitización de parámetros

4. **Sandbox de Ejecución**
   - Límites de tiempo
   - Límites de recursos
   - Aislamiento de filesystem

5. **Auditoría**
   - Log de todas las acciones
   - Chain of custody para evidencia
   - Trazabilidad completa

---

## 📊 Base de Datos

### Esquema Principal

```sql
-- Casos
CREATE TABLE cases (
    id TEXT PRIMARY KEY,
    title TEXT,
    status TEXT,
    priority TEXT,
    created_at TIMESTAMP,
    ...
);

-- IOCs
CREATE TABLE iocs (
    id TEXT PRIMARY KEY,
    case_id TEXT REFERENCES cases(id),
    type TEXT,
    value TEXT,
    severity TEXT,
    ...
);

-- Ejecuciones de herramientas (v4.1)
CREATE TABLE tool_executions (
    id TEXT PRIMARY KEY,
    tool TEXT,
    category TEXT,
    parameters JSON,
    execution_target TEXT,
    status TEXT,
    ...
);

-- Agentes (v4.1)
CREATE TABLE agents (
    id TEXT PRIMARY KEY,
    name TEXT,
    agent_type TEXT,
    status TEXT,
    capabilities JSON,
    ...
);

-- Playbooks (v4.1)
CREATE TABLE playbooks (
    id TEXT PRIMARY KEY,
    name TEXT,
    team_type TEXT,
    steps JSON,
    ...
);

-- Correlation Rules (v4.1)
CREATE TABLE correlation_rules (
    id TEXT PRIMARY KEY,
    rule_type TEXT,
    definition JSON,
    severity TEXT,
    ...
);

-- Graph Nodes (v4.1)
CREATE TABLE graph_nodes (
    id TEXT PRIMARY KEY,
    case_id TEXT,
    node_type TEXT,
    value TEXT,
    metadata JSON,
    ...
);
```

---

## 🌐 WebSocket Channels

| Channel | Descripción |
|---------|-------------|
| `ws/tools/{execution_id}` | Stream de ejecución |
| `ws/agents/{agent_id}` | Updates de agente |
| `ws/cases/{case_id}` | Updates de caso |
| `ws/correlation/alerts` | Alertas en tiempo real |
| `ws/graph/{case_id}` | Cambios en grafo |

---

## 🔗 Integraciones Externas

| Servicio | Propósito | API |
|----------|-----------|-----|
| Microsoft Graph | M365 forensics | REST |
| Azure AD | Sign-in logs | REST |
| HIBP | Credential checks | REST |
| VirusTotal | IOC enrichment | REST |
| Jeturing CORE | Orquestación | REST |

---

## 📈 Métricas y Observabilidad

### Métricas Disponibles
- Casos activos/cerrados
- Ejecuciones por herramienta
- IOCs detectados
- Tiempo de respuesta
- Tasa de detección

### Telemetría (OTel compatible)
```json
{
  "service": "mcp-forensics",
  "version": "4.1",
  "metrics": {
    "cases_active": 15,
    "tool_executions_24h": 234,
    "iocs_detected_24h": 89,
    "agents_online": 5,
    "avg_response_time_ms": 1250
  }
}
```

---

**Versión**: 4.1  
**Última actualización**: 2025-12-05
