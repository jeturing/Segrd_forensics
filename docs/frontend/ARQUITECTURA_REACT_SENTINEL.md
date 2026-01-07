# 🏗️ ARQUITECTURA REACT: ESTRUCTURA MODULAR TIPO SENTINEL

**Fecha**: 2025-12-05  
**Versión**: 2.0  
**Objetivo**: Diseño completo de UI/UX similar a Microsoft Sentinel  

---

## 📊 ANÁLISIS COMPARATIVO: UI/UX ACTUAL vs PROPUESTA

### ❌ ACTUAL (Dashboard HTML puro)

```
Dashboard.html
├─ HTML inline
├─ CSS global
├─ JavaScript vanilla
├─ Sin componentes reutilizables
├─ Sin estado global (Redux)
├─ Difícil de mantener
├─ Escalabilidad baja
└─ UX poco profesional
```

**Problemas**:
- 🔴 Un solo archivo gigante (4871 líneas)
- 🔴 Duplicación de código
- 🔴 Difícil agregar nuevas funcionalidades
- 🔴 Sin validación en línea real-time
- 🔴 Interfaz poco intuitiva

---

### ✅ PROPUESTA (React Modular)

```
MCP Forensics React App
├─ Componentes reutilizables
├─ Estado global (Redux/Context)
├─ Validación real-time
├─ Menú modular estilo Sentinel
├─ Iconografía clara
├─ Responsive design
├─ Testing automatizado
└─ UX profesional
```

**Beneficios**:
- 🟢 Componentes independientes
- 🟢 Fácil de mantener
- 🟢 Escalable
- 🟢 UX moderna
- 🟢 Performance optimizado

---

## 🎨 ESTRUCTURA VISUAL: SENTINEL STYLE

