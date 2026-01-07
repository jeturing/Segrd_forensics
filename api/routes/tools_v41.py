"""
MCP v4.1 - Tool Execution Routes
Rutas API para ejecución de herramientas con soporte híbrido.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field
import logging

from api.middleware.auth import verify_api_key
from api.database import get_db_context
from api.models.tools import (
    ToolExecution, ExecutionStatus, ExecutionTarget
)
from api.services.executor_engine import execution_service
from api.services.kali_tools import get_all_tools, get_tool_by_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v41/tools", tags=["Tools v4.1"])


# =============================================================================
# SCHEMAS
# =============================================================================

class ToolExecuteRequest(BaseModel):
    """Request para ejecutar herramienta"""
    tool_id: str = Field(..., description="ID de la herramienta")
    parameters: Dict[str, Any] = Field(default={}, description="Parámetros de la herramienta")
    target: str = Field(..., description="Target de la ejecución (IP, dominio, etc.)")
    execution_target: str = Field(
        default="mcp_local",
        description="Dónde ejecutar: mcp_local o agent_remote"
    )
    agent_id: Optional[str] = Field(None, description="ID del agente (si execution_target=agent_remote)")
    case_id: Optional[str] = Field(None, description="ID del caso asociado")
    investigation_id: Optional[str] = Field(None, description="ID de investigación")
    
    class Config:
        json_schema_extra = {
            "example": {
                "tool_id": "nmap",
                "parameters": {"ports": "1-1000", "scan_type": "SYN"},
                "target": "192.168.1.1",
                "execution_target": "mcp_local",
                "case_id": "CASE-001"
            }
        }


class ToolExecuteResponse(BaseModel):
    """Response de ejecución de herramienta"""
    execution_id: str
    status: str
    message: str
    estimated_duration: Optional[int] = None


class ExecutionStatusResponse(BaseModel):
    """Response de estado de ejecución"""
    execution_id: str
    tool_id: str
    tool_name: str
    status: str
    started_at: Optional[str]
    finished_at: Optional[str]
    duration_seconds: Optional[float]
    exit_code: Optional[int]
    output_preview: Optional[str]
    error_message: Optional[str]
    iocs_extracted: Optional[int]
    graph_nodes_created: Optional[int]


class ExecutionListResponse(BaseModel):
    """Response de lista de ejecuciones"""
    total: int
    executions: List[Dict]


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/catalog", summary="Obtener catálogo de herramientas")
async def get_catalog(
    category: Optional[str] = Query(None, description="Filtrar por categoría"),
    risk_level: Optional[str] = Query(None, description="Filtrar por nivel de riesgo"),
    _: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Obtiene el catálogo completo de herramientas disponibles.
    """
    # Obtener todas las herramientas y organizarlas por categoría
    all_tools = get_all_tools()
    catalog = {}
    for tool in all_tools:
        cat = tool.get("category", "other")
        if cat not in catalog:
            catalog[cat] = []
        catalog[cat].append(tool)
    
    if category:
        catalog = {cat: tools for cat, tools in catalog.items() if cat == category}
    
    if risk_level:
        filtered = {}
        for cat, tools in catalog.items():
            filtered_tools = [t for t in tools if t.get("risk_level") == risk_level]
            if filtered_tools:
                filtered[cat] = filtered_tools
        catalog = filtered
    
    # Contar totales
    total_tools = sum(len(tools) for tools in catalog.values())
    
    return {
        "total_categories": len(catalog),
        "total_tools": total_tools,
        "catalog": catalog
    }


