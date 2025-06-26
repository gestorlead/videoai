"""
OpenTelemetry Configuration for VideoAI

Configura instrumentação automática e exporters para Prometheus, Jaeger e Loki.
"""

import os
import logging
from typing import Optional

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from prometheus_client import start_http_server

logger = logging.getLogger(__name__)

# Global tracer and meter instances
_tracer: Optional[trace.Tracer] = None
_meter: Optional[metrics.Meter] = None

def setup_telemetry(
    service_name: str = "videoai",
    service_version: str = "1.0.0",
    jaeger_endpoint: str = "http://localhost:14268/api/traces",
    prometheus_port: int = 8000,
    enable_console_export: bool = False
) -> None:
    """
    Configura OpenTelemetry com instrumentação automática
    
    Args:
        service_name: Nome do serviço
        service_version: Versão do serviço
        jaeger_endpoint: Endpoint do Jaeger para traces
        prometheus_port: Porta para métricas Prometheus
        enable_console_export: Habilitar export para console (debug)
    """
    global _tracer, _meter
    
    # Resource identification
    resource = Resource.create({
        SERVICE_NAME: service_name,
        SERVICE_VERSION: service_version,
        "service.instance.id": os.environ.get("HOSTNAME", "unknown"),
        "deployment.environment": os.environ.get("ENVIRONMENT", "development")
    })
    
    # Setup Tracing
    trace_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(trace_provider)
    
    # Jaeger exporter for traces
    jaeger_exporter = JaegerExporter(
        endpoint=jaeger_endpoint,
    )
    span_processor = BatchSpanProcessor(jaeger_exporter)
    trace_provider.add_span_processor(span_processor)
    
    # Console exporter for debugging
    if enable_console_export:
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter
        console_processor = BatchSpanProcessor(ConsoleSpanExporter())
        trace_provider.add_span_processor(console_processor)
    
    # Setup Metrics
    prometheus_reader = PrometheusMetricReader()
    metrics_provider = MeterProvider(
        resource=resource,
        metric_readers=[prometheus_reader]
    )
    metrics.set_meter_provider(metrics_provider)
    
    # Start Prometheus metrics server
    try:
        start_http_server(prometheus_port)
        logger.info(f"Prometheus metrics server started on port {prometheus_port}")
    except Exception as e:
        logger.warning(f"Failed to start Prometheus server: {e}")
    
    # Get tracer and meter instances
    _tracer = trace.get_tracer(__name__)
    _meter = metrics.get_meter(__name__)
    
    # Auto-instrumentation
    setup_auto_instrumentation()
    
    logger.info(f"OpenTelemetry configured for {service_name} v{service_version}")

def setup_auto_instrumentation() -> None:
    """Configura instrumentação automática para bibliotecas comuns"""
    
    # FastAPI instrumentation
    try:
        FastAPIInstrumentor().instrument()
        logger.info("FastAPI auto-instrumentation enabled")
    except Exception as e:
        logger.warning(f"Failed to instrument FastAPI: {e}")
    
    # HTTP requests instrumentation
    try:
        RequestsInstrumentor().instrument()
        logger.info("Requests auto-instrumentation enabled")
    except Exception as e:
        logger.warning(f"Failed to instrument requests: {e}")
    
    # PostgreSQL instrumentation
    try:
        Psycopg2Instrumentor().instrument()
        logger.info("PostgreSQL auto-instrumentation enabled")
    except Exception as e:
        logger.warning(f"Failed to instrument PostgreSQL: {e}")
    
    # Redis instrumentation
    try:
        RedisInstrumentor().instrument()
        logger.info("Redis auto-instrumentation enabled")
    except Exception as e:
        logger.warning(f"Failed to instrument Redis: {e}")
    
    # Celery instrumentation
    try:
        CeleryInstrumentor().instrument()
        logger.info("Celery auto-instrumentation enabled")
    except Exception as e:
        logger.warning(f"Failed to instrument Celery: {e}")

def get_tracer() -> trace.Tracer:
    """Retorna instância do tracer OpenTelemetry"""
    global _tracer
    if _tracer is None:
        _tracer = trace.get_tracer(__name__)
    return _tracer

def get_meter() -> metrics.Meter:
    """Retorna instância do meter OpenTelemetry"""
    global _meter
    if _meter is None:
        _meter = metrics.get_meter(__name__)
    return _meter

def trace_function(name: Optional[str] = None):
    """
    Decorator para adicionar tracing a funções
    
    Args:
        name: Nome do span (usa nome da função se não especificado)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            tracer = get_tracer()
            span_name = name or f"{func.__module__}.{func.__name__}"
            
            with tracer.start_as_current_span(span_name) as span:
                # Add function metadata
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)
                
                try:
                    result = func(*args, **kwargs)
                    span.set_attribute("function.result", "success")
                    return result
                except Exception as e:
                    span.set_attribute("function.result", "error")
                    span.set_attribute("function.error", str(e))
                    span.record_exception(e)
                    raise
        
        return wrapper
    return decorator

async def trace_async_function(name: Optional[str] = None):
    """
    Decorator para adicionar tracing a funções async
    
    Args:
        name: Nome do span (usa nome da função se não especificado)
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            tracer = get_tracer()
            span_name = name or f"{func.__module__}.{func.__name__}"
            
            with tracer.start_as_current_span(span_name) as span:
                # Add function metadata
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)
                
                try:
                    result = await func(*args, **kwargs)
                    span.set_attribute("function.result", "success")
                    return result
                except Exception as e:
                    span.set_attribute("function.result", "error")
                    span.set_attribute("function.error", str(e))
                    span.record_exception(e)
                    raise
        
        return wrapper
    return decorator 