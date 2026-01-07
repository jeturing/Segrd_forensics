# Análisis Unificado de Cuentas - Documentación

## 📋 Resumen

Se ha implementado un **sistema completo de análisis forense de cuentas** que integra todas las herramientas disponibles (M365 Graph API, Sparrow, Hawk, Sherlock) para generar un perfil de riesgo unificado de usuarios.

---

## 🎯 Funcionalidades Implementadas

### 1. **API Endpoints** (`/api/routes/account_analysis_routes.py`)

#### `POST /forensics/accounts/analyze`
Analiza una cuenta individual:
- **Input**: Email, tenant_id, días históricos, incluir OSINT
- **Proceso**:
  - Graph API: Sign-ins de riesgo, eventos de Identity Protection, estado MFA
  - Sparrow: Indicadores de compromiso en Azure AD
  - Hawk: Reglas de buzón maliciosas, delegaciones, OAuth apps
  - Sherlock (opcional): Perfiles en redes sociales
- **Output**: Risk score (0-100), timeline de eventos, recomendaciones

#### `POST /forensics/accounts/analyze-multiple`
Analiza múltiples cuentas en paralelo (máx 50):
- Análisis concurrente (máx 10 simultáneos)
- Identificación de cuentas de alto riesgo
- Risk score promedio
- Reporte agregado

#### `GET /forensics/accounts/{email}/report`
Obtiene reporte de análisis previo (en desarrollo)

#### `GET /forensics/accounts/high-risk`
Lista cuentas de alto riesgo en el tenant (en desarrollo)

---

## 🧮 Algoritmo de Risk Scoring

### Escala: 0-100 puntos

| Categoría | Puntos Máximos | Fuente |
|-----------|----------------|--------|
| **Sign-ins de Riesgo** | 30 | M365 Graph API |
| **Reglas Maliciosas** | 25 | Hawk |
| **OAuth Apps** | 20 | Hawk |
| **OSINT High-Risk** | 15 | Sherlock |
| **Eventos de Riesgo** | 10 | Identity Protection |

### Niveles de Riesgo

- **Critical** (≥70): Compromiso probable, acción inmediata
- **High** (≥50): Actividad sospechosa significativa
- **Medium** (≥30): Anomalías detectadas, investigar
- **Low** (<30): Sin indicadores críticos

### Cálculo Detallado

```python
# Sign-ins de riesgo: hasta 30 puntos
risky_signins * 10 (máx 30)

# Reglas de buzón sospechosas: hasta 25 puntos
suspicious_rules * 12 (máx 25)

# OAuth apps: hasta 20 puntos
oauth_apps * 5 (máx 20)

# Perfiles en plataformas de alto riesgo: hasta 15 puntos
high_risk_platforms * 7 (máx 15)

# Eventos de Identity Protection: hasta 10 puntos
risk_events * 5 (máx 10)
```

---

## 🕒 Timeline de Eventos

Construye cronología unificada de:

1. **Sign-ins anómalos** (Graph API)
   - Ubicaciones inusuales
   - Dispositivos no reconocidos
   - Imposibilidad de viaje

2. **Cambios administrativos** (Sparrow)
   - Elevación de privilegios
   - Creación de usuarios
   - Modificaciones de políticas

3. **Configuración de buzón** (Hawk)
   - Creación de reglas de reenvío
   - Delegaciones de acceso
   - Consentimientos OAuth

4. **Actividad OSINT** (Sherlock)
   - Perfiles encontrados
   - Plataformas de riesgo

Formato de evento:
```json
{
    "timestamp": "2024-12-05T10:30:00Z",
    "event_type": "risky_signin",
    "source": "M365 Graph",
    "description": "Sign-in desde IP sospechosa (185.220.xxx.xxx)",
    "severity": "high",
    "metadata": {
        "ip": "185.220.xxx.xxx",
        "location": "Unknown",
        "risk_level": "high"
    }
}
```

---

## 💡 Recomendaciones Automáticas

El sistema genera recomendaciones basadas en hallazgos:

### Prioridad Critical
- Deshabilitar cuenta comprometida
- Revocar sesiones activas
- Forzar cambio de contraseña

