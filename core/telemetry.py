"""
MCP Kali Forensics - OpenTelemetry Integration v4.4.1
Observabilidad unificada: traces, metrics, logs

Configuración para Jaeger, Prometheus, y exportadores OTLP.
"""

import os
import logging
from typing import Optional, Dict, Any
from functools import wraps
from contextlib import contextmanager

# OpenTelemetry imports
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.trace import Status, StatusCode
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

logger = logging.getLogger(__name__)


class TelemetryConfig:
    """Configuración de telemetría"""
    
    def __init__(self):
        self.enabled = os.getenv("OTEL_ENABLED", "true").lower() == "true"
        self.endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
        self.service_name = os.getenv("OTEL_SERVICE_NAME", "mcp-forensics")
        self.service_version = os.getenv("OTEL_SERVICE_VERSION", "4.4.1")
        self.environment = os.getenv("OTEL_ENVIRONMENT", "development")
        self.sample_rate = float(os.getenv("OTEL_SAMPLE_RATE", "1.0"))
        
        # Métricas
        self.metrics_enabled = os.getenv("OTEL_METRICS_ENABLED", "true").lower() == "true"
        self.metrics_interval = int(os.getenv("OTEL_METRICS_INTERVAL", "60000"))  # ms


# Instancia global
_config: Optional[TelemetryConfig] = None
_tracer: Optional[trace.Tracer] = None
_meter: Optional[metrics.Meter] = None


def init_telemetry(app=None, engine=None) -> bool:
    """
    Inicializar OpenTelemetry
    
    Args:
        app: FastAPI application (opcional, para auto-instrumentación)
        engine: SQLAlchemy engine (opcional, para auto-instrumentación)
    
    Returns:
        bool: True si se inicializó correctamente
    """
    global _config, _tracer, _meter
    
    _config = TelemetryConfig()
    
    if not _config.enabled:
        logger.info("🔇 OpenTelemetry disabled")
        return False
    
    try:
        # Crear resource con información del servicio
        resource = Resource.create({
            SERVICE_NAME: _config.service_name,
            "service.version": _config.service_version,
            "deployment.environment": _config.environment
        })
        
        # =====================================================================
        # TRACES
        # =====================================================================
        tracer_provider = TracerProvider(resource=resource)
        
        # Exportador OTLP
        span_exporter = OTLPSpanExporter(
            endpoint=_config.endpoint,
            insecure=True
        )
        
        # Procesador de spans
        span_processor = BatchSpanProcessor(span_exporter)
        tracer_provider.add_span_processor(span_processor)
        
        # Registrar provider global
        trace.set_tracer_provider(tracer_provider)
        _tracer = trace.get_tracer(_config.service_name, _config.service_version)
        
        logger.info(f"📡 Traces initialized: {_config.endpoint}")
        
        # =====================================================================
        # METRICS
        # =====================================================================
        if _config.metrics_enabled:
            metric_exporter = OTLPMetricExporter(
                endpoint=_config.endpoint,
                insecure=True
            )
            
            metric_reader = PeriodicExportingMetricReader(
                metric_exporter,
                export_interval_millis=_config.metrics_interval
            )
            
            meter_provider = MeterProvider(
                resource=resource,
                metric_readers=[metric_reader]
            )
            
            metrics.set_meter_provider(meter_provider)
            _meter = metrics.get_meter(_config.service_name, _config.service_version)
            
            logger.info(f"📊 Metrics initialized: interval={_config.metrics_interval}ms")
        
        # =====================================================================
        # AUTO-INSTRUMENTACIÓN
        # =====================================================================
        if app:
            FastAPIInstrumentor.instrument_app(app)
            logger.info("✅ FastAPI instrumented")
        
        HTTPXClientInstrumentor().instrument()
        logger.info("✅ HTTPX instrumented")
        
        if engine:
            SQLAlchemyInstrumentor().instrument(engine=engine)
            logger.info("✅ SQLAlchemy instrumented")
        
        logger.info(f"🔭 OpenTelemetry initialized: {_config.service_name} v{_config.service_version}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize OpenTelemetry: {e}")
        return False


def get_tracer() -> trace.Tracer:
    """Obtener tracer global"""
    if _tracer is None:
        return trace.get_tracer("mcp-forensics", "4.4.1")
    return _tracer


def get_meter() -> metrics.Meter:
    """Obtener meter global"""
    if _meter is None:
        return metrics.get_meter("mcp-forensics", "4.4.1")
    return _meter


# =============================================================================
# DECORATORS
# =============================================================================

def traced(
    name: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None
):
    """
    Decorador para trazar funciones
    
    Uso:
        @traced("my_operation")
        async def my_function():
            ...
    """
    def decorator(func):
        span_name = name or f"{func.__module__}.{func.__name__}"
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.start_as_current_span(span_name) as span:
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                
                try:
                    result = await func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.start_as_current_span(span_name) as span:
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                
                try:
                    result = func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


# =============================================================================
# CONTEXT MANAGERS
# =============================================================================

