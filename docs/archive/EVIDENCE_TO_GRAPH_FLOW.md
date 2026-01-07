# 📊 Flujo: Evidencia a Grafo de Ataque

## Descripción General

Cuando investigas un caso y recopilas evidencia, ahora puedes visualizarla automáticamente en el grafo de ataque. El sistema extrae IOCs (Indicadores de Compromiso) de los archivos de evidencia y los agrega como nodos en el grafo visual.

## Flujo de Trabajo

```
1. Abrir Dashboard
   ↓
2. Cargar Caso (IR-2025-001)
   ↓
3. Ver Botón "Investigar" o "Ver en Grafo"
   ↓
4. Hacer Clic → Se Actualiza Estado a "investigating"
   ↓
5. Sistema Extrae IOCs de Archivos de Evidencia:
   - oauth_consents.json → Aplicaciones sospechosas
   - inbox_rules.json → Reglas de buzón maliciosas
   - risky_signins.json → IPs sospechosas
   - investigation_summary.json → Compromisos detectados
   ↓
6. IOCs se Agregan al Grafo como Nodos Coloreados:
   - 🔴 ROJO (crítico/alto): Amenazas serias
   - 🟠 NARANJA (medio): Actividad sospechosa
   - 🟢 VERDE (bajo): Anomalías detectadas
   ↓
7. Grafo se Reorganiza Automáticamente con Animación
   ↓
8. Se Muestra Notificación de Éxito
```

## Componentes Técnicos

### 1. Backend - Extracción de IOCs (`api/services/dashboard_data.py`)

**Nueva Función**: `extract_iocs_from_evidence(case_id)`

```python
def extract_iocs_from_evidence(self, case_id: str) -> List[Dict]:
    """
    Lee archivos de evidencia y extrae IOCs estructurados
    
    Archivos procesados:
    - ~/forensics-evidence/{case_id}/m365_graph/oauth_consents.json
    - ~/forensics-evidence/{case_id}/m365_graph/inbox_rules.json
    - ~/forensics-evidence/{case_id}/m365_graph/risky_signins.json
    - ~/forensics-evidence/{case_id}/m365_graph/investigation_summary.json
    
    Retorna: Lista de IOCs con tipo, valor, severidad y detalles
    """
```

**Tipos de IOCs Extraídos**:

| Archivo | Tipo IOC | Severidad | Descripción |
|---------|----------|-----------|-------------|
| oauth_consents.json | application | HIGH | Apps con permisos Mail/EWS/user_impersonation |
| inbox_rules.json | email_rule | MEDIUM | Reglas de buzón configuradas |
| risky_signins.json | ip_address | HIGH | IPs desde inicios de sesión arriesgados |
| investigation_summary.json | user_account | CRITICAL | Cuentas potencialmente comprometidas |

### 2. API Endpoint - Obtención de Caso (`api/routes/dashboard.py`)

**GET `/api/dashboard/cases/{case_id}`**

```json
{
  "case": {
    "case_id": "IR-2025-001",
    "status": "investigating",
    "priority": "critical",
    ...
  },
  "iocs": [
    {
      "type": "application",
      "value": "Email (2271cddb-5a4d-4d66-bcd9-79f4a4c8d3be)",
      "severity": "high",
      "source": "oauth_consents.json",
      "details": "Scope: EWS.AccessAsUser.All"
    },
    ...
  ],
  "evidence": {
    "exists": true,
    "files": [
      {
        "name": "audit_logs.json",
        "path": "m365_graph/audit_logs.json",
        "size_kb": 0.0
      },
      ...
    ]
  }
}
```

### 3. Frontend - Visualización en Grafo (`api/templates/dashboard.html`)

**Nueva Función**: `sendEvidenceToGraph(caseId)`

```javascript
// Envía evidencia al grafo de ataque
// 1. Cambia a pestaña "Grafo"
// 2. Llama a loadEvidenceToGraph()
// 3. Muestra notificación con count de IOCs
```

**Función Mejorada**: `loadEvidenceToGraph(caseId)`

