"""
Verificación de herramientas forenses instaladas
"""

import asyncio
from pathlib import Path
from typing import Dict
import logging

logger = logging.getLogger(__name__)

async def check_tools_availability() -> Dict[str, bool]:
    """
    Verifica qué herramientas forenses están disponibles
    """
    tools = {
        "sparrow": Path("/opt/forensics-tools/Sparrow").exists(),
        "hawk": Path("/opt/forensics-tools/hawk").exists(),
        "o365_extractor": Path("/opt/forensics-tools/sra-o365-extractor").exists(),
        "loki": Path("/opt/forensics-tools/Loki").exists(),
        "yara_rules": Path("/opt/forensics-tools/yara-rules").exists(),
        "powershell": await check_command("pwsh"),
        "yara": await check_command("yara"),
        "volatility": await check_command("vol.py"),
        "osquery": await check_command("osqueryi")
    }
    
    return tools

async def check_command(command: str) -> bool:
    """
    Verifica si un comando está disponible en el PATH
    """
    try:
        process = await asyncio.create_subprocess_exec(
            "which", command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        return process.returncode == 0
    except Exception:
        return False
