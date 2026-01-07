"""
MCP Kali Forensics - Logging Queue Worker v4.4.1
Procesa logs de análisis y los persiste/distribuye
"""

import os
import asyncio
import logging
import json
from datetime import datetime
from typing import List, Dict, Any

import redis.asyncio as redis
import asyncpg
import aiohttp

# OpenTelemetry
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("logging-worker")

# Configuración
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/3")
WS_ROUTER_URL = os.getenv("WS_ROUTER_URL", "http://ws-router:8091")
POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://forensics:password@localhost:5432/forensics")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "100"))
FLUSH_INTERVAL = int(os.getenv("FLUSH_INTERVAL", "5"))

# OpenTelemetry setup
OTEL_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
if OTEL_ENDPOINT:
    resource = Resource.create({"service.name": "logging-worker"})
    provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=OTEL_ENDPOINT))
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)


class LoggingWorker:
    """
    Worker para procesar logs de análisis
    
    Flujo:
    1. Escucha Redis queue "logs:queue"
    2. Agrupa logs en batches
    3. Persiste en PostgreSQL
    4. Publica en Redis pub/sub para WebSocket router
    """
    
    def __init__(self):
        self.redis_client = None
        self.pg_pool = None
        self.log_buffer: List[Dict[str, Any]] = []
        self.running = False
    
    async def start(self):
        """Iniciar worker"""
        logger.info("🚀 Iniciando Logging Worker v4.4.1")
        
        # Conectar a Redis
        self.redis_client = await redis.from_url(REDIS_URL)
        logger.info(f"✅ Conectado a Redis: {REDIS_URL}")
        
        # Conectar a PostgreSQL
        try:
            self.pg_pool = await asyncpg.create_pool(POSTGRES_URL, min_size=2, max_size=10)
            logger.info(f"✅ Conectado a PostgreSQL")
        except Exception as e:
            logger.warning(f"⚠️ PostgreSQL no disponible: {e}")
            self.pg_pool = None
        
        self.running = True
        
        # Iniciar tareas
        await asyncio.gather(
            self.process_queue(),
            self.flush_buffer_periodically()
        )
    
    async def stop(self):
        """Detener worker"""
        self.running = False
        
        # Flush buffer restante
        await self.flush_buffer()
        
        if self.redis_client:
            await self.redis_client.close()
        
        if self.pg_pool:
            await self.pg_pool.close()
        
        logger.info("🛑 Logging Worker detenido")
    
    async def process_queue(self):
        """Procesar cola de logs de Redis"""
        logger.info("📡 Escuchando cola de logs...")
        
        while self.running:
            try:
                # BLPOP con timeout
                result = await self.redis_client.blpop("logs:queue", timeout=1)
                
                if result:
                    _, log_data = result
                    log_entry = json.loads(log_data)
                    await self.process_log(log_entry)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error procesando queue: {e}")
                await asyncio.sleep(1)
    
    async def process_log(self, log_entry: Dict[str, Any]):
        """Procesar un log individual"""
        # Agregar al buffer
        self.log_buffer.append(log_entry)
        
        # Publicar inmediatamente a WebSocket router via Redis pub/sub
        await self.publish_to_websocket(log_entry)
        
        # Flush si el buffer está lleno
        if len(self.log_buffer) >= BATCH_SIZE:
            await self.flush_buffer()
    
    async def publish_to_websocket(self, log_entry: Dict[str, Any]):
        """Publicar log a canales de Redis para WebSocket router"""
        try:
            # Determinar canal
            if "analysis_id" in log_entry:
                await self.redis_client.publish("logs:analysis", json.dumps(log_entry))
            
            if "case_id" in log_entry:
                await self.redis_client.publish("logs:case", json.dumps(log_entry))
            
            # Siempre publicar a global
            await self.redis_client.publish("logs:global", json.dumps(log_entry))
            
        except Exception as e:
            logger.error(f"❌ Error publicando a WebSocket: {e}")
    
    async def flush_buffer(self):
        """Persistir buffer en PostgreSQL"""
        if not self.log_buffer:
            return
        
        logs_to_persist = self.log_buffer.copy()
        self.log_buffer.clear()
        
        logger.info(f"💾 Persistiendo {len(logs_to_persist)} logs...")
        
        if self.pg_pool:
            await self.persist_to_postgres(logs_to_persist)
        else:
            # Fallback: guardar en archivo
            await self.persist_to_file(logs_to_persist)
    
    async def persist_to_postgres(self, logs: List[Dict[str, Any]]):
        """Persistir logs en PostgreSQL"""
        try:
            async with self.pg_pool.acquire() as conn:
                # Preparar datos para COPY
                records = []
                for log in logs:
                    records.append((
                        log.get("analysis_id"),
                        log.get("case_id"),
                        log.get("level", "INFO"),
                        log.get("message", ""),
                        json.dumps(log.get("context", {})),
                        datetime.fromisoformat(log.get("timestamp", datetime.utcnow().isoformat()))
                    ))
                
                # Insertar en batch
                await conn.executemany(
                    """
                    INSERT INTO analysis_logs 
                    (analysis_id, case_id, level, message, context, timestamp)
                    VALUES ($1, $2, $3, $4, $5::jsonb, $6)
                    """,
                    records
                )
                
                logger.info(f"✅ Persistidos {len(logs)} logs en PostgreSQL")
                
        except Exception as e:
            logger.error(f"❌ Error persistiendo en PostgreSQL: {e}")
            # Fallback a archivo
            await self.persist_to_file(logs)
    
    async def persist_to_file(self, logs: List[Dict[str, Any]]):
        """Persistir logs en archivo (fallback)"""
        try:
            filename = f"/var/analysis-logs/logs_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.jsonl"
            
            with open(filename, 'a') as f:
                for log in logs:
                    f.write(json.dumps(log) + "\n")
            
            logger.info(f"💾 Guardados {len(logs)} logs en {filename}")
            
        except Exception as e:
            logger.error(f"❌ Error guardando en archivo: {e}")
    
    async def flush_buffer_periodically(self):
        """Flush el buffer periódicamente"""
        while self.running:
            await asyncio.sleep(FLUSH_INTERVAL)
            if self.log_buffer:
                await self.flush_buffer()


async def main():
    worker = LoggingWorker()
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        pass
    finally:
        await worker.stop()


if __name__ == "__main__":
    asyncio.run(main())
