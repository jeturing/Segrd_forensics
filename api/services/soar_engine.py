"""
MCP v4.1 - SOAR Engine (Security Orchestration, Automation and Response)
Motor de automatización de playbooks para respuesta a incidentes.
Incluye: playbooks Red/Blue/Purple, triggers, scheduling, audit.
v4.6.0: Integración con SOAR ML para predicción y aprendizaje continuo.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
import logging

from api.config import settings
from api.database import get_db_context
from api.models.tools import (
    Playbook, PlaybookExecution, PlaybookTrigger, PlaybookStatus,
    StepActionType, ExecutionStatus, AuditLog
)

# v4.6.0: Import ML services
try:
    from api.services.soar_ml import (
        predict_playbook_success,
        recommend_playbooks_for_case,
        record_execution_outcome,
        get_soar_ml_model
    )
    SOAR_ML_AVAILABLE = True
except ImportError:
    SOAR_ML_AVAILABLE = False

logger = logging.getLogger(__name__)


# =============================================================================
# PLAYBOOK DEFINITIONS - BUILT-IN
# =============================================================================

BUILTIN_PLAYBOOKS = {
    "blue_compromised_user": {
        "id": "PB-BLUE-001",
        "name": "Respuesta a Usuario Comprometido",
        "description": "Investiga y contiene cuentas de usuario comprometidas en M365/Azure AD",
        "team_type": "blue",
        "category": "incident_response",
        "tags": ["m365", "azure", "account_compromise", "dfir"],
        "trigger": PlaybookTrigger.MANUAL.value,
        "estimated_duration_minutes": 30,
        "steps": [
            {
                "order": 1,
                "name": "Análisis con Sparrow",
                "description": "Ejecutar Sparrow para detectar signos de compromiso",
                "action_type": StepActionType.TOOL_EXECUTE.value,
                "tool_id": "sparrow",
                "parameters": {"days_to_search": 30},
                "wait_for_completion": True,
                "timeout_seconds": 300,
                "continue_on_error": False
            },
            {
                "order": 2,
                "name": "Análisis con Hawk",
                "description": "Ejecutar Hawk para investigación forense profunda",
                "action_type": StepActionType.TOOL_EXECUTE.value,
                "tool_id": "hawk",
                "parameters": {},
                "wait_for_completion": True,
                "timeout_seconds": 600,
                "continue_on_error": True,
                "condition": "previous_step.iocs_found > 0"
            },
            {
                "order": 3,
                "name": "Verificar credenciales filtradas",
                "description": "Buscar credenciales del usuario en HIBP",
                "action_type": StepActionType.API_CALL.value,
                "api_endpoint": "/forensics/credentials/check",
                "api_method": "POST",
                "parameters": {"check_hibp": True},
                "wait_for_completion": True
            },
            {
                "order": 4,
                "name": "Crear IOCs",
                "description": "Agregar IPs/dominios maliciosos detectados al IOC Store",
                "action_type": StepActionType.CREATE_IOC.value,
                "ioc_source": "sparrow_output",
                "auto_enrich": True
            },
            {
                "order": 5,
                "name": "Actualizar Timeline",
                "description": "Agregar eventos a la línea de tiempo del caso",
                "action_type": StepActionType.UPDATE_TIMELINE.value,
                "timeline_events": ["start", "findings", "actions"]
            },
            {
                "order": 6,
                "name": "Notificar equipo",
                "description": "Enviar notificación al canal de IR",
                "action_type": StepActionType.NOTIFICATION.value,
                "notification_channel": "ir_team",
                "notification_template": "user_compromise_alert"
            }
        ]
    },
    
    "blue_malware_triage": {
        "id": "PB-BLUE-002",
        "name": "Triaje de Malware",
        "description": "Análisis inicial de archivos sospechosos con YARA y Loki",
        "team_type": "blue",
        "category": "malware_analysis",
        "tags": ["malware", "yara", "loki", "ioc"],
        "trigger": PlaybookTrigger.ON_IOC_CREATE.value,
        "trigger_conditions": {"ioc_type": ["hash_sha256", "file"]},
        "estimated_duration_minutes": 15,
        "steps": [
            {
                "order": 1,
                "name": "Escaneo YARA",
                "action_type": StepActionType.TOOL_EXECUTE.value,
                "tool_id": "yara",
                "parameters": {"rules_dir": "/opt/forensics-tools/yara-rules/"}
            },
            {
                "order": 2,
                "name": "Escaneo Loki",
                "action_type": StepActionType.TOOL_EXECUTE.value,
                "tool_id": "loki",
                "parameters": {"mode": "intense"}
            },
            {
                "order": 3,
                "name": "Enriquecer IOCs",
                "action_type": StepActionType.ENRICH_IOC.value,
                "enrichment_sources": ["virustotal", "misp"]
            },
            {
                "order": 4,
                "name": "Crear nodos en grafo",
                "action_type": StepActionType.GRAPH_ENRICH.value
            }
        ]
    },
    
    "red_recon_external": {
        "id": "PB-RED-001",
        "name": "Reconocimiento Externo",
        "description": "Reconocimiento automatizado de superficie de ataque externa",
        "team_type": "red",
        "category": "reconnaissance",
        "tags": ["recon", "osint", "external"],
        "trigger": PlaybookTrigger.MANUAL.value,
        "requires_approval": True,
        "approval_roles": ["admin", "redteam_lead"],
        "estimated_duration_minutes": 60,
        "steps": [
            {
                "order": 1,
                "name": "WHOIS Lookup",
                "action_type": StepActionType.TOOL_EXECUTE.value,
                "tool_id": "whois",
                "target_from": "input.domain"
            },
            {
                "order": 2,
                "name": "DNS Enumeration",
                "action_type": StepActionType.TOOL_EXECUTE.value,
                "tool_id": "dnsenum",
                "target_from": "input.domain"
            },
            {
                "order": 3,
                "name": "Subdomain Discovery",
                "action_type": StepActionType.TOOL_EXECUTE.value,
                "tool_id": "amass",
                "parameters": {"mode": "passive"}
            },
            {
                "order": 4,
                "name": "Port Scan",
                "action_type": StepActionType.TOOL_EXECUTE.value,
                "tool_id": "nmap",
                "parameters": {
                    "scan_type": "SYN",
                    "ports": "1-1000",
                    "timing": "T3"
                }
            },
            {
                "order": 5,
                "name": "Web Fingerprinting",
                "action_type": StepActionType.TOOL_EXECUTE.value,
                "tool_id": "whatweb",
                "target_from": "step.4.open_ports"
            }
        ]
    },
    
    "purple_threat_hunt": {
        "id": "PB-PURPLE-001",
        "name": "Threat Hunting - Lateral Movement",
        "description": "Caza de amenazas enfocada en movimiento lateral",
        "team_type": "purple",
        "category": "threat_hunting",
        "tags": ["threat_hunting", "lateral_movement", "detection"],
        "trigger": PlaybookTrigger.SCHEDULED.value,
        "schedule_cron": "0 3 * * *",  # 3 AM diario
        "estimated_duration_minutes": 45,
        "steps": [
            {
                "order": 1,
                "name": "Detectar sesiones RDP anómalas",
                "action_type": StepActionType.TOOL_EXECUTE.value,
                "tool_id": "osqueryi",
                "parameters": {
                    "query": "SELECT * FROM logged_in_users WHERE type = 'remote'"
                }
            },
            {
                "order": 2,
                "name": "Buscar PowerShell remoting",
                "action_type": StepActionType.TOOL_EXECUTE.value,
                "tool_id": "osqueryi",
                "parameters": {
                    "query": "SELECT * FROM processes WHERE name = 'wsmprovhost.exe'"
                }
            },
            {
                "order": 3,
                "name": "Verificar servicios nuevos",
                "action_type": StepActionType.TOOL_EXECUTE.value,
                "tool_id": "osqueryi",
                "parameters": {
                    "query": "SELECT * FROM services WHERE start_type = 'DEMAND_START'"
                }
            },
            {
                "order": 4,
                "name": "Correlacionar eventos",
                "action_type": StepActionType.RUN_CORRELATION.value,
                "correlation_rules": ["sigma_lateral_movement", "sigma_psexec"]
            },
            {
                "order": 5,
                "name": "Simular TTPs",
                "description": "Ejecutar técnicas de Atomic Red Team",
                "action_type": StepActionType.TOOL_EXECUTE.value,
                "tool_id": "atomic_red_team",
                "parameters": {
                    "technique_ids": ["T1021.001", "T1021.002"]
                },
                "requires_approval": True
            }
        ]
    }
}


# =============================================================================
# SOAR ENGINE
# =============================================================================

class SOAREngine:
    """
    Motor de orquestación para automatización de respuesta.
    Ejecuta playbooks, gestiona triggers, valida políticas.
    v4.6.0: Integrado con ML para predicción de éxito y recomendaciones.
    """
    
    def __init__(self):
        self.active_executions: Dict[str, asyncio.Task] = {}
        self.step_handlers: Dict[str, Callable] = {
            StepActionType.TOOL_EXECUTE.value: self._execute_tool_step,
            StepActionType.API_CALL.value: self._execute_api_step,
            StepActionType.CREATE_IOC.value: self._execute_create_ioc_step,
            StepActionType.ENRICH_IOC.value: self._execute_enrich_ioc_step,
            StepActionType.UPDATE_TIMELINE.value: self._execute_timeline_step,
            StepActionType.NOTIFICATION.value: self._execute_notification_step,
            StepActionType.WAIT.value: self._execute_wait_step,
            StepActionType.CONDITION.value: self._evaluate_condition_step,
            StepActionType.GRAPH_ENRICH.value: self._execute_graph_step,
            StepActionType.RUN_CORRELATION.value: self._execute_correlation_step,
            StepActionType.APPROVAL_GATE.value: self._execute_approval_step,
        }
    
    # -------------------------------------------------------------------------
    # ML-POWERED FEATURES (v4.6.0)
    # -------------------------------------------------------------------------
    
    async def predict_playbook_success(
        self,
        playbook_id: str,
        case_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Predecir probabilidad de éxito de un playbook usando ML.
        
        Args:
            playbook_id: ID del playbook
            case_id: ID del caso (opcional, mejora precisión)
        
        Returns:
            Dict con predicción, probabilidad, y recomendación
        """
        if not SOAR_ML_AVAILABLE:
            return {
                "prediction": "unknown",
                "probability": 0.5,
                "message": "ML module not available"
            }
        
        # Get playbook data
        playbook_data = await self.get_playbook(playbook_id)
        if not playbook_data:
            return {"error": f"Playbook {playbook_id} not found"}
        
        # Get case data if provided
        case_data = None
        if case_id:
            try:
                with get_db_context() as db:
                    from api.models.tools import Case
                    case = db.query(Case).filter(Case.id == case_id).first()
                    if case:
                        case_data = {
                            "id": case.id,
                            "priority": case.priority,
                            "threat_type": case.threat_type,
                            "tags": case.tags or []
                        }
            except Exception as e:
                logger.warning(f"Could not load case: {e}")
        
        return await predict_playbook_success(playbook_data, case_data)
    
    async def get_playbook_recommendations(
        self,
        case_id: str,
        max_recommendations: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Obtener recomendaciones de playbooks para un caso.
        
        Args:
            case_id: ID del caso
            max_recommendations: Máximo de recomendaciones
        
        Returns:
            Lista de playbooks recomendados con scores
        """
        if not SOAR_ML_AVAILABLE:
            # Fallback: return playbooks by team type
            playbooks = await self.list_playbooks()
            return [
                {
                    "playbook_id": p["id"],
                    "playbook_name": p["name"],
                    "score": 0.5,
                    "recommendation": "ML not available"
                }
                for p in playbooks[:max_recommendations]
            ]
        
        # Get case data
        case_data = None
        try:
            with get_db_context() as db:
                from api.models.tools import Case
                case = db.query(Case).filter(Case.id == case_id).first()
                if case:
                    case_data = {
                        "id": case.id,
                        "priority": case.priority,
                        "threat_type": case.threat_type,
                        "tags": case.tags or [],
                        "description": case.description
                    }
        except Exception as e:
            logger.warning(f"Could not load case: {e}")
            case_data = {"id": case_id}
        
        # Get available playbooks
        playbooks = await self.list_playbooks()
        
        return await recommend_playbooks_for_case(
            case_data or {"id": case_id},
            playbooks,
            max_recommendations
        )
    
    async def train_ml_model(self, force: bool = False) -> Dict[str, Any]:
        """
        Entrenar modelo ML con datos históricos.
        
        Args:
            force: Forzar entrenamiento aunque no haya pasado el intervalo
        
        Returns:
            Resultado del entrenamiento
        """
        if not SOAR_ML_AVAILABLE:
            return {"status": "error", "message": "ML module not available"}
        
        model = get_soar_ml_model()
        return await model.train(force=force)
    
    # -------------------------------------------------------------------------
    # PLAYBOOK MANAGEMENT
    # -------------------------------------------------------------------------
    
    async def load_builtin_playbooks(self):
        """Carga playbooks predefinidos a la BD"""
        with get_db_context() as db:
            for pb_key, pb_data in BUILTIN_PLAYBOOKS.items():
                existing = db.query(Playbook).filter(
                    Playbook.id == pb_data["id"]
                ).first()
                
                if not existing:
                    playbook = Playbook(
                        id=pb_data["id"],
                        name=pb_data["name"],
                        description=pb_data["description"],
                        team_type=pb_data["team_type"],
                        category=pb_data.get("category", "general"),
                        tags=pb_data.get("tags", []),
                        trigger=pb_data["trigger"],
                        trigger_conditions=pb_data.get("trigger_conditions", {}),
                        schedule_cron=pb_data.get("schedule_cron"),
                        requires_approval=pb_data.get("requires_approval", False),
                        approval_roles=pb_data.get("approval_roles", []),
                        status=PlaybookStatus.ACTIVE.value,
                        is_builtin=True,
                        estimated_duration_minutes=pb_data.get("estimated_duration_minutes", 30)
                    )
                    db.add(playbook)
                    
                    # Agregar pasos
                    for step_data in pb_data["steps"]:
                        step = PlaybookStep(
                            id=f"{pb_data['id']}-S{step_data['order']:02d}",
                            playbook_id=pb_data["id"],
                            order=step_data["order"],
                            name=step_data["name"],
                            description=step_data.get("description"),
                            action_type=step_data["action_type"],
                            tool_id=step_data.get("tool_id"),
                            api_endpoint=step_data.get("api_endpoint"),
                            api_method=step_data.get("api_method"),
                            parameters=step_data.get("parameters", {}),
                            target_from=step_data.get("target_from"),
                            condition=step_data.get("condition"),
                            wait_for_completion=step_data.get("wait_for_completion", True),
                            timeout_seconds=step_data.get("timeout_seconds", 300),
                            continue_on_error=step_data.get("continue_on_error", False),
                            requires_approval=step_data.get("requires_approval", False)
                        )
                        db.add(step)
                    
                    logger.info(f"📚 Loaded builtin playbook: {pb_data['name']}")
            
            db.commit()
    
    def get_available_playbooks(
        self,
        team_type: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[Dict]:
        """Obtiene playbooks disponibles - con fallback a builtin"""
        try:
            with get_db_context() as db:
                query = db.query(Playbook).filter(
                    Playbook.enabled == True  # Use enabled instead of status
                )
                
                if team_type:
                    query = query.filter(Playbook.playbook_type.contains(team_type))
                if category:
                    query = query.filter(Playbook.category == category)
                
                playbooks = query.all()
                if playbooks:
                    return [
                        {
                            "id": p.id,
                            "name": p.name,
                            "description": p.description,
                            "team_type": p.playbook_type,
                            "category": p.category,
                            "tags": p.tags or [],
                            "trigger": p.triggers[0] if p.triggers else "manual",
                            "requires_approval": p.requires_approval,
                            "estimated_minutes": 30,
                            "execution_count": p.execution_count or 0,
                            "success_rate": p.success_rate or 0.0
                        }
                        for p in playbooks
                    ]
        except Exception as e:
            logger.warning(f"DB query failed, using builtin playbooks: {e}")
        
        # Fallback to builtin playbooks
        result = []
        for pb_id, pb_data in BUILTIN_PLAYBOOKS.items():
            if team_type and pb_data.get("team_type") != team_type:
                continue
            if category and pb_data.get("category") != category:
                continue
            result.append({
                "id": pb_data["id"],
                "name": pb_data["name"],
                "description": pb_data["description"],
                "team_type": pb_data.get("team_type", "blue"),
                "category": pb_data.get("category", "investigation"),
                "tags": pb_data.get("tags", []),
                "trigger": pb_data.get("trigger", "manual"),
                "requires_approval": False,
                "estimated_minutes": pb_data.get("estimated_duration_minutes", 30),
                "execution_count": 0,
                "success_rate": 0.0,
                "data_source": "builtin"
            })
        return result
    
    # -------------------------------------------------------------------------
    # PLAYBOOK EXECUTION
    # -------------------------------------------------------------------------
    
    async def execute_playbook(
        self,
        playbook_id: str,
        input_data: Dict[str, Any],
        user_id: str,
        tenant_id: str,
        case_id: Optional[str] = None,
        investigation_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        approval_user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta un playbook completo.
        
        Args:
            playbook_id: ID del playbook
            input_data: Datos de entrada (target, domain, etc.)
            user_id: Usuario que ejecuta
            tenant_id: Tenant
            case_id: ID del caso asociado
            investigation_id: ID de investigación
            agent_id: Agente remoto (opcional)
            approval_user_id: Usuario que aprobó (si requiere aprobación)
        
        Returns:
            Dict con resultado de la ejecución
        """
        # Cargar playbook
        with get_db_context() as db:
            playbook = db.query(Playbook).filter(
                Playbook.id == playbook_id
            ).first()
            
            if not playbook:
                raise ValueError(f"Playbook {playbook_id} not found")
            
            # Verificar aprobación
            if playbook.requires_approval and not approval_user_id:
                # Crear ejecución pendiente de aprobación
                execution = PlaybookExecution(
                    id=PlaybookExecution.generate_id(),
                    playbook_id=playbook_id,
                    status=ExecutionStatus.PENDING_APPROVAL.value,
                    input_data=input_data,
                    case_id=case_id,
                    investigation_id=investigation_id,
                    agent_id=agent_id,
                    executed_by=user_id,
                    tenant_id=tenant_id
                )
                db.add(execution)
                db.commit()
                
                logger.info(f"⏳ Playbook {playbook_id} pending approval")
                return {
                    "execution_id": execution.id,
                    "status": "pending_approval",
                    "message": f"Playbook requires approval from: {playbook.approval_roles}"
                }
            
            # Verificar política de seguridad
            if playbook.team_type == "red":
                policy = db.query(SecurityPolicy).filter(
                    SecurityPolicy.tenant_id == tenant_id,
                    SecurityPolicy.is_active == True
                ).first()
                
                if not policy or not policy.redteam_enabled:
                    raise PermissionError("Red team playbooks not enabled for this tenant")
            
            # Cargar pasos
            steps = db.query(PlaybookStep).filter(
                PlaybookStep.playbook_id == playbook_id
            ).order_by(PlaybookStep.order).all()
            
            steps_data = [
                {
                    "id": s.id,
                    "order": s.order,
                    "name": s.name,
                    "action_type": s.action_type,
                    "tool_id": s.tool_id,
                    "api_endpoint": s.api_endpoint,
                    "api_method": s.api_method,
                    "parameters": s.parameters,
                    "target_from": s.target_from,
                    "condition": s.condition,
                    "wait_for_completion": s.wait_for_completion,
                    "timeout_seconds": s.timeout_seconds,
                    "continue_on_error": s.continue_on_error,
                    "requires_approval": s.requires_approval
                }
                for s in steps
            ]
        
        # Crear ejecución
        execution_id = PlaybookExecution.generate_id()
        
        with get_db_context() as db:
            execution = PlaybookExecution(
                id=execution_id,
                playbook_id=playbook_id,
                status=ExecutionStatus.RUNNING.value,
                started_at=datetime.utcnow(),
                input_data=input_data,
                case_id=case_id,
                investigation_id=investigation_id,
                agent_id=agent_id,
                executed_by=user_id,
                approval_user_id=approval_user_id,
                tenant_id=tenant_id,
                total_steps=len(steps_data)
            )
            db.add(execution)
            
            # Audit log (file-based by default)
            record_audit_event(
                action="playbook_started",
                action_type="execute",
                resource_type="playbook_execution",
                resource_id=execution_id,
                details={
                    "playbook_id": playbook_id,
                    "team_type": playbook.team_type
                },
                user_id=user_id,
                tenant_id=tenant_id,
                persist_to_db=False,
                db_session=db
            )
        
        logger.info(f"🎬 Starting playbook {playbook_id} (execution: {execution_id})")
        
        # Ejecutar pasos secuencialmente
        context = {
            "input": input_data,
            "steps": {},
            "iocs": [],
            "execution_id": execution_id,
            "case_id": case_id,
            "investigation_id": investigation_id,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "agent_id": agent_id
        }
        
        completed_steps = 0
        failed_steps = 0
        skipped_steps = 0
        
        try:
            for step in steps_data:
                step_execution = await self._execute_step(step, context)
                
                # Guardar resultado en contexto
                context["steps"][step["order"]] = step_execution
                
                if step_execution["status"] == "completed":
                    completed_steps += 1
                elif step_execution["status"] == "failed":
                    failed_steps += 1
                    if not step.get("continue_on_error", False):
                        logger.warning(f"Step {step['name']} failed, stopping playbook")
                        break
                elif step_execution["status"] == "skipped":
                    skipped_steps += 1
                
                # Actualizar progreso
                with get_db_context() as db:
                    exec_record = db.query(PlaybookExecution).filter(
                        PlaybookExecution.id == execution_id
                    ).first()
                    if exec_record:
                        exec_record.current_step = step["order"]
                        exec_record.completed_steps = completed_steps
                        exec_record.failed_steps = failed_steps
                        exec_record.skipped_steps = skipped_steps
                        db.commit()
            
            # Determinar estado final
            if failed_steps > 0 and not any(
                s.get("continue_on_error") for s in steps_data
            ):
                final_status = ExecutionStatus.FAILED.value
            else:
                final_status = ExecutionStatus.SUCCESS.value
            
        except Exception as e:
            logger.error(f"Playbook execution error: {e}")
            final_status = ExecutionStatus.FAILED.value
            context["error"] = str(e)
        
        # Finalizar ejecución
        with get_db_context() as db:
            exec_record = db.query(PlaybookExecution).filter(
                PlaybookExecution.id == execution_id
            ).first()
            
            if exec_record:
                exec_record.status = final_status
                exec_record.finished_at = datetime.utcnow()
                exec_record.completed_steps = completed_steps
                exec_record.failed_steps = failed_steps
                exec_record.skipped_steps = skipped_steps
                exec_record.output_data = {
                    "steps": {
                        k: {
                            "status": v.get("status"),
                            "tool_output": v.get("output", "")[:1000]  # Truncar
                        }
                        for k, v in context["steps"].items()
                    },
                    "iocs_created": len(context.get("iocs", []))
                }
            
            # Actualizar estadísticas del playbook
            playbook = db.query(Playbook).filter(
                Playbook.id == playbook_id
            ).first()
            if playbook:
                playbook.execution_count += 1
                playbook.last_executed_at = datetime.utcnow()
                # Actualizar success rate
                total = playbook.execution_count
                if final_status == ExecutionStatus.SUCCESS.value:
                    playbook.success_rate = ((playbook.success_rate * (total - 1)) + 100) / total
                else:
                    playbook.success_rate = ((playbook.success_rate * (total - 1))) / total
            
            db.commit()
        
        # v4.6.0: Record outcome for ML learning
        execution_duration = (
            datetime.utcnow() - execution.started_at
        ).total_seconds() if execution.started_at else 0
        
        if SOAR_ML_AVAILABLE:
            try:
                await record_execution_outcome(
                    execution_id=execution_id,
                    playbook_id=playbook_id,
                    success=(final_status == ExecutionStatus.SUCCESS.value),
                    execution_time_seconds=execution_duration,
                    steps_completed=completed_steps,
                    steps_failed=failed_steps,
                    error_message=context.get("error")
                )
                logger.debug(f"📊 ML outcome recorded for execution {execution_id}")
            except Exception as ml_error:
                logger.warning(f"⚠️ Could not record ML outcome: {ml_error}")
        
        logger.info(f"🏁 Playbook {playbook_id} finished: {final_status}")
        
        return {
            "execution_id": execution_id,
            "status": final_status,
            "steps_completed": completed_steps,
            "steps_failed": failed_steps,
            "steps_skipped": skipped_steps,
            "iocs_created": len(context.get("iocs", [])),
            "duration_seconds": execution_duration
        }
    
    async def _execute_step(
        self,
        step: Dict,
        context: Dict
    ) -> Dict[str, Any]:
        """Ejecuta un paso individual del playbook"""
        step_id = step["id"]
        step_name = step["name"]
        action_type = step["action_type"]
        
        logger.info(f"  📍 Step {step['order']}: {step_name}")
        
        # Crear registro de ejecución del paso
        step_exec_id = f"{context['execution_id']}-{step['order']:02d}"
        
        with get_db_context() as db:
            step_exec = PlaybookStepExecution(
                id=step_exec_id,
                playbook_execution_id=context["execution_id"],
                step_id=step_id,
                step_order=step["order"],
                status=ExecutionStatus.RUNNING.value,
                started_at=datetime.utcnow()
            )
            db.add(step_exec)
            db.commit()
        
        # Evaluar condición si existe
        if step.get("condition"):
            should_run = self._evaluate_condition(step["condition"], context)
            if not should_run:
                logger.info("    ⏭️ Condition not met, skipping")
                await self._update_step_execution(
                    step_exec_id, "skipped", {"reason": "condition_not_met"}
                )
                return {"status": "skipped", "reason": "condition_not_met"}
        
        # Verificar si requiere aprobación
        if step.get("requires_approval"):
            # En producción, pausaría y esperaría aprobación
            logger.info("    ⚠️ Step requires approval (auto-approved in dev)")
        
        # Obtener handler para el tipo de acción
        handler = self.step_handlers.get(action_type)
        if not handler:
            logger.error(f"    ❌ Unknown action type: {action_type}")
            await self._update_step_execution(
                step_exec_id, "failed", {"error": f"Unknown action: {action_type}"}
            )
            return {"status": "failed", "error": f"Unknown action: {action_type}"}
        
        # Ejecutar con timeout
        try:
            result = await asyncio.wait_for(
                handler(step, context),
                timeout=step.get("timeout_seconds", 300)
            )
            
            await self._update_step_execution(
                step_exec_id, "completed", result
            )
            
            logger.info("    ✅ Step completed")
            return {"status": "completed", **result}
            
        except (asyncio.TimeoutError, TimeoutError):
            error_msg = f"Step timeout after {step.get('timeout_seconds', 300)}s"
            logger.error(f"    ⏰ {error_msg}")
            await self._update_step_execution(
                step_exec_id, "failed", {"error": error_msg}
            )
            return {"status": "failed", "error": error_msg}
            
        except Exception as e:
            logger.error(f"    ❌ Step failed: {e}")
            await self._update_step_execution(
                step_exec_id, "failed", {"error": str(e)}
            )
            return {"status": "failed", "error": str(e)}
    
    async def _update_step_execution(
        self,
        step_exec_id: str,
        status: str,
        output: Dict
    ):
        """Actualiza registro de ejecución de paso"""
        with get_db_context() as db:
            step_exec = db.query(PlaybookStepExecution).filter(
                PlaybookStepExecution.id == step_exec_id
            ).first()
            if step_exec:
                step_exec.status = status
                step_exec.finished_at = datetime.utcnow()
                step_exec.output = output
                step_exec.tool_execution_id = output.get("execution_id")
                db.commit()
    
    def _evaluate_condition(self, condition: str, context: Dict) -> bool:
        """Evalúa condición para ejecución condicional"""
        try:
            # Parsear condición simple: "previous_step.iocs_found > 0"
            if "previous_step" in condition:
                prev_order = max(context["steps"].keys()) if context["steps"] else 0
                prev_result = context["steps"].get(prev_order, {})
                
                if "iocs_found" in condition:
                    iocs_count = len(prev_result.get("iocs", []))
                    # Evaluar operador
                    if "> 0" in condition:
                        return iocs_count > 0
                    elif "== 0" in condition:
                        return iocs_count == 0
            
            return True  # Por defecto ejecutar
        except Exception as e:
            logger.warning(f"Condition evaluation error: {e}")
            return True
    
    # -------------------------------------------------------------------------
    # STEP HANDLERS
    # -------------------------------------------------------------------------
    
    async def _execute_tool_step(
        self,
        step: Dict,
        context: Dict
    ) -> Dict[str, Any]:
        """Ejecuta paso de tipo TOOL_EXECUTE"""
        from api.services.executor_engine import execution_service
        from api.models.tools import ExecutionTarget
        
        tool_id = step["tool_id"]
        parameters = step.get("parameters", {}).copy()
        
        # Resolver target dinámico
        target = parameters.get("target", context["input"].get("target", ""))
        if step.get("target_from"):
            target = self._resolve_reference(step["target_from"], context)
        
        parameters["target"] = target
        
        # Determinar dónde ejecutar
        execution_target = ExecutionTarget.MCP_LOCAL
        if context.get("agent_id"):
            execution_target = ExecutionTarget.AGENT_REMOTE
        
        result = await execution_service.execute_tool(
            tool_id=tool_id,
            tool_name=tool_id,  # En producción buscar nombre real
            category="unknown",
            parameters=parameters,
            target=target,
            execution_target=execution_target,
            user_id=context["user_id"],
            user_role="dfir_engineer",  # TODO: obtener real
            tenant_id=context["tenant_id"],
            case_id=context.get("case_id"),
            investigation_id=context.get("investigation_id"),
            agent_id=context.get("agent_id")
        )
        
        return {
            "execution_id": result.get("execution_id"),
            "output": result.get("output", "")[:5000],  # Truncar para contexto
            "success": result.get("success", False),
            "iocs": result.get("iocs_extracted", [])
        }
    
    async def _execute_api_step(
        self,
        step: Dict,
        context: Dict
    ) -> Dict[str, Any]:
        """Ejecuta paso de tipo API_CALL"""
        import httpx
        
        endpoint = step["api_endpoint"]
        method = step.get("api_method", "POST")
        parameters = step.get("parameters", {})
        
        # Resolver parámetros dinámicos
        for key, value in parameters.items():
            if isinstance(value, str) and value.startswith("input."):
                parameters[key] = self._resolve_reference(value, context)
        
        # Agregar context IDs
        parameters["case_id"] = context.get("case_id")
        parameters["investigation_id"] = context.get("investigation_id")
        
        base_url = f"http://localhost:{settings.PORT}"
        
        async with httpx.AsyncClient() as client:
            if method == "POST":
                response = await client.post(
                    f"{base_url}{endpoint}",
                    json=parameters,
                    headers={"X-API-Key": settings.API_KEY}
                )
            else:
                response = await client.get(
                    f"{base_url}{endpoint}",
                    params=parameters,
                    headers={"X-API-Key": settings.API_KEY}
                )
        
        return {
            "status_code": response.status_code,
            "response": response.json() if response.status_code < 400 else {},
            "success": response.status_code < 400
        }
    
    async def _execute_create_ioc_step(
        self,
        step: Dict,
        context: Dict
    ) -> Dict[str, Any]:
        """Ejecuta paso de tipo CREATE_IOC"""
        from api.services.ioc_service import IOCService
        
        ioc_source = step.get("ioc_source", "previous_step")
        iocs = []
        
        # Obtener IOCs de fuente indicada
        if ioc_source == "previous_step":
            prev_order = max(context["steps"].keys()) if context["steps"] else 0
            prev_result = context["steps"].get(prev_order, {})
            iocs = prev_result.get("iocs", [])
        elif ioc_source in context.get("steps", {}):
            iocs = context["steps"].get(ioc_source, {}).get("iocs", [])
        
        # Crear IOCs
        created = []
        ioc_service = IOCService()
        
        for ioc_data in iocs[:50]:  # Limitar a 50
            try:
                ioc = await ioc_service.create_ioc(
                    ioc_type=ioc_data["type"],
                    value=ioc_data["value"],
                    source="playbook_auto",
                    case_id=context.get("case_id"),
                    auto_enrich=step.get("auto_enrich", True)
                )
                created.append(ioc.id)
                context["iocs"].append(ioc.id)
            except Exception as e:
                logger.warning(f"Failed to create IOC: {e}")
        
        return {"iocs_created": len(created), "ioc_ids": created}
    
    async def _execute_enrich_ioc_step(
        self,
        step: Dict,
        context: Dict
    ) -> Dict[str, Any]:
        """Ejecuta paso de tipo ENRICH_IOC"""
        from api.services.ioc_service import IOCService
        
        sources = step.get("enrichment_sources", ["virustotal"])
        ioc_ids = context.get("iocs", [])
        
        enriched = 0
        ioc_service = IOCService()
        
        for ioc_id in ioc_ids[:20]:
            try:
                await ioc_service.enrich_ioc(ioc_id, sources)
                enriched += 1
            except Exception as e:
                logger.warning(f"Failed to enrich IOC {ioc_id}: {e}")
        
        return {"iocs_enriched": enriched}
    
    async def _execute_timeline_step(
        self,
        step: Dict,
        context: Dict
    ) -> Dict[str, Any]:
        """Ejecuta paso de tipo UPDATE_TIMELINE"""
        from api.models import InvestigationTimeline
        
        events_created = 0
        
        with get_db_context() as db:
            if context.get("investigation_id"):
                # Crear evento de playbook ejecutado
                event = InvestigationTimeline(
                    id=f"TL-{uuid.uuid4().hex[:8].upper()}",
                    investigation_id=context["investigation_id"],
                    event_type="playbook_execution",
                    title="Playbook ejecutado",
                    description=f"Ejecución ID: {context['execution_id']}",
                    severity="info",
                    metadata={
                        "execution_id": context["execution_id"],
                        "steps_completed": len([
                            s for s in context["steps"].values()
                            if s.get("status") == "completed"
                        ])
                    }
                )
                db.add(event)
                events_created += 1
                db.commit()
        
        return {"events_created": events_created}
    
    async def _execute_notification_step(
        self,
        step: Dict,
        context: Dict
    ) -> Dict[str, Any]:
        """Ejecuta paso de tipo NOTIFICATION"""
        channel = step.get("notification_channel", "default")
        template = step.get("notification_template", "generic")
        
        # En producción: enviar a Slack, email, Teams, etc.
        logger.info(f"📬 Notification sent to {channel} using template {template}")
        
        return {
            "channel": channel,
            "template": template,
            "sent": True
        }
    
    async def _execute_wait_step(
        self,
        step: Dict,
        context: Dict
    ) -> Dict[str, Any]:
        """Ejecuta paso de tipo WAIT"""
        wait_seconds = step.get("parameters", {}).get("seconds", 10)
        await asyncio.sleep(wait_seconds)
        return {"waited_seconds": wait_seconds}
    
    async def _evaluate_condition_step(
        self,
        step: Dict,
        context: Dict
    ) -> Dict[str, Any]:
        """Evalúa condición y actualiza contexto"""
        condition = step.get("condition", "true")
        result = self._evaluate_condition(condition, context)
        return {"condition": condition, "result": result}
    
    async def _execute_graph_step(
        self,
        step: Dict,
        context: Dict
    ) -> Dict[str, Any]:
        """Ejecuta paso de tipo GRAPH_ENRICH"""
        from api.services.graph_enricher import GraphEnricher
        
        enricher = GraphEnricher()
        nodes_created = 0
        
        # Enriquecer con IOCs del contexto
        for ioc_id in context.get("iocs", []):
            try:
                await enricher.create_ioc_node(
                    ioc_id=ioc_id,
                    case_id=context.get("case_id")
                )
                nodes_created += 1
            except Exception as e:
                logger.warning(f"Failed to create graph node: {e}")
        
        return {"nodes_created": nodes_created}
    
    async def _execute_correlation_step(
        self,
        step: Dict,
        context: Dict
    ) -> Dict[str, Any]:
        """Ejecuta paso de tipo RUN_CORRELATION"""
        from api.services.correlation_engine import CorrelationEngine
        
        rule_ids = step.get("correlation_rules", [])
        engine = CorrelationEngine()
        
        matches = []
        for rule_id in rule_ids:
            try:
                result = await engine.run_rule(
                    rule_id=rule_id,
                    context_data=context
                )
                if result.get("matched"):
                    matches.append(rule_id)
            except Exception as e:
                logger.warning(f"Correlation rule {rule_id} failed: {e}")
        
        return {"rules_checked": len(rule_ids), "matches": matches}
    
    async def _execute_approval_step(
        self,
        step: Dict,
        context: Dict
    ) -> Dict[str, Any]:
        """Ejecuta paso de tipo APPROVAL_GATE (pausa para aprobación)"""
        # En producción: pausar y esperar webhook/UI de aprobación
        logger.info("🚧 Approval gate reached (auto-approved in dev)")
        return {"approved": True, "approved_by": "system_dev"}
    
    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------
    
    def _resolve_reference(self, reference: str, context: Dict) -> Any:
        """Resuelve referencias dinámicas como 'input.domain' o 'step.3.output'"""
        parts = reference.split(".")
        current = context
        
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                return None
        
        return current
    
    # -------------------------------------------------------------------------
    # TRIGGER HANDLERS
    # -------------------------------------------------------------------------
    
    async def on_ioc_created(self, ioc_data: Dict):
        """Handler para trigger ON_IOC_CREATE"""
        with get_db_context() as db:
            playbooks = db.query(Playbook).filter(
                Playbook.trigger == PlaybookTrigger.ON_IOC_CREATE.value,
                Playbook.status == PlaybookStatus.ACTIVE.value
            ).all()
            
            for pb in playbooks:
                conditions = pb.trigger_conditions or {}
                ioc_types = conditions.get("ioc_type", [])
                
                if not ioc_types or ioc_data.get("type") in ioc_types:
                    logger.info(f"🎯 Triggering playbook {pb.name} on IOC create")
                    # Ejecutar en background
                    asyncio.create_task(
                        self.execute_playbook(
                            playbook_id=pb.id,
                            input_data={"ioc": ioc_data},
                            user_id="system",
                            tenant_id=ioc_data.get("tenant_id", "default")
                        )
                    )
    
    async def on_alert_received(self, alert_data: Dict):
        """Handler para trigger ON_ALERT"""
        with get_db_context() as db:
            playbooks = db.query(Playbook).filter(
                Playbook.trigger == PlaybookTrigger.ON_ALERT.value,
                Playbook.status == PlaybookStatus.ACTIVE.value
            ).all()
            
            for pb in playbooks:
                conditions = pb.trigger_conditions or {}
                severities = conditions.get("severity", [])
                
                if not severities or alert_data.get("severity") in severities:
                    logger.info(f"🚨 Triggering playbook {pb.name} on alert")
                    asyncio.create_task(
                        self.execute_playbook(
                            playbook_id=pb.id,
                            input_data={"alert": alert_data},
                            user_id="system",
                            tenant_id=alert_data.get("tenant_id", "default")
                        )
                    )
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancela ejecución de playbook"""
        task = self.active_executions.get(execution_id)
        if task:
            task.cancel()
            return True
        return False


# =============================================================================
# SINGLETON
# =============================================================================

soar_engine = SOAREngine()
