"""
AgentQueue: Cola de ejecución concurrente para agentes Blue/Red/Purple.
Seguridad: No ejecuta nada ofensivo, solo orquesta tareas definidas.

Esta cola permite:
- Procesamiento concurrente con límite configurable
- Prioridades dinámicas (critical > high > normal > low)
- Reintentos automáticos en caso de fallo
- Persistencia de estado en memoria (extensible a Redis/DB)
- Logging detallado para auditoría
"""

import asyncio
from typing import Callable, Any, Dict, Optional, List
from datetime import datetime
from enum import Enum
import logging
import uuid
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


class TaskStatus(Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


@dataclass
class QueuedTask:
    """Representa una tarea en la cola"""
    id: str
    func: Callable
    kwargs: Dict[str, Any]
    priority: TaskPriority
    agent_type: str  # blue, red, purple
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    retries: int = 0
    max_retries: int = 3
    case_id: Optional[str] = None
    investigation_id: Optional[str] = None
    
    def __lt__(self, other):
        # Para ordenar por prioridad en la cola
        return self.priority.value < other.priority.value


class AgentQueue:
    """
    Cola de ejecución concurrente para agentes.
    Soporta múltiples tipos de agentes (Blue/Red/Purple) con límites separados.
    """
    
    def __init__(
        self,
        max_concurrent_total: int = 10,
        max_concurrent_per_type: Dict[str, int] = None
    ):
        """
        Args:
            max_concurrent_total: Límite global de tareas concurrentes
            max_concurrent_per_type: Límites por tipo de agente
        """
        self.max_concurrent_total = max_concurrent_total
        self.max_concurrent_per_type = max_concurrent_per_type or {
            "blue": 5,
            "red": 3,  # Más restrictivo para red team
            "purple": 2,
            "generic": 3
        }
        
        # Colas separadas por prioridad
        self.queues: Dict[TaskPriority, asyncio.PriorityQueue] = {
            priority: asyncio.PriorityQueue()
            for priority in TaskPriority
        }
        
        # Tracking de tareas
        self.tasks: Dict[str, QueuedTask] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.running_count_per_type: Dict[str, int] = defaultdict(int)
        
        # Lock para operaciones thread-safe
        self._lock = asyncio.Lock()
        
        # Worker task
        self._worker_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Callbacks
        self._on_task_complete: List[Callable] = []
        self._on_task_failed: List[Callable] = []
        
        logger.info(f"🔄 AgentQueue inicializada (max: {max_concurrent_total} total)")
    
    async def start(self):
        """Iniciar el worker de la cola"""
        if self._running:
            return
        
        self._running = True
        self._worker_task = asyncio.create_task(self._worker())
        logger.info("✅ AgentQueue worker iniciado")
    
    async def stop(self):
        """Detener el worker de la cola"""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        logger.info("🛑 AgentQueue worker detenido")
    
    async def add_task(
        self,
        task_func: Callable,
        agent_type: str = "generic",
        priority: str = "normal",
        case_id: Optional[str] = None,
        investigation_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Añade tarea a la cola.
        
        Args:
            task_func: Función async a ejecutar
            agent_type: Tipo de agente (blue/red/purple/generic)
            priority: Prioridad (critical/high/normal/low)
            case_id: ID del caso asociado
            investigation_id: ID de la investigación asociada
            **kwargs: Argumentos para la función
            
        Returns:
            task_id: ID único de la tarea
        """
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        
        priority_enum = TaskPriority[priority.upper()]
        
        task = QueuedTask(
            id=task_id,
            func=task_func,
            kwargs=kwargs,
            priority=priority_enum,
            agent_type=agent_type,
            status=TaskStatus.QUEUED,
            case_id=case_id,
            investigation_id=investigation_id
        )
        
        async with self._lock:
            self.tasks[task_id] = task
            await self.queues[priority_enum].put((priority_enum.value, task_id, task))
        
        logger.info(f"📥 Tarea {task_id} añadida [{agent_type}] [{priority}]")
        
        # Trigger processing
        if self._running:
            asyncio.create_task(self._process_queue())
        
        return task_id
    
    async def _worker(self):
        """Worker principal que procesa la cola"""
        while self._running:
            try:
                await self._process_queue()
                await asyncio.sleep(0.1)  # Small delay to prevent busy loop
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error en worker: {e}")
                await asyncio.sleep(1)
    
    async def _process_queue(self):
        """Procesa tareas de la cola respetando límites de concurrencia"""
        # Verificar límite global
        if len(self.running_tasks) >= self.max_concurrent_total:
            return
        
        # Procesar por prioridad (crítico primero)
        for priority in TaskPriority:
            queue = self.queues[priority]
            
            while not queue.empty():
                # Verificar límite global nuevamente
                if len(self.running_tasks) >= self.max_concurrent_total:
                    return
                
                try:
                    _, task_id, task = queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
                
                # Verificar límite por tipo
                agent_type = task.agent_type
                type_limit = self.max_concurrent_per_type.get(agent_type, 3)
                
                if self.running_count_per_type[agent_type] >= type_limit:
                    # Devolver a la cola
                    await queue.put((task.priority.value, task_id, task))
                    continue
                
                # Ejecutar tarea
                async with self._lock:
                    self.running_count_per_type[agent_type] += 1
                    task.status = TaskStatus.RUNNING
                    task.started_at = datetime.utcnow()
                
                asyncio_task = asyncio.create_task(self._run_task(task))
                self.running_tasks[task_id] = asyncio_task
                
                logger.info(f"▶️ Ejecutando tarea {task_id}")
    
    async def _run_task(self, task: QueuedTask):
        """Ejecuta una tarea individual con manejo de errores"""
        try:
            result = await task.func(**task.kwargs)
            
            async with self._lock:
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.utcnow()
                task.result = result
            
            logger.info(f"✅ Tarea {task.id} completada")
            
            # Callbacks
            for callback in self._on_task_complete:
                try:
                    await callback(task)
                except Exception as e:
                    logger.error(f"Error en callback de tarea completada: {e}")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Tarea {task.id} falló: {error_msg}")
            
            async with self._lock:
                task.error = error_msg
                task.retries += 1
                
                if task.retries < task.max_retries:
                    # Reintentar
                    task.status = TaskStatus.RETRYING
                    await self.queues[task.priority].put(
                        (task.priority.value, task.id, task)
                    )
                    logger.info(f"🔄 Reintentando tarea {task.id} ({task.retries}/{task.max_retries})")
                else:
                    task.status = TaskStatus.FAILED
                    task.completed_at = datetime.utcnow()
                    
                    # Callbacks de fallo
                    for callback in self._on_task_failed:
                        try:
                            await callback(task)
                        except Exception as cb_e:
                            logger.error(f"Error en callback de tarea fallida: {cb_e}")
        
        finally:
            # Limpiar tracking
            async with self._lock:
                self.running_count_per_type[task.agent_type] -= 1
                if task.id in self.running_tasks:
                    del self.running_tasks[task.id]
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancela una tarea"""
        async with self._lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            
            if task.status == TaskStatus.RUNNING:
                if task_id in self.running_tasks:
                    self.running_tasks[task_id].cancel()
            
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.utcnow()
            
        logger.info(f"🚫 Tarea {task_id} cancelada")
        return True
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Obtiene el estado de una tarea"""
        if task_id not in self.tasks:
            return None
        
        task = self.tasks[task_id]
        return {
            "id": task.id,
            "status": task.status.value,
            "priority": task.priority.name,
            "agent_type": task.agent_type,
            "created_at": task.created_at.isoformat(),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "retries": task.retries,
            "error": task.error,
            "result": task.result,
            "case_id": task.case_id,
            "investigation_id": task.investigation_id
        }
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de la cola"""
        pending_by_priority = {
            p.name: self.queues[p].qsize() for p in TaskPriority
        }
        
        running_by_type = dict(self.running_count_per_type)
        
        status_counts = defaultdict(int)
        for task in self.tasks.values():
            status_counts[task.status.value] += 1
        
        return {
            "total_tasks": len(self.tasks),
            "running": len(self.running_tasks),
            "pending_by_priority": pending_by_priority,
            "running_by_type": running_by_type,
            "status_counts": dict(status_counts),
            "limits": {
                "max_concurrent_total": self.max_concurrent_total,
                "max_concurrent_per_type": self.max_concurrent_per_type
            }
        }
    
    def on_task_complete(self, callback: Callable):
        """Registra callback para tareas completadas"""
        self._on_task_complete.append(callback)
    
    def on_task_failed(self, callback: Callable):
        """Registra callback para tareas fallidas"""
        self._on_task_failed.append(callback)


# Instancia singleton
agent_queue = AgentQueue(
    max_concurrent_total=10,
    max_concurrent_per_type={
        "blue": 5,
        "red": 2,  # Más restrictivo
        "purple": 3,
        "generic": 4
    }
)
