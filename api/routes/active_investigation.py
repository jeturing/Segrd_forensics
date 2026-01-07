"""
⚡ Active Investigation v4.4 - Real-time Command Execution & Network Capture
Endpoints para análisis en tiempo real con CommandExecutor y captura de red
Completamente orientado a casos con persistencia de resultados
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
import asyncio
import logging

from core import process_manager, ProcessType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/active-investigation", tags=["Active Investigation"])

# Storage para resultados de investigación (v4.4: por caso)
investigation_results: Dict[str, List[Dict]] = {}  # case_id -> [results]
investigation_sessions: Dict[str, Dict] = {}  # session_id -> session_data

# ============================================================================
# MODELOS PYDANTIC v4.4
# ============================================================================

class CommandExecutionRequest(BaseModel):
    """Solicitud de ejecución de comando"""
    case_id: str = Field(..., description="ID del caso (OBLIGATORIO)")
    agent_id: str
    command: str
    os_type: str = "windows"  # windows, mac, linux
    timeout: int = 300
    save_to_timeline: bool = True
    analyze_with_llm: bool = False

class CommandExecutionResponse(BaseModel):
    """Respuesta de ejecución de comando"""
    execution_id: str
    case_id: str
    status: str
    command: str
    output: str
    error: Optional[str] = None
    execution_time: float
    return_code: int
    timestamp: str
    saved_to_timeline: bool = False
    llm_analysis: Optional[Dict] = None

class NetworkPacket(BaseModel):
    """Paquete de red capturado"""
    src: str
    dst: str
    protocol: str
    src_port: Optional[int] = None
    dst_port: Optional[int] = None
    size: int
    flags: Optional[str] = None
    timestamp: str

class NetworkCaptureSession(BaseModel):
    """Sesión de captura de red"""
    capture_id: str
    agent_id: str
    status: str  # capturing, stopped, completed
    packets_captured: int
    bytes_captured: int
    start_time: str
    stop_time: Optional[str] = None
    filters: Optional[str] = None

class MemoryDumpRequest(BaseModel):
    """Solicitud de dump de memoria"""
    case_id: str = Field(..., description="ID del caso (OBLIGATORIO)")
    agent_id: str
    format: str = "raw"  # raw, vmem, dump

# ============================================================================
# COMMAND TEMPLATES BY OS
# ============================================================================

COMMAND_TEMPLATES = {
    "windows": {
        "Processes": [
            "tasklist /v",
            "Get-Process | Select-Object Name, Id, Memory | Sort-Object Memory -Descending",
            "wmic process get name,processid,executablepath",
        ],
        "Network": [
            "netstat -ano",
            "Get-NetTCPConnection -State Established | Select-Object LocalAddress, LocalPort, RemoteAddress, RemotePort, State",
            "netstat -anob",
        ],
        "System": [
            "systeminfo",
            "Get-ComputerInfo",
            "wmic os get name,version,buildnumber",
        ],
        "Memory": [
            "wmic logicaldisk get name,size,freespace",
            "Get-Volume",
            "mem",
        ]
    },
    "mac": {
        "Processes": [
            "ps aux",
            "ps aux | grep -v grep | sort -k3 -nr | head -20",
            "top -b -n 1",
        ],
        "Network": [
            "lsof -i -P -n",
            "netstat -an",
            "ss -tulpn",
        ],
        "System": [
            "system_profiler SPSoftwareDataType",
            "uname -a",
            "df -h",
        ],
        "Memory": [
            "vm_stat",
            "free -h",
            "top -l 1",
        ]
    },
    "linux": {
        "Processes": [
            "ps aux",
            "ps aux | sort -k3 -nr | head -20",
            "top -b -n 1",
        ],
        "Network": [
            "ss -tulpn",
            "netstat -an",
            "lsof -i -P -n",
        ],
        "System": [
            "uname -a",
            "cat /etc/os-release",
            "df -h",
        ],
        "Memory": [
            "free -h",
            "cat /proc/meminfo",
            "vmstat 1 5",
        ]
    }
}

# ============================================================================
# SIMULATED DATA
# ============================================================================

SIMULATED_COMMAND_OUTPUTS = {
    "tasklist /v": """Image Name                     PID Session Name        Session#    Memory
========================= ======== ================ ======== ============
System                       4 Services              0      2,048 K
svchost.exe               1234 Services              0        512 K
cmd.exe                   5678 Console              1      1,024 K
powershell.exe            9012 Console              1      2,048 K
WinLogon.exe             11234 Services              0      1,536 K
""",
    "netstat -ano": """Active Connections
