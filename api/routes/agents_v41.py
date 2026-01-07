"""
🖥️ Agents Routes v4.1 - Real Data with Demo Fallback
Endpoints para gestión de agentes Red/Blue/Purple usando datos reales de DB.
Fallback a datos demo cuando la DB está vacía.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from api.database import get_async_db_context
from api.models.tools import Agent, AgentTask, AgentType, AgentStatus
from api.services.agent_manager import agent_manager
from api.config import settings
from api.config_data.demo_data import get_demo_agents, COMMAND_TEMPLATES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v41/agents", tags=["Agents v4.1"])

# ============================================================================
# SCHEMAS
# ============================================================================

class AgentInfo(BaseModel):
    """Información de agente"""
    id: str
    name: str
    agent_type: str
    status: str
    hostname: Optional[str] = None
    ip_address: Optional[str] = None
    platform: Optional[str] = None
    os_version: Optional[str] = None
    agent_version: Optional[str] = None
    last_seen: Optional[str] = None
    capabilities: Optional[List[str]] = None
    is_demo: bool = False

class AgentRegisterRequest(BaseModel):
    """Solicitud de registro de agente"""
    name: str
    agent_type: str  # blue, red, purple, generic
    hostname: str
    ip_address: str
    platform: str = "linux"
    os_version: Optional[str] = None
    capabilities: Optional[List[str]] = None

class TaskDispatchRequest(BaseModel):
    """Solicitud de despacho de tarea"""
    tool: str
    parameters: Dict[str, Any] = {}
    case_id: Optional[str] = None
    investigation_id: Optional[str] = None
    priority: str = "normal"


class AutoInvestigationRequest(BaseModel):
    """Solicitud de investigación automatizada"""
    investigation_type: str = "full"  # full, quick, targeted
    iocs: List[str] = []  # Lista de IOCs a investigar
    nodes: List[Dict[str, Any]] = []  # Nodos del grafo a investigar
    target_agent: Optional[str] = None  # ID de agente específico o None para auto-selección
    tools: List[str] = []  # Herramientas específicas o vacío para auto-selección
    case_id: Optional[str] = None
    investigation_id: Optional[str] = None
    priority: str = "normal"  # low, normal, high, critical
    timeout_minutes: int = 30


class CommandTemplatesRequest(BaseModel):
    """Solicitud de templates de comandos"""
    os_type: str = "linux"

# ============================================================================
# AGENT TYPES CONFIGURATION (Static, not mock)
# ============================================================================

AGENT_TYPES_CONFIG = {
    "blue": {
        "name": "Blue Agent",
        "description": "Defensive agent for DFIR and threat hunting",
        "capabilities": ["osquery", "yara_scan", "loki_scan", "memory_forensics", "log_collection"],
        "tools": ["osquery", "yara", "loki", "volatility", "tcpdump"]
    },
    "red": {
        "name": "Red Agent",
        "description": "Offensive agent for reconnaissance and assessment",
        "capabilities": ["nmap", "whatweb", "gobuster", "nikto", "passive_recon"],
        "tools": ["nmap", "whatweb", "gobuster", "nikto", "amass", "nuclei"]
    },
    "purple": {
        "name": "Purple Agent",
        "description": "Coordination agent for validation and tuning",
        "capabilities": ["validation", "correlation", "tuning", "sync_cycle"],
        "tools": []
    },
    "generic": {
        "name": "Generic Agent",
        "description": "General purpose agent",
        "capabilities": ["command_execution", "file_collection"],
        "tools": []
    }
}

# ============================================================================
# ENDPOINTS - Real Data with Demo Fallback
# ============================================================================

@router.get("/", summary="Listar todos los agentes")
async def list_agents(
    status: Optional[str] = None,
    agent_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    📋 Listar todos los agentes conectados (datos reales o demo)
    
    Query Parameters:
    - status: Filtrar por estado (online, offline, busy)
    - agent_type: Filtrar por tipo (blue, red, purple, generic)
    
    Response incluye `data_source: "real"` o `"demo"` para indicar origen.
    """
    try:
        # Intentar obtener agentes reales de la DB
        async with get_async_db_context() as db:
            query = db.query(Agent)
            
            if status:
                query = query.filter(Agent.status == status)
            if agent_type:
                query = query.filter(Agent.agent_type == agent_type)
            
            db_agents = query.all()
        
        if db_agents:
            # Datos reales encontrados
            agents = [
                {
                    "id": a.id,
                    "name": a.name,
                    "agent_type": a.agent_type,
                    "status": a.status,
                    "hostname": a.hostname,
                    "ip_address": a.ip_address,
                    "platform": getattr(a, 'platform', 'unknown'),
                    "os_version": getattr(a, 'os_version', None),
                    "agent_version": getattr(a, 'agent_version', None),
                    "last_seen": a.last_seen.isoformat() if a.last_seen else None,
                    "capabilities": a.capabilities or [],
                    "is_demo": False
                }
                for a in db_agents
            ]
            data_source = "real"
            logger.info(f"📋 Retornando {len(agents)} agentes reales")
        else:
            if settings.DEMO_DATA_ENABLED:
                # Fallback a demo data solo si está habilitado
                agents = get_demo_agents()
                
                if status:
                    agents = [a for a in agents if a["status"] == status]
                if agent_type:
                    agents = [a for a in agents if a["agent_type"] == agent_type]
                
                data_source = "demo"
                logger.info(f"📋 Retornando {len(agents)} agentes de demo (DB vacía)")
            else:
                agents = []
                data_source = "empty"
                logger.info("📋 Sin agentes reales y fallback demo deshabilitado")
        
        return {
            "total": len(agents),
            "agents": agents,
            "data_source": data_source
        }
    
    except Exception as e:
        logger.error(f"❌ Error al listar agentes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/types", summary="Obtener tipos de agentes disponibles")
