"""
MCP v4.1 - Tool Executor Engine
Motor de ejecución segura de herramientas Kali con soporte híbrido (MCP + Agents)
Incluye: validación, sandbox, streaming, auditoría
"""

import asyncio
import hashlib
import json
import re
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple
import logging

from api.config import settings
from api.database import get_db_context
from api.models.tools import (
    ToolExecution, ExecutionStatus, ExecutionTarget, ToolRiskLevel,
    Agent, AgentTask, AuditLog
)
from api.services.audit import record_audit_event

logger = logging.getLogger(__name__)


# =============================================================================
# SECURITY CONFIGURATION
# =============================================================================

# Caracteres/patrones prohibidos en comandos
FORBIDDEN_PATTERNS = [
    r';',           # Command chaining
    r'&&',          # AND operator
    r'\|\|',        # OR operator
    r'\|(?!\s)',    # Pipe (except with space for filters)
    r'>',           # Redirect output
    r'<',           # Redirect input
    r'\$\(',        # Subshell
    r'`',           # Backtick subshell
    r'\.\.',        # Path traversal
    r'rm\s+-rf',    # Dangerous rm
    r'dd\s+if=',    # dd command
    r'mkfs',        # Format
    r':(){ :|:& };:',  # Fork bomb
]

# Herramientas permitidas por nivel de riesgo
TOOLS_BY_RISK_LEVEL = {
    ToolRiskLevel.SAFE: [
        "whois", "dig", "host", "nslookup", "ping", "traceroute",
        "file", "strings", "exiftool", "hashid", "curl"
    ],
    ToolRiskLevel.LOW: [
        "nmap", "whatweb", "dnsenum", "theHarvester", "amass",
        "gobuster", "dirb", "enum4linux", "smbclient"
    ],
    ToolRiskLevel.MEDIUM: [
        "nikto", "nuclei", "wpscan", "sqlmap", "yara", "loki",
        "volatility", "osqueryi", "tcpdump"
    ],
    ToolRiskLevel.HIGH: [
        "hydra", "medusa", "john", "hashcat", "netcat", "ncat"
    ],
    ToolRiskLevel.OFFENSIVE: [
        "msfconsole", "msfvenom", "impacket"
    ]
}

# Directorio base para outputs
EVIDENCE_BASE = settings.EVIDENCE_DIR / "tool_outputs"
EVIDENCE_BASE.mkdir(parents=True, exist_ok=True)


# =============================================================================
# COMMAND VALIDATION & SANITIZATION
# =============================================================================

