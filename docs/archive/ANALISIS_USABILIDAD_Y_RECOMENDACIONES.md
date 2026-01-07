# 📊 ANÁLISIS COMPLETO: USABILIDAD Y RECOMENDACIONES ESTRATÉGICAS

**Fecha**: 2025-12-05  
**Versión**: 1.0  
**Estado**: 🔍 ANÁLISIS EN PROFUNDIDAD

---

## 📋 TABLA DE CONTENIDOS

1. [Análisis de Usabilidad Actual](#análisis-de-usabilidad-actual)
2. [Problemas Identificados](#problemas-identificados)
3. [Recomendaciones de Mejora](#recomendaciones-de-mejora)
4. [Herramientas para Mobile Agent](#herramientas-para-mobile-agent)
5. [Arquitectura React (Sentinel Style)](#arquitectura-react-sentinel-style)
6. [Investigaciones Activas vs Pasivas](#investigaciones-activas-vs-pasivas)

---

## 🎯 ANÁLISIS DE USABILIDAD ACTUAL

### ✅ Fortalezas Actuales

#### 1. **Backend Robusto**
```
✓ FastAPI con async/await
✓ Manejo de errores completo
✓ Rate limiting automático
✓ Timeout management
✓ Evidence isolation
✓ Background tasks (BackgroundTasks)
```

**Calificación**: ⭐⭐⭐⭐⭐ (5/5)

#### 2. **Integración de Herramientas**
```
✓ Sparrow 365 integrado
✓ Hawk (Exchange) integrado
✓ O365 Extractor funcional
✓ Loki Scanner activo
✓ YARA malware detection
✓ Volatility 3 memory analysis
✓ OSQuery endpoint forensics
✓ HIBP API rate-limited
```

**Calificación**: ⭐⭐⭐⭐⭐ (5/5)

#### 3. **API RESTful**
```
✓ Endpoints bien organizados
✓ Autenticación con API key
✓ Swagger/OpenAPI docs
✓ JSON responses structuradas
```

**Calificación**: ⭐⭐⭐⭐ (4/5)

---

### ❌ PROBLEMAS IDENTIFICADOS

#### 🔴 CRÍTICOS (Debe Arreglarse Inmediatamente)

##### Problema #1: **UI/UX Poco Intuitiva**
```
Actualmente:
- Dashboard es funcional pero NO es visual
- No hay iconografía clara
- Navegación confusa
- No hay jerarquía visual clara
- Falta feedback de usuarios (tooltips, help text)

Impacto: 
❌ Usuarios nuevos tardan mucho en aprender
❌ Eficiencia operativa baja
❌ Tasa de errores alta
```

**Severity**: 🔴 CRÍTICO

##### Problema #2: **Sin Capacidad de Mobile Agent**
```
Actualmente:
- Solo análisis remoto (sin endpoint local)
- No hay recolección directa de dispositivos
- No hay integración con MDM/endpoint tools
- No hay soporte para Mac/iOS/Android/Windows local

Impacto:
❌ No se pueden investigar endpoints comprometidos localmente
❌ Pérdida de forensic artifacts
❌ Investigaciones incompletas
```

**Severity**: 🔴 CRÍTICO

##### Problema #3: **Falta de Investigaciones Activas**
```
Actualmente:
- Solo investigaciones PASIVAS (análisis de logs)
- No hay ejecución de comandos en endpoints
- No hay capacidad de respuesta en tiempo real
- No hay hunting automático

Impacto:
❌ Respuesta a incidentes lenta
❌ No se pueden hacer containment activo
❌ No hay threat hunting
```

**Severity**: 🔴 CRÍTICO

##### Problema #4: **Estructura de Rutas Desorganizada**
```
Actualmente:
api/routes/
├── account_analysis_routes.py      ← Desorden
├── cases.py
├── credentials.py
├── dashboard.py
├── endpoint.py
├── evidence.py
├── forensics_tools.py             ← Muy general
├── graph.py
├── graph_editor.py
├── m365.py
├── oauth.py
├── tenants.py
└── workflow.py

Impacto:
❌ Difícil de mantener
❌ Difícil agregar nuevas funcionalidades
❌ Duplicación de código potencial
```

**Severity**: 🟠 ALTO

#### 🟠 ALTOS (Debe Mejorarse)

##### Problema #5: **Sin Validación En Línea**
```
Actualmente:
- Validación solo en backend
- No hay validación UI real-time
- No hay error messages amigables
- No hay form validation visual

Ejemplo problema:
1. Usuario ingresa información en modal
2. Hace clic en botón
3. Espera respuesta del servidor
4. Recibe error genérico
5. No sabe qué fue mal
```

**Severity**: 🟠 ALTO

##### Problema #6: **Dashboard poco visual**
```
Actualmente:
- Texto predomina sobre elementos visuales
- No hay iconografía clara
- No hay indicadores de estado visuales
- No hay gráficos de riesgo
- No hay heatmaps de actividad

Comparar con:
✓ Microsoft Sentinel (muy visual)
✓ Elasticsearch (dashboards ricos)
✓ Grafana (métricas claras)
```

**Severity**: 🟠 ALTO

---

## 💡 RECOMENDACIONES DE MEJORA

### 🎯 RECOMENDACIÓN #1: UI/UX Rediseño (Sentinel Style)

#### Cambio 1: Estructura de Menú React (ESTRUCTURA PRINCIPAL)

```
MODELO PROPUESTO:
┌─────────────────────────────────────────────┐
│ MCP Forensics & IR                          │
├─────────────────────────────────────────────┤
│                                             │
│  ☰ MENU                                     │
│  ├─ 🏠 Dashboard (Overview)                 │
│  ├─ 🔍 Investigaciones                      │
│  │  ├─ 📋 Lista de Casos                   │
│  │  ├─ ➕ Nuevo Caso                        │
│  │  └─ 🔥 En Progreso                      │
│  ├─ 🎯 Threat Hunting                       │
│  │  ├─ 📊 Búsquedas Guardadas              │
│  │  ├─ 🤖 Auto-Hunts                       │
│  │  └─ 📈 Resultados                       │
│  ├─ 🔌 Agentes Remotos                      │
│  │  ├─ 📱 Dispositivos Activos             │
│  │  ├─ 🌐 Conectar Nuevo                   │
│  │  └─ 📥 Recolecciones                    │
│  ├─ ⚙️ Inteligencia de Amenazas             │
│  │  ├─ 💾 IOCs                             │
│  │  ├─ 🛑 Reglas de Detección              │
│  │  └─ 📚 Base de Conocimiento             │
│  ├─ 👥 M365 & Tenants                       │
│  │  ├─ 🏢 Tenants                          │
│  │  ├─ 👤 Usuarios                         │
│  │  └─ 🔐 Análisis OAuth                   │
│  ├─ 📊 Reportes                             │
│  │  ├─ 📈 Activos                          │
│  │  ├─ 📉 Cerrados                         │
│  │  └─ 🎯 Por Amenaza                      │
│  └─ ⚙️ Configuración                        │
│     ├─ 🔑 API Keys                         │
│     ├─ 👨‍💼 Equipo                            │
│     └─ 🔔 Alertas                          │
│                                             │
└─────────────────────────────────────────────┘
```

**Beneficios**:
- ✓ Muy similar a Microsoft Sentinel
- ✓ Estructura lógica
- ✓ Fácil de aprender
- ✓ Escalable

---

### 🎯 RECOMENDACIÓN #2: Validación En Línea (Real-Time)

#### Cambio 2: Componentes React con Validación

```javascript
// MODELO PROPUESTO: Form Component con Validación Real-Time

<FormContainer>
  <InputField
    label="Dirección de Correo"
    placeholder="usuario@empresa.com"
    type="email"
    validation={{
      required: true,
      email: true,
      pattern: /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/,
      custom: async (value) => {
        // Validación async contra servidor
        const isValid = await checkEmailFormat(value);
        return isValid ? null : "Email no válido en el tenant";
      }
    }}
    icon="✉️"
    help="Formato: usuario@empresa.com"
    error={{
      show: hasError,
      message: errorMessage,
      type: 'warning' | 'error' | 'success'
    }}
  />
  
  <InputField
    label="Tipo de Análisis"
    type="select"
    options={[
      { value: 'sparrow', label: '⚡ Sparrow (Rápido)', icon: '⚡' },
      { value: 'hawk', label: '🦅 Hawk (Completo)', icon: '🦅' },
      { value: 'both', label: '🎯 Ambos (Exhaustivo)', icon: '🎯' }
    ]}
    hint="Sparrow es más rápido, Hawk más detallado"
  />
</FormContainer>
```

**Validaciones en línea propuestas**:
- ✓ Email format (regex)
- ✓ Tenant ID válido (async check)
- ✓ Fecha válida
- ✓ Campo requerido
- ✓ Longitud mínima/máxima
- ✓ Valores permitidos (enum)

---

### 🎯 RECOMENDACIÓN #3: Investigaciones Activas & Pasivas

#### Cambio 3: Modo de Investigación

```
INVESTIGACIÓN PASIVA (Actual)
├─ Análisis de logs almacenados
├─ Búsqueda en O365 Unified Audit Log
├─ Análisis de evidencia recopilada
├─ Timeline forense
└─ ⏱️ Tiempo: Minutos a horas

INVESTIGACIÓN ACTIVA (NUEVO) ← CRÍTICO
├─ Ejecución de comandos en endpoints
├─ Recolección de memoria RAM en vivo
├─ Captura de tráfico de red
├─ Ejecutar YARA en tiempo real
├─ Buscar procesos sospechosos
├─ Bloquear archivo/IP (containment)
└─ ⏱️ Tiempo: Segundos a minutos
```

**Ejemplo de Investigación Activa**:

```json
POST /forensics/investigation/active/start
{
  "case_id": "IR-2025-001",
  "type": "active",
  "scope": "endpoint",
  "target": "WORKSTATION-01",
  "actions": [
    {
      "type": "command",
      "command": "tasklist",
      "description": "Listar procesos"
    },
    {
      "type": "memory_dump",
      "format": "minidump",
      "description": "Descargar memoria RAM"
    },
    {
      "type": "file_capture",
      "pattern": "*.lnk",
      "path": "C:\\Users\\*\\Recent",
      "description": "Capturar atajos recientes"
    },
    {
      "type": "network_capture",
      "duration": 30,
      "description": "Capturar tráfico de red 30 segundos"
    }
  ]
}
```

---

## 🌐 HERRAMIENTAS PARA MOBILE AGENT (SIN DESARROLLO CUSTOM)

### ✅ OPCIÓN 1: **Microsoft Intune (RECOMENDADO)**

**Ventajas**:
```
✓ Nativo en ecosistema M365
✓ Control remoto de endpoints Windows/Mac/iOS/Android
✓ Recolección de logs
✓ Ejecución de scripts
✓ MDM integrado
✓ Cumplimiento normativo
```

**Integración Propuesta**:
```python
# api/services/mobile_agent_intune.py

class IntuneRemoteAgent:
    """
    Usa Microsoft Intune para comunicarse con endpoints
    """
    
    async def collect_from_device(self, device_id: str, case_id: str):
        """Recolecta evidencia usando Intune"""
        # 1. Obtener token de Graph API
        # 2. Ejecutar script remoto en dispositivo
        # 3. Descargar artefactos
        # 4. Cargar a caso
        pass
```

**Herramienta**: Microsoft Intune Remote Support
**Costo**: Incluido en M365 (Intune subscription)

---

### ✅ OPCIÓN 2: **OSQuery (MULTIPLATAFORMA)**

**Ventajas**:
```
✓ Gratuito y open-source
✓ Windows/Mac/Linux/iOS
✓ Agente ligero (~5MB)
✓ Queries SQL-like
✓ Real-time collection
✓ Muy usado en empresas
```

**Integración Propuesta**:
```python
# api/services/mobile_agent_osquery.py

class OSQueryAgent:
    """
    Agente OSQuery para recolección en endpoints
    """
    
    async def deploy_agent(self, device_id: str, os_type: str):
        """Deploy de agente OSQuery"""
        urls = {
            'windows': 'https://osquery.io/downloads/windows',
            'mac': 'https://osquery.io/downloads/osx',
            'linux': 'https://osquery.io/downloads/linux'
        }
        # Generar link de descarga + instalación automática
        pass
    
    async def execute_query(self, device_id: str, query: str):
        """Ejecuta query SQL en endpoint"""
        # SELECT * FROM processes WHERE name LIKE '%svchost%'
        # SELECT * FROM open_sockets WHERE port != 0
        pass
```

**Link Público**: https://osquery.io/downloads

---

### ✅ OPCIÓN 3: **EDR Gratuito: Velociraptor**

**Ventajas**:
```
✓ EDR completo gratuito
✓ Windows/Mac/Linux
✓ Recolección en tiempo real
✓ YARA integration
✓ Flujo de trabajo visual
✓ Excelente documentación
```

**Integración Propuesta**:
```python
# api/services/mobile_agent_velociraptor.py

class VelociraptorAgent:
    """
    Agente Velociraptor para respuesta en endpoints
    """
    
    async def deploy_client(self, device_id: str):
        """Deploy cliente Velociraptor"""
        # Generar installer con servidor
        pass
    
    async def collect_artifacts(self, device_id: str, artifacts: list):
        """Recolecta artefactos predefinidos"""
        # artifacts = ['Windows.Registry.SAM', 'Linux.Auditd']
        pass
```

**Link Público**: https://github.com/Velocidex/velociraptor

---

### ✅ OPCIÓN 4: **EDR de Pago (Si hay presupuesto)**

| Herramienta | Costo | Ventajas | Plataformas |
|---|---|---|---|
| **CrowdStrike Falcon** | $$$$ | Mejor en industria | Win/Mac/Linux |
| **SentinelOne** | $$$ | Muy buena | Win/Mac/Linux/iOS |
| **Sophos XDR** | $$$ | Excelente | Win/Mac/Linux |
| **Defender for Endpoint** | $$$ (M365) | Integrado con Azure | Win/Mac |

---

### 🎯 **RECOMENDACIÓN PARA MOBILE AGENT**

#### **Estrategia Híbrida** (ÓPTIMA):

```
Nivel 1: Intune (Para M365)
├─ Windows Defender
├─ PowerShell Remoto
└─ Colección automática

Nivel 2: OSQuery (Multiplataforma)
├─ Link público para descargar
├─ Configuración automática
└─ Queries predefinidas

Nivel 3: Velociraptor (EDR Gratuito)
├─ Para casos críticos
├─ Cuando Intune no funciona
└─ Análisis forense profundo

Nivel 4: EDR Pago (Si disponible)
└─ Para organizaciones grandes
```

---

## 🏗️ ARQUITECTURA REACT (SENTINEL STYLE)

### ✅ ESTRUCTURA DE COMPONENTES PROPUESTA

```
mcp-kali-forensics-react/
├── src/
│   ├── components/
│   │   ├── Layout/
│   │   │   ├── Sidebar.jsx          (Menú principal)
│   │   │   ├── Topbar.jsx           (Información usuario)
│   │   │   ├── MainContent.jsx      (Área principal)
│   │   │   └── Layout.jsx           (Contenedor)
│   │   │
│   │   ├── Dashboard/
│   │   │   ├── OverviewCard.jsx     (Métrica individual)
│   │   │   ├── ThreatLevel.jsx      (Indicador de amenaza)
│   │   │   ├── ActivityFeed.jsx     (Timeline)
│   │   │   ├── AlertsList.jsx       (Alertas)
│   │   │   └── Dashboard.jsx        (Main)
│   │   │
│   │   ├── Investigations/
│   │   │   ├── CaseList.jsx         (Lista de casos)
│   │   │   ├── CaseDetail.jsx       (Detalle caso)
│   │   │   ├── CaseForm.jsx         (Crear caso)
│   │   │   ├── CaseGraph.jsx        (Grafo de ataque)
│   │   │   └── Investigations.jsx   (Main)
│   │   │
│   │   ├── ThreatHunting/
│   │   │   ├── QueryBuilder.jsx     (Constructor de queries)
│   │   │   ├── SavedQueries.jsx     (Búsquedas guardadas)
│   │   │   ├── HuntResults.jsx      (Resultados)
│   │   │   ├── AutoHunt.jsx         (Búsqueda automática)
│   │   │   └── ThreatHunting.jsx    (Main)
│   │   │
│   │   ├── MobileAgents/
│   │   │   ├── AgentDeploy.jsx      (Desplegar agente)
│   │   │   ├── DeviceList.jsx       (Dispositivos activos)
│   │   │   ├── RemoteCollect.jsx    (Recolección remota)
│   │   │   ├── AgentStatus.jsx      (Estado agentes)
│   │   │   └── MobileAgents.jsx     (Main)
│   │   │
│   │   ├── ActiveInvestigation/
│   │   │   ├── CommandExecutor.jsx  (Ejecutor de comandos)
│   │   │   ├── ProcessMonitor.jsx   (Monitor de procesos)
│   │   │   ├── NetworkCapture.jsx   (Captura de tráfico)
│   │   │   ├── LiveMemory.jsx       (Análisis de memoria)
│   │   │   └── ActiveInvestigation.jsx (Main)
│   │   │
│   │   ├── ThreatIntelligence/
│   │   │   ├── IOCList.jsx          (Lista de IOCs)
│   │   │   ├── RuleBuilder.jsx      (Crear reglas)
│   │   │   ├── KnowledgeBase.jsx    (Base de conocimiento)
│   │   │   └── ThreatIntelligence.jsx (Main)
│   │   │
│   │   ├── M365Management/
│   │   │   ├── TenantList.jsx       (Tenants)
│   │   │   ├── UserAnalysis.jsx     (Análisis de usuarios)
│   │   │   ├── OAuthAnalysis.jsx    (Análisis OAuth)
│   │   │   └── M365Management.jsx   (Main)
│   │   │
│   │   ├── Reports/
│   │   │   ├── ReportBuilder.jsx    (Constructor de reportes)
│   │   │   ├── ReportList.jsx       (Reportes guardados)
│   │   │   ├── ReportExport.jsx     (Exportar PDF)
│   │   │   └── Reports.jsx          (Main)
│   │   │
│   │   ├── Common/
│   │   │   ├── Button.jsx           (Botón estándar)
│   │   │   ├── Card.jsx             (Tarjeta)
│   │   │   ├── Modal.jsx            (Modal dialog)
│   │   │   ├── Table.jsx            (Tabla)
│   │   │   ├── Form.jsx             (Formulario)
│   │   │   ├── Alert.jsx            (Alerta)
│   │   │   ├── Loading.jsx          (Indicador carga)
│   │   │   └── ErrorBoundary.jsx    (Manejador errores)
│   │   │
│   │   └── Icons/
│   │       ├── ThreatIcon.jsx       (Ícono amenaza)
│   │       ├── StatusIcon.jsx       (Ícono estado)
│   │       └── index.jsx            (Exportar todos)
│   │
│   ├── pages/
│   │   ├── Dashboard.jsx
│   │   ├── Investigations.jsx
│   │   ├── ThreatHunting.jsx
│   │   ├── MobileAgents.jsx
│   │   ├── ActiveInvestigation.jsx
│   │   ├── ThreatIntelligence.jsx
│   │   ├── M365Management.jsx
│   │   ├── Reports.jsx
│   │   └── Settings.jsx
│   │
│   ├── services/
│   │   ├── api.js               (Cliente API)
│   │   ├── auth.js              (Autenticación)
│   │   ├── cases.js             (Casos)
│   │   ├── investigations.js     (Investigaciones)
│   │   ├── hunting.js           (Threat hunting)
│   │   ├── agents.js            (Agentes remotos)
│   │   ├── m365.js              (M365)
│   │   └── realtime.js          (WebSocket)
│   │
│   ├── hooks/
│   │   ├── useCase.js           (Custom hook para casos)
│   │   ├── useSWR.js            (Data fetching)
│   │   ├── useAsync.js          (Async operations)
│   │   ├── useValidation.js     (Validación)
│   │   └── useRealtime.js       (WebSocket)
│   │
│   ├── styles/
│   │   ├── index.css            (Global)
│   │   ├── colors.css           (Paleta de colores)
│   │   ├── components.css       (Componentes)
│   │   └── sentinel.css         (Tema Sentinel)
│   │
│   ├── utils/
│   │   ├── formatters.js        (Formateo de datos)
│   │   ├── validators.js        (Validaciones)
│   │   ├── dates.js             (Manejo de fechas)
│   │   ├── colors.js            (Paleta de colores)
│   │   └── constants.js         (Constantes)
│   │
│   ├── store/
│   │   ├── reducers/
│   │   │   ├── cases.js
│   │   │   ├── investigations.js
│   │   │   └── ui.js
│   │   ├── actions/
│   │   │   └── index.js
│   │   └── store.js
│   │
│   ├── App.jsx
│   └── index.jsx
│
├── public/
├── package.json
├── .env.example
└── README.md
```

---

### 📊 EJEMPLO: Component "ActiveInvestigation"

```jsx
// src/pages/ActiveInvestigation.jsx

import React, { useState, useEffect } from 'react';
import CommandExecutor from '../components/ActiveInvestigation/CommandExecutor';
import ProcessMonitor from '../components/ActiveInvestigation/ProcessMonitor';
import NetworkCapture from '../components/ActiveInvestigation/NetworkCapture';
import LiveMemory from '../components/ActiveInvestigation/LiveMemory';
import Card from '../components/Common/Card';
import Tabs from '../components/Common/Tabs';

export default function ActiveInvestigation() {
  const [caseId, setCaseId] = useState(null);
  const [activeTab, setActiveTab] = useState('commands');
  const [deviceId, setDeviceId] = useState(null);

  const tabs = [
    { id: 'commands', label: '⌨️ Ejecutor de Comandos', icon: '⌨️' },
    { id: 'processes', label: '🔄 Monitor de Procesos', icon: '🔄' },
    { id: 'network', label: '🌐 Captura de Tráfico', icon: '🌐' },
    { id: 'memory', label: '💾 Análisis de Memoria', icon: '💾' }
  ];

  return (
    <div className="active-investigation">
      <div className="header">
        <h1>🔍 Investigación Activa en Tiempo Real</h1>
        <p>Ejecuta acciones inmediatas en endpoints comprometidos</p>
      </div>

      <Tabs 
        tabs={tabs} 
        activeTab={activeTab} 
        onChange={setActiveTab}
      >
        {activeTab === 'commands' && (
          <Card title="⌨️ Ejecutor de Comandos">
            <CommandExecutor caseId={caseId} deviceId={deviceId} />
          </Card>
        )}

        {activeTab === 'processes' && (
          <Card title="🔄 Monitor de Procesos">
            <ProcessMonitor caseId={caseId} deviceId={deviceId} />
          </Card>
        )}

        {activeTab === 'network' && (
          <Card title="🌐 Captura de Tráfico">
            <NetworkCapture caseId={caseId} deviceId={deviceId} />
          </Card>
        )}

        {activeTab === 'memory' && (
          <Card title="💾 Análisis de Memoria">
            <LiveMemory caseId={caseId} deviceId={deviceId} />
          </Card>
        )}
      </Tabs>
    </div>
  );
}
```

---

## 🔄 INVESTIGACIONES ACTIVAS vs PASIVAS

### 📊 MATRIZ COMPARATIVA

```
┌──────────────────────────────────┬──────────────┬──────────────┐
│ Característica                   │ PASIVA       │ ACTIVA       │
├──────────────────────────────────┼──────────────┼──────────────┤
│ Análisis de logs                 │ ✓ ✓ ✓       │ ✓            │
│ Búsqueda de artefactos           │ ✓ ✓         │ ✓ ✓ ✓       │
│ Ejecución de comandos            │ ✗           │ ✓ ✓ ✓       │
│ Recolección en tiempo real       │ ✗           │ ✓ ✓ ✓       │
│ Captura de memoria               │ ✗           │ ✓ ✓ ✓       │
│ Captura de red                   │ ✗           │ ✓ ✓ ✓       │
│ Duración                         │ Minutos      │ Segundos     │
│ Intrusividad                     │ Baja        │ Alta        │
│ Riesgo de tipping off            │ Bajo        │ Alto        │
│ Calidad de evidencia             │ Buena       │ Excelente   │
│ Complejidad                      │ Baja        │ Alta        │
│ Requisitos de acceso             │ Logs        │ Admin/Local │
└──────────────────────────────────┴──────────────┴──────────────┘
```

### 🎯 IMPLEMENTACIÓN: Investigaciones Activas

```python
# api/services/active_investigation.py

class ActiveInvestigationService:
    """
    Investigaciones ACTIVAS: Ejecutar acciones en tiempo real
    """
    
    async def execute_command(
        self, 
        case_id: str, 
        device_id: str, 
        command: str,
        os_type: str  # windows | linux | mac
    ) -> Dict:
        """
        Ejecuta comando en endpoint remoto
        
        Ejemplo:
        - Windows: tasklist, Get-Process, netstat
        - Linux: ps aux, netstat -tulpn, ss -tulpn
        - Mac: ps aux, netstat -an, lsof -i
        """
        
        if os_type == 'windows':
            return await self._execute_powershell(device_id, command)
        elif os_type == 'linux':
            return await self._execute_ssh(device_id, command)
        elif os_type == 'mac':
            return await self._execute_ssh(device_id, command)
    
    async def capture_memory(
        self, 
        case_id: str, 
        device_id: str,
        format: str = 'minidump'  # minidump | full | custom
    ) -> Dict:
        """
        Captura memoria RAM del endpoint
        """
        # 1. Deploy herramienta de captura
        # 2. Ejecutar captura
        # 3. Descargar archivo
        # 4. Analizar con Volatility
        pass
    
    async def capture_network(
        self, 
        case_id: str, 
        device_id: str,
        duration: int = 30  # segundos
    ) -> Dict:
        """
        Captura tráfico de red
        """
        # 1. Iniciar packet capture (tcpdump/Wireshark)
        # 2. Capturar durante X segundos
        # 3. Descargar PCAP
        # 4. Analizar con Suricata/Zeek
        pass
    
    async def hunt_process(
        self, 
        case_id: str, 
        device_id: str,
        pattern: str  # regex o wildcard
    ) -> List[Dict]:
        """
        Busca procesos en tiempo real
        
        Ejemplo:
        - pattern="svc*" → Procesos svchost
        - pattern=".*powershell.*" → PowerShell
        - pattern="???.exe" → Procesos de 3 caracteres
        """
        pass
    
    async def get_file_info(
        self, 
        case_id: str, 
        device_id: str,
        file_path: str
    ) -> Dict:
        """
        Obtiene información de archivo en tiempo real
        """
        # Metadatos: tamaño, fecha, hash MD5/SHA256
        # VirusTotal: Escanear el archivo
        # Permisos: NTFS permissions (Windows)
        pass

# Ejemplo de uso en API
@router.post("/forensics/investigation/active/execute")
async def active_investigation(request: ActiveInvestigationRequest):
    """
    POST /forensics/investigation/active/execute
    {
      "case_id": "IR-2025-001",
      "device_id": "WORKSTATION-01",
      "actions": [
        {
          "type": "command",
          "os_type": "windows",
          "command": "tasklist /v",
          "description": "Listar procesos detallado"
        },
        {
          "type": "process_hunt",
          "pattern": "svc*",
          "description": "Buscar procesos sospechosos"
        },
        {
          "type": "memory_capture",
          "format": "minidump",
          "description": "Capturar memoria"
        }
      ]
    }
    """
    service = ActiveInvestigationService()
    results = await service.execute_investigation(request)
    return results
```

---

## 📋 TABLA DE PRIORIDADES

| Prioridad | Feature | Esfuerzo | Impacto | Viabilidad |
|-----------|---------|---------|--------|-----------|
| 🔴 P0 | UI/UX Rediseño React | 🔴🔴🔴 | 🟢🟢🟢 | 🟢🟢🟢 |
| 🔴 P0 | Mobile Agent (Intune/OSQuery) | 🟠🟠 | 🟢🟢🟢 | 🟢🟢🟢 |
| 🔴 P0 | Investigaciones Activas | 🟠🟠🟠 | 🟢🟢🟢 | 🟢🟢 |
| 🟠 P1 | Validación En Línea | 🟢🟢 | 🟠🟠 | 🟢🟢🟢 |
| 🟠 P1 | Threat Hunting Automático | 🟠🟠🟠 | 🟠🟠 | 🟢🟢 |
| 🟠 P1 | Reportes Automáticos | 🟢🟢 | 🟠🟠 | 🟢🟢🟢 |
| 🟡 P2 | WebSocket (Real-time) | 🟠🟠 | 🟠 | 🟢🟢 |
| 🟡 P2 | Colaboración Multi-usuario | 🟠🟠🟠 | 🟠 | 🟠 |

---

## ✅ PLAN DE IMPLEMENTACIÓN (RECOMENDADO)

### **Fase 1: MVP Rediseño UI (2-3 semanas)**
```
├─ Crear estructura React + Sidebar
├─ Implementar Dashboard visual
├─ Forms con validación en línea
└─ Integración con backend actual
```

### **Fase 2: Mobile Agent (1-2 semanas)**
```
├─ Integración Intune
├─ Support OSQuery
└─ Links de descarga públicos
```

### **Fase 3: Investigaciones Activas (2-3 semanas)**
```
├─ Endpoint Command Execution
├─ Memory Capture
├─ Network Capture
└─ Process Monitoring
```

### **Fase 4: Threat Hunting Automático (1-2 semanas)**
```
├─ Query Builder
├─ Hunt Scheduler
└─ Auto-correlation
```

---

**Total Estimado**: 6-10 semanas para sistema completo profesional

---

**Documento Generado**: 2025-12-05  
**Versión**: 1.0  
**Status**: ✅ COMPLETO
