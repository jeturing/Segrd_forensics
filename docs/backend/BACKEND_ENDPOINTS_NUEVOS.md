# 📦 BACKEND ENDPOINTS - Mobile Agents, Investigaciones, Active Investigation

**Ubicación**: `/home/hack/mcp-kali-forensics/api/routes/`

Estos archivos deben crearse o actualizarse en FastAPI para que el frontend funcione correctamente.

---

## 1️⃣ MOBILE AGENTS ENDPOINTS

**Archivo**: `api/routes/agents.py`

```python
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
import asyncio
import subprocess

router = APIRouter(prefix="/api/agents", tags=["Agents"])

class AgentInfo(BaseModel):
    id: str
    name: str
    type: str  # intune, osquery, velociraptor
    status: str  # online, offline
    last_seen: str
    os_version: str
    ip_address: str

class CommandRequest(BaseModel):
    command: str
    os_type: str = "windows"

class DeployRequest(BaseModel):
    agent_type: str  # intune, osquery, velociraptor
    platform: str  # windows, mac, linux
    case_id: Optional[str] = None

# GET /api/agents - Listar todos los agentes
@router.get("/", response_model=List[AgentInfo])
async def get_agents():
    """Obtiene lista de agentes conectados"""
    try:
        # Simular datos - implementar conexión con DB
        agents = [
            {
                "id": "agent-001",
                "name": "WORKSTATION-01",
                "type": "intune",
                "status": "online",
                "last_seen": "2 minutes ago",
                "os_version": "Windows 11 Pro",
                "ip_address": "192.168.1.100"
            }
        ]
        return agents
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# GET /api/agents/{agent_id} - Obtener detalles de agente
@router.get("/{agent_id}", response_model=AgentInfo)
async def get_agent(agent_id: str):
    """Obtiene detalles de un agente específico"""
    # Implementar búsqueda en DB
    pass

# POST /api/agents/deploy - Desplegar agente
@router.post("/deploy")
async def deploy_agent(deploy_req: DeployRequest, background_tasks: BackgroundTasks):
    """Genera código de deploy para un agente específico"""
    try:
        # Generar script según tipo
        scripts = {
            "intune": "# PowerShell - Intune Deploy...",
            "osquery": "#!/bin/bash # OSQuery Deploy...",
            "velociraptor": "#!/bin/bash # Velociraptor Deploy..."
        }
        return {
            "status": "success",
            "script": scripts.get(deploy_req.agent_type, ""),
            "platform": deploy_req.platform
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# POST /api/agents/{agent_id}/execute - Ejecutar comando
@router.post("/{agent_id}/execute")
async def execute_command(agent_id: str, cmd_req: CommandRequest):
    """Ejecuta un comando en un agente remoto"""
    try:
        # En caso de Intune: usar MS Graph API
        # En caso de OSQuery: usar OSQuery API
        # En caso de Velociraptor: usar Velociraptor API
        
        output = f"Executed: {cmd_req.command} on {agent_id}\n"
        return {
            "status": "success",
            "agent_id": agent_id,
            "command": cmd_req.command,
            "output": output,
            "execution_time": 1.5
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# POST /api/agents/{agent_id}/network/capture/start - Iniciar captura
@router.post("/{agent_id}/network/capture/start")
async def start_network_capture(agent_id: str):
    """Inicia captura de tráfico de red"""
    return {
        "status": "capturing",
        "capture_id": f"capture-{agent_id}-001",
        "start_time": "2025-12-05T14:32:00Z"
    }

# POST /api/agents/{agent_id}/network/capture/stop - Detener captura
@router.post("/{agent_id}/network/capture/stop")
async def stop_network_capture(agent_id: str):
    """Detiene captura de tráfico de red"""
    return {
        "status": "stopped",
        "packets": 1234,
        "file_size": "2.5 MB"
    }
```

---

## 2️⃣ INVESTIGACIONES ENDPOINTS

**Archivo**: `api/routes/investigations.py`

