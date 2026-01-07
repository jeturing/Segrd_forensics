import asyncio
import logging
import json
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class DockerContainer:
    id: str
    name: str
    image: str
    status: str
    ports: str
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "image": self.image,
            "status": self.status,
            "ports": self.ports
        }

class DockerService:
    """
    Service to interact with Docker daemon via CLI (subprocess).
    Used for discovering LLM containers and managing models.
    """
    
    @staticmethod
    async def is_docker_available() -> bool:
        """Check if docker is available and accessible."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "info",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await proc.wait()
            return proc.returncode == 0
        except FileNotFoundError:
            return False

    @staticmethod
    async def list_containers() -> List[DockerContainer]:
        """List all running containers."""
        if not await DockerService.is_docker_available():
            logger.warning("Docker not available or not accessible")
            return []

        try:
            # Format: ID|Names|Image|Status|Ports
            cmd = [
                "docker", "ps", "--format", 
                "{{.ID}}|{{.Names}}|{{.Image}}|{{.Status}}|{{.Ports}}"
            ]
            
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode != 0:
                logger.error(f"Error listing containers: {stderr.decode()}")
                return []
            
            containers = []
            for line in stdout.decode().splitlines():
                if not line.strip():
                    continue
                parts = line.split("|")
                if len(parts) >= 5:
                    containers.append(DockerContainer(
                        id=parts[0],
                        name=parts[1],
                        image=parts[2],
                        status=parts[3],
                        ports=parts[4]
                    ))
            return containers
            
        except Exception as e:
            logger.error(f"Exception listing containers: {e}")
            return []

    @staticmethod
    async def exec_command(container_id: str, command: List[str], user: str = None) -> Dict[str, Any]:
        """Execute a command inside a container."""
        if not await DockerService.is_docker_available():
            return {"success": False, "error": "Docker not available"}

        cmd = ["docker", "exec"]
        if user:
            cmd.extend(["-u", user])
        cmd.append(container_id)
        cmd.extend(command)
        
        try:
            logger.info(f"Executing in {container_id}: {' '.join(command)} (user={user})")
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            success = proc.returncode == 0
            return {
                "success": success,
                "stdout": stdout.decode(),
                "stderr": stderr.decode(),
                "code": proc.returncode
            }
        except Exception as e:
            logger.error(f"Exception executing command: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    async def pull_ollama_model(container_id: str, model_name: str, as_root: bool = False) -> Dict[str, Any]:
        """Pull a model in an Ollama container."""
        # Ollama pull command
        cmd = ["ollama", "pull", model_name]
        user = "root" if as_root else None
        
        # This might take a while, so we might want to run it in background or stream it.
        # For now, we'll wait (simple implementation). 
        # In production, this should probably be a background task.
        return await DockerService.exec_command(container_id, cmd, user=user)

    @staticmethod
    async def list_ollama_models(container_id: str) -> List[str]:
        """List models in an Ollama container."""
        cmd = ["ollama", "list"]
        result = await DockerService.exec_command(container_id, cmd)
        if not result["success"]:
            return []
        
        # Parse output
        # NAME    ID    SIZE    MODIFIED
        # phi4:latest    ...
        models = []
        lines = result["stdout"].splitlines()
        if len(lines) > 1:
            for line in lines[1:]: # Skip header
                parts = line.split()
                if parts:
                    models.append(parts[0])
        return models

from typing import Any