```
┌─────────────────────────────────────────────────────────────┐
│  MCP Kali Forensics & IR                    🔔 👤 ⚙️       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ☰ MENU LATERAL                   │ CONTENIDO PRINCIPAL    │
│  ┌───────────────────┐            │ ┌───────────────────┐  │
│  │                   │            │ │                   │  │
│  │ 🏠 Dashboard      │            │ │  Dashboard        │  │
│  │                   │            │ │  ┌─────────────┐  │  │
│  │ 🔍 Investigación  │            │ │  │ 🔴 Crítico  │  │  │
│  │  ├─ Casos         │            │ │  │    5 casos  │  │  │
│  │  ├─ Nuevo caso    │            │ │  ├─────────────┤  │  │
│  │  └─ En progreso   │            │ │  │🟠 Alto     │  │  │
│  │                   │            │ │  │   12 casos  │  │  │
│  │ 🎯 Threat Hunting │            │ │  ├─────────────┤  │  │
│  │  ├─ Búsquedas     │            │ │  │🟡 Medio    │  │  │
│  │  └─ Auto-hunts    │            │ │  │   8 casos   │  │  │
│  │                   │            │ │  └─────────────┘  │  │
│  │ 🔌 Mobile Agents  │            │ │                   │  │
│  │  ├─ Dispositivos  │            │ │ Actividad Reciente│  │
│  │  └─ Recolecciones │            │ │ ┌─────────────┐  │  │
│  │                   │            │ │ │ 🔍 IR-2025- │  │  │
│  │ ⚙️ Inteligencia   │            │ │ │    001 en   │  │  │
│  │  ├─ IOCs          │            │ │ │    progreso │  │  │
│  │  └─ Reglas        │            │ │ │ 🔍 IR-2025- │  │  │
│  │                   │            │ │ │    002: 87% │  │  │
│  │ 👥 M365           │            │ │ │ ✅ IR-2024- │  │  │
│  │ 📊 Reportes       │            │ │ │    999 cierre
│  │ ⚙️ Configuración  │            │ │ └─────────────┘  │  │
│  │                   │            │ │                   │  │
│  └───────────────────┘            │ └───────────────────┘  │
│                                   │                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 🏗️ ARQUITECTURA TÉCNICA COMPLETA

### 1. TECNOLOGÍA STACK

```json
{
  "Frontend": {
    "Framework": "React 18.x",
    "StateManagement": "Redux Toolkit + Redux Thunk",
    "UI Framework": "Material-UI v5",
    "Icons": "React Icons + Font Awesome",
    "Charts": "Chart.js + react-chartjs-2",
    "DataTables": "React Data Grid",
    "Forms": "React Hook Form + Yup",
    "Notifications": "React Toastify",
    "RealTime": "Socket.io-client",
    "Testing": "Jest + React Testing Library",
    "Build": "Vite (mejor que Create React App)",
    "Linting": "ESLint + Prettier"
  },
  "Backend": {
    "Framework": "FastAPI (actual)",
    "WebSocket": "FastAPI WebSockets",
    "AsyncIO": "Uvicorn ASGI",
    "Database": "SQLite (actual)"
  }
}
```

---

### 2. ESTRUCTURA DE DIRECTORIOS (ESCALABLE)

```
mcp-forensics-react/
│
├── src/
│   ├── components/                    # Componentes reutilizables
│   │   ├── Layout/
│   │   │   ├── Sidebar.jsx           # Menú principal
│   │   │   ├── Topbar.jsx            # Barra superior
│   │   │   ├── MainContent.jsx       # Contenedor principal
│   │   │   └── Layout.jsx            # Componente wrapper
│   │   │
│   │   ├── Common/                   # Componentes genéricos
│   │   │   ├── Button.jsx
│   │   │   ├── Card.jsx
│   │   │   ├── Modal.jsx
│   │   │   ├── Table.jsx
│   │   │   ├── Form.jsx
│   │   │   ├── Input.jsx
│   │   │   ├── Select.jsx
│   │   │   ├── Alert.jsx
│   │   │   ├── Badge.jsx
│   │   │   ├── Loading.jsx
│   │   │   ├── Empty.jsx
│   │   │   ├── ErrorBoundary.jsx
│   │   │   └── index.js              # Exportar todo
│   │   │
│   │   ├── Dashboard/                # Dashboard principal
│   │   │   ├── OverviewCard.jsx      # Tarjeta de métrica
│   │   │   ├── ThreatLevel.jsx       # Indicador nivel amenaza
│   │   │   ├── ActivityFeed.jsx      # Timeline de actividades
│   │   │   ├── AlertsList.jsx        # Lista de alertas
│   │   │   ├── QuickStats.jsx        # Estadísticas rápidas
│   │   │   └── Dashboard.jsx         # Página main
│   │   │
│   │   ├── Investigations/           # Módulo investigaciones
│   │   │   ├── CaseList.jsx          # Lista de casos
│   │   │   ├── CaseCard.jsx          # Tarjeta de caso
│   │   │   ├── CaseDetail.jsx        # Detalle completo
│   │   │   ├── CaseForm.jsx          # Formulario crear caso
│   │   │   ├── CaseGraph.jsx         # Grafo de ataque
│   │   │   ├── EvidenceView.jsx      # Vista de evidencia
│   │   │   ├── TimelineView.jsx      # Timeline forense
│   │   │   └── Investigations.jsx    # Página main
│   │   │
│   │   ├── ThreatHunting/            # Módulo threat hunting
│   │   │   ├── QueryBuilder.jsx      # Constructor queries
│   │   │   ├── SavedQueries.jsx      # Consultas guardadas
│   │   │   ├── QueryResults.jsx      # Resultados búsqueda
│   │   │   ├── HuntHistory.jsx       # Historial búsquedas
│   │   │   ├── AutoHunt.jsx          # Búsqueda automática
│   │   │   └── ThreatHunting.jsx     # Página main
│   │   │
│   │   ├── MobileAgents/             # Módulo agentes remotos
│   │   │   ├── AgentDeploy.jsx       # Desplegar agente
│   │   │   ├── DeviceList.jsx        # Dispositivos activos
│   │   │   ├── DeviceDetail.jsx      # Detalle dispositivo
│   │   │   ├── RemoteCollect.jsx     # Recolección remota
│   │   │   ├── AgentStatus.jsx       # Estado de agentes
│   │   │   ├── DeploymentLinks.jsx   # Links públicos deploy
│   │   │   └── MobileAgents.jsx      # Página main
│   │   │
│   │   ├── ActiveInvestigation/      # Investigaciones activas
│   │   │   ├── CommandExecutor.jsx   # Ejecutor comandos
│   │   │   ├── ProcessMonitor.jsx    # Monitor procesos
│   │   │   ├── NetworkCapture.jsx    # Captura tráfico
│   │   │   ├── LiveMemory.jsx        # Análisis memoria
│   │   │   ├── FileManager.jsx       # Gestor archivos remoto
│   │   │   ├── ActionHistory.jsx     # Historial acciones
│   │   │   └── ActiveInvestigation.jsx # Página main
│   │   │
│   │   ├── ThreatIntelligence/       # Inteligencia de amenazas
│   │   │   ├── IOCList.jsx           # Lista IOCs
│   │   │   ├── IOCForm.jsx           # Agregar IOC
│   │   │   ├── RuleBuilder.jsx       # Constructor reglas
│   │   │   ├── KnowledgeBase.jsx     # Base de conocimiento
│   │   │   ├── ThreatCorrelation.jsx # Correlación amenazas
│   │   │   └── ThreatIntelligence.jsx # Página main
│   │   │
│   │   ├── M365Management/           # Gestión M365
│   │   │   ├── TenantList.jsx        # Lista tenants
│   │   │   ├── TenantDetail.jsx      # Detalle tenant
│   │   │   ├── UserAnalysis.jsx      # Análisis usuarios
│   │   │   ├── OAuthAnalysis.jsx     # Análisis OAuth
│   │   │   ├── MailboxAnalysis.jsx   # Análisis buzones
│   │   │   └── M365Management.jsx    # Página main
│   │   │
│   │   ├── Reports/                  # Módulo reportes
│   │   │   ├── ReportBuilder.jsx     # Constructor reportes
│   │   │   ├── ReportList.jsx        # Reportes guardados
│   │   │   ├── ReportTemplate.jsx    # Plantillas
│   │   │   ├── ReportExport.jsx      # Exportar PDF/Excel
│   │   │   ├── ReportSchedule.jsx    # Programación
│   │   │   └── Reports.jsx           # Página main
│   │   │
│   │   ├── Settings/                 # Configuración
│   │   │   ├── APIKeys.jsx           # Gestión API keys
│   │   │   ├── TeamManagement.jsx    # Gestión equipo
│   │   │   ├── AlertRules.jsx        # Reglas alertas
│   │   │   ├── Integrations.jsx      # Integraciones
│   │   │   ├── SystemHealth.jsx      # Salud del sistema
│   │   │   └── Settings.jsx          # Página main
│   │   │
│   │   └── Icons/                    # Iconografía personalizada
│   │       ├── ThreatIcon.jsx
│   │       ├── StatusIcon.jsx
│   │       ├── ProcessIcon.jsx
│   │       ├── NetworkIcon.jsx
│   │       └── index.js
│   │
│   ├── pages/                         # Páginas (rutas)
│   │   ├── Dashboard.jsx
│   │   ├── Investigations.jsx
│   │   ├── ThreatHunting.jsx
│   │   ├── MobileAgents.jsx
│   │   ├── ActiveInvestigation.jsx
│   │   ├── ThreatIntelligence.jsx
│   │   ├── M365Management.jsx
│   │   ├── Reports.jsx
│   │   ├── Settings.jsx
│   │   └── Login.jsx
│   │
│   ├── services/                      # Servicios API
│   │   ├── api.js                    # Cliente HTTP
│   │   ├── auth.js                   # Autenticación
│   │   ├── cases.js                  # Casos API
│   │   ├── investigations.js         # Investigaciones API
│   │   ├── hunting.js                # Threat hunting API
│   │   ├── agents.js                 # Agentes remotos API
│   │   ├── m365.js                   # M365 API
│   │   ├── threat_intel.js           # Threat intel API
│   │   ├── reports.js                # Reportes API
│   │   └── realtime.js               # WebSocket real-time
│   │
│   ├── hooks/                         # Custom Hooks
│   │   ├── useCase.js                # Hook para casos
│   │   ├── useInvestigation.js       # Hook para investigaciones
│   │   ├── useAsync.js               # Hook async operations
│   │   ├── useValidation.js          # Hook validación
│   │   ├── useRealtime.js            # Hook WebSocket
│   │   ├── usePagination.js          # Hook paginación
│   │   ├── useLocalStorage.js        # Hook localStorage
│   │   └── useTheme.js               # Hook tema (dark/light)
│   │
│   ├── store/                         # Redux store
│   │   ├── reducers/
│   │   │   ├── caseReducer.js
│   │   │   ├── investigationReducer.js
│   │   │   ├── agentReducer.js
│   │   │   ├── threatReducer.js
│   │   │   ├── uiReducer.js
│   │   │   └── authReducer.js
│   │   ├── actions/
│   │   │   ├── caseActions.js
│   │   │   ├── investigationActions.js
│   │   │   ├── agentActions.js
│   │   │   └── uiActions.js
│   │   ├── selectors/
│   │   │   ├── caseSelectors.js
│   │   │   ├── investigationSelectors.js
│   │   │   └── uiSelectors.js
│   │   ├── middleware/
│   │   │   └── api.js                # API middleware
│   │   └── store.js                  # Store configuration
│   │
│   ├── styles/                        # Estilos globales
│   │   ├── index.css                 # Reset + globals
│   │   ├── colors.css                # Paleta de colores
│   │   ├── typography.css            # Tipografía
│   │   ├── components.css            # Estilos componentes
│   │   ├── sentinel.css              # Tema Sentinel
│   │   ├── dark.css                  # Tema oscuro
│   │   └── responsive.css            # Media queries
│   │
│   ├── utils/                         # Utilidades
│   │   ├── formatters.js             # Formateo datos
│   │   ├── validators.js             # Validaciones
│   │   ├── dates.js                  # Manejo fechas
│   │   ├── colors.js                 # Funciones color
│   │   ├── constants.js              # Constantes
│   │   ├── localStorage.js           # Storage local
│   │   └── logger.js                 # Logging
│   │
│   ├── config/                        # Configuración
│   │   ├── api.config.js             # Config API
│   │   ├── app.config.js             # Config app
│   │   └── features.js               # Feature flags
│   │
│   ├── types/                         # TypeScript types (si usas TS)
│   │   ├── case.types.js
│   │   ├── investigation.types.js
│   │   ├── agent.types.js
│   │   └── common.types.js
│   │
│   ├── __tests__/                     # Tests
│   │   ├── components/
│   │   ├── services/
│   │   ├── hooks/
│   │   └── utils/
│   │
│   ├── App.jsx                        # Componente root
│   ├── index.jsx                      # Entry point
│   └── index.css
│
├── public/                            # Archivos estáticos
│   ├── index.html
│   ├── favicon.ico
│   └── manifest.json
│
├── .env.example                       # Variables de entorno
├── .eslintrc.json                    # Configuración ESLint
├── .prettierrc.json                  # Configuración Prettier
├── vite.config.js                    # Config Vite
├── package.json
├── package-lock.json
└── README.md
```

---

## 🔄 INVESTIGACIONES ACTIVAS: Arquitectura de Componentes

### CommandExecutor Component

```jsx
// src/components/ActiveInvestigation/CommandExecutor.jsx

