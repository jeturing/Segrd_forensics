# Changelog v4.4 - Case-Centric Architecture

## [4.4.0] - 2025-01

### 🎯 Filosofía de Diseño

> **"TODO en MCP debe estar asociado SIEMPRE a un CASE_ID"**

Esta versión implementa una arquitectura donde cada operación forense está obligatoriamente vinculada a un caso de investigación.

---

### ✨ Nuevas Características

#### Core
- **CaseContextManager** (`/core/context_manager.py`)
  - Singleton para gestión centralizada del contexto de caso
  - Cache de sesiones y casos
  - Validación de casos activos
  - Métodos: `set_context()`, `get_context()`, `require_context()`

- **ProcessManager** (`/core/process_manager.py`)
  - Gestión de procesos persistentes con SQLite
  - Procesos sobreviven a reinicios del servidor
  - Recuperación automática al startup
  - Tracking de progreso, estado y resultados

- **CaseContextMiddleware** (`/api/middleware/case_context.py`)
  - Intercepta requests a rutas protegidas
  - Valida presencia de `case_id` en query/body
  - Logging de contexto de caso

#### Frontend
- **CaseContextProvider** (`/frontend-react/src/context/CaseContext.jsx`)
  - Context global de React para caso activo
  - Persistencia en localStorage
  - Sincronización con backend
  - Hook `useCaseContext()` para acceso fácil

- **CaseHeader** (`/frontend-react/src/components/CaseHeader.jsx`)
  - Componente de header con selector de caso
  - Muestra caso activo en todas las páginas
  - Dropdown para cambiar caso rápidamente

- **CaseSelector** (integrado en CaseContext)
  - Pantalla de selección/creación de caso
  - Se muestra automáticamente cuando no hay caso

---

### 🔄 Cambios en Endpoints

#### Investigación Activa
| Endpoint | Cambio |
|----------|--------|
| `POST /active-investigation/execute` | `case_id` ahora OBLIGATORIO |
| `POST /network-capture/start` | `case_id` ahora OBLIGATORIO |
| `POST /memory-dump/request` | `case_id` ahora OBLIGATORIO |
| `GET /command-history/{agent_id}` | `case_id` query param OBLIGATORIO |
| `POST /file-upload/{agent_id}` | `case_id` query param OBLIGATORIO |
| `GET /file-download/{agent_id}` | `case_id` query param OBLIGATORIO |

#### Nuevos Endpoints
| Endpoint | Descripción |
|----------|-------------|
| `GET /active-investigation/results/{case_id}` | Resultados por caso |
| `GET /active-investigation/stats/{case_id}` | Estadísticas por caso |
| `GET /api/context/current` | Contexto de caso actual |
| `POST /api/context/set` | Establecer caso activo |
| `GET /api/processes` | Listar procesos activos |

---

### 📦 Componentes Actualizados

#### Backend Services
- `api/services/hunting.py` - `case_id` obligatorio en `execute_hunt()`
- `api/services/timeline.py` - Header v4.4
- `api/services/reports.py` - Header v4.4
- `api/services/agent_manager.py` - `case_id` en `assign_task()`

#### Backend Routes
- `api/routes/hunting.py` - Pasa `case_id` a servicios
- `api/routes/active_investigation.py` - Todos los endpoints actualizados

#### Frontend Pages
- `ThreatHuntingPage.jsx` - Usa `useCaseContext()`, muestra `CaseHeader`
- `TimelinePage.jsx` - Usa `useCaseContext()`, muestra `CaseHeader`
- `ReportsPage.jsx` - Usa `useCaseContext()`, muestra `CaseHeader`
- `App.jsx` - Envuelve todo con `CaseContextProvider`

---

### ⚠️ Breaking Changes

1. **API**: `case_id` es ahora obligatorio en:
   - `/hunting/execute`
   - `/hunting/execute/custom`
   - `/active-investigation/execute`
   - `/active-investigation/network-capture/start`
   - `/active-investigation/memory-dump/request`
   - `/active-investigation/command-history/*`
   - `/active-investigation/file-upload/*`
   - `/active-investigation/file-download/*`

2. **Frontend**: Componentes deben estar bajo `CaseContextProvider`

3. **Estado Local**: Ya no se usa `useState('IR-2025-001')` hardcodeado

---

### 🗄️ Nueva Base de Datos

**Archivo**: `forensics_processes.db`

```sql
CREATE TABLE forensics_processes (
    process_id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    process_type TEXT NOT NULL,
    status TEXT DEFAULT 'running',
    progress INTEGER DEFAULT 0,
    description TEXT,
    started_at TEXT,
    updated_at TEXT,
    completed_at TEXT,
    result TEXT,
    error TEXT
);
```

---

### 📝 Guía de Migración

#### Backend
```python
# Antes (v4.3)
async def execute_hunt(hunt_id: str, case_id: Optional[str] = None):
    ...

# Después (v4.4)
async def execute_hunt(hunt_id: str, case_id: str):  # Obligatorio
    ...
```

#### Frontend
```jsx
// Antes (v4.3)
const [caseId] = useState('IR-2025-001');

// Después (v4.4)
const { getCaseId, hasActiveCase } = useCaseContext();

if (!hasActiveCase()) {
  return <CaseSelector />;
}

const caseId = getCaseId();
```

---

### 🔮 Próximos Pasos (v4.5)

1. **Tenants Funcionales** - Health checks y token management
2. **Agentes LLM** - Integración completa con LM Studio
3. **Dashboard Unificado** - Vista de todos los casos activos
4. **Notificaciones** - Alertas cuando procesos completan

---

### 📚 Documentación

- `/docs/V4.4_CASE_CENTRIC_ARCHITECTURE.md` - Arquitectura completa
- `/docs/API.md` - Endpoints actualizados (pendiente)
- `/.github/copilot-instructions.md` - Instrucciones actualizadas

---

**Fecha de Release**: 2025-01  
**Compatibilidad**: Python 3.11+, Node 18+, React 18+