@router.get("/tool/{tool_id}", summary="Obtener detalles de herramienta")
async def get_tool(
    tool_id: str,
    _: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Obtiene detalles de una herramienta específica.
    """
    tool = get_tool_by_id(tool_id)
    
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool {tool_id} not found")
    
    return tool


@router.post("/execute", summary="Ejecutar herramienta")
async def execute_tool(
    request: ToolExecuteRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(verify_api_key)
) -> ToolExecuteResponse:
    """
    Ejecuta una herramienta de forma asíncrona.
    La ejecución se realiza en background y el resultado se puede consultar
    por execution_id.
    """
    # Obtener info de herramienta
    tool = get_tool_by_id(request.tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool {request.tool_id} not found")
    
    # Validar target
    exec_target = ExecutionTarget.MCP_LOCAL
    if request.execution_target == "agent_remote":
        exec_target = ExecutionTarget.AGENT_REMOTE
        if not request.agent_id:
            raise HTTPException(
                status_code=400,
                detail="agent_id required for remote execution"
            )
    
    # Crear ejecución
    try:
        # Ejecutar en background
        async def run_execution():
            try:
                result = await execution_service.execute_tool(
                    tool_id=request.tool_id,
                    tool_name=tool.get("name", request.tool_id),
                    category=tool.get("category", "unknown"),
                    parameters=request.parameters,
                    target=request.target,
                    execution_target=exec_target,
                    user_id=user_id,
                    user_role="dfir_engineer",  # TODO: obtener del token
                    tenant_id="default",  # TODO: obtener del token
                    case_id=request.case_id,
                    investigation_id=request.investigation_id,
                    agent_id=request.agent_id
                )
                logger.info(f"Execution completed: {result.get('execution_id')}")
            except Exception as e:
                logger.error(f"Execution failed: {e}")
        
        # Crear ID para respuesta inmediata
        import uuid
        execution_id = f"EXEC-{uuid.uuid4().hex[:12].upper()}"
        
        background_tasks.add_task(run_execution)
        
        return ToolExecuteResponse(
            execution_id=execution_id,
            status="queued",
            message=f"Tool {request.tool_id} queued for execution",
            estimated_duration=tool.get("estimated_duration", 60)
        )
        
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to queue execution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/queue", summary="Ver cola de ejecuciones pendientes")
async def get_execution_queue(
    _: str = Depends(verify_api_key)
):
    """Obtiene las ejecuciones en cola (status=queued o running)."""
    try:
        with get_db_context() as db:
            from sqlalchemy import or_
            queued = db.query(ToolExecution).filter(
                or_(
                    ToolExecution.status == ExecutionStatus.QUEUED,
                    ToolExecution.status == ExecutionStatus.RUNNING
                )
            ).order_by(ToolExecution.created_at.desc()).limit(50).all()
            
            queue_list = []
            for exec_item in queued:
                queue_list.append({
                    "id": exec_item.id,
                    "tool_id": exec_item.tool_id,
                    "status": exec_item.status.value if exec_item.status else "unknown",
                    "target": exec_item.target,
                    "created_at": exec_item.created_at.isoformat() if exec_item.created_at else None,
                    "case_id": exec_item.case_id
                })
            
            return {"queue": queue_list, "total": len(queue_list), "data_source": "real"}
    except Exception as e:
        logger.warning(f"Queue fetch failed, returning empty: {e}")
        return {"queue": [], "total": 0, "data_source": "demo"}


@router.get("/executions", summary="Listar ejecuciones")
async def list_executions(
    case_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    tool_id: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    _: str = Depends(verify_api_key)
) -> ExecutionListResponse:
    """
    Lista ejecuciones de herramientas con filtros.
    """
    with get_db_context() as db:
        query = db.query(ToolExecution)
        
        if case_id:
            query = query.filter(ToolExecution.case_id == case_id)
        if status:
            query = query.filter(ToolExecution.status == status)
        if tool_id:
            query = query.filter(ToolExecution.tool_id == tool_id)
        
        total = query.count()
        
        executions = query.order_by(
            ToolExecution.created_at.desc()
        ).offset(offset).limit(limit).all()
    
    return ExecutionListResponse(
        total=total,
        executions=[
            {
                "id": e.id,
                "tool_id": e.tool_id,
                "tool_name": e.tool_name,
                "status": e.status,
                "target": e.target,
                "execution_target": e.execution_target,
                "case_id": e.case_id,
                "started_at": e.started_at.isoformat() if e.started_at else None,
                "finished_at": e.finished_at.isoformat() if e.finished_at else None,
                "duration_seconds": e.duration_seconds,
                "executed_by": e.executed_by
            }
            for e in executions
        ]
    )


@router.get("/executions/{execution_id}", summary="Obtener estado de ejecución")
async def get_execution_status(
    execution_id: str,
    include_output: bool = Query(False, description="Incluir output completo"),
    _: str = Depends(verify_api_key)
) -> ExecutionStatusResponse:
    """
    Obtiene el estado detallado de una ejecución.
    """
    with get_db_context() as db:
        execution = db.query(ToolExecution).filter(
            ToolExecution.id == execution_id
        ).first()
        
        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")
        
        # Leer output si se solicita
        output_preview = None
        if include_output and execution.output_file:
            try:
                from pathlib import Path
                output_path = Path(execution.output_file)
                if output_path.exists():
                    content = output_path.read_text()
                    output_preview = content[:10000]  # Limitar a 10KB
            except Exception as e:
                logger.warning(f"Failed to read output: {e}")
    
    return ExecutionStatusResponse(
        execution_id=execution.id,
        tool_id=execution.tool_id,
        tool_name=execution.tool_name,
        status=execution.status,
        started_at=execution.started_at.isoformat() if execution.started_at else None,
        finished_at=execution.finished_at.isoformat() if execution.finished_at else None,
        duration_seconds=execution.duration_seconds,
        exit_code=execution.exit_code,
        output_preview=output_preview,
        error_message=execution.error_message,
        iocs_extracted=len(execution.iocs_extracted or []),
        graph_nodes_created=execution.graph_nodes_created
    )


@router.post("/executions/{execution_id}/cancel", summary="Cancelar ejecución")
async def cancel_execution(
    execution_id: str,
    _: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Cancela una ejecución en progreso.
    """
    from api.services.executor_engine import execution_service
    
    success = await execution_service.executor.cancel_execution(execution_id)
    
    if success:
        with get_db_context() as db:
            execution = db.query(ToolExecution).filter(
                ToolExecution.id == execution_id
            ).first()
            if execution:
                execution.status = ExecutionStatus.CANCELLED.value
                execution.finished_at = datetime.utcnow()
                db.commit()
        
        return {"success": True, "message": "Execution cancelled"}
    else:
        raise HTTPException(
            status_code=404,
            detail="Execution not found or already finished"
        )


@router.get("/executions/{execution_id}/output", summary="Obtener output de ejecución")
async def get_execution_output(
    execution_id: str,
    _: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Obtiene el output completo de una ejecución.
    """
    with get_db_context() as db:
        execution = db.query(ToolExecution).filter(
            ToolExecution.id == execution_id
        ).first()
        
        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")
        
        if execution.status not in [ExecutionStatus.SUCCESS.value, ExecutionStatus.FAILED.value]:
            return {
                "execution_id": execution_id,
                "status": execution.status,
                "output": None,
                "message": "Execution still in progress"
            }
        
        output = ""
        if execution.output_file:
            try:
                from pathlib import Path
                output_path = Path(execution.output_file)
                if output_path.exists():
                    output = output_path.read_text()
            except Exception as e:
                logger.warning(f"Failed to read output: {e}")
    
    return {
        "execution_id": execution_id,
        "tool_id": execution.tool_id,
        "status": execution.status,
        "output": output,
        "output_hash": execution.output_hash,
        "output_size": execution.output_size_bytes,
        "iocs_extracted": execution.iocs_extracted,
        "command_executed": execution.command_executed
    }


@router.get("/executions/{execution_id}/iocs", summary="Obtener IOCs extraídos")
async def get_execution_iocs(
    execution_id: str,
    _: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Obtiene los IOCs extraídos de una ejecución.
    """
    with get_db_context() as db:
        execution = db.query(ToolExecution).filter(
            ToolExecution.id == execution_id
        ).first()
        
        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")
    
    iocs = execution.iocs_extracted or []
    
    # Agrupar por tipo
    grouped = {}
    for ioc in iocs:
        ioc_type = ioc.get("type", "unknown")
        if ioc_type not in grouped:
            grouped[ioc_type] = []
        grouped[ioc_type].append(ioc.get("value"))
    
    return {
        "execution_id": execution_id,
        "total_iocs": len(iocs),
        "iocs": iocs,
        "grouped": grouped
    }


# =============================================================================
# STATS & METRICS
# =============================================================================

@router.get("/stats", summary="Obtener estadísticas de ejecuciones")
async def get_execution_stats(
    days: int = Query(7, le=90),
    _: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Obtiene estadísticas de ejecuciones.
    """
    from datetime import timedelta
    
    with get_db_context() as db:
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        executions = db.query(ToolExecution).filter(
            ToolExecution.created_at >= cutoff
        ).all()
        
        # Calcular estadísticas
        total = len(executions)
        success = len([e for e in executions if e.status == ExecutionStatus.SUCCESS.value])
        failed = len([e for e in executions if e.status == ExecutionStatus.FAILED.value])
        
        # Por herramienta
        by_tool = {}
        for e in executions:
            by_tool[e.tool_id] = by_tool.get(e.tool_id, 0) + 1
        
        # Por categoría
        by_category = {}
        for e in executions:
            by_category[e.category] = by_category.get(e.category, 0) + 1
        
        # Duración promedio
        durations = [e.duration_seconds for e in executions if e.duration_seconds]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        # IOCs extraídos
        total_iocs = sum(len(e.iocs_extracted or []) for e in executions)
    
    return {
        "period_days": days,
        "total_executions": total,
        "successful": success,
        "failed": failed,
        "success_rate": (success / max(total, 1)) * 100,
        "average_duration_seconds": round(avg_duration, 2),
        "total_iocs_extracted": total_iocs,
        "by_tool": dict(sorted(by_tool.items(), key=lambda x: -x[1])[:10]),
        "by_category": by_category
    }
