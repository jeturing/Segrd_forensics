"""
🖥️ Mobile Agents Management - Intune, OSQuery, Velociraptor integration
Endpoints para desplegar y ejecutar comandos en agentes remotos
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
import asyncio
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agents", tags=["Mobile Agents"])

# ============================================================================
# MODELOS PYDANTIC
# ============================================================================

class AgentInfo(BaseModel):
    """Información de agente conectado"""
    id: str
    name: str
    type: str  # intune, osquery, velociraptor
    status: str  # online, offline
    last_seen: str
    os_version: str
    ip_address: str
    platform: str = "windows"  # windows, macos, linux, ios, android
    agent_version: Optional[str] = None
    capabilities: Optional[List[str]] = None

class CommandRequest(BaseModel):
    """Solicitud de ejecución de comando"""
    command: str
    os_type: str = "windows"
    timeout: int = 300  # segundos
    case_id: Optional[str] = None

class DeployRequest(BaseModel):
    """Solicitud de despliegue de agente"""
    agent_type: str  # intune, osquery, velociraptor
    platform: str  # windows, mac, linux, ios, android
    case_id: Optional[str] = None
    tenant_id: Optional[str] = None

class CommandResult(BaseModel):
    """Resultado de ejecución de comando"""
    status: str
    agent_id: str
    command: str
    output: str
    error: Optional[str] = None
    execution_time: float
    return_code: Optional[int] = None
    timestamp: str

class NetworkCapture(BaseModel):
    """Información de captura de red"""
    capture_id: str
    status: str  # capturing, stopped, completed
    packets: int
    file_size: str
    start_time: str
    end_time: Optional[str] = None
    download_url: Optional[str] = None

# ============================================================================
# SIMULATED DATA
# ============================================================================

SIMULATED_AGENTS = [
    {
        "id": "agent-001",
        "name": "WORKSTATION-01",
        "type": "intune",
        "status": "online",
        "last_seen": "2 minutes ago",
        "os_version": "Windows 11 Pro",
        "ip_address": "192.168.1.100",
        "platform": "windows",
        "agent_version": "2.1.4",
        "capabilities": ["command_execution", "network_capture", "memory_dump"]
    },
    {
        "id": "agent-002",
        "name": "LAPTOP-MAC-01",
        "type": "osquery",
        "status": "online",
        "last_seen": "1 minute ago",
        "os_version": "macOS 14.1",
        "ip_address": "192.168.1.101",
        "platform": "macos",
        "agent_version": "5.8.2",
        "capabilities": ["osquery", "system_query", "file_monitoring"]
    },
    {
        "id": "agent-003",
        "name": "SERVER-PROD-01",
        "type": "velociraptor",
        "status": "offline",
        "last_seen": "45 minutes ago",
        "os_version": "Ubuntu 22.04",
        "ip_address": "192.168.1.50",
        "platform": "linux",
        "agent_version": "0.72.1",
        "capabilities": ["artifact_collection", "registry_analysis", "file_system_analysis"]
    }
]

AGENT_TYPES = {
    "intune": {
        "name": "Microsoft Intune",
        "description": "Mobile Device Management via Intune",
        "platforms": ["windows", "macos", "ios", "android"],
        "features": ["Remote execution", "Device management", "Compliance check"]
    },
    "osquery": {
        "name": "OSQuery",
        "description": "OS instrumentation framework",
        "platforms": ["windows", "macos", "linux"],
        "features": ["System query", "File monitoring", "Process analysis"]
    },
    "velociraptor": {
        "name": "Velociraptor",
        "description": "Endpoint monitoring and threat hunting",
        "platforms": ["windows", "macos", "linux"],
        "features": ["Artifact collection", "Registry analysis", "YARA scanning"]
    }
}

# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/", response_model=List[AgentInfo])
async def get_agents(
    status: Optional[str] = None,
    agent_type: Optional[str] = None
):
    """
    📋 Listar todos los agentes conectados
    
    Query Parameters:
    - status: Filtrar por estado (online, offline)
    - agent_type: Filtrar por tipo (intune, osquery, velociraptor)
    """
    try:
        agents = SIMULATED_AGENTS.copy()
        
        if status:
            agents = [a for a in agents if a["status"] == status]
        
        if agent_type:
            agents = [a for a in agents if a["type"] == agent_type]
        
        logger.info(f"📋 Retornando {len(agents)} agentes")
        return agents
    
    except Exception as e:
        logger.error(f"❌ Error al listar agentes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{agent_id}", response_model=AgentInfo)
async def get_agent(agent_id: str):
    """
    🔍 Obtener detalles de un agente específico
    
    Path Parameters:
    - agent_id: ID del agente (ej: agent-001)
    """
    try:
        for agent in SIMULATED_AGENTS:
            if agent["id"] == agent_id:
                logger.info(f"🔍 Detalles del agente {agent_id}")
                return agent
        
        raise HTTPException(status_code=404, detail=f"Agente {agent_id} no encontrado")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error al obtener detalles del agente: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/types")
async def get_agent_types():
    """
    📊 Obtener tipos de agentes disponibles
    """
    return AGENT_TYPES

@router.post("/deploy")
async def deploy_agent(
    deploy_req: DeployRequest,
    background_tasks: BackgroundTasks
):
    """
    🚀 Desplegar nuevo agente
    
    Body:
    {
        "agent_type": "intune|osquery|velociraptor",
        "platform": "windows|mac|linux|ios|android",
        "case_id": "optional-case-id",
        "tenant_id": "optional-tenant-id"
    }
    
    Response: Script de despliegue listo para copiar/ejecutar
    """
    try:
        # Validar tipo de agente
        if deploy_req.agent_type not in AGENT_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Tipo de agente inválido: {deploy_req.agent_type}"
            )
        
        # Validar plataforma
        agent_info = AGENT_TYPES[deploy_req.agent_type]
        if deploy_req.platform not in agent_info["platforms"]:
            raise HTTPException(
                status_code=400,
                detail=f"Plataforma {deploy_req.platform} no soportada para {deploy_req.agent_type}"
            )
        
        # Generar script según tipo
        scripts = {
            "intune": f"""
