"""
MCP Kali Forensics - FastAPI Main Application v4.6
Orquestador de análisis forense para M365, endpoints y credenciales
Con arquitectura orientada a casos, persistencia de procesos y Red Team HexStrike AI
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from contextlib import asynccontextmanager
import logging
from datetime import datetime
from typing import Optional
import json

from api.routes import m365, credentials, endpoint, cases, dashboard, tenants, graph, workflow, evidence, forensics_tools, graph_editor, account_analysis_routes, auth, oauth, agents, investigations, active_investigation, ioc_store, realtime, kali_tools, threat_intel, missing_endpoints, llm_settings, hunting, timeline, reports, modules, system_maintenance, system_health, tools_status, ws_streaming, monkey365, misp, configuration, context, redteam, llm_agents, costs, landing, storage, hunting_web_recon, security_checklist, contact, system_settings
from api.middleware.auth import verify_api_key
from api.middleware.case_context import CaseContextMiddleware
from api.middleware.rbac import RBACMiddleware
from api.services.registry import register_with_jeturing_core
from api.services.llm_provider import init_llm_manager, cleanup_llm_manager, get_llm_manager
from api.config import settings
from api.database import init_db
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

# Import v4.4 core components
from core import case_context_manager, process_manager

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/mcp-forensics.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Cargar routers v4.1 de forma opcional (aún en desarrollo)
v41_enabled = False
try:
    from api.routes import tools_v41, playbooks, correlation, graph_v41
    v41_enabled = True
except Exception as e:
    logger.warning(f"v4.1 routers deshabilitados: {e}")

# Cargar routers v4.1 con datos reales (sin mocks)
v41_real_data_enabled = False
try:
    from api.routes import agents_v41, investigations_v41
    v41_real_data_enabled = True
    logger.info("✅ Routers v4.1 con datos reales cargados")
except Exception as e:
    logger.warning(f"v4.1 routers de datos reales deshabilitados: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events para la aplicación"""
    # Startup
    logger.info("🚀 Iniciando MCP Kali Forensics v4.4 - Case-Oriented Architecture + Persistent Processes")
    
    # Inicializar base de datos
    try:
        init_db()
        logger.info("✅ Base de datos inicializada (SQLite)")
    except Exception as e:
        logger.error(f"❌ Error inicializando BD: {e}")
    
    # Inicializar Context Manager v4.4
    logger.info("🔵 Case Context Manager inicializado")
    
    # Inicializar Process Manager v4.4
    logger.info("🔵 Process Manager inicializado")
    
    # Registrar en Jeturing CORE
    if settings.JETURING_CORE_ENABLED:
        try:
            await register_with_jeturing_core()
            logger.info("✅ Registrado en Jeturing CORE")
        except Exception as e:
            logger.error(f"❌ Error al registrar en Jeturing CORE: {e}")
    
    # Verificar herramientas instaladas
    from api.services.health import check_tools_availability
    tools_status = await check_tools_availability()
    logger.info(f"📦 Herramientas disponibles: {tools_status}")
    
    # Inicializar LLM Provider Manager (agnóstico al modelo)
    try:
        llm_manager = await init_llm_manager()
        active_model = await llm_manager.get_active_model()
        if active_model:
            logger.info(f"🤖 LLM Manager iniciado - Modelo activo: {active_model.id}")
        else:
            logger.warning("⚠️ LLM Manager iniciado sin modelo activo - carga uno en LM Studio u Ollama")
    except Exception as e:
        logger.warning(f"⚠️ LLM Manager no disponible: {e}")
    
    yield
    
    # Shutdown
    logger.info("🛑 Deteniendo MCP Kali Forensics")
    
    # Limpiar recursos del LLM Manager
    try:
        await cleanup_llm_manager()
    except Exception:
        pass

    # Initialize audit logger (rotating file handler)
    try:
        from api.services.audit import _init_audit_logger
        _init_audit_logger()
        logger.info("📝 Audit logging configured (logs/audit.log)")
    except Exception as e:
        logger.warning(f"⚠️ Failed to initialize audit logger: {e}")

