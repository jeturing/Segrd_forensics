"""
MCP Kali Forensics - Tests for Logging Queue & WebSocket Streaming v4.4.1
Tests unitarios para el sistema de logs en tiempo real
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime

# Import modules under test
from core.logging_queue import (
    LoggingQueue, LogLevel, LogEntry, LogSource,
    get_logging_queue, reset_logging_queue
)


class TestLogLevel:
    """Tests para niveles de log"""
    
    def test_log_level_values(self):
        """Verificar valores de niveles"""
        assert LogLevel.DEBUG == "debug"
        assert LogLevel.INFO == "info"
        assert LogLevel.WARNING == "warning"
        assert LogLevel.ERROR == "error"
    
    def test_log_level_ordering(self):
        """Verificar orden de severidad"""
        levels = [LogLevel.DEBUG, LogLevel.INFO, LogLevel.WARNING, LogLevel.ERROR]
        # DEBUG < INFO < WARNING < ERROR
        assert levels == sorted(levels, key=lambda x: levels.index(x))


class TestLogEntry:
    """Tests para modelo LogEntry"""
    
    def test_log_entry_creation(self):
        """Crear LogEntry básico"""
        entry = LogEntry(
            timestamp=datetime.utcnow().isoformat() + "Z",
            source=LogSource.TOOL,
            level=LogLevel.INFO,
            message="Test message"
        )
        
        assert entry.level == LogLevel.INFO
        assert entry.message == "Test message"
        assert entry.timestamp is not None
        assert entry.analysis_id is None
        assert entry.case_id is None
    
    def test_log_entry_with_context(self):
        """LogEntry con contexto completo"""
        entry = LogEntry(
            timestamp=datetime.utcnow().isoformat() + "Z",
            source=LogSource.TOOL,
            level=LogLevel.WARNING,
            message="Warning message",
            analysis_id="FA-2025-00001",
            case_id="IR-2025-001",
            metadata={"tool": "loki", "exit_code": 1}
        )
        
        assert entry.analysis_id == "FA-2025-00001"
        assert entry.case_id == "IR-2025-001"
        assert entry.metadata["tool"] == "loki"
    
    def test_log_entry_to_dict(self):
        """Serialización a diccionario"""
        entry = LogEntry(
            timestamp=datetime.utcnow().isoformat() + "Z",
            source=LogSource.SYSTEM,
            level=LogLevel.ERROR,
            message="Error message",
            analysis_id="FA-2025-00001"
        )
        
        data = entry.to_dict()
        
        assert isinstance(data, dict)
        assert data["level"] == "error"
        assert data["message"] == "Error message"
        assert data["analysis_id"] == "FA-2025-00001"
        assert "timestamp" in data
    
    def test_log_entry_to_json(self):
        """Serialización a JSON"""
        entry = LogEntry(
            timestamp=datetime.utcnow().isoformat() + "Z",
            source=LogSource.AGENT,
            level=LogLevel.INFO,
            message="Test"
        )
        
        json_str = entry.to_json()
        data = json.loads(json_str)
        
        assert data["level"] == "info"
        assert data["message"] == "Test"


class TestLoggingQueue:
    """Tests para LoggingQueue"""
    
    @pytest.fixture
    def queue(self):
        """Fresh queue para cada test"""
        reset_logging_queue()
        return get_logging_queue()
    
    def test_queue_initialization(self, queue):
        """Inicialización de queue"""
        assert queue is not None
        assert queue._buffer_max_size == 1000
        assert len(queue._buffer) == 0
    
    @pytest.mark.asyncio
    async def test_log_message(self, queue):
        """Agregar mensaje a la cola"""
        entry = await queue.log(
            source=LogSource.TOOL,
            level=LogLevel.INFO,
            message="Test message",
            analysis_id="FA-2025-00001"
        )
        
        # Verificar que el mensaje está en el buffer
        assert "FA-2025-00001" in queue._buffer
        assert len(queue._buffer["FA-2025-00001"]) == 1
        assert entry.message == "Test message"
    
    @pytest.mark.asyncio
    async def test_log_with_metadata(self, queue):
        """Log con metadata"""
        entry = await queue.log(
            source=LogSource.TOOL,
            level=LogLevel.WARNING,
            message="Warning message",
            analysis_id="FA-001",
            metadata={"tool": "loki", "exit_code": 1}
        )
        
        assert entry.metadata["tool"] == "loki"
        assert entry.metadata["exit_code"] == 1
    
    @pytest.mark.asyncio
    async def test_log_multiple_analysis(self, queue):
        """Logs separados por analysis_id"""
        await queue.log(
            source=LogSource.TOOL,
            level=LogLevel.INFO,
            message="Msg 1",
            analysis_id="FA-001"
        )
        await queue.log(
            source=LogSource.TOOL,
            level=LogLevel.INFO,
            message="Msg 2",
            analysis_id="FA-002"
        )
        await queue.log(
            source=LogSource.AGENT,
            level=LogLevel.INFO,
            message="Msg 3",
            analysis_id="FA-001"
        )
        
        assert len(queue._buffer["FA-001"]) == 2
        assert len(queue._buffer["FA-002"]) == 1
    
    @pytest.mark.asyncio
    async def test_get_buffer(self, queue):
        """Obtener buffer por analysis_id"""
        await queue.log(
            source=LogSource.TOOL,
            level=LogLevel.INFO,
            message="Test",
            analysis_id="FA-001"
        )
        
        buffer = queue.get_buffer("FA-001")
        assert len(buffer) == 1
        assert buffer[0].message == "Test"
        
        # Buffer vacío para otro analysis
        empty_buffer = queue.get_buffer("FA-999")
        assert len(empty_buffer) == 0


class TestLoggingQueueSubscriptions:
    """Tests para suscripciones de la cola"""
    
    @pytest.fixture
    def queue(self):
        """Fresh queue para cada test"""
        reset_logging_queue()
        return get_logging_queue()
    
    @pytest.mark.asyncio
    async def test_subscribe_to_analysis(self, queue):
        """Suscribirse a logs de análisis"""
        received_logs = []
        
        async def callback(entry):
            received_logs.append(entry)
        
        queue.subscribe("FA-001", callback)
        
        await queue.log(
            source=LogSource.TOOL,
            level=LogLevel.INFO,
            message="Test",
            analysis_id="FA-001"
        )
        await asyncio.sleep(0.1)  # Dar tiempo al callback
        
        assert len(received_logs) == 1
    
    @pytest.mark.asyncio
    async def test_unsubscribe(self, queue):
        """Cancelar suscripción"""
        received_logs = []
        
        async def callback(entry):
            received_logs.append(entry)
        
        queue.subscribe("FA-001", callback)
        await queue.log(
            source=LogSource.TOOL,
            level=LogLevel.INFO,
            message="Test 1",
            analysis_id="FA-001"
        )
        
        queue.unsubscribe("FA-001", callback)
        await queue.log(
            source=LogSource.TOOL,
            level=LogLevel.INFO,
            message="Test 2",
            analysis_id="FA-001"
        )
        
        await asyncio.sleep(0.1)
        
        # Solo debería recibir el primer mensaje
        assert len(received_logs) == 1
    
    @pytest.mark.asyncio
    async def test_multiple_subscribers(self, queue):
        """Múltiples suscriptores al mismo análisis"""
        received_1 = []
        received_2 = []
        
        async def callback_1(entry):
            received_1.append(entry)
        
        async def callback_2(entry):
            received_2.append(entry)
        
        queue.subscribe("FA-001", callback_1)
        queue.subscribe("FA-001", callback_2)
        
        await queue.log(
            source=LogSource.AGENT,
            level=LogLevel.INFO,
            message="Test",
            analysis_id="FA-001"
        )
        await asyncio.sleep(0.1)
        
        assert len(received_1) == 1
        assert len(received_2) == 1


class TestGlobalLoggingQueue:
    """Tests para instancia global"""
    
    def test_get_logging_queue_singleton(self):
        """La misma instancia cada vez"""
        reset_logging_queue()
        
        q1 = get_logging_queue()
        q2 = get_logging_queue()
        
        assert q1 is q2
    
    def test_reset_logging_queue(self):
        """Reset limpia el estado de la instancia"""
        q1 = get_logging_queue()
        # Agregar algo al buffer para verificar que se limpia
        q1._buffer["test"] = ["entry"]
        
        reset_logging_queue()
        q2 = get_logging_queue()
        
        # El buffer debería estar vacío
        assert len(q2._buffer) == 0


class TestWebSocketStreamingMock:
    """Tests mock para WebSocket streaming"""
    
    @pytest.mark.asyncio
    async def test_log_entry_serializable(self):
        """LogEntry puede serializarse para WebSocket"""
        entry = LogEntry(
            timestamp=datetime.utcnow().isoformat() + "Z",
            source=LogSource.TOOL,
            level=LogLevel.INFO,
            message="Test message",
            analysis_id="FA-001",
            case_id="IR-001",
            metadata={"step": 1, "tool": "loki"}
        )
        
        # Simular envío por WebSocket
        json_data = entry.to_json()
        parsed = json.loads(json_data)
        
        assert parsed["level"] == "info"
        assert parsed["message"] == "Test message"
        assert parsed["analysis_id"] == "FA-001"
    
    @pytest.mark.asyncio
    async def test_log_batch_serialization(self):
        """Batch de logs serializable"""
        entries = [
            LogEntry(
                timestamp=datetime.utcnow().isoformat() + "Z",
                source=LogSource.SYSTEM,
                level=LogLevel.INFO,
                message=f"Msg {i}"
            )
            for i in range(5)
        ]
        
        batch = {
            "type": "log_batch",
            "logs": [e.to_dict() for e in entries],
            "count": len(entries)
        }
        
        json_data = json.dumps(batch)
        parsed = json.loads(json_data)
        
        assert parsed["count"] == 5
        assert len(parsed["logs"]) == 5


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