### Prioridad High
- Habilitar MFA
- Revisar reglas de buzón
- Auditar consentimientos OAuth

### Prioridad Medium
- Monitoreo continuo
- Verificar ubicaciones de acceso
- Revisar dispositivos registrados

Formato:
```json
{
    "priority": "critical",
    "title": "Deshabilitar cuenta comprometida",
    "description": "Se detectaron 3 sign-ins de alto riesgo en las últimas 24 horas",
    "action": "Disable-AzureADUser -ObjectId xxx"
}
```

---

## 🖥️ Interfaz de Usuario

### 1. **Modal de Investigación Forense**

Nueva sección "Análisis Unificado de Cuentas":

```html
┌─────────────────────────────────────────────┐
│ ✓ Ejecutar análisis completo de usuarios   │
│   Combina M365, Sparrow, Hawk y Sherlock   │
│   para generar perfil de riesgo            │
│                                             │
│ Usuarios a analizar:                        │
│ ┌─────────────────────────────────────────┐ │
│ │ user1@empresa.com, user2@empresa.com   │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│ ✓ Incluir búsqueda OSINT (Sherlock)       │
└─────────────────────────────────────────────┘
```

### 2. **Tab de Reportes**

Nuevo tab "Análisis de Cuentas" en navegador de evidencias:

```
[Análisis de Cuentas] [M365 Graph] [Sign-ins] [Usuarios] ...
```

### 3. **Vista de Cuenta**

Cada cuenta muestra:

```
┌─────────────────────────────────────────────────────┐
│ 👤 admin@empresa.com              Risk Score: 85/100│
│ Análisis: 2024-12-05 15:30             CRITICAL RISK│
├─────────────────────────────────────────────────────┤
│ 📊 Métricas                                         │
│   ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐             │
│   │  3   │ │  2   │ │  5   │ │  8   │             │
│   │Risky │ │Rules │ │OAuth │ │OSINT │             │
│   └──────┘ └──────┘ └──────┘ └──────┘             │
│                                                      │
│ 📅 Timeline (últimos 10 eventos)                    │
│   2024-12-05 14:20 risky_signin: IP sospechosa     │
│   2024-12-05 12:45 mailbox_rule: Regla reenvío     │
│   2024-12-04 18:30 oauth_consent: App maliciosa    │
│                                                      │
│ 💡 Recomendaciones                                   │
│   🔴 CRITICAL: Deshabilitar cuenta                  │
│   🟠 HIGH: Revocar consentimientos OAuth            │
│   🟡 MEDIUM: Habilitar MFA                          │
└─────────────────────────────────────────────────────┘
```

---

## 🔧 Uso

### Desde Dashboard

1. **Seleccionar caso** en dropdown
2. **Click** en "Ejecutar Investigación Completa"
3. **Activar** checkbox "Análisis Unificado de Cuentas"
4. **Ingresar** emails separados por coma
5. **Opcional**: Activar búsqueda OSINT
6. **Click** "Ejecutar Investigación"
7. **Esperar** resultado (15-48 min según opciones)
8. **Ver** reporte en tab "Análisis de Cuentas"

### Desde API

#### Análisis individual
```bash
curl -X POST http://localhost:9000/forensics/accounts/analyze \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "user_email": "admin@empresa.com",
    "tenant_id": "xxx-tenant-id",
    "days_back": 90,
    "include_osint": true,
    "priority": "high"
  }'
```

#### Análisis múltiple
```bash
curl -X POST http://localhost:9000/forensics/accounts/analyze-multiple \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "user_emails": ["user1@empresa.com", "user2@empresa.com"],
    "tenant_id": "xxx-tenant-id",
    "days_back": 90,
    "include_osint": false
  }'
```

---

## ⚙️ Arquitectura Técnica

### Servicios

```
api/services/account_analysis.py
├── analyze_user_account()          # Análisis individual
├── analyze_multiple_accounts()     # Análisis masivo (max 10 concurrentes)
├── analyze_m365_activity()         # Graph API integration
├── analyze_with_sparrow()          # Sparrow wrapper
├── analyze_with_hawk()             # Hawk wrapper
├── analyze_with_sherlock()         # Sherlock OSINT
├── calculate_unified_risk()        # Risk scoring
├── build_user_timeline()           # Timeline builder
└── generate_recommendations()      # Recommendations engine
```

