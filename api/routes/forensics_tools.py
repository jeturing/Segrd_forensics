"""
Router para ejecutar herramientas forenses integradas
Integra: Sparrow, Hawk, Loki, YARA, OSQuery, Volatility, O365 Extractor
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
import logging

from api.services.cases import create_case, update_case_status
from api.services.m365 import (
    run_sparrow_analysis,
    run_hawk_analysis,
    run_o365_extractor
)
from api.services.endpoint import (
    run_loki_scan,
    run_yara_scan,
    collect_osquery_artifacts,
    analyze_memory_dump
)
from api.services.sherlock_service import (
    run_sherlock_bulk
)

router = APIRouter(prefix="/forensics/tools", tags=["Forensic Tools"])
logger = logging.getLogger(__name__)


class ForensicToolsRequest(BaseModel):
    """Request para ejecutar conjunto de herramientas forenses"""
    case_id: str = Field(..., description="Identificador del caso (ej: IR-2024-001)")
    tenant_id: Optional[str] = Field(None, description="Azure AD Tenant ID para análisis M365")
    hostname: Optional[str] = Field(None, description="Hostname para análisis de endpoint")
    tools: List[Literal[
        "sparrow",
        "hawk",
        "o365_extractor",
        "loki",
        "yara",
        "osquery",
        "volatility",
        "sherlock"
    ]] = Field(..., description="Herramientas a ejecutar")
    target_users: Optional[List[str]] = Field(None, description="Usuarios específicos (M365)")
    days_back: int = Field(default=90, ge=1, le=365, description="Días históricos a analizar")
    memory_dump_path: Optional[str] = Field(None, description="Ruta al dump de memoria (Volatility)")
    sherlock_targets: Optional[List[str]] = Field(None, description="Usernames o emails para OSINT con Sherlock")
    priority: Literal["low", "medium", "high", "critical"] = Field(default="medium")


class ForensicToolsResponse(BaseModel):
    """Response de ejecución de herramientas"""
    case_id: str
    status: str
    message: str
    task_id: str
    tools_queued: List[str]
    estimated_duration_minutes: int


class ToolExecutionStatus(BaseModel):
    """Estado de ejecución de una herramienta"""
    case_id: str
    tool: str
    status: str  # queued, running, completed, failed
    progress_percentage: int
    results_summary: Optional[dict] = None
    error: Optional[str] = None


# Duración estimada por herramienta (en minutos)
TOOL_DURATION_MAP = {
    "sparrow": 15,
    "hawk": 20,
    "o365_extractor": 25,
    "loki": 10,
    "yara": 15,
    "osquery": 5,
    "volatility": 30,
    "sherlock": 8
}


@router.post("/execute", response_model=ForensicToolsResponse)
async def execute_forensic_tools(
    request: ForensicToolsRequest,
    background_tasks: BackgroundTasks
):
    """
    Ejecuta múltiples herramientas forenses en paralelo/secuencial
    
    ## Herramientas disponibles:
    
    ### M365 Forensics (requiere tenant_id)
    - **sparrow**: Detecta Azure AD compromise, token abuse, risky sign-ins
    - **hawk**: Analiza Exchange/Teams, mailbox rules, OAuth permissions
    - **o365_extractor**: Extrae Unified Audit Logs de Exchange
    
    ### Endpoint Forensics (requiere hostname)
    - **loki**: Detección de IOCs y malware conocidos
    - **yara**: Búsqueda de patrones de malware
    - **osquery**: Consultas del sistema operativo
    - **volatility**: Análisis de dumps de memoria
    
    ## Ejemplo de ejecución completa:
    ```json
    {
        "case_id": "IR-2024-001",
        "tenant_id": "xxx-xxx-xxx",
        "hostname": "DESKTOP-PC01",
        "tools": ["sparrow", "hawk", "loki", "yara"],
        "target_users": ["admin@empresa.com"],
        "days_back": 90,
        "priority": "high"
    }
    ```
    """
    try:
        logger.info(f"📋 Iniciando ejecución de herramientas forenses para caso {request.case_id}")
        
        # Validar request
        m365_tools = {"sparrow", "hawk", "o365_extractor"}
        endpoint_tools = {"loki", "yara", "osquery", "volatility"}
        
        requested_m365_tools = set(request.tools) & m365_tools
        requested_endpoint_tools = set(request.tools) & endpoint_tools
        
        if requested_m365_tools and not request.tenant_id:
            raise HTTPException(
                status_code=400,
                detail=f"tenant_id requerido para herramientas M365: {', '.join(requested_m365_tools)}"
            )
        
        if requested_endpoint_tools and not request.hostname:
            raise HTTPException(
                status_code=400,
                detail=f"hostname requerido para herramientas de endpoint: {', '.join(requested_endpoint_tools)}"
            )
        
        if "volatility" in request.tools and not request.memory_dump_path:
            raise HTTPException(
                status_code=400,
                detail="memory_dump_path requerido para Volatility"
            )
        
        # Crear caso si no existe
        case = await create_case({
            "case_id": request.case_id,
            "type": "forensic_investigation",
            "tenant_id": request.tenant_id,
            "priority": request.priority,
            "status": "queued",
            "metadata": {
                "tools": request.tools,
                "target_users": request.target_users,
                "days_back": request.days_back,
                "hostname": request.hostname
            }
        })
        
        # Calcular duración estimada
        estimated_duration = sum(
            TOOL_DURATION_MAP.get(tool, 10) for tool in request.tools
        )
        
        # Ejecutar en background
        background_tasks.add_task(
            execute_forensic_tools_background,
            request.case_id,
            request.tenant_id,
            request.hostname,
            request.tools,
            request.target_users,
            request.days_back,
            request.memory_dump_path,
            request.priority
        )
        
        logger.info(f"✅ Ejecución encolada para caso {request.case_id} con {len(request.tools)} herramienta(s)")
        
        return ForensicToolsResponse(
            case_id=request.case_id,
            status="queued",
            message=f"Análisis forense iniciado con {len(request.tools)} herramienta(s)",
            task_id=case["task_id"],
            tools_queued=request.tools,
            estimated_duration_minutes=estimated_duration
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error al iniciar herramientas forenses: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def execute_forensic_tools_background(
    case_id: str,
    tenant_id: Optional[str],
    hostname: Optional[str],
    tools: List[str],
    target_users: Optional[List[str]],
    days_back: int,
    memory_dump_path: Optional[str],
    priority: str
):
    """
    Ejecuta las herramientas forenses en background
    """
    try:
        await update_case_status(case_id, "running")
        logger.info(f"🔍 Iniciando análisis forense para {case_id}")
        
        results = {}
        all_errors = []
        
        # ==================== M365 TOOLS ====================
        
        # Sparrow
        if "sparrow" in tools:
            try:
                logger.info(f"🦅 Ejecutando Sparrow para {tenant_id}")
                results["sparrow"] = await run_sparrow_analysis(
                    tenant_id=tenant_id,
                    case_id=case_id,
                    days_back=days_back
                )
                logger.info("✅ Sparrow completado")
            except Exception as e:
                logger.error(f"❌ Error en Sparrow: {e}")
                all_errors.append(f"Sparrow: {str(e)}")
                results["sparrow"] = {"status": "failed", "error": str(e)}
        
        # Hawk
        if "hawk" in tools:
            try:
                logger.info(f"🦅 Ejecutando Hawk para {tenant_id}")
                results["hawk"] = await run_hawk_analysis(
                    tenant_id=tenant_id,
                    case_id=case_id,
                    target_users=target_users,
                    days_back=days_back
                )
                logger.info("✅ Hawk completado")
            except Exception as e:
                logger.error(f"❌ Error en Hawk: {e}")
                all_errors.append(f"Hawk: {str(e)}")
                results["hawk"] = {"status": "failed", "error": str(e)}
        
        # O365 Extractor
        if "o365_extractor" in tools:
            try:
                logger.info(f"📦 Ejecutando O365 Extractor para {tenant_id}")
                results["o365_extractor"] = await run_o365_extractor(
                    tenant_id=tenant_id,
                    case_id=case_id,
                    days_back=days_back
                )
                logger.info("✅ O365 Extractor completado")
            except Exception as e:
                logger.error(f"❌ Error en O365 Extractor: {e}")
                all_errors.append(f"O365 Extractor: {str(e)}")
                results["o365_extractor"] = {"status": "failed", "error": str(e)}
        
        # ==================== ENDPOINT TOOLS ====================
        
        # Loki
        if "loki" in tools:
            try:
                logger.info(f"🔍 Ejecutando Loki Scanner en {hostname}")
                results["loki"] = await run_loki_scan(
                    hostname=hostname,
                    tailscale_ip=None  # TODO: Soportar remote via Tailscale
                )
                logger.info("✅ Loki completado")
            except Exception as e:
                logger.error(f"❌ Error en Loki: {e}")
                all_errors.append(f"Loki: {str(e)}")
                results["loki"] = {"status": "failed", "error": str(e)}
        
        # YARA
        if "yara" in tools:
            try:
                logger.info(f"🦅 Ejecutando YARA en {hostname}")
                results["yara"] = await run_yara_scan(
                    hostname=hostname,
                    target_paths=["/tmp", "/home", "/var/www"]
                )
                logger.info("✅ YARA completado")
            except Exception as e:
                logger.error(f"❌ Error en YARA: {e}")
                all_errors.append(f"YARA: {str(e)}")
                results["yara"] = {"status": "failed", "error": str(e)}
        
        # OSQuery
        if "osquery" in tools:
            try:
                logger.info(f"🔎 Ejecutando OSQuery en {hostname}")
                results["osquery"] = await collect_osquery_artifacts(
                    hostname=hostname
                )
                logger.info("✅ OSQuery completado")
            except Exception as e:
                logger.error(f"❌ Error en OSQuery: {e}")
                all_errors.append(f"OSQuery: {str(e)}")
                results["osquery"] = {"status": "failed", "error": str(e)}
        
        # Volatility
        if "volatility" in tools:
            try:
                logger.info(f"🧠 Ejecutando Volatility 3 en {memory_dump_path}")
                results["volatility"] = await analyze_memory_dump(
                    dump_path=memory_dump_path
                )
                logger.info("✅ Volatility completado")
            except Exception as e:
                logger.error(f"❌ Error en Volatility: {e}")
                all_errors.append(f"Volatility: {str(e)}")
                results["volatility"] = {"status": "failed", "error": str(e)}
        
        # ==================== OSINT TOOLS ====================
        
        # Sherlock
        if "sherlock" in tools:
            try:
                logger.info("🕵️ Ejecutando Sherlock OSINT")
                if target_users:
                    # Buscar perfiles sociales de usuarios M365
                    results["sherlock"] = await run_sherlock_bulk(
                        usernames=target_users,
                        case_id=case_id
                    )
                else:
                    results["sherlock"] = {
                        "status": "skipped",
                        "message": "No se especificaron targets para Sherlock"
                    }
                logger.info("✅ Sherlock completado")
            except Exception as e:
                logger.error(f"❌ Error en Sherlock: {e}")
                all_errors.append(f"Sherlock: {str(e)}")
                results["sherlock"] = {"status": "failed", "error": str(e)}
        
        # Generar resumen
        summary = generate_forensic_summary(results)
        
        # Actualizar estado del caso
        status = "completed" if not all_errors else "completed_with_errors"
        await update_case_status(
            case_id,
            status,
            results=results,
            summary=summary,
            error="; ".join(all_errors) if all_errors else None
        )
        
        logger.info(f"✅ Análisis forense completado para {case_id}")
        
    except Exception as e:
        logger.error(f"❌ Error en análisis forense: {e}", exc_info=True)
        await update_case_status(case_id, "failed", error=str(e))


def generate_forensic_summary(results: dict) -> dict:
    """Genera resumen ejecutivo de la investigación forense"""
    summary = {
        "tools_executed": [],
        "tools_failed": [],
        "total_findings": 0,
        "critical_findings": [],
        "iocs_detected": [],
        "suspicious_processes": [],
        "malicious_files": [],
        "risk_score": 0,
        "recommendations": []
    }
    
    # Analizar resultados de Sparrow
    if "sparrow" in results and results["sparrow"].get("status") != "failed":
        summary["tools_executed"].append("Sparrow")
        sparrow_data = results["sparrow"]
        summary["critical_findings"].extend(
            sparrow_data.get("critical_findings", [])
        )
        summary["total_findings"] += len(sparrow_data.get("critical_findings", []))
        summary["risk_score"] += 20 if sparrow_data.get("critical_findings") else 0
    elif "sparrow" in results:
        summary["tools_failed"].append("Sparrow")
    
    # Analizar resultados de Hawk
    if "hawk" in results and results["hawk"].get("status") != "failed":
        summary["tools_executed"].append("Hawk")
        hawk_data = results["hawk"]
        summary["critical_findings"].extend(
            hawk_data.get("malicious_rules", [])
        )
        summary["total_findings"] += len(hawk_data.get("malicious_rules", []))
        summary["risk_score"] += 15 if hawk_data.get("malicious_rules") else 0
    elif "hawk" in results:
        summary["tools_failed"].append("Hawk")
    
    # Analizar resultados de Loki
    if "loki" in results and results["loki"].get("status") != "failed":
        summary["tools_executed"].append("Loki")
        loki_data = results["loki"]
        summary["iocs_detected"].extend(
            loki_data.get("iocs", [])
        )
        summary["total_findings"] += loki_data.get("ioc_count", 0)
        summary["risk_score"] += loki_data.get("ioc_count", 0) * 5
    elif "loki" in results:
        summary["tools_failed"].append("Loki")
    
    # Analizar resultados de YARA
    if "yara" in results and results["yara"].get("status") != "failed":
        summary["tools_executed"].append("YARA")
        yara_data = results["yara"]
        summary["malicious_files"].extend(
            yara_data.get("matches", [])
        )
        summary["total_findings"] += len(yara_data.get("matches", []))
        summary["risk_score"] += len(yara_data.get("matches", [])) * 10
    elif "yara" in results:
        summary["tools_failed"].append("YARA")
    
    # Analizar resultados de OSQuery
    if "osquery" in results and results["osquery"].get("status") != "failed":
        summary["tools_executed"].append("OSQuery")
        osquery_data = results["osquery"]
        summary["suspicious_processes"].extend(
            osquery_data.get("suspicious_processes", [])
        )
        summary["total_findings"] += len(osquery_data.get("suspicious_processes", []))
    elif "osquery" in results:
        summary["tools_failed"].append("OSQuery")
    
    # Analizar resultados de Volatility
    if "volatility" in results and results["volatility"].get("status") != "failed":
        summary["tools_executed"].append("Volatility")
        vol_data = results["volatility"]
        summary["suspicious_processes"].extend(
            vol_data.get("suspicious_processes", [])
        )
        summary["malicious_files"].extend(
            vol_data.get("injected_dlls", [])
        )
        summary["total_findings"] += len(vol_data.get("suspicious_processes", [])) + len(vol_data.get("injected_dlls", []))
    elif "volatility" in results:
        summary["tools_failed"].append("Volatility")
    
    # Analizar resultados de O365 Extractor
    if "o365_extractor" in results and results["o365_extractor"].get("status") != "failed":
        summary["tools_executed"].append("O365 Extractor")
    elif "o365_extractor" in results:
        summary["tools_failed"].append("O365 Extractor")
    
    # Analizar resultados de Sherlock
    if "sherlock" in results and results["sherlock"].get("status") != "failed":
        summary["tools_executed"].append("Sherlock")
        sherlock_data = results["sherlock"]
        total_profiles = sherlock_data.get("total_profiles_found", 0)
        if total_profiles > 0:
            summary["total_findings"] += total_profiles
            summary["risk_score"] += min(total_profiles * 2, 20)  # Max 20 puntos
            
            # Agregar perfiles de alto riesgo a critical findings
            profiles = sherlock_data.get("profiles", [])
            high_risk_profiles = [p for p in profiles if p.get("risk_level") == "high"]
            if high_risk_profiles:
                summary["critical_findings"].append({
                    "type": "high_risk_social_profiles",
                    "count": len(high_risk_profiles),
                    "platforms": [p["platform"] for p in high_risk_profiles]
                })
    elif "sherlock" in results:
        summary["tools_failed"].append("Sherlock")
    
    # Generar recomendaciones basadas en hallazgos
    if summary["risk_score"] >= 80:
        summary["recommendations"].append("🔴 Riesgo CRÍTICO: Se recomienda activar el protocolo de incidente")
        summary["recommendations"].append("Aislar inmediatamente los sistemas afectados")
        summary["recommendations"].append("Notificar al equipo de seguridad senior")
    elif summary["risk_score"] >= 50:
        summary["recommendations"].append("🟠 Riesgo ALTO: Investigación profunda recomendada")
        summary["recommendations"].append("Revisar acceso a datos sensibles")
    elif summary["risk_score"] >= 20:
        summary["recommendations"].append("🟡 Riesgo MEDIO: Monitoreo continuo recomendado")
    
    return summary


@router.get("/tools/list")
async def list_available_tools():
    """Lista todas las herramientas forenses disponibles"""
    return {
        "m365_tools": [
            {
                "name": "Sparrow",
                "id": "sparrow",
                "description": "Detecta Azure AD compromise, token abuse, risky sign-ins",
                "duration_minutes": TOOL_DURATION_MAP["sparrow"]
            },
            {
                "name": "Hawk M365",
                "id": "hawk",
                "description": "Analiza Exchange/Teams, mailbox rules, OAuth permissions",
                "duration_minutes": TOOL_DURATION_MAP["hawk"]
            },
            {
                "name": "O365 Extractor",
                "id": "o365_extractor",
                "description": "Extrae Unified Audit Logs de Exchange",
                "duration_minutes": TOOL_DURATION_MAP["o365_extractor"]
            }
        ],
        "osint_tools": [
            {
                "name": "Sherlock (Mr. Holmes)",
                "id": "sherlock",
                "description": "OSINT - Búsqueda de perfiles en redes sociales",
                "duration_minutes": TOOL_DURATION_MAP["sherlock"]
            }
        ],
        "endpoint_tools": [
            {
                "name": "Loki Scanner",
                "id": "loki",
                "description": "Detección de IOCs y malware conocidos",
                "duration_minutes": TOOL_DURATION_MAP["loki"]
            },
            {
                "name": "YARA",
                "id": "yara",
                "description": "Búsqueda de patrones de malware",
                "duration_minutes": TOOL_DURATION_MAP["yara"]
            },
            {
                "name": "OSQuery",
                "id": "osquery",
                "description": "Consultas del sistema operativo",
                "duration_minutes": TOOL_DURATION_MAP["osquery"]
            },
            {
                "name": "Volatility 3",
                "id": "volatility",
                "description": "Análisis de dumps de memoria",
                "duration_minutes": TOOL_DURATION_MAP["volatility"]
            }
        ]
    }

@router.get("/{case_id}/status")
async def get_tools_execution_status(case_id: str):
    """Obtiene el estado de ejecución de las herramientas para un caso"""
    # TODO: Implementar consulta a base de datos
    return {
        "case_id": case_id,
        "status": "running",
        "tools": [
            {
                "tool": "sparrow",
                "status": "running",
                "progress_percentage": 45
            },
            {
                "tool": "hawk",
                "status": "queued",
                "progress_percentage": 0
            }
        ]
    }
