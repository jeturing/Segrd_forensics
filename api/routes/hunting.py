"""
Threat Hunting Routes
=====================
Endpoints para ejecutar y gestionar queries de threat hunting
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from api.services.hunting import hunting_service, HUNTING_QUERIES

router = APIRouter(tags=["hunting"])


# ==================== ENUMS ====================

class QueryType(str, Enum):
    KQL = "kql"
    GRAPH = "graph"
    OSQUERY = "osquery"
    YARA = "yara"


class HuntCategory(str, Enum):
    INITIAL_ACCESS = "initial_access"
    PERSISTENCE = "persistence"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DEFENSE_EVASION = "defense_evasion"
    CREDENTIAL_ACCESS = "credential_access"
    DISCOVERY = "discovery"
    LATERAL_MOVEMENT = "lateral_movement"
    COLLECTION = "collection"
    EXFILTRATION = "exfiltration"
    COMMAND_CONTROL = "command_control"


# ==================== REQUEST MODELS ====================

class ExecuteHuntRequest(BaseModel):
    """Request para ejecutar un hunt predefinido"""
    hunt_id: str = Field(..., description="ID del hunt query predefinido")
    case_id: str = Field(..., description="ID del caso asociado")
    tenant_id: Optional[str] = Field(None, description="Tenant ID para queries M365")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Parámetros adicionales")
    use_llm_analysis: bool = Field(True, description="Analizar resultados con LLM")


class CustomHuntRequest(BaseModel):
    """Request para ejecutar un hunt personalizado"""
    case_id: str
    query_type: QueryType
    query: str = Field(..., min_length=10)
    name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = None
    tenant_id: Optional[str] = None
    target_hosts: Optional[List[str]] = None
    use_llm_analysis: bool = True


class SaveHuntQueryRequest(BaseModel):
    """Request para guardar una query personalizada"""
    name: str = Field(..., min_length=3, max_length=100)
    description: str
    query_type: QueryType
    query: str
    category: HuntCategory
    severity: str = Field("medium", pattern="^(low|medium|high|critical)$")
    mitre_techniques: Optional[List[str]] = None
    data_sources: Optional[List[str]] = None


# ==================== RESPONSE MODELS ====================

class HuntResultResponse(BaseModel):
    """Respuesta de ejecución de hunt"""
    hunt_id: str
    case_id: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    results_count: int = 0
    findings: List[Dict[str, Any]] = []
    llm_analysis: Optional[str] = None
    recommendations: Optional[List[str]] = None


# ==================== ENDPOINTS ====================

@router.get("/")
async def get_hunting_status():
    """Estado general del servicio de hunting"""
    return {
        "service": "threat_hunting",
        "status": "operational",
        "available_queries": len(HUNTING_QUERIES),
        "categories": [c.value for c in HuntCategory],
        "query_types": [q.value for q in QueryType]
    }


@router.get("/queries")
async def list_hunting_queries(
    category: Optional[HuntCategory] = None,
    severity: Optional[str] = Query(None, pattern="^(low|medium|high|critical)$"),
    query_type: Optional[QueryType] = None
):
    """
    Listar queries de hunting disponibles
    
    - Filtrar por categoría MITRE ATT&CK
    - Filtrar por severidad
    - Filtrar por tipo de query
    """
    queries = []
    
    for query_id, query_data in HUNTING_QUERIES.items():
        # Aplicar filtros
        if category and query_data.get("category") != category.value:
            continue
        if severity and query_data.get("severity") != severity:
            continue
        if query_type and query_data.get("query_type") != query_type.value:
            continue
        
        queries.append({
            "id": query_id,
            "name": query_data["name"],
            "description": query_data["description"],
            "category": query_data["category"],
            "severity": query_data["severity"],
            "mitre": query_data.get("mitre", []),
            "query_type": query_data["query_type"]
        })
    
    return {
        "count": len(queries),
        "queries": queries
    }


@router.get("/queries/{query_id}")
async def get_hunting_query(query_id: str):
    """Obtener detalles de una query específica"""
    if query_id not in HUNTING_QUERIES:
        raise HTTPException(status_code=404, detail=f"Query '{query_id}' no encontrada")
    
    query = HUNTING_QUERIES[query_id]
    return {
        "id": query_id,
        **query
    }


@router.post("/execute")
async def execute_hunt(
    request: ExecuteHuntRequest,
    background_tasks: BackgroundTasks
):
    """
    Ejecutar un hunt query predefinido
    
    v4.4: El hunt se ejecuta vinculado a un caso obligatorio.
    Los resultados y el proceso se trackean en el sistema.
    """
    if request.hunt_id not in HUNTING_QUERIES:
        raise HTTPException(status_code=404, detail=f"Hunt '{request.hunt_id}' no encontrado")
    
    if not request.case_id:
        raise HTTPException(status_code=400, detail="case_id es obligatorio para ejecutar hunts")
    
    query_config = HUNTING_QUERIES[request.hunt_id]
    
    # Generar ID de ejecución
    execution_id = f"hunt-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # v4.4: Ejecutar con case_id obligatorio
    result = await hunting_service.execute_hunt(
        query_id=request.hunt_id,
        case_id=request.case_id,
        tenant_id=request.tenant_id,
        time_range="7d",
        parameters=request.parameters
    )
    
    return {
        "execution_id": execution_id,
        "result_id": result.get("result_id"),
        "process_id": result.get("process_id"),
        "hunt_id": request.hunt_id,
        "case_id": request.case_id,
        "status": result.get("status", "completed"),
        "message": f"Hunt '{query_config['name']}' ejecutado",
        "query_type": query_config["query_type"],
        "severity": query_config["severity"],
        "total_hits": result.get("total_hits", 0),
        "llm_analysis": result.get("llm_analysis")
    }


@router.post("/execute/custom")
async def execute_custom_hunt(
    request: CustomHuntRequest,
    background_tasks: BackgroundTasks
):
    """
    Ejecutar un hunt query personalizado
    
    v4.4: Permite ejecutar queries KQL, Graph, OSQuery o YARA personalizadas
    vinculadas a un caso.
    """
    if not request.case_id:
        raise HTTPException(status_code=400, detail="case_id es obligatorio")
    
    execution_id = f"custom-hunt-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Guardar query temporal para ejecución
    await hunting_service.save_custom_query(
        query_id=execution_id,
        name=request.name,
        description=request.description or "Custom hunting query",
        query_type=request.query_type.value,
        query=request.query,
        category="custom",
        severity="medium"
    )
    
    # v4.4: Ejecutar con case_id
    result = await hunting_service.execute_hunt(
        query_id=execution_id,
        case_id=request.case_id,
        tenant_id=request.tenant_id,
        time_range="7d",
        parameters={"name": request.name, "query": request.query}
    )
    
    return {
        "execution_id": execution_id,
        "result_id": result.get("result_id"),
        "process_id": result.get("process_id"),
        "case_id": request.case_id,
        "status": result.get("status", "completed"),
        "message": f"Custom hunt '{request.name}' ejecutado",
        "query_type": request.query_type.value,
        "total_hits": result.get("total_hits", 0)
    }


@router.get("/results/{case_id}")
async def get_hunt_results(
    case_id: str,
    limit: int = Query(50, ge=1, le=500),
    severity: Optional[str] = Query(None, pattern="^(low|medium|high|critical)$")
):
    """
    Obtener resultados de hunting para un caso
    """
    results = await hunting_service.get_case_results(
        case_id=case_id,
        limit=limit,
        severity_filter=severity
    )
    
    return {
        "case_id": case_id,
        "total_hunts": len(results),
        "results": results
    }


@router.get("/results/{case_id}/{hunt_id}")
async def get_specific_hunt_result(case_id: str, hunt_id: str):
    """Obtener resultado específico de un hunt"""
    result = await hunting_service.get_hunt_result(case_id, hunt_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="Hunt result no encontrado")
    
    return result


@router.post("/queries/save")
async def save_custom_query(request: SaveHuntQueryRequest):
    """
    Guardar una query personalizada para uso futuro
    """
    query_id = request.name.lower().replace(" ", "_")
    
    if query_id in HUNTING_QUERIES:
        raise HTTPException(
            status_code=409, 
            detail=f"Ya existe una query con el nombre '{request.name}'"
        )
    
    saved = await hunting_service.save_custom_query(
        query_id=query_id,
        name=request.name,
        description=request.description,
        query_type=request.query_type.value,
        query=request.query,
        category=request.category.value,
        severity=request.severity,
        mitre=request.mitre_techniques,
        data_sources=request.data_sources
    )
    
    return {
        "saved": True,
        "query_id": query_id,
        "message": f"Query '{request.name}' guardada exitosamente"
    }


@router.get("/categories")
async def get_hunting_categories():
    """Listar categorías de hunting (basadas en MITRE ATT&CK)"""
    categories = {}
    
    for query_id, query_data in HUNTING_QUERIES.items():
        cat = query_data.get("category", "unknown")
        if cat not in categories:
            categories[cat] = {
                "name": cat.replace("_", " ").title(),
                "query_count": 0,
                "queries": []
            }
        categories[cat]["query_count"] += 1
        categories[cat]["queries"].append(query_id)
    
    return {
        "total_categories": len(categories),
        "categories": categories
    }


@router.get("/mitre")
async def get_mitre_coverage():
    """
    Obtener cobertura MITRE ATT&CK de las queries disponibles
    """
    mitre_map = {}
    
    for query_id, query_data in HUNTING_QUERIES.items():
        for technique in query_data.get("mitre", []):
            if technique not in mitre_map:
                mitre_map[technique] = {
                    "technique_id": technique,
                    "queries": []
                }
            mitre_map[technique]["queries"].append({
                "id": query_id,
                "name": query_data["name"],
                "severity": query_data["severity"]
            })
    
    return {
        "techniques_covered": len(mitre_map),
        "coverage": mitre_map
    }


@router.delete("/results/{case_id}/{hunt_id}")
async def delete_hunt_result(case_id: str, hunt_id: str):
    """Eliminar resultado de un hunt"""
    deleted = await hunting_service.delete_hunt_result(case_id, hunt_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Hunt result no encontrado")
    
    return {"deleted": True, "hunt_id": hunt_id}


@router.post("/batch")
async def execute_batch_hunts(
    case_id: str,
    hunt_ids: List[str],
    tenant_id: Optional[str] = None,
    background_tasks: BackgroundTasks = None
):
    """
    Ejecutar múltiples hunts en batch
    """
    valid_hunts = []
    invalid_hunts = []
    
    for hunt_id in hunt_ids:
        if hunt_id in HUNTING_QUERIES:
            valid_hunts.append(hunt_id)
        else:
            invalid_hunts.append(hunt_id)
    
    if not valid_hunts:
        raise HTTPException(status_code=400, detail="Ningún hunt válido especificado")
    
    # Ejecutar cada hunt válido
    for hunt_id in valid_hunts:
        background_tasks.add_task(
            hunting_service.execute_hunt,
            query_id=hunt_id,
            tenant_id=tenant_id,
            time_range="7d"
        )
    
    return {
        "batch_id": f"batch-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "case_id": case_id,
        "queued_hunts": valid_hunts,
        "invalid_hunts": invalid_hunts,
        "status": "queued"
    }
