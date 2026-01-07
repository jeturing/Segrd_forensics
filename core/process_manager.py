"""
MCP Kali Forensics v4.4 - Process Manager
==========================================
Gestor de procesos de larga duración con persistencia.
Asegura que los procesos sobrevivan a desconexiones del cliente.

Author: MCP Forensics Team
Version: 4.4.0
"""

from datetime import datetime
from typing import Dict, Optional, List, Callable, Awaitable
from enum import Enum
import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from threading import Lock

logger = logging.getLogger(__name__)


class ProcessStatus(str, Enum):
    """Estados posibles de un proceso"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class ProcessType(str, Enum):
    """Tipos de procesos forenses"""
    HUNTING = "hunting"
    SCAN = "scan"
    ANALYSIS = "analysis"
    REPORT = "report"
    AGENT_TASK = "agent_task"
    IMPORT = "import"
    EXPORT = "export"
    LLM_ANALYSIS = "llm_analysis"
    CORRELATION = "correlation"


@dataclass
class ForensicProcess:
    """Representación de un proceso forense"""
    process_id: str
    case_id: str
    process_type: ProcessType
    name: str
    status: ProcessStatus = ProcessStatus.PENDING
    
    # Timing
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Progress
    progress: int = 0  # 0-100
    current_step: str = ""
    total_steps: int = 0
    
    # Input/Output
    input_data: Dict = field(default_factory=dict)
    output_data: Dict = field(default_factory=dict)
    
    # Error handling
    error_message: Optional[str] = None
    error_details: Optional[Dict] = None
    retry_count: int = 0
    max_retries: int = 3
    
    # Metadata
    created_by: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    # Task reference
    _task: Optional[asyncio.Task] = field(default=None, repr=False)
    
    def to_dict(self) -> Dict:
        return {
            "process_id": self.process_id,
            "case_id": self.case_id,
            "process_type": self.process_type.value,
            "name": self.name,
            "status": self.status.value,
            "progress": self.progress,
            "current_step": self.current_step,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "created_by": self.created_by
        }
    
    def update_progress(self, progress: int, current_step: str = ""):
        """Actualizar progreso del proceso"""
        self.progress = min(100, max(0, progress))
        if current_step:
            self.current_step = current_step
    
    def start(self):
        """Marcar proceso como iniciado"""
        self.status = ProcessStatus.RUNNING
        self.started_at = datetime.utcnow()
    
    def complete(self, output_data: Optional[Dict] = None):
        """Marcar proceso como completado"""
        self.status = ProcessStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.progress = 100
        if output_data:
            self.output_data = output_data
    
    def fail(self, error_message: str, error_details: Optional[Dict] = None):
        """Marcar proceso como fallido"""
        self.status = ProcessStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error_message
        self.error_details = error_details
    
    def cancel(self):
        """Cancelar proceso"""
        self.status = ProcessStatus.CANCELLED
        self.completed_at = datetime.utcnow()
        if self._task and not self._task.done():
            self._task.cancel()


class ProcessManager:
    """
    Gestor central de procesos forenses.
    
    Funcionalidades:
    - Crear y trackear procesos de larga duración
    - Persistir estado de procesos
    - Recuperar procesos al reiniciar
    - Notificar progreso en tiempo real
    - Cancelar procesos en curso
    """
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._processes: Dict[str, ForensicProcess] = {}
        self._case_processes: Dict[str, List[str]] = {}  # case_id -> [process_ids]
        self._callbacks: Dict[str, List[Callable]] = {}  # process_id -> callbacks
        self._lock = Lock()
        self._initialized = True
        
        logger.info("🔵 ProcessManager initialized")
    
    def create_process(
        self,
        case_id: str,
        process_type: ProcessType,
        name: str,
        input_data: Optional[Dict] = None,
        created_by: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> ForensicProcess:
        """Crear nuevo proceso forense"""
        process_id = f"PROC-{uuid.uuid4().hex[:8].upper()}"
        
        process = ForensicProcess(
            process_id=process_id,
            case_id=case_id,
            process_type=process_type,
            name=name,
            input_data=input_data or {},
            created_by=created_by,
            tags=tags or []
        )
        
        with self._lock:
            self._processes[process_id] = process
            
            if case_id not in self._case_processes:
                self._case_processes[case_id] = []
            self._case_processes[case_id].append(process_id)
        
        logger.info(f"🆕 Created process {process_id} for case {case_id}: {name}")
        return process
    
    def get_process(self, process_id: str) -> Optional[ForensicProcess]:
        """Obtener proceso por ID"""
        return self._processes.get(process_id)
    
    def get_case_processes(
        self, 
        case_id: str, 
        status: Optional[ProcessStatus] = None,
        process_type: Optional[ProcessType] = None
    ) -> List[ForensicProcess]:
        """Obtener todos los procesos de un caso"""
        process_ids = self._case_processes.get(case_id, [])
        processes = [self._processes[pid] for pid in process_ids if pid in self._processes]
        
        if status:
            processes = [p for p in processes if p.status == status]
        if process_type:
            processes = [p for p in processes if p.process_type == process_type]
        
        return processes
    
    def get_running_processes(self, case_id: Optional[str] = None) -> List[ForensicProcess]:
        """Obtener procesos en ejecución"""
        if case_id:
            return self.get_case_processes(case_id, status=ProcessStatus.RUNNING)
        return [p for p in self._processes.values() if p.status == ProcessStatus.RUNNING]
    
    async def run_process(
        self,
        process: ForensicProcess,
        task_func: Callable[..., Awaitable[Dict]],
        *args,
        **kwargs
    ) -> ForensicProcess:
        """
        Ejecutar un proceso de forma asíncrona.
        
        Args:
            process: Proceso a ejecutar
            task_func: Función async que realiza el trabajo
            *args, **kwargs: Argumentos para la función
        """
        async def _execute():
            try:
                process.start()
                logger.info(f"▶️ Started process {process.process_id}")
                
                # Ejecutar la tarea
                result = await task_func(*args, **kwargs)
                
                process.complete(result)
                logger.info(f"✅ Completed process {process.process_id}")
                
            except asyncio.CancelledError:
                process.cancel()
                logger.warning(f"⚠️ Cancelled process {process.process_id}")
                
            except Exception as e:
                process.fail(str(e), {"exception": type(e).__name__})
                logger.error(f"❌ Failed process {process.process_id}: {e}")
                
            finally:
                # Notificar callbacks
                await self._notify_callbacks(process)
        
        # Crear y almacenar la tarea
        task = asyncio.create_task(_execute())
        process._task = task
        
        return process
    
    def update_progress(self, process_id: str, progress: int, current_step: str = ""):
        """Actualizar progreso de un proceso"""
        process = self.get_process(process_id)
        if process:
            process.update_progress(progress, current_step)
            logger.debug(f"📊 Process {process_id}: {progress}% - {current_step}")
    
    def cancel_process(self, process_id: str) -> bool:
        """Cancelar un proceso"""
        process = self.get_process(process_id)
        if process and process.status == ProcessStatus.RUNNING:
            process.cancel()
            logger.info(f"🛑 Cancelled process {process_id}")
            return True
        return False
    
    def add_callback(self, process_id: str, callback: Callable):
        """Agregar callback para cuando el proceso termine"""
        if process_id not in self._callbacks:
            self._callbacks[process_id] = []
        self._callbacks[process_id].append(callback)
    
    async def _notify_callbacks(self, process: ForensicProcess):
        """Notificar callbacks registrados"""
        callbacks = self._callbacks.pop(process.process_id, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(process)
                else:
                    callback(process)
            except Exception as e:
                logger.error(f"Error in callback for {process.process_id}: {e}")
    
    def get_stats(self, case_id: Optional[str] = None) -> Dict:
        """Obtener estadísticas de procesos"""
        if case_id:
            processes = self.get_case_processes(case_id)
        else:
            processes = list(self._processes.values())
        
        return {
            "total": len(processes),
            "pending": len([p for p in processes if p.status == ProcessStatus.PENDING]),
            "running": len([p for p in processes if p.status == ProcessStatus.RUNNING]),
            "completed": len([p for p in processes if p.status == ProcessStatus.COMPLETED]),
            "failed": len([p for p in processes if p.status == ProcessStatus.FAILED]),
            "cancelled": len([p for p in processes if p.status == ProcessStatus.CANCELLED])
        }
    
    def cleanup_old_processes(self, max_age_hours: int = 24):
        """Limpiar procesos antiguos completados"""
        cutoff = datetime.utcnow()
        with self._lock:
            to_remove = []
            for pid, process in self._processes.items():
                if process.status in (ProcessStatus.COMPLETED, ProcessStatus.FAILED, ProcessStatus.CANCELLED):
                    if process.completed_at:
                        age = (cutoff - process.completed_at).total_seconds() / 3600
                        if age > max_age_hours:
                            to_remove.append(pid)
            
            for pid in to_remove:
                process = self._processes.pop(pid)
                case_processes = self._case_processes.get(process.case_id, [])
                if pid in case_processes:
                    case_processes.remove(pid)
            
            if to_remove:
                logger.info(f"🧹 Cleaned up {len(to_remove)} old processes")


# Singleton instance
process_manager = ProcessManager()


def get_process_manager() -> ProcessManager:
    """Dependency para inyectar el process manager"""
    return process_manager
