"""
🛠️ Extended Tool Catalog - Dynamic Tool Discovery & Auto-Installation
Soporta: Kali Linux, Parrot OS, Ubuntu/Debian
Incluye: Metasploit, M365 tools, Purple Team, auto-instalación desde GitHub
"""

import os
import platform
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

# =============================================================================
# OS DETECTION
# =============================================================================

def detect_os() -> Dict[str, str]:
    """Detecta el OS y retorna info relevante"""
    os_info = {
        "system": platform.system(),
        "distribution": "unknown",
        "version": "",
        "package_manager": "apt",
        "is_kali": False,
        "is_parrot": False
    }
    
    try:
        # Leer /etc/os-release
        if os.path.exists("/etc/os-release"):
            with open("/etc/os-release") as f:
                for line in f:
                    if line.startswith("ID="):
                        dist = line.split("=")[1].strip().strip('"')
                        os_info["distribution"] = dist
                        os_info["is_kali"] = "kali" in dist.lower()
                        os_info["is_parrot"] = "parrot" in dist.lower()
                    elif line.startswith("VERSION_ID="):
                        os_info["version"] = line.split("=")[1].strip().strip('"')
    except Exception as e:
        logger.warning(f"Error detecting OS: {e}")
    
    return os_info


# =============================================================================
# TOOL CATALOGS
# =============================================================================

# Metasploit Framework
METASPLOIT_TOOLS = {
    "msfconsole": {
        "id": "msfconsole",
        "name": "Metasploit Console",
        "description": "Framework de explotación y post-explotación",
        "category": "exploitation",
        "command": "msfconsole",
        "package_name": "metasploit-framework",
        "repo_url": None,
        "install_method": "apt",
        "requires_root": True,
        "parameters": [
            {"name": "resource_file", "type": "file", "description": "RC file con comandos", "required": False}
        ]
    },
    "msfvenom": {
        "id": "msfvenom",
        "name": "MSFVenom Payload Generator",
        "description": "Generador de payloads Metasploit",
        "category": "exploitation",
        "command": "msfvenom",
        "package_name": "metasploit-framework",
        "repo_url": None,
        "install_method": "apt",
        "requires_root": False,
        "parameters": [
            {"name": "payload", "type": "string", "description": "Tipo de payload", "required": True},
            {"name": "lhost", "type": "string", "description": "IP del listener", "required": True},
            {"name": "lport", "type": "integer", "description": "Puerto del listener", "required": True},
            {"name": "format", "type": "string", "description": "Formato de salida (exe, elf, raw)", "required": True}
        ]
    },
    "meterpreter": {
        "id": "meterpreter",
        "name": "Meterpreter Sessions",
        "description": "Post-explotación avanzada con Meterpreter (parte de Metasploit)",
        "category": "exploitation",
        "command": "msfconsole",
        "package_name": "metasploit-framework",
        "repo_url": None,
        "install_method": "apt",
        "requires_root": True,
        "parameters": [
            {"name": "session_id", "type": "integer", "description": "ID de la sesión Meterpreter", "required": False},
            {"name": "command", "type": "string", "description": "Comando Meterpreter a ejecutar", "required": True}
        ]
    }
}

# M365 & Azure AD Tools
M365_TOOLS = {
    "sparrow": {
        "id": "sparrow",
        "name": "Sparrow365",
        "description": "Detección de compromisos en M365 y Azure AD",
        "category": "m365_forensics",
        "command": "pwsh",
        "package_name": None,
        "repo_url": "https://github.com/cisagov/Sparrow",
        "install_method": "github",
        "install_path": "/opt/forensics-tools/Sparrow",
        "requires_root": False,
        "parameters": [
            {"name": "tenant_id", "type": "string", "description": "Azure Tenant ID", "required": True},
            {"name": "days_to_search", "type": "integer", "description": "Días a analizar", "required": False, "default": 90}
        ]
    },
    "hawk": {
        "id": "hawk",
        "name": "Hawk",
        "description": "Análisis forense de compromisos Exchange/M365",
        "category": "m365_forensics",
        "command": "pwsh",
        "package_name": None,
        "repo_url": "https://github.com/T0pCyber/hawk",
        "install_method": "powershell_gallery",
        "requires_root": False,
        "parameters": [
            {"name": "tenant", "type": "string", "description": "Dominio del tenant", "required": True}
        ]
    },
    "o365spray": {
        "id": "o365spray",
        "name": "o365spray",
        "description": "Password spraying contra Office 365",
        "category": "m365_recon",
        "command": "o365spray",
        "package_name": None,
        "repo_url": "https://github.com/0xZDH/o365spray",
        "install_method": "pip",
        "pip_package": "o365spray",
        "requires_root": False,
        "parameters": [
            {"name": "target", "type": "string", "description": "Usuario o dominio", "required": True},
            {"name": "passwords", "type": "file", "description": "Lista de contraseñas", "required": True}
        ]
    },
    "azurehound": {
        "id": "azurehound",
        "name": "AzureHound",
        "description": "Mapeo de Azure AD con BloodHound",
        "category": "m365_recon",
        "command": "azurehound",
        "package_name": None,
        "repo_url": "https://github.com/BloodHoundAD/AzureHound",
        "install_method": "github_release",
        "requires_root": False,
        "parameters": [
            {"name": "tenant", "type": "string", "description": "Tenant ID", "required": True}
        ]
    },
    "roadrecon": {
        "id": "roadrecon",
        "name": "ROADrecon",
        "description": "Azure AD reconnaissance framework",
        "category": "m365_recon",
        "command": "roadrecon",
        "package_name": None,
        "repo_url": "https://github.com/dirkjanm/ROADtools",
        "install_method": "pip",
        "pip_package": "roadrecon",
        "requires_root": False,
        "parameters": []
    }
}

