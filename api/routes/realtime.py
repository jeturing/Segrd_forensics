"""
MCP Kali Forensics - WebSocket Router
Endpoints WebSocket para actualizaciones en tiempo real
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging

from api.services.websocket_manager import ws_manager

router = APIRouter(prefix="/ws", tags=["WebSocket"])
logger = logging.getLogger(__name__)


@router.websocket("/ioc-store")
async def ioc_store_websocket(websocket: WebSocket):
    """
    WebSocket para actualizaciones del IOC Store.
    
    Eventos que se reciben:
    - ioc_created: Nuevo IOC creado
    - ioc_updated: IOC actualizado
    - ioc_deleted: IOC eliminado
    - ioc_enriched: IOC enriquecido con datos externos
    - import_completed: Importación de IOCs completada
    """
    await ws_manager.connect("ioc_store", websocket)
    try:
        while True:
            # Mantener conexión activa, escuchar por mensajes del cliente
            data = await websocket.receive_text()
            # Opcionalmente procesar comandos del cliente
            if data == "ping":
                await ws_manager.send_personal_message({"event": "pong"}, websocket)
    except WebSocketDisconnect:
        await ws_manager.disconnect("ioc_store", websocket)
    except Exception as e:
        logger.error(f"IOC Store WebSocket error: {e}")
        await ws_manager.disconnect("ioc_store", websocket)


@router.websocket("/investigations")
async def investigations_websocket(websocket: WebSocket):
    """
    WebSocket para actualizaciones generales de investigaciones.
    
    Eventos:
    - investigation_created: Nueva investigación
    - investigation_updated: Investigación actualizada
    - investigation_status_changed: Cambio de estado
    - ioc_linked: IOC vinculado a investigación
    - ioc_unlinked: IOC desvinculado
    """
    await ws_manager.connect("investigations", websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await ws_manager.send_personal_message({"event": "pong"}, websocket)
    except WebSocketDisconnect:
        await ws_manager.disconnect("investigations", websocket)
    except Exception as e:
        logger.error(f"Investigations WebSocket error: {e}")
        await ws_manager.disconnect("investigations", websocket)


@router.websocket("/investigation/{investigation_id}")
async def investigation_detail_websocket(
    websocket: WebSocket,
    investigation_id: str
):
    """
    WebSocket para actualizaciones de una investigación específica.
    
    Eventos:
    - updated: Datos de investigación actualizados
    - ioc_linked: IOC vinculado
    - ioc_unlinked: IOC desvinculado
    - timeline_event: Nuevo evento en timeline
    """
    channel = f"investigation:{investigation_id}"
    await ws_manager.connect(channel, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await ws_manager.send_personal_message({"event": "pong"}, websocket)
    except WebSocketDisconnect:
        await ws_manager.disconnect(channel, websocket)
    except Exception as e:
        logger.error(f"Investigation {investigation_id} WebSocket error: {e}")
        await ws_manager.disconnect(channel, websocket)


@router.websocket("/dashboard")
async def dashboard_websocket(websocket: WebSocket):
    """
    WebSocket para métricas y estadísticas del dashboard en tiempo real.
    
    Eventos:
    - stats_update: Actualización de estadísticas
    - alert: Nueva alerta
    - case_update: Actualización de caso
    """
    await ws_manager.connect("dashboard", websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await ws_manager.send_personal_message({"event": "pong"}, websocket)
    except WebSocketDisconnect:
        await ws_manager.disconnect("dashboard", websocket)
    except Exception as e:
        logger.error(f"Dashboard WebSocket error: {e}")
        await ws_manager.disconnect("dashboard", websocket)


@router.websocket("/agents")
async def agents_websocket(websocket: WebSocket):
    """
    WebSocket para actualizaciones de agentes móviles.
    
    Eventos:
    - agent_connected: Agente conectado
    - agent_disconnected: Agente desconectado
    - task_started: Tarea iniciada
    - task_completed: Tarea completada
    - evidence_collected: Evidencia recolectada
    """
    await ws_manager.connect("agents", websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await ws_manager.send_personal_message({"event": "pong"}, websocket)
    except WebSocketDisconnect:
        await ws_manager.disconnect("agents", websocket)
    except Exception as e:
        logger.error(f"Agents WebSocket error: {e}")
        await ws_manager.disconnect("agents", websocket)


# ============================================================================
# ENDPOINT DE ESTADÍSTICAS
# ============================================================================

@router.get("/stats")
async def get_websocket_stats():
    """
    Obtiene estadísticas de conexiones WebSocket activas.
    """
    return ws_manager.get_stats()