### Rutas

```
api/routes/account_analysis_routes.py
├── POST /forensics/accounts/analyze
├── POST /forensics/accounts/analyze-multiple
├── GET /forensics/accounts/{email}/report (TODO)
└── GET /forensics/accounts/high-risk (TODO)
```

### Base de Datos

Resultados guardados en:
- **SQLite**: Metadatos y risk scores
- **Filesystem**: 
  ```
  ~/forensics-evidence/{case_id}/
  ├── account_analysis_{email}.json
  ├── sparrow_results.csv
  ├── hawk_results/
  └── sherlock_results/
  ```

---

## 🧪 Testing

Script de prueba completo:

```bash
cd /home/hack/mcp-kali-forensics
python3 scripts/test_account_analysis.py
```

Tests incluidos:
1. ✅ Análisis de cuenta individual
2. ✅ Análisis de múltiples cuentas
3. ✅ Cálculo de risk score

---

## 📈 Duración Estimada

| Opción | Tiempo por Cuenta |
|--------|-------------------|
| **M365 + Sparrow + Hawk** | ~40 min |
| **M365 + Sparrow + Hawk + Sherlock** | ~48 min |
| **Análisis múltiple (10 concurrentes)** | ~8 min por lote |

---

## 🔐 Credenciales Requeridas

### Azure AD
- **Tenant ID**: En configuración M365
- **Permisos Graph API**:
  - `AuditLog.Read.All`
  - `IdentityRiskEvent.Read.All`
  - `User.Read.All`
  - `Directory.Read.All`

### Herramientas
- **Sparrow**: Credenciales Azure AD
- **Hawk**: Exchange Online Management
- **Sherlock**: No requiere credenciales

---

## 🚀 Próximos Pasos

### Funcionalidades Pendientes

1. **Persistencia de Reportes**
   - Guardar análisis histórico en DB
   - Endpoint GET para reportes previos
   - Comparación de análisis (antes/después)

2. **Alertas Automáticas**
   - Webhook cuando risk score > 70
   - Email a SOC con cuentas críticas
   - Integración con SIEM

3. **Enriquecimiento de Datos**
   - Correlación con threat intelligence
   - Análisis de comportamiento (UEBA)
   - Machine learning para anomalías

4. **Optimizaciones**
   - Cache de resultados M365
   - Análisis incremental (solo nuevos eventos)
   - Compresión de evidencias

---

## 📝 Notas de Implementación

### Decisiones de Diseño

1. **Paralelización**: Máximo 10 análisis concurrentes para evitar rate limits de Microsoft Graph API

2. **Timeout**: 5 minutos por herramienta (Sparrow/Hawk/Sherlock) antes de cancelar

3. **Error Handling**: Si una herramienta falla, el análisis continúa con las demás

4. **OSINT Opcional**: Sherlock deshabilitado por defecto (aumenta tiempo 8 minutos)

5. **Risk Scoring**: Pesos ajustados según severidad real observada en incidentes

### Limitaciones Conocidas

- **Rate Limits**: Microsoft Graph API limita a 10 req/seg
- **Sherlock**: Algunos sitios bloquean scraping (resultados parciales)
- **Hawk**: Requiere Exchange Online Management instalado
- **Sparrow**: Necesita Azure AD Premium P2 para risk events

---

## 📚 Referencias

- [Microsoft Graph API - Sign-in Logs](https://learn.microsoft.com/graph/api/signin-list)
- [Azure AD Identity Protection](https://learn.microsoft.com/azure/active-directory/identity-protection/)
- [Sparrow Documentation](https://github.com/cisagov/Sparrow)
- [Hawk Documentation](https://github.com/T0pCyber/hawk)
- [Sherlock Project](https://github.com/sherlock-project/sherlock)

---

**Última Actualización**: 2024-12-05  
**Versión**: 1.0.0  
**Autor**: MCP Kali Forensics Team
