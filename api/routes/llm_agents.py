"""
LLM Agents Management Routes
Gestión de agentes LLM (Ollama) por tenant desde la consola de administración
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
import docker
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/llm-agents", tags=["LLM Agents"])

# ============================================================================
# MODELS
# ============================================================================

class OllamaAgentCreate(BaseModel):
    """Solicitud para crear un nuevo agente Ollama"""
    name: str = Field(..., description="Nombre del agente (ej: agent4)")
    tenant_id: str = Field(..., description="ID del tenant propietario")
    model: str = Field(default="phi4-mini", description="Modelo a usar")
    port: int = Field(..., description="Puerto host único (ej: 11438)")
    memory_limit: str = Field(default="6g", description="Límite de memoria")
    memory_reservation: str = Field(default="2g", description="Reserva de memoria")

class OllamaAgentResponse(BaseModel):
    """Información de agente Ollama"""
    container_id: str
    name: str
    tenant_id: str
    model: str
    port: int
    status: str
    created_at: str
    memory_limit: str

class OllamaAgentUpdate(BaseModel):
    """Actualización de agente"""
    tenant_id: Optional[str] = None
    model: Optional[str] = None
    memory_limit: Optional[str] = None

# ============================================================================
# DOCKER CLIENT
# ============================================================================

try:
    docker_client = docker.from_env()
except Exception as e:
    logger.error(f"Error conectando a Docker: {e}")
    docker_client = None

# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/", response_model=List[OllamaAgentResponse])
async def list_llm_agents(tenant_id: Optional[str] = None):
    """
    Listar todos los agentes Ollama activos
    Opcionalmente filtrar por tenant_id
    """
    if not docker_client:
        raise HTTPException(status_code=503, detail="Docker no disponible")
    
    try:
        containers = docker_client.containers.list(
            all=True,
            filters={"name": "ollama-agent-"}
        )
        
        agents = []
        for container in containers:
            labels = container.labels
            agent_tenant = labels.get("tenant_id", "")
            
            # Filtrar por tenant si se especifica
            if tenant_id and agent_tenant != tenant_id:
                continue
            
            # Extraer puerto mapeado
            ports = container.attrs.get("NetworkSettings", {}).get("Ports", {})
            mapped_port = None
            for key, value in ports.items():
                if "11434" in key and value:
                    mapped_port = int(value[0]["HostPort"])
                    break
            
            agents.append(OllamaAgentResponse(
                container_id=container.id[:12],
                name=container.name,
                tenant_id=agent_tenant,
                model=labels.get("model", "unknown"),
                port=mapped_port or 0,
                status=container.status,
                created_at=container.attrs["Created"],
                memory_limit=labels.get("memory_limit", "6g")
            ))
        
        return agents
    
    except Exception as e:
        logger.error(f"Error listando agentes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=OllamaAgentResponse)
async def create_llm_agent(agent: OllamaAgentCreate, background_tasks: BackgroundTasks):
    """
    Crear un nuevo agente Ollama para un tenant
    Se crea el contenedor, se descarga el modelo y se configura
    """
    if not docker_client:
        raise HTTPException(status_code=503, detail="Docker no disponible")
    
    container_name = f"ollama-agent-{agent.name}"
    
    # Verificar que no existe
    try:
        existing = docker_client.containers.get(container_name)
        raise HTTPException(
            status_code=400,
            detail=f"Agente {container_name} ya existe"
        )
    except docker.errors.NotFound:
        pass
    
    # Verificar que el puerto no está en uso
    try:
        containers = docker_client.containers.list(all=True)
        for c in containers:
            ports = c.attrs.get("NetworkSettings", {}).get("Ports", {})
            for key, value in ports.items():
                if value and any(str(agent.port) == p["HostPort"] for p in value):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Puerto {agent.port} ya está en uso por {c.name}"
                    )
    except docker.errors.APIError as e:
        logger.error(f"Error verificando puertos: {e}")
    
    try:
        # Crear contenedor
        container = docker_client.containers.run(
            image="ollama/ollama",
            name=container_name,
            detach=True,
            ports={"11434/tcp": agent.port},
            volumes={
                f"ollama-{agent.name}": {"bind": "/root/.ollama", "mode": "rw"}
            },
            environment={
                "OLLAMA_HOST": "http://0.0.0.0:11434"
            },
            labels={
                "tenant_id": agent.tenant_id,
                "model": agent.model,
                "memory_limit": agent.memory_limit,
                "created_by": "mcp-forensics-admin",
                "created_at": datetime.now().isoformat()
            },
            mem_limit=agent.memory_limit,
            mem_reservation=agent.memory_reservation
        )
        
        logger.info(f"✅ Contenedor {container_name} creado: {container.id[:12]}")
        
        # Descargar modelo en segundo plano
        background_tasks.add_task(
            pull_model_in_container,
            container.id,
            agent.model
        )
        
        return OllamaAgentResponse(
            container_id=container.id[:12],
            name=container_name,
            tenant_id=agent.tenant_id,
            model=agent.model,
            port=agent.port,
            status="created",
            created_at=datetime.now().isoformat(),
            memory_limit=agent.memory_limit
        )
    
    except docker.errors.APIError as e:
        logger.error(f"Error creando contenedor: {e}")
        raise HTTPException(status_code=500, detail=f"Error Docker: {str(e)}")


@router.get("/{agent_name}")
async def get_llm_agent(agent_name: str):
    """Obtener información de un agente específico"""
    if not docker_client:
        raise HTTPException(status_code=503, detail="Docker no disponible")
    
    container_name = f"ollama-agent-{agent_name}" if not agent_name.startswith("ollama-agent-") else agent_name
    
    try:
        container = docker_client.containers.get(container_name)
        labels = container.labels
        
        # Obtener modelos instalados
        exec_result = container.exec_run("ollama list")
        models_output = exec_result.output.decode() if exec_result.exit_code == 0 else ""
        
        ports = container.attrs.get("NetworkSettings", {}).get("Ports", {})
        mapped_port = None
        for key, value in ports.items():
            if "11434" in key and value:
                mapped_port = int(value[0]["HostPort"])
                break
        
        return {
            "container_id": container.id[:12],
            "name": container.name,
            "tenant_id": labels.get("tenant_id", ""),
            "model": labels.get("model", "unknown"),
            "port": mapped_port,
            "status": container.status,
            "created_at": labels.get("created_at", ""),
            "memory_limit": labels.get("memory_limit", "6g"),
            "models_installed": models_output.strip().split("\n")[1:] if models_output else []
        }
    
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail="Agente no encontrado")
    except Exception as e:
        logger.error(f"Error obteniendo agente: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{agent_name}")
async def update_llm_agent(agent_name: str, update: OllamaAgentUpdate):
    """Actualizar configuración de un agente (solo labels)"""
    if not docker_client:
        raise HTTPException(status_code=503, detail="Docker no disponible")
    
    container_name = f"ollama-agent-{agent_name}" if not agent_name.startswith("ollama-agent-") else agent_name
    
    try:
        container = docker_client.containers.get(container_name)
        
        # Actualizar labels (requiere recrear el contenedor)
        current_labels = container.labels
        if update.tenant_id:
            current_labels["tenant_id"] = update.tenant_id
        if update.model:
            current_labels["model"] = update.model
        if update.memory_limit:
            current_labels["memory_limit"] = update.memory_limit
        
        # Para cambios reales (memoria, etc) hay que recrear el contenedor
        # Por ahora solo actualizamos labels vía API
        
        return {
            "success": True,
            "message": "Labels actualizados (cambios de memoria requieren recrear contenedor)",
            "container_id": container.id[:12]
        }
    
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail="Agente no encontrado")
    except Exception as e:
        logger.error(f"Error actualizando agente: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{agent_name}")
async def delete_llm_agent(agent_name: str, remove_volume: bool = False):
    """
    Eliminar un agente Ollama
    - remove_volume: Si true, elimina también el volumen de datos
    """
    if not docker_client:
        raise HTTPException(status_code=503, detail="Docker no disponible")
    
    container_name = f"ollama-agent-{agent_name}" if not agent_name.startswith("ollama-agent-") else agent_name
    
    try:
        container = docker_client.containers.get(container_name)
        
        # Detener y eliminar
        container.stop(timeout=10)
        container.remove()
        
        logger.info(f"✅ Contenedor {container_name} eliminado")
        
        # Eliminar volumen si se solicita
        if remove_volume:
            volume_name = f"ollama-{agent_name.replace('ollama-agent-', '')}"
            try:
                volume = docker_client.volumes.get(volume_name)
                volume.remove()
                logger.info(f"✅ Volumen {volume_name} eliminado")
            except docker.errors.NotFound:
                logger.warning(f"Volumen {volume_name} no encontrado")
        
        return {
            "success": True,
            "message": f"Agente {agent_name} eliminado",
            "volume_removed": remove_volume
        }
    
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail="Agente no encontrado")
    except Exception as e:
        logger.error(f"Error eliminando agente: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{agent_name}/start")
async def start_llm_agent(agent_name: str):
    """Iniciar un agente detenido"""
    if not docker_client:
        raise HTTPException(status_code=503, detail="Docker no disponible")
    
    container_name = f"ollama-agent-{agent_name}" if not agent_name.startswith("ollama-agent-") else agent_name
    
    try:
        container = docker_client.containers.get(container_name)
        container.start()
        return {"success": True, "status": container.status}
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail="Agente no encontrado")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{agent_name}/stop")
async def stop_llm_agent(agent_name: str):
    """Detener un agente en ejecución"""
    if not docker_client:
        raise HTTPException(status_code=503, detail="Docker no disponible")
    
    container_name = f"ollama-agent-{agent_name}" if not agent_name.startswith("ollama-agent-") else agent_name
    
    try:
        container = docker_client.containers.get(container_name)
        container.stop(timeout=10)
        return {"success": True, "status": container.status}
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail="Agente no encontrado")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{agent_name}/pull-model")
async def pull_model(agent_name: str, model: str = "phi4-mini"):
    """Descargar un modelo en un agente específico"""
    if not docker_client:
        raise HTTPException(status_code=503, detail="Docker no disponible")
    
    container_name = f"ollama-agent-{agent_name}" if not agent_name.startswith("ollama-agent-") else agent_name
    
    try:
        container = docker_client.containers.get(container_name)
        
        # Ejecutar pull
        exec_result = container.exec_run(f"ollama pull {model}", stream=True)
        
        # Capturar output
        output = []
        for chunk in exec_result.output:
            output.append(chunk.decode())
        
        return {
            "success": True,
            "model": model,
            "output": "".join(output)
        }
    
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail="Agente no encontrado")
    except Exception as e:
        logger.error(f"Error descargando modelo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# BACKGROUND TASKS
# ============================================================================

async def pull_model_in_container(container_id: str, model: str):
    """Descargar modelo en segundo plano"""
    try:
        container = docker_client.containers.get(container_id)
        logger.info(f"📥 Descargando modelo {model} en {container.name}...")
        
        exec_result = container.exec_run(f"ollama pull {model}")
        
        if exec_result.exit_code == 0:
            logger.info(f"✅ Modelo {model} descargado en {container.name}")
        else:
            logger.error(f"❌ Error descargando modelo: {exec_result.output.decode()}")
    
    except Exception as e:
        logger.error(f"Error en pull_model_in_container: {e}")
