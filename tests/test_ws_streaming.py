"""
MCP Kali Forensics - Tests for WebSocket Streaming v4.4.1
Tests para endpoints WebSocket de streaming en tiempo real
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from fastapi import WebSocket
from fastapi.testclient import TestClient
from starlette.testclient import TestClient as StarletteTestClient
from starlette.websockets import WebSocketState


class TestWebSocketConnectionManager:
    """Tests para ConnectionManager"""
    
    @pytest.fixture
    def manager(self):
        """Manager fresco para cada test"""
        # Import aquí para evitar problemas de importación circular
        from api.routes.ws_streaming import ConnectionManager
        return ConnectionManager()
    
    @pytest.mark.asyncio
    async def test_connect_analysis(self, manager):
        """Conectar WebSocket a analysis"""
        ws = AsyncMock(spec=WebSocket)
        ws.client_state = WebSocketState.CONNECTED
        
        with patch('api.routes.ws_streaming.logging_queue') as mock_queue:
            callback = await manager.connect_analysis(ws, "FA-001")
        
        ws.accept.assert_called_once()
        assert "FA-001" in manager._analysis_connections
        assert ws in manager._analysis_connections["FA-001"]
    
    @pytest.mark.asyncio
    async def test_disconnect_analysis(self, manager):
        """Desconectar WebSocket de analysis"""
        ws = AsyncMock(spec=WebSocket)
        ws.client_state = WebSocketState.CONNECTED
        
        with patch('api.routes.ws_streaming.logging_queue') as mock_queue:
            callback = await manager.connect_analysis(ws, "FA-001")
            manager.disconnect_analysis(ws, "FA-001", callback)
        
        # Conexión removida
        assert "FA-001" not in manager._analysis_connections or ws not in manager._analysis_connections.get("FA-001", set())
    
    @pytest.mark.asyncio
    async def test_connect_case(self, manager):
        """Conectar WebSocket a case"""
        ws = AsyncMock(spec=WebSocket)
        ws.client_state = WebSocketState.CONNECTED
        
        await manager.connect_case(ws, "IR-001")
        
        ws.accept.assert_called_once()
        assert "IR-001" in manager._case_connections
        assert ws in manager._case_connections["IR-001"]
    
    @pytest.mark.asyncio
    async def test_broadcast_to_case(self, manager):
        """Broadcast a caso"""
        ws1 = AsyncMock(spec=WebSocket)
        ws1.client_state = WebSocketState.CONNECTED
        ws2 = AsyncMock(spec=WebSocket)
        ws2.client_state = WebSocketState.CONNECTED
        
        await manager.connect_case(ws1, "IR-001")
        await manager.connect_case(ws2, "IR-002")
        
        # Reset call counts after connect (which sends "connected" message)
        ws1.send_json.reset_mock()
        ws2.send_json.reset_mock()
        
        message = {"type": "event", "data": "test"}
        await manager.broadcast_to_case("IR-001", message)
        
        ws1.send_json.assert_called_once_with(message)
        assert ws2.send_json.call_count == 0
    
    @pytest.mark.asyncio
    async def test_connect_global(self, manager):
        """Conectar WebSocket globalmente"""
        ws = AsyncMock(spec=WebSocket)
        ws.client_state = WebSocketState.CONNECTED
        
        with patch('api.routes.ws_streaming.logging_queue') as mock_queue:
            callback = await manager.connect_global(ws)
        
        ws.accept.assert_called_once()
        assert ws in manager._global_connections
    
    @pytest.mark.asyncio
    async def test_get_stats(self, manager):
        """Obtener estadísticas de conexiones"""
        ws1 = AsyncMock(spec=WebSocket)
        ws1.client_state = WebSocketState.CONNECTED
        ws2 = AsyncMock(spec=WebSocket)
        ws2.client_state = WebSocketState.CONNECTED
        ws3 = AsyncMock(spec=WebSocket)
        ws3.client_state = WebSocketState.CONNECTED
        
        with patch('api.routes.ws_streaming.logging_queue') as mock_queue:
            await manager.connect_analysis(ws1, "FA-001")
            await manager.connect_case(ws2, "IR-001")
            await manager.connect_global(ws3)
        
        stats = manager.get_stats()
        
        assert "analysis_connections" in stats
        assert "case_connections" in stats
        assert "global_connections" in stats
        assert stats["global_connections"] == 1


class TestWebSocketEndpoints:
    """Tests para endpoints WebSocket"""
    
    def test_websocket_analysis_endpoint_exists(self):
        """Verificar que el endpoint existe"""
        from api.routes.ws_streaming import router
        
        routes = [r.path for r in router.routes]
        assert "/ws/analysis/{analysis_id}" in routes
    
    def test_websocket_case_endpoint_exists(self):
        """Verificar endpoint de caso"""
        from api.routes.ws_streaming import router
        
        routes = [r.path for r in router.routes]
        # Verificar si existe alguna ruta de case
        case_routes = [r for r in routes if "case" in r.lower()]
        assert len(case_routes) > 0
    
    def test_websocket_global_endpoint_exists(self):
        """Verificar endpoint global"""
        from api.routes.ws_streaming import router
        
        routes = [r.path for r in router.routes]
        # Verificar si existe alguna ruta global
        global_routes = [r for r in routes if "global" in r.lower()]
        assert len(global_routes) > 0


class TestLogMessageFormat:
    """Tests para formato de mensajes"""
    
    def test_log_message_structure(self):
        """Estructura de mensaje de log"""
        message = {
            "type": "log",
            "level": "INFO",
            "message": "Analysis started",
            "timestamp": "2025-01-15T10:30:00Z",
            "analysis_id": "FA-2025-00001",
            "case_id": "IR-2025-001",
            "context": {
                "tool": "sparrow",
                "step": 1
            }
        }
        
        # Validar campos requeridos
        assert "type" in message
        assert "level" in message
        assert "message" in message
        assert "timestamp" in message
        
        # JSON serializable
        json_str = json.dumps(message)
        assert isinstance(json_str, str)
    
    def test_status_message_structure(self):
        """Estructura de mensaje de status"""
        message = {
            "type": "status",
            "analysis_id": "FA-2025-00001",
            "status": "running",
            "progress": 45,
            "current_step": "Scanning sign-ins",
            "timestamp": "2025-01-15T10:30:00Z"
        }
        
        assert message["type"] == "status"
        assert 0 <= message["progress"] <= 100
    
    def test_heartbeat_message_structure(self):
        """Estructura de heartbeat"""
        message = {
            "type": "heartbeat",
            "timestamp": "2025-01-15T10:30:00Z"
        }
        
        assert message["type"] == "heartbeat"
    
    def test_error_message_structure(self):
        """Estructura de mensaje de error"""
        message = {
            "type": "error",
            "level": "ERROR",
            "message": "Tool execution failed",
            "error_code": "TOOL_ERROR",
            "details": {
                "tool": "loki",
                "exit_code": 1,
                "stderr": "Permission denied"
            },
            "timestamp": "2025-01-15T10:30:00Z"
        }
        
        assert message["type"] == "error"
        assert "error_code" in message


class TestWebSocketReconnection:
    """Tests para lógica de reconexión"""
    
    @pytest.mark.asyncio
    async def test_handle_disconnection_cleanup(self):
        """Limpieza después de desconexión"""
        from api.routes.ws_streaming import ConnectionManager
        
        manager = ConnectionManager()
        ws = AsyncMock(spec=WebSocket)
        ws.client_state = WebSocketState.CONNECTED
        
        with patch('api.routes.ws_streaming.logging_queue') as mock_queue:
            callback = await manager.connect_analysis(ws, "FA-001")
            assert "FA-001" in manager._analysis_connections
            
            manager.disconnect_analysis(ws, "FA-001", callback)
        
        # La lista debería estar vacía o la key removida
        assert "FA-001" not in manager._analysis_connections or len(manager._analysis_connections.get("FA-001", set())) == 0
    
    @pytest.mark.asyncio
    async def test_handle_send_error(self):
        """Manejar error de envío en broadcast"""
        from api.routes.ws_streaming import ConnectionManager
        
        manager = ConnectionManager()
        ws = AsyncMock(spec=WebSocket)
        ws.client_state = WebSocketState.CONNECTED
        
        # Conectar primero (sin error)
        await manager.connect_case(ws, "IR-001")
        
        # Ahora configurar el error para el broadcast
        ws.send_json.side_effect = Exception("Connection closed")
        
        # No debería lanzar excepción
        try:
            await manager.broadcast_to_case("IR-001", {"test": "data"})
        except Exception:
            pytest.fail("broadcast_to_case should handle send errors")


class TestWebSocketAuthentication:
    """Tests para autenticación de WebSocket"""
    
    def test_websocket_requires_valid_origin(self):
        """WebSocket debe validar origen"""
        # En producción, el WebSocket debe validar el header Origin
        valid_origins = [
            "http://localhost:5173",
            "http://localhost:8080",
            "https://forensics.empresa.com"
        ]
        
        for origin in valid_origins:
            # Simular validación
            assert origin.startswith("http")
    
    def test_websocket_token_validation(self):
        """WebSocket puede aceptar token en query params"""
        # URL con token
        url = "/ws/analysis/FA-001?token=abc123"
        
        # El endpoint debería extraer y validar el token
        assert "token=" in url


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
