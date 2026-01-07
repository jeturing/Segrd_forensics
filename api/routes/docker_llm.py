from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from typing import List, Optional
import logging

from api.services.docker_service import DockerService
from api.middleware.auth import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v41/docker", tags=["Docker LLM"])

class ContainerResponse(BaseModel):
    id: str
    name: str
    image: str
    status: str
    ports: str

class PullModelRequest(BaseModel):
    model_name: str
    as_root: bool = False

@router.get("/containers", response_model=List[ContainerResponse])
async def list_llm_containers(api_key: str = Depends(verify_api_key)):
    """
    List running Docker containers.
    Frontend can filter for 'ollama', 'lm-studio', etc.
    """
    containers = await DockerService.list_containers()
    return [c.to_dict() for c in containers]

@router.get("/containers/{container_id}/models", response_model=List[str])
async def list_container_models(container_id: str, api_key: str = Depends(verify_api_key)):
    """
    List models available inside a container (Ollama only for now).
    """
    # Verify container exists
    containers = await DockerService.list_containers()
    container = next((c for c in containers if c.id.startswith(container_id) or c.name == container_id), None)
    
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")
        
    # Only support Ollama for now
    if "ollama" in container.image.lower() or "ollama" in container.name.lower():
        return await DockerService.list_ollama_models(container.id)
    
    return []

@router.post("/containers/{container_id}/pull")
async def pull_model(
    container_id: str, 
    request: PullModelRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key)
):
    """
    Pull a model inside a container (e.g. Ollama).
    Supports running as root if needed.
    """
    # Verify container exists
    containers = await DockerService.list_containers()
    if not any(c.id.startswith(container_id) or c.name == container_id for c in containers):
        raise HTTPException(status_code=404, detail="Container not found")

    # Run in background as it can take time
    background_tasks.add_task(
        _pull_model_task, 
        container_id, 
        request.model_name, 
        request.as_root
    )
    
    return {"status": "started", "message": f"Pulling {request.model_name} in {container_id}"}

async def _pull_model_task(container_id: str, model_name: str, as_root: bool):
    logger.info(f"Starting background pull for {model_name} in {container_id}")
    result = await DockerService.pull_ollama_model(container_id, model_name, as_root)
    if result["success"]:
        logger.info(f"Successfully pulled {model_name}")
    else:
        logger.error(f"Failed to pull {model_name}: {result.get('stderr') or result.get('error')}")
