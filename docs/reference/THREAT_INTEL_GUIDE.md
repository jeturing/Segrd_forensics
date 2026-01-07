# 🔍 Threat Intelligence & SOAR Platform

Plataforma completa de inteligencia de amenazas con integración de 9 APIs externas, playbooks SOAR automatizados, cache Redis y webhooks en tiempo real.

## 📋 Tabla de Contenidos

- [Características](#-características)
- [APIs Integradas](#-apis-integradas)
- [Playbooks SOAR](#-playbooks-soar)
- [Cache Redis](#-cache-redis)
- [Webhooks](#-webhooks)
- [Instalación](#-instalación)
- [Configuración](#-configuración)
- [Uso](#-uso)
- [API Reference](#-api-reference)

---

## 🚀 Características

### ✅ Completo
- **9 APIs de Threat Intelligence** configuradas y operacionales (100%)
- **3 Playbooks SOAR** automatizados para investigación
- **Cache Redis** para evitar rate limits
- **Webhooks** para alertas en tiempo real (Slack, Discord, Custom)
- **Frontend React** con 6 tabs funcionales
- **Dashboard Widget** con quick scan
- **Swagger UI** auto-generado

### 🎯 Casos de Uso
- Análisis de reputación de IPs
- Investigación de credenciales comprometidas
- Detección de URLs de phishing
- Búsquedas en dark web
- Escaneo de malware
- Descubrimiento de emails en dominios

---

## 🔌 APIs Integradas

### 1. **Shodan** - Network Intelligence
```bash
Endpoint: /api/threat-intel/ip/lookup
Función: Puertos abiertos, servicios, vulnerabilidades, geolocalización
Rate Limit: 1 req/second (cacheado 1 hora)
```

### 2. **Censys** - Internet Scanning
```bash
Endpoint: /api/threat-intel/ip/lookup
Función: Datos de escaneo internet-wide, certificados SSL
Rate Limit: 250 req/day (cacheado 1 hora)
```

### 3. **VirusTotal** - Malware Analysis
```bash
Endpoints: 
  - /api/threat-intel/ip/lookup (IP reputation)
  - /api/threat-intel/url/scan (URL scanning)
  - /api/threat-intel/file/scan (File analysis)
Función: Detecciones de malware con 70+ motores
Rate Limit: 4 req/minute (cacheado 1 hora)
```

### 4. **HaveIBeenPwned (HIBP)** - Breach Detection
```bash
Endpoints:
  - /api/threat-intel/email/check (Email breaches)
  - /api/threat-intel/password/check (Password compromises)
Función: Base de datos de brechas de seguridad
Rate Limit: 1 req/1.5s (cacheado 24 horas)
```

### 5. **IBM X-Force** - Threat Intelligence
```bash
Endpoint: /api/threat-intel/ip/lookup
Función: Threat score, categorización de IPs
Rate Limit: 5000 req/month (cacheado 1 hora)
```

### 6. **SecurityTrails** - DNS Intelligence
```bash
Endpoint: /api/threat-intel/domain/lookup
Función: Historial DNS, registros de dominio
Rate Limit: 50 req/month (cacheado 2 horas)
```

### 7. **Hunter.io** - Email Discovery
```bash
Endpoint: /api/threat-intel/domain/lookup
Función: Descubrimiento de emails en dominios
Rate Limit: 50 searches/month (cacheado 2 horas)
```

### 8. **Intelligence X** - Dark Web Search
```bash
Endpoint: /api/threat-intel/intelx/search
Función: Búsqueda en dark web, paste sites, data leaks
Rate Limit: 100 req/day (cacheado 1 hora)
```

### 9. **Hybrid Analysis** - Malware Sandbox
```bash
Endpoint: /api/threat-intel/file/scan
Función: Análisis de malware en sandbox
Rate Limit: 200 submissions/month (cacheado 30 minutos)
```

---

## 🤖 Playbooks SOAR

Los playbooks se ejecutan automáticamente y envían alertas webhook cuando detectan amenazas críticas.

### 1. IP Reputation Analysis
**Endpoint:** `POST /api/threat-intel/playbooks/execute`

**Payload:**
```json
{
  "playbook_name": "ip_reputation_analysis",
  "target": "8.8.8.8",
  "investigation_id": "IR-2024-001"
}
```

**Flujo:**
1. ✅ Shodan lookup (puertos, servicios, vulns)
2. ✅ VirusTotal IP report (detecciones)
3. ✅ X-Force threat score
4. ✅ Censys SSL certificates
5. 📊 **Genera risk score (0-100)**
6. 💡 **Recomendaciones automáticas**
7. 🔔 **Webhook alert si risk >= 60**

**Output:**
```json
{
  "risk_score": 85,
  "action": "block",
  "indicators": [
    "Open suspicious ports: 22, 445, 3389",
    "8 malicious detections in VirusTotal",
    "Known botnet IP"
  ],
  "recommendations": [
    "🚨 BLOCK immediately in firewall",
    "🔍 Review all connections from this IP"
  ]
}
```

---

### 2. Email Compromise Investigation
**Endpoint:** `POST /api/threat-intel/playbooks/execute`

**Payload:**
```json
{
  "playbook_name": "email_compromise_investigation",
  "target": "john@company.com",
  "investigation_id": "IR-2024-002",
  "parameters": {
    "check_domain": true
  }
}
```

**Flujo:**
1. ✅ HaveIBeenPwned check (brechas)
2. ✅ Intelligence X dark web search
3. ✅ Hunter.io domain email discovery
4. 📊 **Determina exposure level**
5. 💡 **Lista brechas y datos expuestos**
6. 🔔 **Webhook alert si exposure = critical/high**

**Output:**
```json
{
  "exposure_level": "critical",
  "breaches_found": 7,
  "breaches": [
    {
      "name": "LinkedIn",
      "date": "2021-04-08",
      "data_classes": ["Email addresses", "Passwords"]
    }
  ],
  "exposed_data": ["email", "passwords", "names"],
  "domain_emails": 25,
  "recommendations": [
    "🚨 IMMEDIATE PASSWORD RESET required",
    "🔐 Enable MFA on all accounts"
  ]
}
```

---

### 3. Phishing URL Analysis
**Endpoint:** `POST /api/threat-intel/playbooks/execute`

**Payload:**
```json
{
  "playbook_name": "phishing_url_analysis",
  "target": "https://suspicious-site.com/login",
  "investigation_id": "IR-2024-003"
}
```

**Flujo:**
1. ✅ VirusTotal URL scan (70+ engines)
2. ✅ SecurityTrails domain analysis
3. 📊 **Calcula threat level**
4. 💡 **Identifica indicadores de phishing**
5. 🔔 **Webhook alert si threat = critical/high**

**Output:**
```json
{
  "threat_level": "critical",
  "malicious_detections": 45,
  "phishing_indicators": [
    "Domain registered 2 days ago",
    "Typosquatting detected",
    "Suspicious SSL certificate"
  ],
  "recommendations": [
    "🚨 BLOCK URL immediately in web gateway",
    "📧 Alert users who may have clicked"
  ]
}
```

---

## 💾 Cache Redis

### Propósito
- **Evitar rate limits** de APIs externas
- **Mejorar rendimiento** (resultados instantáneos)
- **Reducir costos** de APIs de pago

### TTL (Time To Live) por Tipo
```python
ip_lookup:      3600s (1 hora)
email_check:   86400s (24 horas)
domain_info:    7200s (2 horas)
url_scan:       1800s (30 minutos)
shodan_search:  3600s (1 hora)
virustotal:     3600s (1 hora)
hibp:          86400s (24 horas)
xforce:         3600s (1 hora)
```

### Instalación
```bash
# Instalar Redis automáticamente
cd /home/hack/mcp-kali-forensics
./scripts/setup_redis.sh

# O manualmente
sudo apt-get install redis-server
pip install redis[hiredis]

# Verificar
systemctl status redis-server
redis-cli ping  # Debe responder "PONG"
```

### Configuración (.env)
```bash
REDIS_ENABLED=true
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
```

### Endpoints de Gestión

#### Ver Estadísticas
```bash
GET /api/threat-intel/cache/stats

Response:
{
  "enabled": true,
  "total_keys": 156,
  "threat_intel_keys": 142,
  "hits": 3452,
  "misses": 789,
  "hit_rate": 81.39,
  "used_memory_human": "45.2M",
  "connected_clients": 3
}
```

#### Limpiar Cache
```bash
POST /api/threat-intel/cache/clear?pattern=threat_intel:*

# Limpiar solo IPs
POST /api/threat-intel/cache/clear?pattern=threat_intel:ip:*

# Limpiar solo emails
POST /api/threat-intel/cache/clear?pattern=threat_intel:email:*
```

### Monitoreo
```bash
# Ver logs de Redis
tail -f /var/log/redis/redis-server.log

# Monitorear comandos en tiempo real
redis-cli monitor

# Ver keys almacenadas
redis-cli KEYS "threat_intel:*"

# Información de memoria
redis-cli INFO memory
```

---

## 📡 Webhooks

### Plataformas Soportadas
- **Slack** - Rich message blocks con color coding
- **Discord** - Embeds con fields estructurados
- **Custom** - JSON genérico para cualquier webhook

### Niveles de Amenaza
```python
critical  🔴  # Acción inmediata requerida
high      🟠  # Alta prioridad
medium    🟡  # Monitoreo necesario
low       🟢  # Informativo
info      ℹ️   # General
```

### Configuración (.env)

#### Slack
```bash
WEBHOOK_ENABLED=true
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
SLACK_CHANNEL=#security-alerts
SLACK_USERNAME=Forensics Bot
SLACK_ICON=:shield:
```

Para obtener Slack webhook:
1. Ir a https://api.slack.com/apps
2. Crear nueva app → "Incoming Webhooks"
3. Activar y añadir a workspace
4. Copiar Webhook URL

#### Discord
```bash
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR/WEBHOOK/URL
DISCORD_USERNAME=Forensics Bot
```

Para obtener Discord webhook:
1. Ir a Server Settings → Integrations → Webhooks
2. New Webhook
3. Copiar Webhook URL

#### Custom Webhooks
```bash
CUSTOM_WEBHOOK_URLS=https://api1.com/alerts,https://api2.com/notifications
```

### Endpoints de Gestión

#### Ver Estado
```bash
GET /api/threat-intel/webhooks/status

Response:
{
  "enabled": true,
  "webhooks": {
    "slack": {
      "configured": true,
      "channel": "#security-alerts"
    },
    "discord": {
      "configured": true
    },
    "custom": {
      "configured": true,
      "count": 2
    }
  }
}
```

#### Probar Webhooks
```bash
POST /api/threat-intel/webhooks/test

Response:
{
  "test_sent": true,
  "timestamp": "2024-12-06T02:30:45",
  "results": {
    "slack": true,
    "discord": true,
    "custom_0": true
  }
}
```

#### Enviar Alerta Manual
```bash
POST /api/threat-intel/webhooks/alert

Payload:
{
  "title": "Suspicious Activity Detected",
  "message": "Multiple failed login attempts from IP 10.0.0.1",
  "threat_level": "high",
  "target": "10.0.0.1",
  "investigation_id": "IR-2024-004",
  "metadata": {
    "failed_attempts": 50,
    "time_window": "5 minutes"
  },
  "recommendations": [
    "Block IP immediately",
    "Review authentication logs"
  ]
}
```

### Alertas Automáticas

Los playbooks SOAR envían alertas automáticamente cuando detectan:

| Playbook | Condición de Alerta | Función |
|----------|---------------------|---------|
| IP Reputation | risk_score >= 60 | `alert_malicious_ip()` |
| Email Compromise | exposure_level = critical/high | `alert_email_breach()` |
| Phishing URL | threat_level = critical/high | `alert_phishing_url()` |

---

## 🔧 Instalación

### 1. Clonar Repositorio
```bash
git clone https://github.com/your-org/mcp-kali-forensics.git
cd mcp-kali-forensics
```

### 2. Instalar Backend
```bash
# Crear virtual environment
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Instalar Redis
./scripts/setup_redis.sh
```

### 3. Configurar .env
```bash
cp .env.example .env
nano .env

# Configurar APIs obligatorias
SHODAN_API_KEY=tu-api-key
VT_API_KEY=tu-api-key
HIBP_API_KEY=tu-api-key

# Habilitar Redis
REDIS_ENABLED=true

# Configurar webhooks (opcional)
WEBHOOK_ENABLED=true
SLACK_WEBHOOK_URL=https://...
```

### 4. Iniciar Backend
```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8888
```

### 5. Instalar Frontend (opcional)
```bash
cd frontend-react
npm install
npm run dev
```

---

## ⚙️ Configuración

### Variables de Entorno Críticas

#### Threat Intelligence APIs
```bash
# Obligatorias (sin estas el sistema funciona parcialmente)
SHODAN_API_KEY=
VT_API_KEY=
HIBP_API_KEY=

# Recomendadas
XFORCE_API_KEY=
XFORCE_API_SECRET=
CENSYS_API_ID=
CENSYS_API_SECRET=

# Opcionales
SECURITYTRAILS_API_KEY=
HUNTER_API_KEY=
INTELX_API_KEY=
HYBRID_ANALYSIS_KEY=
```

#### Redis Cache
```bash
REDIS_ENABLED=true  # IMPORTANTE: Activar para producción
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=  # Dejar vacío si no hay auth
```

#### Webhooks
```bash
WEBHOOK_ENABLED=false  # Activar cuando configures webhooks
SLACK_WEBHOOK_URL=
DISCORD_WEBHOOK_URL=
CUSTOM_WEBHOOK_URLS=
```

---

## 📖 Uso

### 1. Verificar Estado
```bash
# Health check
curl http://localhost:8888/health

# API status (muestra 9/9 APIs configuradas)
curl http://localhost:8888/api/threat-intel/status

# Cache stats
curl http://localhost:8888/api/threat-intel/cache/stats

# Webhook status
curl http://localhost:8888/api/threat-intel/webhooks/status
```

### 2. Análisis de IP
```bash
curl -X POST http://localhost:8888/api/threat-intel/ip/lookup \
  -H "Content-Type: application/json" \
  -d '{
    "ip": "8.8.8.8",
    "sources": ["shodan", "virustotal", "xforce", "censys"]
  }'
```

### 3. Verificar Email
```bash
curl -X POST http://localhost:8888/api/threat-intel/email/check \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "check_domain": true
  }'
```

### 4. Ejecutar Playbook SOAR
```bash
curl -X POST http://localhost:8888/api/threat-intel/playbooks/execute \
  -H "Content-Type: application/json" \
  -d '{
    "playbook_name": "ip_reputation_analysis",
    "target": "1.2.3.4",
    "investigation_id": "IR-2024-001"
  }'
```

### 5. Frontend
```bash
# Abrir en navegador
http://localhost:3000/threat-intel

# Dashboard widget
http://localhost:3000/
```

---

## 📚 API Reference

### Swagger UI
```
http://localhost:8888/docs
```

Todos los endpoints están documentados con:
- Descripción detallada
- Modelos de request/response
- Ejemplos de uso
- Códigos de error

### Endpoints Principales

#### IP Lookup
```
POST /api/threat-intel/ip/lookup
```

#### Email Check
```
POST /api/threat-intel/email/check
```

#### Domain Lookup
```
POST /api/threat-intel/domain/lookup
```

#### URL Scan
```
POST /api/threat-intel/url/scan
```

#### Shodan Search
```
POST /api/threat-intel/shodan/search
```

#### Dark Web Search
```
POST /api/threat-intel/intelx/search
```

#### Playbooks
```
POST /api/threat-intel/playbooks/execute
GET  /api/threat-intel/playbooks/available
```

#### Cache Management
```
GET  /api/threat-intel/cache/stats
POST /api/threat-intel/cache/clear
```

#### Webhooks
```
GET  /api/threat-intel/webhooks/status
POST /api/threat-intel/webhooks/test
POST /api/threat-intel/webhooks/alert
```

---

## 🔐 Seguridad

### Rate Limiting
- Implementado cache Redis para evitar exceder límites de APIs
- Rate limit checker incluido en `redis_cache.py`
- TTLs optimizados por tipo de consulta

### API Keys
- Almacenadas en `.env` (nunca commitear)
- Validación en cada request
- Logging sin exponer credenciales

### Webhooks
- Timeouts de 10 segundos
- Retry logic incluido
- Logs detallados de envíos

---

## 🐛 Troubleshooting

### Backend no inicia
```bash
# Verificar puerto
lsof -i :8888

# Ver logs
tail -f /tmp/backend.log

# Verificar dependencias
pip list | grep aiohttp
```

### Redis no funciona
```bash
# Verificar servicio
systemctl status redis-server

# Test conexión
redis-cli ping

# Ver logs
tail -f /var/log/redis/redis-server.log

# Reinstalar
./scripts/setup_redis.sh
```

### Webhooks fallan
```bash
# Test manual
curl -X POST http://localhost:8888/api/threat-intel/webhooks/test

# Verificar URLs en .env
echo $SLACK_WEBHOOK_URL
echo $DISCORD_WEBHOOK_URL

# Ver logs de envío
grep "webhook" /tmp/backend.log
```

### APIs no responden
```bash
# Verificar configuración
curl http://localhost:8888/api/threat-intel/status

# Test individual
curl "https://api.shodan.io/shodan/host/8.8.8.8?key=YOUR_KEY"

# Verificar rate limits
redis-cli GET "threat_intel:ip:*"
```

---

## 📞 Soporte

- **Documentación:** http://localhost:8888/docs
- **Logs:** `/tmp/backend.log`, `/var/log/redis/redis-server.log`
- **Issues:** GitHub Issues

---

## 📜 Licencia

MIT License - Ver LICENSE file

---

**Desarrollado con ❤️ para MCP Kali Forensics v4.1**
