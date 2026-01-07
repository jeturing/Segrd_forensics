"""
MCP Kali Forensics - WebSocket Router Main v4.4.1
Servidor independiente para streaming de logs
"""

import os
import asyncio
import logging
from datetime import datetime
from typing import Dict, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import uvicorn
import redis.asyncio as redis

# OpenTelemetry
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ws-router")

# Configuración
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/1")
API_URL = os.getenv("API_URL", "http://localhost:8080")
MAX_CONNECTIONS = int(os.getenv("MAX_CONNECTIONS", "1000"))
HEARTBEAT_INTERVAL = int(os.getenv("HEARTBEAT_INTERVAL", "30"))

# OpenTelemetry setup
OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
if OTEL_ENDPOINT:
    resource = Resource.create({"service.name": "ws-router"})
    provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=OTEL_ENDPOINT))
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

# FastAPI app
app = FastAPI(
    title="MCP WebSocket Router",
    version="4.4.1",
    docs_url="/docs"
)

# Instrumentar FastAPI
FastAPIInstrumentor.instrument_app(app)

# Conexiones activas
connections: Dict[str, Set[WebSocket]] = {
    "analysis": {},  # analysis_id -> set of websockets
    "case": {},      # case_id -> set of websockets
    "global": set()  # global log subscribers
}

# Redis client
redis_client = None


@app.on_event("startup")
async def startup():
    global redis_client
    redis_client = await redis.from_url(REDIS_URL)
    logger.info(f"🔌 Conectado a Redis: {REDIS_URL}")
    
    # Iniciar listener de Redis
    asyncio.create_task(redis_listener())


@app.on_event("shutdown")
async def shutdown():
    if redis_client:
        await redis_client.close()


async def redis_listener():
    """Escucha logs de Redis y los distribuye a WebSockets"""
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("logs:analysis", "logs:case", "logs:global")
    
    logger.info("📡 Escuchando canales de logs en Redis")
    
    async for message in pubsub.listen():
        if message["type"] == "message":
            channel = message["channel"].decode()
            data = message["data"].decode()
            
            try:
                import json
                log_entry = json.loads(data)
                await distribute_log(log_entry, channel)
            except Exception as e:
                logger.error(f"Error procesando log: {e}")


async def distribute_log(log_entry: dict, channel: str):
    """Distribuir log a las conexiones correspondientes"""
    if channel == "logs:analysis" and "analysis_id" in log_entry:
        analysis_id = log_entry["analysis_id"]
        if analysis_id in connections["analysis"]:
            await broadcast(connections["analysis"][analysis_id], log_entry)
    
    elif channel == "logs:case" and "case_id" in log_entry:
        case_id = log_entry["case_id"]
        if case_id in connections["case"]:
            await broadcast(connections["case"][case_id], log_entry)
    
    elif channel == "logs:global":
        await broadcast(connections["global"], log_entry)


async def broadcast(websockets: Set[WebSocket], message: dict):
    """Enviar mensaje a múltiples WebSockets"""
    import json
    disconnected = set()
    
    for ws in websockets:
        try:
            await ws.send_json(message)
        except Exception:
            disconnected.add(ws)
    
    # Limpiar desconectados
    for ws in disconnected:
        websockets.discard(ws)


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "ws-router",
        "version": "4.4.1",
        "connections": {
            "analysis": sum(len(s) for s in connections["analysis"].values()),
            "case": sum(len(s) for s in connections["case"].values()),
            "global": len(connections["global"])
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@app.websocket("/ws/analysis/{analysis_id}")
async def ws_analysis(websocket: WebSocket, analysis_id: str):
    """WebSocket para streaming de un análisis específico"""
    await websocket.accept()
    
    if analysis_id not in connections["analysis"]:
        connections["analysis"][analysis_id] = set()
    connections["analysis"][analysis_id].add(websocket)
    
    logger.info(f"🔗 Nueva conexión para análisis: {analysis_id}")
    
    try:
        while True:
            # Heartbeat / esperar mensajes
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=HEARTBEAT_INTERVAL
                )
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "heartbeat"})
    except WebSocketDisconnect:
        pass
    finally:
        connections["analysis"][analysis_id].discard(websocket)
        if not connections["analysis"][analysis_id]:
            del connections["analysis"][analysis_id]
        logger.info(f"🔌 Desconexión de análisis: {analysis_id}")


@app.websocket("/ws/case/{case_id}")
async def ws_case(websocket: WebSocket, case_id: str):
    """WebSocket para streaming de todos los eventos de un caso"""
    await websocket.accept()
    
    if case_id not in connections["case"]:
        connections["case"][case_id] = set()
    connections["case"][case_id].add(websocket)
    
    logger.info(f"🔗 Nueva conexión para caso: {case_id}")
    
    try:
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=HEARTBEAT_INTERVAL
                )
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "heartbeat"})
    except WebSocketDisconnect:
        pass
    finally:
        connections["case"][case_id].discard(websocket)
        if not connections["case"][case_id]:
            del connections["case"][case_id]
        logger.info(f"🔌 Desconexión de caso: {case_id}")


@app.websocket("/ws/global")
async def ws_global(websocket: WebSocket):
    """WebSocket para todos los logs del sistema"""
    await websocket.accept()
    connections["global"].add(websocket)
    
    logger.info("🔗 Nueva conexión global")
    
    try:
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=HEARTBEAT_INTERVAL
                )
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "heartbeat"})
    except WebSocketDisconnect:
        pass
    finally:
        connections["global"].discard(websocket)
        logger.info("🔌 Desconexión global")


@app.get("/stats")
async def stats():
    """Estadísticas del router"""
    return {
        "total_connections": (
            sum(len(s) for s in connections["analysis"].values()) +
            sum(len(s) for s in connections["case"].values()) +
            len(connections["global"])
        ),
        "analysis_subscriptions": len(connections["analysis"]),
        "case_subscriptions": len(connections["case"]),
        "global_subscribers": len(connections["global"]),
        "max_connections": MAX_CONNECTIONS
    }


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8091,
        log_level="info"
    )
