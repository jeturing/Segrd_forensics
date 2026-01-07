"""
Gestión de casos forenses
"""

from datetime import datetime
from typing import Optional
import uuid
import logging

logger = logging.getLogger(__name__)

# TODO: Reemplazar con implementación de base de datos real
_cases_db = {}

async def create_case(case_data: dict) -> dict:
    """
    Crea un nuevo caso forense
    """
    task_id = str(uuid.uuid4())
    
    case = {
        "task_id": task_id,
        "case_id": case_data["case_id"],
        "type": case_data["type"],
        "status": case_data.get("status", "queued"),
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "metadata": case_data.get("metadata", {}),
        "results": None,
        "summary": None,
        "error": None
    }
    
    _cases_db[case_data["case_id"]] = case
    
    logger.info(f"📋 Caso creado: {case_data['case_id']}")
    return case

async def update_case_status(
    case_id: str,
    status: str,
    results: Optional[dict] = None,
    summary: Optional[dict] = None,
    error: Optional[str] = None,
    metadata: Optional[dict] = None
):
    """
    Actualiza el estado de un caso
    """
    if case_id not in _cases_db:
        logger.error(f"❌ Caso no encontrado: {case_id}")
        return
    
    case = _cases_db[case_id]
    case["status"] = status
    case["updated_at"] = datetime.utcnow().isoformat()
    
    if results:
        case["results"] = results
    if summary:
        case["summary"] = summary
    if error:
        case["error"] = error
    if metadata:
        case.setdefault("metadata", {}).update(metadata)
    if status == "completed":
        case["completed_at"] = datetime.utcnow().isoformat()
    
    logger.info(f"📝 Caso actualizado: {case_id} -> {status}")

async def get_case(case_id: str) -> Optional[dict]:
    """
    Obtiene información de un caso
    """
    return _cases_db.get(case_id)

async def get_case_status_detailed(case_id: str) -> Optional[dict]:
    """
    Obtiene el estado detallado de un caso para el frontend
    """
    case = _cases_db.get(case_id)
    if not case:
        return None
    
    # Calcular progreso basado en herramientas completadas
    metadata = case.get("metadata", {})
    scope = metadata.get("scope", [])
    completed_tools = case.get("completed_tools", [])
    current_tool = case.get("current_tool")
    
    total_tools = len(scope) if scope else 1
    completed_count = len(completed_tools) if completed_tools else 0
    
    if case["status"] == "completed":
        progress = 100
    elif case["status"] == "failed":
        progress = case.get("progress_percentage", 0)
    elif case["status"] == "running":
        progress = min(int((completed_count / total_tools) * 100), 95)
    else:
        progress = 0
    
    # Contar archivos de evidencia
    from pathlib import Path
    from api.config import settings
    evidence_dir = settings.EVIDENCE_DIR / case_id
    evidence_count = 0
    if evidence_dir.exists():
        for root, dirs, files in Path(evidence_dir).walk():
            evidence_count += len(files)
    
    return {
        "case_id": case_id,
        "type": case.get("type", "forensics"),
        "status": case["status"],
        "created_at": case["created_at"],
        "updated_at": case["updated_at"],
        "progress_percentage": progress,
        "current_step": case.get("current_step", f"Ejecutando {current_tool}" if current_tool else None),
        "current_tool": current_tool,
        "completed_tools": completed_tools,
        "scope": scope,
        "estimated_completion": case.get("estimated_completion"),
        "evidence_count": evidence_count,
        "error": case.get("error"),
        "results": case.get("results") if case["status"] == "completed" else None
    }

async def update_case_progress(
    case_id: str,
    current_tool: Optional[str] = None,
    current_step: Optional[str] = None,
    completed_tool: Optional[str] = None,
    progress_percentage: Optional[int] = None
):
    """
    Actualiza el progreso de un caso durante ejecución
    """
    if case_id not in _cases_db:
        return
    
    case = _cases_db[case_id]
    case["updated_at"] = datetime.utcnow().isoformat()
    
    if current_tool:
        case["current_tool"] = current_tool
    if current_step:
        case["current_step"] = current_step
    if progress_percentage is not None:
        case["progress_percentage"] = progress_percentage
    
    if completed_tool:
        if "completed_tools" not in case:
            case["completed_tools"] = []
        if completed_tool not in case["completed_tools"]:
            case["completed_tools"].append(completed_tool)
    
    logger.info(f"📊 Progreso actualizado: {case_id} - {current_step or current_tool}")

