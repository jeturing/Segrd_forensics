# api/routes/llm_settings.py

"""
LLM Settings API - Model Agnostic
=================================
Gestión de proveedores LLM, detección automática de modelos,
y análisis forense enriquecido.

Endpoints:
- GET  /api/v41/llm/status        - Estado general del sistema
- GET  /api/v41/llm/health        - Health check de proveedores
- GET  /api/v41/llm/models        - Lista modelos disponibles (auto-detecta)
- POST /api/v41/llm/models/active - Establece modelo activo
- POST /api/v41/llm/generate      - Genera texto con modelo activo
- POST /api/v41/llm/analyze       - Analiza hallazgos forenses
- POST /api/v41/llm/test          - Prueba de conectividad
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Dict, Optional, Any
from pydantic import BaseModel, Field
import logging
from datetime import datetime

from api.services.llm_provider import get_llm_manager, LLMProviderManager, ProviderType
from api.services.case_context_builder import CaseContextBuilder
from api.middleware.auth import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v41/llm", tags=["LLM Settings"])


# ==================== MODELOS PYDANTIC ====================

class SetActiveModelRequest(BaseModel):
    """Request para establecer modelo activo"""
    model_id: str = Field(..., description="ID del modelo a activar")


class GenerateRequest(BaseModel):
    """Request para generación de texto"""
    prompt: str = Field(..., description="Prompt del usuario")
    system_prompt: Optional[str] = Field(None, description="Prompt de sistema")
    max_tokens: int = Field(2000, description="Máximo de tokens a generar")
    temperature: float = Field(0.7, ge=0, le=2, description="Temperatura de muestreo")
    model_id: Optional[str] = Field(None, description="Modelo específico (usa activo si None)")
    use_chat: bool = Field(True, description="Usar chat/completions vs completions")


class AnalyzeRequest(BaseModel):
    """Request para análisis forense"""
    findings: Dict[str, Any] = Field(..., description="Hallazgos a analizar")
    context: str = Field("m365", description="Contexto: m365, endpoint, credentials")
    severity_threshold: str = Field("medium", description="Umbral de severidad")
    case_id: Optional[str] = Field(None, description="ID del caso para contexto enriquecido")


class TestRequest(BaseModel):
    """Request para test de LLM"""
    prompt: str = Field("¿Cuál es tu modelo?", description="Prompt de prueba")
    provider: Optional[str] = Field(None, description="Proveedor específico a probar")


class ProviderConfigRequest(BaseModel):
    """Request para configurar un proveedor"""
    provider_type: str = Field(..., description="Tipo: lm_studio, ollama, openai")
    base_url: Optional[str] = Field(None, description="URL base del proveedor")
    api_key: Optional[str] = Field(None, description="API key (si aplica)")
    enabled: bool = Field(True, description="Habilitar/deshabilitar")


# ==================== HELPERS ====================

def get_manager() -> LLMProviderManager:
    """Obtiene instancia del LLM Manager"""
    return get_llm_manager()


# ==================== ENDPOINTS ====================

@router.get("/")
async def llm_info():
    """Información general del sistema LLM"""
    return {
        "version": "4.5.0",
        "engine": "LLM Provider Manager - Model Agnostic",
        "supported_providers": [p.value for p in ProviderType],
        "features": [
            "Auto-detección de modelos",
            "Soporte multi-proveedor",
            "Fallback automático",
            "Análisis forense integrado",
            "Chat y completions compatibles"
        ],
        "endpoints": {
            "status": "GET /api/v41/llm/status",
            "health": "GET /api/v41/llm/health",
            "models": "GET /api/v41/llm/models",
            "set_active": "POST /api/v41/llm/models/active",
            "generate": "POST /api/v41/llm/generate",
            "analyze": "POST /api/v41/llm/analyze",
            "test": "POST /api/v41/llm/test"
        }
    }


@router.get("/status")
async def get_status(api_key: str = Depends(verify_api_key)):
    """
    Obtiene estado completo del sistema LLM
    
    Returns:
        - Proveedores configurados con estado
        - Modelo activo
        - Modelos en cache
        - Estadísticas
    """
    try:
        manager = get_manager()
        health = await manager.health_check()
        active_model = await manager.get_active_model()
        
        return {
            "success": True,
            "data": {
                "healthy": health.get("healthy", False),
                "providers": health.get("providers", {}),
                "active_model": active_model.to_dict() if active_model else None,
                "cached_models": len(manager.models_cache),
                "cache_age_seconds": (
                    (datetime.now() - manager.last_cache_update).total_seconds()
                    if manager.last_cache_update else None
                )
            }
        }
    except Exception as e:
        logger.error(f"❌ Error getting LLM status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check(api_key: str = Depends(verify_api_key)):
    """
    Verifica conectividad de todos los proveedores
    
    Returns:
        Estado de salud por proveedor
    """
    try:
        manager = get_manager()
        health = await manager.health_check()
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            **health
        }
    except Exception as e:
        logger.error(f"❌ Error in health check: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
async def list_models(
    refresh: bool = False,
    api_key: str = Depends(verify_api_key)
):
    """
    Lista modelos disponibles de todos los proveedores
    
    Args:
        refresh: Forzar refresco del cache
        
    Returns:
        Lista de modelos con información detallada
    """
    try:
        manager = get_manager()
        models = await manager.get_available_models(force_refresh=refresh)
        active_model = await manager.get_active_model()
        
        return {
            "success": True,
            "total": len(models),
            "active_model_id": active_model.id if active_model else None,
            "models": [m.to_dict() for m in models],
            "by_provider": {
                provider.value: [
                    m.to_dict() for m in models if m.provider == provider
                ]
                for provider in ProviderType
                if any(m.provider == provider for m in models)
            }
        }
    except Exception as e:
        logger.error(f"❌ Error listing models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/active")
async def get_active_model(api_key: str = Depends(verify_api_key)):
    """
    Obtiene el modelo activo actual
    """
    try:
        manager = get_manager()
        model = await manager.get_active_model()
        
        if model:
            return {
                "success": True,
                "model": model.to_dict()
            }
        else:
            return {
                "success": False,
                "message": "No hay modelo activo. Carga un modelo en LM Studio o Ollama.",
                "model": None
            }
    except Exception as e:
        logger.error(f"❌ Error getting active model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/models/active")
async def set_active_model(
    request: SetActiveModelRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Establece el modelo activo por ID
    
    El modelo debe existir en algún proveedor conectado
    """
    try:
        manager = get_manager()
        success = await manager.set_active_model(request.model_id)
        
        if success:
            model = await manager.get_active_model()
            logger.info(f"🎯 Modelo activo cambiado a: {request.model_id}")
            return {
                "success": True,
                "message": f"Modelo activo establecido: {request.model_id}",
                "model": model.to_dict() if model else None
            }
        else:
            available = await manager.get_available_models()
            raise HTTPException(
                status_code=404,
                detail={
                    "message": f"Modelo no encontrado: {request.model_id}",
                    "available_models": [m.id for m in available]
                }
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error setting active model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/models/load/{model_id}")
async def load_model(
    model_id: str,
    provider: Optional[str] = None,
    api_key: str = Depends(verify_api_key)
):
    """
    Intenta cargar un modelo en el proveedor
    
    Nota: LM Studio no soporta carga remota.
    Ollama puede descargar y cargar modelos.
    """
    try:
        manager = get_manager()
        provider_type = None
        if provider:
            try:
                provider_type = ProviderType(provider)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Proveedor inválido: {provider}. Opciones: {[p.value for p in ProviderType]}"
                )
        
        success, message = await manager.load_model(model_id, provider_type)
        
        return {
            "success": success,
            "message": message,
            "model_id": model_id,
            "provider": provider
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error loading model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate")
async def generate_text(
    request: GenerateRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Genera texto con el modelo activo
    
    Soporta tanto chat/completions como completions según el parámetro use_chat
    """
    try:
        manager = get_manager()
        
        result = await manager.generate(
            prompt=request.prompt,
            system_prompt=request.system_prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            model_id=request.model_id,
            use_chat=request.use_chat
        )
        
        return {
            "success": result.get("success", False),
            "content": result.get("content", ""),
            "model": result.get("model"),
            "provider": result.get("provider"),
            "usage": result.get("usage"),
            "warning": result.get("warning")
        }
    except Exception as e:
        logger.error(f"❌ Error generating text: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze")
async def analyze_findings(
    request: AnalyzeRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Analiza hallazgos forenses con LLM
    
    Contextos disponibles:
    - m365: Microsoft 365 / Azure AD
    - endpoint: Análisis de malware / endpoint
    - credentials: Breaches y credenciales
    """
    valid_contexts = ["m365", "endpoint", "credentials", "general"]
    if request.context not in valid_contexts:
        raise HTTPException(
            status_code=400,
            detail=f"Contexto inválido. Opciones: {valid_contexts}"
        )
    
    try:
        manager = get_manager()
        
        # Construir contexto enriquecido si hay case_id
        full_context = None
        if request.case_id:
            try:
                context_builder = CaseContextBuilder()
                full_context = await context_builder.build_context(request.case_id)
            except Exception as e:
                # Log error pero continuar con análisis básico
                print(f"⚠️ Error building case context: {e}")
        
        result = await manager.analyze_forensic_findings(
            findings=request.findings,
            context=request.context,
            severity_threshold=request.severity_threshold,
            full_context=full_context
        )
        
        return {
            "success": result.get("success", False),
            "analysis": result.get("content", ""),
            "model_used": result.get("model"),
            "provider": result.get("provider"),
            "context": result.get("context"),
            "is_offline": result.get("provider") == "offline"
        }
    except Exception as e:
        logger.error(f"❌ Error analyzing findings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test")
async def test_llm(
    request: TestRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Prueba la conectividad y generación del LLM
    
    Útil para verificar que el modelo está respondiendo correctamente
    """
    try:
        manager = get_manager()
        
        # Primero verificar salud
        health = await manager.health_check()
        
        # Luego intentar generar
        start_time = datetime.now()
        result = await manager.generate(
            prompt=request.prompt,
            max_tokens=100,
            temperature=0.5
        )
        elapsed = (datetime.now() - start_time).total_seconds()
        
        return {
            "success": result.get("success", False),
            "test_prompt": request.prompt,
            "response": result.get("content", "")[:500],  # Limitar respuesta
            "model_used": result.get("model"),
            "provider": result.get("provider"),
            "response_time_seconds": round(elapsed, 2),
            "health": health.get("providers", {}),
            "is_offline": result.get("provider") == "offline"
        }
    except Exception as e:
        logger.error(f"❌ Error testing LLM: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refresh")
async def refresh_models(api_key: str = Depends(verify_api_key)):
    """
    Fuerza refresco del cache de modelos
    
    Útil después de cargar un nuevo modelo en LM Studio u Ollama
    """
    try:
        manager = get_manager()
        models = await manager.get_available_models(force_refresh=True)
        active = await manager.get_active_model()
        
        return {
            "success": True,
            "message": "Cache de modelos actualizado",
            "total_models": len(models),
            "active_model": active.id if active else None,
            "models": [m.id for m in models]
        }
    except Exception as e:
        logger.error(f"❌ Error refreshing models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_statistics(api_key: str = Depends(verify_api_key)):
    """
    Obtiene estadísticas de uso del sistema LLM
    
    Returns:
        Métricas de uso por proveedor, tokens procesados, latencias
    """
    try:
        manager = get_manager()
        
        # Obtener métricas de uso
        stats = {
            "total_requests": 0,
            "total_tokens": 0,
            "providers": {},
            "cache_info": {
                "models_cached": len(manager.models_cache),
                "cache_age_seconds": (
                    (datetime.now() - manager.last_cache_update).total_seconds()
                    if manager.last_cache_update else None
                )
            }
        }
        
        # Estadísticas por proveedor
        for provider_type, config in manager.providers.items():
            stats["providers"][provider_type.value] = {
                "enabled": config.enabled,
                "priority": config.priority,
                "available": config.enabled
            }
        
        return {
            "success": True,
            "statistics": stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"❌ Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/providers")
async def list_providers(api_key: str = Depends(verify_api_key)):
    """
    Lista proveedores configurados y su estado
    """
    try:
        manager = get_manager()
        
        providers_info = []
        for provider_type, config in manager.providers.items():
            providers_info.append({
                "type": provider_type.value,
                "base_url": config.base_url if config.base_url else None,
                "enabled": config.enabled,
                "priority": config.priority,
                "has_api_key": bool(config.api_key) if provider_type == ProviderType.OPENAI else None,
                "timeout": config.timeout
            })
        
        return {
            "success": True,
            "providers": sorted(providers_info, key=lambda x: x["priority"])
        }
    except Exception as e:
        logger.error(f"❌ Error listing providers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/providers/{provider_type}")
async def configure_provider(
    provider_type: str,
    request: ProviderConfigRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Actualiza configuración de un proveedor
    """
    try:
        # Validar tipo de proveedor
        try:
            ptype = ProviderType(provider_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Proveedor inválido: {provider_type}"
            )
        
        manager = get_manager()
        
        if ptype not in manager.providers:
            raise HTTPException(status_code=404, detail="Proveedor no encontrado")
        
        config = manager.providers[ptype]
        
        # Actualizar configuración
        if request.base_url is not None:
            config.base_url = request.base_url
        if request.api_key is not None:
            config.api_key = request.api_key
        if request.enabled is not None:
            config.enabled = request.enabled
        
        logger.info(f"⚙️ Proveedor {provider_type} configurado: enabled={config.enabled}")
        
        return {
            "success": True,
            "message": f"Proveedor {provider_type} actualizado",
            "config": {
                "type": ptype.value,
                "base_url": config.base_url,
                "enabled": config.enabled,
                "priority": config.priority
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error configuring provider: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class SetProviderRequest(BaseModel):
    """Request para cambiar proveedor activo"""
    provider: str = Field(..., description="Tipo de proveedor: lm_studio, ollama, openai")
    reason: Optional[str] = Field(None, description="Razón del cambio")


@router.post("/provider")
async def set_active_provider(
    request: SetProviderRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Cambia el proveedor LLM activo
    
    El frontend usa este endpoint para cambiar entre proveedores:
    - lm_studio
    - ollama  
    - openai
    """
    try:
        # Validar tipo de proveedor
        try:
            ptype = ProviderType(request.provider)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Proveedor inválido: {request.provider}. Opciones: {[p.value for p in ProviderType]}"
            )
        
        manager = get_manager()
        
        if ptype not in manager.providers:
            raise HTTPException(status_code=404, detail="Proveedor no configurado")
        
        # Verificar que el proveedor está habilitado
        config = manager.providers[ptype]
        if not config.enabled:
            raise HTTPException(
                status_code=400,
                detail=f"Proveedor {request.provider} está deshabilitado"
            )
        
        # Actualizar proveedor activo
        manager.active_provider = ptype
        
        logger.info(f"🔄 Proveedor activo cambiado a: {request.provider} (razón: {request.reason or 'manual'})")
        
        return {
            "success": True,
            "message": f"Proveedor cambiado a {request.provider}",
            "active_provider": ptype.value,
            "reason": request.reason
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error setting active provider: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ANÁLISIS FORENSE AVANZADO v4.5 ====================

class ForensicAnalysisRequest(BaseModel):
    """Request para análisis forense avanzado con LLM"""
    case_id: str = Field(..., description="ID del caso a analizar")
    analysis_type: str = Field(
        "standard",
        description="Tipo: quick, standard, deep, executive"
    )
    custom_prompt: Optional[str] = Field(
        None, 
        description="Prompt adicional del analista"
    )


@router.post("/analyze/forensic")
async def analyze_forensic_case(
    request: ForensicAnalysisRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key)
):
    """
    Análisis forense avanzado con detección MITRE ATT&CK
    
    Tipos de análisis:
    - quick: Clasificación rápida de severidad (30s)
    - standard: Análisis con recomendaciones (1-2min)
    - deep: Análisis completo MITRE + reporte (3-5min)
    - executive: Resumen ejecutivo para management
    
    Returns:
        - Mapeo MITRE ATT&CK
        - Cadena de ataque reconstruida  
        - Recomendaciones SOAR
        - Score de riesgo
    """
    from api.services.llm_forensic_analyzer import (
        llm_forensic_analyzer, 
        AnalysisType
    )
    
    # Validar tipo de análisis
    valid_types = ["quick", "standard", "deep", "executive"]
    if request.analysis_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo inválido. Opciones: {valid_types}"
        )
    
    try:
        analysis_type = AnalysisType(request.analysis_type)
        
        logger.info(f"🔬 Iniciando análisis forense: {request.case_id} ({request.analysis_type})")
        
        result = await llm_forensic_analyzer.analyze_case(
            case_id=request.case_id,
            analysis_type=analysis_type,
            custom_prompt=request.custom_prompt
        )
        
        return {
            "success": True,
            "analysis": llm_forensic_analyzer.to_dict(result)
        }
        
    except Exception as e:
        logger.error(f"❌ Error en análisis forense: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analyze/forensic/{case_id}/quick")
async def quick_forensic_analysis(
    case_id: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Análisis rápido de caso - clasificación de severidad
    
    Retorna en <30 segundos:
    - Nivel de riesgo (critical/high/medium/low)
    - Top 3 preocupaciones
    - Si requiere acción inmediata
    """
    from api.services.llm_forensic_analyzer import (
        llm_forensic_analyzer,
        AnalysisType
    )
    
    try:
        result = await llm_forensic_analyzer.analyze_case(
            case_id=case_id,
            analysis_type=AnalysisType.QUICK
        )
        
        return {
            "success": True,
            "case_id": case_id,
            "risk_level": result.overall_risk,
            "risk_score": result.risk_score,
            "executive_summary": result.executive_summary,
            "confidence": result.confidence_score
        }
        
    except Exception as e:
        logger.error(f"❌ Error en análisis rápido: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analyze/forensic/{case_id}/mitre")
async def get_mitre_mapping(
    case_id: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Obtener mapeo MITRE ATT&CK para un caso
    
    Retorna:
    - Técnicas detectadas con confianza
    - Cobertura de tácticas
    - Kill chain stage
    """
    from api.services.llm_forensic_analyzer import (
        llm_forensic_analyzer,
        AnalysisType
    )
    
    try:
        result = await llm_forensic_analyzer.analyze_case(
            case_id=case_id,
            analysis_type=AnalysisType.STANDARD
        )
        
        return {
            "success": True,
            "case_id": case_id,
            "techniques": [
                {
                    "id": t.technique_id,
                    "name": t.technique_name,
                    "tactic": t.tactic,
                    "confidence": t.confidence,
                    "evidence": t.evidence
                }
                for t in result.techniques_detected
            ],
            "tactics_coverage": result.tactics_coverage,
            "total_techniques": len(result.techniques_detected)
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo mapeo MITRE: {e}")
        raise HTTPException(status_code=500, detail=str(e))