```javascript
// Procesa los IOCs y los agrega al grafo Cytoscape:
// 1. Fetch del caso con IOCs
// 2. Por cada IOC:
//    - Crea nodo con color según severidad
//    - ID único: ioc-{caseId}-{index}
//    - Etiqueta: valor truncado a 20 caracteres
// 3. Por cada archivo de evidencia:
//    - Crea nodo de tipo "file" en color púrpura
// 4. Re-organiza grafo con layout fcose
// 5. Anima durante 500ms
// 6. Notifica al usuario
```

**Paleta de Colores**:

```javascript
Severidad HIGH   → #ef4444 (Rojo)
Severidad MEDIUM → #f97316 (Naranja)
Severidad LOW    → #22c55e (Verde)
Tipo FILE        → #8b5cf6 (Púrpura)
```

## Botones de Acción

En la modal de detalle del caso:

| Botón | Función | Resultado |
|-------|---------|-----------|
| 🔍 **Investigar** | Marca caso como "investigating" | Estado actualizado en DB |
| 📊 **Ver en Grafo** | Envía evidencia al grafo explícitamente | IOCs visualizados en grafo |
| ✅ **Cerrar** | Marca caso como "closed" | Caso finalizado |
| 📝 **Nota** | Agrega nota al caso | Se registra en activity_log |

## Ejemplo de Flujo Completo

### Paso 1: Abrir Dashboard

```bash
# Servidor ejecutándose en puerto 9000
curl http://localhost:9000/dashboard
```

### Paso 2: Cargar Caso IR-2025-001

```bash
# API obtiene datos del caso
curl http://localhost:9000/api/dashboard/cases/IR-2025-001

# Respuesta incluye IOCs extraídos de evidencia:
{
  "iocs": [
    {"type": "application", "value": "Email...", "severity": "high"},
    {"type": "ip_address", "value": "185.22.91.14", "severity": "high"},
    {"type": "email_rule", "value": "Forward to external", "severity": "medium"},
    ...
  ]
}
```

### Paso 3: Hacer Clic en "Ver en Grafo"

```javascript
// Frontend ejecuta:
sendEvidenceToGraph("IR-2025-001")

// Que hace:
// 1. Cambia a pestaña "Grafo"
// 2. Carga caso IR-2025-001
// 3. Obtiene lista de IOCs
// 4. Por cada IOC, agrega nodo a Cytoscape:
//    - ID: ioc-IR-2025-001-0
//    - Label: "Email (2271cddb-...)"
//    - Color: #ef4444 (severidad high)
// 5. Re-layout del grafo
// 6. Muestra: "📊 Evidencia agregada al grafo (8 IOCs, 8 archivos)"
```

### Paso 4: Visualización en Grafo

El grafo ahora muestra:

```
┌─────────────────────────────────────┐
│   Attack Graph Visualization        │
│                                     │
│    [Email App]  ──→  [185.22.91]    │
│       🔴           🔴                │
│                                     │
│    [SharePoint]     [Forward Rule]  │
│       🔴                🟠           │
│                                     │
│    [audit_logs.json]  [inbox_rules] │
│         🟣                 🟣        │
└─────────────────────────────────────┘
```

## Archivos Modificados

### 1. `/api/services/dashboard_data.py`

**Cambios**:
- ✅ Agregada función `extract_iocs_from_evidence(case_id)`
- ✅ Procesa 4 tipos de archivos de evidencia
- ✅ Extrae IOCs con severidad y detalles
- ✅ Integración con rutas de evidencia

**Líneas**: ~860 en total

### 2. `/api/routes/dashboard.py`

**Cambios**:
- ✅ Modificado endpoint `GET /api/dashboard/cases/{case_id}`
- ✅ Ahora extrae IOCs de evidencia si no existen en DB
- ✅ Agregada lógica: `iocs = iocs or extract_iocs_from_evidence(case_id)`

### 3. `/api/templates/dashboard.html`