# BlueTeam / Purple Team Tools
BLUETEAM_TOOLS = {
    "bluehunter": {
        "id": "bluehunter",
        "name": "BlueHunter",
        "description": "Threat hunting en sistemas Windows",
        "category": "threat_hunting",
        "command": "python3",
        "package_name": None,
        "repo_url": "https://github.com/arlessweschler/BlueHunter",
        "install_method": "github",
        "install_path": "/opt/forensics-tools/BlueHunter",
        "requires_root": False,
        "parameters": []
    },
    "chainsaw": {
        "id": "chainsaw",
        "name": "Chainsaw",
        "description": "Análisis rápido de logs de Windows",
        "category": "log_analysis",
        "command": "chainsaw",
        "package_name": None,
        "repo_url": "https://github.com/WithSecureLabs/chainsaw",
        "install_method": "github_release",
        "requires_root": False,
        "parameters": [
            {"name": "evtx_path", "type": "directory", "description": "Directorio con logs EVTX", "required": True}
        ]
    },
    "sigma": {
        "id": "sigma",
        "name": "Sigma Rules",
        "description": "Reglas de detección genéricas para SIEM",
        "category": "detection_rules",
        "command": None,
        "package_name": None,
        "repo_url": "https://github.com/SigmaHQ/sigma",
        "install_method": "github",
        "install_path": "/opt/forensics-tools/sigma",
        "requires_root": False,
        "parameters": []
    },
    "velociraptor": {
        "id": "velociraptor",
        "name": "Velociraptor",
        "description": "Plataforma de respuesta a incidentes y threat hunting",
        "category": "edr",
        "command": "velociraptor",
        "package_name": None,
        "repo_url": "https://github.com/Velocidex/velociraptor",
        "install_method": "github_release",
        "requires_root": True,
        "parameters": []
    },
    "atomic-red-team": {
        "id": "atomic-red-team",
        "name": "Atomic Red Team",
        "description": "Tests de seguridad automatizados para simular ataques (Purple Team)",
        "category": "purple_team",
        "command": "pwsh",
        "package_name": None,
        "repo_url": "https://github.com/redcanaryco/atomic-red-team",
        "install_method": "github",
        "install_path": "/opt/forensics-tools/atomic-red-team",
        "requires_root": False,
        "parameters": [
            {"name": "technique", "type": "string", "description": "ID de técnica MITRE ATT&CK (ej: T1059.001)", "required": True}
        ]
    },
    "caldera": {
        "id": "caldera",
        "name": "CALDERA",
        "description": "Plataforma de adversary emulation automatizada (Red/Purple Team)",
        "category": "purple_team",
        "command": "python3",
        "package_name": None,
        "repo_url": "https://github.com/mitre/caldera",
        "install_method": "github",
        "install_path": "/opt/forensics-tools/caldera",
        "requires_root": False,
        "parameters": [
            {"name": "operation", "type": "string", "description": "Nombre de la operación a ejecutar", "required": True}
        ]
    },
    "breach-attack-simulation": {
        "id": "breach-attack-simulation",
        "name": "Breach and Attack Simulation",
        "description": "Framework BAS para validar controles de seguridad",
        "category": "purple_team",
        "command": "python3",
        "package_name": None,
        "repo_url": "https://github.com/NextronSystems/APTSimulator",
        "install_method": "github",
        "install_path": "/opt/forensics-tools/APTSimulator",
        "requires_root": False,
        "parameters": []
    }
}

