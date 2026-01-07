"""
MCP v4.1 - Playbook Routes
Rutas API para gestión y ejecución de playbooks SOAR.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field
import logging

from api.middleware.auth import verify_api_key
from api.database import get_db_context
from api.models.tools import (
    Playbook, PlaybookExecution, PlaybookStatus
)
from api.services.soar_engine import soar_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v41/playbooks", tags=["Playbooks v4.1"])


# =============================================================================
# SCHEMAS
# =============================================================================

class PlaybookListItem(BaseModel):
    id: str
    name: str
    description: str
    team_type: str
    category: str
    tags: List[str]
    trigger: str
    requires_approval: bool
    estimated_minutes: int
    execution_count: int
    success_rate: float


class PlaybookDetail(PlaybookListItem):
    steps: List[Dict]
    trigger_conditions: Optional[Dict]
    schedule_cron: Optional[str]
    approval_roles: List[str]
    is_builtin: bool
    created_at: str
    last_executed_at: Optional[str]


class ExecutePlaybookRequest(BaseModel):
    """Request para ejecutar playbook"""
    input_data: Dict[str, Any] = Field(
        default={},
        description="Datos de entrada (target, domain, etc.)"
    )
    case_id: Optional[str] = Field(None, description="ID del caso")
    investigation_id: Optional[str] = Field(None, description="ID de investigación")
    agent_id: Optional[str] = Field(None, description="Agente remoto")
    approval_user_id: Optional[str] = Field(None, description="Usuario que aprueba")
    
    class Config:
        json_schema_extra = {
            "example": {
                "input_data": {"target": "user@empresa.com", "domain": "empresa.com"},
                "case_id": "CASE-001"
            }
        }


class PlaybookExecutionResponse(BaseModel):
    execution_id: str
    status: str
    message: Optional[str]
    steps_completed: Optional[int]
    steps_failed: Optional[int]


class CreatePlaybookRequest(BaseModel):
    """Request para crear playbook custom"""
    name: str
    description: str
    team_type: str = Field(..., description="blue, red, purple")
    category: str
    tags: List[str] = []
    trigger: str = Field(default="manual")
    trigger_conditions: Optional[Dict] = None
    schedule_cron: Optional[str] = None
    requires_approval: bool = False
    approval_roles: List[str] = []
    estimated_duration_minutes: int = 30
    steps: List[Dict] = Field(..., description="Lista de pasos del playbook")

class PlaybookRecommendation(BaseModel):
    playbook_id: str
    name: str
    score: float
    reason: str

class PredictionRequest(BaseModel):
    playbook_id: str
    case_type: str
    severity: str
    entity_count: int

class PredictionResponse(BaseModel):
    success_probability: float
    risk_level: str
    factors: List[str]

# =============================================================================
# PLAYBOOK MANAGEMENT
# =============================================================================

@router.get("/recommendations", response_model=List[PlaybookRecommendation])
async def get_recommendations(
    case_type: str,
    severity: str = "medium",
    entities: str = "", # comma separated
    _=Depends(verify_api_key)
):
    """
    Get AI-powered playbook recommendations
    """
    try:
        entity_list = entities.split(",") if entities else []
        recs = soar_engine.get_playbook_recommendations(
            case_context={"type": case_type, "severity": severity, "entities": entity_list}
        )
        return [
            PlaybookRecommendation(
                playbook_id=r["playbook_id"],
                name=r["name"],
                score=r["score"],
                reason=r["reason"]
            ) for r in recs
        ]
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        return []

@router.post("/predict", response_model=PredictionResponse)
async def predict_success(
    request: PredictionRequest,
    _=Depends(verify_api_key)
):
    """
    Predict playbook success probability
    """
    try:
        result = soar_engine.predict_playbook_success(
            request.playbook_id,
            {"type": request.case_type, "severity": request.severity, "entities": ["dummy"] * request.entity_count}
        )
        return PredictionResponse(
            success_probability=result["probability"],
            risk_level=result["risk_level"],
            factors=result["factors"]
        )
    except Exception as e:
        logger.error(f"Error predicting success: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("", summary="Listar playbooks")
async def list_playbooks(
    team_type: Optional[str] = Query(None, description="Filtrar: blue, red, purple"),
    category: Optional[str] = Query(None),
    _: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Lista todos los playbooks disponibles.
    """
    playbooks = soar_engine.get_available_playbooks(
        team_type=team_type,
        category=category
    )
    
    # Agrupar por equipo
    by_team = {"blue": [], "red": [], "purple": []}
    for pb in playbooks:
        team = pb.get("team_type", "blue")
        if team in by_team:
            by_team[team].append(pb)
    
    return {
        "total": len(playbooks),
        "by_team": by_team,
        "playbooks": playbooks
    }


