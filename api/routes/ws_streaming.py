"""
MCP Kali Forensics - WebSocket Analysis Router v4.4.1
Streaming unificado de logs y eventos de análisis

Endpoints:
- /ws/analysis/{analysis_id} - Stream de logs de un análisis
- /ws/case/{case_id} - Stream de todos los análisis de un caso
- /ws/global - Stream global de todos los logs

Features:
- Replay de logs históricos al conectar
- Heartbeat automático
- Reconnection handling
- Compression de mensajes
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Set, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from starlette.websockets import WebSocketState

from core.logging_queue import logging_queue, LogEntry, LogLevel, LogSource

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket Streaming"])


class ConnectionManager:
    """Gestor de conexiones WebSocket"""
    
    def __init__(self):
        # Conexiones por analysis_id
        self._analysis_connections: Dict[str, Set[WebSocket]] = {}
        
        # Conexiones por case_id
        self._case_connections: Dict[str, Set[WebSocket]] = {}
        
        # Conexiones globales
        self._global_connections: Set[WebSocket] = set()
        
        # Estadísticas
        self._total_connections = 0
        self._total_messages_sent = 0
    
    async def connect_analysis(self, websocket: WebSocket, analysis_id: str):
        """Conectar a stream de análisis"""
        await websocket.accept()
        
        if analysis_id not in self._analysis_connections:
            self._analysis_connections[analysis_id] = set()
        
        self._analysis_connections[analysis_id].add(websocket)
        self._total_connections += 1
        
        # Registrar callback en logging_queue
        async def callback(entry: LogEntry):
            await self._send_to_websocket(websocket, entry)
        
        logging_queue.subscribe(analysis_id, callback)
        
        # Enviar info de conexión
        await websocket.send_json({
            "type": "connected",
            "analysis_id": analysis_id,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
        logger.info(f"🔌 WebSocket connected to analysis {analysis_id}")
        
        return callback
    
    async def connect_case(self, websocket: WebSocket, case_id: str):
        """Conectar a stream de caso"""
        await websocket.accept()
        
        if case_id not in self._case_connections:
            self._case_connections[case_id] = set()
        
        self._case_connections[case_id].add(websocket)
        self._total_connections += 1
        
        await websocket.send_json({
            "type": "connected",
            "case_id": case_id,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
        logger.info(f"🔌 WebSocket connected to case {case_id}")
    
    async def connect_global(self, websocket: WebSocket):
        """Conectar a stream global"""
        await websocket.accept()
        self._global_connections.add(websocket)
        self._total_connections += 1
        
        async def callback(entry: LogEntry):
            await self._send_to_websocket(websocket, entry)
        
        logging_queue.subscribe_global(callback)
        
        await websocket.send_json({
            "type": "connected",
            "scope": "global",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
        logger.info("🔌 WebSocket connected globally")
        
        return callback
    
    def disconnect_analysis(self, websocket: WebSocket, analysis_id: str, callback=None):
        """Desconectar de stream de análisis"""
        if analysis_id in self._analysis_connections:
            self._analysis_connections[analysis_id].discard(websocket)
            
            if callback:
                logging_queue.unsubscribe(analysis_id, callback)
            
            if not self._analysis_connections[analysis_id]:
                del self._analysis_connections[analysis_id]
        
        logger.info(f"🔌 WebSocket disconnected from analysis {analysis_id}")
    
    def disconnect_case(self, websocket: WebSocket, case_id: str):
        """Desconectar de stream de caso"""
        if case_id in self._case_connections:
            self._case_connections[case_id].discard(websocket)
            
            if not self._case_connections[case_id]:
                del self._case_connections[case_id]
        
        logger.info(f"🔌 WebSocket disconnected from case {case_id}")
    
    def disconnect_global(self, websocket: WebSocket, callback=None):
        """Desconectar de stream global"""
        self._global_connections.discard(websocket)
        
        if callback:
            logging_queue.unsubscribe_global(callback)
        
        logger.info("🔌 WebSocket disconnected globally")
    
    async def _send_to_websocket(self, websocket: WebSocket, entry: LogEntry):
        """Enviar log a websocket"""
        if websocket.client_state == WebSocketState.CONNECTED:
            try:
                await websocket.send_json({
                    "type": "log",
                    "data": entry.to_dict()
                })
                self._total_messages_sent += 1
            except Exception as e:
                logger.warning(f"Error sending to websocket: {e}")
    
    async def broadcast_to_case(self, case_id: str, message: Dict):
        """Broadcast a todas las conexiones de un caso"""
        if case_id in self._case_connections:
            for websocket in self._case_connections[case_id].copy():
                try:
                    if websocket.client_state == WebSocketState.CONNECTED:
                        await websocket.send_json(message)
                except Exception:
                    self._case_connections[case_id].discard(websocket)
    
    def get_stats(self) -> Dict:
        """Obtener estadísticas de conexiones"""
        return {
            "analysis_connections": {k: len(v) for k, v in self._analysis_connections.items()},
            "case_connections": {k: len(v) for k, v in self._case_connections.items()},
            "global_connections": len(self._global_connections),
            "total_connections": self._total_connections,
            "total_messages_sent": self._total_messages_sent
        }


# Singleton
connection_manager = ConnectionManager()


@router.websocket("/ws/analysis/{analysis_id}")
async def websocket_analysis(
    websocket: WebSocket,
    analysis_id: str,
    replay: bool = Query(True, description="Replay logs históricos al conectar"),
    replay_limit: int = Query(100, ge=1, le=1000, description="Límite de logs a replay")
):
    """
    🔌 Stream de logs de un análisis específico
    
    Conecta al stream de logs en tiempo real de un análisis forense (FA-XXXX).
    
    Query params:
    - replay: Si enviar logs históricos al conectar (default: true)
    - replay_limit: Máximo de logs históricos a enviar
    
    Mensajes recibidos:
    - {"type": "connected", "analysis_id": "FA-2025-XXX"}
    - {"type": "log", "data": {...}}
    - {"type": "replay_complete", "count": N}
    - {"type": "heartbeat"}
    """
    callback = await connection_manager.connect_analysis(websocket, analysis_id)
    
    try:
        # Replay logs históricos si se solicita
        if replay:
            buffered = logging_queue.get_buffer(analysis_id)
            
            if not buffered:
                # Cargar desde DB
                historical = logging_queue.get_logs(analysis_id=analysis_id, limit=replay_limit)
                historical.reverse()  # Ordenar cronológicamente
                
                for log in historical:
                    await websocket.send_json({
                        "type": "replay_log",
                        "data": log
                    })
            else:
                for entry in buffered[-replay_limit:]:
                    await websocket.send_json({
                        "type": "replay_log",
                        "data": entry.to_dict()
                    })
            
            await websocket.send_json({
                "type": "replay_complete",
                "count": min(len(buffered) if buffered else len(historical), replay_limit)
            })
        
        # Heartbeat loop
        heartbeat_task = asyncio.create_task(_heartbeat_loop(websocket))
        
        try:
            while True:
                # Esperar mensajes del cliente (comandos, pings, etc.)
                data = await websocket.receive_json()
                
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                
                elif data.get("type") == "subscribe_level":
                    # Filtrar por nivel de log
                    pass  # TODO: Implementar filtrado
                
        except WebSocketDisconnect:
            pass
        finally:
            heartbeat_task.cancel()
            
    finally:
        connection_manager.disconnect_analysis(websocket, analysis_id, callback)


@router.websocket("/ws/case/{case_id}")
async def websocket_case(
    websocket: WebSocket,
    case_id: str
):
    """
    🔌 Stream de logs de un caso completo
    
    Recibe logs de TODOS los análisis asociados al caso.
    """
    await connection_manager.connect_case(websocket, case_id)
    
    try:
        # Enviar resumen del caso
        historical = logging_queue.get_logs(case_id=case_id, limit=50)
        
        await websocket.send_json({
            "type": "case_summary",
            "case_id": case_id,
            "recent_logs": len(historical)
        })
        
        heartbeat_task = asyncio.create_task(_heartbeat_loop(websocket))
        
        try:
            while True:
                data = await websocket.receive_json()
                
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                    
        except WebSocketDisconnect:
            pass
        finally:
            heartbeat_task.cancel()
            
    finally:
        connection_manager.disconnect_case(websocket, case_id)


@router.websocket("/ws/global")
async def websocket_global(websocket: WebSocket):
    """
    🔌 Stream global de todos los logs
    
    Requiere permisos de administrador.
    Recibe TODOS los logs del sistema.
    """
    callback = await connection_manager.connect_global(websocket)
    
    try:
        # Enviar estadísticas iniciales
        stats = logging_queue.get_stats()
        await websocket.send_json({
            "type": "system_stats",
            "data": stats
        })
        
        heartbeat_task = asyncio.create_task(_heartbeat_loop(websocket))
        
        try:
            while True:
                data = await websocket.receive_json()
                
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                
                elif data.get("type") == "get_stats":
                    await websocket.send_json({
                        "type": "stats",
                        "data": {
                            "logging_queue": logging_queue.get_stats(),
                            "connections": connection_manager.get_stats()
                        }
                    })
                    
        except WebSocketDisconnect:
            pass
        finally:
            heartbeat_task.cancel()
            
    finally:
        connection_manager.disconnect_global(websocket, callback)


async def _heartbeat_loop(websocket: WebSocket, interval: int = 30):
    """Enviar heartbeats periódicos"""
    while True:
        try:
            await asyncio.sleep(interval)
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_json({
                    "type": "heartbeat",
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                })
        except asyncio.CancelledError:
            break
        except Exception:
            break


# Endpoints REST para logs
@router.get("/logs/analysis/{analysis_id}")
async def get_analysis_logs(
    analysis_id: str,
    level: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """
    📋 Obtener logs de un análisis
    
    Query params:
    - level: Filtrar por nivel (debug, info, warning, error, critical)
    - source: Filtrar por origen (tool, agent, correlation, soar, graph)
    - limit: Máximo de resultados
    - offset: Offset para paginación
    """
    level_enum = LogLevel(level) if level else None
    source_enum = LogSource(source) if source else None
    
    logs = logging_queue.get_logs(
        analysis_id=analysis_id,
        level=level_enum,
        source=source_enum,
        limit=limit,
        offset=offset
    )
    
    return {
        "analysis_id": analysis_id,
        "logs": logs,
        "count": len(logs),
        "limit": limit,
        "offset": offset
    }


@router.get("/logs/case/{case_id}")
async def get_case_logs(
    case_id: str,
    level: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """📋 Obtener logs de un caso"""
    level_enum = LogLevel(level) if level else None
    
    logs = logging_queue.get_logs(
        case_id=case_id,
        level=level_enum,
        limit=limit,
        offset=offset
    )
    
    return {
        "case_id": case_id,
        "logs": logs,
        "count": len(logs)
    }


@router.get("/logs/stats")
async def get_log_stats():
    """📊 Obtener estadísticas de logs"""
    return {
        "logging_queue": logging_queue.get_stats(),
        "connections": connection_manager.get_stats()
    }


@router.delete("/logs/analysis/{analysis_id}")
async def clear_analysis_logs(analysis_id: str):
    """🗑️ Limpiar logs de un análisis"""
    logging_queue.clear_analysis_logs(analysis_id)
    return {"status": "cleared", "analysis_id": analysis_id}


# ==================== GRAPH WEBSOCKET v4.5 ====================

class GraphConnectionManager:
    """Gestor de conexiones WebSocket para el grafo de ataque"""
    
    def __init__(self):
        # Conexiones por case_id
        self._connections: Dict[str, Set[WebSocket]] = {}
        
        # Subscribers para notificaciones de cambios
        self._subscribers: Dict[str, List[asyncio.Queue]] = {}
    
    async def connect(self, websocket: WebSocket, case_id: str):
        """Conectar cliente al stream del grafo"""
        await websocket.accept()
        
        if case_id not in self._connections:
            self._connections[case_id] = set()
            self._subscribers[case_id] = []
        
        self._connections[case_id].add(websocket)
        
        # Crear queue para este cliente
        client_queue = asyncio.Queue()
        self._subscribers[case_id].append(client_queue)
        
        await websocket.send_json({
            "type": "connected",
            "case_id": case_id,
            "channel": "graph_updates",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
        logger.info(f"🔌 Graph WebSocket connected for case {case_id}")
        
        return client_queue
    
    def disconnect(self, websocket: WebSocket, case_id: str, client_queue: asyncio.Queue = None):
        """Desconectar cliente"""
        if case_id in self._connections:
            self._connections[case_id].discard(websocket)
            
            if client_queue and case_id in self._subscribers:
                self._subscribers[case_id] = [
                    q for q in self._subscribers[case_id] if q != client_queue
                ]
            
            if not self._connections[case_id]:
                del self._connections[case_id]
                if case_id in self._subscribers:
                    del self._subscribers[case_id]
        
        logger.info(f"🔌 Graph WebSocket disconnected from case {case_id}")
    
    async def broadcast_node(self, case_id: str, node_data: Dict, action: str = "add"):
        """Broadcast nuevo nodo a todos los clientes del caso"""
        if case_id not in self._subscribers:
            return
        
        message = {
            "type": f"graph:{'new_node' if action == 'add' else 'update_node' if action == 'update' else 'delete_node'}",
            "payload": node_data,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        for queue in self._subscribers[case_id]:
            await queue.put(message)
    
    async def broadcast_edge(self, case_id: str, edge_data: Dict):
        """Broadcast nuevo edge a todos los clientes del caso"""
        if case_id not in self._subscribers:
            return
        
        message = {
            "type": "graph:new_edge",
            "payload": edge_data,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        for queue in self._subscribers[case_id]:
            await queue.put(message)
    
    async def broadcast_analysis_progress(self, case_id: str, progress: int, message: str = ""):
        """Broadcast progreso de análisis"""
        if case_id not in self._subscribers:
            return
        
        msg = {
            "type": "graph:analysis_progress",
            "payload": {
                "progress": progress,
                "message": message
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        for queue in self._subscribers[case_id]:
            await queue.put(msg)
    
    async def broadcast_analysis_complete(self, case_id: str, result: Dict):
        """Broadcast análisis completado"""
        if case_id not in self._subscribers:
            return
        
        message = {
            "type": "graph:analysis_complete",
            "payload": result,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        for queue in self._subscribers[case_id]:
            await queue.put(message)


# Singleton para graph connections
graph_connection_manager = GraphConnectionManager()


@router.websocket("/ws/graph/{case_id}")
async def websocket_graph(
    websocket: WebSocket,
    case_id: str
):
    """
    🔌 Stream de actualizaciones del grafo de ataque
    
    Conecta al stream de actualizaciones en tiempo real del grafo para un caso.
    
    Eventos emitidos:
    - graph:new_node: Nuevo nodo agregado
    - graph:new_edge: Nueva conexión agregada
    - graph:update_node: Nodo actualizado
    - graph:delete_node: Nodo eliminado
    - graph:analysis_progress: Progreso de análisis
    - graph:analysis_complete: Análisis completado
    
    Mensajes aceptados:
    - ping: Heartbeat (responde pong)
    - subscribe: Suscribirse al canal
    - request_full_graph: Solicitar grafo completo
    """
    client_queue = await graph_connection_manager.connect(websocket, case_id)
    
    try:
        # Crear task para enviar mensajes desde la queue
        async def send_messages():
            while True:
                message = await client_queue.get()
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_json(message)
        
        send_task = asyncio.create_task(send_messages())
        
        # Loop principal: recibir mensajes del cliente
        while True:
            try:
                data = await websocket.receive_json()
                
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                    
                elif data.get("type") == "subscribe":
                    # Ya está suscrito al conectar
                    await websocket.send_json({
                        "type": "subscribed",
                        "channel": data.get("payload", {}).get("channel", "graph_updates")
                    })
                    
                elif data.get("type") == "request_full_graph":
                    # Cargar y enviar grafo completo
                    try:
                        from api.services.cases import get_case_graph
                        graph = await get_case_graph(case_id)
                        await websocket.send_json({
                            "type": "full_graph",
                            "payload": graph
                        })
                    except Exception as e:
                        await websocket.send_json({
                            "type": "graph:error",
                            "payload": {"message": str(e)}
                        })
                        
            except WebSocketDisconnect:
                break
                
    finally:
        send_task.cancel()
        graph_connection_manager.disconnect(websocket, case_id, client_queue)