import React, { useState, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import useAsync from '../../hooks/useAsync';
import Card from '../Common/Card';
import Button from '../Common/Button';
import Input from '../Common/Input';
import Alert from '../Common/Alert';
import Loading from '../Common/Loading';
import { executeCommand } from '../../services/agents.js';

const COMMAND_TEMPLATES = {
  windows: [
    { label: 'Listar procesos', cmd: 'tasklist /v' },
    { label: 'Conexiones activas', cmd: 'netstat -ano' },
    { label: 'Usuarios locales', cmd: 'net user' },
    { label: 'Services', cmd: 'Get-Service | Export-Csv' },
    { label: 'Scheduled Tasks', cmd: 'Get-ScheduledTask' },
    { label: 'Event logs', cmd: 'Get-EventLog -LogName Security' },
  ],
  mac: [
    { label: 'Procesos', cmd: 'ps aux' },
    { label: 'Conexiones', cmd: 'lsof -i' },
    { label: 'Usuarios', cmd: 'dscl . -list /Users' },
    { label: 'System logs', cmd: 'log stream --level debug' },
  ],
  linux: [
    { label: 'Procesos', cmd: 'ps aux' },
    { label: 'Conexiones', cmd: 'ss -tulpn' },
    { label: 'Usuarios', cmd: 'cat /etc/passwd' },
    { label: 'Auditd logs', cmd: 'ausearch -m ALL' },
  ],
};

export default function CommandExecutor({ caseId, deviceId }) {
  const [osType, setOsType] = useState('windows');
  const [command, setCommand] = useState('');
  const [output, setOutput] = useState('');
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  
  const { 
    status, 
    data, 
    error, 
    run 
  } = useAsync(null);

  const handleExecute = async () => {
    if (!command.trim()) {
      return;
    }

    try {
      const result = await run(
        executeCommand(caseId, deviceId, command, osType)
      );
      setOutput(result.stdout || result.output || '');
    } catch (err) {
      setOutput(`ERROR: ${err.message}`);
    }
  };

  const handleTemplateSelect = (template) => {
    setCommand(template.cmd);
    setSelectedTemplate(template);
  };

  return (
    <Card title="⌨️ Ejecutor de Comandos" className="command-executor">
      <div className="command-section">
        <div className="form-group">
          <label>🖥️ Sistema Operativo</label>
          <select value={osType} onChange={(e) => setOsType(e.target.value)}>
            <option value="windows">Windows</option>
            <option value="mac">Mac/macOS</option>
            <option value="linux">Linux</option>
          </select>
        </div>

        <div className="form-group">
          <label>📋 Plantillas Predefinidas</label>
          <div className="template-buttons">
            {COMMAND_TEMPLATES[osType].map((tmpl, idx) => (
              <Button
                key={idx}
                variant={selectedTemplate?.cmd === tmpl.cmd ? 'primary' : 'secondary'}
                onClick={() => handleTemplateSelect(tmpl)}
                size="sm"
              >
                {tmpl.label}
              </Button>
            ))}
          </div>
        </div>

        <div className="form-group">
          <label>⌨️ Comando</label>
          <textarea
            value={command}
            onChange={(e) => setCommand(e.target.value)}
            placeholder={`Ej: tasklist /v`}
            rows={4}
            className="command-input"
          />
        </div>

        <div className="form-actions">
          <Button
            onClick={handleExecute}
            disabled={!command.trim() || status === 'pending'}
            variant="primary"
          >
            {status === 'pending' ? '⏳ Ejecutando...' : '▶️ Ejecutar'}
          </Button>
          <Button
            onClick={() => setCommand('')}
            variant="secondary"
          >
            🗑️ Limpiar
          </Button>
        </div>
      </div>

      {error && (
        <Alert type="error" message={`Error: ${error}`} />
      )}

      {output && (
        <div className="output-section">
          <div className="output-header">
            <h4>📤 Resultado</h4>
            <Button
              onClick={() => navigator.clipboard.writeText(output)}
              size="sm"
              variant="secondary"
            >
              📋 Copiar
            </Button>
          </div>
          <pre className="output-box">{output}</pre>
        </div>
      )}

      {status === 'pending' && <Loading message="Ejecutando comando remoto..." />}
    </Card>
  );
}
```

---

## 🎯 STATE MANAGEMENT: Redux Architecture

```javascript
// src/store/store.js

import { configureStore } from '@reduxjs/toolkit';
import caseReducer from './reducers/caseReducer';
import investigationReducer from './reducers/investigationReducer';
import agentReducer from './reducers/agentReducer';
import threatReducer from './reducers/threatReducer';
import uiReducer from './reducers/uiReducer';
import authReducer from './reducers/authReducer';
import apiMiddleware from './middleware/api';

export const store = configureStore({
  reducer: {
    cases: caseReducer,
    investigations: investigationReducer,
    agents: agentReducer,
    threats: threatReducer,
    ui: uiReducer,
    auth: authReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware()
      .concat(apiMiddleware),
  devTools: process.env.NODE_ENV !== 'production',
});
```

---

## 📊 DIAGRAMA DE FLUJO: Investigación Activa

```
┌─────────────────────────────────────────────────────┐
│  Usuario: Abre CommandExecutor                      │
└──────────────────┬──────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────┐
│ Selecciona dispositivo y comando                    │
│ - Device: WORKSTATION-01                           │
│ - OS: Windows                                       │
│ - Cmd: tasklist /v                                 │
└──────────────────┬──────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────┐
│ Redux: executeCommand ACTION                       │
│ → caseReducer.pending                              │
└──────────────────┬──────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────┐
│ API Middleware: POST /api/agents/execute            │
│ Payload: {device_id, command, os_type}             │
└──────────────────┬──────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────┐
│ Backend: FastAPI Route                             │
│ /forensics/active-investigation/execute             │
│ ├─ Validate input                                  │
│ ├─ Connect to device (Intune/OSQuery/Velociraptor) │
│ └─ Execute command                                 │
└──────────────────┬──────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────┐
│ Agent Response: stdout + stderr                    │
│ → WebSocket update (real-time)                     │
└──────────────────┬──────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────┐
│ Redux: executeCommand FULFILLED                    │
│ → Update state with results                        │
└──────────────────┬──────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────┐
│ UI Update: Display output in <pre>                 │
│ ✅ Command ejecutado exitosamente                  │
└─────────────────────────────────────────────────────┘
```

---

## 📈 ESTIMACIÓN DE ESFUERZO

| Componente | Horas | Dificultad | Prioridad |
|---|---|---|---|
| Setup React + Vite | 4 | 🟢 Fácil | 🔴 P0 |
| Componentes base (Button, Card, etc) | 8 | 🟢 Fácil | 🔴 P0 |
| Sidebar + Layout | 6 | 🟢 Fácil | 🔴 P0 |
| Dashboard | 12 | 🟡 Medio | 🔴 P0 |
| Investigations (List + Detail) | 16 | 🟡 Medio | 🔴 P0 |
| Threat Hunting | 12 | 🟡 Medio | 🟠 P1 |
| Mobile Agents | 14 | 🟡 Medio | 🔴 P0 |
| Active Investigation | 16 | 🟠 Alto | 🔴 P0 |
| Reports | 10 | 🟡 Medio | 🟠 P1 |
| Settings | 8 | 🟢 Fácil | 🟡 P2 |
| Testing | 20 | 🟠 Alto | 🟡 P2 |
| **TOTAL** | **≈126 horas** | | |

**Estimación por equipo**:
- 1 dev: 3-4 semanas (tiempo completo)
- 2 devs: 2-2.5 semanas (paralelo)
- 3 devs: 10-12 días (muy paralelo)

---

## ✅ CHECKLIST DE MIGRACIÓN

- [ ] Crear proyecto Vite
- [ ] Instalar dependencias (React, Redux, Material-UI)
- [ ] Implementar componentes base
- [ ] Crear estructura Redux
- [ ] Implementar Layout + Sidebar
- [ ] Migrar Dashboard
- [ ] Migrar Investigaciones
- [ ] Implementar Mobile Agents
- [ ] Implementar Active Investigation
- [ ] Setup WebSocket real-time
- [ ] Testing + QA
- [ ] Deploy a producción

---

**Documento Completado**: 2025-12-05  
**Recomendación**: Comenzar con FASE 1 (Frontend React)  
**Viabilidad**: 🟢🟢🟢 MUY ALTA
