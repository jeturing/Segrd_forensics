# 🎯 Análisis Unificado de Cuentas - Quick Start

## ¿Qué hace?

Analiza cuentas de usuario combinando **TODAS** las herramientas forenses disponibles para generar un **Risk Score unificado (0-100)** con timeline y recomendaciones.

### Herramientas Integradas:
- ☁️ **M365 Graph API**: Sign-ins de riesgo, eventos de Identity Protection, MFA
- 🦅 **Sparrow 365**: Indicadores de compromiso en Azure AD
- 📧 **Hawk M365**: Reglas maliciosas, delegaciones, OAuth apps
- 🔍 **Sherlock**: Perfiles en redes sociales (OSINT)

---

## 🚀 Uso desde Dashboard

1. Abre el dashboard: http://localhost:9000
2. Selecciona un caso en el dropdown
3. Click en **"Ejecutar Investigación Completa"**
4. ✅ Activa **"Análisis Unificado de Cuentas"**
5. Ingresa emails: `usuario1@empresa.com, usuario2@empresa.com`
6. ✅ (Opcional) Marca **"Incluir búsqueda OSINT"**
7. Click **"Ejecutar Investigación"**
8. Espera ~40-48 minutos (según opciones)
9. Ve el reporte en **tab "Análisis de Cuentas"**

---

## 📊 Ejemplo de Resultado

```
┌─────────────────────────────────────────────────────┐
│ 👤 admin@empresa.com              Risk Score: 85/100│
│ Análisis: 2024-12-05 15:30             CRITICAL RISK│
├─────────────────────────────────────────────────────┤
│ 📊 Métricas                                         │
│   Risky Sign-ins: 3    Reglas Maliciosas: 2        │
│   OAuth Apps: 5        Perfiles OSINT: 8           │
│                                                      │
│ 📅 Timeline (últimos eventos)                       │
│   • 2024-12-05 14:20 - Sign-in desde IP sospechosa │
│   • 2024-12-05 12:45 - Regla de reenvío creada     │
│   • 2024-12-04 18:30 - Consentimiento OAuth         │
│                                                      │
│ 💡 Recomendaciones                                   │
│   🔴 CRITICAL: Deshabilitar cuenta inmediatamente   │
│   🟠 HIGH: Revocar consentimientos OAuth            │
│   🟡 MEDIUM: Habilitar MFA                          │
└─────────────────────────────────────────────────────┘
```

---

## 🔥 Uso desde API (avanzado)

### Analizar una cuenta

```bash
curl -X POST http://localhost:9000/forensics/accounts/analyze \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "user_email": "admin@empresa.com",
    "tenant_id": "3af2e132-c361-4467-9d8b-081f06630c12",
    "days_back": 90,
    "include_osint": true,
    "priority": "high"
  }'
```

**Response:**
```json
{
  "status": "queued",
  "message": "Análisis de cuenta iniciado para admin@empresa.com",
  "case_id": "ACC-20241205-153045",
  "estimated_duration_minutes": 48
}
```

### Analizar múltiples cuentas

```bash
curl -X POST http://localhost:9000/forensics/accounts/analyze-multiple \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "user_emails": [
      "user1@empresa.com",
      "user2@empresa.com",
      "user3@empresa.com"
    ],
    "tenant_id": "3af2e132-c361-4467-9d8b-081f06630c12",
    "days_back": 90,
    "include_osint": false
  }'
```

---

## 🧮 Risk Scoring

| Score | Nivel | Significado |
|-------|-------|-------------|
| **≥70** | 🔴 **Critical** | Compromiso probable, acción inmediata |
| **≥50** | 🟠 **High** | Actividad sospechosa significativa |
| **≥30** | 🟡 **Medium** | Anomalías detectadas, investigar |
| **<30** | 🟢 **Low** | Sin indicadores críticos |

### Cálculo de Puntos

- **Sign-ins de Riesgo**: hasta 30 pts (10 por sign-in)
- **Reglas Maliciosas**: hasta 25 pts (12 por regla)
- **OAuth Apps**: hasta 20 pts (5 por app)
- **OSINT High-Risk**: hasta 15 pts (7 por plataforma)
- **Eventos de Riesgo**: hasta 10 pts (5 por evento)

---

## ⏱️ Duración Estimada

| Opción | Tiempo |
|--------|--------|
| Sin OSINT | ~40 min |
| Con OSINT (Sherlock) | ~48 min |
| Múltiples (10 cuentas) | ~8 min por lote |

---

## 📝 Datos Generados

### Timeline
Eventos cronológicos de todas las fuentes:
- Sign-ins anómalos (ubicaciones, IPs, dispositivos)
- Cambios administrativos (privilegios, usuarios)
- Configuración de buzón (reglas, delegaciones, OAuth)
- Actividad OSINT (perfiles encontrados)

### Recomendaciones
Auto-generadas según hallazgos:
- **Critical**: Deshabilitar cuenta, revocar sesiones
- **High**: Habilitar MFA, auditar OAuth
- **Medium**: Monitoreo, verificar dispositivos

### Evidencias
Guardadas en:
```
~/forensics-evidence/{case_id}/
├── account_analysis_{email}.json
├── sparrow_results.csv
├── hawk_results/
└── sherlock_results/
```

---

## 🧪 Testing

```bash
cd /home/hack/mcp-kali-forensics
python3 scripts/test_account_analysis.py
```

Tests incluidos:
- ✅ Análisis de cuenta individual
- ✅ Análisis de múltiples cuentas  
- ✅ Cálculo de risk score

---

## 🔐 Credenciales Necesarias

### Azure AD
- Tenant ID configurado en M365
- Permisos Graph API:
  - `AuditLog.Read.All`
  - `IdentityRiskEvent.Read.All`
  - `User.Read.All`
  - `Directory.Read.All`

### Herramientas
- **Sparrow**: Credenciales Azure AD
- **Hawk**: Exchange Online Management
- **Sherlock**: No requiere (público)

---

## 📚 Documentación Completa

Ver: `/docs/ACCOUNT_ANALYSIS.md`

---

## ⚡ Casos de Uso

### 1. Investigación de Compromiso
Usuario reporta actividad sospechosa → Ejecuta análisis completo → Revisa risk score y timeline → Implementa recomendaciones

### 2. Auditoría de Seguridad
Necesitas evaluar seguridad de cuentas privilegiadas → Analiza múltiples admins → Identifica cuentas de alto riesgo → Prioriza remediación

### 3. Incident Response
Detectan malware en endpoint → Analiza cuenta del usuario → Verifica lateral movement (OAuth, delegaciones) → Contiene amenaza

### 4. OSINT Investigation
Sospechas de ingeniería social → Ejecuta con Sherlock → Encuentra perfiles en sitios de alto riesgo → Valida amenaza

---

## 🚨 Troubleshooting

### "Error: No case selected"
→ Selecciona un caso en el dropdown antes de abrir el modal

### "Error 500: Tool not found"
→ Verifica que Sparrow/Hawk/Sherlock estén instalados: `./scripts/check_tools.sh`

### "Timeout error"
→ Análisis puede demorar hasta 48 minutos. Revisa estado del caso en dashboard

### "Rate limit exceeded"
→ Microsoft Graph API limita 10 req/seg. Espera unos minutos y reintenta

---

**Creado**: 2024-12-05  
**Versión**: 1.0.0  
**Soporte**: MCP Kali Forensics Team
