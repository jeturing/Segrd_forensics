"""
Router para análisis forense de cuentas de usuario
Integra todas las herramientas para perfil completo
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
import logging

from api.services.account_analysis import (
    analyze_user_account,
    analyze_multiple_accounts
)
from api.services.cases import create_case, update_case_status

router = APIRouter(prefix="/forensics/accounts", tags=["Account Analysis"])
logger = logging.getLogger(__name__)


class AccountAnalysisRequest(BaseModel):
    """Request para análisis de cuenta"""
    user_email: str = Field(..., description="Email del usuario a analizar")
    case_id: Optional[str] = Field(None, description="ID del caso (se crea si no existe)")
    tenant_id: str = Field(..., description="Azure AD Tenant ID")
    days_back: int = Field(default=90, ge=1, le=365, description="Días históricos a analizar")
    include_osint: bool = Field(default=True, description="Incluir búsqueda OSINT con Sherlock")
    priority: str = Field(default="medium", description="Prioridad del análisis")


class MultipleAccountsRequest(BaseModel):
    """Request para análisis de múltiples cuentas"""
    user_emails: List[str] = Field(..., description="Lista de emails a analizar")
    case_id: Optional[str] = Field(None, description="ID del caso")
    tenant_id: str = Field(..., description="Azure AD Tenant ID")
    days_back: int = Field(default=90, ge=1, le=365)
    include_osint: bool = Field(default=True)
    priority: str = Field(default="medium")


class AccountAnalysisResponse(BaseModel):
    """Response del análisis"""
    status: str
    message: str
    case_id: str
    user_email: Optional[str] = None
    task_id: Optional[str] = None
    estimated_duration_minutes: int


@router.post("/analyze", response_model=AccountAnalysisResponse)
async def analyze_account(
    request: AccountAnalysisRequest,
    background_tasks: BackgroundTasks
):
    """
    Análisis forense completo de una cuenta de usuario
    
    ## Análisis incluye:
    
    ### Microsoft 365 (Graph API)
    - Sign-ins de riesgo (últimos 90 días)
    - Eventos de Identity Protection
    - Estado de MFA
    - Ubicaciones de acceso
    - Dispositivos utilizados
    
    ### Sparrow 365
    - Indicadores de compromiso en Azure AD
    - Tokens abusados
    - Actividad administrativa sospechosa
    
    ### Hawk M365
    - Reglas de buzón maliciosas
    - Delegaciones de buzón
    - Consentimientos OAuth
    - Reenvío de correos
    
    ### Sherlock (OSINT)
    - Perfiles en redes sociales
    - Presencia en plataformas de alto riesgo
    - Digital footprint
    
    ## Resultado:
    - **Risk Score** (0-100)
    - **Timeline** de eventos
    - **Recomendaciones** de seguridad
    - **Informe unificado** con todos los hallazgos
    
    ## Ejemplo:
    ```json
    {
        "user_email": "admin@empresa.com",
        "tenant_id": "xxx-tenant-id",
        "days_back": 90,
        "include_osint": true,
        "priority": "high"
    }
    ```
    """
    try:
        logger.info(f"📋 Iniciando análisis de cuenta: {request.user_email}")
        
        # Crear o usar caso existente
        case_id = request.case_id or f"ACC-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        
        if not request.case_id:
            await create_case({
                "case_id": case_id,
                "type": "account_analysis",
                "tenant_id": request.tenant_id,
                "priority": request.priority,
                "status": "queued",
                "title": f"Análisis de cuenta: {request.user_email}",
                "metadata": {
                    "user_email": request.user_email,
                    "days_back": request.days_back,
                    "include_osint": request.include_osint
                }
            })
        
        # Estimar duración
        estimated_duration = 15  # Sparrow
        estimated_duration += 20  # Hawk
        estimated_duration += 5   # M365 Graph API
        if request.include_osint:
            estimated_duration += 8  # Sherlock
        
        # Ejecutar en background
        background_tasks.add_task(
            execute_account_analysis,
            request.user_email,
            case_id,
            request.tenant_id,
            request.days_back,
            request.include_osint
        )
        
        logger.info(f"✅ Análisis de cuenta encolado: {request.user_email}")
        
        return AccountAnalysisResponse(
            status="queued",
            message=f"Análisis de cuenta iniciado para {request.user_email}",
            case_id=case_id,
            user_email=request.user_email,
            task_id=case_id,
            estimated_duration_minutes=estimated_duration
        )
        
    except Exception as e:
        logger.error(f"❌ Error al iniciar análisis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-multiple", response_model=AccountAnalysisResponse)
async def analyze_multiple_accounts_endpoint(
    request: MultipleAccountsRequest,
    background_tasks: BackgroundTasks
):
    """
    Análisis forense de múltiples cuentas en paralelo
    
    Ejecuta el análisis completo para cada cuenta (máximo 10 concurrentes)
    y genera un informe agregado con:
    - Cuentas de alto riesgo
    - Risk score promedio
    - Hallazgos críticos
    - Recomendaciones priorizadas
    """
    try:
        logger.info(f"📋 Iniciando análisis de {len(request.user_emails)} cuentas")
        
        # Validar límite
        if len(request.user_emails) > 50:
            raise HTTPException(
                status_code=400,
                detail="Máximo 50 cuentas por análisis"
            )
        
        # Crear caso
        case_id = request.case_id or f"ACC-BULK-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        
        if not request.case_id:
            await create_case({
                "case_id": case_id,
                "type": "bulk_account_analysis",
                "tenant_id": request.tenant_id,
                "priority": request.priority,
                "status": "queued",
                "title": f"Análisis masivo: {len(request.user_emails)} cuentas",
                "metadata": {
                    "user_emails": request.user_emails,
                    "days_back": request.days_back,
                    "include_osint": request.include_osint
                }
            })
        
        # Estimar duración (por cuenta)
        estimated_per_account = 48 if request.include_osint else 40
        estimated_duration = min(estimated_per_account * len(request.user_emails) // 3, 300)  # Max 5 horas
        
        # Ejecutar en background
        background_tasks.add_task(
            execute_multiple_accounts_analysis,
            request.user_emails,
            case_id,
            request.tenant_id,
            request.days_back,
            request.include_osint
        )
        
        logger.info(f"✅ Análisis masivo encolado: {len(request.user_emails)} cuentas")
        
        return AccountAnalysisResponse(
            status="queued",
            message=f"Análisis masivo iniciado para {len(request.user_emails)} cuentas",
            case_id=case_id,
            task_id=case_id,
            estimated_duration_minutes=estimated_duration
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def execute_account_analysis(
    user_email: str,
    case_id: str,
    tenant_id: str,
    days_back: int,
    include_osint: bool
):
    """Función background para análisis de cuenta"""
    try:
        await update_case_status(case_id, "running")
        logger.info(f"🔍 Ejecutando análisis de cuenta: {user_email}")
        
        # Ejecutar análisis completo
        result = await analyze_user_account(
            user_email=user_email,
            case_id=case_id,
            tenant_id=tenant_id,
            days_back=days_back,
            include_osint=include_osint
        )
        
        # Actualizar caso con resultados
        await update_case_status(
            case_id,
            "completed",
            results=result,
            summary=generate_account_summary(result)
        )
        
        logger.info(f"✅ Análisis completado: {user_email} - Risk Score: {result.get('risk_assessment', {}).get('risk_score', 0)}")
        
    except Exception as e:
        logger.error(f"❌ Error en análisis: {e}", exc_info=True)
        await update_case_status(case_id, "failed", error=str(e))


async def execute_multiple_accounts_analysis(
    user_emails: List[str],
    case_id: str,
    tenant_id: str,
    days_back: int,
    include_osint: bool
):
    """Función background para análisis masivo"""
    try:
        await update_case_status(case_id, "running")
        logger.info(f"🔍 Ejecutando análisis masivo: {len(user_emails)} cuentas")
        
        # Ejecutar análisis masivo
        result = await analyze_multiple_accounts(
            user_emails=user_emails,
            case_id=case_id,
            tenant_id=tenant_id,
            days_back=days_back,
            include_osint=include_osint
        )
        
        # Actualizar caso con resultados
        await update_case_status(
            case_id,
            "completed",
            results=result,
            summary=generate_bulk_summary(result)
        )
        
        logger.info(f"✅ Análisis masivo completado: {result.get('accounts_analyzed', 0)} cuentas")
        
    except Exception as e:
        logger.error(f"❌ Error en análisis masivo: {e}", exc_info=True)
        await update_case_status(case_id, "failed", error=str(e))


def generate_account_summary(result: Dict) -> Dict:
    """Genera resumen ejecutivo del análisis de cuenta"""
    risk = result.get("risk_assessment", {})
    
    return {
        "user_email": result.get("user_email"),
        "risk_score": risk.get("risk_score", 0),
        "risk_level": risk.get("risk_level", "unknown"),
        "total_risk_factors": risk.get("total_factors", 0),
        "timeline_events": len(result.get("timeline", [])),
        "recommendations_count": len(result.get("recommendations", [])),
        "tools_executed": [
            "M365 Graph API",
            "Sparrow" if result.get("sparrow_analysis") else None,
            "Hawk" if result.get("mailbox_analysis") else None,
            "Sherlock" if result.get("osint_analysis") else None
        ],
        "critical_findings": [
            f for f in risk.get("risk_factors", [])
            if f.get("points", 0) >= 15
        ]
    }


def generate_bulk_summary(result: Dict) -> Dict:
    """Genera resumen de análisis masivo"""
    return {
        "total_accounts_analyzed": result.get("accounts_analyzed", 0),
        "high_risk_accounts": result.get("high_risk_accounts", []),
        "high_risk_count": len(result.get("high_risk_accounts", [])),
        "average_risk_score": round(result.get("average_risk_score", 0), 2),
        "status": result.get("status", "unknown")
    }


@router.get("/{user_email}/report")
async def get_account_report(user_email: str, case_id: Optional[str] = None):
    """
    Obtiene el reporte de análisis de una cuenta
    
    Si no se especifica case_id, busca el análisis más reciente
    """
    try:
        # TODO: Implementar búsqueda en base de datos
        return {
            "status": "not_implemented",
            "message": "Endpoint en desarrollo"
        }
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/high-risk")
async def list_high_risk_accounts(tenant_id: str, days: int = 30):
    """
    Lista cuentas de alto riesgo en el tenant
    
    Busca cuentas con risk score >= 70 en los últimos N días
    """
    try:
        # TODO: Implementar búsqueda en base de datos
        return {
            "status": "not_implemented",
            "message": "Endpoint en desarrollo"
        }
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
