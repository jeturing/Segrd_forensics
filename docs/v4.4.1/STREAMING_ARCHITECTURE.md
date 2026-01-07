# 📡 Streaming Architecture - v4.4.1

> **Real-Time Log Streaming via WebSocket**  
> Documentación técnica de la arquitectura de streaming

---

## 📋 Tabla de Contenidos

1. [Overview](#overview)
2. [Arquitectura](#arquitectura)
3. [Componentes](#componentes)
4. [Protocolo WebSocket](#protocolo-websocket)
5. [Endpoints](#endpoints)
6. [Formato de Mensajes](#formato-de-mensajes)
7. [Frontend Integration](#frontend-integration)
8. [Escalabilidad](#escalabilidad)
9. [Troubleshooting](#troubleshooting)

---

## Overview

La arquitectura de streaming v4.4.1 proporciona:

- **Real-time logs**: Logs de análisis en tiempo real
- **Multi-client support**: Múltiples clientes por análisis
- **Filtering**: Filtrado por nivel, análisis, caso
- **Heartbeat**: Detección de conexiones muertas
- **Reconnection**: Soporte para reconexión automática

### Por qué WebSocket?

| Método | Latencia | Overhead | Bidireccional |
|--------|----------|----------|---------------|
| Polling | Alta (5s+) | Alto | No |
| Long Polling | Media | Medio | No |
| SSE | Baja | Bajo | No |
| **WebSocket** | **Muy baja** | **Muy bajo** | **Sí** |

---

## Arquitectura

```
┌────────────────────────────────────────────────────────────────┐
│                    Streaming Architecture                       │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐      │
│  │   Client 1   │     │   Client 2   │     │   Client N   │      │
│  │  (Browser)   │     │  (Browser)   │     │    (CLI)     │      │
│  └──────┬──────┘     └──────┬──────┘     └──────┬──────┘      │
│         │                   │                   │              │
│         └───────────────────┼───────────────────┘              │
│                             │                                   │
│                             ▼                                   │
│                    ┌─────────────────┐                         │
│                    │   WS Router     │  (Nginx/Traefik)        │
│                    │   (Optional)    │                         │
│                    └────────┬────────┘                         │
│                             │                                   │
│                             ▼                                   │
│         ┌───────────────────────────────────────┐              │
│         │        ConnectionManager              │              │
│         │  ┌─────────────────────────────────┐  │              │
│         │  │ analysis_connections            │  │              │
│         │  │   FA-001: [ws1, ws2]            │  │              │
│         │  │   FA-002: [ws3]                 │  │              │
│         │  ├─────────────────────────────────┤  │              │
│         │  │ case_connections                │  │              │
│         │  │   IR-001: [ws4, ws5]            │  │              │
│         │  ├─────────────────────────────────┤  │              │
│         │  │ global_connections              │  │              │
│         │  │   [ws6, ws7]                    │  │              │
│         │  └─────────────────────────────────┘  │              │
│         └───────────────────┬───────────────────┘              │
│                             │                                   │
│                             ▼                                   │
│                    ┌─────────────────┐                         │
│                    │  LoggingQueue   │                         │
│                    │   (Singleton)   │                         │
│                    └────────┬────────┘                         │
│                             │                                   │
│              ┌──────────────┼──────────────┐                   │
│              │              │              │                   │
│              ▼              ▼              ▼                   │
│         ┌────────┐    ┌────────┐    ┌────────┐                │
│         │Sparrow │    │  Hawk  │    │  Loki  │                │
│         │Service │    │Service │    │Service │                │
│         └────────┘    └────────┘    └────────┘                │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

---

## Componentes

### 1. LoggingQueue (`core/logging_queue.py`)

Cola thread-safe para logs con patrón singleton.

```python
from core.logging_queue import get_logging_queue, LogEntry

# Obtener instancia singleton
queue = get_logging_queue()

# Agregar log
queue.push(LogEntry(
    level="INFO",
    message="Analysis started",
    analysis_id="FA-2025-00001",
    case_id="IR-2025-001",
    context={"tool": "sparrow"}
))

# Suscribirse a logs de un análisis
subscriber_id = queue.subscribe_analysis("FA-2025-00001")

# Obtener logs
logs = queue.get_logs_for_analysis("FA-2025-00001")

# Desuscribirse
queue.unsubscribe(subscriber_id)
```

**Características**:
- Thread-safe con `threading.Lock`
- Buffer circular (máximo 10,000 logs)
- Indexación por `analysis_id` y `case_id`
- Suscriptores con callbacks async

### 2. ConnectionManager (`api/routes/ws_streaming.py`)

Gestor de conexiones WebSocket.

```python
from api.routes.ws_streaming import manager

# Estadísticas de conexiones
stats = manager.get_connection_stats()
# {
#     "analysis_subscriptions": 5,
#     "case_subscriptions": 3,
#     "global_connections": 2,
#     "total": 10
# }

# Broadcast a análisis específico
await manager.broadcast_to_analysis("FA-2025-00001", {
    "type": "log",
    "message": "Processing..."
})

# Broadcast a caso
await manager.broadcast_to_case("IR-2025-001", {
    "type": "status",
    "status": "running"
})

# Broadcast global (admin)
await manager.broadcast_global({
    "type": "system",
    "message": "Maintenance in 5 minutes"
})
```

### 3. WSStreamingRouter (`api/routes/ws_streaming.py`)

Router FastAPI con endpoints WebSocket.

```python
from fastapi import APIRouter, WebSocket

router = APIRouter(prefix="/ws", tags=["streaming"])

@router.websocket("/analysis/{analysis_id}")
async def ws_analysis(websocket: WebSocket, analysis_id: str):
    await manager.connect(websocket, "analysis", analysis_id)
    try:
        while True:
            # Esperar mensajes del cliente (ping, close, etc.)
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket, "analysis", analysis_id)
```

---

## Protocolo WebSocket

### Handshake

```
Client                                   Server
  │                                        │
  │  GET /ws/analysis/FA-001              │
  │  Connection: Upgrade                   │
  │  Upgrade: websocket                    │
  │  Sec-WebSocket-Key: xxx               │
  │ ─────────────────────────────────────▶│
  │                                        │
  │  HTTP/1.1 101 Switching Protocols     │
  │  Upgrade: websocket                    │
  │  Connection: Upgrade                   │
  │  Sec-WebSocket-Accept: yyy            │
  │◀───────────────────────────────────── │
  │                                        │
  │  ═══════ WebSocket Open ═══════       │
  │                                        │
```

### Flujo de Mensajes

```
Client                                   Server
  │                                        │
  │  {"type": "subscribe"}                │
  │ ─────────────────────────────────────▶│
  │                                        │
  │  {"type": "subscribed",               │
  │   "analysis_id": "FA-001"}            │
  │◀───────────────────────────────────── │
  │                                        │
  │  {"type": "log", "level": "INFO"...}  │
  │◀───────────────────────────────────── │
  │                                        │
  │  {"type": "log", "level": "DEBUG"...} │
  │◀───────────────────────────────────── │
  │                                        │
  │  {"type": "heartbeat"}                │
  │◀───────────────────────────────────── │
  │                                        │
  │  {"type": "pong"}                     │
  │ ─────────────────────────────────────▶│
  │                                        │
  │  {"type": "status",                   │
  │   "status": "completed"}              │
  │◀───────────────────────────────────── │
  │                                        │
  │  Close Frame                          │
  │ ─────────────────────────────────────▶│
  │                                        │
```

### Heartbeat

El servidor envía heartbeats cada 30 segundos:

```json
{"type": "heartbeat", "timestamp": "2025-12-08T10:30:00Z"}
```

El cliente debe responder con:

```json
{"type": "pong"}
```

Si no hay respuesta en 2 heartbeats consecutivos, la conexión se cierra.

---

## Endpoints

### `/ws/analysis/{analysis_id}`

Stream de logs para un análisis específico.

**Parámetros**:
- `analysis_id`: ID del análisis (formato `FA-YYYY-XXXXX`)

**Query Params** (opcionales):
- `token`: API token para autenticación
- `level`: Filtrar por nivel mínimo (DEBUG, INFO, WARNING, ERROR)
- `from_start`: Recibir logs históricos al conectar (default: false)

**Ejemplo**:
```javascript
const ws = new WebSocket(
    'ws://localhost:8888/ws/analysis/FA-2025-00001?level=INFO&from_start=true'
);
```

### `/ws/case/{case_id}/live`

Stream de todos los eventos de un caso.

**Parámetros**:
- `case_id`: ID del caso (formato `IR-YYYY-XXX`)

**Eventos**:
- Logs de todos los análisis del caso
- Cambios de estado del caso
- Nuevos análisis iniciados
- Evidencia agregada

**Ejemplo**:
```javascript
const ws = new WebSocket('ws://localhost:8888/ws/case/IR-2025-001/live');
```

### `/ws/global/logs`

Stream global de todos los logs (solo admin).

**Autenticación**: Requiere `mcp:admin` permission

**Eventos**:
- Todos los logs del sistema
- Eventos de sistema
- Alertas críticas

---

## Formato de Mensajes

### Log Message

```json
{
    "type": "log",
    "level": "INFO",
    "message": "Scanning Azure AD sign-ins for last 90 days",
    "timestamp": "2025-12-08T10:30:15.123Z",
    "analysis_id": "FA-2025-00001",
    "case_id": "IR-2025-001",
    "context": {
        "tool": "sparrow",
        "step": 3,
        "total_steps": 12,
        "progress": 25
    }
}
```

### Status Message

```json
{
    "type": "status",
    "analysis_id": "FA-2025-00001",
    "status": "running",
    "progress": 45,
    "current_step": "Analyzing OAuth applications",
    "eta_seconds": 120,
    "timestamp": "2025-12-08T10:31:00Z"
}
```

### Finding Message

```json
{
    "type": "finding",
    "analysis_id": "FA-2025-00001",
    "severity": "HIGH",
    "title": "Suspicious OAuth App Detected",
    "description": "Application 'DataExfil' has excessive permissions",
    "evidence": {
        "app_id": "abc123",
        "permissions": ["Mail.Read", "Files.ReadWrite.All"]
    },
    "timestamp": "2025-12-08T10:32:00Z"
}
```

### Error Message

```json
{
    "type": "error",
    "level": "ERROR",
    "message": "Failed to connect to Microsoft Graph API",
    "error_code": "GRAPH_AUTH_ERROR",
    "details": {
        "status_code": 401,
        "error": "invalid_grant",
        "retry_after": 60
    },
    "timestamp": "2025-12-08T10:33:00Z"
}
```

### Heartbeat Message

```json
{
    "type": "heartbeat",
    "timestamp": "2025-12-08T10:30:00Z",
    "server_time": "2025-12-08T10:30:00.000Z"
}
```

---

## Frontend Integration

### React Hook

```jsx
// hooks/useAnalysisStream.js
import { useState, useEffect, useCallback } from 'react';

export function useAnalysisStream(analysisId, options = {}) {
    const [logs, setLogs] = useState([]);
    const [status, setStatus] = useState('connecting');
    const [error, setError] = useState(null);
    
    const connect = useCallback(() => {
        const wsUrl = `ws://localhost:8888/ws/analysis/${analysisId}`;
        const ws = new WebSocket(wsUrl);
        
        ws.onopen = () => {
            setStatus('connected');
            setError(null);
        };
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            switch (data.type) {
                case 'log':
                    setLogs(prev => [...prev, data].slice(-1000)); // Keep last 1000
                    break;
                case 'status':
                    if (data.status === 'completed' || data.status === 'failed') {
                        setStatus(data.status);
                    }
                    break;
                case 'heartbeat':
                    // Respond to heartbeat
                    ws.send(JSON.stringify({ type: 'pong' }));
                    break;
            }
            
            options.onMessage?.(data);
        };
        
        ws.onerror = (err) => {
            setError(err);
            setStatus('error');
        };
        
        ws.onclose = () => {
            setStatus('disconnected');
            // Reconnect after 3 seconds
            if (options.autoReconnect !== false) {
                setTimeout(connect, 3000);
            }
        };
        
        return ws;
    }, [analysisId, options]);
    
    useEffect(() => {
        const ws = connect();
        return () => ws.close();
    }, [connect]);
    
    return { logs, status, error };
}
```

### Uso del Hook

```jsx
// components/AnalysisLogs.jsx
import { useAnalysisStream } from '../hooks/useAnalysisStream';

function AnalysisLogs({ analysisId }) {
    const { logs, status, error } = useAnalysisStream(analysisId, {
        autoReconnect: true,
        onMessage: (data) => {
            if (data.type === 'finding' && data.severity === 'HIGH') {
                // Notificar hallazgo crítico
                showNotification(data.title);
            }
        }
    });
    
    return (
        <div className="logs-container">
            <div className="status-bar">
                Status: {status}
                {error && <span className="error">{error.message}</span>}
            </div>
            
            <div className="logs-list">
                {logs.map((log, idx) => (
                    <LogEntry key={idx} log={log} />
                ))}
            </div>
        </div>
    );
}
```

### LiveLogsPanel Component

Ver `/frontend-react/src/components/LiveLogsPanel.jsx` para implementación completa con:
- Filtrado por nivel
- Búsqueda de texto
- Auto-scroll
- Pause/Resume
- Export

---

## Escalabilidad

### Single Server

Para deployments pequeños (<100 conexiones simultáneas):

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ MCP Server  │
│ (WS built-in)│
└─────────────┘
```

### Multi-Server con WS Router

Para deployments medianos (100-1000 conexiones):

```
┌─────────────┐  ┌─────────────┐
│   Client    │  │   Client    │
└──────┬──────┘  └──────┬──────┘
       │                │
       └───────┬────────┘
               │
               ▼
        ┌─────────────┐
        │  WS Router  │  (sticky sessions)
        └──────┬──────┘
               │
       ┌───────┴───────┐
       │               │
       ▼               ▼
┌─────────────┐ ┌─────────────┐
│ MCP Server 1│ │ MCP Server 2│
└─────────────┘ └─────────────┘
       │               │
       └───────┬───────┘
               │
               ▼
        ┌─────────────┐
        │    Redis    │  (pub/sub)
        └─────────────┘
```

### Docker Compose (WS Router)

```yaml
# docker-compose.v4.4.1.yml
services:
  ws-router:
    build:
      context: .
      dockerfile: docker/Dockerfile.ws-router
    ports:
      - "8889:8889"
    environment:
      - BACKEND_SERVERS=mcp-forensics:8888
      - STICKY_SESSIONS=true
    depends_on:
      - mcp-forensics
```

### Redis Pub/Sub para Multi-Server

```python
# Publicar log a todos los servidores
import redis

redis_client = redis.Redis(host='redis', port=6379)

async def publish_log(log_entry: LogEntry):
    # Local: agregar a queue
    logging_queue.push(log_entry)
    
    # Distributed: publicar a Redis
    redis_client.publish(
        f"logs:{log_entry.analysis_id}",
        log_entry.json()
    )

# Suscribirse a logs de Redis
async def subscribe_redis_logs():
    pubsub = redis_client.pubsub()
    pubsub.psubscribe("logs:*")
    
    for message in pubsub.listen():
        if message['type'] == 'pmessage':
            log = LogEntry.parse_raw(message['data'])
            await broadcast_to_local_clients(log)
```

---

## Troubleshooting

### Conexión WebSocket falla

**Síntoma**: `WebSocket connection failed`

**Diagnóstico**:
```bash
# Verificar que el servidor está corriendo
curl http://localhost:8888/health

# Verificar WebSocket con wscat
npx wscat -c ws://localhost:8888/ws/analysis/FA-2025-00001
```

**Soluciones**:
1. Verificar CORS en nginx/proxy
2. Verificar que el endpoint existe
3. Verificar firewall

### Logs no llegan

**Síntoma**: Conectado pero no recibe logs

**Diagnóstico**:
```python
# Verificar queue tiene logs
from core.logging_queue import get_logging_queue
queue = get_logging_queue()
print(f"Logs en queue: {len(queue._logs)}")
print(f"Suscriptores: {queue._subscribers}")
```

**Soluciones**:
1. Verificar que el `analysis_id` es correcto
2. Verificar que los servicios están publicando logs
3. Verificar filtro de nivel

### Conexión se cierra inesperadamente

**Síntoma**: `WebSocket closed with code 1006`

**Causas posibles**:
- Timeout del proxy (nginx)
- No responder a heartbeat
- Error del servidor

**Solución nginx**:
```nginx
location /ws/ {
    proxy_pass http://backend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 86400;  # 24 hours
}
```

### Memory leak con muchas conexiones

**Síntoma**: Memoria crece con el tiempo

**Diagnóstico**:
```python
# Verificar conexiones activas
stats = manager.get_connection_stats()
print(f"Total conexiones: {stats['total']}")
```

**Soluciones**:
1. Configurar máximo de conexiones: `WS_MAX_CONNECTIONS=100`
2. Limpiar conexiones huérfanas con heartbeat
3. Reiniciar periódicamente ws-router

---

## Métricas

### Prometheus Metrics

```python
# Métricas exportadas
ws_connections_active{type="analysis"}
ws_connections_active{type="case"}
ws_connections_active{type="global"}
ws_messages_sent_total{type="log"}
ws_messages_sent_total{type="status"}
ws_message_latency_seconds{quantile="0.99"}
```

### Grafana Dashboard

Disponible en `/monitoring/grafana/dashboards/websocket.json`

---

## Referencias

- [RFC 6455 - WebSocket Protocol](https://tools.ietf.org/html/rfc6455)
- [FastAPI WebSocket](https://fastapi.tiangolo.com/advanced/websockets/)
- [core/logging_queue.py](/core/logging_queue.py)
- [api/routes/ws_streaming.py](/api/routes/ws_streaming.py)
- [frontend-react/src/components/LiveLogsPanel.jsx](/frontend-react/src/components/LiveLogsPanel.jsx)

---

**Última actualización**: December 2025  
**Versión**: 1.0
