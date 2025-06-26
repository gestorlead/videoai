import asyncio
import time
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import uuid
from enum import Enum
import logging

from .base_provider import (
    ImageGenerationRequest,
    ImageGenerationResponse,
    ProviderError,
    RateLimitError
)
from .provider_manager import ImageProviderManager

logger = logging.getLogger(__name__)

class BatchStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"  # Alguns items falharam

@dataclass
class BatchItem:
    """Item individual em um batch"""
    id: str
    request: ImageGenerationRequest
    status: str = "pending"
    result: Optional[ImageGenerationResponse] = None
    error: Optional[str] = None
    attempts: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

@dataclass
class BatchJob:
    """Job de processamento em batch"""
    id: str
    items: List[BatchItem]
    provider_id: Optional[str] = None
    status: BatchStatus = BatchStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_cost: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def progress(self) -> Dict[str, int]:
        """Retorna progresso do batch"""
        status_count = defaultdict(int)
        for item in self.items:
            status_count[item.status] += 1
        return dict(status_count)
    
    @property
    def is_complete(self) -> bool:
        """Verifica se todos os items foram processados"""
        return all(item.status in ["completed", "failed"] for item in self.items)

class RateLimiter:
    """Rate limiter simples por provider"""
    
    def __init__(self, rpm: int = 60):
        self.rpm = rpm
        self.requests = deque()
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        """Aguarda até poder fazer próxima request"""
        async with self.lock:
            now = datetime.utcnow()
            # Remove requests antigas (> 1 minuto)
            while self.requests and (now - self.requests[0]) > timedelta(minutes=1):
                self.requests.popleft()
            
            # Se atingiu limite, aguarda
            if len(self.requests) >= self.rpm:
                wait_time = 60 - (now - self.requests[0]).total_seconds()
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                    # Tenta novamente
                    return await self.acquire()
            
            # Registra request
            self.requests.append(now)

