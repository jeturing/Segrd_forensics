"""
MCP v4.1 - Agent Manager
Gestión de agentes Blue/Red/Purple para ejecución remota de herramientas.
Incluye: registro, autenticación, heartbeat, tareas, telemetría.
"""

import asyncio
import hashlib
import json
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
import logging

from api.config import settings
from api.database import get_db_context
from api.models.tools import (
    Agent, AgentTask, AgentCapability, AgentHeartbeat,
    AgentType, AgentStatus, AuditLog
)
from api.services.audit import record_audit_event

logger = logging.getLogger(__name__)


# =============================================================================
# AGENT REGISTRATION TOKEN MANAGER
# =============================================================================

class TokenManager:
    """Gestiona tokens de registro para agentes"""
    
    def __init__(self):
        self.pending_tokens: Dict[str, Dict] = {}  # token -> {expires, agent_type, tenant_id}
    
    def generate_registration_token(
        self,
        agent_type: AgentType,
        tenant_id: str,
        expires_hours: int = 24
    ) -> str:
        """Genera token de registro único"""
        token = secrets.token_urlsafe(32)
        
        self.pending_tokens[token] = {
            "agent_type": agent_type.value,
            "tenant_id": tenant_id,
            "expires": datetime.utcnow() + timedelta(hours=expires_hours),
            "created_at": datetime.utcnow()
        }
        
        logger.info(f"🔑 Generated registration token for {agent_type.value} agent")
        
        return token
    
    def validate_token(self, token: str) -> Optional[Dict]:
        """Valida token y retorna datos asociados"""
        data = self.pending_tokens.get(token)
        
        if not data:
            return None
        
        if datetime.utcnow() > data["expires"]:
            del self.pending_tokens[token]
            return None
        
        return data
    
    def consume_token(self, token: str) -> Optional[Dict]:
        """Consume y elimina token después de uso"""
        data = self.validate_token(token)
        if data:
            del self.pending_tokens[token]
        return data


# =============================================================================
# AGENT MANAGER
# =============================================================================

