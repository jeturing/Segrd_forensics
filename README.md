# 🛡️ MCP Kali Forensics & IR Worker

**Micro Compute Pod** especializado en análisis forense y respuesta a incidentes para Microsoft 365, Azure AD, endpoints comprometidos y credenciales filtradas.

[![Version](https://img.shields.io/badge/version-4.6.0-blue.svg)](docs/v4.6/)
[![Backend](https://img.shields.io/badge/backend-FastAPI-009688.svg)](api/)
[![Frontend](https://img.shields.io/badge/frontend-React%2018-61DAFB.svg)](frontend-react/)
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)](#)

---

## 🆕 Novedades v4.6.0 - Gestión de Agentes LLM

**Nueva funcionalidad**: Sistema completo de gestión de agentes LLM (Ollama) por tenant desde la consola de administración.

📖 **[Ver Guía Completa](/docs/v4.6/LLM_AGENT_MANAGEMENT.md)** | 📄 **[Resumen Ejecutivo](/docs/v4.6/EXECUTIVE_SUMMARY.md)**

### Características principales:
- 🤖 **Crear agentes Ollama con un click** desde el frontend
- 🏢 **Asignación por tenant** - Cada tenant puede tener sus agentes dedicados
- 🎛️ **Gestión completa**: Iniciar, detener, eliminar contenedores desde UI
- 👥 **Administración multi-tenant**: CRUD de tenants y usuarios integrado
- 📊 **Dashboard en tiempo real**: Estadísticas de agentes, recursos y estado
- 🐳 **Integración Docker nativa**: Creación dinámica de contenedores

**Endpoints disponibles**: `/api/llm-agents/*` (8 endpoints REST)  
**Componentes React**: `LLMAgentManager.jsx`, `TenantManagement.jsx`  
**Instalación**: `./scripts/install_llm_agent_mgmt.sh`

---

## 📚 DOCUMENTACIÓN

### ⭐ **[EMPEZAR AQUÍ → /docs/README.md](/docs/README.md)**

**Toda la documentación está organizada en la carpeta `/docs/`**

- 🚀 **Nuevo usuario?** → [Getting Started](/docs/getting-started/)
- 👨‍💻 **Desarrollador?** → [Backend](/docs/backend/) o [Frontend](/docs/frontend/)
- 🚀 **Producción?** → [Deployment](/docs/deployment/)
- 🆘 **Problemas?** → [Troubleshooting](/docs/reference/TROUBLESHOOTING.md)

**📊 Análisis del Repositorio (Nuevo - Dic 2024):**
- 🎯 [**ÍNDICE DE ANÁLISIS**](INDICE_ANALISIS.md) - ⭐ Empieza aquí - Guía completa del análisis
- 📊 [Análisis Completo](ANALISIS_COMPLETO_REPOSITORIO.md) - Análisis técnico detallado (35KB)
- 📋 [Resumen Ejecutivo](RESUMEN_EJECUTIVO.md) - Para stakeholders y management (10KB)
- 🚀 [Guía Rápida](GUIA_RAPIDA_HALLAZGOS.md) - Para desarrolladores (8KB)
- 📈 [Métricas](METRICAS_Y_ESTADISTICAS.md) - Estadísticas del proyecto (14KB)

**✅ Mejoras Implementadas (Nuevo - Dic 2024):**
- 🎯 [**RESUMEN DE MEJORAS**](RESUMEN_MEJORAS_IMPLEMENTADAS.md) - ⭐ 6/11 mejoras completadas (54%)
- 🔐 RBAC habilitado por defecto - Seguridad en producción
- 🚀 CI/CD Pipeline completo - GitHub Actions con testing/security/deploy
- 💾 PostgreSQL Migration - Base de datos escalable
- 🐳 Docker Optimization - Imagen reducida 70% (2GB → 600MB)
- 🔄 API Consolidation - Rutas versionadas `/api/v1/*`

**Novedades v4.4.1:**
- [CHANGELOG](/docs/v4.4.1/CHANGELOG.md)
- [BREAKING CHANGES](/docs/v4.4.1/BREAKING_CHANGES.md)
- [RBAC GUIDE](/docs/v4.4.1/RBAC_GUIDE.md)
- [STREAMING ARCHITECTURE](/docs/v4.4.1/STREAMING_ARCHITECTURE.md)

---

## 🎯 Propósito

Automatizar flujos de investigación forense usando herramientas enterprise (Sparrow, Hawk, Loki, YARA) ejecutándose **nativamente en Kali Linux/WSL** con integración a **Jeturing CORE**.

## ✨ Características v4.4.1

| Módulo | Descripción | Estado |
|--------|-------------|--------|
| 🔐 **M365 Forensics** | 12 herramientas (Sparrow, Hawk, AzureHound, ROADtools, etc.) | ✅ |
| 📡 **Streaming** | Logs en tiempo real via WebSocket | ✅ |
| 🎯 **ForensicAnalysis** | Modelo completo con auditoría y versionado | ✅ |
| 🛡️ **RBAC** | Permisos granulares y rate limiting | ✅ |
| 🐳 **Microservicios** | Arquitectura Docker escalable | ✅ |
| 📊 **Observabilidad** | OpenTelemetry (Traces/Metrics) | ✅ |
| 🔍 **Investigations** | Gestión de casos con timeline y IOC linking | ✅ |
| ⚡ **WebSockets** | Actualizaciones en tiempo real | ✅ |
| 📱 **Mobile Agents** | Ejecución remota en endpoints | ✅ |
| 🕸️ **Attack Graph** | Visualización de cadenas de ataque | ✅ |
| 🔑 **Credentials** | HIBP, Dehashed, stealer logs | ✅ |
| 🖥️ **Endpoint Scan** | Loki, YARA, OSQuery, Volatility | ✅ |

---

## 📌 Novedades v4.4.1 - Enterprise Architecture

### 🏗️ **Arquitectura de Microservicios**

La versión 4.4.1 introduce una arquitectura robusta basada en Docker Compose:

- **mcp-forensics**: API Gateway y orquestador principal.
- **ws-router**: Enrutador WebSocket para streaming masivo.
- **logging-worker**: Procesamiento asíncrono de logs.
- **executor**: Entorno sandboxed para herramientas forenses.
- **postgres**: Base de datos relacional para metadatos.
- **redis**: Cola de tareas y Pub/Sub.

### 📡 **Streaming en Tiempo Real**

Nuevo sistema de logs via WebSocket:

```javascript
// Frontend Client
const ws = new WebSocket('ws://localhost:8888/ws/analysis/FA-2025-00001');
ws.onmessage = (event) => {
    const log = JSON.parse(event.data);
    console.log(`[${log.level}] ${log.message}`);
};
```

### 🛡️ **RBAC Hardening**

Sistema de permisos granulares con 5 niveles:
- `mcp:read`: Lectura de casos y análisis.
- `mcp:write`: Creación y modificación de casos.
- `mcp:run-tools`: Ejecución de herramientas forenses.
- `mcp:manage-agents`: Gestión de agentes remotos.
- `mcp:admin`: Acceso total al sistema.

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                    JETURING CORE                            │
│         (Multi-tenant · Auth0 · AppRegistry)                │
└─────────────────────────┬───────────────────────────────────┘
                          │ REST + WebSocket
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              MCP-KALI (Docker Compose)                      │
                        ### Despliegue
                        **Despliegue Rápido:** see `DEPLOYMENT.md` for a one-click local docker-compose deployment and Ollama per-agent setup.

│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ WS Router   │  │ API Gateway │  │ Logging Worker      │  │
│  │ (Streaming) │  │ (FastAPI)   │  │ (Aggregation)       │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │            Executor (Sandboxed Tools)               │    │
│  │ Sparrow | Hawk | Loki | YARA | Volatility           │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
    ┌──────────┐   ┌──────────┐   ┌──────────────┐
    │ Postgres │   │ Redis    │   │ Filesystem   │
    └──────────┘   └──────────┘   └──────────────┘
```

---

## 🚀 Quick Start

### ⭐ Instalación Unificada (Nuevo v4.6.0)

Hemos simplificado el proceso de instalación con un único script que maneja tanto la instalación nativa como Docker.

```bash
# Clonar repositorio
git clone https://github.com/jcarvajalantigua/mcp-kali-forensics.git
cd mcp-kali-forensics

# Ejecutar instalador unificado
chmod +x unified_install.sh
./unified_install.sh
```

El instalador te permitirá elegir entre:
1. **Instalación Nativa (Kali/WSL)**: Ideal para desarrollo y acceso directo a herramientas.
2. **Instalación Docker**: Ideal para producción y aislamiento.

El script se encargará de:
- Verificar dependencias del sistema.
- Configurar entorno Python/Node.js.
- Generar archivo `.env` interactivo.
- Instalar herramientas forenses.
- Iniciar los servicios.

### 🐳 Docker Compose Manual (Alternativa)

Si prefieres usar Docker Compose directamente:

```bash
# Configurar entorno
cp .env.example .env
# Editar .env con credenciales M365 y configuración RBAC

# Iniciar servicios
docker-compose -f docker-compose.v4.4.1.yml up -d


# Verificar estado
docker-compose -f docker-compose.v4.4.1.yml ps

---

### **Configuración de Base de Datos y Migración de Credenciales**

- **Generación de credenciales durante la instalación:** El instalador unificado (`unified_install.sh` / `scripts/install_brac.py`) crea de forma interactiva el archivo `.env` y puede generar las credenciales iniciales (usuarios, contraseñas, tokens) para que la instancia funcione en modo nativo. En instalaciones nativas (Kali/WSL) el backend utiliza por defecto SQLite (`./forensics.db`) y algunos secretos/credenciales pueden almacenarse en esa base de datos local o en el propio `.env` generado.

- **Comportamiento al mover a Docker:** En entorno Docker/producción la recomendación es usar PostgreSQL. Cuando trasladas la aplicación desde una instalación nativa (SQLite) a Docker, debes migrar los datos (incluyendo las credenciales que el instalador pudo generar) desde SQLite hacia PostgreSQL para que queden centralizados y persistentes en el servicio `postgres`.

- **Pasos recomendados para migrar credenciales y metadatos a PostgreSQL:**
   1. Parar la aplicación local si está corriendo y asegurar una copia de seguridad del archivo SQLite:

```bash
cp ./forensics.db ./forensics.db.backup.$(date +%Y%m%d_%H%M%S)
```

   2. Preparar Postgres (docker-compose): editar `.env` o exportar variables para que `docker-compose` cree la base de datos y el usuario. Ejemplo mínimo en la raíz del repo:

```bash
cat > .env <<'EOF'
DB_PASSWORD=mi_contraseña_segura
# O puede definir la cadena completa:
DATABASE_URL=postgresql+asyncpg://forensics:mi_contraseña_segura@postgres:5432/forensics
EOF
```

   3. Levantar solo Postgres (opcional):

```bash
docker-compose up -d postgres
```

   4. Ejecutar la herramienta de migración incluida que copia datos de SQLite a PostgreSQL (existe `scripts/migrate_sqlite_to_postgres.py`):

```bash
# Opcional: exportar variables de entorno para que el script las use
export SQLITE_URL="sqlite:///./forensics.db"
export DATABASE_URL="postgresql+asyncpg://forensics:mi_contraseña_segura@localhost:5432/forensics"
python3 scripts/migrate_sqlite_to_postgres.py
```

   5. Verificar que los datos y usuarios (credenciales) existen en PostgreSQL. Puedes usar `psql` o alguna GUI para comprobar tablas relevantes (`user`, `tenant`, `config`, `credentials` según el esquema):

```bash
psql "postgresql://forensics:mi_contraseña_segura@localhost:5432/forensics" -c "\dt"
```

   6. Actualizar `.env` en la raíz para apuntar a PostgreSQL (si no lo hiciste antes) y reiniciar los servicios del backend:

```bash
# Asegúrate de que .env contiene la cadena correcta
docker-compose up -d
```

   7. (Opcional) Archivar o eliminar el fichero `forensics.db` local tras verificar la migración:

```bash
mv forensics.db forensics.db.archived
```

- **Notas y buenas prácticas:**
   - Nunca guardar `.env` con credenciales en el repositorio. Usa `.env.example` para variables de ejemplo y mantén `.env` en `.gitignore`.
   - Establece permisos restrictivos para `.env`: `chmod 600 .env`.
   - Si usas Kubernetes/Helm, gestiona la cadena `DATABASE_URL` como Secret (ver `helm/mcp-forensics/templates/secrets.yaml`).
   - Si prefieres un procedimiento manual, puedes exportar tablas concretas desde SQLite y cargarlas en PostgreSQL, pero la herramienta `scripts/migrate_sqlite_to_postgres.py` automatiza este proceso y preserva relaciones.

---
```

### Acceso

| Servicio | URL | Puerto |
|----------|-----|--------|
| 🔧 API Swagger | http://localhost:8888/docs | 8888 |
| 🎨 React Frontend | http://localhost:3001 | 3001 |
| 📊 API Health | http://localhost:8888/health | 8888 |
| 📡 WebSocket | ws://localhost:8888/ws | 8888 |

---

## 🎯 Flujo de Trabajo: Análisis Forense M365

### Con Streaming (v4.4.1)

```
1. Crear Caso
   POST /cases -> IR-2025-001
   
2. Iniciar Análisis
   POST /forensics/m365/analyze
   { "case_id": "IR-2025-001", "scope": ["sparrow"] }
   -> Retorna: FA-2025-00001 (Accepted)
   
3. Conectar Streaming (Frontend)
   WS /ws/analysis/FA-2025-00001
   <- Recibe logs en tiempo real, status updates, findings
   
4. Ejecución (Backend)
   Executor -> Docker Sandbox -> Tool (Sparrow)
   Logs -> LoggingQueue -> WS Router -> Client
   Evidence -> Filesystem -> EvidenceTree
   
5. Finalización
   Status -> Completed
   Findings -> DB
   Report -> Generated
```

---

## 📡 API Endpoints Principales

### Forensic Analysis
```bash
# Iniciar análisis
curl -X POST http://localhost:8888/forensics/m365/analyze \
  -H "X-API-Key: $API_KEY" \
  -d '{"case_id":"IR-2025-001","scope":["sparrow"]}'

# Obtener estado
curl http://localhost:8888/forensics/status/FA-2025-00001
```

### Streaming
```javascript
// WebSocket connection
const ws = new WebSocket('ws://localhost:8888/ws/analysis/FA-2025-00001');
```

---

## 📂 Estructura del Proyecto v4.4.1

```
mcp-kali-forensics/
├── api/                      # FastAPI Backend
│   ├── main.py              # Entry point
│   ├── middleware/          # RBAC, Audit
│   ├── routes/              # REST endpoints
│   └── services/            # Business logic
├── core/                     # Core Components
│   ├── logging_queue.py     # Streaming Queue
│   ├── rbac_config.py       # Permission System
│   └── telemetry.py         # OpenTelemetry
├── docker/                   # Microservices
│   ├── Dockerfile.*         # Service definitions
│   └── seccomp-*.json       # Security profiles
├── frontend-react/          # React 18 + Vite
│   └── src/components/      # AnalysisViewer, LiveLogsPanel
├── docs/                    # Documentation
│   └── v4.4.1/              # Version specific docs
└── tests/                   # Test suites
```

---

## 🛠️ Herramientas Forenses Integradas

| Herramienta | Función | Ubicación |
|-------------|---------|-----------|
| **Sparrow 365** | Azure AD, OAuth tokens | `/opt/forensics-tools/Sparrow/` |
| **Hawk** | Mailboxes, Teams, reglas | PowerShell module |
| **Loki Scanner** | IOC detection | `/opt/forensics-tools/Loki/` |
| **YARA** | Malware detection | Nativo Kali |
| **Volatility 3** | Memory forensics | `/opt/forensics-tools/volatility3/` |
| **OSQuery** | System artifacts | Nativo Kali |

---

## 📖 Documentación

| Documento | Descripción |
|-----------|-------------|
| 📘 [**Documentación v4.4.1**](docs/v4.4.1/README.md) | Documentación de la versión actual |
| 🚀 [Quick Start](docs/getting-started/QUICKSTART.md) | Guía rápida de inicio |
| 📋 [API Reference](docs/backend/ESPECIFICACION_API.md) | Especificación de endpoints |
| 🛡️ [RBAC Guide](docs/v4.4.1/RBAC_GUIDE.md) | Guía de permisos y seguridad |
| 📡 [Streaming](docs/v4.4.1/STREAMING_ARCHITECTURE.md) | Arquitectura de streaming |

---

## 🔐 Seguridad

- ✅ **RBAC Hardening**: 5 niveles de permisos.
- ✅ **Rate Limiting**: Protección contra abuso.
- ✅ **Audit Logging**: Registro inmutable de operaciones.
- ✅ **Seccomp Filters**: Ejecución aislada de herramientas.
- ✅ **Network Isolation**: Microservicios en redes separadas.
- ✅ **Secrets Management**: Variables de entorno estrictas.

---

## 🧪 Testing

```bash
# Ejecutar tests
pytest tests/ -v

# Tests específicos v4.4.1
pytest tests/test_rbac.py -v
pytest tests/test_logging_queue.py -v
```

---

## 🤝 Contribuir

Proyecto interno de **Jeturing Security Platform**.

Para contribuir:
1. Fork del repositorio
2. Crear branch feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit cambios (`git commit -m 'feat: nueva funcionalidad'`)
4. Push al branch (`git push origin feature/nueva-funcionalidad`)
5. Abrir Pull Request

---

## 📄 Licencia

**Propietario** - Jeturing Security Platform

---

<div align="center">

**Desarrollado por Jeturing Security Team**

🔒 *Securing the digital world, one investigation at a time*

</div>
