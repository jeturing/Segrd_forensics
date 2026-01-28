"""
Security Tools Routes v4.7
==========================
Endpoints para herramientas de seguridad, catálogo extendido y sesiones.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from api.middleware.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/security-tools",
    tags=["Security Tools"]
)


# ============================================================================
# SCHEMAS
# ============================================================================

class QuickAction(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    category: str
    command: Optional[str] = None
    enabled: bool = True

class ToolCatalogItem(BaseModel):
    id: str
    name: str
    description: str
    category: str
    version: Optional[str] = None
    installed: bool = True
    enabled: bool = True
    path: Optional[str] = None

class ToolStatus(BaseModel):
    tool_id: str
    name: str
    status: str  # available, running, error, disabled
    last_run: Optional[datetime] = None
    version: Optional[str] = None


# ============================================================================
# QUICK ACTIONS
# ============================================================================

QUICK_ACTIONS = [
    {"id": "scan_host", "name": "Escanear Host", "description": "Escaneo rápido de puertos y servicios", "icon": "search", "category": "recon", "enabled": True},
    {"id": "check_creds", "name": "Verificar Credenciales", "description": "Buscar credenciales filtradas en HIBP/Dehashed", "icon": "key", "category": "osint", "enabled": True},
    {"id": "run_yara", "name": "Análisis YARA", "description": "Escanear archivos con reglas YARA", "icon": "shield", "category": "forensics", "enabled": True},
    {"id": "m365_audit", "name": "Auditoría M365", "description": "Revisar logs de Microsoft 365", "icon": "cloud", "category": "cloud", "enabled": True},
    {"id": "network_capture", "name": "Captura de Red", "description": "Iniciar captura de tráfico", "icon": "wifi", "category": "network", "enabled": True},
    {"id": "memory_dump", "name": "Dump de Memoria", "description": "Volcado de memoria para análisis", "icon": "cpu", "category": "forensics", "enabled": True},
    {"id": "hash_lookup", "name": "Buscar Hash", "description": "Verificar hash en VirusTotal/OTX", "icon": "hash", "category": "osint", "enabled": True},
    {"id": "dns_recon", "name": "Reconocimiento DNS", "description": "Enumerar registros DNS", "icon": "globe", "category": "recon", "enabled": True}
]


@router.get("/quick-actions")
async def get_quick_actions(
    category: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    ⚡ Obtener acciones rápidas disponibles.
    """
    actions = QUICK_ACTIONS
    
    if category:
        actions = [a for a in actions if a["category"] == category]
    
    return {
        "actions": actions,
        "categories": list(set(a["category"] for a in QUICK_ACTIONS))
    }


# ============================================================================
# EXTENDED CATALOG
# ============================================================================

TOOL_CATALOG = [
    # Forensics
    {"id": "loki", "name": "Loki Scanner", "description": "IOC and YARA scanner", "category": "forensics", "version": "0.51.0", "installed": True, "enabled": True},
    {"id": "yara", "name": "YARA", "description": "Pattern matching for malware", "category": "forensics", "version": "4.3.2", "installed": True, "enabled": True},
    {"id": "volatility", "name": "Volatility 3", "description": "Memory forensics framework", "category": "forensics", "version": "3.0.0", "installed": True, "enabled": True},
    {"id": "autopsy", "name": "Autopsy", "description": "Digital forensics platform", "category": "forensics", "version": "4.21", "installed": False, "enabled": False},
    
    # Recon
    {"id": "nmap", "name": "Nmap", "description": "Network scanner", "category": "recon", "version": "7.94", "installed": True, "enabled": True},
    {"id": "masscan", "name": "Masscan", "description": "Fast port scanner", "category": "recon", "version": "1.3.2", "installed": True, "enabled": True},
    {"id": "subfinder", "name": "Subfinder", "description": "Subdomain discovery", "category": "recon", "version": "2.6.3", "installed": True, "enabled": True},
    {"id": "amass", "name": "Amass", "description": "Attack surface mapping", "category": "recon", "version": "4.2.0", "installed": True, "enabled": True},
    
    # OSINT
    {"id": "theHarvester", "name": "theHarvester", "description": "Email/subdomain harvesting", "category": "osint", "version": "4.4.4", "installed": True, "enabled": True},
    {"id": "shodan", "name": "Shodan CLI", "description": "Shodan search engine", "category": "osint", "version": "1.31.0", "installed": True, "enabled": True},
    {"id": "spiderfoot", "name": "SpiderFoot", "description": "OSINT automation", "category": "osint", "version": "4.0", "installed": False, "enabled": False},
    
    # Cloud
    {"id": "sparrow", "name": "Sparrow", "description": "M365 forensics", "category": "cloud", "version": "1.0", "installed": True, "enabled": True},
    {"id": "hawk", "name": "Hawk", "description": "M365 investigation", "category": "cloud", "version": "3.0", "installed": True, "enabled": True},
    {"id": "monkey365", "name": "Monkey365", "description": "M365 security assessment", "category": "cloud", "version": "1.3", "installed": True, "enabled": True},
    {"id": "azurehound", "name": "AzureHound", "description": "Azure AD enumeration", "category": "cloud", "version": "2.1", "installed": True, "enabled": True},
    
    # Network
    {"id": "wireshark", "name": "Wireshark", "description": "Network protocol analyzer", "category": "network", "version": "4.2.0", "installed": True, "enabled": True},
    {"id": "tcpdump", "name": "tcpdump", "description": "Command-line packet analyzer", "category": "network", "version": "4.99.4", "installed": True, "enabled": True},
    {"id": "zeek", "name": "Zeek", "description": "Network security monitor", "category": "network", "version": "6.0.2", "installed": False, "enabled": False},
    
    # Exploitation
    {"id": "metasploit", "name": "Metasploit", "description": "Penetration testing framework", "category": "exploitation", "version": "6.3.45", "installed": True, "enabled": True},
    {"id": "nuclei", "name": "Nuclei", "description": "Vulnerability scanner", "category": "exploitation", "version": "3.1.0", "installed": True, "enabled": True},
    {"id": "sqlmap", "name": "SQLMap", "description": "SQL injection tool", "category": "exploitation", "version": "1.7.12", "installed": True, "enabled": True}
]


