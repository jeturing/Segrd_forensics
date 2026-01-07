# 🔧 Especificación Técnica - API de Evidencia a Grafo

## Endpoint Principal

### GET `/api/dashboard/cases/{case_id}`

**Descripción**: Obtiene detalles completos del caso incluyendo IOCs extraídos de evidencia

**Parámetros**:
- `case_id` (string, requerido): ID del caso (ej: `IR-2025-001`)

**Respuesta (200 OK)**:

```json
{
  "case": {
    "id": 6,
    "case_id": "IR-2025-001",
    "title": "Analisis de abuso de envio de correo",
    "description": "",
    "status": "investigating",
    "priority": "critical",
    "created_at": "2025-12-05 16:32:30",
    "updated_at": "2025-12-05T11:33:13.099233",
    "closed_at": null,
    "assigned_to": null,
    "threat_type": "BEC",
    "tenant_id": "3af2e132-c361-4467-9d8b-081f06630c12"
  },
  "iocs": [
    {
      "type": "application",
      "value": "Email (2271cddb-5a4d-4d66-bcd9-79f4a4c8d3be)",
      "severity": "high",
      "source": "oauth_consents.json",
      "details": "Scope: EWS.AccessAsUser.All EWS.AccessAsUser.All"
    },
    {
      "type": "application",
      "value": "SharePoint Online Web Client Extensibility (b7fa6bed-f25f-4496-b2b2-69d85af9f361)",
      "severity": "high",
      "source": "oauth_consents.json",
      "details": "Scope: user_impersonation"
    }
  ],
  "evidence": {
    "exists": true,
    "case_id": "IR-2025-001",
    "files": [
      {
        "name": "audit_logs.json",
        "path": "m365_graph/audit_logs.json",
        "size_kb": 0.0,
        "modified": "2025-12-05T11:32:33.368429"
      },
      {
        "name": "oauth_consents.json",
        "path": "m365_graph/oauth_consents.json",
        "size_kb": 13.96,
        "modified": "2025-12-05T11:32:41.848707"
      }
    ]
  },
  "activity": [],
  "data_source": "real"
}
```

---

## Estructura de IOC

```typescript
interface IOC {
  type: "application" | "ip_address" | "email_rule" | "user_account";
  value: string;                    // Valor del IOC
  severity: "critical" | "high" | "medium" | "low";
  source: string;                   // Archivo de origen
  details: string;                  // Información adicional
}
```

### Tipos de IOC

#### 1. Application (Aplicación OAuth)
```json
{
  "type": "application",
  "value": "Email (2271cddb-5a4d-4d66-bcd9-79f4a4c8d3be)",
  "severity": "high",
  "source": "oauth_consents.json",
  "details": "Scope: EWS.AccessAsUser.All"
}
```

**Cuándo se extrae**: 
- Del archivo `oauth_consents.json`
- Si tiene permisos para Mail, EWS, o user_impersonation

**Severidad**:
- HIGH: Permisos amplios (Mail, EWS, etc.)
- MEDIUM: Permisos limitados
- LOW: Lectura solamente

#### 2. IP Address (Dirección IP)
```json
{
  "type": "ip_address",
  "value": "185.22.91.14",
  "severity": "high",
  "source": "risky_signins.json",
  "details": "User: admin@empresa.com"
}
```

**Cuándo se extrae**:
- Del archivo `risky_signins.json`
- IPs desde inicios de sesión marcados como riesgosos

**Severidad**:
- HIGH: Siempre (si aparece en risky_signins, es riesgosa)

#### 3. Email Rule (Regla de Buzón)
```json
{
  "type": "email_rule",
  "value": "Forward to external",
  "severity": "medium",
  "source": "inbox_rules.json",
  "details": "Actions: 2"
}
```

**Cuándo se extrae**:
- Del archivo `inbox_rules.json`
- Cualquier regla de buzón configurada

**Severidad**:
- MEDIUM: Todas las reglas (reenrutamiento potencial)

#### 4. User Account (Cuenta de Usuario)
```json
{
  "type": "user_account",
  "value": "admin@empresa.com",
  "severity": "critical",
  "source": "investigation_summary.json",
  "details": "Potential compromise"
}
```

**Cuándo se extrae**:
- Del archivo `investigation_summary.json`
- Cuentas marcadas como comprometidas

**Severidad**:
- CRITICAL: Compromiso confirmado

---

## Función de Extracción

### `extract_iocs_from_evidence(case_id: str) -> List[Dict]`

**Ubicación**: `/api/services/dashboard_data.py`

**Descripción**: Extrae IOCs de archivos de evidencia del caso

**Parámetros**:
- `case_id`: ID del caso (ej: `IR-2025-001`)

**Retorna**: Lista de IOCs extraídos

**Archivos Procesados**:

| Archivo | Ruta | IOCs Extraídos |
|---------|------|---|
| OAuth Consents | `~/forensics-evidence/{case_id}/m365_graph/oauth_consents.json` | Aplicaciones con permisos peligrosos |
| Inbox Rules | `~/forensics-evidence/{case_id}/m365_graph/inbox_rules.json` | Reglas de buzón sospechosas |
| Risky SignIns | `~/forensics-evidence/{case_id}/m365_graph/risky_signins.json` | IPs de inicios de sesión arriesgados |
| Investigation Summary | `~/forensics-evidence/{case_id}/m365_graph/investigation_summary.json` | Cuentas potencialmente comprometidas |

---

## Ejemplo de Uso (cURL)

### 1. Obtener Caso con IOCs

```bash
curl -s http://localhost:9000/api/dashboard/cases/IR-2025-001 \
  | python3 -m json.tool
```

**Respuesta esperada**:
```json
{
  "case": {...},
  "iocs": [
    {"type": "application", "value": "Email (...)", "severity": "high"},
    {"type": "application", "value": "SharePoint (...)", "severity": "high"},
    ...
  ],
  "evidence": {...}
}
```

### 2. Extraer Solo IOCs

```bash
curl -s http://localhost:9000/api/dashboard/cases/IR-2025-001 \
  | python3 -c "import sys, json; d=json.load(sys.stdin); [print(f'{ioc[\"type\"]}: {ioc[\"value\"]}') for ioc in d['iocs']]"
```

**Salida esperada**:
```
application: Email (2271cddb-...)
application: SharePoint (b7fa6bed-...)
application: iOS Accounts (b486e9cd-...)
...
```

### 3. Filtrar por Severidad

```bash
curl -s http://localhost:9000/api/dashboard/cases/IR-2025-001 \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
high_risk = [ioc for ioc in d['iocs'] if ioc['severity'] == 'high']
print(f'IOCs de alto riesgo: {len(high_risk)}')
for ioc in high_risk:
    print(f'  - {ioc[\"type\"]}: {ioc[\"value\"]}')
"
```

---

## Flujo de Datos Frontend → Backend

```
Frontend: sendEvidenceToGraph(caseId)
    ↓
    ├─ Cambiar a pestaña grafo
    │
    └─ Frontend: loadEvidenceToGraph(caseId)
         ↓
         ├─ fetch(`/api/dashboard/cases/${caseId}`)
         │
         ├─ Backend: GET /api/dashboard/cases/{caseId}
         │  ├─ get_iocs_by_case(caseId)  [intenta DB]
         │  └─ if empty:
         │     └─ extract_iocs_from_evidence(caseId)  [lee archivos]
         │
         └─ Response con IOCs
              ↓
              ├─ Por cada IOC:
              │  └─ cy.add({id, label, data, style})
              │
              ├─ Por cada archivo de evidencia:
              │  └─ cy.add({id, label, data, style})
              │
              ├─ cy.layout({name: "fcose", animate: true})
              │
              └─ showNotification("Evidencia agregada...")
```

---

## Integración con Cytoscape.js

### Nodo IOC en Grafo

```javascript
cy.add({
  data: {
    id: `ioc-IR-2025-001-0`,
    label: "Email",
    type: "application",
    severity: "high",
    fullValue: "Email (2271cddb-5a4d-4d66-bcd9-79f4a4c8d3be)",
    source: "oauth_consents.json"
  },
  style: {
    'background-color': '#ef4444',  // Rojo
    'width': 40,
    'height': 40,
    'label': 'Email',
    'text-valign': 'center',
    'text-halign': 'center'
  }
});
```

### Colores por Severidad

```javascript
function getSeverityColor(severity) {
  const colors = {
    'critical': '#ef4444',  // Rojo oscuro
    'high': '#ef4444',      // Rojo
    'medium': '#f97316',    // Naranja
    'low': '#22c55e'        // Verde
  };
  return colors[severity] || '#9ca3af';  // Gris por defecto
}
```

### Layout Automático

```javascript
// fcose layout: Fast COSim-based Embedder
cy.layout({
  name: 'fcose',
  animate: true,
  animationDuration: 500,
  randomize: false,
  quality: 'default',
  nodeSpacing: 10,
  edgeElasticity: 0.45
}).run();
```

---

## Manejo de Errores

### Caso no encontrado

**Status**: 404 Not Found

```json
{
  "detail": "Caso IR-XXXX-XXX no encontrado"
}
```

### Archivos de evidencia no existen

**Resultado**: Retorna lista vacía de IOCs

```json
{
  "case": {...},
  "iocs": [],
  "evidence": {"exists": false}
}
```

### Error al leer archivo JSON

**Resultado**: Skip del archivo, continúa con otros

```python
# En extract_iocs_from_evidence():
try:
    with open(oauth_file) as f:
        consents = json.load(f)
except Exception as e:
    print(f"Error processing oauth_consents.json: {e}")
    # Continúa procesando otros archivos
```

---

## Performance

### Tiempos de Respuesta

| Operación | Tiempo | Escalabilidad |
|-----------|--------|---|
| Extracción de IOCs (8 IOCs) | < 100ms | O(n) |
| Serialización JSON | < 50ms | O(n) |
| Transporte de red | 50-200ms | Depende del cliente |
| Renderización Cytoscape | 200-500ms | O(n²) para edges |
| **Total** | **< 1 segundo** | Escalable |