async def get_agent_types() -> Dict[str, Any]:
    """
    📊 Obtener configuración de tipos de agentes
    """
    return {
        "types": AGENT_TYPES_CONFIG,
        "data_source": "config"  # Siempre es configuración, no mock
    }


@router.get("/{agent_id}", summary="Obtener detalles de agente")
async def get_agent(agent_id: str) -> Dict[str, Any]:
    """
    🔍 Obtener detalles de un agente específico
    """
    try:
        # Buscar en DB real
        async with get_async_db_context() as db:
            agent = db.query(Agent).filter(Agent.id == agent_id).first()
        
        if agent:
            return {
                "agent": {
                    "id": agent.id,
                    "name": agent.name,
                    "agent_type": agent.agent_type,
                    "status": agent.status,
                    "hostname": agent.hostname,
                    "ip_address": agent.ip_address,
                    "last_seen": agent.last_seen.isoformat() if agent.last_seen else None,
                    "capabilities": agent.capabilities or [],
                    "is_demo": False
                },
                "data_source": "real"
            }
        
        # Buscar en demo data solo si está habilitado
        if settings.DEMO_DATA_ENABLED:
            demo_agents = get_demo_agents()
            for demo_agent in demo_agents:
                if demo_agent["id"] == agent_id:
                    return {
                        "agent": demo_agent,
                        "data_source": "demo"
                    }
        
        raise HTTPException(status_code=404, detail=f"Agente {agent_id} no encontrado")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error al obtener agente {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/register", summary="Registrar nuevo agente")
async def register_agent(request: AgentRegisterRequest) -> Dict[str, Any]:
    """
    🚀 Registrar un nuevo agente en el sistema
    
    Este endpoint registra agentes REALES en la base de datos.
    No usa datos demo.
    """
    try:
        # Validar tipo de agente
        if request.agent_type not in AGENT_TYPES_CONFIG:
            raise HTTPException(
                status_code=400,
                detail=f"Tipo de agente inválido: {request.agent_type}"
            )
        
        # Usar AgentManager para registro real
        result = await agent_manager.register_agent(
            name=request.name,
            agent_type=AgentType(request.agent_type),
            hostname=request.hostname,
            ip_address=request.ip_address,
            capabilities=request.capabilities or AGENT_TYPES_CONFIG[request.agent_type]["capabilities"]
        )
        
        logger.info(f"🚀 Agente registrado: {result['agent_id']}")
        
        return {
            "success": True,
            "agent_id": result["agent_id"],
            "message": f"Agente {request.name} registrado exitosamente",
            "data_source": "real"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error al registrar agente: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{agent_id}/task", summary="Despachar tarea a agente")
async def dispatch_task(
    agent_id: str,
    request: TaskDispatchRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    📤 Despachar una tarea a un agente específico
    
    Crea una tarea real en la cola del agente.
    """
    try:
        # Verificar que el agente existe
        async with get_async_db_context() as db:
            agent = db.query(Agent).filter(Agent.id == agent_id).first()
        
        if not agent:
            # Check demo agents solo si está habilitado
            if settings.DEMO_DATA_ENABLED:
                demo_agents = get_demo_agents()
                demo_agent = next((a for a in demo_agents if a["id"] == agent_id), None)
                
                if demo_agent:
                    return {
                        "success": False,
                        "message": "No se pueden despachar tareas a agentes demo",
                        "data_source": "demo"
                    }
            
            raise HTTPException(status_code=404, detail=f"Agente {agent_id} no encontrado")
        
        # Crear tarea real
        task = await agent_manager.dispatch_task(
            agent_id=agent_id,
            tool=request.tool,
            parameters=request.parameters,
            case_id=request.case_id,
            investigation_id=request.investigation_id,
            priority=request.priority
        )
        
        logger.info(f"📤 Tarea {task['task_id']} despachada a {agent_id}")
        
        return {
            "success": True,
            "task_id": task["task_id"],
            "agent_id": agent_id,
            "status": "queued",
            "data_source": "real"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error al despachar tarea: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{agent_id}/tasks", summary="Listar tareas de agente")
async def get_agent_tasks(
    agent_id: str,
    status: Optional[str] = None
) -> Dict[str, Any]:
    """
    📋 Listar tareas de un agente
    """
    try:
        async with get_async_db_context() as db:
            query = db.query(AgentTask).filter(AgentTask.agent_id == agent_id)
            
            if status:
                query = query.filter(AgentTask.status == status)
            
            tasks = query.order_by(AgentTask.created_at.desc()).limit(50).all()
        
        return {
            "agent_id": agent_id,
            "total": len(tasks),
            "tasks": [
                {
                    "id": t.id,
                    "tool": t.tool,
                    "parameters": t.parameters,
                    "status": t.status,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                    "completed_at": t.completed_at.isoformat() if t.completed_at else None
                }
                for t in tasks
            ],
            "data_source": "real" if tasks else "empty"
        }
    
    except Exception as e:
        logger.error(f"❌ Error al listar tareas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/commands/templates", summary="Obtener templates de comandos")
async def get_command_templates(
    os_type: str = "linux"
) -> Dict[str, Any]:
    """
    📚 Obtener templates de comandos forenses por OS
    
    Estos NO son datos mock - son templates útiles para comandos forenses.
    """
    if os_type not in COMMAND_TEMPLATES:
        os_type = "linux"
    
    return {
        "os_type": os_type,
        "templates": COMMAND_TEMPLATES[os_type],
        "data_source": "config"  # Templates son configuración, no mock
    }


@router.get("/stats", summary="Estadísticas de agentes")
async def get_agent_stats() -> Dict[str, Any]:
    """
    📊 Obtener estadísticas de agentes
    """
    try:
        async with get_async_db_context() as db:
            total = db.query(Agent).count()
            online = db.query(Agent).filter(Agent.status == "online").count()
            offline = db.query(Agent).filter(Agent.status == "offline").count()
            busy = db.query(Agent).filter(Agent.status == "busy").count()
            
            by_type = {}
            for agent_type in ["blue", "red", "purple", "generic"]:
                by_type[agent_type] = db.query(Agent).filter(Agent.agent_type == agent_type).count()
        
        if total > 0:
            return {
                "total": total,
                "online": online,
                "offline": offline,
                "busy": busy,
                "by_type": by_type,
                "data_source": "real"
            }
        else:
            if settings.DEMO_DATA_ENABLED:
                # Demo stats
                demo_agents = get_demo_agents()
                return {
                    "total": len(demo_agents),
                    "online": len([a for a in demo_agents if a["status"] == "online"]),
                    "offline": len([a for a in demo_agents if a["status"] == "offline"]),
                    "busy": 0,
                    "by_type": {
                        "blue": len([a for a in demo_agents if a["agent_type"] == "blue"]),
                        "red": len([a for a in demo_agents if a["agent_type"] == "red"]),
                        "purple": len([a for a in demo_agents if a["agent_type"] == "purple"]),
                        "generic": 0
                    },
                    "data_source": "demo"
                }
            
            return {
                "total": 0,
                "online": 0,
                "offline": 0,
                "busy": 0,
                "by_type": {
                    "blue": 0,
                    "red": 0,
                    "purple": 0,
                    "generic": 0
                },
                "data_source": "empty"
            }
    
    except Exception as e:
        logger.error(f"❌ Error al obtener stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{agent_id}", summary="Eliminar agente")
async def delete_agent(agent_id: str) -> Dict[str, Any]:
    """
    🗑️ Eliminar un agente del sistema
    """
    try:
        async with get_async_db_context() as db:
            agent = db.query(Agent).filter(Agent.id == agent_id).first()
            
            if not agent:
                raise HTTPException(status_code=404, detail=f"Agente {agent_id} no encontrado")
            
            db.delete(agent)
            db.commit()
        
        logger.info(f"🗑️ Agente {agent_id} eliminado")
        
        return {
            "success": True,
            "message": f"Agente {agent_id} eliminado",
            "data_source": "real"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error al eliminar agente: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# AUTOMATED INVESTIGATION ENDPOINTS
# ============================================================================

# Mapeo de tipos de IOC a herramientas recomendadas
IOC_TOOL_MAPPING = {
    "ip": ["nmap", "whois", "ping", "traceroute", "tcpdump"],
    "domain": ["whois", "dig", "nslookup", "theHarvester", "amass"],
    "url": ["curl", "wget", "nikto", "whatweb"],
    "hash": ["yara_scan", "hashid", "strings"],
    "email": ["theHarvester", "sherlock"],
    "file": ["yara_scan", "strings", "file", "exiftool", "binwalk"],
    "user": ["osquery", "enum4linux", "ldapsearch"],
    "process": ["osquery", "volatility"],
    "registry": ["osquery"],
}

# Herramientas por tipo de investigación
INVESTIGATION_PROFILES = {
    "quick": {
        "description": "Investigación rápida - solo herramientas básicas",
        "tools": ["whois", "dig", "ping", "curl"],
        "timeout": 5
    },
    "full": {
        "description": "Investigación completa - todas las herramientas relevantes",
        "tools": None,  # Todas las disponibles para el IOC
        "timeout": 30
    },
    "targeted": {
        "description": "Investigación dirigida - herramientas específicas del usuario",
        "tools": None,  # Usar las especificadas por el usuario
        "timeout": 15
    }
}


@router.post("/investigate", summary="Iniciar investigación automatizada")
async def start_automated_investigation(
    request: AutoInvestigationRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    🔍 Iniciar una investigación automatizada con agentes
    
    Esta función:
    1. Analiza los IOCs proporcionados
    2. Selecciona las herramientas apropiadas
    3. Asigna la tarea al agente más adecuado
    4. Ejecuta las herramientas en paralelo o secuencia
    5. Recopila y correlaciona los resultados
    """
    try:
        investigation_id = f"AUTOINV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Clasificar IOCs por tipo
        classified_iocs = classify_iocs(request.iocs)
        
        # Determinar herramientas a usar
        tools_to_run = []
        if request.investigation_type == "targeted" and request.tools:
            tools_to_run = request.tools
        else:
            for ioc_type, iocs in classified_iocs.items():
                if iocs and ioc_type in IOC_TOOL_MAPPING:
                    profile = INVESTIGATION_PROFILES.get(request.investigation_type, INVESTIGATION_PROFILES["full"])
                    if profile["tools"]:
                        tools_to_run.extend([t for t in profile["tools"] if t in IOC_TOOL_MAPPING.get(ioc_type, [])])
                    else:
                        tools_to_run.extend(IOC_TOOL_MAPPING[ioc_type])
        
        # Eliminar duplicados manteniendo orden
        tools_to_run = list(dict.fromkeys(tools_to_run))
        
        # Seleccionar agente
        selected_agent = request.target_agent
        if not selected_agent:
            selected_agent = await select_best_agent(classified_iocs)
        
        # Crear tareas para cada herramienta
        tasks_created = []
        for tool in tools_to_run:
            for ioc_type, iocs in classified_iocs.items():
                if tool in IOC_TOOL_MAPPING.get(ioc_type, []):
                    for ioc in iocs:
                        task_id = f"TASK-{datetime.now().strftime('%Y%m%d%H%M%S%f')[:17]}"
                        tasks_created.append({
                            "task_id": task_id,
                            "tool": tool,
                            "target": ioc,
                            "ioc_type": ioc_type,
                            "agent_id": selected_agent,
                            "status": "queued"
                        })
        
        # Iniciar ejecución en background
        background_tasks.add_task(
            execute_automated_investigation,
            investigation_id,
            tasks_created,
            selected_agent,
            request.case_id,
            request.timeout_minutes
        )
        
        logger.info(f"🔍 Investigación automatizada iniciada: {investigation_id} con {len(tasks_created)} tareas")
        
        return {
            "investigation_id": investigation_id,
            "status": "started",
            "agent_id": selected_agent,
            "tasks_queued": len(tasks_created),
            "tasks": tasks_created[:10],  # Mostrar solo las primeras 10
            "classified_iocs": {k: len(v) for k, v in classified_iocs.items()},
            "tools_selected": tools_to_run,
            "message": f"Investigación iniciada. {len(tasks_created)} tareas enviadas al agente {selected_agent}"
        }
    
    except Exception as e:
        logger.error(f"❌ Error al iniciar investigación: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/investigate/profiles", summary="Obtener perfiles de investigación")
async def get_investigation_profiles() -> Dict[str, Any]:
    """
    📋 Obtener perfiles de investigación disponibles
    """
    return {
        "profiles": INVESTIGATION_PROFILES,
        "ioc_tool_mapping": IOC_TOOL_MAPPING
    }


@router.get("/investigate/{investigation_id}", summary="Estado de investigación")
async def get_investigation_status(investigation_id: str) -> Dict[str, Any]:
    """
    📊 Obtener estado de una investigación automatizada
    """
    # TODO: Implementar persistencia real
    return {
        "investigation_id": investigation_id,
        "status": "running",
        "progress": 50,
        "tasks_completed": 5,
        "tasks_total": 10,
        "results_preview": [],
        "message": "Investigación en progreso"
    }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def classify_iocs(iocs: List[str]) -> Dict[str, List[str]]:
    """Clasificar IOCs por tipo"""
    import re
    
    classified = {
        "ip": [],
        "domain": [],
        "url": [],
        "hash": [],
        "email": [],
        "file": [],
        "user": [],
        "unknown": []
    }
    
    # Patrones de clasificación
    patterns = {
        "ip": r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$',
        "domain": r'^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.[A-Za-z]{2,})+$',
        "url": r'^https?://',
        "hash": r'^[a-fA-F0-9]{32}$|^[a-fA-F0-9]{40}$|^[a-fA-F0-9]{64}$',
        "email": r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
    }
    
    for ioc in iocs:
        ioc = ioc.strip()
        if not ioc:
            continue
            
        matched = False
        for ioc_type, pattern in patterns.items():
            if re.match(pattern, ioc, re.IGNORECASE):
                classified[ioc_type].append(ioc)
                matched = True
                break
        
        if not matched:
            # Verificar si parece un path de archivo
            if '/' in ioc or '\\' in ioc or ioc.startswith('.'):
                classified["file"].append(ioc)
            else:
                classified["unknown"].append(ioc)
    
    # Eliminar categorías vacías
    return {k: v for k, v in classified.items() if v}


async def select_best_agent(classified_iocs: Dict[str, List[str]]) -> str:
    """Seleccionar el mejor agente para la investigación"""
    try:
        # Determinar qué tipo de agente necesitamos
        needs_network = any(t in classified_iocs for t in ["ip", "domain", "url"])
        needs_host = any(t in classified_iocs for t in ["file", "process", "registry", "user"])
        
        # Buscar agentes reales online
        async with get_async_db_context() as db:
            real_agents = db.query(Agent).filter(Agent.status == "online").all()
        
        if real_agents:
            # Preferir blue agents para investigaciones
            blue_agents = [a for a in real_agents if a.agent_type == "blue"]
            if blue_agents:
                return blue_agents[0].id
            
            return real_agents[0].id
        
        # Fallback a demo solo si está habilitado
        if settings.DEMO_DATA_ENABLED:
            demo_agents = get_demo_agents()
            online_agents = [a for a in demo_agents if a["status"] == "online"]
            
            if online_agents:
                blue_agents = [a for a in online_agents if a["agent_type"] == "blue"]
                if blue_agents:
                    return blue_agents[0]["id"]
                
                return online_agents[0]["id"]
        
        return "local-mcp"  # Fallback a ejecución local cuando no hay agentes
    
    except Exception as e:
        logger.warning(f"Error selecting agent: {e}, using local")
        return "local-mcp"


async def execute_automated_investigation(
    investigation_id: str,
    tasks: List[Dict],
    agent_id: str,
    case_id: Optional[str],
    timeout_minutes: int
):
    """Ejecutar investigación automatizada en background"""
    import asyncio
    
    logger.info(f"🔍 Ejecutando investigación {investigation_id} con {len(tasks)} tareas")
    
    results = []
    
    for task in tasks:
        try:
            logger.info(f"  ⚙️ Ejecutando {task['tool']} en {task['target']}")
            
            # Simular ejecución (en producción, usar agent_manager.dispatch_task)
            await asyncio.sleep(0.5)  # Simular tiempo de ejecución
            
            results.append({
                "task_id": task["task_id"],
                "tool": task["tool"],
                "target": task["target"],
                "status": "completed",
                "result": f"Resultado de {task['tool']} para {task['target']}"
            })
            
        except Exception as e:
            logger.error(f"  ❌ Error en tarea {task['task_id']}: {e}")
            results.append({
                "task_id": task["task_id"],
                "tool": task["tool"],
                "target": task["target"],
                "status": "failed",
                "error": str(e)
            })
    
    logger.info(f"✅ Investigación {investigation_id} completada: {len(results)} resultados")
    
    # TODO: Guardar resultados en DB y notificar via WebSocket


# ============================================================================
# REMOTE AGENT DEPLOYMENT
# ============================================================================

@router.get("/deploy/script/{agent_type}", summary="Generar script de despliegue")
async def generate_deployment_script(
    agent_type: str,
    platform: str = "linux",
    mcp_host: str = "localhost",
    mcp_port: int = 8888
) -> Dict[str, Any]:
    """
    🚀 Genera un script de instalación para desplegar agentes remotos.
    
    El script:
    1. Instala dependencias necesarias
    2. Descarga y configura el agente
    3. Se registra automáticamente con el MCP
    4. Inicia el servicio del agente
    
    Args:
        agent_type: Tipo de agente (blue, red, purple, generic)
        platform: Plataforma destino (linux, windows, macos)
        mcp_host: Host del servidor MCP
        mcp_port: Puerto del servidor MCP
    """
    if agent_type not in AGENT_TYPES_CONFIG:
        raise HTTPException(status_code=400, detail=f"Tipo de agente inválido: {agent_type}")
    
    agent_config = AGENT_TYPES_CONFIG[agent_type]
    
    if platform == "linux":
        script = generate_linux_agent_script(agent_type, agent_config, mcp_host, mcp_port)
        filename = f"install_agent_{agent_type}.sh"
        content_type = "text/x-shellscript"
    elif platform == "windows":
        script = generate_windows_agent_script(agent_type, agent_config, mcp_host, mcp_port)
        filename = f"install_agent_{agent_type}.ps1"
        content_type = "text/plain"
    elif platform == "macos":
        script = generate_macos_agent_script(agent_type, agent_config, mcp_host, mcp_port)
        filename = f"install_agent_{agent_type}.sh"
        content_type = "text/x-shellscript"
    else:
        raise HTTPException(status_code=400, detail=f"Plataforma no soportada: {platform}")
    
    return {
        "agent_type": agent_type,
        "platform": platform,
        "filename": filename,
        "content_type": content_type,
        "script": script,
        "instructions": get_deployment_instructions(platform, agent_type, mcp_host, mcp_port)
    }


def generate_linux_agent_script(agent_type: str, config: Dict, mcp_host: str, mcp_port: int) -> str:
    """Genera script de instalación para Linux"""
    capabilities = ",".join(config.get("capabilities", []))
    tools = " ".join(config.get("tools", []))
    
    return f'''#!/bin/bash
# ============================================================================
# JETURING MCP Agent Installer - {config["name"]}
# Tipo: {agent_type}
# Generado: {datetime.now().isoformat()}
# ============================================================================

set -e

# Colores
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
BLUE='\\033[0;34m'
NC='\\033[0m'

echo -e "${{BLUE}}╔════════════════════════════════════════════╗${{NC}}"
echo -e "${{BLUE}}║   JETURING MCP Agent Installer             ║${{NC}}"
echo -e "${{BLUE}}║   Tipo: {agent_type.upper():40}║${{NC}}"
echo -e "${{BLUE}}╚════════════════════════════════════════════╝${{NC}}"
echo ""

# Configuración
MCP_HOST="{mcp_host}"
MCP_PORT="{mcp_port}"
AGENT_TYPE="{agent_type}"
AGENT_DIR="/opt/jeturing-agent"
CAPABILITIES="{capabilities}"

# Detectar hostname e IP
HOSTNAME=$(hostname)
IP_ADDRESS=$(hostname -I | awk '{{print $1}}')
OS_VERSION=$(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)
PLATFORM="linux"

echo -e "${{YELLOW}}[INFO]${{NC}} Hostname: $HOSTNAME"
echo -e "${{YELLOW}}[INFO]${{NC}} IP: $IP_ADDRESS"
echo -e "${{YELLOW}}[INFO]${{NC}} OS: $OS_VERSION"
echo ""

# Verificar permisos de root
if [ "$EUID" -ne 0 ]; then
    echo -e "${{RED}}[ERROR]${{NC}} Este script debe ejecutarse como root"
    exit 1
fi

# Instalar dependencias
echo -e "${{YELLOW}}[1/5]${{NC}} Instalando dependencias..."
apt-get update -qq
apt-get install -y -qq curl jq python3 python3-pip python3-venv > /dev/null 2>&1

# Crear directorio del agente
echo -e "${{YELLOW}}[2/5]${{NC}} Configurando directorio del agente..."
mkdir -p $AGENT_DIR
cd $AGENT_DIR

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias Python
pip install -q requests psutil

# Crear script del agente
echo -e "${{YELLOW}}[3/5]${{NC}} Creando agente..."

cat > agent.py << 'AGENT_EOF'
#!/usr/bin/env python3
"""
JETURING MCP Remote Agent
Tipo: {agent_type}
"""

import os
import sys
import time
import json
import socket
import platform
import subprocess
import threading
import requests
from datetime import datetime

class MCPAgent:
    def __init__(self, mcp_host, mcp_port, agent_type):
        self.mcp_url = f"http://{{mcp_host}}:{{mcp_port}}"
        self.agent_type = agent_type
        self.agent_id = None
        self.hostname = socket.gethostname()
        self.ip_address = self._get_ip()
        self.platform = platform.system().lower()
        self.os_version = platform.platform()
        self.running = True
        
    def _get_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    def register(self):
        """Registrar agente con el MCP"""
        payload = {{
            "name": f"{{self.hostname}}-{{self.agent_type}}",
            "agent_type": self.agent_type,
            "hostname": self.hostname,
            "ip_address": self.ip_address,
            "platform": self.platform,
            "os_version": self.os_version,
            "capabilities": os.environ.get("CAPABILITIES", "").split(",")
        }}
        
        try:
            response = requests.post(
                f"{{self.mcp_url}}/api/v41/agents/register",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.agent_id = data.get("agent_id")
                print(f"[OK] Registrado como: {{self.agent_id}}")
                return True
            else:
                print(f"[ERROR] Registro fallido: {{response.text}}")
                return False
                
        except Exception as e:
            print(f"[ERROR] No se pudo conectar al MCP: {{e}}")
            return False
    
    def heartbeat(self):
        """Enviar heartbeat al MCP"""
        while self.running:
            try:
                requests.post(
                    f"{{self.mcp_url}}/api/v41/agents/{{self.agent_id}}/heartbeat",
                    json={{"status": "online", "timestamp": datetime.utcnow().isoformat()}},
                    timeout=5
                )
            except:
                pass
            time.sleep(30)
    
    def poll_tasks(self):
        """Polling de tareas pendientes"""
        while self.running:
            try:
                response = requests.get(
                    f"{{self.mcp_url}}/api/v41/agents/{{self.agent_id}}/pending-tasks",
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    for task in data.get("tasks", []):
                        self.execute_task(task)
                        
            except Exception as e:
                print(f"[WARN] Error polling: {{e}}")
            
            time.sleep(5)
    
    def execute_task(self, task):
        """Ejecutar una tarea"""
        task_id = task.get("task_id")
        tool = task.get("tool")
        params = task.get("parameters", {{}})
        
        print(f"[TASK] Ejecutando {{tool}}...")
        
        try:
            # Ejecutar herramienta
            result = self.run_tool(tool, params)
            
            # Reportar resultado
            requests.post(
                f"{{self.mcp_url}}/api/v41/agents/{{self.agent_id}}/task/{{task_id}}/complete",
                json={{"status": "completed", "result": result}},
                timeout=30
            )
            print(f"[OK] Tarea {{task_id}} completada")
            
        except Exception as e:
            requests.post(
                f"{{self.mcp_url}}/api/v41/agents/{{self.agent_id}}/task/{{task_id}}/complete",
                json={{"status": "failed", "error": str(e)}},
                timeout=10
            )
            print(f"[ERROR] Tarea {{task_id}} falló: {{e}}")
    
    def run_tool(self, tool, params):
        """Ejecutar herramienta del sistema"""
        target = params.get("target", "")
        
        commands = {{
            "nmap": f"nmap -sV {{target}}",
            "whois": f"whois {{target}}",
            "dig": f"dig {{target}}",
            "ping": f"ping -c 4 {{target}}",
            "curl": f"curl -sI {{target}}",
            "osquery": f"osqueryi --json 'SELECT * FROM system_info'",
        }}
        
        cmd = commands.get(tool, f"echo 'Tool {{tool}} not implemented'")
        
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=300
        )
        
        return {{
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }}
    
    def run(self):
        """Iniciar agente"""
        print(f"Iniciando agente {{self.agent_type}}...")
        
        if not self.register():
            print("No se pudo registrar. Reintentando en 30s...")
            time.sleep(30)
            return self.run()
        
        # Iniciar threads
        threading.Thread(target=self.heartbeat, daemon=True).start()
        threading.Thread(target=self.poll_tasks, daemon=True).start()
        
        print(f"[OK] Agente activo. Esperando tareas...")
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.running = False
            print("\\n[INFO] Agente detenido")


if __name__ == "__main__":
    agent = MCPAgent(
        mcp_host=os.environ.get("MCP_HOST", "localhost"),
        mcp_port=int(os.environ.get("MCP_PORT", "8888")),
        agent_type=os.environ.get("AGENT_TYPE", "generic")
    )
    agent.run()
AGENT_EOF

# Crear archivo de configuración
cat > config.env << EOF
MCP_HOST=$MCP_HOST
MCP_PORT=$MCP_PORT
AGENT_TYPE=$AGENT_TYPE
CAPABILITIES=$CAPABILITIES
EOF

# Crear servicio systemd
echo -e "${{YELLOW}}[4/5]${{NC}} Creando servicio systemd..."

cat > /etc/systemd/system/jeturing-agent.service << EOF
[Unit]
Description=JETURING MCP Agent
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$AGENT_DIR
EnvironmentFile=$AGENT_DIR/config.env
ExecStart=$AGENT_DIR/venv/bin/python $AGENT_DIR/agent.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Habilitar e iniciar servicio
systemctl daemon-reload
systemctl enable jeturing-agent
systemctl start jeturing-agent

echo -e "${{YELLOW}}[5/5]${{NC}} Verificando instalación..."
sleep 3

if systemctl is-active --quiet jeturing-agent; then
    echo ""
    echo -e "${{GREEN}}╔════════════════════════════════════════════╗${{NC}}"
    echo -e "${{GREEN}}║   ✅ Agente instalado exitosamente!        ║${{NC}}"
    echo -e "${{GREEN}}╚════════════════════════════════════════════╝${{NC}}"
    echo ""
    echo -e "Tipo:     ${{BLUE}}$AGENT_TYPE${{NC}}"
    echo -e "Hostname: ${{BLUE}}$HOSTNAME${{NC}}"
    echo -e "IP:       ${{BLUE}}$IP_ADDRESS${{NC}}"
    echo -e "MCP:      ${{BLUE}}$MCP_HOST:$MCP_PORT${{NC}}"
    echo ""
    echo "Comandos útiles:"
    echo "  journalctl -u jeturing-agent -f    # Ver logs"
    echo "  systemctl status jeturing-agent    # Estado del servicio"
    echo "  systemctl restart jeturing-agent   # Reiniciar"
else
    echo -e "${{RED}}[ERROR]${{NC}} El servicio no pudo iniciarse"
    journalctl -u jeturing-agent --no-pager -n 20
    exit 1
fi
'''


def generate_windows_agent_script(agent_type: str, config: Dict, mcp_host: str, mcp_port: int) -> str:
    """Genera script de instalación para Windows (PowerShell)"""
    capabilities = ",".join(config.get("capabilities", []))
    
    return f'''# ============================================================================
# JETURING MCP Agent Installer - {config["name"]}
# Tipo: {agent_type}
# Generado: {datetime.now().isoformat()}
# ============================================================================

$ErrorActionPreference = "Stop"

# Configuración
$MCP_HOST = "{mcp_host}"
$MCP_PORT = "{mcp_port}"
$AGENT_TYPE = "{agent_type}"
$AGENT_DIR = "C:\\JETURING-Agent"
$CAPABILITIES = "{capabilities}"

Write-Host "========================================" -ForegroundColor Blue
Write-Host "   JETURING MCP Agent Installer" -ForegroundColor Blue
Write-Host "   Tipo: {agent_type.upper()}" -ForegroundColor Blue
Write-Host "========================================" -ForegroundColor Blue
Write-Host ""

# Detectar hostname e IP
$HOSTNAME = $env:COMPUTERNAME
$IP_ADDRESS = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {{ $_.InterfaceAlias -notlike "*Loopback*" }} | Select-Object -First 1).IPAddress
$OS_VERSION = (Get-WmiObject Win32_OperatingSystem).Caption

Write-Host "[INFO] Hostname: $HOSTNAME" -ForegroundColor Yellow
Write-Host "[INFO] IP: $IP_ADDRESS" -ForegroundColor Yellow
Write-Host "[INFO] OS: $OS_VERSION" -ForegroundColor Yellow
Write-Host ""

# Verificar permisos de administrador
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {{
    Write-Host "[ERROR] Este script debe ejecutarse como Administrador" -ForegroundColor Red
    exit 1
}}

# Crear directorio
Write-Host "[1/5] Configurando directorio del agente..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $AGENT_DIR | Out-Null
Set-Location $AGENT_DIR

# Verificar Python
Write-Host "[2/5] Verificando Python..." -ForegroundColor Yellow
try {{
    python --version
}} catch {{
    Write-Host "[ERROR] Python no está instalado. Instalando..." -ForegroundColor Red
    winget install Python.Python.3.11 --accept-source-agreements --accept-package-agreements
}}

# Crear entorno virtual
Write-Host "[3/5] Creando entorno virtual..." -ForegroundColor Yellow
python -m venv venv
.\\venv\\Scripts\\Activate.ps1
pip install -q requests psutil

# Crear archivo de configuración
Write-Host "[4/5] Configurando agente..." -ForegroundColor Yellow
@"
MCP_HOST=$MCP_HOST
MCP_PORT=$MCP_PORT
AGENT_TYPE=$AGENT_TYPE
CAPABILITIES=$CAPABILITIES
"@ | Out-File -FilePath "$AGENT_DIR\\config.env" -Encoding utf8

# Registrar con el MCP
Write-Host "[5/5] Registrando agente..." -ForegroundColor Yellow

$payload = @{{
    name = "$HOSTNAME-{agent_type}"
    agent_type = "{agent_type}"
    hostname = $HOSTNAME
    ip_address = $IP_ADDRESS
    platform = "windows"
    os_version = $OS_VERSION
    capabilities = "{capabilities}".Split(",")
}} | ConvertTo-Json

try {{
    $response = Invoke-RestMethod -Uri "http://${{MCP_HOST}}:${{MCP_PORT}}/api/v41/agents/register" -Method Post -Body $payload -ContentType "application/json"
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "   ✅ Agente registrado exitosamente!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Agent ID: $($response.agent_id)" -ForegroundColor Cyan
}} catch {{
    Write-Host "[ERROR] No se pudo registrar: $_" -ForegroundColor Red
    exit 1
}}
'''


def generate_macos_agent_script(agent_type: str, config: Dict, mcp_host: str, mcp_port: int) -> str:
    """Genera script de instalación para macOS"""
    capabilities = ",".join(config.get("capabilities", []))
    
    return f'''#!/bin/bash
# ============================================================================
# JETURING MCP Agent Installer - {config["name"]} (macOS)
# Tipo: {agent_type}
# Generado: {datetime.now().isoformat()}
# ============================================================================

set -e

# Configuración
MCP_HOST="{mcp_host}"
MCP_PORT="{mcp_port}"
AGENT_TYPE="{agent_type}"
AGENT_DIR="$HOME/.jeturing-agent"
CAPABILITIES="{capabilities}"

echo "========================================"
echo "   JETURING MCP Agent Installer"
echo "   Tipo: {agent_type.upper()}"
echo "========================================"
echo ""

# Detectar hostname e IP
HOSTNAME=$(hostname)
IP_ADDRESS=$(ipconfig getifaddr en0 || ipconfig getifaddr en1 || echo "127.0.0.1")
OS_VERSION=$(sw_vers -productVersion)

echo "[INFO] Hostname: $HOSTNAME"
echo "[INFO] IP: $IP_ADDRESS"
echo "[INFO] macOS: $OS_VERSION"
echo ""

# Crear directorio
echo "[1/4] Configurando directorio..."
mkdir -p "$AGENT_DIR"
cd "$AGENT_DIR"

# Verificar Python
echo "[2/4] Verificando Python..."
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 no instalado. Instalando con Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    brew install python3
fi

# Crear entorno virtual
echo "[3/4] Creando entorno virtual..."
python3 -m venv venv
source venv/bin/activate
pip install -q requests psutil

# Registrar agente
echo "[4/4] Registrando agente..."

PAYLOAD=$(cat <<EOF
{{
    "name": "$HOSTNAME-{agent_type}",
    "agent_type": "{agent_type}",
    "hostname": "$HOSTNAME",
    "ip_address": "$IP_ADDRESS",
    "platform": "macos",
    "os_version": "macOS $OS_VERSION",
    "capabilities": ["{capabilities.replace(',', '","')}"]
}}
EOF
)

RESPONSE=$(curl -s -X POST "http://$MCP_HOST:$MCP_PORT/api/v41/agents/register" \\
    -H "Content-Type: application/json" \\
    -d "$PAYLOAD")

if echo "$RESPONSE" | grep -q "agent_id"; then
    echo ""
    echo "========================================"
    echo "   ✅ Agente registrado exitosamente!"
    echo "========================================"
    echo ""
    echo "$RESPONSE" | python3 -c "import sys, json; print('Agent ID:', json.load(sys.stdin).get('agent_id'))"
else
    echo "[ERROR] Registro fallido: $RESPONSE"
    exit 1
fi
'''


def get_deployment_instructions(platform: str, agent_type: str, mcp_host: str, mcp_port: int) -> Dict:
    """Obtiene instrucciones de despliegue para una plataforma"""
    
    base_instructions = {
        "linux": {
            "title": "Despliegue en Linux",
            "steps": [
                f"1. Descargar script: curl -O http://{mcp_host}:{mcp_port}/api/v41/agents/deploy/script/{agent_type}?platform=linux",
                "2. Dar permisos: chmod +x install_agent_*.sh",
                "3. Ejecutar como root: sudo ./install_agent_*.sh",
                "4. Verificar: systemctl status jeturing-agent"
            ],
            "one_liner": f"curl -sSL http://{mcp_host}:{mcp_port}/api/v41/agents/deploy/script/{agent_type}?platform=linux | sudo bash"
        },
        "windows": {
            "title": "Despliegue en Windows",
            "steps": [
                "1. Abrir PowerShell como Administrador",
                f"2. Ejecutar: irm http://{mcp_host}:{mcp_port}/api/v41/agents/deploy/script/{agent_type}?platform=windows | iex",
                "3. Verificar en el dashboard del MCP"
            ],
            "one_liner": f"irm http://{mcp_host}:{mcp_port}/api/v41/agents/deploy/script/{agent_type}?platform=windows | iex"
        },
        "macos": {
            "title": "Despliegue en macOS",
            "steps": [
                f"1. Descargar: curl -O http://{mcp_host}:{mcp_port}/api/v41/agents/deploy/script/{agent_type}?platform=macos",
                "2. Dar permisos: chmod +x install_agent_*.sh",
                "3. Ejecutar: ./install_agent_*.sh",
                "4. Verificar en el dashboard del MCP"
            ],
            "one_liner": f"curl -sSL http://{mcp_host}:{mcp_port}/api/v41/agents/deploy/script/{agent_type}?platform=macos | bash"
        }
    }
    
    return base_instructions.get(platform, base_instructions["linux"])


@router.post("/{agent_id}/heartbeat", summary="Recibir heartbeat de agente")
async def agent_heartbeat(
    agent_id: str,
    status: str = "online"
) -> Dict[str, Any]:
    """
    💓 Recibe heartbeat de un agente remoto
    """
    try:
        async with get_async_db_context() as db:
            agent = db.query(Agent).filter(Agent.id == agent_id).first()
            
            if agent:
                agent.status = status
                agent.last_seen = datetime.now()
                db.commit()
                
                return {"success": True, "agent_id": agent_id, "status": status}
        
        return {"success": False, "error": "Agente no encontrado"}
        
    except Exception as e:
        logger.error(f"Error en heartbeat: {e}")
        return {"success": False, "error": str(e)}


@router.get("/{agent_id}/pending-tasks", summary="Obtener tareas pendientes")
async def get_pending_tasks(agent_id: str) -> Dict[str, Any]:
    """
    📋 Obtiene tareas pendientes para un agente
    """
    try:
        async with get_async_db_context() as db:
            tasks = db.query(AgentTask).filter(
                AgentTask.agent_id == agent_id,
                AgentTask.status == "pending"
            ).limit(10).all()
            
            return {
                "agent_id": agent_id,
                "tasks": [
                    {
                        "task_id": t.id,
                        "tool": t.tool,
                        "parameters": t.parameters or {},
                        "case_id": t.case_id,
                        "priority": t.priority
                    }
                    for t in tasks
                ]
            }
    
    except Exception as e:
        logger.error(f"Error obteniendo tareas: {e}")
        return {"agent_id": agent_id, "tasks": []}


@router.post("/{agent_id}/task/{task_id}/complete", summary="Completar tarea")
async def complete_task(
    agent_id: str,
    task_id: str,
    status: str = "completed",
    result: Optional[Dict] = None,
    error: Optional[str] = None
) -> Dict[str, Any]:
    """
    ✅ Marca una tarea como completada
    """
    try:
        async with get_async_db_context() as db:
            task = db.query(AgentTask).filter(
                AgentTask.id == task_id,
                AgentTask.agent_id == agent_id
            ).first()
            
            if task:
                task.status = status
                task.result = result
                task.error = error
                task.completed_at = datetime.now()
                db.commit()
                
                logger.info(f"✅ Tarea {task_id} completada por {agent_id}")
                return {"success": True, "task_id": task_id, "status": status}
        
        return {"success": False, "error": "Tarea no encontrada"}
        
    except Exception as e:
        logger.error(f"Error completando tarea: {e}")
        return {"success": False, "error": str(e)}