# Intune Deploy Script - {deploy_req.platform.upper()}
# Instalación via PowerShell (Admin required)

# 1. Registrar en Intune
Add-AppxPackage -Path "https://intune.microsoft.com/enrollment"

# 2. Configurar policies
Set-IntunePolicy -PolicyName "Forensics-Discovery"

# 3. Iniciar agente
Start-Service IntuneMgmt

echo "✅ Intune agent deployed"
""",
            "osquery": f"""
#!/bin/bash
# OSQuery Deploy Script - {deploy_req.platform.upper()}

# 1. Descargar OSQuery
{"brew install osquery" if deploy_req.platform == "mac" else "apt-get install osquery" if deploy_req.platform == "linux" else "choco install osquery"}

# 2. Configurar
sudo cp /etc/osquery/osquery.conf.d/forensics.conf /etc/osquery/

# 3. Iniciar servicio
sudo systemctl start osqueryd
sudo systemctl enable osqueryd

echo "✅ OSQuery deployed"
""",
            "velociraptor": f"""
#!/bin/bash
# Velociraptor Deploy Script - {deploy_req.platform.upper()}

# 1. Descargar Velociraptor
wget https://downloads.velocidex.com/velociraptor/latest

# 2. Configurar cliente
./velociraptor-v0.72 --config /etc/velociraptor/client.config.yaml

# 3. Conectar al servidor
./velociraptor-v0.72 client -v

