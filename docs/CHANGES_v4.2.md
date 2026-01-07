# Cambios de UI v4.2: Consola Automatizada de Análisis Forense

## Resumen Ejecutivo

Se ha implementado una **Consola Interactiva Integrada** en el dashboard M365 que permite:

1. ✅ Ejecutar análisis forenses con visualización en tiempo real
2. ✅ Tomar decisiones interactivas mediante interface gráfica
3. ✅ Monitorear progreso con logs estilo terminal
4. ✅ Configurar opciones avanzadas de extracción
5. ✅ Auditar todas las acciones en ForensicAnalysis records

## Nueva Arquitectura de Componentes

### 1. **Tarjeta "Comandos Automatizados"** (Nueva)

```
┌─────────────────────────────────────────────────────┐
│ 💻 Comandos Automatizados                           │
│                                                     │
│ ┌─ Consola de Ejecución ─────────────────────────┐ │
│ │ $ Iniciando análisis forense para IR-2024...  │ │
│ │ $ Herramientas: 4 seleccionadas               │ │
│ │ $ Ejecutando: Sparrow...                      │ │
│ │ $ ✅ Sparrow completado - 12 hallazgos       │ │
│ │ $ Ejecutando: Hawk...                         │ │
│ │ $ Ejecutando: AzureHound...                   │ │
│ │ $ ✅ Análisis completado en 15 minutos       │ │
│ │ $ ▌                                           │ │
│ └────────────────────────────────────────────────┘ │
│                                                     │
│ ┌─ Panel de Decisión (Condicional) ─────────────┐ │
│ │ ❓ ¿Incluir buzones archivados?               │ │
│ │                                                 │ │
│ │  [✅ Sí]  [❌ No]                            │ │
│ └────────────────────────────────────────────────┘ │
│                                                     │
│ ┌─ Opciones de Extracción ───────────────────────┐ │
│ │ ☐ Incluir usuarios inactivos (>90 días)      │ │
│ │ ☑ Incluir usuarios externos (B2B)            │ │
│ │ ☑ Incluir buzones archivados                 │ │
│ │ ☐ Incluir objetos eliminados (últimos 30d)   │ │
│ └────────────────────────────────────────────────┘ │
│                                                     │
│ ┌─ Información del Análisis ─────────────────────┐ │
│ │ ID Análisis:    FA-2025-00001                 │ │
│ │ Herramientas:   4 seleccionadas               │ │
│ │ Caso:           IR-2024-001                   │ │
│ │ Iniciado:       2025-01-10 14:23:45           │ │
│ └────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

**Ubicación en layout:**
- Aparece entre "Progreso del Análisis" y "Señales de Identidad y Auditoría"
- En la columna izquierda (espacio principal)
- Scrolleable con max-height: 96 (24rem × 4)

## Cambios en el Componente M365.jsx

### Imports Añadidos
```jsx
import { CommandLineIcon } from '@heroicons/react/24/outline';
```

### Nuevo Estado

```jsx
// Estado de consola interactiva y opciones de extracción
const [executionLog, setExecutionLog] = useState([]);
const [pendingDecision, setPendingDecision] = useState(null);
const [extractionOptions, setExtractionOptions] = useState({
  includeInactive: false,
  includeExternal: false,
  includeArchived: false,
  includeDeleted: false
});
```

### Nuevas Referencias

```jsx
const consoleRef = useRef(null); // Para auto-scroll de consola
```

### Nuevo useEffect

```jsx
// Auto-scroll de consola cuando se agrega un nuevo log
useEffect(() => {
  if (consoleRef.current) {
    consoleRef.current.scrollTop = consoleRef.current.scrollHeight;
  }
}, [executionLog]);
```

### Nuevas Funciones

#### `handleAnalyze()` - Mejorada

Ahora agrega logs a la consola durante la ejecución:

```jsx
const handleAnalyze = async () => {
  // ... validaciones ...
  
  // Limpiar consola anterior
  setExecutionLog([]);
  setAnalysisRunning(true);
  
  try {
    // Agregar logs iniciales
    setExecutionLog(prev => [...prev, {
      type: 'info',
      message: `Iniciando análisis forense para caso ${analysisForm.caseId}...`
    }]);
    
    // ... resto de lógica ...
    
    setExecutionLog(prev => [...prev, {
      type: 'success',
      message: `✅ Análisis iniciado - ID: ${result.task_id}`
    }]);
    
    // ... actualizar activeAnalysis con analysisId ...
  } catch (error) {
    setExecutionLog(prev => [...prev, {
      type: 'error',
      message: `❌ Error: ${detail}`
    }]);
  }
};
```

#### `handleDecision(answer)` - Nueva

Captura decisiones del usuario y las registra en logs:

```jsx
const handleDecision = (answer) => {
  if (!pendingDecision) return;
  
  setExecutionLog(prev => [...prev, {
    type: 'success',
    message: `Usuario respondió: ${answer ? '✅ SÍ' : '❌ NO'} a "${pendingDecision.question}"`
  }]);
  
  // Procesar decisión...
  setPendingDecision(null);
};
```

## Estructura de Datos de Log

Cada entrada en `executionLog` tiene:

```typescript
interface LogEntry {
  type: 'info' | 'success' | 'error' | 'warning' | 'prompt';
  message: string;
  timestamp?: string;
  data?: any;
}
```

**Colores por tipo:**

| Tipo | Color | Ejemplo |
|------|-------|---------|
| `info` | Gris (`text-gray-300`) | `Iniciando análisis...` |
| `success` | Verde (`text-green-400`) | `✅ Completado` |
| `error` | Rojo (`text-red-400`) | `❌ Error: conexión fallida` |
| `warning` | Amarillo (`text-yellow-400`) | `⚠️ Timeout próximo` |
| `prompt` | Púrpura (`text-purple-400`) | `❓ Continuar?` |

## Estructura de Datos de Decisión Pendiente

```typescript
interface PendingDecision {
  question: string;
  options?: string[];
  timeout?: number;
  tool?: string;
}
```

Ejemplo:
```jsx
setPendingDecision({
  question: "¿Incluir buzones archivados?",
  options: ["yes", "no"],
  timeout: 300000, // 5 minutos
  tool: "o365_extractor"
});
```

## Estructura de Opciones de Extracción

```typescript
interface ExtractionOptions {
  includeInactive: boolean;    // Usuarios sin actividad >90 días
  includeExternal: boolean;    // Usuarios B2B/guest
  includeArchived: boolean;    // Buzones archivados
  includeDeleted: boolean;     // Objetos en Recycle Bin (<30 días)
}
```

Se envían al backend en cada solicitud de análisis:

```json
{
  "tenant_id": "...",
  "case_id": "...",
  "scope": [...],
  "extraction_options": {
    "includeInactive": true,
    "includeExternal": false,
    "includeArchived": true,
    "includeDeleted": false
  }
}
```

## Cambios en activeAnalysis

El objeto `activeAnalysis` ahora incluye:

```jsx
{
  taskId: string;           // ID de tarea en backend
  analysisId: string;       // FA-YYYY-XXXXX nuevo
  caseId: string;           // ID del caso
  scope: string[];          // Tools seleccionadas
  startedAt: ISO8601;       // Timestamp de inicio
}
```

## Integración con ForensicAnalysis Backend

Cada análisis que se ejecuta desde la consola debe:

1. **Crear un nuevo registro ForensicAnalysis:**
   ```
   FA-2025-00001 (generado con counter)
   ```

2. **Registrar todos los parámetros:**
   - Herramientas ejecutadas
   - Opciones de extracción
   - Usuarios objetivo
   - Decisiones del usuario

3. **Auditar las acciones:**
   - Quién ejecutó (usuario)
   - Cuándo (timestamp)
   - Qué respondió (yes/no para cada prompt)
   - Duración total

4. **Vincular evidencia:**
   - Todos los archivos generados → CaseEvidence
   - Todos los CaseEvidence → ForensicAnalysis

## Flujos de Ejecución

### Flujo 1: Análisis Sin Decisiones

```
Usuario selecciona tools
        ↓