### Optimizaciones Aplicadas

- ✅ Lectura de archivos una sola vez
- ✅ Parsing JSON directo (sin transformaciones extra)
- ✅ Lista comprehension en Python
- ✅ Caché del Cytoscape
- ✅ Layout asincrónico

---

## Formato de Archivos de Entrada

### oauth_consents.json

```json
[
  {
    "clientId": "2271cddb-5a4d-4d66-bcd9-79f4a4c8d3be",
    "consentType": "Principal",
    "id": "281xIk1aZk282Xn0pMjTvkgd7zgunLdHlSmnmGKKD9Z...",
    "principalId": "ff894445-78ad-4657-8bca-d0d2345c848c",
    "resourceId": "38ef1d48-9c2e-47b7-9529-a798628a0fd6",
    "scope": "User.Read",
    "appDisplayName": "Email",
    "appPublisher": null,
    "appHomepage": null
  },
  ...
]
```

### inbox_rules.json

```json
[
  {
    "displayName": "Forward to external",
    "actions": ["forward", "redirectToRecipients"],
    "conditions": {"...": "..."}
  },
  ...
]
```

### risky_signins.json

```json
[
  {
    "userDisplayName": "admin@empresa.com",
    "ipAddress": "185.22.91.14",
    "riskLevel": "high",
    "riskEventType": "unusualActivity",
    "createdDateTime": "2025-12-05T10:30:00Z"
  },
  ...
]
```

### investigation_summary.json

```json
{
  "summary": "Investigation findings",
  "suspicious_ips": ["185.22.91.14", "192.168.1.100"],
  "compromised_accounts": ["admin@empresa.com", "user@empresa.com"],
  "risk_score": 85,
  "recommendations": ["Resetear contraseñas", "Auditar acceso"]
}
```

---

## Validaciones

### Validación de IOC

```python
def validate_ioc(ioc: Dict) -> bool:
    required_fields = {'type', 'value', 'severity', 'source', 'details'}
    return all(field in ioc for field in required_fields)

# Severidades válidas
valid_severities = ['critical', 'high', 'medium', 'low']

# Tipos válidos
valid_types = ['application', 'ip_address', 'email_rule', 'user_account']
```

### Validación de Entrada

```python
# case_id debe ser alfanumérico con guiones
if not re.match(r'^[A-Z]{2}-\d{4}-\d{3}$', case_id):
    raise ValueError(f"Invalid case_id format: {case_id}")
```

---

## Logging

### Ejemplos de Logs

```
[INFO] 🦅 Extrayendo IOCs para caso: IR-2025-001
[INFO] ✅ Nodo IOC agregado: application - Email (2271cddb-...)
[INFO] ✅ Nodo IOC agregado: application - SharePoint (...) 
[INFO] 📊 Evidencia encontrada: 8 IOCs
[INFO] 📊 Layout actualizado con 8 nodos en 500ms
```

---

## Monitoreo y Métricas

### Métricas Disponibles

- Total de IOCs extraídos por caso
- Distribución de severidades
- Archivos de evidencia procesados
- Errores de parsing
- Tiempos de respuesta

### Query de Ejemplo

```bash
# Contar IOCs por severidad
curl -s http://localhost:9000/api/dashboard/cases/IR-2025-001 \
  | python3 -c "
import sys, json, collections
d = json.load(sys.stdin)
counts = collections.Counter(ioc['severity'] for ioc in d['iocs'])
for severity in sorted(counts.keys(), reverse=True):
    print(f'{severity}: {counts[severity]}')
"
```

---

## Casos de Uso

### UC-1: Investigación Inicial Rápida

```bash
# Obtener resumen de amenazas
curl -s http://localhost:9000/api/dashboard/cases/IR-2025-001 \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(f'Caso: {d[\"case\"][\"case_id\"]}')
print(f'Amenazas detectadas: {len(d[\"iocs\"])}')
print(f'Severidad máxima: {max((ioc[\"severity\"] for ioc in d[\"iocs\"]), default=\"none\").upper()}')
"
```

### UC-2: Análisis de Aplicaciones OAuth

```bash
# Listar apps con permisos peligrosos
curl -s http://localhost:9000/api/dashboard/cases/IR-2025-001 \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
apps = [ioc for ioc in d['iocs'] if ioc['type'] == 'application']
for app in apps:
    print(f'{app[\"value\"]} - {app[\"severity\"].upper()}')
"
```

### UC-3: Búsqueda de Cuentas Comprometidas

```bash
# Buscar cuentas críticas
curl -s http://localhost:9000/api/dashboard/cases/IR-2025-001 \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
critical = [ioc for ioc in d['iocs'] if ioc['severity'] in ['critical', 'high'] and ioc['type'] == 'user_account']
for acc in critical:
    print(f'⚠️ {acc[\"value\"]}')
"
```

---

**Versión**: 1.0  
**Última actualización**: 2025-12-05  
**Estado**: ✅ Documentado
