"""
Workflow Routes - Flujo automatizado de casos IR
Wizard para crear y ejecutar análisis forense completo
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime
import logging

from api.services.dashboard_data import dashboard_data
from api.services.graph_builder import graph_builder

router = APIRouter(prefix="/workflow", tags=["Case Workflow"])
logger = logging.getLogger(__name__)

# Store for tracking analysis progress
analysis_progress = {}


class NewCaseWizardRequest(BaseModel):
    """Request para crear nuevo caso con análisis automatizado"""
    tenant_id: str = Field(..., description="ID del tenant a analizar")
    title: str = Field(..., description="Título del incidente")
    description: Optional[str] = Field(None, description="Descripción detallada")
    priority: Literal["low", "medium", "high", "critical"] = Field(default="medium")
    threat_type: Optional[str] = Field(None, description="Tipo de amenaza sospechada")
    
    # Análisis a ejecutar
    run_sparrow: bool = Field(default=True, description="Ejecutar análisis Sparrow (Azure AD)")
    run_hawk: bool = Field(default=True, description="Ejecutar análisis Hawk (Exchange)")
    run_loki: bool = Field(default=False, description="Ejecutar escaneo Loki (IOCs)")
    run_yara: bool = Field(default=False, description="Ejecutar escaneo YARA")
    
    # Opciones
    days_back: int = Field(default=90, ge=1, le=365)
    target_users: Optional[List[str]] = Field(None, description="Usuarios específicos a analizar")
    auto_generate_report: bool = Field(default=True)


class CaseProgress(BaseModel):
    """Estado de progreso del análisis"""
    case_id: str
    status: Literal["initializing", "running", "completed", "failed"]
    progress_percentage: int
    current_step: str
    steps_completed: List[str]
    steps_pending: List[str]
    started_at: str
    estimated_completion: Optional[str] = None
    error: Optional[str] = None
    results_summary: Optional[dict] = None


@router.get("/next-case-id")
async def get_next_case_id():
    """
    Genera el próximo ID de caso automáticamente
    Formato: IR-YYYY-NNN
    """
    year = datetime.utcnow().year
    
    # Obtener el último número de caso del año actual
    cases = dashboard_data.get_all_cases()
    
    max_number = 0
    prefix = f"IR-{year}-"
    
    for case in cases:
        case_id = case.get("case_id", "")
        if case_id.startswith(prefix):
            try:
                num = int(case_id.replace(prefix, ""))
                max_number = max(max_number, num)
            except ValueError:
                pass
    
    next_number = max_number + 1
    next_case_id = f"IR-{year}-{next_number:03d}"
    
    return {
        "next_case_id": next_case_id,
        "year": year,
        "sequence": next_number
    }


@router.post("/start-investigation")
async def start_investigation(
    request: NewCaseWizardRequest,
    background_tasks: BackgroundTasks
):
    """
    Inicia una investigación forense completa
    
    Flujo:
    1. Genera ID automático
    2. Crea el caso en la base de datos
    3. Ejecuta herramientas seleccionadas en secuencia
    4. Construye grafo de ataque
    5. Genera reporte automático
    """
    try:
        # 1. Generar ID de caso
        next_id_response = await get_next_case_id()
        case_id = next_id_response["next_case_id"]
        
        logger.info(f"🚀 Iniciando investigación {case_id} para tenant {request.tenant_id}")
        
        # 2. Crear caso en BD
        case_result = dashboard_data.create_case(
            case_id=case_id,
            title=request.title,
            priority=request.priority,
            threat_type=request.threat_type,
            description=request.description,
            tenant_id=request.tenant_id
        )
        
        if not case_result.get("success"):
            raise HTTPException(status_code=400, detail=case_result.get("error"))
        
        # 3. Determinar pasos a ejecutar
        steps = []
        if request.run_sparrow:
            steps.append("sparrow")
        if request.run_hawk:
            steps.append("hawk")
        if request.run_loki:
            steps.append("loki")
        if request.run_yara:
            steps.append("yara")
        steps.append("graph")  # Siempre construir grafo
        if request.auto_generate_report:
            steps.append("report")
        
        # 4. Inicializar progreso
        analysis_progress[case_id] = {
            "case_id": case_id,
            "tenant_id": request.tenant_id,
            "status": "initializing",
            "progress_percentage": 0,
            "current_step": "Inicializando...",
            "steps_completed": [],
            "steps_pending": steps.copy(),
            "started_at": datetime.utcnow().isoformat(),
            "estimated_completion": None,
            "error": None,
            "results_summary": None
        }
        
        # 5. Ejecutar análisis en background
        background_tasks.add_task(
            execute_full_analysis,
            case_id=case_id,
            tenant_id=request.tenant_id,
            steps=steps,
            days_back=request.days_back,
            target_users=request.target_users
        )
        
        return {
            "success": True,
            "case_id": case_id,
            "status": "initializing",
            "message": f"Investigación {case_id} iniciada con {len(steps)} pasos",
            "steps": steps,
            "progress_url": f"/api/workflow/progress/{case_id}"
        }
        
    except Exception as e:
        logger.error(f"❌ Error al iniciar investigación: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/progress/{case_id}", response_model=CaseProgress)
async def get_analysis_progress(case_id: str):
    """
    Obtener el progreso actual del análisis
    Usar para polling desde el frontend
    """
    if case_id not in analysis_progress:
        # Intentar cargar desde la BD si no está en memoria
        case = dashboard_data.get_case_by_id(case_id)
        if not case:
            raise HTTPException(status_code=404, detail=f"Caso {case_id} no encontrado")
        
        # Reconstruir estado desde BD
        return CaseProgress(
            case_id=case_id,
            status=case.get("status", "unknown"),
            progress_percentage=100 if case.get("status") == "closed" else 0,
            current_step=case.get("status", "unknown"),
            steps_completed=[],
            steps_pending=[],
            started_at=case.get("created_at", ""),
            results_summary=None
        )
    
    progress = analysis_progress[case_id]
    return CaseProgress(**progress)


@router.get("/active-investigations")
async def get_active_investigations():
    """
    Listar todas las investigaciones activas (en progreso)
    """
    active = []
    for case_id, progress in analysis_progress.items():
        if progress["status"] in ["initializing", "running"]:
            active.append({
                "case_id": case_id,
                "status": progress["status"],
                "progress": progress["progress_percentage"],
                "current_step": progress["current_step"],
                "started_at": progress["started_at"]
            })
    
    return {"count": len(active), "investigations": active}


async def execute_full_analysis(
    case_id: str,
    tenant_id: str,
    steps: List[str],
    days_back: int,
    target_users: Optional[List[str]]
):
    """
    Ejecuta el análisis forense completo en background
    Usa Microsoft Graph API para recopilar datos REALES del tenant
    """
    try:
        progress = analysis_progress[case_id]
        progress["status"] = "running"
        total_steps = len(steps)
        results = {}
        
        # Importar servicios
        from api.services.m365_investigation import M365InvestigationService
        from api.services.endpoint import run_loki_scan, run_yara_scan
        import os
        
        # Crear servicio M365 con credenciales del .env
        m365_service = M365InvestigationService(
            tenant_id=os.getenv("M365_TENANT_ID", tenant_id),
            client_id=os.getenv("M365_CLIENT_ID", ""),
            client_secret=os.getenv("M365_CLIENT_SECRET", "")
        )
        
        for i, step in enumerate(steps):
            try:
                progress["current_step"] = f"Ejecutando {step.upper()}..."
                progress["progress_percentage"] = int((i / total_steps) * 100)
                
                logger.info(f"📊 [{case_id}] Paso {i+1}/{total_steps}: {step}")
                
                if step == "sparrow":
                    # Usar Graph API para recopilar datos M365 REALES
                    progress["current_step"] = "Recopilando datos de Azure AD vía Graph API..."
                    m365_result = await m365_service.run_full_investigation(
                        case_id=case_id,
                        days_back=days_back,
                        target_users=target_users
                    )
                    results["sparrow"] = m365_result
                    results["m365_graph"] = m365_result  # También guardar como m365_graph
                    
                elif step == "hawk":
                    # Hawk también usa los mismos datos de Graph
                    progress["current_step"] = "Analizando reglas de correo y permisos..."
                    # Si ya ejecutamos sparrow, usamos esos datos
                    if "m365_graph" not in results:
                        m365_result = await m365_service.run_full_investigation(
                            case_id=case_id,
                            days_back=days_back,
                            target_users=target_users
                        )
                        results["hawk"] = m365_result
                    else:
                        results["hawk"] = {"status": "completed", "note": "Datos incluidos en análisis Sparrow"}
                    
                elif step == "loki":
                    results["loki"] = await run_loki_scan(
                        case_id=case_id,
                        paths=["/tmp", "/home"]
                    )
                    
                elif step == "yara":
                    results["yara"] = await run_yara_scan(
                        case_id=case_id,
                        target_path="/tmp"
                    )
                    
                elif step == "graph":
                    # Construir grafo de ataque
                    graph = graph_builder.build_case_graph(case_id, tenant_id)
                    results["graph"] = {
                        "nodes_count": len(graph.nodes),
                        "edges_count": len(graph.edges),
                        "risk_score": graph.risk_score
                    }
                    
                elif step == "report":
                    # El reporte se genera bajo demanda desde /forensics/report/
                    results["report"] = {
                        "executive_url": f"/forensics/report/executive/{case_id}",
                        "technical_url": f"/forensics/report/technical/{case_id}"
                    }
                
                # Marcar paso completado
                progress["steps_completed"].append(step)
                progress["steps_pending"].remove(step)
                
                # Registrar actividad
                dashboard_data.add_case_activity(
                    case_id=case_id,
                    action_type="analysis_step",
                    message=f"Completado: {step.upper()}"
                )
                
            except Exception as step_error:
                logger.error(f"❌ [{case_id}] Error en paso {step}: {step_error}")
                results[step] = {"error": str(step_error)}
                progress["steps_completed"].append(f"{step} (error)")
                if step in progress["steps_pending"]:
                    progress["steps_pending"].remove(step)
        
        # Análisis completado
        progress["status"] = "completed"
        progress["progress_percentage"] = 100
        progress["current_step"] = "Análisis completado"
        
        # Generar resumen
        risk_score = results.get("graph", {}).get("risk_score", 0)
        iocs_count = sum(1 for r in results.values() if isinstance(r, dict) and r.get("iocs"))
        
        progress["results_summary"] = {
            "risk_score": risk_score,
            "tools_executed": len([s for s in progress["steps_completed"] if "error" not in s]),
            "iocs_detected": iocs_count,
            "graph_nodes": results.get("graph", {}).get("nodes_count", 0)
        }
        
        # Actualizar estado del caso en BD
        dashboard_data.update_case_status(case_id, "investigating")
        dashboard_data.add_case_activity(
            case_id=case_id,
            action_type="analysis_completed",
            message=f"Análisis completado. Risk Score: {risk_score}"
        )
        
        logger.info(f"✅ [{case_id}] Análisis completado. Risk Score: {risk_score}")
        
    except Exception as e:
        logger.error(f"❌ [{case_id}] Error fatal en análisis: {e}", exc_info=True)
        
        if case_id in analysis_progress:
            analysis_progress[case_id]["status"] = "failed"
            analysis_progress[case_id]["error"] = str(e)
            analysis_progress[case_id]["current_step"] = "Error en análisis"
        
        dashboard_data.update_case_status(case_id, "failed")
        dashboard_data.add_case_activity(
            case_id=case_id,
            action_type="analysis_failed",
            message=f"Error: {str(e)[:100]}"
        )


@router.post("/cancel/{case_id}")
async def cancel_investigation(case_id: str):
    """
    Cancelar una investigación en progreso
    """
    if case_id not in analysis_progress:
        raise HTTPException(status_code=404, detail="Investigación no encontrada")
    
    progress = analysis_progress[case_id]
    
    if progress["status"] not in ["initializing", "running"]:
        raise HTTPException(status_code=400, detail="La investigación no está en progreso")
    
    progress["status"] = "cancelled"
    progress["current_step"] = "Cancelado por usuario"
    
    dashboard_data.update_case_status(case_id, "cancelled")
    dashboard_data.add_case_activity(
        case_id=case_id,
        action_type="analysis_cancelled",
        message="Investigación cancelada por el usuario"
    )
    
    return {"success": True, "message": f"Investigación {case_id} cancelada"}


@router.get("/templates")
async def get_investigation_templates():
    """
    Obtener plantillas de investigación predefinidas
    """
    return {
        "templates": [
            {
                "id": "bec",
                "name": "Business Email Compromise (BEC)",
                "description": "Investigación de compromiso de correo empresarial",
                "threat_type": "BEC",
                "priority": "critical",
                "run_sparrow": True,
                "run_hawk": True,
                "run_loki": False,
                "run_yara": False,
                "days_back": 90
            },
            {
                "id": "phishing",
                "name": "Phishing Attack",
                "description": "Análisis de ataque de phishing",
                "threat_type": "Phishing",
                "priority": "high",
                "run_sparrow": True,
                "run_hawk": True,
                "run_loki": False,
                "run_yara": False,
                "days_back": 30
            },
            {
                "id": "malware",
                "name": "Malware Investigation",
                "description": "Investigación de infección por malware",
                "threat_type": "Malware",
                "priority": "critical",
                "run_sparrow": False,
                "run_hawk": False,
                "run_loki": True,
                "run_yara": True,
                "days_back": 14
            },
            {
                "id": "insider",
                "name": "Insider Threat",
                "description": "Investigación de amenaza interna",
                "threat_type": "Insider Threat",
                "priority": "high",
                "run_sparrow": True,
                "run_hawk": True,
                "run_loki": False,
                "run_yara": False,
                "days_back": 180
            },
            {
                "id": "full",
                "name": "Full Investigation",
                "description": "Análisis forense completo con todas las herramientas",
                "threat_type": "Unknown",
                "priority": "critical",
                "run_sparrow": True,
                "run_hawk": True,
                "run_loki": True,
                "run_yara": True,
                "days_back": 90
            }
        ]
    }