@router.get("/{playbook_id}", summary="Obtener playbook")
async def get_playbook(
    playbook_id: str,
    _: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Obtiene detalles de un playbook específico.
    """
    with get_db_context() as db:
        playbook = db.query(Playbook).filter(
            Playbook.id == playbook_id
        ).first()
        
        if not playbook:
            raise HTTPException(status_code=404, detail="Playbook not found")
        
        steps = db.query(PlaybookStep).filter(
            PlaybookStep.playbook_id == playbook_id
        ).order_by(PlaybookStep.order).all()
    
    return {
        "id": playbook.id,
        "name": playbook.name,
        "description": playbook.description,
        "team_type": playbook.team_type,
        "category": playbook.category,
        "tags": playbook.tags,
        "trigger": playbook.trigger,
        "trigger_conditions": playbook.trigger_conditions,
        "schedule_cron": playbook.schedule_cron,
        "requires_approval": playbook.requires_approval,
        "approval_roles": playbook.approval_roles,
        "estimated_minutes": playbook.estimated_duration_minutes,
        "is_builtin": playbook.is_builtin,
        "status": playbook.status,
        "execution_count": playbook.execution_count,
        "success_rate": playbook.success_rate,
        "created_at": playbook.created_at.isoformat(),
        "last_executed_at": playbook.last_executed_at.isoformat() if playbook.last_executed_at else None,
        "steps": [
            {
                "id": s.id,
                "order": s.order,
                "name": s.name,
                "description": s.description,
                "action_type": s.action_type,
                "tool_id": s.tool_id,
                "api_endpoint": s.api_endpoint,
                "parameters": s.parameters,
                "condition": s.condition,
                "timeout_seconds": s.timeout_seconds,
                "continue_on_error": s.continue_on_error,
                "requires_approval": s.requires_approval
            }
            for s in steps
        ]
    }


@router.post("", summary="Crear playbook")
async def create_playbook(
    request: CreatePlaybookRequest,
    user_id: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Crea un playbook personalizado.
    """
    import uuid
    
    playbook_id = f"PB-CUSTOM-{uuid.uuid4().hex[:6].upper()}"
    
    with get_db_context() as db:
        playbook = Playbook(
            id=playbook_id,
            name=request.name,
            description=request.description,
            team_type=request.team_type,
            category=request.category,
            tags=request.tags,
            trigger=request.trigger,
            trigger_conditions=request.trigger_conditions,
            schedule_cron=request.schedule_cron,
            requires_approval=request.requires_approval,
            approval_roles=request.approval_roles,
            status=PlaybookStatus.DRAFT.value,
            is_builtin=False,
            estimated_duration_minutes=request.estimated_duration_minutes,
            created_by=user_id
        )
        db.add(playbook)
        
        # Agregar pasos
        for i, step_data in enumerate(request.steps, 1):
            step = PlaybookStep(
                id=f"{playbook_id}-S{i:02d}",
                playbook_id=playbook_id,
                order=i,
                name=step_data.get("name", f"Step {i}"),
                description=step_data.get("description"),
                action_type=step_data.get("action_type", "tool_execute"),
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
        
        db.commit()
    
    logger.info(f"📚 Created custom playbook: {playbook_id}")
    
    return {
        "id": playbook_id,
        "name": request.name,
        "status": "draft",
        "message": "Playbook created. Activate with PATCH /{id}/activate"
    }


@router.patch("/{playbook_id}/activate", summary="Activar playbook")
async def activate_playbook(
    playbook_id: str,
    _: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Activa un playbook en draft.
    """
    with get_db_context() as db:
        playbook = db.query(Playbook).filter(
            Playbook.id == playbook_id
        ).first()
        
        if not playbook:
            raise HTTPException(status_code=404, detail="Playbook not found")
        
        playbook.status = PlaybookStatus.ACTIVE.value
        db.commit()
    
    return {"success": True, "status": "active"}


@router.patch("/{playbook_id}/disable", summary="Desactivar playbook")
async def disable_playbook(
    playbook_id: str,
    _: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Desactiva un playbook.
    """
    with get_db_context() as db:
        playbook = db.query(Playbook).filter(
            Playbook.id == playbook_id
        ).first()
        
        if not playbook:
            raise HTTPException(status_code=404, detail="Playbook not found")
        
        playbook.status = PlaybookStatus.DISABLED.value
        db.commit()
    
    return {"success": True, "status": "disabled"}


@router.delete("/{playbook_id}", summary="Eliminar playbook")
async def delete_playbook(
    playbook_id: str,
    _: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Elimina un playbook (solo custom, no builtin).
    """
    with get_db_context() as db:
        playbook = db.query(Playbook).filter(
            Playbook.id == playbook_id
        ).first()
        
        if not playbook:
            raise HTTPException(status_code=404, detail="Playbook not found")
        
        if playbook.is_builtin:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete builtin playbooks"
            )
        
        # Eliminar pasos
        db.query(PlaybookStep).filter(
            PlaybookStep.playbook_id == playbook_id
        ).delete()
        
        db.delete(playbook)
        db.commit()
    
    return {"success": True, "message": "Playbook deleted"}


# =============================================================================
# PLAYBOOK EXECUTION
# =============================================================================

@router.post("/{playbook_id}/execute", summary="Ejecutar playbook")
async def execute_playbook(
    playbook_id: str,
    request: ExecutePlaybookRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(verify_api_key)
) -> PlaybookExecutionResponse:
    """
    Ejecuta un playbook.
    La ejecución se realiza en background.
    """
    # Verificar que existe
    with get_db_context() as db:
        playbook = db.query(Playbook).filter(
            Playbook.id == playbook_id,
            Playbook.status == PlaybookStatus.ACTIVE.value
        ).first()
        
        if not playbook:
            raise HTTPException(
                status_code=404,
                detail="Playbook not found or not active"
            )
    
    # Ejecutar en background
    async def run_playbook():
        try:
            result = await soar_engine.execute_playbook(
                playbook_id=playbook_id,
                input_data=request.input_data,
                user_id=user_id,
                tenant_id="default",
                case_id=request.case_id,
                investigation_id=request.investigation_id,
                agent_id=request.agent_id,
                approval_user_id=request.approval_user_id
            )
            logger.info(f"Playbook execution completed: {result}")
        except Exception as e:
            logger.error(f"Playbook execution failed: {e}")
    
    background_tasks.add_task(run_playbook)
    
    import uuid
    exec_id = f"PBEXEC-{uuid.uuid4().hex[:12].upper()}"
    
    return PlaybookExecutionResponse(
        execution_id=exec_id,
        status="queued",
        message=f"Playbook {playbook_id} queued for execution"
    )


@router.get("/executions", summary="Listar ejecuciones")
async def list_executions(
    playbook_id: Optional[str] = Query(None),
    case_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    _: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Lista ejecuciones de playbooks.
    """
    with get_db_context() as db:
        query = db.query(PlaybookExecution)
        
        if playbook_id:
            query = query.filter(PlaybookExecution.playbook_id == playbook_id)
        if case_id:
            query = query.filter(PlaybookExecution.case_id == case_id)
        if status:
            query = query.filter(PlaybookExecution.status == status)
        
        executions = query.order_by(
            PlaybookExecution.created_at.desc()
        ).limit(limit).all()
    
    return {
        "total": len(executions),
        "executions": [
            {
                "id": e.id,
                "playbook_id": e.playbook_id,
                "status": e.status,
                "case_id": e.case_id,
                "total_steps": e.total_steps,
                "completed_steps": e.completed_steps,
                "failed_steps": e.failed_steps,
                "started_at": e.started_at.isoformat() if e.started_at else None,
                "finished_at": e.finished_at.isoformat() if e.finished_at else None,
                "executed_by": e.executed_by
            }
            for e in executions
        ]
    }


@router.get("/executions/{execution_id}", summary="Obtener ejecución")
async def get_execution(
    execution_id: str,
    _: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Obtiene detalles de una ejecución de playbook.
    """
    from api.models.tools import PlaybookStepExecution
    
    with get_db_context() as db:
        execution = db.query(PlaybookExecution).filter(
            PlaybookExecution.id == execution_id
        ).first()
        
        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")
        
        step_executions = db.query(PlaybookStepExecution).filter(
            PlaybookStepExecution.playbook_execution_id == execution_id
        ).order_by(PlaybookStepExecution.step_order).all()
    
    return {
        "id": execution.id,
        "playbook_id": execution.playbook_id,
        "status": execution.status,
        "input_data": execution.input_data,
        "output_data": execution.output_data,
        "total_steps": execution.total_steps,
        "current_step": execution.current_step,
        "completed_steps": execution.completed_steps,
        "failed_steps": execution.failed_steps,
        "skipped_steps": execution.skipped_steps,
        "case_id": execution.case_id,
        "investigation_id": execution.investigation_id,
        "started_at": execution.started_at.isoformat() if execution.started_at else None,
        "finished_at": execution.finished_at.isoformat() if execution.finished_at else None,
        "executed_by": execution.executed_by,
        "steps": [
            {
                "id": s.id,
                "step_order": s.step_order,
                "status": s.status,
                "output": s.output,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "finished_at": s.finished_at.isoformat() if s.finished_at else None
            }
            for s in step_executions
        ]
    }


@router.post("/executions/{execution_id}/cancel", summary="Cancelar ejecución")
async def cancel_execution(
    execution_id: str,
    _: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Cancela una ejecución en progreso.
    """
    success = await soar_engine.cancel_execution(execution_id)
    
    if success:
        return {"success": True, "message": "Execution cancelled"}
    else:
        raise HTTPException(
            status_code=404,
            detail="Execution not found or already finished"
        )


# =============================================================================
# STATS
# =============================================================================

@router.get("/stats/summary", summary="Estadísticas de playbooks")
async def get_playbook_stats(
    days: int = Query(30, le=90),
    _: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Obtiene estadísticas de ejecución de playbooks.
    """
    from datetime import timedelta
    
    with get_db_context() as db:
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        playbooks = db.query(Playbook).all()
        executions = db.query(PlaybookExecution).filter(
            PlaybookExecution.created_at >= cutoff
        ).all()
        
        # Por equipo
        by_team = {}
        for pb in playbooks:
            by_team[pb.team_type] = by_team.get(pb.team_type, 0) + 1
        
        # Por estado de ejecución
        by_status = {}
        for e in executions:
            by_status[e.status] = by_status.get(e.status, 0) + 1
        
        # Más ejecutados
        exec_count = {}
        for e in executions:
            exec_count[e.playbook_id] = exec_count.get(e.playbook_id, 0) + 1
        
        top_executed = sorted(
            exec_count.items(),
            key=lambda x: -x[1]
        )[:5]
    
    return {
        "period_days": days,
        "total_playbooks": len(playbooks),
        "total_executions": len(executions),
        "by_team": by_team,
        "by_status": by_status,
        "top_executed": [
            {"playbook_id": pb_id, "count": count}
            for pb_id, count in top_executed
        ]
    }