```python
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/api/investigations", tags=["Investigations"])

class Investigation(BaseModel):
    id: str
    name: str
    severity: str  # critical, high, medium, low
    status: str  # open, in-progress, on-hold, resolved, closed
    created_at: str
    updated_at: str
    assigned_to: str
    description: str
    iocs_count: int
    evidence_count: int

# GET /api/investigations - Listar investigaciones
@router.get("/", response_model=dict)
async def get_investigations(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = None,
    severity: Optional[str] = None
):
    """Obtiene lista de investigaciones con paginación"""
    return {
        "items": [
            {
                "id": "IR-2025-001",
                "name": "Análisis de abuso de envío de correo",
                "severity": "critical",
                "status": "in-progress",
                "created_at": "2025-12-01",
                "updated_at": "2025-12-05",
                "assigned_to": "Juan Pérez",
                "description": "Investigación de patrón anómalo",
                "iocs_count": 12,
                "evidence_count": 8
            }
        ],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": 24
        }
    }

# GET /api/investigations/{inv_id} - Detalles investigación
@router.get("/{inv_id}", response_model=Investigation)
async def get_investigation(inv_id: str):
    """Obtiene detalles de una investigación específica"""
    # Implementar búsqueda en DB
    pass

# POST /api/investigations - Crear investigación
@router.post("/", response_model=Investigation)
async def create_investigation(investigation: Investigation):
    """Crea una nueva investigación"""
    return investigation

# GET /api/investigations/{inv_id}/graph - Obtener grafo de ataque
@router.get("/{inv_id}/graph")
async def get_investigation_graph(inv_id: str):
    """Obtiene el grafo de ataque (cytoscape nodes/edges)"""
    return {
        "nodes": [
            {"data": {"id": "user1", "label": "usuario@empresa.com"}},
            {"data": {"id": "mailbox1", "label": "Mailbox compromizado"}}
        ],
        "edges": [
            {"data": {"source": "user1", "target": "mailbox1"}}
        ]
    }

# GET /api/investigations/{inv_id}/evidence - Evidencias
@router.get("/{inv_id}/evidence")
async def get_evidence(inv_id: str):
    """Obtiene evidencias del caso"""
    return {
        "evidence": [
            {"id": "ev-001", "type": "m365_log", "source": "Sparrow", "count": 156},
            {"id": "ev-002", "type": "oauth", "source": "Hawk", "count": 8}
        ]
    }

# GET /api/investigations/{inv_id}/iocs - IOCs
@router.get("/{inv_id}/iocs")
async def get_iocs(inv_id: str):
    """Obtiene IOCs del caso"""
    return {
        "iocs": [
            {"id": "ioc-001", "type": "email", "value": "attacker@external.com"},
            {"id": "ioc-002", "type": "ip", "value": "203.0.113.45"}
        ]
    }

# POST /api/investigations/{inv_id}/iocs - Agregar IOC
@router.post("/{inv_id}/iocs")
async def add_ioc(inv_id: str, ioc_data: dict):
    """Agrega un IOC a la investigación"""
    return {"status": "created", "ioc_id": "ioc-new-001"}

# GET /api/investigations/{inv_id}/report - Generar reporte
@router.get("/{inv_id}/report")
async def generate_report(inv_id: str, format: str = "pdf"):
    """Genera reporte de investigación (PDF o JSON)"""
    return {
        "status": "generated",
        "format": format,
        "download_url": f"/api/investigations/{inv_id}/report/download"
    }
```

---

## 3️⃣ ACTIVE INVESTIGATION ENDPOINTS

**Archivo**: `api/routes/active_investigation.py`