class CommandValidator:
    """Valida y sanitiza comandos antes de ejecución"""
    
    @staticmethod
    def validate_command(command: str) -> Tuple[bool, str]:
        """
        Valida que el comando sea seguro.
        Returns: (is_valid, error_message)
        """
        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, command):
                return False, f"Forbidden pattern detected: {pattern}"
        
        return True, ""
    
    @staticmethod
    def sanitize_parameters(params: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitiza parámetros para evitar inyección"""
        sanitized = {}
        for key, value in params.items():
            if isinstance(value, str):
                # Remover caracteres peligrosos
                value = re.sub(r'[;&|`$><]', '', value)
                # Escapar comillas
                value = value.replace('"', '\\"').replace("'", "\\'")
            sanitized[key] = value
        return sanitized
    
    @staticmethod
    def get_tool_risk_level(tool_id: str) -> ToolRiskLevel:
        """Obtiene el nivel de riesgo de una herramienta"""
        for level, tools in TOOLS_BY_RISK_LEVEL.items():
            if tool_id in tools:
                return level
        return ToolRiskLevel.MEDIUM  # Default
    
    @staticmethod
    def check_permission(
        user_role: str,
        risk_level: ToolRiskLevel,
        tenant_settings: Dict
    ) -> Tuple[bool, str]:
        """Verifica si el usuario tiene permiso para ejecutar"""
        # Roles con permisos por nivel
        role_permissions = {
            "viewer": [ToolRiskLevel.SAFE],
            "analyst": [ToolRiskLevel.SAFE, ToolRiskLevel.LOW],
            "senior_analyst": [ToolRiskLevel.SAFE, ToolRiskLevel.LOW, ToolRiskLevel.MEDIUM],
            "dfir_engineer": [ToolRiskLevel.SAFE, ToolRiskLevel.LOW, ToolRiskLevel.MEDIUM, ToolRiskLevel.HIGH],
            "redteam_operator": list(ToolRiskLevel),
            "admin": list(ToolRiskLevel)
        }
        
        allowed = role_permissions.get(user_role, [])
        if risk_level not in allowed:
            return False, f"Role '{user_role}' cannot execute '{risk_level.value}' tools"
        
        # Verificar configuración del tenant
        if risk_level == ToolRiskLevel.OFFENSIVE:
            if not tenant_settings.get("enable_redteam", False):
                return False, "Red team tools not enabled for this tenant"
        
        return True, ""


# =============================================================================
# TOOL EXECUTOR ENGINE
# =============================================================================

class ToolExecutor:
    """
    Motor principal de ejecución de herramientas.
    Soporta ejecución local (MCP) y remota (Agents).
    """
    
    def __init__(self):
        self.active_processes: Dict[str, asyncio.subprocess.Process] = {}
        self.output_callbacks: Dict[str, List[Callable]] = {}
        self.validator = CommandValidator()
    
    # -------------------------------------------------------------------------
    # EJECUCIÓN LOCAL (MCP)
    # -------------------------------------------------------------------------
    
    async def execute_local(
        self,
        execution_id: str,
        tool_id: str,
        command: List[str],
        working_dir: Optional[str] = None,
        timeout: int = 300,
        output_callback: Optional[Callable[[str, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta herramienta localmente en el servidor MCP.
        
        Args:
            execution_id: ID de la ejecución
            tool_id: ID de la herramienta
            command: Lista de argumentos del comando
            working_dir: Directorio de trabajo
            timeout: Timeout en segundos
            output_callback: Función para streaming de output
        
        Returns:
            Dict con resultados de la ejecución
        """
        start_time = datetime.utcnow()
        output_lines = []
        error_lines = []
        
        # Crear directorio para output
        output_dir = EVIDENCE_BASE / execution_id
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "output.txt"
        
        try:
            # Validar comando
            cmd_str = " ".join(command)
            is_valid, error = self.validator.validate_command(cmd_str)
            if not is_valid:
                raise SecurityError(f"Command validation failed: {error}")
            
            logger.info(f"🔧 [{execution_id}] Executing: {cmd_str[:100]}...")
            
            # Crear proceso
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir
            )
            
            self.active_processes[execution_id] = process
            
            # Streaming de output
            async def read_stream(stream, stream_type):
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    
                    decoded = line.decode('utf-8', errors='replace')
                    
                    if stream_type == "stdout":
                        output_lines.append(decoded)
                    else:
                        error_lines.append(decoded)
                    
                    if output_callback:
                        await output_callback(stream_type, decoded)
            
            # Leer stdout y stderr en paralelo con timeout
            try:
                await asyncio.wait_for(
                    asyncio.gather(
                        read_stream(process.stdout, "stdout"),
                        read_stream(process.stderr, "stderr")
                    ),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise TimeoutError(f"Execution timed out after {timeout}s")
            
            # Esperar que termine
            exit_code = await process.wait()
            
            # Combinar output
            full_output = "".join(output_lines)
            full_error = "".join(error_lines)
            
            # Guardar output
            with open(output_file, "w") as f:
                f.write(f"=== COMMAND ===\n{cmd_str}\n\n")
                f.write(f"=== STDOUT ===\n{full_output}\n\n")
                f.write(f"=== STDERR ===\n{full_error}\n")
            
            # Calcular hash
            output_hash = hashlib.sha256(full_output.encode()).hexdigest()
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            logger.info(f"✅ [{execution_id}] Completed in {duration:.2f}s, exit code: {exit_code}")
            
            return {
                "success": exit_code == 0,
                "exit_code": exit_code,
                "output": full_output,
                "error": full_error,
                "output_file": str(output_file),
                "output_hash": output_hash,
                "output_size": len(full_output),
                "duration_seconds": duration,
                "command": cmd_str
            }
            
        except Exception as e:
            logger.error(f"❌ [{execution_id}] Failed: {str(e)}")
            return {
                "success": False,
                "exit_code": -1,
                "error": str(e),
                "output": "".join(output_lines),
                "duration_seconds": (datetime.utcnow() - start_time).total_seconds()
            }
        finally:
            self.active_processes.pop(execution_id, None)

    # ---------------------------------------------------------------------
    # EJECUCIÓN LOCAL CON SANDBOX (PENTEST)
    # ---------------------------------------------------------------------

    async def execute_sandboxed(
        self,
        execution_id: str,
        tool_id: str,
        command: Any,
        timeout: int = 300,
        sandbox_type: str = None
    ) -> Dict[str, Any]:
        """Ejecuta comando en modo sandboxed.

        Acepta command como lista o string. Si sandbox está habilitado en
        settings y sandbox_type es "firejail", envuelve el comando.
        """

        # Normalizar comando a lista
        if isinstance(command, str):
            import shlex
            command_list = shlex.split(command)
        else:
            command_list = list(command)

        # Opcional: envolver en firejail
        if settings.PENTEST_SANDBOX_ENABLED and (sandbox_type or settings.PENTEST_EXECUTOR_TYPE) == "firejail":
            command_list = ["firejail", "--quiet"] + command_list

        result = await self.execute_local(
            execution_id=execution_id,
            tool_id=tool_id,
            command=command_list,
            timeout=timeout
        )

        # Adjuntar parsing rápido
        parsed = None
        if isinstance(result, dict) and result.get("output"):
            from api.services.autonomous_pentest import _parse_tool_output
            parsed = _parse_tool_output(tool_id, result.get("output", ""))
            result["parsed"] = parsed
        return result
    
    # -------------------------------------------------------------------------
    # EJECUCIÓN REMOTA (AGENTS)
    # -------------------------------------------------------------------------
    
    async def execute_remote(
        self,
        execution_id: str,
        agent_id: str,
        tool_id: str,
        command: List[str],
        timeout: int = 300,
        output_callback: Optional[Callable[[str, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta herramienta en un agente remoto.
        Crea AgentTask y espera resultado vía WebSocket.
        """
        from api.services.websocket_manager import manager as ws_manager
        
        with get_db_context() as db:
            # Verificar agente
            agent = db.query(Agent).filter(Agent.id == agent_id).first()
            if not agent:
                raise ValueError(f"Agent {agent_id} not found")
            
            if agent.status != "online":
                raise ValueError(f"Agent {agent_id} is not online (status: {agent.status})")
            
            if not agent.authorized:
                raise ValueError(f"Agent {agent_id} is not authorized")
            
            # Crear tarea
            task = AgentTask(
                id=AgentTask.generate_id(),
                agent_id=agent_id,
                execution_id=execution_id,
                command=json.dumps(command),
                parameters={},
                timeout_seconds=timeout,
                status="pending"
            )
            db.add(task)
            
            # Actualizar contador del agente
            agent.current_tasks += 1
            db.commit()
            
            task_id = task.id
        
        # Enviar tarea al agente vía WebSocket
        await ws_manager.send_to_agent(agent_id, {
            "type": "task_assigned",
            "task_id": task_id,
            "execution_id": execution_id,
            "command": command,
            "timeout": timeout
        })
        
        # Esperar resultado (el agente responderá vía WS)
        result = await self._wait_for_agent_result(task_id, timeout)
        
        # Actualizar agente
        with get_db_context() as db:
            agent = db.query(Agent).filter(Agent.id == agent_id).first()
            if agent:
                agent.current_tasks = max(0, agent.current_tasks - 1)
                agent.total_executions += 1
                if result.get("success"):
                    agent.successful_executions += 1
                else:
                    agent.failed_executions += 1
                db.commit()
        
        return result
    
    async def _wait_for_agent_result(self, task_id: str, timeout: int) -> Dict:
        """Espera resultado de tarea del agente"""
        # Implementación simplificada - en producción usar queue/events
        start = datetime.utcnow()
        
        while (datetime.utcnow() - start).total_seconds() < timeout:
            with get_db_context() as db:
                task = db.query(AgentTask).filter(AgentTask.id == task_id).first()
                if task and task.status in ["completed", "failed"]:
                    return {
                        "success": task.status == "completed",
                        "exit_code": task.exit_code,
                        "output": task.output_path,
                        "error": task.error_output
                    }
            
            await asyncio.sleep(0.5)
        
        return {"success": False, "error": "Agent task timeout"}
    
    # -------------------------------------------------------------------------
    # CANCELACIÓN
    # -------------------------------------------------------------------------
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancela una ejecución en progreso"""
        process = self.active_processes.get(execution_id)
        if process:
            process.kill()
            return True
        return False


# =============================================================================
# EXECUTION SERVICE (HIGH-LEVEL)
# =============================================================================

class ExecutionService:
    """
    Servicio de alto nivel para gestionar ejecuciones de herramientas.
    Integra: validación, ejecución, auditoría, timeline, graph.
    """
    
    def __init__(self):
        self.executor = ToolExecutor()
        self.validator = CommandValidator()
    
    async def execute_tool(
        self,
        tool_id: str,
        tool_name: str,
        category: str,
        parameters: Dict[str, Any],
        target: str,
        execution_target: ExecutionTarget,
        user_id: str,
        user_role: str,
        tenant_id: str,
        case_id: Optional[str] = None,
        investigation_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        output_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta una herramienta con todo el flujo completo:
        1. Validación
        2. Auditoría
        3. Ejecución
        4. Parseo de resultados
        5. Timeline event
        6. Graph enrichment
        7. Correlation check
        """
        from api.services.graph_enricher import GraphEnricher
        from api.services.correlation_engine import CorrelationEngine
        
        # Determinar nivel de riesgo
        risk_level = self.validator.get_tool_risk_level(tool_id)
        
        # Verificar permisos
        tenant_settings = {"enable_redteam": True}  # TODO: cargar de BD
        allowed, error = self.validator.check_permission(user_role, risk_level, tenant_settings)
        if not allowed:
            raise PermissionError(error)
        
        # Sanitizar parámetros
        safe_params = self.validator.sanitize_parameters(parameters)
        
        # Crear registro de ejecución
        execution_id = ToolExecution.generate_id()
        
        with get_db_context() as db:
            execution = ToolExecution(
                id=execution_id,
                tool_id=tool_id,
                tool_name=tool_name,
                category=category,
                risk_level=risk_level.value,
                parameters=safe_params,
                target=target,
                execution_target=execution_target.value,
                agent_id=agent_id,
                case_id=case_id,
                investigation_id=investigation_id,
                executed_by=user_id,
                tenant_id=tenant_id,
                status=ExecutionStatus.QUEUED.value
            )
            db.add(execution)
            
            # Record audit (write to file by default to avoid DB saturation)
            record_audit_event(
                action="tool_execution_started",
                action_type="execute",
                resource_type="tool_execution",
                resource_id=execution_id,
                details={
                    "tool_id": tool_id,
                    "target": target,
                    "risk_level": risk_level.value
                },
                user_id=user_id,
                tenant_id=tenant_id,
                persist_to_db=False,
                db_session=db
            )
        
        # Construir comando
        from api.services.kali_tools import build_command
        try:
            command = build_command(tool_id, safe_params)
        except Exception as e:
            await self._update_execution_status(
                execution_id, ExecutionStatus.FAILED, error=str(e)
            )
            raise
        
        # Actualizar estado a running
        await self._update_execution_status(execution_id, ExecutionStatus.RUNNING)
        
        # Ejecutar según target
        try:
            if execution_target == ExecutionTarget.MCP_LOCAL:
                result = await self.executor.execute_local(
                    execution_id=execution_id,
                    tool_id=tool_id,
                    command=command,
                    output_callback=output_callback
                )
            else:
                if not agent_id:
                    raise ValueError("agent_id required for remote execution")
                result = await self.executor.execute_remote(
                    execution_id=execution_id,
                    agent_id=agent_id,
                    tool_id=tool_id,
                    command=command,
                    output_callback=output_callback
                )
        except Exception as e:
            await self._update_execution_status(
                execution_id, ExecutionStatus.FAILED, error=str(e)
            )
            raise
        
        # Actualizar resultado
        status = ExecutionStatus.SUCCESS if result.get("success") else ExecutionStatus.FAILED
        
        with get_db_context() as db:
            execution = db.query(ToolExecution).filter(
                ToolExecution.id == execution_id
            ).first()
            
            if execution:
                execution.status = status.value
                execution.finished_at = datetime.utcnow()
                execution.duration_seconds = result.get("duration_seconds")
                execution.exit_code = result.get("exit_code")
                execution.output_file = result.get("output_file")
                execution.output_hash = result.get("output_hash")
                execution.output_size_bytes = result.get("output_size", 0)
                execution.error_message = result.get("error") if not result.get("success") else None
                execution.command_executed = result.get("command")
                
                # Parsear IOCs del output
                if result.get("output"):
                    iocs = self._extract_iocs_from_output(result["output"])
                    execution.iocs_extracted = iocs
                
                db.commit()
        
        # Enriquecer grafo
        if result.get("success") and result.get("output"):
            try:
                enricher = GraphEnricher()
                nodes_created = await enricher.enrich_from_tool_output(
                    output=result["output"],
                    tool_id=tool_id,
                    execution_id=execution_id,
                    case_id=case_id
                )
                
                with get_db_context() as db:
                    execution = db.query(ToolExecution).filter(
                        ToolExecution.id == execution_id
                    ).first()
                    if execution:
                        execution.graph_nodes_created = nodes_created
                        db.commit()
            except Exception as e:
                logger.warning(f"Graph enrichment failed: {e}")
        
        # Ejecutar correlación
        try:
            corr_engine = CorrelationEngine()
            await corr_engine.correlate_tool_output(
                execution_id=execution_id,
                tool_id=tool_id,
                output=result.get("output", ""),
                case_id=case_id
            )
        except Exception as e:
            logger.warning(f"Correlation failed: {e}")
        
        # Crear timeline event
        if case_id or investigation_id:
            await self._create_timeline_event(
                execution_id=execution_id,
                tool_name=tool_name,
                target=target,
                success=result.get("success", False),
                case_id=case_id,
                investigation_id=investigation_id
            )
        
        return {
            "execution_id": execution_id,
            "status": status.value,
            **result
        }
    
    async def _update_execution_status(
        self,
        execution_id: str,
        status: ExecutionStatus,
        error: Optional[str] = None
    ):
        """Actualiza estado de ejecución"""
        with get_db_context() as db:
            execution = db.query(ToolExecution).filter(
                ToolExecution.id == execution_id
            ).first()
            if execution:
                execution.status = status.value
                if status == ExecutionStatus.RUNNING:
                    execution.started_at = datetime.utcnow()
                if error:
                    execution.error_message = error
                db.commit()
    
    def _extract_iocs_from_output(self, output: str) -> List[Dict]:
        """Extrae IOCs del output de la herramienta"""
        iocs = []
        
        # IPs
        ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
        for match in re.finditer(ip_pattern, output):
            ip = match.group()
            if not ip.startswith(('10.', '172.16.', '192.168.', '127.')):
                iocs.append({"type": "ip", "value": ip})
        
        # Dominios
        domain_pattern = r'\b[a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,}\b'
        for match in re.finditer(domain_pattern, output):
            iocs.append({"type": "domain", "value": match.group()})
        
        # Hashes MD5
        md5_pattern = r'\b[a-fA-F0-9]{32}\b'
        for match in re.finditer(md5_pattern, output):
            iocs.append({"type": "hash_md5", "value": match.group()})
        
        # Hashes SHA256
        sha256_pattern = r'\b[a-fA-F0-9]{64}\b'
        for match in re.finditer(sha256_pattern, output):
            iocs.append({"type": "hash_sha256", "value": match.group()})
        
        # URLs
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        for match in re.finditer(url_pattern, output):
            iocs.append({"type": "url", "value": match.group()})
        
        # Deduplicar
        seen = set()
        unique_iocs = []
        for ioc in iocs:
            key = f"{ioc['type']}:{ioc['value']}"
            if key not in seen:
                seen.add(key)
                unique_iocs.append(ioc)
        
        return unique_iocs[:100]  # Limitar a 100
    
    async def _create_timeline_event(
        self,
        execution_id: str,
        tool_name: str,
        target: str,
        success: bool,
        case_id: Optional[str],
        investigation_id: Optional[str]
    ):
        """Crea evento en timeline"""
        from api.models import InvestigationTimeline
        
        with get_db_context() as db:
            event = InvestigationTimeline(
                id=f"TL-{uuid.uuid4().hex[:8].upper()}",
                investigation_id=investigation_id,
                event_type="tool_execution",
                title=f"{'✅' if success else '❌'} Ejecutado {tool_name}",
                description=f"Herramienta {tool_name} ejecutada contra {target}",
                severity="info" if success else "warning",
                metadata={
                    "execution_id": execution_id,
                    "target": target,
                    "success": success
                }
            )
            db.add(event)
            db.commit()


# =============================================================================
# EXCEPTIONS
# =============================================================================

class SecurityError(Exception):
    """Error de seguridad en ejecución"""
    pass


# =============================================================================
# SINGLETON
# =============================================================================

execution_service = ExecutionService()
