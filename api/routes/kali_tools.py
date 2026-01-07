"""
Kali Tools Router - API para explorar y ejecutar herramientas de seguridad
Proporciona catálogo visual organizado por categorías de trabajo
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio
import uuid
import logging
import re
import getpass
import os
import socket

from api.services.kali_tools import (
    get_all_tools,
    get_tools_by_category,
    get_tool_by_id,
    get_categories,
    get_tools_status,
    check_tool_availability,
    execute_tool,
    build_command,
    ToolCategory,
    ToolStatus
)

router = APIRouter(prefix="/api/kali-tools", tags=["Kali Tools"])
logger = logging.getLogger(__name__)

# Almacén de ejecuciones activas
active_executions: Dict[str, Dict] = {}

# Whitelist de metapaquetes Kali (instalación guiada)
ALLOWED_METAPACKAGES = {
    "kali-linux-everything",
    "kali-linux-default",
    "kali-linux-large",
    "kali-linux-top10",
    "kali-linux-headless",
    "kali-linux-nethunter",
    "kali-linux-core",
    "kali-linux-wireless",
    "kali-linux-web",
    "kali-linux-rfid",
    "kali-linux-voip",
    "kali-linux-full",
    "kali-linux-gpu",
    "kali-linux-pwtools",
    "kali-linux-sdr",
    "kali-linux-gaming",
    "kali-linux-forensic",
    "kali-linux-bluetooth",
    "kali-tools-top10",
    "kali-tools-forensics",
    "kali-tools-passwords",
    "kali-tools-wireless",
    "kali-tools-web",
    "kali-tools-crypto",
    "kali-tools-sdr",
    "kali-tools-voip",
    "kali-tools-gpu",
    "kali-tools-sniffing-spoofing",
    "kali-tools-vulnerability",
    "kali-tools-exploitation"
}


# ============================================================================
# MODELOS PYDANTIC
# ============================================================================

class ToolExecuteRequest(BaseModel):
    """Request para ejecutar una herramienta"""
    tool_id: str = Field(..., description="ID de la herramienta a ejecutar")
    params: Dict[str, Any] = Field(..., description="Parámetros de ejecución")
    case_id: Optional[str] = Field(None, description="ID del caso asociado (opcional)")


class ToolPreviewRequest(BaseModel):
    """Request para previsualizar comando"""
    tool_id: str
    params: Dict[str, Any]


class ToolExecuteResponse(BaseModel):
    """Response de ejecución"""
    execution_id: str
    tool_id: str
    tool_name: str
    status: str
    command: str
    output: Optional[str] = None
    stderr: Optional[str] = None
    duration_seconds: Optional[float] = None
    success: Optional[bool] = None
    error: Optional[str] = None
    timestamp: str
    run_as: Optional[str] = None
    hostname: Optional[str] = None
    shell: Optional[str] = None


class CategoryInfo(BaseModel):
    """Información de categoría"""
    id: str
    name: str
    count: int
    icon: str


class ToolInfo(BaseModel):
    """Información de herramienta"""
    id: str
    name: str
    description: str
    category: str
    icon: str
    requires_root: bool
    dangerous: bool
    status: str
    parameters: List[Dict]
    examples: List[str]


class InstallMetapackagesRequest(BaseModel):
    """Solicitud de instalación de metapaquetes Kali"""
    role: str = Field(..., description="blue, red, purple, hybrid, custom")
    packages: List[str] = Field(..., description="Metapaquetes aprobados")


def _get_os_session() -> Dict[str, str]:
    """Contexto de sesión del sistema operativo para auditar ejecución local."""
    user = os.getenv("SUDO_USER") or getpass.getuser()
    return {
        "user": user,
        "hostname": socket.gethostname(),
        "shell": os.getenv("SHELL", ""),
        "cwd": os.getcwd()
    }


# ============================================================================
# ENDPOINTS DE CATÁLOGO
# ============================================================================

@router.get("/session")
async def get_kali_session():
    """
    Retorna la sesión OS usada para ejecutar los comandos (autenticación local).
    Incluye usuario, hostname, shell y cwd actual.
    """
    return _get_os_session()

@router.get("/categories", response_model=List[CategoryInfo])
async def list_categories():
    """
    Lista todas las categorías de herramientas disponibles
    
    Categorías organizadas por tipo de trabajo de investigación:
    - reconnaissance: Reconocimiento inicial
    - scanning: Escaneo de puertos y servicios
    - enumeration: Enumeración de recursos
    - vulnerability: Análisis de vulnerabilidades
    - web: Análisis de aplicaciones web
    - network: Herramientas de red
    - password: Análisis de contraseñas
    - forensics: Análisis forense
    - osint: Inteligencia de fuentes abiertas
    - crypto: Análisis criptográfico
    """
    return get_categories()


@router.get("/tools", response_model=List[Dict])
async def list_all_tools(
    category: Optional[str] = None,
    available_only: bool = False
):
    """
    Lista todas las herramientas del catálogo
    
    - **category**: Filtrar por categoría (opcional)
    - **available_only**: Solo mostrar herramientas instaladas
    """
    if category:
        try:
            cat_enum = ToolCategory(category)
            tools = get_tools_by_category(cat_enum)
        except ValueError:
            raise HTTPException(400, f"Invalid category: {category}")
    else:
        tools = get_all_tools()
    
    # Añadir estado de disponibilidad
    tools_status = get_tools_status()
    for tool in tools:
        tool["status"] = tools_status.get(tool["id"], "unknown")
    
    if available_only:
        tools = [t for t in tools if t["status"] == "available"]
    
    return tools


@router.get("/tools/{tool_id}", response_model=Dict)
async def get_tool_details(tool_id: str):
    """
    Obtiene detalles completos de una herramienta específica
    
    Incluye:
    - Parámetros con tipos y validación
    - Ejemplos de uso
    - Estado de disponibilidad
    - Documentación
    """
    tool = get_tool_by_id(tool_id)
    if not tool:
        raise HTTPException(404, f"Tool '{tool_id}' not found")
    
    tool_dict = tool.to_dict()
    tool_dict["status"] = check_tool_availability(tool_id).value
    
    return tool_dict


@router.get("/status")
async def get_all_tools_status():
    """
    Obtiene el estado de disponibilidad de todas las herramientas
    
    Estados posibles:
    - available: Instalada y lista para usar
    - not_installed: No instalada en el sistema
    - requires_root: Necesita privilegios de administrador
    """
    return get_tools_status()


# ============================================================================
# ENDPOINTS DE EJECUCIÓN
# ============================================================================

@router.post("/preview")
async def preview_command(request: ToolPreviewRequest):
    """
    Previsualiza el comando que se ejecutará sin ejecutarlo
    
    Útil para revisar el comando antes de ejecutar
    """
    tool = get_tool_by_id(request.tool_id)
    if not tool:
        raise HTTPException(404, f"Tool '{request.tool_id}' not found")
    
    try:
        cmd = build_command(request.tool_id, request.params)
        return {
            "tool_id": request.tool_id,
            "tool_name": tool.name,
            "command": " ".join(cmd),
            "command_parts": cmd,
            "requires_root": tool.requires_root,
            "dangerous": tool.dangerous,
            "timeout_seconds": tool.timeout_seconds
        }
    except Exception as e:
        raise HTTPException(400, f"Error building command: {str(e)}")


@router.post("/execute", response_model=ToolExecuteResponse)
async def execute_tool_endpoint(
    request: ToolExecuteRequest,
    background_tasks: BackgroundTasks
):
    """
    Ejecuta una herramienta de seguridad
    
    La ejecución es síncrona para herramientas rápidas (<30s)
    o asíncrona para herramientas largas.
    
    ⚠️ **ADVERTENCIA**: Algunas herramientas pueden ser detectadas
    como intrusivas. Úselas solo en sistemas autorizados.
    """
    tool = get_tool_by_id(request.tool_id)
    if not tool:
        raise HTTPException(404, f"Tool '{request.tool_id}' not found")
    
    # Verificar disponibilidad
    status = check_tool_availability(request.tool_id)
    if status == ToolStatus.NOT_INSTALLED:
        raise HTTPException(
            400, 
            f"Tool '{tool.command}' is not installed. Install with: sudo apt install {tool.command}"
        )
    
    if status == ToolStatus.REQUIRES_ROOT:
        raise HTTPException(
            403,
            f"Tool '{tool.name}' requires root privileges"
        )
    
    execution_id = str(uuid.uuid4())[:8]
    
    logger.info(f"🔧 [{execution_id}] Starting execution of {tool.name}")
    
    # Ejecutar herramienta
    result = await execute_tool(request.tool_id, request.params)
    
    logger.info(f"✅ [{execution_id}] Completed {tool.name} - Success: {result.get('success')}")
    session_info = _get_os_session()
    
    return ToolExecuteResponse(
        execution_id=execution_id,
        tool_id=request.tool_id,
        tool_name=tool.name,
        status="completed" if result.get("success") else "failed",
        command=result.get("command", ""),
        output=result.get("output"),
        stderr=result.get("stderr"),
        duration_seconds=result.get("duration_seconds"),
        success=result.get("success"),
        error=result.get("error"),
        timestamp=datetime.now().isoformat(),
        run_as=session_info.get("user"),
        hostname=session_info.get("hostname"),
        shell=session_info.get("shell")
    )


@router.post("/execute/async")
async def execute_tool_async(
    request: ToolExecuteRequest,
    background_tasks: BackgroundTasks
):
    """
    Ejecuta una herramienta en background
    
    Retorna inmediatamente un execution_id para consultar el estado.
    Ideal para herramientas de larga duración.
    """
    tool = get_tool_by_id(request.tool_id)
    if not tool:
        raise HTTPException(404, f"Tool '{request.tool_id}' not found")
    
    execution_id = str(uuid.uuid4())
    session_info = _get_os_session()
    
    # Registrar ejecución
    active_executions[execution_id] = {
        "tool_id": request.tool_id,
        "tool_name": tool.name,
        "params": request.params,
        "status": "queued",
        "started_at": datetime.now().isoformat(),
        "output": "",
        "result": None,
        "session": session_info
    }
    
    async def run_in_background():
        active_executions[execution_id]["status"] = "running"
        result = await execute_tool(request.tool_id, request.params)
        active_executions[execution_id]["status"] = "completed" if result.get("success") else "failed"
        active_executions[execution_id]["result"] = result
        active_executions[execution_id]["completed_at"] = datetime.now().isoformat()
    
    background_tasks.add_task(run_in_background)
    
    return {
        "execution_id": execution_id,
        "tool_id": request.tool_id,
        "tool_name": tool.name,
        "status": "queued",
        "message": f"Tool execution queued. Check status at /api/kali-tools/executions/{execution_id}"
    }


@router.get("/executions/{execution_id}")
async def get_execution_status(execution_id: str):
    """
    Obtiene el estado de una ejecución asíncrona
    """
    if execution_id not in active_executions:
        raise HTTPException(404, f"Execution '{execution_id}' not found")
    
    return active_executions[execution_id]


@router.get("/executions")
async def list_executions():
    """
    Lista todas las ejecuciones activas y recientes
    """
    return {
        "active": len([e for e in active_executions.values() if e["status"] in ["queued", "running"]]),
        "total": len(active_executions),
        "executions": list(active_executions.values())
    }


# ============================================================================
# INSTALACIÓN DE METAPAQUETES KALI (ROLES)
# ============================================================================

def _validate_packages(packages: List[str]) -> List[str]:
    """Valida metapaquetes contra whitelist y formato seguro"""
    cleaned = []
    for pkg in packages:
        if not re.match(r"^[a-z0-9][a-z0-9\\-\\.]+$", pkg):
            raise HTTPException(400, f"Nombre de paquete inválido: {pkg}")
        if pkg not in ALLOWED_METAPACKAGES:
            raise HTTPException(400, f"Paquete no permitido: {pkg}")
        cleaned.append(pkg)
    return cleaned


async def _run_cmd(cmd: List[str]) -> Dict[str, Any]:
    """Ejecuta comando y retorna stdout/stderr"""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    return {
        "command": " ".join(cmd),
        "stdout": stdout.decode(errors="ignore"),
        "stderr": stderr.decode(errors="ignore"),
        "returncode": proc.returncode
    }


@router.post("/install")
async def install_metapackages(request: InstallMetapackagesRequest):
    """
    Instala metapaquetes Kali por rol (blue/red/purple/hybrid/custom).
    Usa los meta paquetes oficiales de Kali Linux.
    """
    packages = _validate_packages(request.packages)
    
    if not packages:
        raise HTTPException(400, "Debe enviar al menos un metapaquete")
    
    logger.info(f"⬇️ Instalando metapaquetes para rol {request.role}: {packages}")
    
    # Ejecutar update + install
    update_result = await _run_cmd(["sudo", "apt-get", "update"])
    install_result = await _run_cmd(["sudo", "apt-get", "install", "-y", *packages])
    
    return {
        "role": request.role,
        "packages": packages,
        "update": {"returncode": update_result["returncode"], "stdout": update_result["stdout"], "stderr": update_result["stderr"][-1000:]},
        "install": {"returncode": install_result["returncode"], "stdout": install_result["stdout"], "stderr": install_result["stderr"][-1000:]},
        "success": install_result["returncode"] == 0
    }


# ============================================================================
# WEBSOCKET PARA STREAMING
# ============================================================================

# Almacén de conexiones WebSocket activas
ws_connections: Dict[str, WebSocket] = {}


@router.websocket("/ws/execute/{execution_id}")
async def websocket_tool_execution(websocket: WebSocket, execution_id: str):
    """
    WebSocket para recibir output de herramientas en tiempo real
    
    Envía líneas de output conforme se generan.
    Eventos:
    - tool_started: Inicio de ejecución
    - tool_output: Línea de output
    - tool_completed: Fin de ejecución
    - tool_error: Error durante ejecución
    """
    await websocket.accept()
    ws_connections[execution_id] = websocket
    
    logger.info(f"🔌 WebSocket connected for execution {execution_id}")
    
    try:
        while True:
            # Mantener conexión viva
            data = await websocket.receive_text()
            
            if data == "ping":
                await websocket.send_json({"type": "pong"})
            elif data.startswith("execute:"):
                # Formato: execute:tool_id:params_json
                parts = data.split(":", 2)
                if len(parts) >= 3:
                    tool_id = parts[1]
                    import json
                    params = json.loads(parts[2])
                    
                    # Ejecutar con streaming
                    await websocket.send_json({
                        "type": "tool_started",
                        "tool_id": tool_id,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    async def send_output(line: str):
                        await websocket.send_json({
                            "type": "tool_output",
                            "line": line,
                            "timestamp": datetime.now().isoformat()
                        })
                    
                    result = await execute_tool(tool_id, params, send_output)
                    
                    await websocket.send_json({
                        "type": "tool_completed",
                        "result": result,
                        "timestamp": datetime.now().isoformat()
                    })
    
    except WebSocketDisconnect:
        logger.info(f"🔌 WebSocket disconnected for execution {execution_id}")
    finally:
        ws_connections.pop(execution_id, None)


# ============================================================================
# ENDPOINTS DE UTILIDAD
# ============================================================================

@router.get("/search")
async def search_tools(q: str):
    """
    Busca herramientas por nombre o descripción
    """
    query = q.lower()
    tools = get_all_tools()
    
    results = []
    for tool in tools:
        if (query in tool["name"].lower() or 
            query in tool["description"].lower() or
            query in tool["id"].lower()):
            tool["status"] = check_tool_availability(tool["id"]).value
            results.append(tool)
    
    return {
        "query": q,
        "count": len(results),
        "tools": results
    }


@router.get("/quick-actions")
async def get_quick_actions():
    """
    Obtiene acciones rápidas predefinidas para investigaciones comunes
    """
    return [
        {
            "id": "domain_recon",
            "name": "🔍 Reconocimiento de Dominio",
            "description": "WHOIS + DNS + Subdominios",
            "tools": ["whois", "dig", "host"],
            "params_template": {"target": "{domain}"}
        },
        {
            "id": "web_scan",
            "name": "🌐 Análisis Web Básico",
            "description": "Headers + Tecnologías + Directorios",
            "tools": ["curl", "whatweb"],
            "params_template": {"url": "{url}"}
        },
        {
            "id": "network_scan",
            "name": "📡 Escaneo de Red",
            "description": "Ping + Traceroute + Puertos comunes",
            "tools": ["ping", "traceroute", "nmap_quick"],
            "params_template": {"target": "{ip}"}
        },
        {
            "id": "osint_user",
            "name": "🕵️ OSINT de Usuario",
            "description": "Búsqueda de username en redes sociales",
            "tools": ["sherlock"],
            "params_template": {"username": "{username}"}
        },
        {
            "id": "forensic_file",
            "name": "🔬 Análisis Forense de Archivo",
            "description": "Tipo + Strings + Metadatos + YARA",
            "tools": ["file", "strings", "exiftool", "yara_scan"],
            "params_template": {"file": "{file_path}"}
        },
        {
            "id": "ssl_analysis",
            "name": "🔐 Análisis SSL/TLS",
            "description": "Certificado + Configuración SSL",
            "tools": ["openssl", "sslyze"],
            "params_template": {"target": "{host}:443"}
        },
        {
            "id": "hash_crack",
            "name": "🔑 Identificar y Crackear Hash",
            "description": "Identifica tipo de hash",
            "tools": ["hashid"],
            "params_template": {"hash": "{hash_value}"}
        },
        {
            "id": "email_osint",
            "name": "📧 OSINT de Email/Dominio",
            "description": "theHarvester para emails y subdominios",
            "tools": ["theHarvester"],
            "params_template": {"domain": "{domain}"}
        }
    ]


@router.post("/quick-actions/{action_id}/execute")
async def execute_quick_action(
    action_id: str,
    params: Dict[str, str],
    background_tasks: BackgroundTasks
):
    """
    Ejecuta una acción rápida predefinida con múltiples herramientas
    """
    quick_actions = await get_quick_actions()
    action = next((a for a in quick_actions if a["id"] == action_id), None)
    
    if not action:
        raise HTTPException(404, f"Quick action '{action_id}' not found")
    
    execution_id = str(uuid.uuid4())[:8]
    results = []
    
    for tool_id in action["tools"]:
        tool = get_tool_by_id(tool_id)
        if not tool:
            continue
        
        # Construir parámetros para esta herramienta
        tool_params = {}
        for param in tool.parameters:
            if param.required:
                # Buscar en params o en template
                template_key = action["params_template"].get(param.name, "")
                if template_key.startswith("{") and template_key.endswith("}"):
                    param_name = template_key[1:-1]
                    if param_name in params:
                        tool_params[param.name] = params[param_name]
                elif param.name in params:
                    tool_params[param.name] = params[param.name]
        
        # Ejecutar herramienta
        if check_tool_availability(tool_id) == ToolStatus.AVAILABLE:
            result = await execute_tool(tool_id, tool_params)
            results.append({
                "tool_id": tool_id,
                "tool_name": tool.name,
                **result
            })
        else:
            results.append({
                "tool_id": tool_id,
                "tool_name": tool.name,
                "success": False,
                "error": "Tool not available"
            })
    
    return {
        "execution_id": execution_id,
        "action_id": action_id,
        "action_name": action["name"],
        "tools_executed": len(results),
        "results": results,
        "timestamp": datetime.now().isoformat()
    }


# ============================================================================
# EXTENDED CATALOG - M365, Metasploit, Purple Team, Auto-Install
# ============================================================================

@router.get("/extended-catalog")
async def get_extended_catalog():
    """
    Retorna catálogo extendido con:
    - Metasploit Framework (msfconsole, msfvenom, meterpreter)
    - Herramientas M365 (Sparrow, Hawk, o365spray, AzureHound, ROADtools)
    - BlueTeam/Purple Team (BlueHunter, Chainsaw, Velociraptor, Atomic Red Team)
    - Metapaquetes Kali/Parrot
    - Estado de instalación en tiempo real
    - Capacidad de auto-instalación desde GitHub
    """
    from api.services.tool_catalog_extended import get_all_tools_catalog
    
    catalog = get_all_tools_catalog()
    
    # El catálogo ya tiene el estado de instalación (campo "installed")
    # Solo necesitamos agregarlo en formato compatible con el frontend
    
    # Convertir formato de {"categories": {"cat1": {"tools": [...]}, ...}}
    # a {"cat1": [...], "cat2": [...], ...}
    formatted_catalog = {}
    
    if "categories" in catalog:
        for category_name, category_data in catalog["categories"].items():
            tools_list = category_data.get("tools", [])
            # Mapear "installed" a "status"
            for tool in tools_list:
                if tool.get("installed"):
                    tool["status"] = "available"
                else:
                    tool["status"] = "missing"
            formatted_catalog[category_name] = tools_list
    
    return formatted_catalog


@router.post("/install/{tool_id}")
async def install_tool_endpoint(tool_id: str, background_tasks: BackgroundTasks):
    """
    Instala una herramienta automáticamente
    
    Soporta:
    - apt-get (metapaquetes Kali/Parrot, Metasploit)
    - GitHub clone (Sparrow, Hawk, BlueHunter)
    - pip (o365spray, ROADrecon)
    - PowerShell Gallery (módulos PowerShell)
    - GitHub releases (binarios precompilados)
    """
    from api.services.tool_catalog_extended import install_tool
    
    execution_id = str(uuid.uuid4())[:8]
    
    # Ejecutar instalación en background
    async def run_installation():
        result = await install_tool(tool_id)
        active_executions[execution_id] = {
            "tool_id": tool_id,
            "status": "completed" if result["success"] else "failed",
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
    
    background_tasks.add_task(run_installation)
    
    return {
        "execution_id": execution_id,
        "tool_id": tool_id,
        "status": "installing",
        "message": f"Installing {tool_id}...",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/install/status/{execution_id}")
async def get_install_status(execution_id: str):
    """Obtiene el estado de una instalación"""
    if execution_id not in active_executions:
        raise HTTPException(404, "Installation not found")
    
    return active_executions[execution_id]


@router.get("/metapackages")
async def get_metapackages():
    """
    Lista metapaquetes disponibles según el OS
    
    Kali: kali-linux-large, kali-linux-everything, kali-tools-*
    Parrot: parrot-tools-full, parrot-tools-cloud
    """
    from api.services.tool_catalog_extended import detect_os, KALI_METAPACKAGES, PARROT_METAPACKAGES
    
    os_info = detect_os()
    
    if os_info["is_kali"]:
        packages = KALI_METAPACKAGES
    elif os_info["is_parrot"]:
        packages = PARROT_METAPACKAGES
    else:
        packages = {}
    
    return {
        "os_info": os_info,
        "metapackages": list(packages.values()),
        "total": len(packages)
    }


@router.get("/github/validate")
async def validate_github_repo(repo_url: str):
    """
    Valida un repositorio GitHub y extrae metadata
    
    Lee README, busca comandos de instalación, detecta lenguaje
    """
    import aiohttp
    import re
    
    # Extraer owner/repo de la URL
    match = re.search(r'github\.com/([^/]+)/([^/]+)', repo_url)
    if not match:
        raise HTTPException(400, "Invalid GitHub URL")
    
    owner, repo = match.groups()
    repo = repo.replace('.git', '')
    
    # Obtener info del repo via API
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.github.com/repos/{owner}/{repo}") as resp:
            if resp.status != 200:
                raise HTTPException(404, "Repository not found")
            
            repo_data = await resp.json()
        
        # Obtener README
        async with session.get(f"https://raw.githubusercontent.com/{owner}/{repo}/main/README.md") as resp:
            if resp.status == 200:
                readme = await resp.text()
            else:
                readme = ""
    
    # Extraer comandos de instalación del README
    install_commands = []
    for line in readme.split('\n'):
        if any(cmd in line.lower() for cmd in ['install', 'pip install', 'apt install', 'git clone']):
            install_commands.append(line.strip())
    
    return {
        "repo_url": repo_url,
        "name": repo_data.get("name"),
        "description": repo_data.get("description"),
        "language": repo_data.get("language"),
        "stars": repo_data.get("stargazers_count"),
        "topics": repo_data.get("topics", []),
        "install_commands": install_commands[:5],  # Top 5
        "suggested_category": suggest_category_from_topics(repo_data.get("topics", [])),
        "can_auto_install": len(install_commands) > 0
    }


def suggest_category_from_topics(topics: List[str]) -> str:
    """Sugiere categoría basada en topics de GitHub"""
    category_keywords = {
        "reconnaissance": ["recon", "osint", "enumeration", "discovery"],
        "exploitation": ["exploit", "payload", "metasploit", "rce"],
        "post_exploitation": ["post-exploitation", "privilege-escalation", "persistence"],
        "m365_forensics": ["office365", "microsoft365", "azuread", "azure"],
        "password_attacks": ["password", "hash", "crack", "brute-force"],
        "wireless": ["wifi", "wireless", "bluetooth", "rfid"],
        "web": ["web", "xss", "sqli", "burp"],
        "forensics": ["forensic", "dfir", "incident-response", "memory"],
        "malware": ["malware", "virus", "trojan", "ransomware"],
        "network": ["network", "scanner", "packet", "sniff"]
    }
    
    for category, keywords in category_keywords.items():
        if any(keyword in topic.lower() for topic in topics for keyword in keywords):
            return category
    
    return "other"


@router.post("/playbooks/generate/{tool_id}")
async def generate_playbook_for_tool(tool_id: str):
    """
    Genera un playbook SOAR automáticamente para una herramienta
    
    Analiza la documentación de la herramienta y crea:
    - Pasos de ejecución
    - Validaciones
    - Manejo de errores
    - Outputs esperados
    """
    from api.services.auto_playbooks import generate_tool_playbook
    from api.services.tool_catalog_extended import get_all_tools_catalog
    
    # Obtener info de la herramienta
    catalog = get_all_tools_catalog()
    tool = None
    for tools_list in catalog.values():
        for t in tools_list:
            if t["id"] == tool_id:
                tool = t
                break
        if tool:
            break
    
    if not tool:
        raise HTTPException(404, f"Tool {tool_id} not found")
    
    # Generar playbook
    playbook = await generate_tool_playbook(tool)
    
    return {
        "tool_id": tool_id,
        "playbook": playbook,
        "generated_at": datetime.now().isoformat(),
        "message": "Playbook generado automáticamente desde documentación"
    }


@router.get("/playbooks/investigation/{investigation_type}")
async def get_playbook_for_investigation(investigation_type: str):
    """
    Retorna playbook completo para un tipo de investigación
    
    Tipos soportados:
    - ransomware
    - phishing
    - data_breach
    - insider_threat
    - apt
    - m365_compromise
    """
    from api.services.auto_playbooks import get_playbook_for_investigation_type
    
    playbook = await get_playbook_for_investigation_type(investigation_type)
    
    return {
        "investigation_type": investigation_type,
        "playbook": playbook,
        "tools_required": playbook.get("tools", []),
        "estimated_duration": playbook.get("estimated_duration"),
        "message": "Playbook multi-herramienta generado"
    }