echo "✅ Velociraptor deployed"
"""
        }
        
        deploy_script = scripts.get(deploy_req.agent_type, "# Unknown agent type")
        
        logger.info(f"🚀 Deploy script generado para {deploy_req.agent_type} ({deploy_req.platform})")
        
        return {
            "status": "success",
            "agent_type": deploy_req.agent_type,
            "platform": deploy_req.platform,
            "script": deploy_script,
            "instructions": [
                "1. Copiar el script completo",
                "2. Ejecutar en un terminal con permisos de administrador",
                "3. El agente se registrará automáticamente",
                "4. Verificar conectividad en la sección 'Agentes Activos'"
            ],
            "deployment_id": f"deploy-{deploy_req.agent_type}-{datetime.now().isoformat()}",
            "generated_at": datetime.now().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error en deploy: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{agent_id}/execute", response_model=CommandResult)
async def execute_command(
    agent_id: str,
    cmd_req: CommandRequest,
    background_tasks: BackgroundTasks
):
    """
    ⌨️ Ejecutar comando en un agente remoto
    
    Path Parameters:
    - agent_id: ID del agente
    
    Body:
    {
        "command": "tasklist /v",
        "os_type": "windows|mac|linux",
        "timeout": 300,
        "case_id": "optional-case-id"
    }
    
    Response: Resultado de ejecución con stdout/stderr
    """
    try:
        # Validar agente existe
        agent_found = any(a["id"] == agent_id for a in SIMULATED_AGENTS)
        if not agent_found:
            raise HTTPException(status_code=404, detail=f"Agente {agent_id} no encontrado")
        
        logger.info(f"⌨️ Ejecutando comando en {agent_id}: {cmd_req.command[:50]}...")
        
        # Simular ejecución
        start_time = datetime.now()
        await asyncio.sleep(1.5)  # Simular latencia de red
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # Output simulado según comando
        output_map = {
            "tasklist": "svchost.exe           1234\ncmd.exe                5678\npython.exe             9012",
            "netstat": "Proto  Local Address          Foreign Address        State\nTCP    192.168.1.100:443    203.0.113.45:12345   ESTABLISHED",
            "ps aux": "root        1  0.0  0.2  19224  1234 ?  Ss   Dec05   0:00 /sbin/init",
            "Get-Service": "Status   Name\n------   ----\nRunning  WinRM\nStopped  VSS",
            "default": f"Output: {cmd_req.command}\n[Command executed successfully]\nReturn code: 0"
        }
        
        output = output_map.get(cmd_req.command.strip(), output_map["default"])
        
        result = CommandResult(
            status="completed",
            agent_id=agent_id,
            command=cmd_req.command,
            output=output,
            execution_time=execution_time,
            return_code=0,
            timestamp=datetime.now().isoformat()
        )
        
        logger.info(f"✅ Comando completado en {agent_id} (tiempo: {execution_time}s)")
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error al ejecutar comando: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{agent_id}/network/capture/start", response_model=NetworkCapture)
async def start_network_capture(agent_id: str):
    """
    🔴 Iniciar captura de tráfico de red
    
    Path Parameters:
    - agent_id: ID del agente
    
    Response: Información de captura iniciada
    """
    try:
        # Validar agente
        agent = next((a for a in SIMULATED_AGENTS if a["id"] == agent_id), None)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agente {agent_id} no encontrado")
        
        logger.info(f"🔴 Iniciando captura de red en {agent_id}")
        
        return NetworkCapture(
            capture_id=f"capture-{agent_id}-{datetime.now().isoformat()}",
            status="capturing",
            packets=0,
            file_size="0 MB",
            start_time=datetime.now().isoformat(),
            download_url=None
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error al iniciar captura: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{agent_id}/network/capture/stop", response_model=NetworkCapture)
async def stop_network_capture(agent_id: str, capture_id: Optional[str] = None):
    """
    🛑 Detener captura de tráfico de red
    
    Path Parameters:
    - agent_id: ID del agente
    
    Query Parameters:
    - capture_id: ID de la captura (opcional)
    """
    try:
        logger.info(f"🛑 Deteniendo captura en {agent_id}")
        
        return NetworkCapture(
            capture_id=capture_id or f"capture-{agent_id}-001",
            status="stopped",
            packets=1234,
            file_size="2.5 MB",
            start_time=datetime.now().isoformat(),
            end_time=datetime.now().isoformat(),
            download_url=f"/api/agents/{agent_id}/network/capture/{capture_id}/download"
        )
    
    except Exception as e:
        logger.error(f"❌ Error al detener captura: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{agent_id}/network/capture/{capture_id}/download")
async def download_network_capture(agent_id: str, capture_id: str):
    """
    📥 Descargar archivo PCAP de captura de red
    
    Path Parameters:
    - agent_id: ID del agente
    - capture_id: ID de la captura
    """
    try:
        logger.info(f"📥 Descargando captura {capture_id} de {agent_id}")
        
        return {
            "status": "ready",
            "download_url": f"/tmp/{capture_id}.pcap",
            "size": "2.5 MB",
            "format": "PCAP",
            "packets_count": 1234,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"❌ Error al descargar captura: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{agent_id}/memory-dump")
async def request_memory_dump(agent_id: str, case_id: Optional[str] = None):
    """
    💾 Solicitar dump de memoria del sistema
    
    Path Parameters:
    - agent_id: ID del agente
    
    Query Parameters:
    - case_id: ID del caso forense (opcional)
    """
    try:
        agent = next((a for a in SIMULATED_AGENTS if a["id"] == agent_id), None)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agente {agent_id} no encontrado")
        
        logger.info(f"💾 Solicitando dump de memoria de {agent_id}")
        
        return {
            "status": "dumping",
            "dump_id": f"memdump-{agent_id}-{datetime.now().isoformat()}",
            "agent_id": agent_id,
            "size_estimate": "8 GB" if agent["platform"] in ["windows", "linux"] else "4 GB",
            "estimated_time": "5-15 minutes",
            "start_time": datetime.now().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error al solicitar dump: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{agent_id}/status")
async def get_agent_status(agent_id: str):
    """
    📊 Obtener estado detallado de un agente
    
    Path Parameters:
    - agent_id: ID del agente
    """
    try:
        agent = next((a for a in SIMULATED_AGENTS if a["id"] == agent_id), None)
        if not agent:
            raise HTTPException(status_code=404, detail=f"Agente {agent_id} no encontrado")
        
        return {
            "agent_id": agent_id,
            "name": agent["name"],
            "status": agent["status"],
            "cpu_usage": "15%",
            "memory_usage": "512 MB",
            "disk_usage": "45%",
            "network_latency": "12ms",
            "last_heartbeat": agent["last_seen"],
            "uptime": "45 days",
            "version": agent["agent_version"]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error al obtener estado: {e}")
        raise HTTPException(status_code=500, detail=str(e))
