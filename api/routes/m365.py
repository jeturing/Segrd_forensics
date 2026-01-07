"""
Router para análisis forense de Microsoft 365 / Azure AD
Integra Sparrow, Hawk y O365 Extractor
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict
from datetime import datetime
import logging

from api.services.cases import create_case, update_case_status
from api.services.m365 import (
    run_sparrow_analysis,
    run_hawk_analysis,
    run_o365_extractor
)

router = APIRouter()
logger = logging.getLogger(__name__)

class M365AnalysisRequest(BaseModel):
    """Request para análisis M365"""
    investigation_id: Optional[str] = Field(None, description="ID de la investigación a vincular (opcional)")
    tenant_id: str = Field(..., description="Azure AD Tenant ID")
    case_id: str = Field(..., description="Identificador del caso (ej: IR-2024-001)")
    scope: List[Literal[
        "sparrow", "hawk", "o365_extractor",
        "azurehound", "roadtools", "aadinternals",
        "monkey365", "crowdstrike_crt", "maester",
        "m365_extractor_suite", "graph_explorer", "cloud_katana"
    ]] = Field(
        default=["sparrow", "hawk"],
        description="Herramientas a ejecutar"
    )
    target_users: Optional[List[str]] = Field(
        default=None,
        description="Usuarios específicos a analizar"
    )
    days_back: int = Field(
        default=90,
        description="Días históricos a analizar",
        ge=1,
        le=365
    )
    priority: Literal["low", "medium", "high", "critical"] = Field(
        default="medium"
    )

class M365AnalysisResponse(BaseModel):
    """Response del análisis M365"""
    case_id: str
    status: str
    message: str
    task_id: str
    estimated_duration_minutes: int

@router.post("/analyze", response_model=M365AnalysisResponse)
async def analyze_m365_tenant(
    request: M365AnalysisRequest,
    background_tasks: BackgroundTasks
):
    """
    Ejecuta análisis forense completo del tenant M365
    
    ## Herramientas disponibles:
    - **sparrow**: Detecta actividad sospechosa en Azure AD, tokens abusados
    - **hawk**: Analiza mailboxes, Teams, reglas maliciosas, OAuth apps
    - **o365_extractor**: Extrae Unified Audit Logs completos
    
    ## Proceso:
    1. Crea un caso en la base de datos
    2. Ejecuta las herramientas seleccionadas en background
    3. Recolecta evidencia y genera reportes
    4. Notifica a Jeturing CORE cuando termine
    """
    try:
        logger.info(f"📋 Iniciando análisis M365 para caso {request.case_id}")
        
        # Crear caso
        case = await create_case({
            "case_id": request.case_id,
            "type": "m365_forensics",
            "tenant_id": request.tenant_id,
            "priority": request.priority,
            "status": "queued",
            "metadata": {
                "scope": request.scope,
                "target_users": request.target_users,
                "days_back": request.days_back
            }
        })
        
        # Estimar duración
        duration_map = {
            "sparrow": 10,
            "hawk": 15,
            "o365_extractor": 20
        }
        estimated_duration = sum(duration_map.get(tool, 10) for tool in request.scope)
        
        # Ejecutar en background
        background_tasks.add_task(
            execute_m365_analysis,
            request.case_id,
            request.tenant_id,
            request.scope,
            request.target_users,
            request.days_back
        )
        
        logger.info(f"✅ Análisis M365 encolado para caso {request.case_id}")
        
        return M365AnalysisResponse(
            case_id=request.case_id,
            status="queued",
            message=f"Análisis iniciado con {len(request.scope)} herramienta(s)",
            task_id=case["task_id"],
            estimated_duration_minutes=estimated_duration
        )
        
    except Exception as e:
        logger.error(f"❌ Error al iniciar análisis M365: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

async def execute_m365_analysis(
    case_id: str,
    tenant_id: str,
    scope: List[str],
    target_users: Optional[List[str]],
    days_back: int
):
    """
    Función background que ejecuta el análisis M365 completo:
    1. Ejecuta herramientas forenses (Sparrow, Hawk, O365)
    2. Enriquece con LLM (SOAR Intelligence)
    3. Genera nodos de grafo con contexto real
    4. Inicia playbook automático si hay hallazgos críticos
    """
    from api.services.cases import update_case_progress
    from api.services.soar_intelligence import soar_engine
    
    try:
        await update_case_status(case_id, "running")
        logger.info(f"🔍 Ejecutando análisis M365 para {case_id}")
        
        results = {}
        all_findings = []
        analyzed_users = target_users or []
        
        # ================================================================
        # FASE 1: Ejecutar herramientas forenses
        # ================================================================
        
        # Ejecutar Sparrow
        if "sparrow" in scope:
            await update_case_progress(
                case_id, 
                current_tool="sparrow",
                current_step="Ejecutando Sparrow - Análisis de sign-ins y OAuth apps"
            )
            logger.info(f"🦅 Ejecutando Sparrow para {tenant_id}")
            results["sparrow"] = await run_sparrow_analysis(
                tenant_id=tenant_id,
                case_id=case_id,
                days_back=days_back
            )
            await update_case_progress(case_id, completed_tool="sparrow")
        
        # Ejecutar Hawk
        if "hawk" in scope:
            await update_case_progress(
                case_id,
                current_tool="hawk", 
                current_step="Ejecutando Hawk - Análisis de reglas de reenvío y permisos"
            )
            logger.info(f"🦅 Ejecutando Hawk para {tenant_id}")
            results["hawk"] = await run_hawk_analysis(
                tenant_id=tenant_id,
                case_id=case_id,
                target_users=target_users,
                days_back=days_back
            )
            await update_case_progress(case_id, completed_tool="hawk")
        
        # Ejecutar O365 Extractor
        if "o365extractor" in scope or "o365_extractor" in scope:
            await update_case_progress(
                case_id,
                current_tool="o365extractor",
                current_step="Ejecutando O365 Extractor - Extracción de logs de auditoría"
            )
            logger.info(f"📦 Ejecutando O365 Extractor para {tenant_id}")
            results["o365_extractor"] = await run_o365_extractor(
                tenant_id=tenant_id,
                case_id=case_id,
                days_back=days_back
            )
            await update_case_progress(case_id, completed_tool="o365extractor")
        
        # ================================================================
        # FASE 2: Enriquecimiento con LLM (SOAR Intelligence)
        # ================================================================
        await update_case_progress(
            case_id,
            current_tool="llm",
            current_step="🧠 Analizando hallazgos con IA..."
        )
        
        try:
            # Preparar hallazgos para el LLM
            findings_for_llm = {
                "case_id": case_id,
                "tenant_id": tenant_id,
                "target_users": target_users,
                "days_analyzed": days_back,
                "tools_executed": list(results.keys()),
                "raw_results": results
            }
            
            # Analizar con SOAR Intelligence (usa LLM)
            enriched_analysis = await soar_engine.analyze_findings_async(findings_for_llm)
            results["llm_analysis"] = enriched_analysis
            
            logger.info(f"🧠 LLM Analysis: severity={enriched_analysis.get('severity')}, risk_score={enriched_analysis.get('risk_score')}")
            
        except Exception as llm_error:
            logger.warning(f"⚠️ LLM analysis failed, using basic analysis: {llm_error}")
            results["llm_analysis"] = {
                "severity": "medium",
                "risk_score": 50,
                "error": str(llm_error)
            }
        
        # ================================================================
        # FASE 3: Generar nodos de grafo con contexto real
        # ================================================================
        await update_case_progress(
            case_id,
            current_tool="graph",
            current_step="📊 Generando grafo de ataque..."
        )
        
        try:
            graph_nodes = await generate_graph_nodes(
                case_id=case_id,
                tenant_id=tenant_id,
                target_users=target_users,
                results=results,
                enriched_analysis=results.get("llm_analysis", {})
            )
            results["graph_nodes"] = graph_nodes
            logger.info(f"📊 Generated {len(graph_nodes.get('nodes', []))} graph nodes")
            
        except Exception as graph_error:
            logger.warning(f"⚠️ Graph generation failed: {graph_error}")
            results["graph_nodes"] = {"error": str(graph_error)}
        
        # ================================================================
        # FASE 4: Playbook automático si hay hallazgos críticos
        # ================================================================
        severity = results.get("llm_analysis", {}).get("severity", "low")
        
        if severity in ["critical", "high"]:
            await update_case_progress(
                case_id,
                current_tool="playbook",
                current_step="🎭 Iniciando playbook de respuesta automática..."
            )
            
            try:
                playbook_result = await execute_auto_playbook(
                    case_id=case_id,
                    severity=severity,
                    findings=results,
                    target_users=target_users
                )
                results["auto_playbook"] = playbook_result
                logger.info(f"🎭 Auto-playbook executed: {playbook_result.get('playbook_id')}")
                
            except Exception as pb_error:
                logger.warning(f"⚠️ Auto-playbook failed: {pb_error}")
                results["auto_playbook"] = {"error": str(pb_error)}
        
        # ================================================================
        # FASE 5: Generar resumen ejecutivo
        # ================================================================
        summary = generate_m365_summary_enhanced(results, target_users)
        
        # Actualizar caso con resultados completos
        await update_case_status(
            case_id,
            "completed",
            results=results,
            summary=summary
        )
        
        logger.info(f"✅ Análisis M365 completado para {case_id} - Severity: {severity}")
        
    except Exception as e:
        logger.error(f"❌ Error en análisis M365: {e}", exc_info=True)
        await update_case_status(case_id, "failed", error=str(e))


async def generate_graph_nodes(
    case_id: str,
    tenant_id: str,
    target_users: Optional[List[str]],
    results: Dict,
    enriched_analysis: Dict
) -> Dict:
    """
    Genera nodos de grafo con contexto real del análisis
    """
    
    nodes = []
    edges = []
    
    # Nodo principal del tenant
    tenant_node = {
        "id": f"tenant_{tenant_id[:8]}",
        "type": "organization",
        "label": f"Tenant {tenant_id[:8]}...",
        "properties": {
            "tenant_id": tenant_id,
            "case_id": case_id
        }
    }
    nodes.append(tenant_node)
    
    # Crear nodos para usuarios analizados
    if target_users:
        for user in target_users:
            user_id = f"user_{user.split('@')[0]}"
            user_node = {
                "id": user_id,
                "type": "user",
                "label": user,
                "properties": {
                    "email": user,
                    "analyzed": True,
                    "case_id": case_id,
                    "risk_level": enriched_analysis.get("severity", "unknown")
                }
            }
            nodes.append(user_node)
            
            # Edge: Usuario -> Tenant
            edges.append({
                "source": user_id,
                "target": tenant_node["id"],
                "relationship": "MEMBER_OF",
                "properties": {"case_id": case_id}
            })
    
    # Extraer entidades de los resultados de herramientas
    for tool_name, tool_result in results.items():
        if tool_name in ["llm_analysis", "graph_nodes"]:
            continue
            
        if isinstance(tool_result, dict):
            # Extraer IPs sospechosas
            suspicious_ips = tool_result.get("suspicious_ips", [])
            for ip in suspicious_ips[:10]:  # Limitar a 10
                ip_id = f"ip_{ip.replace('.', '_')}"
                nodes.append({
                    "id": ip_id,
                    "type": "ip",
                    "label": ip,
                    "properties": {"source": tool_name, "case_id": case_id}
                })
            
            # Extraer OAuth apps maliciosas
            malicious_apps = tool_result.get("malicious_apps", tool_result.get("abused_tokens", []))
            for app in malicious_apps[:5]:
                app_name = app.get("name", app) if isinstance(app, dict) else str(app)
                app_id = f"app_{app_name[:20].replace(' ', '_').lower()}"
                nodes.append({
                    "id": app_id,
                    "type": "application",
                    "label": app_name[:30],
                    "properties": {"malicious": True, "source": tool_name, "case_id": case_id}
                })
            
            # Extraer reglas de reenvío
            forwarding_rules = tool_result.get("forwarding_rules", [])
            for rule in forwarding_rules[:5]:
                rule_id = f"rule_{len(nodes)}"
                nodes.append({
                    "id": rule_id,
                    "type": "mailrule",
                    "label": "Forward Rule",
                    "properties": {"details": rule, "source": tool_name, "case_id": case_id}
                })
    
    # Guardar en base de datos de grafos
    try:
        from api.database import get_db_context
        from api.models.tools import GraphNode, GraphEdge
        
        with get_db_context() as db:
            for node in nodes:
                db_node = GraphNode(
                    id=f"{case_id}_{node['id']}",
                    case_id=case_id,
                    node_type=node["type"],
                    label=node["label"],
                    properties=node.get("properties", {})
                )
                db.merge(db_node)
            
            for edge in edges:
                db_edge = GraphEdge(
                    id=f"{case_id}_{edge['source']}_{edge['target']}",
                    case_id=case_id,
                    source_id=f"{case_id}_{edge['source']}",
                    target_id=f"{case_id}_{edge['target']}",
                    relationship=edge["relationship"],
                    properties=edge.get("properties", {})
                )
                db.merge(db_edge)
            
            db.commit()
            
    except Exception as db_error:
        logger.warning(f"⚠️ Could not persist graph to DB: {db_error}")
    
    return {
        "nodes": nodes,
        "edges": edges,
        "total_nodes": len(nodes),
        "total_edges": len(edges)
    }


async def execute_auto_playbook(
    case_id: str,
    severity: str,
    findings: Dict,
    target_users: Optional[List[str]]
) -> Dict:
    """
    Ejecuta playbook automático basado en severidad
    """
    
    playbook_id = f"AUTO-{case_id}"
    
    # Determinar playbook basado en severidad
    if severity == "critical":
        playbook_name = "Critical IR Response"
        actions = [
            {"action": "revoke_sessions", "target": target_users, "priority": "immediate"},
            {"action": "reset_passwords", "target": target_users, "priority": "immediate"},
            {"action": "notify_soc", "priority": "immediate"},
            {"action": "escalate_ciso", "priority": "high"},
            {"action": "generate_report", "priority": "normal"}
        ]
    else:  # high
        playbook_name = "High Priority Investigation"
        actions = [
            {"action": "validate_sessions", "target": target_users, "priority": "high"},
            {"action": "notify_soc", "priority": "high"},
            {"action": "document_findings", "priority": "normal"},
            {"action": "generate_report", "priority": "normal"}
        ]
    
    # Encolar acciones del playbook
    queued_tasks = []
    for action in actions:
        task_id = f"{playbook_id}_{action['action']}"
        queued_tasks.append({
            "task_id": task_id,
            "action": action["action"],
            "status": "queued",
            "priority": action["priority"]
        })
    
    logger.info(f"🎭 Auto-playbook '{playbook_name}' queued with {len(actions)} actions")
    
    return {
        "playbook_id": playbook_id,
        "playbook_name": playbook_name,
        "severity": severity,
        "actions_queued": len(actions),
        "tasks": queued_tasks,
        "status": "running"
    }


def generate_m365_summary_enhanced(results: dict, target_users: Optional[List[str]]) -> dict:
    """Genera resumen ejecutivo mejorado del análisis M365"""
    llm_analysis = results.get("llm_analysis", {})
    
    summary = {
        "critical_findings": [],
        "suspicious_users": target_users or [],
        "compromised_tokens": [],
        "malicious_rules": [],
        "risk_score": llm_analysis.get("risk_score", 0),
        "severity": llm_analysis.get("severity", "unknown"),
        "threat_categories": llm_analysis.get("threat_categories", []),
        "tags": llm_analysis.get("tags", []),
        "action_plan": llm_analysis.get("action_plan", []),
        "recommendations": llm_analysis.get("recommendations", []),
        "llm_justification": llm_analysis.get("justification", ""),
        "auto_playbook": results.get("auto_playbook", {}),
        "graph_summary": {
            "nodes_created": results.get("graph_nodes", {}).get("total_nodes", 0),
            "edges_created": results.get("graph_nodes", {}).get("total_edges", 0)
        }
    }
    
    # Analizar resultados de Sparrow
    if "sparrow" in results:
        sparrow_data = results["sparrow"]
        if isinstance(sparrow_data, dict):
            summary["critical_findings"].extend(
                sparrow_data.get("critical_findings", [])
            )
            summary["compromised_tokens"].extend(
                sparrow_data.get("abused_tokens", [])
            )
    
    # Analizar resultados de Hawk
    if "hawk" in results:
        hawk_data = results["hawk"]
        if isinstance(hawk_data, dict):
            summary["malicious_rules"].extend(
                hawk_data.get("forwarding_rules", [])
            )
    
    return summary

@router.get("/tenants")
async def list_analyzed_tenants():
    """
    Lista todos los tenants analizados previamente
    """
    try:
        from api.database import SessionLocal
        from api.models.tenant import TenantConfig
        
        db = SessionLocal()
        try:
            tenants = db.query(TenantConfig).all()
            return {
                "tenants": [
                    {
                        "id": t.id,
                        "tenant_id": t.tenant_id,
                        "tenant_name": t.tenant_name,
                        "organization": t.tenant_name,
                        "connected": t.is_active,
                        "created_at": t.created_at.isoformat() if t.created_at else None,
                        "last_analysis": t.updated_at.isoformat() if t.updated_at else None
                    }
                    for t in tenants
                ],
                "total": len(tenants)
            }
        finally:
            db.close()
    except Exception as e:
        logger.error(f"❌ Error loading tenants: {e}")
        return {
            "tenants": [],
            "total": 0,
            "error": str(e)
        }


@router.post("/investigations/{investigation_id}/report")
async def generate_investigation_report(
    investigation_id: str,
    language: Literal["en", "es", "zh-CN", "zh-HK"] = "en",
    format: Literal["html", "pdf", "json", "markdown"] = "html"
):
    """
    Genera reporte de investigación en múltiples idiomas
    
    ## Idiomas soportados:
    - **en**: English
    - **es**: Español
    - **zh-CN**: 中文 (简体) - Chino Simplificado
    - **zh-HK**: 中文 (繁體) - Cantonés / Chino Tradicional
    
    ## Formatos:
    - **html**: Reporte HTML completo con estilos
    - **pdf**: Documento PDF (requiere wkhtmltopdf)
    - **json**: Datos estructurados JSON
    - **markdown**: Formato Markdown
    """
    from api.services.report_generator import report_generator
    
    try:
        logger.info(f"📄 Generando reporte {language}/{format} para investigación {investigation_id}")
        
        # Obtener datos de la investigación (mock por ahora)
        investigation_data = {
            "case_id": investigation_id,
            "summary": {
                "description": "Análisis forense completo de Microsoft 365",
                "total_findings": 15,
                "critical_findings": 3,
                "risk_score": 78
            },
            "findings": [
                {
                    "title": "Compromised OAuth Application",
                    "description": "Se detectó aplicación OAuth con permisos excesivos",
                    "severity": "critical",
                    "timestamp": datetime.utcnow().isoformat()
                },
                {
                    "title": "Suspicious Sign-in Activity",
                    "description": "Múltiples intentos de inicio de sesión desde IPs no autorizadas",
                    "severity": "high",
                    "timestamp": datetime.utcnow().isoformat()
                }
            ],
            "iocs": [
                {"type": "ip", "value": "185.220.101.34", "severity": "high", "source": "Sparrow"},
                {"type": "domain", "value": "malicious-phishing.com", "severity": "critical", "source": "Hawk"},
                {"type": "email", "value": "attacker@evil.com", "severity": "high", "source": "O365 Extractor"}
            ],
            "timeline": [
                {"timestamp": "2025-12-01 10:30 UTC", "description": "Initial compromise detected"},
                {"timestamp": "2025-12-01 14:45 UTC", "description": "Lateral movement observed"},
                {"timestamp": "2025-12-02 08:15 UTC", "description": "Data exfiltration attempt blocked"}
            ],
            "recommendations": [
                "Revoke compromised OAuth applications immediately",
                "Implement Conditional Access policies",
                "Enable MFA for all administrative accounts",
                "Review and rotate all service account credentials"
            ],
            "tools_used": ["Sparrow", "Hawk", "O365 Extractor", "AzureHound"],
            "risk_level": "high",
            "analyst": "JETURING Forensics Platform",
            "m365_results": {}
        }
        
        # Generar reporte
        report_result = await report_generator.generate_investigation_report(
            investigation_id=investigation_id,
            investigation_data=investigation_data,
            language=language,
            format=format
        )
        
        logger.info(f"✅ Reporte generado: {report_result['file_path']}")
        
        return {
            "status": "success",
            **report_result,
            "download_url": f"/api/reports/download/{investigation_id}_{language}.{format}"
        }
        
    except Exception as e:
        logger.error(f"❌ Error generando reporte: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINTS PARA REPORTES M365
# ============================================================================

@router.get("/reports/{case_id}")
async def get_case_reports(case_id: str, tool_name: Optional[str] = None):
    """
    Obtiene todos los reportes de herramientas M365 para un caso
    
    ## Parámetros:
    - **case_id**: ID del caso (ej: IR-2024-001)
    - **tool_name**: Filtrar por herramienta (opcional): sparrow, hawk, o365-extractor
    
    ## Retorna:
    Lista de reportes con resultados parseados y metadatos
    """
    from api.services.m365 import get_tool_reports
    
    try:
        reports = get_tool_reports(case_id, tool_name)
        
        return {
            "case_id": case_id,
            "total_reports": len(reports),
            "reports": reports,
            "filter": {"tool_name": tool_name} if tool_name else None
        }
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo reportes para {case_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/detail/{report_id}")
async def get_report_detail(report_id: str):
    """
    Obtiene el detalle completo de un reporte específico
    
    ## Parámetros:
    - **report_id**: ID único del reporte (ej: M365-XXXXXXXX)
    
    ## Retorna:
    Reporte completo con resultados, evidencia y metadatos
    """
    from api.services.m365 import get_report_by_id
    
    try:
        report = get_report_by_id(report_id)
        
        if not report:
            raise HTTPException(status_code=404, detail=f"Reporte {report_id} no encontrado")
        
        return {
            "status": "success",
            "report": report
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error obteniendo reporte {report_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/summary/{case_id}")
async def get_case_summary(case_id: str):
    """
    Obtiene resumen ejecutivo de todos los análisis de un caso
    
    Consolida hallazgos de todas las herramientas ejecutadas
    """
    from api.services.m365 import get_tool_reports
    
    try:
        reports = get_tool_reports(case_id)
        
        if not reports:
            return {
                "case_id": case_id,
                "status": "no_reports",
                "summary": None
            }
        
        # Consolidar resultados
        summary = {
            "case_id": case_id,
            "total_tools_executed": len(reports),
            "tools": [],
            "total_findings": 0,
            "total_alerts": 0,
            "total_warnings": 0,
            "critical_findings": [],
            "risk_score": 0,
            "evidence_paths": []
        }
        
        for report in reports:
            tool_info = {
                "tool_name": report["tool_name"],
                "status": report["status"],
                "findings_count": report.get("findings_count", 0),
                "alerts_count": report.get("alerts_count", 0),
                "completed_at": report.get("completed_at")
            }
            summary["tools"].append(tool_info)
            summary["total_findings"] += report.get("findings_count", 0)
            summary["total_alerts"] += report.get("alerts_count", 0)
            summary["total_warnings"] += report.get("warnings_count", 0)
            
            if report.get("evidence_path"):
                summary["evidence_paths"].append(report["evidence_path"])
            
            # Extraer hallazgos críticos
            results = report.get("results", {})
            if isinstance(results, dict):
                critical = results.get("critical_findings", [])
                if critical:
                    summary["critical_findings"].extend(critical)
        
        # Calcular risk score
        summary["risk_score"] = (
            len(summary["critical_findings"]) * 10 +
            summary["total_alerts"] * 5 +
            summary["total_warnings"] * 2
        )
        
        # Determinar estado general
        failed = sum(1 for r in reports if r["status"] == "failed")
        if failed == len(reports):
            summary["overall_status"] = "failed"
        elif failed > 0:
            summary["overall_status"] = "partial"
        else:
            summary["overall_status"] = "completed"
        
        return {
            "status": "success",
            "summary": summary
        }
        
    except Exception as e:
        logger.error(f"❌ Error generando resumen para {case_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