# Kali Metapackages
KALI_METAPACKAGES = {
    "kali-linux-large": {
        "id": "kali-linux-large",
        "name": "Kali Linux Large",
        "description": "Conjunto extendido de herramientas Kali (más de 100)",
        "category": "metapackage",
        "package_name": "kali-linux-large",
        "install_method": "apt",
        "size_mb": 9000,
        "tool_count": 100
    },
    "kali-linux-everything": {
        "id": "kali-linux-everything",
        "name": "Kali Linux Everything",
        "description": "Todas las herramientas de Kali Linux",
        "category": "metapackage",
        "package_name": "kali-linux-everything",
        "install_method": "apt",
        "size_mb": 15000,
        "tool_count": 600
    },
    "kali-tools-forensics": {
        "id": "kali-tools-forensics",
        "name": "Kali Forensics Tools",
        "description": "Herramientas de análisis forense",
        "category": "metapackage",
        "package_name": "kali-tools-forensics",
        "install_method": "apt",
        "size_mb": 500
    },
    "kali-tools-exploitation": {
        "id": "kali-tools-exploitation",
        "name": "Kali Exploitation Tools",
        "description": "Herramientas de explotación",
        "category": "metapackage",
        "package_name": "kali-tools-exploitation",
        "install_method": "apt",
        "size_mb": 800
    },
    "kali-tools-wireless": {
        "id": "kali-tools-wireless",
        "name": "Kali Wireless Tools",
        "description": "Herramientas de análisis WiFi",
        "category": "metapackage",
        "package_name": "kali-tools-wireless",
        "install_method": "apt",
        "size_mb": 300
    }
}

# Parrot Metapackages
PARROT_METAPACKAGES = {
    "parrot-tools-full": {
        "id": "parrot-tools-full",
        "name": "Parrot Tools Full",
        "description": "Todas las herramientas de Parrot OS",
        "category": "metapackage",
        "package_name": "parrot-tools-full",
        "install_method": "apt",
        "size_mb": 12000
    },
    "parrot-tools-cloud": {
        "id": "parrot-tools-cloud",
        "name": "Parrot Cloud Tools",
        "description": "Herramientas para pentesting cloud",
        "category": "metapackage",
        "package_name": "parrot-tools-cloud",
        "install_method": "apt",
        "size_mb": 400
    }
}

# =============================================================================
# DYNAMIC TOOL DISCOVERY
# =============================================================================

def get_installed_tools() -> Dict[str, bool]:
    """Verifica qué herramientas están instaladas"""
    installed = {}
    
    all_tools = {
        **METASPLOIT_TOOLS,
        **M365_TOOLS,
        **BLUETEAM_TOOLS
    }
    
    for tool_id, tool in all_tools.items():
        if tool.get("command"):
            installed[tool_id] = check_command_exists(tool["command"])
        elif tool.get("install_path"):
            installed[tool_id] = os.path.exists(tool["install_path"])
        else:
            installed[tool_id] = False
    
    return installed


def check_command_exists(command: str) -> bool:
    """Verifica si un comando existe en el sistema"""
    try:
        result = subprocess.run(
            ["which", command],
            capture_output=True,
            text=True,
            timeout=2
        )
        return result.returncode == 0
    except Exception:
        return False


async def get_tool_status(tool_id: str) -> str:
    """
    Retorna el estado de instalación de una herramienta
    
    Estados posibles:
    - "available": Instalado y funcional
    - "missing": No instalado
    - "partial": Instalado pero con dependencias faltantes
    - "unknown": No se pudo determinar
    """
    all_tools = {
        **METASPLOIT_TOOLS,
        **M365_TOOLS,
        **BLUETEAM_TOOLS
    }
    
    if tool_id not in all_tools:
        return "unknown"
    
    tool = all_tools[tool_id]
    
    # Verificar comando principal
    if tool.get("command"):
        if check_command_exists(tool["command"]):
            return "available"
        else:
            return "missing"
    
    # Verificar ruta de instalación
    if tool.get("install_path"):
        if os.path.exists(tool["install_path"]):
            return "available"
        else:
            return "missing"
    
    # Verificar repo GitHub clonado
    if tool.get("repo_url"):
        repo_name = tool["repo_url"].split("/")[-1].replace(".git", "")
        expected_path = f"/opt/forensics-tools/{repo_name}"
        if os.path.exists(expected_path):
            return "available"
        else:
            return "missing"
    
    return "unknown"


