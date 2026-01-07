"""
MCP Kali Forensics - Logging Queue v4.4.1
Cola de logs unificada para streaming en tiempo real

Consolida logs de:
- Tools execution
- Agent operations
- Correlation engine
- SOAR engine
- Graph enrichment

Features:
- Push via WebSocket al cliente
- Replay de logs por analysis_id
- Persistencia opcional en SQLite
- Backpressure handling
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, asdict, field
from enum import Enum
from collections import defaultdict
import sqlite3
from pathlib import Path

try:
    import zstandard as zstd
    ZSTD_AVAILABLE = True
except ImportError:
    ZSTD_AVAILABLE = False

logger = logging.getLogger(__name__)


class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    

class LogSource(str, Enum):
    TOOL = "tool"
    AGENT = "agent"
    CORRELATION = "correlation"
    SOAR = "soar"
    GRAPH = "graph"
    EXECUTOR = "executor"
    SYSTEM = "system"


@dataclass
class LogEntry:
    """Entrada de log estructurada"""
    timestamp: str
    source: LogSource
    level: LogLevel
    message: str
    analysis_id: Optional[str] = None
    case_id: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    sequence: int = 0
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class LoggingQueue:
    """
    Cola de logs unificada con soporte para:
    - Múltiples subscriptores por analysis_id
    - Persistencia en SQLite
    - Replay de logs históricos
    - Rate limiting y backpressure
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        
        # Subscribers por analysis_id
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        
        # Subscribers globales (reciben todo)
        self._global_subscribers: List[Callable] = []
        
        # Buffer de logs recientes por analysis (para replay)
        self._buffer: Dict[str, List[LogEntry]] = defaultdict(list)
        self._buffer_max_size = 1000  # Logs por analysis
        
        # Contador de secuencia global
        self._sequence_counter = 0
        
        # Base de datos para persistencia
        self._db_path = Path("logs/logging_queue.db")
        self._init_db()
        
        # Queue asíncrona para processing
        self._queue: asyncio.Queue = None
        self._processing_task: asyncio.Task = None
        
        # Rate limiting
        self._rate_limit = 100  # Logs por segundo
        self._last_flush = datetime.now()
        
        logger.info("📋 LoggingQueue inicializado")

    def compress_batch(self, entries: List[LogEntry]) -> bytes:
        """
        Comprime un lote de logs usando Zstd si está disponible.
        Retorna bytes comprimidos o JSON bytes si no hay Zstd.
        """
        data = json.dumps([e.to_dict() for e in entries]).encode('utf-8')
        
        if ZSTD_AVAILABLE:
            cctx = zstd.ZstdCompressor(level=3)
            return cctx.compress(data)
        
        return data
    
    def decompress_batch(self, compressed_data: bytes) -> List[Dict]:
        """
        Descomprime un lote de logs.
        Detecta automáticamente si está comprimido con Zstd.
        """
        if ZSTD_AVAILABLE and len(compressed_data) > 4:
            # Verificar magic bytes de Zstd
            if compressed_data[:4] == b'\x28\xb5\x2f\xfd':
                dctx = zstd.ZstdDecompressor()
                data = dctx.decompress(compressed_data)
                return json.loads(data.decode('utf-8'))
        
        # Asumir que es JSON sin comprimir
        return json.loads(compressed_data.decode('utf-8'))
    
    def get_batch_for_websocket(
        self,
        analysis_id: str,
        since_sequence: int = 0,
        max_entries: int = 100,
        compress: bool = True
    ) -> Dict[str, Any]:
        """
        Obtiene un lote de logs optimizado para envío por WebSocket.
        
        Args:
            analysis_id: ID del análisis
            since_sequence: Obtener solo logs después de esta secuencia
            max_entries: Máximo de entradas a retornar
            compress: Si comprimir el payload
            
        Returns:
            Dict con:
                - entries: Lista de logs o bytes comprimidos
                - compressed: bool indicando si está comprimido
                - count: Número de entradas
                - last_sequence: Última secuencia incluida
        """
        buffer = self._buffer.get(analysis_id, [])
        
        # Filtrar por secuencia
        new_entries = [e for e in buffer if e.sequence > since_sequence][:max_entries]
        
        if not new_entries:
            return {
                "entries": [],
                "compressed": False,
                "count": 0,
                "last_sequence": since_sequence
            }
        
        last_seq = new_entries[-1].sequence
        
        if compress and ZSTD_AVAILABLE and len(new_entries) > 5:
            # Comprimir si hay suficientes entradas
            compressed = self.compress_batch(new_entries)
            return {
                "entries": compressed,
                "compressed": True,
                "count": len(new_entries),
                "last_sequence": last_seq
            }
        
        return {
            "entries": [e.to_dict() for e in new_entries],
            "compressed": False,
            "count": len(new_entries),
            "last_sequence": last_seq
        }
    
    async def stream_to_websocket(
        self,
        websocket,
        analysis_id: str,
        compress: bool = True,
        batch_size: int = 50,
        batch_delay_ms: int = 100
    ):
        """
        Stream de logs a un WebSocket con batching y compresión opcional.
        
        Args:
            websocket: WebSocket connection (FastAPI WebSocket)
            analysis_id: ID del análisis a monitorear
            compress: Si usar compresión Zstd
            batch_size: Tamaño del batch antes de enviar
            batch_delay_ms: Delay en ms para acumular logs
        """
        batch_buffer = []
        last_send = datetime.now()
        
        async def send_batch():
            nonlocal batch_buffer, last_send
            if not batch_buffer:
                return
            
            if compress and ZSTD_AVAILABLE:
                payload = {
                    "type": "log_batch",
                    "analysis_id": analysis_id,
                    "compressed": True,
                    "data": self.compress_batch(batch_buffer).hex(),
                    "count": len(batch_buffer)
                }
            else:
                payload = {
                    "type": "log_batch",
                    "analysis_id": analysis_id,
                    "compressed": False,
                    "data": [e.to_dict() for e in batch_buffer],
                    "count": len(batch_buffer)
                }
            
            await websocket.send_json(payload)
            batch_buffer = []
            last_send = datetime.now()
        
        async def on_log(entry: LogEntry):
            nonlocal batch_buffer
            batch_buffer.append(entry)
            
            # Enviar si el batch está lleno o ha pasado el tiempo
            now = datetime.now()
            elapsed_ms = (now - last_send).total_seconds() * 1000
            
            if len(batch_buffer) >= batch_size or elapsed_ms >= batch_delay_ms:
                await send_batch()
        
        # Subscribirse
        self.subscribe(analysis_id, on_log)
        
        try:
            # Mantener conexión abierta
            while True:
                try:
                    # Esperar mensajes del cliente (para mantener conexión)
                    message = await asyncio.wait_for(
                        websocket.receive_json(),
                        timeout=5.0
                    )
                    
                    if message.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})
                    elif message.get("type") == "flush":
                        await send_batch()
                        
                except asyncio.TimeoutError:
                    # Enviar cualquier log pendiente
                    await send_batch()
                    
        finally:
            self.unsubscribe(analysis_id, on_log)

    
    def _init_db(self):
        """Inicializar base de datos de logs"""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS log_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    source TEXT NOT NULL,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    analysis_id TEXT,
                    case_id TEXT,
                    metadata TEXT,
                    sequence INTEGER
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_analysis_id ON log_entries(analysis_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_case_id ON log_entries(case_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp ON log_entries(timestamp)
            """)
            conn.commit()
    
    async def start(self):
        """Iniciar procesamiento de cola"""
        if self._queue is None:
            self._queue = asyncio.Queue(maxsize=10000)
        
        if self._processing_task is None or self._processing_task.done():
            self._processing_task = asyncio.create_task(self._process_queue())
            logger.info("📋 LoggingQueue processing started")
    
    async def stop(self):
        """Detener procesamiento"""
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
            logger.info("📋 LoggingQueue processing stopped")
    
    async def _process_queue(self):
        """Procesar logs de la cola"""
        while True:
            try:
                entry = await self._queue.get()
                await self._dispatch(entry)
                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing log entry: {e}")
    
    async def log(
        self,
        source: LogSource,
        level: LogLevel,
        message: str,
        analysis_id: Optional[str] = None,
        case_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> LogEntry:
        """
        Agregar log a la cola
        
        Args:
            source: Origen del log (tool, agent, etc.)
            level: Nivel de severidad
            message: Mensaje del log
            analysis_id: ID del análisis forense (FA-XXXX)
            case_id: ID del caso (IR-XXXX)
            metadata: Datos adicionales
        
        Returns:
            LogEntry creada
        """
        self._sequence_counter += 1
        
        entry = LogEntry(
            timestamp=datetime.utcnow().isoformat() + "Z",
            source=source,
            level=level,
            message=message,
            analysis_id=analysis_id,
            case_id=case_id,
            metadata=metadata or {},
            sequence=self._sequence_counter
        )
        
        # Agregar a buffer
        if analysis_id:
            self._buffer[analysis_id].append(entry)
            # Limitar tamaño del buffer
            if len(self._buffer[analysis_id]) > self._buffer_max_size:
                self._buffer[analysis_id] = self._buffer[analysis_id][-self._buffer_max_size:]
        
        # Agregar a cola para procesamiento async
        if self._queue:
            try:
                self._queue.put_nowait(entry)
            except asyncio.QueueFull:
                logger.warning("LoggingQueue full, dropping log entry")
        else:
            # Procesamiento síncrono si no hay cola
            await self._dispatch(entry)
        
        return entry
    
    async def _dispatch(self, entry: LogEntry):
        """Despachar log a subscribers y persistir"""
        # Persistir en DB
        self._persist(entry)
        
        # Notificar subscribers del analysis
        if entry.analysis_id and entry.analysis_id in self._subscribers:
            for callback in self._subscribers[entry.analysis_id]:
                try:
                    await self._call_subscriber(callback, entry)
                except Exception as e:
                    logger.error(f"Error in subscriber callback: {e}")
        
        # Notificar subscribers globales
        for callback in self._global_subscribers:
            try:
                await self._call_subscriber(callback, entry)
            except Exception as e:
                logger.error(f"Error in global subscriber callback: {e}")
    
    async def _call_subscriber(self, callback: Callable, entry: LogEntry):
        """Llamar subscriber (sync o async)"""
        if asyncio.iscoroutinefunction(callback):
            await callback(entry)
        else:
            callback(entry)
    
    def _persist(self, entry: LogEntry):
        """Persistir log en SQLite"""
        try:
            with sqlite3.connect(str(self._db_path)) as conn:
                conn.execute("""
                    INSERT INTO log_entries (timestamp, source, level, message, analysis_id, case_id, metadata, sequence)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    entry.timestamp,
                    entry.source.value,
                    entry.level.value,
                    entry.message,
                    entry.analysis_id,
                    entry.case_id,
                    json.dumps(entry.metadata),
                    entry.sequence
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Error persisting log: {e}")
    
    def subscribe(self, analysis_id: str, callback: Callable):
        """
        Subscribirse a logs de un análisis específico
        
        Args:
            analysis_id: ID del análisis (FA-XXXX)
            callback: Función a llamar con cada log
        """
        self._subscribers[analysis_id].append(callback)
        logger.info(f"📋 Subscriber added for analysis {analysis_id}")
    
    def unsubscribe(self, analysis_id: str, callback: Callable):
        """Remover subscription"""
        if callback in self._subscribers[analysis_id]:
            self._subscribers[analysis_id].remove(callback)
            logger.info(f"📋 Subscriber removed for analysis {analysis_id}")
    
    def subscribe_global(self, callback: Callable):
        """Subscribirse a todos los logs"""
        self._global_subscribers.append(callback)
    
    def unsubscribe_global(self, callback: Callable):
        """Remover subscription global"""
        if callback in self._global_subscribers:
            self._global_subscribers.remove(callback)
    
    def get_buffer(self, analysis_id: str) -> List[LogEntry]:
        """Obtener logs buffereados de un análisis"""
        return self._buffer.get(analysis_id, [])
    
    def get_logs(
        self,
        analysis_id: Optional[str] = None,
        case_id: Optional[str] = None,
        level: Optional[LogLevel] = None,
        source: Optional[LogSource] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """
        Consultar logs persistidos
        
        Args:
            analysis_id: Filtrar por análisis
            case_id: Filtrar por caso
            level: Filtrar por nivel
            source: Filtrar por origen
            limit: Máximo de resultados
            offset: Offset para paginación
        
        Returns:
            Lista de logs
        """
        query = "SELECT * FROM log_entries WHERE 1=1"
        params = []
        
        if analysis_id:
            query += " AND analysis_id = ?"
            params.append(analysis_id)
        
        if case_id:
            query += " AND case_id = ?"
            params.append(case_id)
        
        if level:
            query += " AND level = ?"
            params.append(level.value)
        
        if source:
            query += " AND source = ?"
            params.append(source.value)
        
        query += " ORDER BY sequence DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        try:
            with sqlite3.connect(str(self._db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error querying logs: {e}")
            return []
    
    def clear_analysis_logs(self, analysis_id: str):
        """Limpiar logs de un análisis"""
        try:
            with sqlite3.connect(str(self._db_path)) as conn:
                conn.execute("DELETE FROM log_entries WHERE analysis_id = ?", (analysis_id,))
                conn.commit()
            
            if analysis_id in self._buffer:
                del self._buffer[analysis_id]
            
            if analysis_id in self._subscribers:
                del self._subscribers[analysis_id]
                
            logger.info(f"📋 Logs cleared for analysis {analysis_id}")
        except Exception as e:
            logger.error(f"Error clearing logs: {e}")
    
    def get_stats(self) -> Dict:
        """Obtener estadísticas de la cola"""
        try:
            with sqlite3.connect(str(self._db_path)) as conn:
                total = conn.execute("SELECT COUNT(*) FROM log_entries").fetchone()[0]
                by_level = dict(conn.execute(
                    "SELECT level, COUNT(*) FROM log_entries GROUP BY level"
                ).fetchall())
                by_source = dict(conn.execute(
                    "SELECT source, COUNT(*) FROM log_entries GROUP BY source"
                ).fetchall())
                
                return {
                    "total_logs": total,
                    "by_level": by_level,
                    "by_source": by_source,
                    "active_subscriptions": sum(len(s) for s in self._subscribers.values()),
                    "global_subscribers": len(self._global_subscribers),
                    "buffered_analyses": len(self._buffer),
                    "queue_size": self._queue.qsize() if self._queue else 0
                }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}


# Singleton global
_logging_queue_instance: Optional[LoggingQueue] = None


def get_logging_queue() -> LoggingQueue:
    """Obtener instancia singleton del LoggingQueue"""
    global _logging_queue_instance
    if _logging_queue_instance is None:
        _logging_queue_instance = LoggingQueue()
    return _logging_queue_instance


def reset_logging_queue():
    """Resetear instancia singleton (para tests)"""
    global _logging_queue_instance
    if _logging_queue_instance is not None:
        _logging_queue_instance._initialized = False
        _logging_queue_instance._subscribers.clear()
        _logging_queue_instance._global_subscribers.clear()
        _logging_queue_instance._buffer.clear()
    _logging_queue_instance = None


# Mantener compatibilidad con código existente
logging_queue = get_logging_queue()


# Helper functions para uso fácil
async def log_tool(message: str, analysis_id: str = None, case_id: str = None, level: LogLevel = LogLevel.INFO, **metadata):
    """Log de herramienta"""
    return await logging_queue.log(LogSource.TOOL, level, message, analysis_id, case_id, metadata)


async def log_agent(message: str, analysis_id: str = None, case_id: str = None, level: LogLevel = LogLevel.INFO, **metadata):
    """Log de agente"""
    return await logging_queue.log(LogSource.AGENT, level, message, analysis_id, case_id, metadata)


async def log_correlation(message: str, analysis_id: str = None, case_id: str = None, level: LogLevel = LogLevel.INFO, **metadata):
    """Log de correlación"""
    return await logging_queue.log(LogSource.CORRELATION, level, message, analysis_id, case_id, metadata)


async def log_soar(message: str, analysis_id: str = None, case_id: str = None, level: LogLevel = LogLevel.INFO, **metadata):
    """Log de SOAR"""
    return await logging_queue.log(LogSource.SOAR, level, message, analysis_id, case_id, metadata)


async def log_executor(message: str, analysis_id: str = None, case_id: str = None, level: LogLevel = LogLevel.INFO, **metadata):
    """Log de executor"""
    return await logging_queue.log(LogSource.EXECUTOR, level, message, analysis_id, case_id, metadata)


async def log_system(message: str, level: LogLevel = LogLevel.INFO, **metadata):
    """Log de sistema"""
    return await logging_queue.log(LogSource.SYSTEM, level, message, metadata=metadata)


# Test helpers
def get_logging_queue():
    """Get the global logging queue instance (for testing)"""
    return logging_queue


def reset_logging_queue():
    """Reset the global logging queue instance (for testing)"""
    global logging_queue
    logging_queue = LoggingQueue()
