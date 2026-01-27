# 🛡️ Security Checklist - Guía de Configuración

## Descripción

El **Security Checklist** es un formulario interactivo que permite a los clientes potenciales completar un cuestionario de ciberseguridad. El sistema automáticamente:

1. ✅ Valida las respuestas
2. 📊 Calcula una puntuación de riesgo (1-10)
3. 🎯 Recomienda un nivel de servicio (Esencial, Profesional, Misión Crítica)
4. 📧 Genera un reporte HTML y lo envía a `sales@jeturing.com`

## Acceso

- **URL pública:** `https://segrd.com/security-checklist`
- **Ruta local:** `/security-checklist`

## Características

### 1. Formulario Completo
El formulario contiene 9 secciones con 27 preguntas:
- 📋 Datos básicos (empresa, país, industria, empleados)
- 💻 Infraestructura tecnológica
- 🔐 Estado actual de seguridad
- ⚠️ Riesgos e incidentes
- 📋 Cumplimiento normativo
- 🔍 Monitoreo y respuesta
- 💾 Respaldos y continuidad
- ⚖️ Legal y forense
- 💬 Comentarios adicionales

### 2. Cálculo Automático de Riesgo
El sistema calcula un **Risk Score (1-10)** basado en:
- ✅ Factores de riesgo (incidentes previos, operación 24/7, criticidad del negocio)
- ✅ Factores mitigantes (monitoreo 24/7, logs centralizados, backups probados)

### 3. Recomendación de Nivel
Basado en el score de riesgo:
- **Esencial (1-3):** Pequeñas empresas sin presión regulatoria
- **Profesional (4-6):** Medianas empresas con requisitos de cumplimiento
- **Misión Crítica (7-10):** Empresas de alto riesgo, 24/7, o muy reguladas

### 4. Reporte HTML Detallado
El email que se envía a sales incluye:
- Información de la empresa
- Puntuación de riesgo
- Nivel recomendado
- Resumen de respuestas
- Badge visual de criticidad
- Tabla de infraestructura
- Tabla de estado de seguridad

## Configuración Requerida

### 1. Variables de Entorno (.env)

Configura SMTP para enviar emails. Copia y personaliza:

```bash
cp .env.smtp.example .env.smtp
# Edita .env.smtp con tus credenciales SMTP
```

**Ejemplo con Gmail:**
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu-email@gmail.com
SMTP_PASSWORD=tu-app-password
SMTP_FROM_EMAIL=noreply@jeturing.com
```

**Instrucciones Gmail:**
1. Habilita autenticación de dos factores
2. Genera una "Contraseña de aplicación" en https://myaccount.google.com/apppasswords
3. Copia esa contraseña (NO tu contraseña normal) en SMTP_PASSWORD

### 2. Endpoints

El backend expone dos endpoints:

#### POST /security-checklist/submit
Recibe el formulario completado y envía el email.

**Request body:**
```json
{
  "company_name": "Acme Corp",
  "country": "Colombia",
  "industry": "Financiero",
  "employees": "150",
  "computers": "120",
  "has_servers": "Sí, en la nube",
  "uses_m365": "Sí",
  "m365_users": "150",
  "has_vpn": "Sí",
  "has_security_officer": false,
  "security_only_it": true,
  "has_policies": true,
  "had_incidents": false,
  "operates_24_7": true,
  "attack_could_stop_business": true,
  "clients_demand_security": true,
  "has_cyber_insurance": false,
  "compliance_requirements": ["PCI", "ISO 27001"],
  "has_24_7_monitoring": false,
  "has_centralized_logs": false,
  "can_reconstruct_incident": true,
  "has_backups": true,
  "tested_backups": true,
  "recovery_time_target": "4 horas",
  "needs_digital_evidence": true,
  "concerned_internal_fraud": false,
  "comments": "Somos empresa financiera, muy regulada",
  "recommended_tier": "Misión Crítica",
  "risk_score": 8,
  "submitted_at": "2025-01-27T10:30:00Z"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Formulario enviado exitosamente",
  "recommended_tier": "Misión Crítica",
  "risk_score": 8
}
```

#### GET /security-checklist/status
Verifica si el servicio está operativo.

**Response:**
```json
{
  "status": "operational",
  "service": "Security Checklist",
  "email_configured": true,
  "timestamp": "2025-01-27T10:30:00Z"
}
```

## Flujo de Usuario

```
1. Usuario abre https://segrd.com/security-checklist
   ↓
