import asyncio
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque, defaultdict
import logging
import json

from .batch_processor import BatchProcessor, BatchJob, BatchStatus

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Métricas de performance do sistema"""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    total_cost: float = 0.0
    active_batches: int = 0
    queue_sizes: Dict[str, int] = field(default_factory=dict)
    provider_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)

class BatchMonitor:
    """Monitor para acompanhar performance e status dos batches"""
    
    def __init__(self, batch_processor: BatchProcessor, metrics_window: int = 300):
        self.batch_processor = batch_processor
        self.metrics_window = metrics_window  # Janela de métricas em segundos
        
        # Histórico de métricas
        self.metrics_history: deque = deque(maxlen=1000)
        
        # Performance por provider
        self.provider_performance: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # Alertas
        self.alerts: List[Dict[str, Any]] = []
        self.alert_thresholds = {
            'high_failure_rate': 0.2,  # 20% de falhas
            'slow_response_time': 30.0,  # 30 segundos
            'queue_backlog': 100,  # 100 items na fila
            'low_credits': 10.0  # $10 em créditos
        }
        
        # Task de monitoramento
        self.monitor_task: Optional[asyncio.Task] = None
        self.running = False
        
        # Registra callbacks no processor
        self._register_callbacks()
    
    def _register_callbacks(self):
        """Registra callbacks no batch processor"""
        self.batch_processor.on('on_item_complete', self._on_item_complete)
        self.batch_processor.on('on_item_error', self._on_item_error)
        self.batch_processor.on('on_batch_complete', self._on_batch_complete)
    
    async def start(self):
        """Inicia monitoramento"""
        if self.running:
            return
        
        self.running = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Batch monitor started")
    
    async def stop(self):
        """Para monitoramento"""
        self.running = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Batch monitor stopped")
    
    async def _monitor_loop(self):
        """Loop principal de monitoramento"""
        while self.running:
            try:
                # Coleta métricas
                metrics = await self._collect_metrics()
                self.metrics_history.append(metrics)
                
                # Verifica alertas
                await self._check_alerts(metrics)
                
                # Limpa alertas antigos
                self._cleanup_old_alerts()
                
                # Aguarda próximo ciclo
                await asyncio.sleep(30)  # Coleta a cada 30 segundos
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                await asyncio.sleep(5)
    
    async def _collect_metrics(self) -> PerformanceMetrics:
        """Coleta métricas atuais do sistema"""
        processor_metrics = self.batch_processor.get_metrics()
        
        # Estatísticas por provider
        provider_stats = {}
        for provider_id, perf_queue in self.provider_performance.items():
            if perf_queue:
                recent_times = [p['response_time'] for p in list(perf_queue)[-10:]]
                recent_success = [p['success'] for p in list(perf_queue)[-10:]]
                
                provider_stats[provider_id] = {
                    'avg_response_time': sum(recent_times) / len(recent_times) if recent_times else 0,
                    'success_rate': sum(recent_success) / len(recent_success) if recent_success else 1,
                    'total_requests': len(perf_queue),
                    'recent_requests': len(recent_times)
                }
        
        return PerformanceMetrics(
            total_requests=processor_metrics['total_processed'] + processor_metrics['total_failed'],
            successful_requests=processor_metrics['total_processed'],
            failed_requests=processor_metrics['total_failed'],
            avg_response_time=processor_metrics['avg_generation_time'],
            total_cost=processor_metrics['total_cost'],
            active_batches=processor_metrics['active_jobs'],
            queue_sizes=processor_metrics['queue_sizes'],
            provider_stats=provider_stats
        )
    
    async def _check_alerts(self, metrics: PerformanceMetrics):
        """Verifica condições de alerta"""
        now = datetime.utcnow()
        
        # Alta taxa de falhas
        if metrics.total_requests > 0:
            failure_rate = metrics.failed_requests / metrics.total_requests
            if failure_rate >= self.alert_thresholds['high_failure_rate']:
                await self._create_alert(
                    'high_failure_rate',
                    f"Alta taxa de falhas: {failure_rate:.1%}",
                    'warning'
                )
        
        # Tempo de resposta lento
        if metrics.avg_response_time >= self.alert_thresholds['slow_response_time']:
            await self._create_alert(
                'slow_response_time',
                f"Tempo de resposta lento: {metrics.avg_response_time:.1f}s",
                'warning'
            )
        
        # Backlog nas filas
        for provider_id, queue_size in metrics.queue_sizes.items():
            if queue_size >= self.alert_thresholds['queue_backlog']:
                await self._create_alert(
                    'queue_backlog',
                    f"Backlog na fila do {provider_id}: {queue_size} items",
                    'warning'
                )
        
        # Verifica créditos baixos (se disponível)
        try:
            for provider_id in metrics.provider_stats.keys():
                credits = await self._check_provider_credits(provider_id)
                if credits and credits <= self.alert_thresholds['low_credits']:
                    await self._create_alert(
                        'low_credits',
                        f"Créditos baixos para {provider_id}: ${credits:.2f}",
                        'error'
                    )
        except Exception as e:
            logger.debug(f"Could not check credits: {e}")
    
    async def _check_provider_credits(self, provider_id: str) -> Optional[float]:
        """Verifica créditos disponíveis de um provider"""
        try:
            provider = await self.batch_processor.provider_manager.get_provider(provider_id)
            if hasattr(provider, 'get_credits'):
                return await provider.get_credits()
        except Exception:
            pass
        return None
    
    async def _create_alert(self, alert_type: str, message: str, severity: str):
        """Cria um novo alerta"""
        # Evita duplicar alertas similares recentes
        recent_alerts = [a for a in self.alerts 
                        if a['type'] == alert_type and 
                        (datetime.utcnow() - a['timestamp']).total_seconds() < 300]
        
        if recent_alerts:
            return
        
        alert = {
            'id': f"{alert_type}_{int(time.time())}",
            'type': alert_type,
            'message': message,
            'severity': severity,
            'timestamp': datetime.utcnow(),
            'resolved': False
        }
        
        self.alerts.append(alert)
        logger.warning(f"Alert created: {message}")
    
    def _cleanup_old_alerts(self):
        """Remove alertas antigos"""
        cutoff = datetime.utcnow() - timedelta(hours=24)
        self.alerts = [a for a in self.alerts if a['timestamp'] > cutoff]
    
    async def _on_item_complete(self, item, job):
        """Callback quando item completa"""
        if item.result:
            provider_id = job.provider_id or 'unknown'
            generation_time = (item.completed_at - item.created_at).total_seconds()
            
            self.provider_performance[provider_id].append({
                'timestamp': datetime.utcnow(),
                'response_time': generation_time,
                'success': True,
                'cost': item.result.cost
            })
    
    async def _on_item_error(self, item, job, error):
        """Callback quando item falha"""
        provider_id = job.provider_id or 'unknown'
        
        self.provider_performance[provider_id].append({
            'timestamp': datetime.utcnow(),
            'response_time': 0,
            'success': False,
            'error': str(error)
        })
    
    async def _on_batch_complete(self, job: BatchJob):
        """Callback quando batch completa"""
        logger.info(f"Batch {job.id} completed: {job.status.value}")
    
    def get_current_metrics(self) -> Optional[PerformanceMetrics]:
        """Retorna métricas mais recentes"""
        return self.metrics_history[-1] if self.metrics_history else None
    
    def get_metrics_history(self, minutes: int = 60) -> List[PerformanceMetrics]:
        """Retorna histórico de métricas dos últimos N minutos"""
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        return [m for m in self.metrics_history if m.timestamp > cutoff]
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Retorna alertas ativos"""
        return [a for a in self.alerts if not a['resolved']]
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Marca alerta como resolvido"""
        for alert in self.alerts:
            if alert['id'] == alert_id:
                alert['resolved'] = True
                alert['resolved_at'] = datetime.utcnow()
                return True
        return False
    
    def get_provider_performance(self, provider_id: str, hours: int = 24) -> Dict[str, Any]:
        """Retorna performance de um provider específico"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        performance_data = self.provider_performance.get(provider_id, deque())
        recent_data = [p for p in performance_data if p['timestamp'] > cutoff]
        
        if not recent_data:
            return {}
        
        successful = [p for p in recent_data if p['success']]
        failed = [p for p in recent_data if not p['success']]
        
        return {
            'total_requests': len(recent_data),
            'successful_requests': len(successful),
            'failed_requests': len(failed),
            'success_rate': len(successful) / len(recent_data) if recent_data else 0,
            'avg_response_time': sum(p['response_time'] for p in successful) / len(successful) if successful else 0,
            'total_cost': sum(p.get('cost', 0) for p in successful),
            'error_types': self._group_errors([p.get('error') for p in failed if p.get('error')])
        }
    
    def _group_errors(self, errors: List[str]) -> Dict[str, int]:
        """Agrupa erros por tipo"""
        error_counts = defaultdict(int)
        for error in errors:
            if error:
                # Simplifica mensagem de erro
                if 'rate limit' in error.lower():
                    error_counts['Rate Limit'] += 1
                elif 'timeout' in error.lower():
                    error_counts['Timeout'] += 1
                elif 'auth' in error.lower():
                    error_counts['Authentication'] += 1
                elif 'credit' in error.lower():
                    error_counts['Insufficient Credits'] += 1
                else:
                    error_counts['Other'] += 1
        return dict(error_counts)
    
    def export_metrics(self, format: str = 'json') -> str:
        """Exporta métricas em formato específico"""
        current = self.get_current_metrics()
        if not current:
            return ""
        
        if format == 'json':
            return json.dumps({
                'timestamp': current.timestamp.isoformat(),
                'metrics': {
                    'total_requests': current.total_requests,
                    'success_rate': current.successful_requests / current.total_requests if current.total_requests > 0 else 0,
                    'avg_response_time': current.avg_response_time,
                    'total_cost': current.total_cost,
                    'active_batches': current.active_batches,
                    'queue_sizes': current.queue_sizes,
                    'provider_stats': current.provider_stats
                },
                'alerts': len(self.get_active_alerts())
            }, indent=2)
        
        return "" 