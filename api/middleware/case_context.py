"""
MCP Kali Forensics v4.4 - Case Context Middleware
==================================================
Middleware que asegura que todas las operaciones forenses
estén asociadas a un case_id.

Author: MCP Forensics Team
Version: 4.4.0
"""

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import json

logger = logging.getLogger(__name__)

# Rutas que REQUIEREN case_id obligatorio
CASE_REQUIRED_PATHS = [
    "/hunting/execute",
    "/hunting/batch",
    "/hunting/save-custom",
    "/timeline/events",
    "/timeline/correlate",
    "/timeline/import",
    "/timeline/export",
    "/reports/generate",
    "/reports/generate-llm",
    "/agents/tasks",
    "/agents/execute",
    "/investigation/commands",
    "/investigation/execute",
    "/endpoint/scan",
    "/endpoint/analyze",
    # v1 API routes
    "/api/v1/m365/analyze",
    "/api/v1/endpoint/scan",
    "/api/v1/endpoint/analyze",
]

# Rutas excluidas (no requieren case_id)
CASE_EXEMPT_PATHS = [
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/static",
    "/api/status",
    "/cases",  # La creación de casos no requiere case_id previo
    "/api/v1/cases",  # v1 API - creación de casos
    "/hunting/queries",  # Listar queries disponibles
    "/hunting/categories",
    "/hunting/stats",  # Stats globales
    "/tenants",  # Gestión de tenants es independiente
    "/llm",  # Configuración LLM
    "/modules",  # Registry de módulos
    "/iocs",  # IOC store puede ser global
    "/api/remote-agents",  # v4.5 - Remote agents (uses token auth)
]

# Prefijos que siempre requieren case_id
CASE_REQUIRED_PREFIXES = [
    "/investigation/",
    "/forensics/endpoint/",
    "/forensics/m365/analyze",
]


def path_requires_case_id(path: str, method: str) -> bool:
    """
    Determinar si una ruta requiere case_id.
    
    Reglas:
    1. Rutas en CASE_EXEMPT_PATHS nunca requieren
    2. Rutas en CASE_REQUIRED_PATHS siempre requieren
    3. Prefijos en CASE_REQUIRED_PREFIXES requieren
    4. POST/PUT/DELETE a rutas de datos generalmente requieren
    """
    # Normalizar path
    path = path.rstrip("/").lower()
    
    # Verificar exempciones
    for exempt in CASE_EXEMPT_PATHS:
        if path.startswith(exempt.lower()):
            return False
    
    # Verificar rutas explícitamente requeridas
    for required in CASE_REQUIRED_PATHS:
        if path.startswith(required.lower()):
            return True
    
    # Verificar prefijos requeridos
    for prefix in CASE_REQUIRED_PREFIXES:
        if path.startswith(prefix.lower()):
            return True
    
    return False


class CaseContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware que intercepta requests y valida/inyecta case_id.
    
    Extrae case_id de:
    1. Header X-Case-ID
    2. Query parameter case_id
    3. Body JSON (para POST/PUT)
    
    Inyecta case_id en request.state para uso posterior.
    """
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method
        
        # Verificar si la ruta requiere case_id
        if path_requires_case_id(path, method):
            case_id = await self._extract_case_id(request)
            
            if not case_id:
                logger.warning(f"⚠️ Missing case_id for {method} {path}")
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "case_id_required",
                        "message": "This operation requires a case_id. "
                                   "Provide it via X-Case-ID header, case_id query parameter, "
                                   "or in the request body.",
                        "path": path,
                        "method": method
                    }
                )
            
            # Inyectar case_id en request state
            request.state.case_id = case_id
            logger.debug(f"🔵 Case context set: {case_id} for {method} {path}")
        
        response = await call_next(request)
        return response
    
    async def _extract_case_id(self, request: Request) -> str | None:
        """Extraer case_id de la request"""
        
        # 1. Intentar header
        case_id = request.headers.get("X-Case-ID")
        if case_id:
            return case_id
        
        # 2. Intentar query params
        case_id = request.query_params.get("case_id")
        if case_id:
            return case_id
        
        # 3. Intentar body (solo para POST/PUT/PATCH)
        if request.method in ("POST", "PUT", "PATCH"):
            try:
                # Leer y cachear el body
                body = await request.body()
                if body:
                    try:
                        data = json.loads(body)
                        case_id = data.get("case_id")
                        if case_id:
                            return case_id
                    except json.JSONDecodeError:
                        pass
            except Exception:
                pass
        
        return None


class ProcessTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware para tracking de procesos de larga duración.
    
    Registra inicio/fin de operaciones largas y permite
    consultar el estado de procesos en curso.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Por ahora, simple pass-through
        # Se extenderá para tracking de background tasks
        response = await call_next(request)
        return response


def get_case_id_from_request(request: Request) -> str | None:
    """
    Utility function para obtener case_id de una request.
    Usar cuando el middleware ya ha procesado la request.
    """
    return getattr(request.state, 'case_id', None)


def require_case_id(request: Request) -> str:
    """
    Obtener case_id o lanzar HTTPException.
    Usar como dependency en endpoints que requieren case.
    """
    case_id = get_case_id_from_request(request)
    if not case_id:
        raise HTTPException(
            status_code=400,
            detail="case_id is required for this operation"
        )
    return case_id
