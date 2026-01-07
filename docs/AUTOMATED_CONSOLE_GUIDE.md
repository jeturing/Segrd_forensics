# Guía: Consola Automatizada de Análisis Forense

## Descripción General

La **Consola Automatizada** es una interfaz interactiva integrada en el dashboard M365 que permite:

- ✅ Ejecutar análisis forenses de forma automatizada
- ✅ Monitorear el progreso en tiempo real con logs en consola
- ✅ Tomar decisiones interactivas durante la extracción de datos
- ✅ Configurar opciones de extracción avanzadas
- ✅ Auditar todas las acciones realizadas

## Ubicación en la UI

```
┌─ M365 Forensics Dashboard
│
├─ Tarjeta: "Selecciona herramientas" (parte superior)
│  └─ Seleccionar tools por categoría (BÁSICO, RECONOCIMIENTO, etc.)
│
├─ Tarjeta: "Comandos Automatizados" ⬅️ NUEVA
│  ├─ Consola de Ejecución (terminal-style)
│  ├─ Panel de Decisión Interactiva (si es necesario)
│  ├─ Opciones de Extracción (checkboxes)
│  └─ Información del Análisis (metadata)
│
└─ Tarjeta: "Señales de Identidad"
```

## Componentes de la Consola

### 1. **Consola de Ejecución**

Terminal estilo *nix con auto-scroll que muestra:

```
$ Iniciando análisis forense para caso IR-2024-001...
$ Herramientas: 4 seleccionadas
$ Usuarios objetivo: 3
$ Opciones activas: Usuarios inactivos, Buzones archivados
$ ✅ Análisis iniciado - ID: FA-2025-00001
```

**Colores por tipo de mensaje:**
- 🔵 Azul (`text-gray-300`): Información general
- 🟢 Verde (`text-green-400`): Éxito/completado
- 🔴 Rojo (`text-red-400`): Error
- 🟡 Amarillo (`text-yellow-400`): Advertencia
- 🟣 Púrpura (`text-purple-400`): Prompt/decisión requerida

### 2. **Panel de Decisión Interactiva**

Aparece cuando el análisis necesita confirmación del usuario:

```
┌────────────────────────────────────────┐
│ ❓ ¿Incluir buzones de servicio?       │
│                                        │
│  [✅ Sí]  [❌ No]                     │
└────────────────────────────────────────┘
```

**Decisiones típicas:**
- "¿Incluir usuarios inactivos (>90 días)?"
- "¿Exportar Unified Audit Logs (puede tomar >30 min)?"
- "¿Incluir objetos eliminados del Recycle Bin?"
- "¿Ejecutar scanning de malware (recursos CPU/Memory)?"

### 3. **Opciones de Extracción**

Checkboxes para configurar el comportamiento:

```
☐ Incluir usuarios inactivos (>90 días)
☐ Incluir usuarios externos (B2B)
☐ Incluir buzones archivados
☐ Incluir objetos eliminados (últimos 30 días)
```

Estas opciones se envían al backend para personalizar cada herramienta:

| Opción | SPARROW | HAWK | O365 | AzureHound | ROADtools |
|--------|---------|------|------|-----------|-----------|
| Incluir Inactivos | ✅ | ❌ | ✅ | ✅ | ✅ |
| Incluir Externos | ✅ | ❌ | ✅ | ✅ | ❌ |
| Incluir Archivados | ✅ | ✅ | ✅ | ❌ | ❌ |
| Incluir Eliminados | ❌ | ❌ | ✅ | ❌ | ❌ |

### 4. **Información del Análisis**

Metadatos mostrados en formato tabla:

```
ID Análisis:    FA-2025-00001
Herramientas:   4 seleccionadas
Caso:           IR-2024-001
Iniciado:       2025-01-10 14:23:45
```

## Flujo de Trabajo: Paso a Paso

### Paso 1: Seleccionar Herramientas

En la tarjeta "Selecciona herramientas", marca los tools:

```
BÁSICO (3)
  ☑ Sparrow      (🦅 Tokens abusados y apps OAuth)
  ☑ Hawk         (🦅 Reglas maliciosas, delegaciones y Teams)
  ☐ O365         (📦 Unified Audit Logs completos)

RECONOCIMIENTO (3)
  ☑ AzureHound   (🐕 Attack paths BloodHound)
  ☐ ROADtools    (🗺️ Reconocimiento completo de Azure AD)
  ☐ AADInternals (🔓 Red Team Azure AD)

[Iniciar análisis]  [Actualizar señales]
```

### Paso 2: Configurar Opciones (Opcional)

En la sección "Opciones de extracción" de la consola:

```
☑ Incluir usuarios inactivos (>90 días)
☐ Incluir usuarios externos (B2B)
☑ Incluir buzones archivados
☑ Incluir objetos eliminados (últimos 30 días)
```

### Paso 3: Iniciar Análisis

Haz clic en **[Iniciar análisis]**. La consola se llenará automáticamente con logs:

```
$ Iniciando análisis forense para caso IR-2024-001...
$ Herramientas: 4 seleccionadas
$ Usuarios objetivo: 3
$ Opciones activas: Usuarios inactivos, Buzones archivados
$ ✅ Análisis iniciado - ID: FA-2025-00001
$ Ejecutando: Sparrow...
```

### Paso 4: Responder Decisiones (Si es necesario)

Cuando la consola muestre un prompt en púrpura:

```
$ Ejecutando: O365 Extractor
$ ⚠️ Esta operación puede tomar >30 minutos
```

El panel de decisión aparecerá automáticamente:

```
┌────────────────────────────────────────┐
│ ❓ ¿Continuar con extracción completa?│
│                                        │
│  [✅ Sí]  [❌ No]                     │
└────────────────────────────────────────┘
```

Selecciona tu opción:
- **Sí**: Continúa con la extracción completa
- **No**: Usa modo rápido (últimas 24 horas)

### Paso 5: Monitorear Progreso

La consola muestra el estado en tiempo real:

```
$ Ejecutando: Sparrow...
$ ✅ Sparrow completado - 12 hallazgos
$ Ejecutando: Hawk...
$ Ejecutando: AzureHound...
$ ✅ AzureHound completado - 5 rutas de ataque
$ Análisis completado en 15 minutos
$ Total de evidencia: 23 archivos
```

### Paso 6: Ver Resultados

Una vez completado:

```
┌────────────────────────────────────────┐
│ ✅ Completado                          │
│                                        │
│ [📊 Ver Grafo de Ataque]               │
│ [📋 Ver Caso]                          │
│ [📁 23 archivos de evidencia]          │
└────────────────────────────────────────┘
```

## Comandos Automatizados Predefinidos

El sistema proporciona "recetas" de análisis automático:

### 🏃 **Análisis Rápido (< 5 min)**
```
Herramientas: Sparrow, Hawk
Opciones: Sin usuarios inactivos, sin archivados
Perfil: Compromiso activo/inmediato
```

### 🔍 **Análisis Completo (30-60 min)**
```
Herramientas: Todos (12 tools)
Opciones: Con todos los filtros
Perfil: Investigación exhaustiva
```

### 🎯 **Análisis Dirigido (10-20 min)**
```
Herramientas: Sparrow, O365, AzureHound
Opciones: Usuarios inactivos, archivados
Perfil: Búsqueda de actividad sospechosa
```

### 🛡️ **Análisis de Cumplimiento (20-30 min)**
```
Herramientas: Monkey365, Maester, AADInternals
Opciones: Todos los filtros
Perfil: Evaluación de seguridad/normativa
```

## Funcionalidades Avanzadas

### Integración con ForensicAnalysis

Cada análisis genera un registro **ForensicAnalysis** con:

- **ID único**: `FA-YYYY-XXXXX` (ej: `FA-2025-00001`)
- **Auditoría completa**:
  - Quién ejecutó (usuario)
  - Cuándo (timestamp)
  - Qué herramientas
  - Qué opciones se usaron
  - Decisiones del usuario
