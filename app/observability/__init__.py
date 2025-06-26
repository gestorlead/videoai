"""
VideoAI Observability Module

Este módulo contém toda a instrumentação de observabilidade do VideoAI,
incluindo OpenTelemetry, métricas customizadas, e integração com Prometheus.
"""

from .telemetry import setup_telemetry, get_tracer, get_meter
from .metrics import VideoAIMetrics
from .middleware import TracingMiddleware

__all__ = [
    'setup_telemetry',
    'get_tracer', 
    'get_meter',
    'VideoAIMetrics',
    'TracingMiddleware'
] 