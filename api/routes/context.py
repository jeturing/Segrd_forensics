# api/routes/context.py

"""
Context Management API
======================
Endpoints para gestión de contexto de casos activos.

Endpoints:
- POST /api/context/set   - Establecer caso activo
- GET  /api/context       - Obtener contexto actual
- DELETE /api/context     - Cerrar contexto
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Dict, Optional
from pydantic import BaseModel, Field
import logging

from core.context_manager import get_case_context, CaseContextManager
from api.middleware.auth import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/context", tags=["Context Management"])


# ==================== MODELOS PYDANTIC ====================

class SetContextRequest(BaseModel):
    """Request para establecer contexto activo"""
    case_id: str = Field(..., description="ID del caso a establecer como activo")
    session_id: Optional[str] = Field(None, description="ID de sesión (se genera si no se proporciona)")
    metadata: Optional[Dict] = Field(None, description="Metadatos del caso")


# ==================== ENDPOINTS ====================

@router.post("/set")
async def set_active_context(
    request: SetContextRequest,
    context_manager: CaseContextManager = Depends(get_case_context),
    api_key: str = Depends(verify_api_key)
):
    """
    Establece un caso como contexto activo para la sesión actual.
    
    Args:
        case_id: ID del caso a activar
        session_id: ID de sesión (opcional, se genera automáticamente)
        metadata: Metadatos adicionales del caso
    
    Returns:
        Información del contexto creado/actualizado
    """
    try:
        # Crear o actualizar contexto
        if request.session_id:
            ctx = context_manager.get_or_create_context(
                request.session_id,
                request.case_id,
                request.metadata
            )
        else:
            ctx = context_manager.create_context(
                request.case_id,
                request.metadata
            )
        
        logger.info(f"✅ Context set: case={request.case_id}, session={ctx.session_id}")
        
        return {
            "success": True,
            "message": f"Case {request.case_id} set as active context",
            "context": ctx.to_dict()
        }
    
    except Exception as e:
        logger.error(f"❌ Error setting context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def get_current_context(
    session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    context_manager: CaseContextManager = Depends(get_case_context),
    api_key: str = Depends(verify_api_key)
):
    """
    Obtiene el contexto activo de la sesión actual.
    
    Args:
        session_id: ID de sesión (via header X-Session-ID)
    
    Returns:
        Información del contexto actual o null si no hay contexto activo
    """
    try:
        if not session_id:
            return {
                "success": True,
                "context": None,
                "message": "No session ID provided"
            }
        
        ctx = context_manager.get_context(session_id)
        
        if not ctx:
            return {
                "success": True,
                "context": None,
                "message": f"No active context for session {session_id}"
            }
        
        return {
            "success": True,
            "context": ctx.to_dict()
        }
    
    except Exception as e:
        logger.error(f"❌ Error getting context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("")
async def close_context(
    session_id: str = Header(..., alias="X-Session-ID"),
    context_manager: CaseContextManager = Depends(get_case_context),
    api_key: str = Depends(verify_api_key)
):
    """
    Cierra el contexto activo de una sesión.
    
    Args:
        session_id: ID de sesión a cerrar (via header X-Session-ID)
    
    Returns:
        Confirmación de cierre
    """
    try:
        context_manager.close_context(session_id)
        
        logger.info(f"🔴 Context closed: session={session_id}")
        
        return {
            "success": True,
            "message": f"Context for session {session_id} closed"
        }
    
    except Exception as e:
        logger.error(f"❌ Error closing context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active")
async def get_active_contexts(
    context_manager: CaseContextManager = Depends(get_case_context),
    api_key: str = Depends(verify_api_key)
):
    """
    Lista todos los contextos activos en el sistema.
    
    Returns:
        Lista de casos con contextos activos
    """
    try:
        active_cases = context_manager.get_all_active_cases()
        
        return {
            "success": True,
            "active_cases": len(active_cases),
            "cases": active_cases
        }
    
    except Exception as e:
        logger.error(f"❌ Error getting active contexts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup")
async def cleanup_expired_contexts(
    context_manager: CaseContextManager = Depends(get_case_context),
    api_key: str = Depends(verify_api_key)
):
    """
    Fuerza limpieza de contextos expirados.
    
    Returns:
        Confirmación de limpieza
    """
    try:
        context_manager.cleanup_expired()
        
        logger.info("🧹 Forced cleanup of expired contexts")
        
        return {
            "success": True,
            "message": "Expired contexts cleaned up"
        }
    
    except Exception as e:
        logger.error(f"❌ Error cleaning up contexts: {e}")
        raise HTTPException(status_code=500, detail=str(e))