@router.get("/extended-catalog")
async def get_extended_catalog(
    category: Optional[str] = None,
    installed_only: bool = False,
    current_user: dict = Depends(get_current_user)
):
    """
    📚 Obtener catálogo extendido de herramientas.
    """
    tools = TOOL_CATALOG
    
    if category:
        tools = [t for t in tools if t["category"] == category]
    
    if installed_only:
        tools = [t for t in tools if t["installed"]]
    
    categories = {}
    for tool in TOOL_CATALOG:
        cat = tool["category"]
        if cat not in categories:
            categories[cat] = {"name": cat, "count": 0, "installed": 0}
        categories[cat]["count"] += 1
        if tool["installed"]:
            categories[cat]["installed"] += 1
    
    return {
        "tools": tools,
        "categories": list(categories.values()),
        "total": len(TOOL_CATALOG),
        "installed": len([t for t in TOOL_CATALOG if t["installed"]])
    }


# ============================================================================
# SESSION / STATUS
# ============================================================================

@router.get("/session")
async def get_session_info(
    current_user: dict = Depends(get_current_user)
):
    """
    🖥️ Obtener información de sesión del sistema operativo.
    """
    import os
    import platform
    
    return {
        "os": platform.system(),
        "os_release": platform.release(),
        "hostname": platform.node(),
        "arch": platform.machine(),
        "python_version": platform.python_version(),
        "user": os.getenv("USER", "forensics"),
        "home": os.getenv("HOME", "/home/forensics"),
        "cwd": os.getcwd(),
        "pid": os.getpid()
    }


@router.get("/status")
async def get_tools_status(
    current_user: dict = Depends(get_current_user)
):
    """
    📊 Obtener estado de las herramientas instaladas.
    """
    import shutil
    
    # Check common tools availability
    tools_status = []
    
    tools_to_check = [
        ("nmap", "nmap"),
        ("yara", "yara"),
        ("volatility", "vol.py"),
        ("tcpdump", "tcpdump"),
        ("wireshark", "tshark"),
        ("nuclei", "nuclei"),
        ("subfinder", "subfinder"),
        ("amass", "amass"),
        ("sqlmap", "sqlmap"),
        ("metasploit", "msfconsole")
    ]
    
    for tool_id, binary in tools_to_check:
        path = shutil.which(binary)
        tools_status.append({
            "tool_id": tool_id,
            "name": tool_id.capitalize(),
            "status": "available" if path else "not_found",
            "path": path,
            "version": None
        })
    
    available_count = len([t for t in tools_status if t["status"] == "available"])
    
    return {
        "tools": tools_status,
        "summary": {
            "total": len(tools_status),
            "available": available_count,
            "missing": len(tools_status) - available_count
        }
    }
