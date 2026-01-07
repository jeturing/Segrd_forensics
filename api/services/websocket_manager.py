"""
MCP Kali Forensics - WebSocket Connection Manager
Gestiona conexiones WebSocket para actualizaciones en tiempo real
"""

from fastapi import WebSocket
from typing import Dict, List, Any
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Gestor de conexiones WebSocket con soporte para múltiples canales.
    
    Canales disponibles:
    - ioc_store: Actualizaciones de IOC Store
    - investigations: Actualizaciones de investigaciones
    - investigation:{id}: Actualizaciones de una investigación específica
    - cases: Actualizaciones de casos
    - agents: Actualizaciones de agentes móviles
    - dashboard: Métricas y stats en tiempo real
    """
    
    def __init__(self):
        # Conexiones por canal: {"channel_name": [websocket1, websocket2, ...]}
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # Lock para operaciones thread-safe
        self._lock = asyncio.Lock()
        # Estadísticas
        self.stats = {
            "total_connections": 0,
            "total_messages_sent": 0,
            "channels": {}
        }
    
    async def connect(self, channel: str, websocket: WebSocket):
        """
        Acepta y registra una nueva conexión WebSocket en un canal.
        """
        await websocket.accept()
        
        async with self._lock:
            if channel not in self.active_connections:
                self.active_connections[channel] = []
            self.active_connections[channel].append(websocket)
            
            # Actualizar stats
            self.stats["total_connections"] += 1
            if channel not in self.stats["channels"]:
                self.stats["channels"][channel] = 0
            self.stats["channels"][channel] += 1
        
        logger.info(f"🔌 WebSocket connected to channel: {channel} (total: {len(self.active_connections[channel])})")
        
        # Enviar mensaje de bienvenida
        await self.send_personal_message({
            "event": "connected",
            "channel": channel,
            "timestamp": datetime.utcnow().isoformat(),
            "message": f"Connected to {channel} channel"
        }, websocket)
    
    async def disconnect(self, channel: str, websocket: WebSocket):
        """
        Desconecta y elimina una conexión WebSocket de un canal.
        """
        async with self._lock:
            if channel in self.active_connections:
                if websocket in self.active_connections[channel]:
                    self.active_connections[channel].remove(websocket)
                    if channel in self.stats["channels"]:
                        self.stats["channels"][channel] -= 1
                
                # Limpiar canal vacío
                if not self.active_connections[channel]:
                    del self.active_connections[channel]
        
        logger.info(f"🔌 WebSocket disconnected from channel: {channel}")
    
    async def send_personal_message(self, message: Any, websocket: WebSocket):
        """
        Envía un mensaje a una conexión específica.
        """
        try:
            if isinstance(message, dict):
                await websocket.send_json(message)
            else:
                await websocket.send_text(str(message))
            self.stats["total_messages_sent"] += 1
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
    
    async def broadcast(self, channel: str, message: Any):
        """
        Envía un mensaje a todos los clientes conectados a un canal.
        """
        if channel not in self.active_connections:
            return
        
        # Añadir metadata al mensaje
        if isinstance(message, dict):
            message["_channel"] = channel
            message["_timestamp"] = datetime.utcnow().isoformat()
        
        disconnected = []
        
        for websocket in self.active_connections[channel]:
            try:
                if isinstance(message, dict):
                    await websocket.send_json(message)
                else:
                    await websocket.send_text(str(message))
                self.stats["total_messages_sent"] += 1
            except Exception as e:
                logger.error(f"Error broadcasting to {channel}: {e}")
                disconnected.append(websocket)
        
        # Limpiar conexiones muertas
        for ws in disconnected:
            await self.disconnect(channel, ws)
    
    async def broadcast_to_multiple(self, channels: List[str], message: Any):
        """
        Envía un mensaje a múltiples canales.
        """
        for channel in channels:
            await self.broadcast(channel, message)
    
    async def broadcast_except(self, channel: str, message: Any, exclude: WebSocket):
        """
        Envía un mensaje a todos excepto una conexión específica.
        """
        if channel not in self.active_connections:
            return
        
        for websocket in self.active_connections[channel]:
            if websocket != exclude:
                try:
                    if isinstance(message, dict):
                        await websocket.send_json(message)
                    else:
                        await websocket.send_text(str(message))
                    self.stats["total_messages_sent"] += 1
                except Exception:
                    pass
    
    def get_channel_count(self, channel: str) -> int:
        """
        Retorna el número de conexiones en un canal.
        """
        return len(self.active_connections.get(channel, []))
    
    def get_all_channels(self) -> List[str]:
        """
        Retorna lista de todos los canales activos.
        """
        return list(self.active_connections.keys())
    
    def get_stats(self) -> Dict:
        """
        Retorna estadísticas del manager.
        """
        return {
            **self.stats,
            "active_channels": len(self.active_connections),
            "connections_per_channel": {
                channel: len(connections)
                for channel, connections in self.active_connections.items()
            }
        }


# Instancia global del manager
ws_manager = ConnectionManager()


# ============================================================================
# HELPER FUNCTIONS PARA BROADCAST DE EVENTOS ESPECÍFICOS
# ============================================================================

async def notify_ioc_created(ioc_data: Dict):
    """Notifica creación de nuevo IOC"""
    await ws_manager.broadcast("ioc_store", {
        "event": "ioc_created",
        "data": ioc_data
    })


async def notify_ioc_updated(ioc_id: str, ioc_data: Dict):
    """Notifica actualización de IOC"""
    await ws_manager.broadcast("ioc_store", {
        "event": "ioc_updated",
        "ioc_id": ioc_id,
        "data": ioc_data
    })


async def notify_ioc_deleted(ioc_id: str):
    """Notifica eliminación de IOC"""
    await ws_manager.broadcast("ioc_store", {
        "event": "ioc_deleted",
        "ioc_id": ioc_id
    })


async def notify_ioc_enriched(ioc_id: str, enrichment_data: Dict):
    """Notifica enriquecimiento de IOC"""
    await ws_manager.broadcast("ioc_store", {
        "event": "ioc_enriched",
        "ioc_id": ioc_id,
        "enrichment": enrichment_data
    })


async def notify_ioc_linked(investigation_id: str, ioc_id: str, link_data: Dict):
    """Notifica vinculación de IOC a investigación"""
    # Notificar a ambos canales
    message = {
        "event": "ioc_linked",
        "investigation_id": investigation_id,
        "ioc_id": ioc_id,
        "data": link_data
    }
    await ws_manager.broadcast("ioc_store", message)
    await ws_manager.broadcast(f"investigation:{investigation_id}", message)
    await ws_manager.broadcast("investigations", message)


async def notify_ioc_unlinked(investigation_id: str, ioc_id: str):
    """Notifica desvinculación de IOC de investigación"""
    message = {
        "event": "ioc_unlinked",
        "investigation_id": investigation_id,
        "ioc_id": ioc_id
    }
    await ws_manager.broadcast("ioc_store", message)
    await ws_manager.broadcast(f"investigation:{investigation_id}", message)
    await ws_manager.broadcast("investigations", message)


async def notify_investigation_updated(investigation_id: str, data: Dict):
    """Notifica actualización de investigación"""
    await ws_manager.broadcast("investigations", {
        "event": "investigation_updated",
        "investigation_id": investigation_id,
        "data": data
    })
    await ws_manager.broadcast(f"investigation:{investigation_id}", {
        "event": "updated",
        "data": data
    })


async def notify_import_completed(import_type: str, count: int, details: Dict):
    """Notifica que una importación de IOCs se completó"""
    await ws_manager.broadcast("ioc_store", {
        "event": "import_completed",
        "import_type": import_type,
        "count": count,
        "details": details
    })


# ============================================================================
# v4.1 - TOOL EXECUTION & STREAMING
# ============================================================================

async def notify_tool_execution_started(execution_id: str, tool_name: str, case_id: str = None):
    """Notifica inicio de ejecución de herramienta"""
    message = {
        "event": "execution_started",
        "execution_id": execution_id,
        "tool_name": tool_name,
        "case_id": case_id,
        "status": "running"
    }
    await ws_manager.broadcast("tool_executions", message)
    await ws_manager.broadcast(f"execution:{execution_id}", message)


async def notify_tool_output(execution_id: str, output_line: str, stream: str = "stdout"):
    """Envía línea de output en tiempo real"""
    await ws_manager.broadcast(f"execution:{execution_id}", {
        "event": "output",
        "stream": stream,
        "data": output_line
    })


async def notify_tool_execution_completed(
    execution_id: str, 
    tool_name: str, 
    status: str, 
    result: Dict = None,
    error: str = None
):
    """Notifica finalización de ejecución"""
    message = {
        "event": "execution_completed",
        "execution_id": execution_id,
        "tool_name": tool_name,
        "status": status,
        "result": result,
        "error": error
    }
    await ws_manager.broadcast("tool_executions", message)
    await ws_manager.broadcast(f"execution:{execution_id}", message)


async def notify_execution_progress(execution_id: str, progress: int, message: str = None):
    """Notifica progreso de ejecución (0-100)"""
    await ws_manager.broadcast(f"execution:{execution_id}", {
        "event": "progress",
        "progress": progress,
        "message": message
    })


# ============================================================================
# v4.1 - SOAR & PLAYBOOK EVENTS
# ============================================================================

async def notify_playbook_triggered(playbook_id: str, trigger_type: str, context: Dict):
    """Notifica que un playbook fue disparado"""
    await ws_manager.broadcast("playbooks", {
        "event": "playbook_triggered",
        "playbook_id": playbook_id,
        "trigger_type": trigger_type,
        "context": context
    })


async def notify_playbook_step_started(execution_id: str, step_number: int, action: str):
    """Notifica inicio de paso de playbook"""
    await ws_manager.broadcast(f"playbook:{execution_id}", {
        "event": "step_started",
        "step_number": step_number,
        "action": action
    })


async def notify_playbook_step_completed(
    execution_id: str, 
    step_number: int, 
    status: str,
    result: Dict = None
):
    """Notifica finalización de paso"""
    await ws_manager.broadcast(f"playbook:{execution_id}", {
        "event": "step_completed",
        "step_number": step_number,
        "status": status,
        "result": result
    })


async def notify_playbook_completed(execution_id: str, playbook_name: str, status: str, summary: Dict):
    """Notifica finalización de playbook completo"""
    message = {
        "event": "playbook_completed",
        "execution_id": execution_id,
        "playbook_name": playbook_name,
        "status": status,
        "summary": summary
    }
    await ws_manager.broadcast("playbooks", message)
    await ws_manager.broadcast(f"playbook:{execution_id}", message)


# ============================================================================
# v4.1 - CORRELATION & ALERTS
# ============================================================================

async def notify_alert_created(alert: Dict):
    """Notifica nueva alerta de correlación"""
    await ws_manager.broadcast("correlation_alerts", {
        "event": "alert_created",
        "alert": alert
    })


async def notify_correlation_match(rule_id: str, rule_name: str, match_details: Dict):
    """Notifica match de regla de correlación"""
    await ws_manager.broadcast("correlation_alerts", {
        "event": "correlation_match",
        "rule_id": rule_id,
        "rule_name": rule_name,
        "details": match_details
    })


async def notify_threat_detected(threat_type: str, severity: str, indicators: List, context: Dict):
    """Notifica detección de amenaza por ML/heurística"""
    await ws_manager.broadcast("correlation_alerts", {
        "event": "threat_detected",
        "threat_type": threat_type,
        "severity": severity,
        "indicators": indicators,
        "context": context
    })


async def notify_alert_status_change(alert_id: str, old_status: str, new_status: str, user: str):
    """Notifica cambio de estado de alerta"""
    await ws_manager.broadcast("correlation_alerts", {
        "event": "alert_status_changed",
        "alert_id": alert_id,
        "old_status": old_status,
        "new_status": new_status,
        "changed_by": user
    })


# ============================================================================
# v4.1 - AGENT EVENTS
# ============================================================================

async def notify_agent_registered(agent: Dict):
    """Notifica registro de nuevo agente"""
    await ws_manager.broadcast("agents_v41", {
        "event": "agent_registered",
        "agent": agent
    })


async def notify_agent_heartbeat(agent_id: str, status: str, metrics: Dict = None):
    """Notifica heartbeat de agente"""
    await ws_manager.broadcast("agents_v41", {
        "event": "agent_heartbeat",
        "agent_id": agent_id,
        "status": status,
        "metrics": metrics
    })


async def notify_agent_task_assigned(agent_id: str, task_id: str, task_type: str):
    """Notifica asignación de tarea a agente"""
    await ws_manager.broadcast("agents_v41", {
        "event": "task_assigned",
        "agent_id": agent_id,
        "task_id": task_id,
        "task_type": task_type
    })
    await ws_manager.broadcast(f"agent:{agent_id}", {
        "event": "task_assigned",
        "task_id": task_id,
        "task_type": task_type
    })


async def notify_agent_task_completed(agent_id: str, task_id: str, status: str, result: Dict = None):
    """Notifica finalización de tarea de agente"""
    message = {
        "event": "task_completed",
        "agent_id": agent_id,
        "task_id": task_id,
        "status": status,
        "result": result
    }
    await ws_manager.broadcast("agents_v41", message)
    await ws_manager.broadcast(f"agent:{agent_id}", message)


async def notify_agent_offline(agent_id: str, last_seen: str, reason: str = None):
    """Notifica que un agente se desconectó"""
    await ws_manager.broadcast("agents_v41", {
        "event": "agent_offline",
        "agent_id": agent_id,
        "last_seen": last_seen,
        "reason": reason
    })


# ============================================================================
# v4.1 - GRAPH UPDATES
# ============================================================================

async def notify_graph_node_created(case_id: str, node: Dict):
    """Notifica creación de nodo en grafo"""
    await ws_manager.broadcast(f"graph:{case_id}", {
        "event": "node_created",
        "node": node
    })


async def notify_graph_edge_created(case_id: str, edge: Dict):
    """Notifica creación de arista en grafo"""
    await ws_manager.broadcast(f"graph:{case_id}", {
        "event": "edge_created",
        "edge": edge
    })


async def notify_graph_auto_enriched(case_id: str, source: str, nodes_added: int, edges_added: int):
    """Notifica auto-enriquecimiento de grafo"""
    await ws_manager.broadcast(f"graph:{case_id}", {
        "event": "auto_enriched",
        "source": source,
        "nodes_added": nodes_added,
        "edges_added": edges_added
    })


async def notify_graph_updated(case_id: str, action: str, entity_type: str, entity_id: str):
    """Notifica actualización general del grafo"""
    await ws_manager.broadcast(f"graph:{case_id}", {
        "event": "graph_updated",
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id
    })


# ============================================================================
# v4.1 - DASHBOARD METRICS
# ============================================================================

async def notify_metrics_update(metrics: Dict):
    """Envía actualización de métricas al dashboard"""
    await ws_manager.broadcast("dashboard_v41", {
        "event": "metrics_update",
        "metrics": metrics
    })


async def notify_case_activity(case_id: str, activity_type: str, description: str, user: str = None):
    """Notifica actividad en caso para dashboard"""
    await ws_manager.broadcast("dashboard_v41", {
        "event": "case_activity",
        "case_id": case_id,
        "activity_type": activity_type,
        "description": description,
        "user": user
    })