2. Completa el formulario (recomendado: 5-10 minutos)
   ↓
3. Ve su puntuación y nivel recomendado en tiempo real
   ↓
4. Hace clic en "Enviar Formulario"
   ↓
5. Backend valida y envía email a sales@jeturing.com
   ↓
6. Usuario ve confirmación con su nivel recomendado
   ↓
7. Equipo de sales recibe reporte HTML detallado
   ↓
8. Sales contacta al cliente con propuesta personalizada
```

## Estructura de Archivos

```
segrd-forensics/
├── frontend-react/
│   └── src/
│       └── pages/
│           └── SecurityChecklistForm.jsx     # Componente del formulario
├── api/
│   ├── routes/
│   │   └── security_checklist.py             # Endpoint FastAPI
│   └── main.py                                # Router registrado aquí
├── .env.smtp.example                         # Variables SMTP de ejemplo
└── nginx/
    └── conf.d/
        └── ssl.conf                           # Proxy para /security-checklist
```

## Customización

### Cambiar email de destino

En `api/routes/security_checklist.py`, línea ~102:
```python
background_tasks.add_task(
    send_email,
    to_email="sales@jeturing.com",  # ← Cambiar aquí
    ...
)
```

### Modificar preguntas del formulario

1. Edita `frontend-react/src/pages/SecurityChecklistForm.jsx`
2. Añade/quita campos en:
   - Objeto `formData` (state inicial)
   - Función `handleInputChange`
   - Sección correspondiente del formulario
3. Si cambias la lógica de scoring, actualiza `calculateRiskScore()`

### Personalizar colores y diseño

El formulario usa Tailwind CSS. Cambia clases como:
- `bg-slate-800` → color de fondo
- `text-blue-600` → color de texto
- `border-slate-700` → bordes

## Testing

### Verificar que el endpoint está disponible
```bash
curl http://localhost:9000/security-checklist/status
```

### Probar envío de email (sin SMTP real)
Modifica temporalmente `security_checklist.py` para loguear el HTML:
```python
print(f"📧 Email que se enviaría:\n{html_report}")
```

### Validar desde el navegador
1. Abre `http://localhost:3000/security-checklist`
2. Abre DevTools (F12)
3. Completa el formulario
4. Busca POST `/api/security-checklist/submit` en la pestaña Network

## Solución de Problemas

### ❌ "Error al enviar formulario"
- Verifica que SMTP está configurado en `.env`
- Revisa logs: `docker logs mcp-forensics-api`
- Prueba SMTP: `python -m smtplib test`

### ❌ "Email configured: false"
- Las variables SMTP no están en `.env`
- Recarga el backend después de cambiar `.env`

### ❌ Formulario no aparece
- Verifica que `SecurityChecklistForm.jsx` está en `src/pages/`
- Verifica que la ruta se añadió en `App.jsx`
- Reconstruye el frontend: `npm run build`

## Despliegue

### Desarrollo (local)
```bash
# Terminal 1: Backend
cd /opt/segrd-forensics
./start.sh --bg

# Terminal 2: Frontend
cd frontend-react
npm run dev
```

### Producción (Docker)
```bash
cd /opt/segrd-forensics

# Asegúrate de que .env tiene SMTP configurado
cat .env | grep SMTP

# Reinicia los servicios
docker-compose restart mcp-forensics-api mcp-forensics-nginx

# Verifica
curl https://segrd.com/security-checklist
```

## Notas Importantes

- ✅ El formulario es **público** (no requiere login)
- ✅ Los datos se envían **inmediatamente** a sales@jeturing.com
- ✅ Se genera un **reporte HTML profesional** con colores y tablas
- ✅ El cálculo de riesgo es **automático** sin intervención
- ⚠️ Asegúrate de que SMTP esté configurado ANTES de publicar
- ⚠️ El email es el único registro del formulario (considera guardar en BD si necesitas historial)

## Próximas Mejoras

- [ ] Guardar respuestas en base de datos para historial
- [ ] Enviar confirmación al cliente con su propuesta recomendada
- [ ] Integración con Salesforce CRM
- [ ] Webhooks para alertas en Slack
- [ ] Análisis de tendencias de respuestas
- [ ] A/B testing de preguntas

---

**Soporte:** contacta a tech@jeturing.com