class BatchProcessor:
    """Processador de batch para geração de imagens"""
    
    def __init__(
        self,
        provider_manager: ImageProviderManager,
        max_concurrent: int = 5,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        self.provider_manager = provider_manager
        self.max_concurrent = max_concurrent
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Rate limiters por provider
        self.rate_limiters: Dict[str, RateLimiter] = {}
        
        # Jobs em processamento
        self.active_jobs: Dict[str, BatchJob] = {}
        
        # Filas por provider
        self.queues: Dict[str, asyncio.Queue] = defaultdict(lambda: asyncio.Queue())
        
        # Workers
        self.workers: List[asyncio.Task] = []
        self.running = False
        
        # Callbacks
        self.callbacks: Dict[str, List[Callable]] = {
            'on_item_complete': [],
            'on_item_error': [],
            'on_batch_complete': [],
            'on_progress': []
        }
        
        # Métricas
        self.metrics = {
            'total_processed': 0,
            'total_failed': 0,
            'total_cost': 0.0,
            'avg_generation_time': 0.0,
            'generation_times': deque(maxlen=100)  # Últimos 100 tempos
        }
    
    async def start(self):
        """Inicia workers de processamento"""
        if self.running:
            return
        
        self.running = True
        
        # Cria workers para cada provider configurado
        providers = self.provider_manager.get_available_providers()
        for provider in providers:
            if provider['is_active']:
                provider_id = provider['id']
                
                # Configura rate limiter
                rpm = provider.get('rate_limit_rpm', 60)
                self.rate_limiters[provider_id] = RateLimiter(rpm)
                
                # Cria workers baseado em max_batch_size
                max_batch = min(provider.get('max_batch_size', 1), self.max_concurrent)
                for i in range(max_batch):
                    worker = asyncio.create_task(
                        self._worker(provider_id, f"{provider_id}_worker_{i}")
                    )
                    self.workers.append(worker)
        
        logger.info(f"Started {len(self.workers)} batch workers")
    
    async def stop(self):
        """Para workers de processamento"""
        self.running = False
        
        # Cancela workers
        for worker in self.workers:
            worker.cancel()
        
        # Aguarda finalização
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()
        
        logger.info("Stopped all batch workers")
    
    async def submit_batch(
        self,
        requests: List[ImageGenerationRequest],
        provider_id: Optional[str] = None,
        priority: int = 0,
        metadata: Dict[str, Any] = None
    ) -> BatchJob:
        """Submete batch para processamento"""
        # Cria job
        job_id = str(uuid.uuid4())
        items = [
            BatchItem(
                id=f"{job_id}_{i}",
                request=req
            )
            for i, req in enumerate(requests)
        ]
        
        job = BatchJob(
            id=job_id,
            items=items,
            provider_id=provider_id,
            metadata=metadata or {}
        )
        
        # Registra job
        self.active_jobs[job_id] = job
        
        # Distribui items nas filas
        if provider_id:
            # Fila específica
            queue = self.queues[provider_id]
            for item in items:
                await queue.put((priority, item, job))
        else:
            # Distribui entre providers disponíveis
            providers = [p for p in self.provider_manager.get_available_providers() 
                        if p['is_active']]
            
            if not providers:
                raise ValueError("No active providers available")
            
            # Round-robin simples
            for i, item in enumerate(items):
                provider = providers[i % len(providers)]
                queue = self.queues[provider['id']]
                await queue.put((priority, item, job))
        
        logger.info(f"Submitted batch {job_id} with {len(items)} items")
        
        return job
    
    async def get_batch_status(self, job_id: str) -> Optional[BatchJob]:
        """Retorna status de um batch"""
        return self.active_jobs.get(job_id)
    
    async def cancel_batch(self, job_id: str) -> bool:
        """Cancela processamento de um batch"""
        job = self.active_jobs.get(job_id)
        if not job:
            return False
        
        # Marca items pendentes como cancelados
        for item in job.items:
            if item.status == "pending":
                item.status = "cancelled"
        
        job.status = BatchStatus.PARTIAL
        job.completed_at = datetime.utcnow()
        
        await self._trigger_callback('on_batch_complete', job)
        
        return True
    
    async def _worker(self, provider_id: str, worker_name: str):
        """Worker que processa items da fila"""
        queue = self.queues[provider_id]
        rate_limiter = self.rate_limiters[provider_id]
        
        logger.info(f"Worker {worker_name} started for provider {provider_id}")
        
        while self.running:
            try:
                # Pega próximo item (com timeout para permitir shutdown)
                priority, item, job = await asyncio.wait_for(
                    queue.get(), 
                    timeout=1.0
                )
                
                # Rate limiting
                await rate_limiter.acquire()
                
                # Processa item
                await self._process_item(item, job, provider_id)
                
                # Verifica se batch completou
                if job.is_complete and job.status == BatchStatus.PROCESSING:
                    await self._complete_batch(job)
                
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_name} error: {e}")
        
        logger.info(f"Worker {worker_name} stopped")
    
    async def _process_item(self, item: BatchItem, job: BatchJob, provider_id: str):
        """Processa um item individual"""
        # Marca início se for primeiro item
        if job.status == BatchStatus.PENDING:
            job.status = BatchStatus.PROCESSING
            job.started_at = datetime.utcnow()
        
        item.status = "processing"
        item.attempts += 1
        
        start_time = time.time()
        
        try:
            # Gera imagem
            provider = await self.provider_manager.get_provider(provider_id)
            response = await provider.generate(item.request)
            
            # Sucesso
            item.status = "completed"
            item.result = response
            item.completed_at = datetime.utcnow()
            
            # Atualiza métricas
            generation_time = time.time() - start_time
            self.metrics['total_processed'] += 1
            self.metrics['total_cost'] += response.cost
            self.metrics['generation_times'].append(generation_time)
            self.metrics['avg_generation_time'] = sum(self.metrics['generation_times']) / len(self.metrics['generation_times'])
            
            job.total_cost += response.cost
            
            # Callback
            await self._trigger_callback('on_item_complete', item, job)
            await self._trigger_callback('on_progress', job)
            
            logger.debug(f"Item {item.id} completed in {generation_time:.2f}s")
            
        except RateLimitError as e:
            # Rate limit - recoloca na fila com delay
            if item.attempts < self.max_retries:
                await asyncio.sleep(self.retry_delay * item.attempts)
                await self.queues[provider_id].put((0, item, job))  # Prioridade baixa
                logger.warning(f"Rate limit for item {item.id}, retrying...")
            else:
                await self._fail_item(item, job, str(e))
                
        except Exception as e:
            # Outros erros
            if item.attempts < self.max_retries:
                # Tenta com outro provider se disponível
                fallback_provider = await self._get_fallback_provider(provider_id)
                if fallback_provider:
                    await self.queues[fallback_provider].put((0, item, job))
                    logger.warning(f"Item {item.id} failed, trying fallback provider")
                else:
                    await self._fail_item(item, job, str(e))
            else:
                await self._fail_item(item, job, str(e))
    
    async def _fail_item(self, item: BatchItem, job: BatchJob, error: str):
        """Marca item como falho"""
        item.status = "failed"
        item.error = error
        item.completed_at = datetime.utcnow()
        
        self.metrics['total_failed'] += 1
        
        await self._trigger_callback('on_item_error', item, job, error)
        await self._trigger_callback('on_progress', job)
        
        logger.error(f"Item {item.id} failed: {error}")
    
    async def _complete_batch(self, job: BatchJob):
        """Finaliza processamento de batch"""
        job.completed_at = datetime.utcnow()
        
        # Define status final
        progress = job.progress
        if progress.get('failed', 0) == 0:
            job.status = BatchStatus.COMPLETED
        elif progress.get('completed', 0) == 0:
            job.status = BatchStatus.FAILED
        else:
            job.status = BatchStatus.PARTIAL
        
        # Calcula tempo total
        if job.started_at:
            total_time = (job.completed_at - job.started_at).total_seconds()
            job.metadata['total_time'] = total_time
        
        await self._trigger_callback('on_batch_complete', job)
        
        logger.info(f"Batch {job.id} completed: {job.status.value} - {progress}")
    
    async def _get_fallback_provider(self, current_provider_id: str) -> Optional[str]:
        """Retorna provider alternativo para fallback"""
        providers = [p for p in self.provider_manager.get_available_providers() 
                    if p['is_active'] and p['id'] != current_provider_id]
        
        if providers:
            # Retorna o de menor custo
            return min(providers, key=lambda p: p.get('cost_per_image', float('inf')))['id']
        
        return None
    
    async def _trigger_callback(self, event: str, *args, **kwargs):
        """Dispara callbacks registrados"""
        for callback in self.callbacks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(*args, **kwargs)
                else:
                    callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Callback error for {event}: {e}")
    
    def on(self, event: str, callback: Callable):
        """Registra callback para evento"""
        if event in self.callbacks:
            self.callbacks[event].append(callback)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Retorna métricas de performance"""
        return {
            **self.metrics,
            'active_jobs': len(self.active_jobs),
            'queue_sizes': {
                provider_id: queue.qsize() 
                for provider_id, queue in self.queues.items()
            }
        } 