# MCP Kali Forensics - Guía de Uso

## 🚀 Instalación Rápida

### Opción 1: Instalación Automática (Recomendada)

```bash
cd /home/hack/mcp-kali-forensics
sudo ./scripts/quick_install.sh
```

Este script instala:
- ✅ Dependencias del sistema (Python, YARA, PowerShell, OSQuery)
- ✅ Herramientas forenses (Sparrow, Hawk, Loki, O365 Extractor)
- ✅ Reglas YARA para detección de malware
- ✅ Dependencias Python en virtualenv
- ✅ Genera API key automáticamente

### Opción 2: Instalación Manual

```bash
# 1. Instalar dependencias del sistema
sudo apt update
sudo apt install python3 python3-pip python3-venv git curl wget yara powershell

# 2. Crear directorios
sudo mkdir -p /opt/forensics-tools /var/evidence
sudo chown $USER:$USER /opt/forensics-tools /var/evidence

# 3. Instalar herramientas
cd /opt/forensics-tools
git clone https://github.com/cisagov/Sparrow.git
git clone https://github.com/T0pCyber/hawk.git
git clone https://github.com/Neo23x0/Loki.git

# 4. Configurar proyecto
cd /home/hack/mcp-kali-forensics
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 5. Configurar .env
cp .env.example .env
nano .env  # Editar credenciales
```

## 🔧 Configuración

### 1. Editar `.env`

```bash
nano .env
```

**Configuración mínima requerida:**

```env
# API del MCP
API_KEY=tu-clave-segura-aqui  # ¡CAMBIAR!

# Jeturing CORE (opcional)
JETURING_CORE_ENABLED=false  # Cambiar a true si usas Jeturing CORE
JETURING_CORE_URL=https://core.jeturing.local
JETURING_CORE_API_KEY=tu-api-key-jeturing

# Microsoft 365 (para Sparrow/Hawk)
M365_TENANT_ID=tu-tenant-id
M365_CLIENT_ID=tu-app-id
M365_CLIENT_SECRET=tu-secret

# Have I Been Pwned (opcional)
HIBP_ENABLED=true
HIBP_API_KEY=tu-hibp-key  # Obtener en https://haveibeenpwned.com/API/Key

# Tailscale (opcional, para endpoints remotos)
TAILSCALE_ENABLED=false
TAILSCALE_AUTH_KEY=tskey-auth-xxx
```

### 2. Permisos Microsoft 365

Para usar Sparrow y Hawk, necesitas una App Registration en Azure AD con estos permisos:

**API Permissions requeridos:**
- `AuditLog.Read.All` (Application)
- `Directory.Read.All` (Application)
- `User.Read.All` (Application)
- `Mail.Read` (Application - para Hawk)

**Crear App Registration:**
```bash
# 1. Azure Portal → App registrations → New registration
# 2. Name: MCP-Kali-Forensics
# 3. Supported account types: Single tenant
# 4. Redirect URI: (dejar vacío)
# 5. API permissions → Add permissions → Microsoft Graph
# 6. Certificates & secrets → New client secret
# 7. Copiar: Application (client) ID, Tenant ID, Secret Value
```

## 🎯 Uso Básico

### Iniciar el Servicio

```bash
cd /home/hack/mcp-kali-forensics
source venv/bin/activate
uvicorn api.main:app --host 0.0.0.0 --port 8080 --reload
```

El servicio estará disponible en: `http://localhost:8080`

### Verificar Estado

```bash
# Health check
curl http://localhost:8080/health

# Documentación interactiva
open http://localhost:8080/docs
```

## 📡 Ejemplos de Uso

### 1. Análisis de Microsoft 365

Investiga un tenant M365 completo con Sparrow y Hawk:

```bash
curl -X POST http://localhost:8080/forensics/m365/analyze \
  -H "X-API-Key: tu-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "case_id": "IR-2024-001",
    "scope": ["sparrow", "hawk"],
    "target_users": ["fbdal@empresa.com"],
    "days_back": 90,
    "priority": "high"
  }'
```

**Respuesta:**
```json
{
  "case_id": "IR-2024-001",
  "status": "queued",
  "task_id": "abc-123-def",
  "message": "Análisis iniciado con 2 herramienta(s)",
  "estimated_duration_minutes": 25
}
```

### 2. Verificar Credenciales Filtradas

Busca emails en HIBP y dumps locales:

```bash
curl -X POST http://localhost:8080/forensics/credentials/check \
  -H "X-API-Key: tu-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "case_id": "IR-2024-002",
    "emails": [
      "usuario@empresa.com",
      "admin@empresa.com"
    ],
    "check_hibp": true,
    "check_local_dumps": true,
    "analyze_stealers": true
  }'
```

### 3. Escanear Endpoint con YARA y Loki

Analiza un endpoint local o remoto:

```bash
curl -X POST http://localhost:8080/forensics/endpoint/scan \
  -H "X-API-Key: tu-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "case_id": "IR-2024-003",
    "hostname": "PC-JUAN",
    "tailscale_ip": "100.64.0.5",
    "actions": ["yara", "loki", "osquery"],
    "target_paths": ["/tmp", "/home"]
  }'
```

### 4. Analizar Dump de Memoria

Sube y analiza un dump con Volatility 3:

```bash
curl -X POST http://localhost:8080/forensics/endpoint/memory/analyze \
  -H "X-API-Key: tu-api-key" \
  -F "memory_dump=@/path/to/memory.dmp" \
  -F "case_id=IR-2024-004" \
  -F "hostname=SERVER-01"
```

### 5. Consultar Estado de Caso