Proto  Local Address          Foreign Address        State           PID
TCP    192.168.1.100:443      203.0.113.45:12345    ESTABLISHED     5678
TCP    192.168.1.100:445      0.0.0.0:0              LISTENING       1234
TCP    192.168.1.100:3389     0.0.0.0:0              LISTENING       9012
UDP    192.168.1.100:53       0.0.0.0:0              BOUND TO PORT   1234
""",
    "ps aux": """USER        PID %CPU %MEM    VSZ   RSS TTY STAT START   TIME COMMAND
root          1  0.0  0.2  19224  1234 ?   Ss   Dec05   0:00 /sbin/init
root          2  0.0  0.0      0     0 ?   S    Dec05   0:00 [kthreadd]
www-data   5678  0.8  1.5 234567 12345 ?   S    14:32   0:05 python3 -m http.server
attacker   9012  2.1  3.2 567890 23456 ?   S    14:35   0:12 nc -l -p 4444
""",
    "df -h": """Filesystem     Size  Used Avail Use% Mounted on
/dev/sda1      100G   45G   50G  45% /
/dev/sda2       50G   12G   35G  25% /home
tmpfs           16G   20M  16G   1% /dev/shm
/dev/sdb1      500G  250G  250G  50% /data
""",
}

# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/execute", response_model=CommandExecutionResponse)
async def execute_command(req: CommandExecutionRequest):
    """
    ⌨️ Ejecutar comando en modo investigación activa v4.4
    
    Body:
    {
        "case_id": "IR-2025-001",  // OBLIGATORIO
        "agent_id": "agent-001",
        "command": "tasklist /v",
        "os_type": "windows",
        "timeout": 300,
        "save_to_timeline": true,
        "analyze_with_llm": false
    }
    
    Response: Salida del comando con timing y análisis
    """
    import uuid
    
    # v4.4: Validar case_id obligatorio
    if not req.case_id:
        raise HTTPException(
            status_code=400, 
            detail="case_id es OBLIGATORIO para todas las operaciones de investigación activa"
        )
    
    try:
        execution_id = f"EXEC-{uuid.uuid4().hex[:8].upper()}"
        start_time = datetime.now()
        
        logger.info(f"⌨️ Ejecutando: {req.command[:50]}... en {req.agent_id} (caso: {req.case_id})")
        
        # v4.4: Crear proceso trackeable
        process = process_manager.create_process(
            case_id=req.case_id,
            process_type=ProcessType.ANALYSIS,
            name=f"Command: {req.command[:30]}...",
            input_data={"agent_id": req.agent_id, "command": req.command}
        )
        
        # Validar agent_id format
        if not req.agent_id.startswith("agent-") and not req.agent_id.startswith("AGT-"):
            raise HTTPException(status_code=400, detail=f"Agent ID inválido: {req.agent_id}")
        
        process.start()
        process.update_progress(20, "Enviando comando")
        
        # Simular ejecución (en producción: conectar con agente real)
        await asyncio.sleep(1.2)  # Simular latencia de red
        
        process.update_progress(60, "Procesando respuesta")
        
        # Buscar output simulado
        output = SIMULATED_COMMAND_OUTPUTS.get(
            req.command.strip(),
            f"Output from command: {req.command}\n[Command executed successfully]\nReturn code: 0"
        )
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # v4.4: Guardar resultado en índice por caso
        result_data = {
            "execution_id": execution_id,
            "case_id": req.case_id,
            "agent_id": req.agent_id,
            "command": req.command,
            "output": output,
            "return_code": 0,
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat() + "Z"
        }
        
        if req.case_id not in investigation_results:
            investigation_results[req.case_id] = []
        investigation_results[req.case_id].append(result_data)
        
        # v4.4: Guardar en timeline si se solicita
        saved_to_timeline = False
        if req.save_to_timeline:
            # TODO: Integrar con timeline_service
            saved_to_timeline = True
            process.update_progress(80, "Guardando en timeline")
        
        # v4.4: Análisis LLM si se solicita
        llm_analysis = None
        if req.analyze_with_llm:
            process.update_progress(90, "Analizando con IA")
            # TODO: Integrar con LLM provider
            llm_analysis = {
                "summary": "Análisis pendiente de implementación",
                "suspicious_indicators": [],
                "recommendations": []
            }
        
        process.complete({"execution_id": execution_id})
        
        return CommandExecutionResponse(
            execution_id=execution_id,
            case_id=req.case_id,
            status="completed",
            command=req.command,
            output=output,
            execution_time=execution_time,
            return_code=0,
            timestamp=datetime.now().isoformat() + "Z",
            saved_to_timeline=saved_to_timeline,
            llm_analysis=llm_analysis
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error ejecutando comando: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# v4.4: Endpoint para obtener resultados por caso
@router.get("/results/{case_id}")
async def get_case_investigation_results(
    case_id: str,
    limit: int = Query(50, ge=1, le=500)
):
    """
    📋 Obtener resultados de investigación activa por caso
    
    v4.4: Todos los resultados están vinculados a un caso
    """
    results = investigation_results.get(case_id, [])
    
    # Ordenar por timestamp descendente
    results_sorted = sorted(results, key=lambda x: x.get("timestamp", ""), reverse=True)
    
    return {
        "case_id": case_id,
        "total_executions": len(results),
        "results": results_sorted[:limit]
    }


# v4.4: Endpoint para estadísticas por caso
@router.get("/stats/{case_id}")
async def get_case_investigation_stats(case_id: str):
    """
    📊 Obtener estadísticas de investigación activa por caso
    """
    results = investigation_results.get(case_id, [])
    
    # Calcular estadísticas
    total = len(results)
    agents_used = list(set(r.get("agent_id") for r in results))
    commands_executed = list(set(r.get("command") for r in results))
    
    avg_execution_time = 0
    if results:
        avg_execution_time = sum(r.get("execution_time", 0) for r in results) / total
    
    return {
        "case_id": case_id,
        "total_executions": total,
        "unique_agents": len(agents_used),
        "agents": agents_used,
        "unique_commands": len(commands_executed),
        "avg_execution_time": round(avg_execution_time, 2),
        "processes_running": len(process_manager.get_running_processes(case_id))
    }


@router.get("/templates")
async def get_command_templates(os_type: str = Query("windows", regex="^(windows|mac|linux)$")):
    """
    📚 Obtener plantillas de comandos por SO
    
    Query Parameters:
    - os_type: Sistema operativo (windows, mac, linux)
    
    Response: Comando por categoría
    """
    try:
        templates = COMMAND_TEMPLATES.get(os_type, {})
        logger.info(f"📚 Templates para {os_type}: {len(templates)} categorías")
        
        return {
            "os_type": os_type,
            "templates": templates,
            "categories": list(templates.keys()),
            "total_commands": sum(len(cmds) for cmds in templates.values())
        }
    
    except Exception as e:
        logger.error(f"❌ Error obteniendo templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/network-capture/start")
async def start_network_capture(
    agent_id: str,
    case_id: str = Query(..., description="ID del caso - OBLIGATORIO v4.4"),
    filter: Optional[str] = None,
    duration_seconds: int = Query(60, ge=10, le=3600)
):
    """
    🔴 Iniciar captura de tráfico de red
    
    v4.4: case_id obligatorio - toda captura vinculada a investigación
    
    Query Parameters:
    - agent_id: ID del agente
    - case_id: ID del caso (OBLIGATORIO)
    - filter: Filtro BPF (ej: "dst port 443", "src 192.168.1.100")
    - duration_seconds: Duración máxima de captura
    
    Response: Información de sesión de captura iniciada
    """
    try:
        if not agent_id.startswith("agent-"):
            raise HTTPException(status_code=400, detail=f"Agent ID inválido: {agent_id}")
        
        capture_id = f"capture-{case_id}-{agent_id.split('-')[1]}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # v4.4: Registrar proceso persistente
        process = process_manager.create_process(
            process_id=capture_id,
            case_id=case_id,
            process_type="network_capture",
            description=f"Captura de red en {agent_id} (filtro: {filter or 'all'})"
        )
        
        logger.info(f"🔴 Iniciando captura en {agent_id} para caso {case_id} (filtro: {filter or 'ninguno'})")
        
        # Almacenar en resultados del caso
        if case_id not in investigation_results:
            investigation_results[case_id] = []
        
        investigation_results[case_id].append({
            "type": "network_capture_start",
            "capture_id": capture_id,
            "agent_id": agent_id,
            "filter": filter,
            "duration_seconds": duration_seconds,
            "timestamp": datetime.now().isoformat()
        })
        
        return {
            "capture_id": capture_id,
            "case_id": case_id,
            "agent_id": agent_id,
            "status": "capturing",
            "packets_captured": 0,
            "bytes_captured": 0,
            "start_time": datetime.now().isoformat() + "Z",
            "filters": filter,
            "max_duration_seconds": duration_seconds,
            "process": {
                "process_id": process.process_id,
                "status": process.status
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error iniciando captura: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/network-capture/stop")
async def stop_network_capture(
    capture_id: str,
    save_to_evidence: bool = Query(True, description="Guardar PCAP en evidencia del caso")
):
    """
    🛑 Detener captura de tráfico de red
    
    v4.4: Guarda automáticamente en evidencia del caso
    
    Query Parameters:
    - capture_id: ID de la captura
    - save_to_evidence: Si guardar el PCAP en directorio de evidencia
    
    Response: Información final de captura
    """
    try:
        logger.info(f"🛑 Deteniendo captura {capture_id}")
        
        # Extraer case_id del capture_id (formato: capture-{case_id}-{agent}-{timestamp})
        parts = capture_id.split("-")
        case_id = parts[1] if len(parts) > 1 else "unknown"
        
        # Simular paquetes capturados (en producción: leer de tcpdump)
        packets_captured = 1234
        bytes_captured = 256789
        
        # v4.4: Marcar proceso como completado
        process_manager.complete_process(
            capture_id,
            result={
                "packets_captured": packets_captured,
                "bytes_captured": bytes_captured,
                "pcap_saved": save_to_evidence
            }
        )
        
        # Actualizar resultados del caso
        if case_id in investigation_results:
            investigation_results[case_id].append({
                "type": "network_capture_stop",
                "capture_id": capture_id,
                "packets_captured": packets_captured,
                "bytes_captured": bytes_captured,
                "timestamp": datetime.now().isoformat()
            })
        
        return {
            "status": "stopped",
            "capture_id": capture_id,
            "case_id": case_id,
            "packets_captured": packets_captured,
            "bytes_captured": bytes_captured,
            "size_mb": round(bytes_captured / 1024 / 1024, 2),
            "stop_time": datetime.now().isoformat() + "Z",
            "evidence_saved": save_to_evidence,
            "download_url": f"/api/active-investigation/network-capture/{capture_id}/download" if not save_to_evidence else None,
            "evidence_path": f"forensics-evidence/{case_id}/network/{capture_id}.pcap" if save_to_evidence else None
        }
    
    except Exception as e:
        logger.error(f"❌ Error deteniendo captura: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/network-capture/{capture_id}")
async def get_capture_packets(
    capture_id: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """
    📦 Obtener paquetes de una captura
    
    Path Parameters:
    - capture_id: ID de la captura
    
    Query Parameters:
    - limit: Máximo de paquetes a retornar
    - offset: Offset para paginación
    """
    try:
        logger.info(f"📦 Obteniendo paquetes de {capture_id} (limit: {limit}, offset: {offset})")
        
        # Simular paquetes
        packets = [
            {
                "src": "192.168.1.100",
                "dst": "8.8.8.8",
                "protocol": "DNS",
                "src_port": 53456,
                "dst_port": 53,
                "size": 64,
                "timestamp": f"2025-12-05T14:32:{i:02d}Z"
            }
            for i in range(limit)
        ]
        
        return {
            "capture_id": capture_id,
            "packets": packets,
            "total_packets": 1234,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < 1234
        }
    
    except Exception as e:
        logger.error(f"❌ Error obteniendo paquetes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/network-capture/{capture_id}/download")
async def download_network_capture(capture_id: str):
    """
    📥 Descargar archivo PCAP de captura
    
    Path Parameters:
    - capture_id: ID de la captura
    
    Response: URL de descarga
    """
    try:
        logger.info(f"📥 Descargando {capture_id}")
        
        return {
            "status": "ready",
            "capture_id": capture_id,
            "filename": f"{capture_id}.pcap",
            "format": "PCAP",
            "size_mb": 2.5,
            "packets": 1234,
            "download_url": f"/api/active-investigation/network-capture/{capture_id}/download/file",
            "expires_in": 3600
        }
    
    except Exception as e:
        logger.error(f"❌ Error descargando captura: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/memory-dump/request")
async def request_memory_dump(req: MemoryDumpRequest):
    """
    💾 Solicitar dump de memoria del sistema
    
    v4.4: case_id OBLIGATORIO, proceso persistente rastreado
    
    Body:
    {
        "agent_id": "agent-001",
        "case_id": "IR-2025-001",
        "format": "raw|vmem|dump"
    }
    
    Response: Información de dump iniciado
    """
    try:
        if not req.agent_id.startswith("agent-"):
            raise HTTPException(status_code=400, detail=f"Agent ID inválido: {req.agent_id}")
        
        dump_id = f"memdump-{req.case_id}-{req.agent_id.split('-')[1]}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # v4.4: Registrar proceso persistente
        process = process_manager.create_process(
            process_id=dump_id,
            case_id=req.case_id,
            process_type="memory_dump",
            description=f"Dump de memoria en {req.agent_id} (formato: {req.format})"
        )
        
        logger.info(f"💾 Dump de memoria solicitado en {req.agent_id} para caso {req.case_id} (formato: {req.format})")
        
        # Almacenar en resultados del caso
        if req.case_id not in investigation_results:
            investigation_results[req.case_id] = []
        
        investigation_results[req.case_id].append({
            "type": "memory_dump_request",
            "dump_id": dump_id,
            "agent_id": req.agent_id,
            "format": req.format,
            "timestamp": datetime.now().isoformat()
        })
        
        return {
            "status": "dumping",
            "dump_id": dump_id,
            "agent_id": req.agent_id,
            "format": req.format,
            "size_estimate_gb": 8,
            "estimated_time_minutes": 10,
            "start_time": datetime.now().isoformat() + "Z",
            "case_id": req.case_id,
            "process": {
                "process_id": process.process_id,
                "status": process.status
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error solicitando dump: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/memory-dump/{dump_id}/status")
async def get_memory_dump_status(dump_id: str):
    """
    ⏳ Obtener estado de dump de memoria
    
    v4.4: Usa ProcessManager para estado persistente
    
    Path Parameters:
    - dump_id: ID del dump
    """
    try:
        # v4.4: Obtener estado del ProcessManager
        process = process_manager.get_process(dump_id)
        
        if process:
            # Proceso registrado - usar estado real
            progress = process.progress or 0
            if process.status == "completed":
                progress = 100
            elif process.status == "failed":
                progress = process.progress or 0
            
            # Extraer case_id del dump_id
            parts = dump_id.split("-")
            case_id = parts[1] if len(parts) > 1 else "unknown"
            
            return {
                "dump_id": dump_id,
                "case_id": case_id,
                "status": process.status,
                "progress": progress,
                "eta_minutes": max(0, int((100 - progress) / 10)),
                "started_at": process.started_at,
                "error": process.error,
                "download_url": f"/api/active-investigation/memory-dump/{dump_id}/download" if process.status == "completed" else None,
                "evidence_path": f"forensics-evidence/{case_id}/memory/{dump_id}.raw" if process.status == "completed" else None
            }
        
        # Simular para dumps no registrados (legacy)
        status_map = {
            "dumping": {"progress": 45, "eta_minutes": 5},
            "compressing": {"progress": 75, "eta_minutes": 2},
            "completed": {"progress": 100, "eta_minutes": 0},
        }
        
        current_status = "completed"
        status_info = status_map[current_status]
        
        logger.info(f"⏳ Estado de {dump_id}: {current_status}")
        
        return {
            "dump_id": dump_id,
            "status": current_status,
            "progress": status_info["progress"],
            "eta_minutes": status_info["eta_minutes"],
            "download_url": f"/api/active-investigation/memory-dump/{dump_id}/download" if current_status == "completed" else None
        }
    
    except Exception as e:
        logger.error(f"❌ Error obteniendo estado: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/memory-dump/{dump_id}/download")
async def download_memory_dump(dump_id: str):
    """
    📥 Descargar archivo de dump de memoria
    
    Path Parameters:
    - dump_id: ID del dump
    """
    try:
        logger.info(f"📥 Descargando dump {dump_id}")
        
        return {
            "status": "ready",
            "dump_id": dump_id,
            "filename": f"{dump_id}.raw",
            "format": "raw",
            "size_gb": 8.2,
            "hash_sha256": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6",
            "download_url": f"/api/active-investigation/memory-dump/{dump_id}/download/file",
            "expires_in": 7200
        }
    
    except Exception as e:
        logger.error(f"❌ Error descargando dump: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/command-history/{agent_id}")
async def get_command_history(
    agent_id: str,
    case_id: str = Query(..., description="ID del caso - OBLIGATORIO v4.4"),
    limit: int = Query(100, ge=1, le=500)
):
    """
    📜 Obtener historial de comandos ejecutados
    
    v4.4: case_id obligatorio - historial vinculado a investigación
    
    Path Parameters:
    - agent_id: ID del agente
    
    Query Parameters:
    - case_id: ID del caso (OBLIGATORIO)
    - limit: Máximo de comandos a retornar
    """
    try:
        logger.info(f"📜 Historial de {agent_id} para caso {case_id} (limit: {limit})")
        
        # v4.4: Obtener historial real del caso
        case_results = investigation_results.get(case_id, [])
        
        # Filtrar por agent_id si especificado
        history = []
        for result in case_results:
            if result.get("type") == "command_execution":
                if agent_id == "all" or result.get("agent_id") == agent_id:
                    history.append({
                        "execution_id": result.get("execution_id"),
                        "command": result.get("command"),
                        "executed_at": result.get("timestamp"),
                        "execution_time": result.get("execution_time", 0),
                        "return_code": result.get("return_code", 0),
                        "output_preview": result.get("stdout", "")[:200]
                    })
        
        # Ordenar por timestamp descendente
        history = sorted(history, key=lambda x: x.get("executed_at", ""), reverse=True)[:limit]
        
        return {
            "agent_id": agent_id,
            "case_id": case_id,
            "total_commands": len(history),
            "history": history
        }
    
    except Exception as e:
        logger.error(f"❌ Error obteniendo historial: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/file-upload/{agent_id}")
async def upload_file_to_agent(
    agent_id: str,
    destination: str,
    case_id: str = Query(..., description="ID del caso - OBLIGATORIO v4.4")
):
    """
    📤 Cargar archivo a agente remoto
    
    v4.4: case_id obligatorio - operación vinculada a investigación
    
    Path Parameters:
    - agent_id: ID del agente
    
    Query Parameters:
    - destination: Ruta destino en el agente
    - case_id: ID del caso (OBLIGATORIO)
    """
    try:
        if not agent_id.startswith("agent-"):
            raise HTTPException(status_code=400, detail=f"Agent ID inválido: {agent_id}")
        
        upload_id = f"upload-{case_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        logger.info(f"📤 Cargando archivo a {agent_id} → {destination} (caso: {case_id})")
        
        # v4.4: Registrar en resultados del caso
        if case_id not in investigation_results:
            investigation_results[case_id] = []
        
        investigation_results[case_id].append({
            "type": "file_upload",
            "upload_id": upload_id,
            "agent_id": agent_id,
            "destination": destination,
            "timestamp": datetime.now().isoformat()
        })
        
        return {
            "status": "uploading",
            "agent_id": agent_id,
            "case_id": case_id,
            "destination": destination,
            "upload_id": upload_id,
            "started_at": datetime.now().isoformat() + "Z"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error cargando archivo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/file-download/{agent_id}")
async def download_file_from_agent(
    agent_id: str,
    source: str,
    case_id: str = Query(..., description="ID del caso - OBLIGATORIO v4.4"),
    save_to_evidence: bool = Query(True, description="Guardar en directorio de evidencia")
):
    """
    📥 Descargar archivo desde agente remoto
    
    v4.4: case_id obligatorio - archivo guardado como evidencia
    
    Path Parameters:
    - agent_id: ID del agente
    
    Query Parameters:
    - source: Ruta del archivo en el agente
    - case_id: ID del caso (OBLIGATORIO)
    - save_to_evidence: Si guardar en directorio de evidencia
    """
    try:
        if not agent_id.startswith("agent-"):
            raise HTTPException(status_code=400, detail=f"Agent ID inválido: {agent_id}")
        
        download_id = f"download-{case_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        filename = source.split("/")[-1] if "/" in source else source.split("\\")[-1]
        
        logger.info(f"📥 Descargando de {agent_id} → {source} (caso: {case_id})")
        
        # v4.4: Registrar en resultados del caso
        if case_id not in investigation_results:
            investigation_results[case_id] = []
        
        investigation_results[case_id].append({
            "type": "file_download",
            "download_id": download_id,
            "agent_id": agent_id,
            "source": source,
            "filename": filename,
            "timestamp": datetime.now().isoformat()
        })
        
        return {
            "status": "ready",
            "agent_id": agent_id,
            "case_id": case_id,
            "source": source,
            "filename": filename,
            "size_bytes": 256000,
            "download_url": f"/api/active-investigation/file-download/{agent_id}/file?source={source}" if not save_to_evidence else None,
            "evidence_path": f"forensics-evidence/{case_id}/files/{filename}" if save_to_evidence else None,
            "hash_md5": "d41d8cd98f00b204e9800998ecf8427e"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error descargando archivo: {e}")
        raise HTTPException(status_code=500, detail=str(e))