**Cambios**:
- ✅ Agregado botón "📊 Ver en Grafo" en modal de caso
- ✅ Nueva función `sendEvidenceToGraph(caseId)`
- ✅ Mejorada función `loadEvidenceToGraph(caseId)`
- ✅ Integración con Cytoscape para visualización

**Líneas totales**: ~4871

## Pruebas

### Test 1: Verificar Extracción de IOCs

```bash
curl -s http://localhost:9000/api/dashboard/cases/IR-2025-001 | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'IOCs: {len(d[\"iocs\"])}')
for ioc in d['iocs'][:3]:
    print(f'  - {ioc[\"type\"]}: {ioc[\"value\"][:40]}')
"

# Output:
# IOCs: 8
#   - application: Email (2271cddb-5a4d-4d66-bcd9-79f4a4c8d...
#   - application: SharePoint Online Web Client Extensibili...
#   - application: SharePoint Online Web Client Extensibili...
```

### Test 2: Actualizar Estado a "Investigating"

```bash
curl -X PUT http://localhost:9000/api/dashboard/cases/IR-2025-001/status?status=investigating

# Output:
# {"success": true, "case_id": "IR-2025-001", "new_status": "investigating"}
```

### Test 3: Verificar Grafo en UI

1. Abrir http://localhost:9000/dashboard
2. Cargar caso IR-2025-001
3. Hacer clic en botón "Ver en Grafo"
4. ✅ Verificar que aparecen nodos en el grafo
5. ✅ Verificar colores según severidad
6. ✅ Verificar notificación de éxito

## Flujo de Datos Resumido

```
┌─────────────────────────────────────────────────────────────────┐
│ CASO: IR-2025-001                                               │
│ ─────────────────────────────────────────────────────────────── │
│                                                                 │
│ Archivos de Evidencia:                                          │
│ ~/forensics-evidence/IR-2025-001/m365_graph/                    │
│   ├── oauth_consents.json      → Aplicaciones OAuth             │
│   ├── inbox_rules.json         → Reglas de buzón                │
│   ├── risky_signins.json       → IPs sospechosas               │
│   └── investigation_summary.json → Resumen de investigación    │
│                                                                 │
│ ↓ extract_iocs_from_evidence()                                  │
│                                                                 │
│ IOCs Extraídos:                                                 │
│ [                                                               │
│   {type: "application", value: "Email", severity: "high"},      │
│   {type: "ip_address", value: "185.22.91.14", ...},            │
│   {type: "email_rule", value: "Forward", severity: "medium"},  │
│   ...                                                           │
│ ]                                                               │
│                                                                 │
│ ↓ GET /api/dashboard/cases/IR-2025-001                          │
│                                                                 │
│ API Response:                                                   │
│ {                                                               │
│   "case": {...},                                                │
│   "iocs": [...],     ← IOCs para visualizar                     │
│   "evidence": {...}                                             │
│ }                                                               │
│                                                                 │
│ ↓ Frontend: sendEvidenceToGraph()                               │
│                                                                 │
│ Cytoscape Graph Visualization:                                  │
│ [🔴 Email] ──→ [🔴 185.22.91.14] ──→ [🟠 Forward Rule]        │
│                                                                 │
│ ✅ Notificación: "Evidencia agregada al grafo (8 IOCs)"        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Ventajas de Este Flujo

✅ **Automatizado**: No necesita configuración manual  
✅ **Visual**: IOCs aparecen inmediatamente en el grafo  
✅ **Inteligente**: Extrae información relevante de evidencia  
✅ **Escalable**: Soporta múltiples fuentes de IOCs  
✅ **Interactivo**: Botón explícito + estado automático  
✅ **Documentado**: Cada IOC incluye tipo, severidad y fuente  

## Próximas Características

- [ ] Agregar relaciones entre IOCs en el grafo
- [ ] Exportar grafo como imagen/PDF
- [ ] Historial de cambios en el grafo
- [ ] Colaboración multi-usuario en grafo
- [ ] Alertas en tiempo real de nuevos IOCs

---

**Creado**: 2025-12-05  
**Versión**: 1.0  
**Estado**: ✅ Funcional