```bash
# Ver estado actual
curl http://localhost:8080/forensics/case/IR-2024-001/status \
  -H "X-API-Key: tu-api-key"

# Descargar reporte completo
curl http://localhost:8080/forensics/case/IR-2024-001/report \
  -H "X-API-Key: tu-api-key" > reporte.json
```

## 🔍 Casos de Uso Reales

### Caso 1: Compromiso de Cuenta M365

**Escenario:** Usuario FBDAL reporta actividad sospechosa en su cuenta.

```bash
# Paso 1: Verificar credenciales filtradas
curl -X POST http://localhost:8080/forensics/credentials/check \
  -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d '{"case_id":"FBDAL-001","emails":["fbdal@empresa.com"]}'

# Paso 2: Analizar actividad en M365
curl -X POST http://localhost:8080/forensics/m365/analyze \
  -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d '{"case_id":"FBDAL-001","tenant_id":"xxx","target_users":["fbdal@empresa.com"],"scope":["hawk"]}'

# Paso 3: Ver resultados
curl http://localhost:8080/forensics/case/FBDAL-001/report \
  -H "X-API-Key: $API_KEY" | jq .
```

**Qué buscar en el reporte:**
- ✅ Inicios de sesión desde IPs desconocidas
- ✅ Reglas de reenvío de correo sospechosas
- ✅ Aplicaciones OAuth con permisos peligrosos
- ✅ Cambios en configuración de buzón
- ✅ Credenciales en brechas públicas

### Caso 2: Endpoint Infectado

**Escenario:** Equipo "PC-JUAN" muestra comportamiento anómalo.

```bash
# Paso 1: Escaneo rápido con YARA/Loki
curl -X POST http://localhost:8080/forensics/endpoint/scan \
  -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d '{"case_id":"PC-JUAN-001","hostname":"PC-JUAN","actions":["yara","loki"]}'

# Paso 2: Recolectar artefactos con OSQuery
curl -X POST http://localhost:8080/forensics/endpoint/scan \
  -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" \
  -d '{"case_id":"PC-JUAN-002","hostname":"PC-JUAN","actions":["osquery"]}'

# Paso 3: Revisar hallazgos
curl http://localhost:8080/forensics/case/PC-JUAN-001/report \
  -H "X-API-Key: $API_KEY" | jq '.summary'
```

**Indicadores de compromiso:**
- 🚨 Matches de YARA en infostealers
- 🚨 Procesos sospechosos (nc, powershell, etc.)
- 🚨 Conexiones a IPs maliciosas
- 🚨 Archivos en /tmp con nombres aleatorios

### Caso 3: Análisis Post-Mortem

**Escenario:** Dump de memoria de servidor comprometido.

```bash
# Analizar dump
curl -X POST http://localhost:8080/forensics/endpoint/memory/analyze \
  -H "X-API-Key: $API_KEY" \
  -F "memory_dump=@server-crash.dmp" \
  -F "case_id=SERVER-POSTMORTEM" \
  -F "hostname=WEB-SERVER-01"

# Esperar resultados (puede tomar 10-20 minutos)
watch -n 10 "curl -s http://localhost:8080/forensics/case/SERVER-POSTMORTEM/status -H 'X-API-Key: $API_KEY' | jq .progress_percentage"

# Descargar reporte
curl http://localhost:8080/forensics/case/SERVER-POSTMORTEM/report \
  -H "X-API-Key: $API_KEY" -o postmortem.json
```

## 🐛 Troubleshooting

### Error: "PowerShell no está instalado"

```bash
# Instalar PowerShell en Kali
sudo apt install powershell
pwsh --version
```

### Error: "HIBP rate limit exceeded"

El MCP implementa rate limiting automático (1.5s entre requests), pero si ves este error:

```bash
# Reducir cantidad de emails simultáneos
# En lugar de 100 emails de una vez, dividir en grupos de 10
```

### Error: "Sparrow/Hawk no puede autenticar"

Verifica credenciales M365:

```bash
# Probar autenticación manualmente
pwsh -Command "Connect-AzureAD -TenantId 'xxx' -ApplicationId 'yyy' -CertificateThumbprint 'zzz'"
```

### Ver Logs Detallados

```bash
# Logs del servicio
tail -f logs/mcp-forensics.log

# Habilitar modo debug
# En .env: DEBUG=true
```

## 📊 Monitoreo

### Prometheus Metrics (futuro)

```bash
curl http://localhost:8080/metrics
```

### Status Dashboard

Accede a `http://localhost:8080/docs` para:
- Ver casos activos
- Monitorear progreso
- Descargar reportes
- Probar endpoints

## 🔒 Seguridad

### Rotación de API Keys

```bash
# Generar nueva key
openssl rand -hex 32

# Actualizar en .env
nano .env  # Cambiar API_KEY
```

### Cifrado de Evidencia

```bash
# Cifrar directorio de evidencia
sudo apt install ecryptfs-utils
sudo mount -t ecryptfs /var/evidence /var/evidence
```

### Firewall

```bash
# Permitir solo localhost (más seguro)
sudo ufw allow from 127.0.0.1 to any port 8080

# O permitir desde red local
sudo ufw allow from 192.168.1.0/24 to any port 8080
```

## 📚 Recursos Adicionales

- **Sparrow Docs**: https://github.com/cisagov/Sparrow
- **Hawk Docs**: https://github.com/T0pCyber/hawk
- **HIBP API**: https://haveibeenpwned.com/API/v3
- **Volatility 3**: https://github.com/volatilityfoundation/volatility3
- **YARA Rules**: https://github.com/Yara-Rules/rules

## 🆘 Soporte

Para reportar issues o contribuir:
- **Email**: security@jeturing.local
- **Issues**: GitHub Issues (si aplica)
- **Docs**: Ver `/docs/` en el proyecto