[Iniciar análisis]
        ↓
Log: "Iniciando análisis..."
        ↓
API Request con extraction_options
        ↓
Log: "Ejecutando: Sparrow..."
        ↓
API Response: completado
        ↓
Log: "✅ Sparrow completado - 12 hallazgos"
        ↓
Log: "Ejecutando: Hawk..."
        ↓
... (repite por cada tool)
        ↓
Log: "✅ Análisis completado"
        ↓
Mostrar "Ver Grafo", "Ver Caso"
```

### Flujo 2: Análisis Con Decisiones

```
Usuario selecciona tools
        ↓
[Iniciar análisis]
        ↓
API Request
        ↓
API Response: "waiting_for_decision"
        ↓
Log: "❓ ¿Continuar?" (púrpura)
        ↓
Mostrar: Panel de Decisión Interactiva
        ↓
[✅ Sí]  ← Usuario clickea
        ↓
handleDecision(true)
        ↓
Log: "Usuario respondió: ✅ SÍ"
        ↓
setExtractionOptions actualiza
        ↓
API Resume con nueva config
        ↓
Log: "Reanudando extracción..."
        ↓
... (continúa análisis)
```

## Testing en Desarrollo

### 1. Iniciar Frontend

```bash
cd /home/hack/mcp-kali-forensics/frontend-react
npm run dev
# Abre http://localhost:3000
```

### 2. Ir a M365 Tab

```
http://localhost:3000/m365
```

### 3. Verificar Consola Visible

Debería ver:
- Card title: "💻 Comandos Automatizados"
- Console area vacía (gris oscuro)
- Sección de opciones (4 checkboxes)

### 4. Pruebas Manuales

**Test 1: Logging básico**
```jsx
// En console del navegador (DevTools)
// Simular log añadido
setExecutionLog(prev => [...prev, {
  type: 'info',
  message: 'Test manual de log'
}]);
```

**Test 2: Auto-scroll**
- Agregar muchos logs
- Verificar que la consola hace scroll automático

**Test 3: Decisión interactiva**
```jsx
// Simular prompt
setPendingDecision({
  question: "¿Incluir usuarios inactivos?"
});
```

**Test 4: Cambiar opciones**
- Marcar/desmarcar checkboxes
- Verificar que `extractionOptions` se actualiza

## Configuración CSS

Las clases Tailwind usadas:

```css
/* Consola */
.bg-gray-950              /* Fondo muy oscuro */
.border-gray-700          /* Borde gris */
.font-mono                /* Fuente monoespaciada */
.max-h-96                 /* Altura máxima */
.overflow-y-auto          /* Scroll vertical */

