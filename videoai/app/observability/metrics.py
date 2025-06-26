"""
VideoAI Custom Metrics

Define métricas específicas do negócio para monitoramento do VideoAI.
"""

import time
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

from opentelemetry import metrics
from .telemetry import get_meter

@dataclass
class MetricLabels:
    """Labels padrão para métricas"""
    provider_id: Optional[str] = None
    user_id: Optional[str] = None
    endpoint: Optional[str] = None
    status: Optional[str] = None
    error_type: Optional[str] = None

class VideoAIMetrics:
    """
    Coletor de métricas customizadas para VideoAI
    
    Centraliza todas as métricas de negócio e sistema específicas do VideoAI.
    """
    
    def __init__(self):
        self.meter = get_meter()
        
        # HTTP Request Metrics
        self.http_requests_total = self.meter.create_counter(
            name="http_requests_total",
            description="Total number of HTTP requests",
            unit="1"
        )
        
        self.http_request_duration = self.meter.create_histogram(
            name="http_request_duration_seconds",
            description="HTTP request duration in seconds",
            unit="s"
        )
        
        # Image Generation Metrics
        self.image_generation_requests_total = self.meter.create_counter(
            name="image_generation_requests_total",
            description="Total number of image generation requests",
            unit="1"
        )
        
        self.image_generation_failures_total = self.meter.create_counter(
            name="image_generation_failures_total",
            description="Total number of failed image generation requests",
            unit="1"
        )
        
        self.image_generation_duration = self.meter.create_histogram(
            name="image_generation_duration_seconds",
            description="Image generation duration in seconds",
            unit="s"
        )
        
        self.image_generation_cost_total = self.meter.create_counter(
            name="image_generation_cost_total",
            description="Total cost of image generation",
            unit="USD"
        )
        
        # Provider Metrics
        self.provider_requests_total = self.meter.create_counter(
            name="provider_requests_total",
            description="Total requests per provider",
            unit="1"
        )
        
        self.provider_failures_total = self.meter.create_counter(
            name="provider_failures_total",
            description="Total failures per provider",
            unit="1"
        )
        
        self.provider_response_time = self.meter.create_histogram(
            name="provider_response_time_seconds",
            description="Provider response time in seconds",
            unit="s"
        )
        
        self.provider_credits_remaining = self.meter.create_gauge(
            name="provider_credits_remaining",
            description="Remaining credits per provider",
            unit="USD"
        )
        
        # Cache Metrics
        self.cache_hits_total = self.meter.create_counter(
            name="cache_hits_total",
            description="Total cache hits",
            unit="1"
        )
        
        self.cache_misses_total = self.meter.create_counter(
            name="cache_misses_total",
            description="Total cache misses",
            unit="1"
        )
        
        self.cache_size_bytes = self.meter.create_gauge(
            name="cache_size_bytes",
            description="Current cache size in bytes",
            unit="By"
        )
        
        # Queue Metrics
        self.celery_queue_length = self.meter.create_gauge(
            name="celery_queue_length",
            description="Number of tasks in Celery queue",
            unit="1"
        )
        
        self.celery_worker_up = self.meter.create_gauge(
            name="celery_worker_up",
            description="Celery worker status (1=up, 0=down)",
            unit="1"
        )
        
        self.celery_task_duration = self.meter.create_histogram(
            name="celery_task_duration_seconds",
            description="Celery task execution duration",
            unit="s"
        )
        
        # Business Metrics
        self.active_users = self.meter.create_gauge(
            name="active_users_total",
            description="Number of active users",
            unit="1"
        )
        
        self.revenue_total = self.meter.create_counter(
            name="revenue_total",
            description="Total revenue generated",
            unit="USD"
        )
        
        self.user_satisfaction_score = self.meter.create_histogram(
            name="user_satisfaction_score",
            description="User satisfaction score (1-5)",
            unit="1"
        )
        
        # Batch Processing Metrics
        self.batch_jobs_total = self.meter.create_counter(
            name="batch_jobs_total",
            description="Total batch jobs processed",
            unit="1"
        )
        
        self.batch_job_duration = self.meter.create_histogram(
            name="batch_job_duration_seconds",
            description="Batch job duration in seconds",
            unit="s"
        )
        
        self.batch_job_size = self.meter.create_histogram(
            name="batch_job_size",
            description="Number of items in batch job",
            unit="1"
        )
    
    def record_http_request(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        duration: float,
        user_id: Optional[str] = None
    ):
        """Registra métricas de requisição HTTP"""
        labels = {
            "method": method,
            "endpoint": endpoint,
            "status": str(status_code),
        }
        
        if user_id:
            labels["user_id"] = user_id
        
        self.http_requests_total.add(1, labels)
        self.http_request_duration.record(duration, labels)
    
    def record_image_generation(
        self,
        provider_id: str,
        success: bool,
        duration: float,
        cost: float,
        user_id: Optional[str] = None,
        error_type: Optional[str] = None
    ):
        """Registra métricas de geração de imagem"""
        labels = {
            "provider_id": provider_id,
            "status": "success" if success else "failure"
        }
        
        if user_id:
            labels["user_id"] = user_id
        
        if error_type and not success:
            labels["error_type"] = error_type
        
        # Request count
        self.image_generation_requests_total.add(1, labels)
        
        if success:
            # Duration and cost only for successful requests
            self.image_generation_duration.record(duration, labels)
            self.image_generation_cost_total.add(cost, labels)
        else:
            # Failure count
            self.image_generation_failures_total.add(1, labels)
    
    def record_provider_request(
        self,
        provider_id: str,
        success: bool,
        response_time: float,
        error_type: Optional[str] = None
    ):
        """Registra métricas específicas do provider"""
        labels = {"provider_id": provider_id}
        
        self.provider_requests_total.add(1, labels)
        self.provider_response_time.record(response_time, labels)
        
        if not success:
            if error_type:
                labels["error_type"] = error_type
            self.provider_failures_total.add(1, labels)
    
    def update_provider_credits(self, provider_id: str, credits: float):
        """Atualiza créditos restantes do provider"""
        self.provider_credits_remaining.set(credits, {"provider_id": provider_id})
    
    def record_cache_operation(self, cache_type: str, hit: bool):
        """Registra operação de cache"""
        labels = {"cache_type": cache_type}
        
        if hit:
            self.cache_hits_total.add(1, labels)
        else:
            self.cache_misses_total.add(1, labels)
    
    def update_cache_size(self, cache_type: str, size_bytes: int):
        """Atualiza tamanho do cache"""
        self.cache_size_bytes.set(size_bytes, {"cache_type": cache_type})
    
    def update_queue_length(self, queue_name: str, length: int):
        """Atualiza tamanho da fila"""
        self.celery_queue_length.set(length, {"queue": queue_name})
    
    def update_worker_status(self, worker_id: str, is_up: bool):
        """Atualiza status do worker"""
        self.celery_worker_up.set(1 if is_up else 0, {"worker_id": worker_id})
    
    def record_task_execution(
        self,
        task_name: str,
        duration: float,
        success: bool,
        worker_id: Optional[str] = None
    ):
        """Registra execução de tarefa Celery"""
        labels = {
            "task_name": task_name,
            "status": "success" if success else "failure"
        }
        
        if worker_id:
            labels["worker_id"] = worker_id
        
        self.celery_task_duration.record(duration, labels)
    
    def update_active_users(self, count: int):
        """Atualiza número de usuários ativos"""
        self.active_users.set(count)
    
    def record_revenue(self, amount: float, user_id: Optional[str] = None):
        """Registra receita"""
        labels = {}
        if user_id:
            labels["user_id"] = user_id
        
        self.revenue_total.add(amount, labels)
    
    def record_user_satisfaction(self, score: float, user_id: Optional[str] = None):
        """Registra satisfação do usuário (1-5)"""
        labels = {}
        if user_id:
            labels["user_id"] = user_id
        
        self.user_satisfaction_score.record(score, labels)
    
    def record_batch_job(
        self,
        job_type: str,
        duration: float,
        item_count: int,
        success: bool,
        user_id: Optional[str] = None
    ):
        """Registra execução de job em batch"""
        labels = {
            "job_type": job_type,
            "status": "success" if success else "failure"
        }
        
        if user_id:
            labels["user_id"] = user_id
        
        self.batch_jobs_total.add(1, labels)
        
        if success:
            self.batch_job_duration.record(duration, labels)
            self.batch_job_size.record(item_count, labels)

# Global metrics instance
_metrics_instance: Optional[VideoAIMetrics] = None

def get_metrics() -> VideoAIMetrics:
    """Retorna instância global de métricas"""
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = VideoAIMetrics()
    return _metrics_instance

class MetricsTimer:
    """Context manager para medir duração de operações"""
    
    def __init__(self, callback, *args, **kwargs):
        self.callback = callback
        self.args = args
        self.kwargs = kwargs
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        success = exc_type is None
        self.callback(duration=duration, success=success, *self.args, **self.kwargs)