- **Versionado**: Puedes ejecutar el mismo análisis múltiples veces, cada una con nuevo ID
- **Cadena de custodia**: Cada archivo de evidencia vinculado

### Exportar Sesión de Análisis

Descarga el registro completo:
```json
{
  "analysis_id": "FA-2025-00001",
  "case_id": "IR-2024-001",
  "executed_by": "analyst@empresa.com",
  "executed_at": "2025-01-10T14:23:45Z",
  "tools": ["sparrow", "hawk", "azurehound"],
  "extraction_options": {
    "includeInactive": true,
    "includeArchived": true
  },
  "user_decisions": [
    {
      "question": "¿Continuar con extracción completa?",
      "answer": true,
      "timestamp": "2025-01-10T14:25:00Z"
    }
  ],
  "findings": [ ... ],
  "duration_seconds": 900,
  "status": "completed"
}
```

### Reproducibilidad

Guarda un "snapshot" de análisis para:
- Reproducir investigación más tarde
- Compartir configuración con otros analistas
- Comparar resultados antes/después de cambios

## Troubleshooting

### ❌ "Selecciona herramientas para iniciar"

**Problema**: La consola dice esto pero tienes herramientas seleccionadas.

**Solución**: 
1. Verifica que `analysisForm.scope` tenga elementos
2. Abre DevTools (F12) → Console
3. Escribe `console.log(analysisForm.scope)` para verificar

### ❌ Consola no muestra logs

**Problema**: Inició análisis pero la consola está vacía.

**Solución**:
1. Verifica que `executionLog` se esté actualizando
2. Comprueba en la pestaña Network que la API responde
3. Mira los logs del backend: `tail -f logs/mcp-forensics.log`

### ❌ Panel de decisión no aparece

**Problema**: El análisis necesita confirmación pero no sale el diálogo.

**Solución**:
1. El backend debe enviar `pendingDecision` en la respuesta
2. Verifica que el endpoint de análisis devuelva:
   ```json
   {
     "status": "waiting_for_decision",
     "pending_decision": {
       "question": "¿Continuar con extracción?"
     }
   }
   ```

## API Backend Esperada

### Endpoint: `POST /forensics/m365/analyze`

**Request:**
```json
{
  "tenant_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "case_id": "IR-2024-001",
  "scope": ["sparrow", "hawk", "azurehound"],
  "target_users": ["user@empresa.com"],
  "extraction_options": {
    "includeInactive": true,
    "includeArchived": false
  },
  "days_back": 90
}
```

**Response (inicial):**
```json
{
  "status": "queued",
  "analysis_id": "FA-2025-00001",
  "task_id": "task-xxx-yyy-zzz"
}
```

**Response (progreso):**
```json
{
  "status": "running",
  "current_tool": "sparrow",
  "progress_percentage": 25,
  "log_entries": [
    {"type": "info", "message": "Ejecutando Sparrow..."},
    {"type": "success", "message": "✅ Sparrow completado - 12 hallazgos"}
  ]
}
```

**Response (con decisión pendiente):**
```json
{
  "status": "waiting_for_decision",
  "current_tool": "o365_extractor",
  "pending_decision": {
    "question": "¿Continuar con extracción completa (>30 min)?",
    "options": ["continue", "skip"]
  }
}
```

## Notas Importantes

⚠️ **Auto-scroll**: La consola automáticamente hace scroll al final cuando se agregan logs.

⚠️ **Persistencia**: Los logs se limpian cuando inicia un nuevo análisis.

⚠️ **Timeouts**: Los análisis con >4 horas se cancelan automáticamente (configurable).

⚠️ **Permisos**: Requiere permisos de API en Azure AD:
- `AuditLog.Read.All`
- `User.Read.All`
- `Directory.Read.All`
- `SecurityEvents.Read.All`

## Próximas Mejoras

- [ ] Guardar/cargar configuraciones de análisis
- [ ] Graficar timeline de eventos encontrados
- [ ] Integración con Graph para visualizar relaciones
- [ ] Exportar análisis a PDF/HTML
- [ ] Comparar resultados de múltiples análisis
- [ ] Alert automático cuando se detecten IOCs