def get_all_tools_catalog() -> Dict[str, Any]:
    """Retorna catálogo completo con estado de instalación"""
    os_info = detect_os()
    installed = get_installed_tools()
    
    catalog = {
        "os_info": os_info,
        "categories": {},
        "total_tools": 0,
        "installed_count": 0
    }
    
    # Agregar todas las herramientas
    all_tools = {
        **METASPLOIT_TOOLS,
        **M365_TOOLS,
        **BLUETEAM_TOOLS
    }
    
    # Agregar metapaquetes según el OS
    if os_info["is_kali"]:
        all_tools.update(KALI_METAPACKAGES)
    elif os_info["is_parrot"]:
        all_tools.update(PARROT_METAPACKAGES)
    
    # Organizar por categoría
    for tool_id, tool_data in all_tools.items():
        category = tool_data.get("category", "other")
        
        if category not in catalog["categories"]:
            catalog["categories"][category] = {
                "name": category.replace("_", " ").title(),
                "tools": []
            }
        
        tool_info = {
            **tool_data,
            "installed": installed.get(tool_id, False),
            "can_install": tool_data.get("install_method") is not None
        }
        
        catalog["categories"][category]["tools"].append(tool_info)
        catalog["total_tools"] += 1
        if tool_info["installed"]:
            catalog["installed_count"] += 1
    
    return catalog


# =============================================================================
# AUTO-INSTALLATION
# =============================================================================

async def install_tool(tool_id: str) -> Dict[str, Any]:
    """Instala una herramienta automáticamente"""
    all_tools = {
        **METASPLOIT_TOOLS,
        **M365_TOOLS,
        **BLUETEAM_TOOLS,
        **KALI_METAPACKAGES,
        **PARROT_METAPACKAGES
    }
    
    if tool_id not in all_tools:
        return {"success": False, "error": "Tool not found"}
    
    tool = all_tools[tool_id]
    install_method = tool.get("install_method")
    
    logger.info(f"🔧 Installing {tool['name']} via {install_method}")
    
    try:
        if install_method == "apt":
            return await install_via_apt(tool)
        elif install_method == "github":
            return await install_from_github(tool)
        elif install_method == "github_release":
            return await install_from_github_release(tool)
        elif install_method == "pip":
            return await install_via_pip(tool)
        elif install_method == "powershell_gallery":
            return await install_from_powershell_gallery(tool)
        else:
            return {"success": False, "error": f"Unknown install method: {install_method}"}
    
    except Exception as e:
        logger.error(f"Installation failed: {e}")
        return {"success": False, "error": str(e)}


async def install_via_apt(tool: Dict) -> Dict[str, Any]:
    """Instala via apt-get"""
    package = tool.get("package_name")
    if not package:
        return {"success": False, "error": "No package name"}
    
    cmd = ["sudo", "apt-get", "install", "-y", package]
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()
    
    return {
        "success": process.returncode == 0,
        "output": stdout.decode()[:500],
        "error": stderr.decode()[:500] if process.returncode != 0 else None
    }


async def install_from_github(tool: Dict) -> Dict[str, Any]:
    """Clona repositorio desde GitHub"""
    repo_url = tool.get("repo_url")
    install_path = tool.get("install_path")
    
    if not repo_url or not install_path:
        return {"success": False, "error": "Missing repo_url or install_path"}
    
    # Crear directorio padre
    Path(install_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Clonar repo
    cmd = ["git", "clone", repo_url, install_path]
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()
    
    if process.returncode != 0:
        return {
            "success": False,
            "error": stderr.decode()[:500]
        }
    
    # Ejecutar instalación si existe script
    install_script = Path(install_path) / "install.sh"
    if install_script.exists():
        process = await asyncio.create_subprocess_exec(
            "bash", str(install_script),
            cwd=install_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        await process.communicate()
    
    return {"success": True, "output": "Installed from GitHub"}


async def install_from_github_release(tool: Dict) -> Dict[str, Any]:
    """Instala desde GitHub releases (binarios precompilados)"""
    # TODO: Implementar descarga de releases
    return {"success": False, "error": "Not implemented yet"}


async def install_via_pip(tool: Dict) -> Dict[str, Any]:
    """Instala via pip"""
    package = tool.get("pip_package")
    if not package:
        return {"success": False, "error": "No pip package"}
    
    cmd = ["pip3", "install", package]
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()
    
    return {
        "success": process.returncode == 0,
        "output": stdout.decode()[:500],
        "error": stderr.decode()[:500] if process.returncode != 0 else None
    }


async def install_from_powershell_gallery(tool: Dict) -> Dict[str, Any]:
    """Instala módulo de PowerShell Gallery"""
    module_name = tool.get("id")
    
    cmd = ["pwsh", "-Command", f"Install-Module -Name {module_name} -Force -Scope CurrentUser"]
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()
    
    return {
        "success": process.returncode == 0,
        "output": stdout.decode()[:500],
        "error": stderr.decode()[:500] if process.returncode != 0 else None
    }


# Import asyncio at the top
import asyncio