@contextmanager
def trace_span(
    name: str,
    attributes: Optional[Dict[str, Any]] = None,
    kind: trace.SpanKind = trace.SpanKind.INTERNAL
):
    """
    Context manager para crear spans
    
    Uso:
        with trace_span("my_operation", {"case_id": "IR-2025-001"}):
            # do work
    """
    tracer = get_tracer()
    with tracer.start_as_current_span(name, kind=kind) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        
        try:
            yield span
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise


# =============================================================================
# MÉTRICAS FORENSES
# =============================================================================

class ForensicsMetrics:
    """Métricas específicas para operaciones forenses"""
    
    def __init__(self):
        meter = get_meter()
        
        # Contadores
        self.analyses_total = meter.create_counter(
            "forensics.analyses.total",
            description="Total number of forensic analyses",
            unit="1"
        )
        
        self.analyses_by_tool = meter.create_counter(
            "forensics.analyses.by_tool",
            description="Analyses by tool type",
            unit="1"
        )
        
        self.iocs_detected = meter.create_counter(
            "forensics.iocs.detected",
            description="Total IOCs detected",
            unit="1"
        )
        
        self.agent_tasks = meter.create_counter(
            "forensics.agent.tasks",
            description="Agent tasks executed",
            unit="1"
        )
        
        # Histogramas
        self.analysis_duration = meter.create_histogram(
            "forensics.analysis.duration",
            description="Analysis duration",
            unit="s"
        )
        
        self.tool_execution_time = meter.create_histogram(
            "forensics.tool.execution_time",
            description="Tool execution time",
            unit="s"
        )
        
        # Gauges (via callbacks)
        self._active_analyses = 0
        self._active_agents = 0
        
        meter.create_observable_gauge(
            "forensics.analyses.active",
            callbacks=[lambda options: [(self._active_analyses, {})]],
            description="Currently active analyses",
            unit="1"
        )
        
        meter.create_observable_gauge(
            "forensics.agents.active",
            callbacks=[lambda options: [(self._active_agents, {})]],
            description="Currently active agents",
            unit="1"
        )
    
    def record_analysis_started(self, tool: str, case_id: str):
        """Registrar inicio de análisis"""
        self.analyses_total.add(1, {"status": "started"})
        self.analyses_by_tool.add(1, {"tool": tool})
        self._active_analyses += 1
    
    def record_analysis_completed(self, tool: str, duration_seconds: float, success: bool):
        """Registrar fin de análisis"""
        status = "success" if success else "failed"
        self.analyses_total.add(1, {"status": status})
        self.analysis_duration.record(duration_seconds, {"tool": tool, "status": status})
        self._active_analyses = max(0, self._active_analyses - 1)
    
    def record_tool_execution(self, tool: str, duration_seconds: float, exit_code: int):
        """Registrar ejecución de herramienta"""
        status = "success" if exit_code == 0 else "failed"
        self.tool_execution_time.record(duration_seconds, {"tool": tool, "status": status})
    
    def record_iocs_detected(self, count: int, ioc_type: str, source: str):
        """Registrar IOCs detectados"""
        self.iocs_detected.add(count, {"type": ioc_type, "source": source})
    
    def record_agent_task(self, agent_type: str, task_type: str, status: str):
        """Registrar tarea de agente"""
        self.agent_tasks.add(1, {"agent_type": agent_type, "task_type": task_type, "status": status})
    
    def set_active_agents(self, count: int):
        """Actualizar agentes activos"""
        self._active_agents = count


# Instancia global de métricas
_forensics_metrics: Optional[ForensicsMetrics] = None


def get_forensics_metrics() -> ForensicsMetrics:
    """Obtener métricas forenses"""
    global _forensics_metrics
    if _forensics_metrics is None:
        _forensics_metrics = ForensicsMetrics()
    return _forensics_metrics


# =============================================================================
# HELPERS
# =============================================================================

def add_span_attributes(attributes: Dict[str, Any]):
    """Agregar atributos al span actual"""
    span = trace.get_current_span()
    if span and span.is_recording():
        for key, value in attributes.items():
            span.set_attribute(key, value)


def add_span_event(name: str, attributes: Optional[Dict[str, Any]] = None):
    """Agregar evento al span actual"""
    span = trace.get_current_span()
    if span and span.is_recording():
        span.add_event(name, attributes or {})


def get_trace_context() -> Dict[str, str]:
    """Obtener contexto de trace para propagación"""
    carrier = {}
    TraceContextTextMapPropagator().inject(carrier)
    return carrier


def set_span_error(error: Exception, message: Optional[str] = None):
    """Marcar span actual como error"""
    span = trace.get_current_span()
    if span and span.is_recording():
        span.set_status(Status(StatusCode.ERROR, message or str(error)))
        span.record_exception(error)


# =============================================================================
# SHUTDOWN
# =============================================================================

def shutdown_telemetry():
    """Cerrar telemetría de forma limpia"""
    try:
        provider = trace.get_tracer_provider()
        if hasattr(provider, 'shutdown'):
            provider.shutdown()
        
        meter_provider = metrics.get_meter_provider()
        if hasattr(meter_provider, 'shutdown'):
            meter_provider.shutdown()
        
        logger.info("🛑 OpenTelemetry shutdown complete")
    except Exception as e:
        logger.error(f"Error shutting down telemetry: {e}")
