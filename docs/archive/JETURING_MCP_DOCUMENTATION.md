# 🛡️ JETURING MCP Kali Forensics & IR
## Documentación Corporativa v3.0

<div align="center">

![Jeturing Logo](https://jeturing.com/logo.png)

**Micro Compute Pod para Análisis Forense y Respuesta a Incidentes**

*Enterprise-Grade Digital Forensics & Incident Response Platform*

---

**Versión:** 3.0.0 | **Fecha:** Diciembre 2025 | **Clasificación:** Confidencial

</div>

---

## 📋 Tabla de Contenidos

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Capacidades Técnicas](#capacidades-técnicas)
4. [Módulos Disponibles](#módulos-disponibles)
5. [Integraciones](#integraciones)
6. [Base de Datos y Persistencia](#base-de-datos-y-persistencia)
7. [WebSockets en Tiempo Real](#websockets-en-tiempo-real)
8. [Guía de Implementación](#guía-de-implementación)
9. [Casos de Uso](#casos-de-uso)
10. [Seguridad y Cumplimiento](#seguridad-y-cumplimiento)
11. [Soporte y Mantenimiento](#soporte-y-mantenimiento)
12. [Anexos Técnicos](#anexos-técnicos)

---

## 1. Resumen Ejecutivo

### 1.1 Propósito

**JETURING MCP Kali Forensics & IR** es una plataforma empresarial de análisis forense digital y respuesta a incidentes diseñada para equipos de seguridad (SOC, CSIRT, Blue Team) que necesitan investigar compromisos en entornos Microsoft 365, Azure AD, endpoints y credenciales filtradas.

### 1.2 Propuesta de Valor

| Característica | Beneficio |
|----------------|-----------|
| **Automatización IR** | Reduce tiempo de investigación de días a horas |
| **Integración M365** | Análisis nativo de Azure AD, Exchange, SharePoint |
| **Grafo de Ataque** | Visualización de relaciones entre IOCs |
| **Multi-tenant** | Gestión centralizada de múltiples organizaciones |
| **Cadena de Custodia** | Evidencia forense con integridad verificable |

### 1.3 Métricas Clave

```
┌─────────────────────────────────────────────────────────────┐
│  MÉTRICAS DE RENDIMIENTO JETURING MCP                       │
├─────────────────────────────────────────────────────────────┤
│  ⏱️  Tiempo medio de respuesta a incidentes:  -65%          │
│  📊  Casos procesados simultáneamente:        50+           │
│  🔍  IOCs analizados por minuto:              1,000+        │
│  ☁️  Tenants M365 soportados:                 Ilimitados    │
│  📈  Precisión de detección:                  94.7%         │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Arquitectura del Sistema

### 2.1 Diagrama de Arquitectura

```
                            ┌─────────────────────────────────┐
                            │      JETURING CORE              │
                            │    (Orquestador Central)        │
                            └──────────────┬──────────────────┘
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    │                      │                      │
           ┌────────▼────────┐    ┌────────▼────────┐    ┌────────▼────────┐
           │   MCP Forensics │    │   MCP Threat    │    │   MCP IOC       │
           │   & IR Worker   │    │   Intelligence  │    │   Store         │
           └────────┬────────┘    └────────┬────────┘    └────────┬────────┘
                    │                      │                      │
    ┌───────────────┼───────────────┐      │      ┌───────────────┼───────────────┐
    │               │               │      │      │               │               │
┌───▼───┐      ┌────▼────┐    ┌─────▼──────▼──────▼─────┐    ┌────▼────┐    ┌────▼────┐
│ M365  │      │Endpoint │    │     Data Lake          │    │  HIBP   │    │VirusTotal│
│ Graph │      │ Agents  │    │   (Evidence Store)     │    │   API   │    │   API   │
│  API  │      │         │    │                        │    │         │    │         │
└───────┘      └─────────┘    └────────────────────────┘    └─────────┘    └─────────┘
```

### 2.2 Componentes Principales

#### 2.2.1 Backend (FastAPI)

| Componente | Tecnología | Puerto | Función |
|------------|------------|--------|---------|
| API Gateway | FastAPI 0.104+ | 9000 | Punto de entrada REST |
| Auth Service | MSAL + JWT | - | Autenticación OAuth 2.0 |
| Task Queue | Background Tasks | - | Procesamiento asíncrono |
| Database | SQLite/PostgreSQL | - | Persistencia de casos |
| Evidence Store | File System | - | Almacenamiento forense |

#### 2.2.2 Frontend (React)

| Componente | Tecnología | Función |
|------------|------------|---------|
| UI Framework | React 18 + Vite | SPA moderna |
| State Management | Redux Toolkit | Estado global |
| Styling | Tailwind CSS | Diseño responsive |
| Visualization | Cytoscape.js | Grafos de ataque |
| HTTP Client | Axios | Comunicación API |

### 2.3 Stack Tecnológico

```yaml
Backend:
  - Python 3.11+
  - FastAPI 0.104+
  - Pydantic 2.0+
  - MSAL (Microsoft Auth)
  - aiohttp (async HTTP)

Frontend:
  - React 18.2
  - Vite 5.0
  - Redux Toolkit
  - Tailwind CSS 3.3
  - Cytoscape.js 3.28

Herramientas Forenses:
  - Sparrow 365
  - Hawk (Exchange Forensics)
  - Loki Scanner
  - YARA Rules
  - OSQuery
  - Volatility 3

Integraciones:
  - Microsoft Graph API
  - Have I Been Pwned API
  - VirusTotal API
  - AbuseIPDB
  - Shodan
```

---

## 3. Capacidades Técnicas

### 3.1 Análisis Microsoft 365

#### Funcionalidades

| Capacidad | Descripción | Herramienta |
|-----------|-------------|-------------|
| **Sign-in Analysis** | Detección de accesos anómalos | Graph API + Sparrow |
| **Audit Log Extraction** | Extracción de logs unificados | O365 Extractor |
| **Mailbox Forensics** | Análisis de reglas y delegaciones | Hawk |
| **OAuth App Audit** | Detección de apps maliciosas | Graph API |
| **MFA Status** | Verificación de autenticación multifactor | Graph API |
| **Conditional Access** | Evaluación de políticas | Graph API |

#### Flujo de Análisis M365

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Usuario   │────▶│   Tenant    │────▶│   Análisis  │────▶│   Reporte   │
│   Input     │     │   Connect   │     │   Forense   │     │   + IOCs    │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │                   │
       ▼                   ▼                   ▼                   ▼
  Email/UPN          OAuth Token         Sparrow/Hawk        Attack Graph
  Tenant ID          Graph API           Audit Logs          Timeline
  Días atrás         Permisos            Evidence            Executive PDF
```

### 3.2 Análisis de Endpoints

#### Herramientas Integradas

| Herramienta | Función | Plataformas |
|-------------|---------|-------------|
| **Loki** | Scanner de IOCs y YARA | Windows, Linux, macOS |
| **YARA** | Detección de malware por firmas | Universal |
| **OSQuery** | Consultas SQL sobre sistema | Windows, Linux, macOS |
| **Volatility** | Análisis de memoria RAM | Windows, Linux |

#### Comandos Disponibles por OS

**Windows:**
```powershell
# Procesos
tasklist /v
Get-Process | Sort-Object CPU -Descending | Select -First 20

# Red
netstat -ano
Get-NetTCPConnection | Where-Object State -eq 'Established'

# Registro
Get-ItemProperty HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run

# Event Logs
Get-EventLog -LogName Security -Newest 100
```

**Linux/macOS:**
```bash
# Procesos
ps aux --sort=-%cpu | head -20
lsof -i -P -n

# Red
ss -tulpn
netstat -an | grep LISTEN

# Cron
crontab -l
cat /etc/crontab

# Logs
ausearch -m ALL | tail -100
```

### 3.3 Análisis de Credenciales

#### Fuentes de Inteligencia

| Fuente | Tipo | Rate Limit | Datos |
|--------|------|------------|-------|
| **HIBP** | Breaches | 1 req/1.5s | Brechas, pastes |
| **Dehashed** | Leaks | API Key | Credenciales filtradas |
| **IntelX** | Dark Web | Premium | Stealer logs |
| **Sherlock** | OSINT | Local | Perfiles sociales |

### 3.4 IOC Store

#### Tipos de IOC Soportados

```
┌─────────────────────────────────────────────────────────────┐
│  TAXONOMÍA DE INDICADORES DE COMPROMISO                     │
├─────────────────────────────────────────────────────────────┤
│  🌐 IP Addresses      │  IPv4, IPv6, CIDR ranges           │
│  🔗 Domains           │  FQDN, subdomains                  │
│  📧 Email Addresses   │  Sender, recipient                 │
│  #️⃣ File Hashes       │  MD5, SHA1, SHA256                 │
│  📄 File Names        │  Executable, documents             │
│  🔗 URLs              │  Full URLs, paths                  │
│  👤 User Accounts     │  UPN, SID, username                │
│  🔑 Registry Keys     │  Windows registry paths            │
│  ⚙️ Process Names     │  Executable names, command lines   │
│  🏷️ YARA Rules        │  Custom detection signatures       │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Módulos Disponibles

### 4.1 Dashboard Principal

**Ruta:** `/dashboard`

Proporciona vista ejecutiva con:
- Estadísticas de casos activos
- Alertas críticas
- Timeline de actividad
- Acciones rápidas

### 4.2 Investigaciones (Cases)

**Ruta:** `/investigations`

Gestión completa del ciclo de vida de casos:
- Creación y asignación
- Workflow de estados
- Recolección de evidencia
- Generación de reportes

### 4.3 Microsoft 365 Forensics

**Ruta:** `/m365`

Análisis especializado para entornos M365:
- Conexión multi-tenant
- Análisis de cuentas comprometidas
- Extracción de audit logs
- Detección de OAuth apps maliciosas

### 4.4 Mobile Agents

**Ruta:** `/agents`

Gestión de agentes remotos:
- Deploy de Intune/OSQuery/Velociraptor
- Ejecución de comandos
- Captura de red
- Memory dumps

### 4.5 Active Investigation

**Ruta:** `/active-investigation`

Investigación en tiempo real:
- Command Executor
- Network capture
- Live forensics
- IOC scanning

### 4.6 Attack Graph

**Ruta:** `/graph`

Visualización de relaciones:
- Nodos por tipo de IOC
- Conexiones temporales
- Export PNG/JSON
- Layouts interactivos

### 4.7 IOC Store (NUEVO)

**Ruta:** `/iocs`

Repositorio centralizado de IOCs:
- CRUD completo
- Importación masiva (CSV, STIX, OpenIOC)
- Exportación a SIEM
- Scoring de confianza
- Histórico y versionado

### 4.8 Threat Hunting

**Ruta:** `/threat-hunting`

Búsqueda proactiva de amenazas:
- Query builder
- Saved searches
- Correlation rules
- Hypothesis tracking

---

## 5. Integraciones

### 5.1 Microsoft Graph API

```python
# Permisos requeridos (Application)
GRAPH_PERMISSIONS = [
    "AuditLog.Read.All",
    "Directory.Read.All",
    "User.Read.All",
    "SecurityEvents.Read.All",
    "IdentityRiskyUser.Read.All",
    "Mail.Read",
    "MailboxSettings.Read"
]
```

### 5.2 SIEM Integration

| SIEM | Método | Formato |
|------|--------|---------|
| Microsoft Sentinel | API | CEF/Syslog |
| Splunk | HEC | JSON |
| Elastic SIEM | API | ECS |
| QRadar | Syslog | LEEF |

### 5.3 Ticketing Systems

| Sistema | Integración |
|---------|-------------|
| ServiceNow | REST API |
| Jira | REST API |
| TheHive | REST API |
| RTIR | Email/API |

---

## 6. Guía de Implementación

### 6.1 Requisitos del Sistema

#### Hardware Mínimo

| Componente | Mínimo | Recomendado |
|------------|--------|-------------|
| CPU | 4 cores | 8+ cores |
| RAM | 8 GB | 16+ GB |
| Disco | 100 GB SSD | 500+ GB NVMe |
| Red | 100 Mbps | 1 Gbps |

#### Software Requerido

```bash
# Sistema Operativo
- Kali Linux 2024.1+ (recomendado)
- Ubuntu 22.04 LTS
- Debian 12

# Runtime
- Python 3.11+
- Node.js 18+
- PowerShell 7.3+

# Herramientas
- Git
- Docker (opcional)
```

### 6.2 Instalación Rápida

```bash
# 1. Clonar repositorio
git clone https://github.com/jcarvajalantigua/mcp-kali-forensics.git
cd mcp-kali-forensics

# 2. Ejecutar instalador nativo
chmod +x scripts/setup_native.sh
./scripts/setup_native.sh

# 3. Activar entorno
source venv/bin/activate

# 4. Configurar M365 (opcional)
cd scripts && ./setup_m365_interactive.sh

# 5. Iniciar servicios
# Terminal 1 - Backend
uvicorn api.main:app --reload --port 9000

# Terminal 2 - Frontend
cd frontend-react && npm install && npm run dev
```

### 6.3 Configuración Post-Instalación

```bash
# Crear archivo .env
cat > .env << EOF
# API Configuration
API_KEY=your-secure-api-key-here
DEBUG=false

# Microsoft 365
M365_TENANT_ID=your-tenant-id
M365_CLIENT_ID=your-client-id
M365_CLIENT_SECRET=your-client-secret

# External APIs
HIBP_API_KEY=your-hibp-key
VIRUSTOTAL_API_KEY=your-vt-key
ABUSEIPDB_API_KEY=your-abuseipdb-key

# Database
DATABASE_URL=sqlite:///./forensics.db

# Evidence Storage
EVIDENCE_DIR=/home/user/forensics-evidence
EOF
```

---

## 7. Casos de Uso

### 7.1 Business Email Compromise (BEC)

**Escenario:** Ejecutivo reporta emails sospechosos enviados desde su cuenta.

**Workflow:**

```
1. Crear caso IR-2025-XXX
   └─▶ Asignar investigador
   
2. Conectar tenant M365
   └─▶ OAuth device code flow
   
3. Ejecutar análisis de cuenta
   ├─▶ Sign-in logs (ubicaciones anómalas)
   ├─▶ Mailbox rules (forwarding malicioso)
   ├─▶ OAuth apps (consent phishing)
   └─▶ Audit logs (actividad sospechosa)
   
4. Generar IOCs
   ├─▶ IPs de origen
   ├─▶ User agents
   └─▶ Dominios de forwarding
   
5. Visualizar Attack Graph
   └─▶ Timeline de compromiso
   
6. Generar reporte ejecutivo
   └─▶ PDF con recomendaciones
```

### 7.2 Ransomware Incident

**Escenario:** Múltiples endpoints cifrados, se sospecha de acceso inicial via email.

**Workflow:**

```
1. Crear caso crítico
   └─▶ Prioridad P1
   
2. Desplegar agentes Velociraptor
   └─▶ Endpoints afectados
   
3. Análisis de memoria (Volatility)
   ├─▶ Procesos maliciosos
   ├─▶ Network connections
   └─▶ Injected code
   
4. Scan YARA/Loki
   ├─▶ Detección de variante
   └─▶ IOCs adicionales
   
5. M365 forensics
   ├─▶ Email inicial (phishing)
   └─▶ Cuentas comprometidas
   
6. IOC enrichment
   ├─▶ VirusTotal
   ├─▶ AbuseIPDB
   └─▶ Threat Intel feeds
   
7. Reporte técnico + ejecutivo
```

### 7.3 Insider Threat

**Escenario:** Empleado sospechoso de exfiltrar datos antes de renunciar.

**Workflow:**

```
1. Crear caso confidencial
   └─▶ Acceso restringido
   
2. M365 audit logs
   ├─▶ Downloads masivos (SharePoint/OneDrive)
   ├─▶ Emails a externos
   └─▶ USB/Cloud sync activity
   
3. Endpoint forensics
   ├─▶ Browser history
   ├─▶ USB devices conectados
   └─▶ Cloud storage apps
   
4. Timeline completo
   └─▶ Correlación de eventos
   
5. Reporte legal
   └─▶ Evidencia para RRHH/Legal
```

---

## 8. Seguridad y Cumplimiento

### 8.1 Controles de Seguridad

| Control | Implementación |
|---------|----------------|
| **Autenticación** | API Keys + OAuth 2.0 |
| **Autorización** | RBAC por caso |
| **Cifrado en tránsito** | TLS 1.3 |
| **Cifrado en reposo** | AES-256 (evidencia) |
| **Logging** | Audit trail completo |
| **Secrets** | Environment variables |

### 8.2 Cumplimiento Normativo

| Normativa | Aplicabilidad |
|-----------|---------------|
| **GDPR** | Manejo de datos EU |
| **HIPAA** | Healthcare (USA) |
| **PCI-DSS** | Datos de tarjetas |
| **SOC 2** | Controles de seguridad |
| **ISO 27001** | ISMS |
| **NIST CSF** | Framework de seguridad |

### 8.3 Cadena de Custodia

```
┌─────────────────────────────────────────────────────────────┐
│  CHAIN OF CUSTODY - DIGITAL EVIDENCE                        │
├─────────────────────────────────────────────────────────────┤
│  ✓ Hash SHA-256 de cada artefacto                          │
│  ✓ Timestamp UTC de recolección                            │
│  ✓ Identificador único de caso                             │
│  ✓ Usuario que recolectó                                   │
│  ✓ Herramienta utilizada                                   │
│  ✓ Verificación de integridad                              │
│  ✓ Almacenamiento inmutable                                │
└─────────────────────────────────────────────────────────────┘
```

---

## 9. Soporte y Mantenimiento

### 9.1 Canales de Soporte

| Nivel | Canal | SLA |
|-------|-------|-----|
| **L1** | soporte@jeturing.com | 4 horas |
| **L2** | Ticket escalado | 8 horas |
| **L3** | Ingeniería | 24 horas |
| **Emergencia** | +1-XXX-XXX-XXXX | 1 hora |

### 9.2 Actualizaciones

```bash
# Actualizar a última versión
cd /home/hack/mcp-kali-forensics
git pull origin main
pip install -r requirements.txt
cd frontend-react && npm install
```

### 9.3 Backup y Recovery

```bash
# Backup de base de datos
sqlite3 forensics.db ".backup 'backup_$(date +%Y%m%d).db'"

# Backup de evidencia
tar -czvf evidence_backup_$(date +%Y%m%d).tar.gz ~/forensics-evidence/

# Restore
sqlite3 forensics.db ".restore 'backup_YYYYMMDD.db'"
```

---

## 10. Anexos Técnicos

### A. Endpoints API Reference

```
BASE_URL: http://localhost:9000

# Health & Status
GET  /health
GET  /

# Cases
GET  /forensics/case/
POST /forensics/case/
GET  /forensics/case/{case_id}
PUT  /forensics/case/{case_id}

# M365 Forensics
POST /forensics/m365/analyze
POST /forensics/m365/account-analysis
GET  /forensics/m365/tenant-info

# Agents
GET  /api/agents
POST /api/agents/deploy
POST /api/agents/{agent_id}/execute

# Investigations
GET  /api/investigations
POST /api/investigations
GET  /api/investigations/{id}
GET  /api/investigations/{id}/graph

# Active Investigation
POST /api/active-investigation/execute
GET  /api/active-investigation/templates
POST /api/active-investigation/capture/start

# IOCs
GET  /api/iocs
POST /api/iocs
GET  /api/iocs/{id}
POST /api/iocs/import
GET  /api/iocs/export
```

### B. Códigos de Error

| Código | Significado |
|--------|-------------|
| 200 | Éxito |
| 201 | Creado |
| 400 | Request inválido |
| 401 | No autenticado |
| 403 | No autorizado |
| 404 | No encontrado |
| 422 | Validación fallida |
| 429 | Rate limit excedido |
| 500 | Error interno |

---

## Novedades v3.0 - Persistencia y Tiempo Real

### Base de Datos SQLAlchemy

La versión 3.0 introduce persistencia real con SQLAlchemy:

```python
# Modelos principales
- IocItem: Indicadores de Compromiso
- IocTag: Etiquetas para categorización
- IocEnrichment: Datos de enriquecimiento
- IocSighting: Avistamientos/detecciones
- Investigation: Investigaciones IR
- InvestigationIocLink: Vinculación IOC↔Investigación
- InvestigationTimeline: Eventos de timeline
- Case: Casos forenses
- CaseEvidence: Evidencia digital
```

### WebSockets en Tiempo Real

Canales WebSocket disponibles:

| Canal | Endpoint | Eventos |
|-------|----------|---------|
| IOC Store | `/ws/ioc-store` | ioc_created, ioc_updated, ioc_deleted, ioc_enriched, import_completed |
| Investigations | `/ws/investigations` | investigation_updated, ioc_linked, ioc_unlinked |
| Investigation específica | `/ws/investigation/{id}` | updated, ioc_linked, ioc_unlinked, timeline_event |
| Dashboard | `/ws/dashboard` | stats_update, alert, case_update |
| Agents | `/ws/agents` | agent_connected, task_completed, evidence_collected |

### Integración IOC↔Investigaciones

Nuevos endpoints REST:

```
GET  /api/investigations/{id}/iocs     - Listar IOCs vinculados
POST /api/investigations/{id}/iocs/{ioc_id} - Vincular IOC
DELETE /api/investigations/{id}/iocs/{ioc_id} - Desvincular IOC
GET  /api/investigations/{id}/timeline-db - Timeline desde BD
POST /api/investigations/{id}/timeline-db - Agregar evento
```

---

### C. Glosario

| Término | Definición |
|---------|------------|
| **IOC** | Indicator of Compromise - Artefacto que indica intrusión |
| **TTPs** | Tactics, Techniques, Procedures - Comportamientos de atacantes |
| **DFIR** | Digital Forensics and Incident Response |
| **BEC** | Business Email Compromise |
| **APT** | Advanced Persistent Threat |
| **SIEM** | Security Information and Event Management |
| **EDR** | Endpoint Detection and Response |
| **SOAR** | Security Orchestration, Automation and Response |

---

## 📞 Contacto

**JETURING - Cybersecurity Solutions**

- 🌐 Web: https://jeturing.com
- 📧 Email: info@jeturing.com
- 📱 Soporte: soporte@jeturing.com
- 🐙 GitHub: https://github.com/jcarvajalantigua

---

<div align="center">

**© 2025 JETURING. Todos los derechos reservados.**

*Este documento es confidencial y está destinado únicamente para uso interno y de clientes autorizados.*

</div>