class AgentManager:
    """
    Gestor central de agentes Blue/Red/Purple.
    Maneja registro, autenticación, heartbeat y asignación de tareas.
    """
    
    def __init__(self):
        self.token_manager = TokenManager()
        self.connected_agents: Dict[str, Dict] = {}  # agent_id -> connection info
        self.heartbeat_tasks: Dict[str, asyncio.Task] = {}
        self.task_callbacks: Dict[str, Callable] = {}
    
    # -------------------------------------------------------------------------
    # AGENT REGISTRATION
    # -------------------------------------------------------------------------
    
    def create_registration_token(
        self,
        agent_type: AgentType,
        tenant_id: str,
        requested_by: str
    ) -> Dict[str, str]:
        """
        Crea token de registro para nuevo agente.
        
        Args:
            agent_type: Tipo de agente (blue/red/purple)
            tenant_id: ID del tenant
            requested_by: Usuario que solicita
        
        Returns:
            Dict con token e instrucciones
        """
        token = self.token_manager.generate_registration_token(
            agent_type=agent_type,
            tenant_id=tenant_id
        )
        
        # Log audit to file (no DB write by default to avoid saturation)
        record_audit_event(
            action="agent_token_created",
            action_type="create",
            resource_type="agent",
            resource_id=token[:16] + "...",
            details={
                "agent_type": agent_type.value,
                "tenant_id": tenant_id
            },
            user_id=requested_by,
            tenant_id=tenant_id,
            persist_to_db=False
        )
        
        # Generar comando de instalación
        mcp_url = f"http://{settings.HOST}:{settings.PORT}"
        
        install_command = f"""
# MCP Agent Installation
# Token válido por 24 horas

# 1. Descargar agente
curl -O {mcp_url}/static/agent/mcp-agent.py

# 2. Instalar dependencias
pip install websockets httpx cryptography

# 3. Ejecutar con token
python mcp-agent.py --register \\
    --token "{token}" \\
    --mcp-url "{mcp_url}" \\
    --type "{agent_type.value}"
"""
        
        return {
            "token": token,
            "expires_in": "24 hours",
            "agent_type": agent_type.value,
            "install_command": install_command.strip()
        }
    
    async def register_agent(
        self,
        token: str,
        agent_name: str,
        hostname: str,
        host_ip: str,
        os_info: str,
        public_key: str,
        capabilities: List[str]
    ) -> Dict[str, Any]:
        """
        Registra nuevo agente usando token.
        
        Args:
            token: Token de registro
            agent_name: Nombre del agente
            hostname: Nombre del host
            host_ip: IP del host
            os_info: Información del SO
            public_key: Clave pública para comunicación segura
            capabilities: Lista de herramientas/capacidades
        
        Returns:
            Dict con agent_id y configuración
        """
        # Validar token
        token_data = self.token_manager.consume_token(token)
        if not token_data:
            raise ValueError("Invalid or expired registration token")
        
        agent_type = AgentType(token_data["agent_type"])
        tenant_id = token_data["tenant_id"]
        
        # Generar ID y fingerprint
        agent_id = f"AGT-{uuid.uuid4().hex[:12].upper()}"
        fingerprint = hashlib.sha256(public_key.encode()).hexdigest()
        
        # Crear agente
        with get_db_context() as db:
            agent = Agent(
                id=agent_id,
                name=agent_name,
                agent_type=agent_type.value,
                status=AgentStatus.PENDING_APPROVAL.value,
                hostname=hostname,
                host_ip=host_ip,
                os_info=os_info,
                public_key=public_key,
                fingerprint=fingerprint,
                authorized=False,  # Requiere aprobación manual
                tenant_id=tenant_id,
                last_heartbeat=datetime.utcnow()
            )
            db.add(agent)
            
            # Registrar capacidades
            for cap_name in capabilities:
                cap = AgentCapability(
                    id=f"{agent_id}-CAP-{uuid.uuid4().hex[:6].upper()}",
                    agent_id=agent_id,
                    name=cap_name,
                    version="1.0",
                    is_available=True
                )
                db.add(cap)
            
            # Audit log (file-based; DB persistence off by default)
            record_audit_event(
                action="agent_registered",
                action_type="create",
                resource_type="agent",
                resource_id=agent_id,
                details={
                    "agent_name": agent_name,
                    "agent_type": agent_type.value,
                    "hostname": hostname,
                    "host_ip": host_ip,
                    "capabilities": capabilities
                },
                user_id="system",
                tenant_id=tenant_id,
                persist_to_db=False,
                db_session=db
            )
            
            db.commit()
        
        logger.info(f"🤖 Agent registered: {agent_name} ({agent_id}) - pending approval")
        
        return {
            "agent_id": agent_id,
            "status": "pending_approval",
            "message": "Agent registered successfully. Awaiting admin approval.",
            "fingerprint": fingerprint,
            "config": {
                "heartbeat_interval": 30,
                "task_poll_interval": 5,
                "max_concurrent_tasks": 3
            }
        }
    
    async def approve_agent(
        self,
        agent_id: str,
        approved_by: str
    ) -> bool:
        """Aprueba un agente pendiente"""
        with get_db_context() as db:
            agent = db.query(Agent).filter(Agent.id == agent_id).first()
            
            if not agent:
                raise ValueError(f"Agent {agent_id} not found")
            
            if agent.authorized:
                return True  # Ya aprobado
            
            agent.authorized = True
            agent.status = AgentStatus.ONLINE.value
            agent.authorized_by = approved_by
            agent.authorized_at = datetime.utcnow()
            # Audit log (file-based by default)
            record_audit_event(
                action="agent_approved",
                action_type="update",
                resource_type="agent",
                resource_id=agent_id,
                details={"approved_by": approved_by},
                user_id=approved_by,
                tenant_id=agent.tenant_id,
                persist_to_db=False,
                db_session=db
            )
            
            db.commit()
        
        logger.info(f"✅ Agent approved: {agent_id} by {approved_by}")
        
        return True
    
    async def revoke_agent(
        self,
        agent_id: str,
        revoked_by: str,
        reason: str = ""
    ) -> bool:
        """Revoca autorización de agente"""
        with get_db_context() as db:
            agent = db.query(Agent).filter(Agent.id == agent_id).first()
            
            if not agent:
                return False
            
            agent.authorized = False
            agent.status = AgentStatus.OFFLINE.value
            # Audit log
            record_audit_event(
                action="agent_revoked",
                action_type="delete",
                resource_type="agent",
                resource_id=agent_id,
                details={"revoked_by": revoked_by, "reason": reason},
                user_id=revoked_by,
                tenant_id=agent.tenant_id,
                persist_to_db=False,
                db_session=db
            )
            
            db.commit()
        
        # Desconectar si está conectado
        if agent_id in self.connected_agents:
            del self.connected_agents[agent_id]
        
        logger.warning(f"⛔ Agent revoked: {agent_id} - {reason}")
        
        return True
    
    # -------------------------------------------------------------------------
    # AGENT CONNECTION & HEARTBEAT
    # -------------------------------------------------------------------------
    
    async def connect_agent(
        self,
        agent_id: str,
        websocket: Any,
        fingerprint: str
    ) -> bool:
        """
        Conecta un agente vía WebSocket.
        
        Args:
            agent_id: ID del agente
            websocket: Conexión WebSocket
            fingerprint: Fingerprint de la clave pública
        
        Returns:
            True si la conexión es exitosa
        """
        with get_db_context() as db:
            agent = db.query(Agent).filter(Agent.id == agent_id).first()
            
            if not agent:
                logger.warning(f"Unknown agent attempted connection: {agent_id}")
                return False
            
            if not agent.authorized:
                logger.warning(f"Unauthorized agent attempted connection: {agent_id}")
                return False
            
            # Verificar fingerprint
            if agent.fingerprint != fingerprint:
                logger.error(f"Fingerprint mismatch for agent: {agent_id}")
                return False
            
            # Actualizar estado
            agent.status = AgentStatus.ONLINE.value
            agent.last_heartbeat = datetime.utcnow()
            db.commit()
        
        # Registrar conexión
        self.connected_agents[agent_id] = {
            "websocket": websocket,
            "connected_at": datetime.utcnow(),
            "last_heartbeat": datetime.utcnow()
        }
        
        # Iniciar monitor de heartbeat
        self.heartbeat_tasks[agent_id] = asyncio.create_task(
            self._monitor_heartbeat(agent_id)
        )
        
        logger.info(f"🔌 Agent connected: {agent_id}")
        
        return True
    
    async def disconnect_agent(self, agent_id: str):
        """Desconecta un agente"""
        if agent_id in self.connected_agents:
            del self.connected_agents[agent_id]
        
        if agent_id in self.heartbeat_tasks:
            self.heartbeat_tasks[agent_id].cancel()
            del self.heartbeat_tasks[agent_id]
        
        with get_db_context() as db:
            agent = db.query(Agent).filter(Agent.id == agent_id).first()
            if agent:
                agent.status = AgentStatus.OFFLINE.value
                db.commit()
        
        logger.info(f"🔌 Agent disconnected: {agent_id}")
    
    async def process_heartbeat(
        self,
        agent_id: str,
        metrics: Dict[str, Any]
    ):
        """Procesa heartbeat de agente"""
        if agent_id not in self.connected_agents:
            return
        
        self.connected_agents[agent_id]["last_heartbeat"] = datetime.utcnow()
        
        with get_db_context() as db:
            agent = db.query(Agent).filter(Agent.id == agent_id).first()
            if agent:
                agent.last_heartbeat = datetime.utcnow()
                agent.status = AgentStatus.ONLINE.value
                db.commit()
                # Record heartbeat in file to avoid DB saturation
                record_audit_event(
                    action="agent_heartbeat",
                    action_type="metric",
                    resource_type="agent",
                    resource_id=agent_id,
                    details=metrics,
                    user_id="system",
                    tenant_id=agent.tenant_id,
                    persist_to_db=False
                )
    
    async def _monitor_heartbeat(self, agent_id: str):
        """Monitorea heartbeat de agente, desconecta si expira"""
        timeout = 90  # 90 segundos sin heartbeat
        
        while agent_id in self.connected_agents:
            await asyncio.sleep(30)
            
            conn = self.connected_agents.get(agent_id)
            if not conn:
                break
            
            last_hb = conn.get("last_heartbeat")
            if last_hb and (datetime.utcnow() - last_hb).total_seconds() > timeout:
                logger.warning(f"⚠️ Agent heartbeat timeout: {agent_id}")
                await self.disconnect_agent(agent_id)
                break
    
    # -------------------------------------------------------------------------
    # TASK MANAGEMENT
    # -------------------------------------------------------------------------
    
    async def assign_task(
        self,
        agent_id: str,
        task_type: str,
        command: List[str],
        parameters: Dict[str, Any],
        case_id: str,  # v4.4: OBLIGATORIO
        timeout: int = 300,
        execution_id: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> str:
        """
        Asigna tarea a un agente.
        
        Args:
            agent_id: ID del agente
            task_type: Tipo de tarea
            command: Comando a ejecutar
            parameters: Parámetros adicionales
            case_id: ID del caso (OBLIGATORIO en v4.4)
            timeout: Timeout en segundos
            execution_id: ID de ejecución asociado
            created_by: Usuario que crea la tarea
        
        Returns:
            ID de la tarea
        """
        # v4.4: Validar case_id
        if not case_id:
            raise ValueError("case_id is required for all agent tasks in v4.4")
        
        # Verificar agente
        if agent_id not in self.connected_agents:
            raise ValueError(f"Agent {agent_id} is not connected")
        
        task_id = f"TASK-{uuid.uuid4().hex[:12].upper()}"
        
        with get_db_context() as db:
            task = AgentTask(
                id=task_id,
                agent_id=agent_id,
                execution_id=execution_id,
                task_type=task_type,
                command=json.dumps(command),
                parameters={**parameters, "case_id": case_id},  # v4.4: incluir case_id
                timeout_seconds=timeout,
                status="pending"
            )
            db.add(task)
            
            # Actualizar contador del agente
            agent = db.query(Agent).filter(Agent.id == agent_id).first()
            if agent:
                agent.current_tasks += 1
            
            db.commit()
        
        # Enviar al agente vía WebSocket
        conn = self.connected_agents[agent_id]
        websocket = conn["websocket"]
        
        await websocket.send(json.dumps({
            "type": "task_assigned",
            "task_id": task_id,
            "task_type": task_type,
            "command": command,
            "parameters": parameters,
            "case_id": case_id,  # v4.4: incluir case_id en mensaje
            "timeout": timeout
        }))
        
        logger.info(f"📋 Task assigned: {task_id} -> {agent_id} (case: {case_id})")
        
        return task_id
    
    async def process_task_result(
        self,
        agent_id: str,
        task_id: str,
        status: str,
        exit_code: int,
        output: str,
        error: Optional[str] = None
    ):
        """Procesa resultado de tarea completada"""
        with get_db_context() as db:
            task = db.query(AgentTask).filter(AgentTask.id == task_id).first()
            
            if not task:
                logger.warning(f"Unknown task result: {task_id}")
                return
            
            task.status = status
            task.exit_code = exit_code
            task.output_path = f"/tmp/task_output/{task_id}.txt"  # Simplificado
            task.error_output = error
            task.finished_at = datetime.utcnow()
            
            # Actualizar contador del agente
            agent = db.query(Agent).filter(Agent.id == agent_id).first()
            if agent:
                agent.current_tasks = max(0, agent.current_tasks - 1)
                agent.total_executions += 1
                if status == "completed":
                    agent.successful_executions += 1
                else:
                    agent.failed_executions += 1
            
            db.commit()
            
            # Callback si existe
            if task_id in self.task_callbacks:
                callback = self.task_callbacks.pop(task_id)
                await callback({
                    "task_id": task_id,
                    "status": status,
                    "exit_code": exit_code,
                    "output": output,
                    "error": error
                })
        
        logger.info(f"✅ Task completed: {task_id} - {status}")
    
    def register_task_callback(
        self,
        task_id: str,
        callback: Callable
    ):
        """Registra callback para cuando la tarea termine"""
        self.task_callbacks[task_id] = callback
    
    # -------------------------------------------------------------------------
    # AGENT QUERIES
    # -------------------------------------------------------------------------
    
    def get_agents(
        self,
        agent_type: Optional[str] = None,
        status: Optional[str] = None,
        tenant_id: Optional[str] = None
    ) -> List[Dict]:
        """Obtiene lista de agentes"""
        with get_db_context() as db:
            query = db.query(Agent)
            
            if agent_type:
                query = query.filter(Agent.agent_type == agent_type)
            if status:
                query = query.filter(Agent.status == status)
            if tenant_id:
                query = query.filter(Agent.tenant_id == tenant_id)
            
            agents = query.all()
        
        return [
            {
                "id": a.id,
                "name": a.name,
                "agent_type": a.agent_type,
                "status": a.status,
                "hostname": a.hostname,
                "host_ip": a.host_ip,
                "os_info": a.os_info,
                "authorized": a.authorized,
                "last_heartbeat": a.last_heartbeat.isoformat() if a.last_heartbeat else None,
                "current_tasks": a.current_tasks,
                "total_executions": a.total_executions,
                "successful_executions": a.successful_executions,
                "is_connected": a.id in self.connected_agents
            }
            for a in agents
        ]
    
    def get_agent_details(self, agent_id: str) -> Optional[Dict]:
        """Obtiene detalles de un agente"""
        with get_db_context() as db:
            agent = db.query(Agent).filter(Agent.id == agent_id).first()
            
            if not agent:
                return None
            
            # Obtener capacidades
            capabilities = db.query(AgentCapability).filter(
                AgentCapability.agent_id == agent_id
            ).all()
            
            # Obtener tareas recientes
            recent_tasks = db.query(AgentTask).filter(
                AgentTask.agent_id == agent_id
            ).order_by(
                AgentTask.created_at.desc()
            ).limit(10).all()
            
            # Obtener métricas recientes
            recent_metrics = db.query(AgentHeartbeat).filter(
                AgentHeartbeat.agent_id == agent_id
            ).order_by(
                AgentHeartbeat.timestamp.desc()
            ).limit(30).all()
        
        return {
            "id": agent.id,
            "name": agent.name,
            "agent_type": agent.agent_type,
            "status": agent.status,
            "hostname": agent.hostname,
            "host_ip": agent.host_ip,
            "os_info": agent.os_info,
            "authorized": agent.authorized,
            "authorized_by": agent.authorized_by,
            "authorized_at": agent.authorized_at.isoformat() if agent.authorized_at else None,
            "fingerprint": agent.fingerprint,
            "last_heartbeat": agent.last_heartbeat.isoformat() if agent.last_heartbeat else None,
            "current_tasks": agent.current_tasks,
            "total_executions": agent.total_executions,
            "successful_executions": agent.successful_executions,
            "failed_executions": agent.failed_executions,
            "success_rate": (
                agent.successful_executions / max(agent.total_executions, 1) * 100
            ),
            "created_at": agent.created_at.isoformat(),
            "is_connected": agent.id in self.connected_agents,
            "capabilities": [
                {"name": c.name, "version": c.version, "available": c.is_available}
                for c in capabilities
            ],
            "recent_tasks": [
                {
                    "id": t.id,
                    "type": t.task_type,
                    "status": t.status,
                    "created_at": t.created_at.isoformat(),
                    "finished_at": t.finished_at.isoformat() if t.finished_at else None
                }
                for t in recent_tasks
            ],
            "metrics": [
                {
                    "timestamp": m.timestamp.isoformat(),
                    "cpu": m.cpu_percent,
                    "memory": m.memory_percent,
                    "disk": m.disk_percent,
                    "tasks": m.active_tasks
                }
                for m in recent_metrics
            ]
        }
    
    def get_available_agents(
        self,
        agent_type: Optional[str] = None,
        required_capability: Optional[str] = None
    ) -> List[Dict]:
        """Obtiene agentes disponibles para tareas"""
        with get_db_context() as db:
            query = db.query(Agent).filter(
                Agent.authorized == True,
                Agent.status == AgentStatus.ONLINE.value
            )
            
            if agent_type:
                query = query.filter(Agent.agent_type == agent_type)
            
            agents = query.all()
            
            # Filtrar por capacidad si se requiere
            if required_capability:
                filtered = []
                for agent in agents:
                    caps = db.query(AgentCapability).filter(
                        AgentCapability.agent_id == agent.id,
                        AgentCapability.name == required_capability,
                        AgentCapability.is_available == True
                    ).first()
                    if caps:
                        filtered.append(agent)
                agents = filtered
        
        return [
            {
                "id": a.id,
                "name": a.name,
                "agent_type": a.agent_type,
                "hostname": a.hostname,
                "current_tasks": a.current_tasks,
                "load": a.current_tasks / 3 * 100  # Assuming max 3 tasks
            }
            for a in agents
        ]
    
    # -------------------------------------------------------------------------
    # AGENT SELECTION
    # -------------------------------------------------------------------------
    
    def select_best_agent(
        self,
        agent_type: Optional[str] = None,
        required_capability: Optional[str] = None
    ) -> Optional[str]:
        """
        Selecciona el mejor agente disponible basado en carga.
        
        Returns:
            ID del agente seleccionado o None
        """
        agents = self.get_available_agents(agent_type, required_capability)
        
        if not agents:
            return None
        
        # Ordenar por carga (menor primero)
        agents.sort(key=lambda a: a["current_tasks"])
        
        return agents[0]["id"]
    
    # -------------------------------------------------------------------------
    # AGENT COMMANDS
    # -------------------------------------------------------------------------
    
    async def send_command(
        self,
        agent_id: str,
        command_type: str,
        payload: Dict
    ):
        """Envía comando directo a un agente"""
        if agent_id not in self.connected_agents:
            raise ValueError(f"Agent {agent_id} not connected")
        
        conn = self.connected_agents[agent_id]
        websocket = conn["websocket"]
        
        await websocket.send(json.dumps({
            "type": command_type,
            **payload
        }))
    
    async def broadcast_to_agents(
        self,
        agent_type: Optional[str],
        message: Dict
    ):
        """Broadcast mensaje a todos los agentes de un tipo"""
        for agent_id, conn in self.connected_agents.items():
            with get_db_context() as db:
                agent = db.query(Agent).filter(Agent.id == agent_id).first()
                if agent and (not agent_type or agent.agent_type == agent_type):
                    try:
                        await conn["websocket"].send(json.dumps(message))
                    except Exception as e:
                        logger.warning(f"Failed to send to {agent_id}: {e}")


# =============================================================================
# SINGLETON
# =============================================================================

agent_manager = AgentManager()