```python
from fastapi import APIRouter, HTTPException, WebSocket
from pydantic import BaseModel
import asyncio
import subprocess

router = APIRouter(prefix="/api/active-investigation", tags=["Active Investigation"])

class CommandExecutionRequest(BaseModel):
    agent_id: str
    command: str
    os_type: str = "windows"

# POST /api/active-investigation/execute - Ejecutar comando
@router.post("/execute")
async def execute_command_active(req: CommandExecutionRequest):
    """Ejecuta comando en modo investigación activa"""
    try:
        # Ejecutar vía agent
        result = f"Output from {req.agent_id}:\n"
        result += f"$ {req.command}\n"
        result += "[Simulated output]\n"
        
        return {
            "status": "completed",
            "command": req.command,
            "output": result,
            "execution_time": 1.5,
            "return_code": 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket para captura de red en tiempo real
@router.websocket("/ws/network-capture/{agent_id}")
async def websocket_network_capture(websocket: WebSocket, agent_id: str):
    """WebSocket para captura de red en tiempo real"""
    await websocket.accept()
    try:
        while True:
            # Simular paquetes
            packet = {
                "src": "192.168.1.100",
                "dst": "8.8.8.8",
                "protocol": "DNS",
                "size": 53,
                "timestamp": "2025-12-05T14:32:05Z"
            }
            await websocket.send_json(packet)
            await asyncio.sleep(0.5)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await websocket.close()

# POST /api/active-investigation/memory-dump - Captura de memoria
@router.post("/memory-dump")
async def request_memory_dump(agent_id: str):
    """Solicita captura de memoria del sistema"""
    return {
        "status": "dumping",
        "dump_id": f"memdump-{agent_id}-001",
        "size_estimate": "8 GB"
    }

# GET /api/active-investigation/memory-dump/{dump_id} - Descargar dump
@router.get("/memory-dump/{dump_id}")
async def download_memory_dump(dump_id: str):
    """Descarga archivo de dump de memoria"""
    return {
        "status": "ready",
        "download_url": f"/api/active-investigation/memory-dump/{dump_id}/download",
        "size": "8.2 GB",
        "hash": "sha256:abc123..."
    }
```

---

## 📊 RESUMEN DE ENDPOINTS

### Agents
```
GET    /api/agents                      - Listar agentes
GET    /api/agents/{id}                 - Detalles agente
POST   /api/agents/deploy               - Deploy agente
POST   /api/agents/{id}/execute         - Ejecutar comando
POST   /api/agents/{id}/network/capture/start
POST   /api/agents/{id}/network/capture/stop
```

### Investigations
```
GET    /api/investigations              - Listar investigaciones
GET    /api/investigations/{id}         - Detalles investigación
POST   /api/investigations              - Crear investigación
GET    /api/investigations/{id}/graph   - Grafo ataque
GET    /api/investigations/{id}/evidence
GET    /api/investigations/{id}/iocs
POST   /api/investigations/{id}/iocs
GET    /api/investigations/{id}/report
```

### Active Investigation
```
POST   /api/active-investigation/execute
WS     /api/active-investigation/ws/network-capture/{id}
POST   /api/active-investigation/memory-dump
GET    /api/active-investigation/memory-dump/{id}
```

---

## 🔧 CÓMO IMPLEMENTAR

1. Crea los archivos en `/home/hack/mcp-kali-forensics/api/routes/`
2. Actualiza `api/main.py` para incluir los routers:

```python
from api.routes import agents, investigations, active_investigation

app.include_router(agents.router)
app.include_router(investigations.router)
app.include_router(active_investigation.router)
```

3. Implementa la lógica de integración con:
   - **Intune**: Microsoft Graph API
   - **OSQuery**: OSQuery API
   - **Velociraptor**: Velociraptor API
   - **Investigaciones**: SQLite DB

---

## ⏱️ PRIORIDAD

1. ✅ **HECHO**: Frontend React (componentes, UI, navegación)
2. 📋 **TODO**: Backend FastAPI (endpoints, lógica)
3. 🔌 **INTEGRACIÓN**: Conectar con Intune/OSQuery/Velociraptor

El frontend está listo para producción. Solo faltan los endpoints del backend.

---

**Versión**: 1.0.0  
**Fecha**: 2025-12-05  
**Estado**: 🟡 Frontend Completo, Backend Pendiente
