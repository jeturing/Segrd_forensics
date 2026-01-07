"""
Router para análisis de credenciales filtradas
Integra HIBP API, Dehashed, IntelX, LeakCheck y análisis de dumps locales
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict
import logging
from datetime import datetime

from api.services.credentials import (
    check_hibp_breach,
    check_local_dumps,
    analyze_stealer_logs,
    check_dehashed,
    check_intelx,
    check_leakcheck
)
from api.services.cases import create_case, update_case_status
from api.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# In-memory search history (para demo - en producción usar BD)
_search_history: List[Dict] = []

class CredentialCheckRequest(BaseModel):
    """Request para verificación de credenciales"""
    case_id: str = Field(..., description="ID del caso")
    emails: Optional[List[EmailStr]] = Field(default=None)
    domains: Optional[List[str]] = Field(default=None)
    check_hibp: bool = Field(default=True, description="Consultar Have I Been Pwned")
    check_local_dumps: bool = Field(default=True, description="Buscar en dumps locales")
    analyze_stealers: bool = Field(default=False, description="Analizar logs de infostealers")

class UnifiedSearchRequest(BaseModel):
    """Request para búsqueda unificada"""
    query: str = Field(..., description="Término de búsqueda")
    type: str = Field(default="email", description="Tipo: email, domain, username, phone, ip")
    sources: List[str] = Field(default=["hibp", "local"], description="Fuentes a consultar")

class CredentialCheckResponse(BaseModel):
    """Response de verificación de credenciales"""
    case_id: str
    status: str
    task_id: str
    total_emails: int
    message: str

class BreachResult(BaseModel):
    """Resultado de exposición individual"""
    email: str
    exposed: bool
    breach_count: int
    breaches: List[str]
    sources: List[str]
    risk_level: str
    recommendations: List[str]


@router.get("/api-status")
async def get_api_status():
    """Obtener estado de las APIs configuradas"""
    return {
        "hibp": {
            "name": "Have I Been Pwned",
            "enabled": bool(settings.HIBP_API_KEY and settings.HIBP_ENABLED)
        },
        "dehashed": {
            "name": "Dehashed",
            "enabled": bool(settings.DEHASHED_API_KEY and settings.DEHASHED_ENABLED)
        },
        "intelx": {
            "name": "Intelligence X",
            "enabled": bool(settings.INTELX_API_KEY)
        },
        "leakcheck": {
            "name": "LeakCheck",
            "enabled": False  # Agregar config cuando esté disponible
        },
        "local": {
            "name": "Local Dumps",
            "enabled": True
        }
    }


@router.get("/history")
async def get_search_history():
    """Obtener historial de búsquedas"""
    return {"searches": _search_history[-50:]}  # Últimas 50


@router.post("/search")
async def unified_search(request: UnifiedSearchRequest):
    """
    Búsqueda unificada en múltiples fuentes de dark web
    """
    global _search_history
    
    logger.info(f"🔍 Búsqueda unificada: {request.query} ({request.type})")
    
    results = {
        "query": request.query,
        "type": request.type,
        "total_breaches": 0,
        "sources_checked": 0,
        "breaches": [],
        "credentials_found": 0,
        "risk_level": "none",
        "recommendations": [],
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        # HIBP
        if "hibp" in request.sources and request.type == "email":
            results["sources_checked"] += 1
            hibp_result = await check_hibp_breach(request.query)
            if hibp_result.get("breached"):
                for breach in hibp_result.get("breaches", []):
                    results["breaches"].append({
                        "name": breach.get("name"),
                        "source": "hibp",
                        "breach_date": breach.get("breach_date"),
                        "pwn_count": breach.get("pwn_count"),
                        "data_classes": breach.get("data_classes", []),
                        "risk_level": "high" if "Passwords" in breach.get("data_classes", []) else "medium"
                    })
                results["total_breaches"] += len(hibp_result.get("breaches", []))
        
        # Dehashed
        if "dehashed" in request.sources and settings.DEHASHED_API_KEY:
            results["sources_checked"] += 1
            dehashed_result = await check_dehashed(request.query, request.type)
            if dehashed_result.get("found"):
                for entry in dehashed_result.get("entries", []):
                    results["breaches"].append({
                        "name": entry.get("database_name", "Unknown"),
                        "source": "dehashed",
                        "breach_date": entry.get("obtained_from"),
                        "credentials": entry.get("credentials", []),
                        "risk_level": "critical" if entry.get("password") else "high"
                    })
                    if entry.get("password"):
                        results["credentials_found"] += 1
                results["total_breaches"] += len(dehashed_result.get("entries", []))
        
        # Intelligence X
        if "intelx" in request.sources and settings.INTELX_API_KEY:
            results["sources_checked"] += 1
            intelx_result = await check_intelx(request.query, request.type)
            if intelx_result.get("found"):
                for entry in intelx_result.get("results", []):
                    results["breaches"].append({
                        "name": entry.get("name", "IntelX Result"),
                        "source": "intelx",
                        "breach_date": entry.get("date"),
                        "data_classes": [entry.get("type", "unknown")],
                        "risk_level": "high"
                    })
                results["total_breaches"] += len(intelx_result.get("results", []))
        
        # LeakCheck
        if "leakcheck" in request.sources:
            results["sources_checked"] += 1
            leakcheck_result = await check_leakcheck(request.query, request.type)
            if leakcheck_result.get("found"):
                for entry in leakcheck_result.get("sources", []):
                    results["breaches"].append({
                        "name": entry.get("name", "LeakCheck"),
                        "source": "leakcheck",
                        "breach_date": entry.get("date"),
                        "credentials": entry.get("credentials", []),
                        "risk_level": "critical" if entry.get("password") else "high"
                    })
                    if entry.get("password"):
                        results["credentials_found"] += 1
                results["total_breaches"] += len(leakcheck_result.get("sources", []))
        
        # Local Dumps
        if "local" in request.sources:
            results["sources_checked"] += 1
            local_result = await check_local_dumps(request.query)
            if local_result.get("found"):
                for dump in local_result.get("dumps", []):
                    results["breaches"].append({
                        "name": dump.get("file", "Local Dump"),
                        "source": "local",
                        "context": dump.get("context", ""),
                        "risk_level": "high"
                    })
                results["total_breaches"] += len(local_result.get("dumps", []))
            
            # También buscar en stealer logs
            stealer_result = await analyze_stealer_logs(request.query)
            if stealer_result.get("found"):
                for log in stealer_result.get("logs", []):
                    results["breaches"].append({
                        "name": log.get("stealer_type", "Stealer Log"),
                        "source": "stealer",
                        "credentials": log.get("credentials", []),
                        "risk_level": "critical"
                    })
                    results["credentials_found"] += len(log.get("credentials", []))
                results["total_breaches"] += len(stealer_result.get("logs", []))
        
        # Calcular nivel de riesgo global
        if results["credentials_found"] > 0 or any(b.get("risk_level") == "critical" for b in results["breaches"]):
            results["risk_level"] = "critical"
        elif results["total_breaches"] >= 5:
            results["risk_level"] = "high"
        elif results["total_breaches"] >= 2:
            results["risk_level"] = "medium"
        elif results["total_breaches"] >= 1:
            results["risk_level"] = "low"
        
        # Generar recomendaciones
        if results["risk_level"] == "critical":
            results["recommendations"] = [
                "🚨 CRÍTICO: Cambiar contraseña inmediatamente",
                "Revocar todas las sesiones activas",
                "Habilitar MFA en todas las cuentas",
                "Ejecutar análisis EDR en dispositivos asociados",
                "Notificar al equipo de seguridad"
            ]
        elif results["risk_level"] == "high":
            results["recommendations"] = [
                "⚠️ Cambiar contraseña lo antes posible",
                "Habilitar MFA si no está activo",
                "Revisar actividad reciente de la cuenta",
                "Monitorear accesos sospechosos"
            ]
        elif results["total_breaches"] > 0:
            results["recommendations"] = [
                "Considerar cambio de contraseña preventivo",
                "Verificar que MFA esté habilitado",
                "Usar contraseñas únicas por servicio"
            ]
        
        # Guardar en historial
        _search_history.append({
            "query": request.query,
            "type": request.type,
            "risk_level": results["risk_level"],
            "total_breaches": results["total_breaches"],
            "timestamp": datetime.now().isoformat()
        })
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Error en búsqueda unificada: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/check", response_model=CredentialCheckResponse)
async def check_credentials(
    request: CredentialCheckRequest,
    background_tasks: BackgroundTasks
):
    """
    Verifica exposición de credenciales en múltiples fuentes
    
    ## Fuentes verificadas:
    - **HIBP API**: Base de datos pública de brechas
    - **Dumps locales**: Colecciones de stealer logs
    - **Logs de infostealers**: Análisis de malware descargado
    
    ## Proceso:
    1. Normaliza lista de correos/dominios
    2. Consulta fuentes en paralelo
    3. Correlaciona resultados
    4. Genera alertas por usuario
    5. Recomienda acciones de remediación
    """
    try:
        # Validar que haya al menos emails o dominios
        if not request.emails and not request.domains:
            raise HTTPException(
                status_code=400,
                detail="Debe proporcionar al menos emails o dominios"
            )
        
        total_emails = len(request.emails or [])
        logger.info(f"🔍 Verificando {total_emails} credenciales para caso {request.case_id}")
        
        # Crear caso
        case = await create_case({
            "case_id": request.case_id,
            "type": "credential_exposure",
            "status": "queued",
            "metadata": {
                "email_count": total_emails,
                "domain_count": len(request.domains or []),
                "sources": {
                    "hibp": request.check_hibp,
                    "local_dumps": request.check_local_dumps,
                    "stealer_logs": request.analyze_stealers
                }
            }
        })
        
        # Ejecutar análisis en background
        background_tasks.add_task(
            execute_credential_check,
            request.case_id,
            request.emails,
            request.domains,
            request.check_hibp,
            request.check_local_dumps,
            request.analyze_stealers
        )
        
        return CredentialCheckResponse(
            case_id=request.case_id,
            status="queued",
            task_id=case["task_id"],
            total_emails=total_emails,
            message=f"Análisis iniciado para {total_emails} credenciales"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error al verificar credenciales: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

async def execute_credential_check(
    case_id: str,
    emails: Optional[List[str]],
    domains: Optional[List[str]],
    check_hibp: bool,
    check_local_dumps: bool,
    analyze_stealers: bool
):
    """
    Ejecuta la verificación de credenciales en background
    """
    try:
        await update_case_status(case_id, "running")
        logger.info(f"🔐 Analizando credenciales para {case_id}")
        
        results = []
        email_list = emails or []
        
        # Si hay dominios, expandir a emails conocidos
        if domains:
            # TODO: Expandir dominios a lista de emails desde AD/M365
            pass
        
        for email in email_list:
            breach_data = {
                "email": email,
                "exposed": False,
                "breach_count": 0,
                "breaches": [],
                "sources": []
            }
            
            # Verificar HIBP
            if check_hibp:
                logger.info(f"🔍 Verificando {email} en HIBP")
                hibp_result = await check_hibp_breach(email)
                if hibp_result["breached"]:
                    breach_data["exposed"] = True
                    breach_data["breach_count"] += len(hibp_result["breaches"])
                    breach_data["breaches"].extend(hibp_result["breaches"])
                    breach_data["sources"].append("hibp")
            
            # Verificar dumps locales
            if check_local_dumps:
                logger.info(f"🗂️ Verificando {email} en dumps locales")
                dump_result = await check_local_dumps(email)
                if dump_result["found"]:
                    breach_data["exposed"] = True
                    breach_data["breach_count"] += len(dump_result["dumps"])
                    breach_data["breaches"].extend(dump_result["dumps"])
                    breach_data["sources"].append("local_dumps")
            
            # Analizar stealer logs
            if analyze_stealers:
                logger.info(f"🦠 Analizando stealer logs para {email}")
                stealer_result = await analyze_stealer_logs(email)
                if stealer_result["found"]:
                    breach_data["exposed"] = True
                    breach_data["breach_count"] += len(stealer_result["logs"])
                    breach_data["breaches"].extend(stealer_result["logs"])
                    breach_data["sources"].append("stealer_logs")
            
            # Calcular risk level
            breach_data["risk_level"] = calculate_risk_level(breach_data)
            breach_data["recommendations"] = generate_recommendations(breach_data)
            
            results.append(breach_data)
        
        # Generar resumen
        summary = {
            "total_checked": len(results),
            "exposed_count": sum(1 for r in results if r["exposed"]),
            "high_risk_count": sum(1 for r in results if r["risk_level"] == "high"),
            "critical_risk_count": sum(1 for r in results if r["risk_level"] == "critical")
        }
        
        await update_case_status(
            case_id,
            "completed",
            results=results,
            summary=summary
        )
        
        logger.info(f"✅ Análisis de credenciales completado para {case_id}")
        
    except Exception as e:
        logger.error(f"❌ Error en análisis de credenciales: {e}", exc_info=True)
        await update_case_status(case_id, "failed", error=str(e))

def calculate_risk_level(breach_data: dict) -> str:
    """Calcula nivel de riesgo basado en exposición"""
    breach_count = breach_data["breach_count"]
    sources = breach_data["sources"]
    
    if "stealer_logs" in sources:
        return "critical"
    elif breach_count >= 5:
        return "high"
    elif breach_count >= 2:
        return "medium"
    elif breach_count >= 1:
        return "low"
    else:
        return "none"

def generate_recommendations(breach_data: dict) -> List[str]:
    """Genera recomendaciones basadas en exposición"""
    recommendations = []
    
    if breach_data["exposed"]:
        recommendations.append("Forzar cambio inmediato de contraseña")
        recommendations.append("Habilitar MFA si no está activo")
        
        if "stealer_logs" in breach_data["sources"]:
            recommendations.append("🚨 CRÍTICO: Dispositivo posiblemente infectado - ejecutar análisis EDR")
            recommendations.append("Revocar todas las sesiones activas")
            recommendations.append("Revisar actividad reciente en M365/Azure AD")
        
        if breach_data["breach_count"] >= 3:
            recommendations.append("Auditar todos los servicios donde se use este correo")
            recommendations.append("Notificar al usuario sobre higiene de contraseñas")
    
    return recommendations

@router.get("/breaches/{email}")
async def get_email_breaches(email: EmailStr):
    """
    Obtiene historial de brechas para un email específico
    """
    try:
        result = await check_hibp_breach(email)
        return result
    except Exception as e:
        logger.error(f"❌ Error al consultar brechas: {e}")
        raise HTTPException(status_code=500, detail=str(e))