# Inicializar FastAPI
app = FastAPI(
    title="MCP Kali Forensics & IR",
    description="Micro Compute Pod para análisis forense automatizado - v4.4 con Arquitectura Orientada a Casos, Persistencia de Procesos y Agentes Funcionales",
    version="4.4.0",
    openapi_version="3.0.2",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Patch: Override openapi() method to return 3.0.2 for Swagger UI compatibility
_original_openapi = app.openapi

def patched_openapi():
    """Return OpenAPI schema with version 3.0.2 instead of 3.1.0 for Swagger UI compatibility."""
    schema = _original_openapi()
    if schema and isinstance(schema, dict):
        # Make a copy to avoid modifying the cached schema
        schema = dict(schema)
        schema["openapi"] = "3.0.2"
    return schema

# Bind the patched method to the app instance
app.openapi = patched_openapi

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
## Private Network Access (PNA) middleware
## Modern browsers enforce Private Network Access when a public origin
## (e.g. https://segrd.com) attempts to call a local/private address (localhost, 10.x.x.x).
## The preflight will include `Access-Control-Request-Private-Network: true` and
## the server must respond with `Access-Control-Allow-Private-Network: true`.
class PrivateNetworkMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # If the browser is sending a preflight with Private-Network hint,
        # we must include Access-Control-Allow-Private-Network in the response.
        add_pna = False
        try:
            if request.method == "OPTIONS":
                # Some browsers include this header in lowercase or mixed case
                if any(h.lower() == "access-control-request-private-network" for h in request.headers.keys()):
                    add_pna = True
        except Exception:
            add_pna = False

        response = await call_next(request)

        if add_pna:
            # Ensure the header is present on the preflight response
            response.headers.setdefault("Access-Control-Allow-Private-Network", "true")

        return response

# Register PNA middleware BEFORE CORS so the header is present for preflight responses
app.add_middleware(PrivateNetworkMiddleware)

# CORS Middleware (registered after PNA middleware so preflight responses
# can include the Access-Control-Allow-Private-Network header)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# RBAC Middleware v4.4.1 - Control de acceso basado en roles
# Verifica permisos por ruta y método HTTP con rate limiting
if settings.RBAC_ENABLED:
    app.add_middleware(RBACMiddleware)
    logger.info("🔐 RBAC Middleware habilitado")

# Case Context Middleware v4.4 - Asegura que operaciones forenses tengan case_id
# NOTA: Comentado temporalmente para no romper endpoints existentes
# app.add_middleware(CaseContextMiddleware)

# Health check endpoint (sin autenticación)
@app.get("/health")
async def health_check():
    """Health check para monitoreo"""
    return {
        "status": "healthy",
        "service": "mcp-kali-forensics",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "4.4.0"
    }

# Custom OpenAPI endpoint that downgrades 3.1 to 3.0.2 for Swagger UI
@app.get("/openapi.json", include_in_schema=False)
async def get_openapi_json():
    """Serve OpenAPI schema with version 3.0.2 for Swagger UI compatibility"""
    schema = app.openapi()
    if schema:
        schema["openapi"] = "3.0.2"
    return schema

@app.get("/")
async def root():
    """Root endpoint con información del servicio"""
    return {
        "service": "MCP Kali Forensics & IR Worker",
        "version": "4.4.0",
        "capabilities": [
            "m365_forensics",
            "credential_analysis", 
            "endpoint_scanning",
            "ioc_detection",
            "case_oriented_architecture",
            "persistent_processes",
            "functional_agents"
        ],
        "docs": "/docs",
        "health": "/health"
    }

# v4.4 - Process Manager endpoints
@app.get("/processes", tags=["Process Management"])
async def get_processes(case_id: Optional[str] = None):
    """Obtener procesos activos, opcionalmente filtrados por caso"""
    if case_id:
        processes = process_manager.get_case_processes(case_id)
    else:
        processes = process_manager.get_running_processes()
    return {
        "processes": [p.to_dict() for p in processes],
        "stats": process_manager.get_stats(case_id)
    }

@app.get("/processes/{process_id}", tags=["Process Management"])
async def get_process_status(process_id: str):
    """Obtener estado de un proceso específico"""
    process = process_manager.get_process(process_id)
    if not process:
        raise HTTPException(status_code=404, detail="Process not found")
    return process.to_dict()

@app.delete("/processes/{process_id}", tags=["Process Management"])
async def cancel_process(process_id: str):
    """Cancelar un proceso en ejecución"""
    success = process_manager.cancel_process(process_id)
    if not success:
        raise HTTPException(status_code=400, detail="Process not running or not found")
    return {"status": "cancelled", "process_id": process_id}

# v4.4 - Active Cases Context endpoints
@app.get("/context/active-cases", tags=["Case Context"])
async def get_active_case_contexts():
    """Obtener todos los casos con sesiones activas"""
    return {
        "active_cases": case_context_manager.get_all_active_cases(),
        "timestamp": datetime.utcnow().isoformat()
    }
    return {
        "service": "MCP Kali Forensics & IR Worker",
        "version": "1.0.0",
        "capabilities": [
            "m365_forensics",
            "credential_analysis", 
            "endpoint_scanning",
            "ioc_detection"
        ],
        "docs": "/docs",
        "health": "/health"
    }

# Authentication & session management
app.include_router(
    auth.router,
    tags=["Authentication"]
)

# Incluir routers con autenticación
app.include_router(
    m365.router,
    prefix="/forensics/m365",
    tags=["M365 Forensics"],
    dependencies=[Depends(verify_api_key)]
)

app.include_router(
    credentials.router,
    prefix="/forensics/credentials",
    tags=["Credential Analysis"],
    dependencies=[Depends(verify_api_key)]
)

# Alias para compatibilidad con frontend (sin prefijo /forensics)
app.include_router(
    credentials.router,
    prefix="/credentials",
    tags=["Credential Analysis (alias)"],
    dependencies=[Depends(verify_api_key)]
)

app.include_router(
    endpoint.router,
    prefix="/forensics/endpoint",
    tags=["Endpoint Forensics"],
    dependencies=[Depends(verify_api_key)]
)

app.include_router(
    cases.router,
    prefix="/forensics/case",
    tags=["Case Management"],
    dependencies=[Depends(verify_api_key)]
)
# Alias sin prefix para compatibilidad con frontend legacy
app.include_router(
    cases.router,
    prefix="/cases",
    tags=["Case Management (alias)"],
    dependencies=[Depends(verify_api_key)]
)

# Alias con /api/cases para frontend React
app.include_router(
    cases.router,
    prefix="/api/cases",
    tags=["Case Management (API)"],
    dependencies=[Depends(verify_api_key)]
)

# Dashboard router (sin autenticación para acceso rápido)
app.include_router(
    dashboard.router,
    tags=["Dashboard"]
)

# API router for dashboard data (con autenticación)
app.include_router(
    dashboard.router,
    prefix="/api",
    tags=["Dashboard API"]
)

# Multi-tenant management router
# IMPORTANTE: Solo registrar UNA VEZ con prefix /tenants
# El frontend debe llamar siempre a /tenants/
app.include_router(
    tenants.router,
    prefix="/tenants",
    tags=["Multi-Tenant Management"]
)

# System maintenance (DB stats/cleanup)
app.include_router(
    system_maintenance.router,
    tags=["System Maintenance"]
)

# Configuration management (API Keys, Settings)
app.include_router(
    configuration.router,
    prefix="/api",
    tags=["Configuration"]
)

# Landing content routers
app.include_router(
    landing.public_router,
    tags=["Public Landing"]
)
app.include_router(
    landing.admin_router,
    tags=["Global Admin Landing"]
)

# Context management (Case-centric architecture)
app.include_router(
    context.router,
    tags=["Context Management"]
)

# Health & tools status
app.include_router(system_health.router)
app.include_router(tools_status.router)

# System Settings router (v4.7 - Dynamic configuration management)
app.include_router(
    system_settings.router,
    tags=["System Settings"]
)

# Attack Graph router (con autenticación)
app.include_router(
    graph.router,
    tags=["Attack Graph"],
    dependencies=[Depends(verify_api_key)]
)

# Evidence router (sin autenticación para dashboard)
app.include_router(
    evidence.router,
    prefix="/api",
    tags=["Evidence"]
)

# Workflow router (sin autenticación para dashboard)
app.include_router(
    workflow.router,
    prefix="/api",
    tags=["Case Workflow"]
)

# Red Team / HexStrike router
app.include_router(
    redteam.router,
    tags=["Red Team"]
)

# Cost Management router (v4.6 - Stripe integration)
app.include_router(
    costs.router,
    tags=["Cost Management"]
)

# Contact Form router (v4.6.1 - Public contact form)
app.include_router(
    contact.router,
    prefix="/api",
    tags=["Contact"]
)

# ============================================================================
# v4.6 ROLE MANAGEMENT ROUTERS
# ============================================================================

# Importar routers de roles
from api.routes import global_admin, admin_roles

# Global Admin router - Solo para Pluton_JE y usuarios is_global_admin=True
app.include_router(
    global_admin.router,
    tags=["Global Admin"]
)

# Admin Roles router - Gestión de roles por tenant
app.include_router(
    admin_roles.router,
    tags=["Role Management"]
)

# ============================================================================
# v4.7 GLOBAL ADMIN CRUD ROUTERS (PostgreSQL)
# ============================================================================

# Import new CRUD routers
from api.routes import global_admin_crud, security_tools_crud, pricing

# Global Admin CRUD router - Full CRUD for users, tenants, subscriptions
app.include_router(
    global_admin_crud.router,
    tags=["Global Admin CRUD"]
)

# Security Tools CRUD router - Quick actions, catalog, session
app.include_router(
    security_tools_crud.router,
    tags=["Security Tools API"]
)

# Pricing Admin router - Manage bundles, addons, pricing config
app.include_router(
    pricing.router,
    tags=["Pricing Admin"]
)

# Pricing Public router - lectura sin autenticación
app.include_router(
    pricing.public_router,
    tags=["Pricing Public"]
)

# ============================================================================
# v4.6 REGISTRATION & SUBSCRIPTION ROUTERS
# ============================================================================

# Import registration routes
from api.routes import registration
from api.routes import stripe_webhook

# Public Registration router (no auth required)
app.include_router(
    registration.router,
    prefix="/api",
    tags=["Registration"]
)

# Stripe Webhook router (no auth required - uses signature verification)
app.include_router(
    stripe_webhook.router,
    prefix="/api",
    tags=["Billing Webhooks"]
)

# ============================================================================

# Forensic Tools router (con autenticación)
app.include_router(
    forensics_tools.router,
    dependencies=[Depends(verify_api_key)]
)

# Graph Editor router (con autenticación)
app.include_router(
    graph_editor.router,
    dependencies=[Depends(verify_api_key)]
)

# Account Analysis router (con autenticación)
app.include_router(
    account_analysis_routes.router,
    dependencies=[Depends(verify_api_key)]
)

# OAuth router (sin autenticación - usa device code flow)
app.include_router(
    oauth.router,
    tags=["OAuth"]
)

# ============================================================================
# NEW ROUTERS - Frontend Integration
# ============================================================================

# Mobile Agents router (sin autenticación para dashboard)
app.include_router(
    agents.router,
    tags=["Mobile Agents"]
)

# LLM Agents router (con autenticación)
app.include_router(
    llm_agents.router,
    tags=["LLM Agents"],
    dependencies=[Depends(verify_api_key)]
)

# Investigations router (sin autenticación para dashboard)
app.include_router(
    investigations.router,
    tags=["Investigations"]
)

# Active Investigation router (sin autenticación para dashboard)
app.include_router(
    active_investigation.router,
    tags=["Active Investigation"]
)

# IOC Store router (sin autenticación para dashboard)
app.include_router(
    ioc_store.router,
    tags=["IOC Store"]
)

# Kali Tools router (sin autenticación para dashboard)
app.include_router(
    kali_tools.router,
    tags=["Kali Tools"]
)

# Monkey365 - M365 Cloud Security Assessment
app.include_router(
    monkey365.router,
    prefix="/api",
    tags=["M365 Cloud Security"]
)

# MISP - Malware Information Sharing Platform
app.include_router(
    misp.router,
    prefix="/api",
    tags=["MISP Threat Intelligence"]
)

# Threat Intelligence router (APIs externas: Shodan, VirusTotal, HIBP, etc.)
app.include_router(
    threat_intel.router,
    tags=["Threat Intelligence"]
)

# ============================================================================
# MinIO STORAGE ROUTER - Multi-tenant Evidence Management
# ============================================================================
app.include_router(
    storage.router,
    prefix="/api",
    tags=["Evidence Storage (MinIO)"]
)

# Missing Endpoints router (endpoints que faltan para integración frontend)
app.include_router(
    missing_endpoints.router,
    tags=["Missing Endpoints"]
)

# WebSocket router para actualizaciones en tiempo real
app.include_router(
    realtime.router,
    tags=["WebSocket Realtime"]
)

# ============================================================================
# v4.4.1 - WEBSOCKET STREAMING (Analysis Logs, Case Live, Global Logs)
# ============================================================================

# WebSocket Streaming router para logs de análisis en tiempo real
app.include_router(
    ws_streaming.router,
    tags=["v4.4.1 WebSocket Streaming"]
)

# ============================================================================
# v4.3 - LLM STUDIO INTEGRATION & DYNAMIC MODEL MANAGER
# ============================================================================

# LLM Settings router (con autenticación)
app.include_router(
    llm_settings.router,
    tags=["v4.3 LLM Studio"],
    dependencies=[Depends(verify_api_key)]
)

# ============================================================================
# v4.3 - THREAT HUNTING, TIMELINE & REPORTS
# ============================================================================

# Threat Hunting router (con autenticación)
app.include_router(
    hunting.router,
    prefix="/hunting",
    tags=["v4.3 Threat Hunting"],
    dependencies=[Depends(verify_api_key)]
)

# Timeline router (con autenticación)
app.include_router(
    timeline.router,
    prefix="/timeline",
    tags=["v4.3 Timeline"],
    dependencies=[Depends(verify_api_key)]
)

# Web Reconnaissance for Threat Hunting (con integración de web-check-api)
app.include_router(
    hunting_web_recon.router,
    tags=["v4.3 Threat Hunting - OSINT"]
)

# Reports router (con autenticación)
app.include_router(
    reports.router,
    prefix="/reports",
    tags=["v4.3 Reports"],
    dependencies=[Depends(verify_api_key)]
)

# Module Registry router (sin autenticación para desarrollo)
app.include_router(
    modules.router,
    tags=["v4.3 Module Registry"]
)

# ============================================================================
# v4.1 - TOOL EXECUTION, AGENTS, SOAR & CORRELATION
# ============================================================================

if v41_enabled:
    # v4.1 - Tool Execution router (con autenticación)
    app.include_router(
        tools_v41.router,
        tags=["v4.1 Tool Execution"],
        dependencies=[Depends(verify_api_key)]
    )

    # v4.1 - SOAR Playbooks router (con autenticación)
    app.include_router(
        playbooks.router,
        tags=["v4.1 SOAR Playbooks"],
        dependencies=[Depends(verify_api_key)]
    )

    # v4.1 - Correlation Engine router (con autenticación)
    app.include_router(
        correlation.router,
        tags=["v4.1 Correlation Engine"],
        dependencies=[Depends(verify_api_key)]
    )

# Security Checklist router (sin autenticación, público)
app.include_router(
    security_checklist.router,
    tags=["Security Checklist"]
)

# v4.1 - Attack Graph Enhanced router (con autenticación)
app.include_router(
    graph_v41.router,
    tags=["v4.1 Attack Graph"],
    dependencies=[Depends(verify_api_key)]
)

# ============================================================================
# v4.1 - REAL DATA ROUTES (NO MOCKS)
# ============================================================================

if v41_real_data_enabled:
    # v4.1 - Agents with real database data
    app.include_router(
        agents_v41.router,
        tags=["v4.1 Agents (Real Data)"]
    )
    
    # v4.1 - Investigations with real database data
    app.include_router(
        investigations_v41.router,
        tags=["v4.1 Investigations (Real Data)"]
    )
    
    logger.info("✅ Rutas v4.1 con datos reales habilitadas: /api/v41/agents, /api/v41/investigations")

# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    logger.error(f"HTTP Error: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.DEBUG else "An error occurred",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8080,
        reload=settings.DEBUG,
        log_level="info"
    )