/* Logs */
.text-gray-300            /* Información */
.text-green-400           /* Éxito */
.text-red-400             /* Error */
.text-yellow-400          /* Advertencia */
.text-purple-400          /* Prompt */

/* Panel de decisión */
.bg-purple-900/20         /* Fondo púrpura semi-transparente */
.border-purple-700        /* Borde púrpura */

/* Opciones */
.bg-gray-800/50           /* Fondo gris semi-transparente */
.bg-blue-900/20           /* Info panel */
```

## Compatibilidad

- ✅ React 18+
- ✅ Tailwind CSS 3+
- ✅ Heroicons 24+
- ✅ Modern browsers (Chrome, Firefox, Safari, Edge)
- ✅ Responsive (adapta a mobile con grid columns)

## Performance

- **Consola ref**: Actualización O(1) del scroll
- **Log entries**: Array push O(1) por entrada
- **Re-renders**: Solo cuando `executionLog` o `pendingDecision` cambia
- **Memory**: Máximo 1000 logs en buffer (limpiar entre análisis)

## Próximas Integraciones

1. **Backend ForensicAnalysis API:**
   ```
   POST /forensics/m365/analyze
   GET /forensics/analyses/{analysis_id}
   PUT /forensics/analyses/{analysis_id}/decision
   ```

2. **WebSocket para actualizaciones en tiempo real:**
   ```javascript
   ws.on('analysis:log', (log) => setExecutionLog(...));
   ws.on('analysis:decision_required', (decision) => setPendingDecision(...));
   ```

3. **Persistencia en IndexedDB:**
   ```javascript
   // Guardar logs localmente para reproducción
   indexedDB.databases[caseId].logs
   ```

4. **Export a JSON/HTML:**
   ```javascript
   downloadAnalysisSession(analysisId, format: 'json' | 'html');
   ```

## Archivos Modificados

- `frontend-react/src/components/M365/M365.jsx` - Consola integrada
- `frontend-react/src/components/Common/Card.jsx` - Sin cambios
- `frontend-react/src/components/Common/Button.jsx` - Sin cambios

## Archivos Nuevos

- `docs/AUTOMATED_CONSOLE_GUIDE.md` - Guía de usuario
- `docs/CHANGES_v4.2.md` - Este documento

## Rollback (Si es necesario)

Si necesitas volver a versión anterior:

```bash
git revert <commit-hash>
# Eliminar estado:
git rm docs/AUTOMATED_CONSOLE_GUIDE.md
git rm docs/CHANGES_v4.2.md
```

---

**Versión**: 4.2 RC1  
**Fecha**: 2025-01-10  
**Estado**: Listos para testing de integración con backend
