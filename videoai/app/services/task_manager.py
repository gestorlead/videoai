import asyncio
import logging
from typing import Dict, Any, Optional, List, Type
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import uuid

from ..models.base_task import MediaTask, TaskStatus, TaskType, TaskLog, TaskPriority
from ..schemas.tasks import TaskCreateRequest, TaskResponse, TaskListFilters, TaskStatistics
from .queue_service import QueueService
from .webhook_service import WebhookService
from .provider_registry import ProviderRegistry

logger = logging.getLogger(__name__)

class UniversalTaskManager:
    """Gerenciador universal de tasks assíncronas para todos os tipos de mídia"""
    
    def __init__(self, db: Session):
        self.db = db
        self.queue_service = QueueService()
        self.webhook_service = WebhookService()
        self.provider_registry = ProviderRegistry()
        
        # Workers por tipo de task
        self.workers: Dict[str, asyncio.Task] = {}
        self.running = False
        
        # Configuração de workers por tipo
        self.worker_config = {
            TaskType.IMAGE_GENERATION: {"count": 3, "batch_size": 5},
            TaskType.IMAGE_OPTIMIZATION: {"count": 2, "batch_size": 10},
            TaskType.VIDEO_GENERATION: {"count": 2, "batch_size": 1},
            TaskType.VIDEO_EDITING: {"count": 2, "batch_size": 1},
            TaskType.AUDIO_TRANSCRIPTION: {"count": 3, "batch_size": 3},
            TaskType.AUDIO_GENERATION: {"count": 2, "batch_size": 5},
            TaskType.SUBTITLE_GENERATION: {"count": 2, "batch_size": 2},
            TaskType.SUBTITLE_TRANSLATION: {"count": 2, "batch_size": 5},
        }
    
    async def create_task(self, user_id: str, task_request: TaskCreateRequest) -> str:
        """Cria nova task assíncrona"""
        
        # Validação da entrada
        await self._validate_task_input(task_request)
        
        # Obtém provider adequado
        provider = await self.provider_registry.get_provider(
            task_request.task_type.value,
            task_request.input_data.get("provider_id")
        )
        
        if not provider:
            raise ValueError(f"No provider available for {task_request.task_type.value}")
        
        # Estimativas
        estimated_cost = await provider.estimate_cost(task_request.input_data)
        estimated_duration = await provider.estimate_duration(task_request.input_data)
        
        # Cria task no banco
        task = MediaTask(
            id=str(uuid.uuid4()),
            user_id=user_id,
            task_type=task_request.task_type.value,
            status=TaskStatus.PENDING.value,
            input_data=task_request.input_data,
            webhook_url=task_request.webhook_url,
            webhook_secret=task_request.webhook_secret,
            priority=task_request.priority,
            estimated_duration=estimated_duration,
            estimated_cost=estimated_cost,
            provider_id=provider.id,
            metadata=task_request.metadata or {},
            tags=task_request.tags or []
        )
        
        self.db.add(task)
        self.db.commit()
        
        # Log de criação
        await self._log_task_event(
            task.id, 
            "task_created", 
            {"provider": provider.id, "estimated_cost": estimated_cost}
        )
        
        # Adiciona à fila
        await self.queue_service.enqueue_task(
            task_id=task.id,
            task_type=task.task_type,
            priority=task.priority
        )
        
        # Atualiza status para queued
        task.status = TaskStatus.QUEUED.value
        self.db.commit()
        
        logger.info(f"Task {task.id} created for user {user_id} - Type: {task.task_type}")
        return task.id
    
    async def get_task_status(self, task_id: str, user_id: Optional[str] = None) -> Optional[TaskResponse]:
        """Retorna status detalhado da task"""
        query = self.db.query(MediaTask).filter(MediaTask.id == task_id)
        
        if user_id:
            query = query.filter(MediaTask.user_id == user_id)
        
        task = query.first()
        if not task:
            return None
        
        # Calcula progresso e posição na fila
        progress = task.progress
        queue_position = None
        
        if task.status == TaskStatus.QUEUED.value:
            queue_position = await self.queue_service.get_position(task_id)
        elif task.status == TaskStatus.PROCESSING.value and not progress:
            # Estima progresso baseado no tempo
            if task.started_at and task.estimated_duration:
                elapsed = (datetime.utcnow() - task.started_at).total_seconds()
                progress = min(elapsed / task.estimated_duration, 0.95)
        
        return TaskResponse(
            id=task.id,
            user_id=task.user_id,
            task_type=task.task_type,
            status=task.status,
            progress=progress,
            progress_message=task.progress_message,
            input_data=task.input_data,
            output_data=task.output_data,
            estimated_duration=task.estimated_duration,
            actual_duration=task.actual_duration,
            estimated_cost=task.estimated_cost,
            actual_cost=task.actual_cost,
            created_at=task.created_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
            expires_at=task.expires_at,
            error_message=task.error_message,
            error_details=task.error_details,
            retry_count=task.retry_count,
            provider_id=task.provider_id,
            external_task_id=task.external_task_id,
            queue_position=queue_position,
            metadata=task.metadata,
            tags=task.tags
        )
    
    async def list_user_tasks(self, user_id: str, filters: TaskListFilters) -> List[TaskResponse]:
        """Lista tasks do usuário com filtros"""
        query = self.db.query(MediaTask).filter(MediaTask.user_id == user_id)
        
        # Aplica filtros
        if filters.status:
            query = query.filter(MediaTask.status == filters.status.value)
        if filters.task_type:
            query = query.filter(MediaTask.task_type == filters.task_type.value)
        if filters.provider_id:
            query = query.filter(MediaTask.provider_id == filters.provider_id)
        if filters.created_after:
            query = query.filter(MediaTask.created_at >= filters.created_after)
        if filters.created_before:
            query = query.filter(MediaTask.created_at <= filters.created_before)
        
        # Filtro por tags (JSON contains)
        if filters.tags:
            for tag in filters.tags:
                query = query.filter(MediaTask.tags.contains([tag]))
        
        # Ordenação e paginação
        tasks = query.order_by(MediaTask.created_at.desc()) \
                    .offset(filters.offset) \
                    .limit(filters.limit) \
                    .all()
        
        # Converte para response
        results = []
        for task in tasks:
            task_response = await self.get_task_status(task.id)
            if task_response:
                results.append(task_response)
        
        return results
    
    async def get_user_statistics(self, user_id: str) -> TaskStatistics:
        """Retorna estatísticas das tasks do usuário"""
        tasks = self.db.query(MediaTask).filter(MediaTask.user_id == user_id).all()
        
        if not tasks:
            return TaskStatistics(
                total_tasks=0,
                tasks_by_status={},
                tasks_by_type={},
                total_cost=0.0,
                average_duration=0.0,
                success_rate=0.0
            )
        
        # Estatísticas por status
        tasks_by_status = {}
        for status in TaskStatus:
            count = len([t for t in tasks if t.status == status.value])
            if count > 0:
                tasks_by_status[status.value] = count
        
        # Estatísticas por tipo
        tasks_by_type = {}
        for task_type in TaskType:
            count = len([t for t in tasks if t.task_type == task_type.value])
            if count > 0:
                tasks_by_type[task_type.value] = count
        
        # Custo total
        total_cost = sum(t.actual_cost or t.estimated_cost for t in tasks)
        
        # Duração média (apenas tasks completadas)
        completed_tasks = [t for t in tasks if t.status == TaskStatus.COMPLETED.value and t.actual_duration]
        average_duration = sum(t.actual_duration for t in completed_tasks) / len(completed_tasks) if completed_tasks else 0.0
        
        # Taxa de sucesso
        finished_tasks = [t for t in tasks if t.status in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value]]
        success_rate = len([t for t in finished_tasks if t.status == TaskStatus.COMPLETED.value]) / len(finished_tasks) if finished_tasks else 0.0
        
        return TaskStatistics(
            total_tasks=len(tasks),
            tasks_by_status=tasks_by_status,
            tasks_by_type=tasks_by_type,
            total_cost=total_cost,
            average_duration=average_duration,
            success_rate=success_rate
        )
    
    async def cancel_task(self, task_id: str, user_id: str) -> bool:
        """Cancela task se ainda não foi processada"""
        task = self.db.query(MediaTask).filter(
            and_(
                MediaTask.id == task_id,
                MediaTask.user_id == user_id
            )
        ).first()
        
        if not task:
            return False
        
        # Verifica se pode cancelar
        if task.status in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value, TaskStatus.CANCELLED.value]:
            return False
        
        # Cancela no provider se já iniciou
        if task.status == TaskStatus.PROCESSING.value and task.external_task_id:
            try:
                provider = await self.provider_registry.get_provider(task.task_type, task.provider_id)
                if provider and hasattr(provider, 'cancel_task'):
                    await provider.cancel_task(task.external_task_id)
            except Exception as e:
                logger.error(f"Error cancelling task in provider: {e}")
        
        # Remove da fila se ainda não iniciou
        if task.status == TaskStatus.QUEUED.value:
            await self.queue_service.remove_from_queue(task_id)
        
        # Atualiza status
        task.status = TaskStatus.CANCELLED.value
        task.completed_at = datetime.utcnow()
        if task.started_at:
            task.actual_duration = (task.completed_at - task.started_at).total_seconds()
        
        self.db.commit()
        
        # Log de cancelamento
        await self._log_task_event(task_id, "task_cancelled", {"cancelled_by": user_id})
        
        # Notifica via webhook se configurado
        if task.webhook_url:
            await self.webhook_service.notify_task_completion(task)
        
        return True
    
    async def update_task_progress(self, task_id: str, progress: float, message: Optional[str] = None):
        """Atualiza progresso de uma task"""
        task = self.db.query(MediaTask).filter(MediaTask.id == task_id).first()
        if not task:
            return
        
        task.progress = max(0.0, min(1.0, progress))
        if message:
            task.progress_message = message
        
        self.db.commit()
        
        # Log de progresso significativo
        if int(progress * 100) % 25 == 0:  # Log a cada 25%
            await self._log_task_event(
                task_id, 
                "progress_update", 
                {"progress": progress, "message": message}
            )
    
    async def start_workers(self):
        """Inicia workers para processar tasks"""
        if self.running:
            return
        
        self.running = True
        
        # Cria workers por tipo de task
        for task_type in TaskType:
            if task_type.value not in self.worker_config:
                continue
                
            config = self.worker_config[task_type]
            for i in range(config["count"]):
                worker_name = f"{task_type.value}_worker_{i}"
                worker = asyncio.create_task(
                    self._worker(task_type, worker_name, config["batch_size"])
                )
                self.workers[worker_name] = worker
        
        logger.info(f"Started {len(self.workers)} task workers")
    
    async def stop_workers(self):
        """Para todos os workers"""
        self.running = False
        
        # Cancela todos os workers
        for worker in self.workers.values():
            worker.cancel()
        
        # Aguarda finalização
        await asyncio.gather(*self.workers.values(), return_exceptions=True)
        self.workers.clear()
        
        logger.info("All task workers stopped")
    
    async def _worker(self, task_type: TaskType, worker_name: str, batch_size: int):
        """Worker que processa tasks de um tipo específico"""
        logger.info(f"Worker {worker_name} started")
        
        while self.running:
            try:
                # Pega próximas tasks da fila (batch)
                task_ids = await self.queue_service.dequeue_batch(
                    task_type.value, 
                    batch_size
                )
                
                if not task_ids:
                    await asyncio.sleep(1)
                    continue
                
                # Processa tasks em paralelo
                tasks = []
                for task_id in task_ids:
                    tasks.append(self._process_task(task_id))
                
                await asyncio.gather(*tasks, return_exceptions=True)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_name} error: {e}")
                await asyncio.sleep(5)
        
        logger.info(f"Worker {worker_name} stopped")
    
    async def _process_task(self, task_id: str):
        """Processa uma task individual"""
        task = self.db.query(MediaTask).filter(MediaTask.id == task_id).first()
        if not task:
            logger.warning(f"Task {task_id} not found")
            return
        
        try:
            # Marca como processando
            task.status = TaskStatus.PROCESSING.value
            task.started_at = datetime.utcnow()
            self.db.commit()
            
            await self._log_task_event(task_id, "processing_started", {"provider": task.provider_id})
            
            # Obtém provider
            provider = await self.provider_registry.get_provider(
                task.task_type, 
                task.provider_id
            )
            
            if not provider:
                raise ValueError(f"Provider {task.provider_id} not found")
            
            # Processa com o provider
            result = await self._execute_with_provider(task, provider)
            
            # Sucesso
            await self._complete_task(task, result)
            
        except Exception as e:
            # Falha
            await self._fail_task(task, str(e))
    
    async def _execute_with_provider(self, task: MediaTask, provider: Any) -> Dict[str, Any]:
        """Executa task com o provider apropriado"""
        
        # Provider com suporte a webhook
        if hasattr(provider, 'supports_webhook') and provider.supports_webhook:
            # Configura webhook callback
            callback_url = f"{self.webhook_service.base_url}/api/v1/internal/webhooks/{task.id}"
            
            # Inicia task assíncrona
            external_id = await provider.start_async_task(
                task.input_data,
                webhook_url=callback_url,
                webhook_secret=task.webhook_secret
            )
            
            task.external_task_id = external_id
            self.db.commit()
            
            # Aguarda callback ou timeout
            result = await self._wait_for_webhook_or_poll(task, provider)
            
        else:
            # Provider sem webhook - polling ou síncrono
            if hasattr(provider, 'process_with_polling'):
                result = await provider.process_with_polling(
                    task.input_data,
                    progress_callback=lambda p, m: asyncio.create_task(
                        self.update_task_progress(task.id, p, m)
                    )
                )
            else:
                # Processamento síncrono
                result = await provider.process(task.input_data)
        
        return result
    
    async def _wait_for_webhook_or_poll(self, task: MediaTask, provider: Any, timeout: int = 3600) -> Dict[str, Any]:
        """Aguarda webhook ou faz polling até conclusão"""
        start_time = datetime.utcnow()
        poll_interval = 30  # segundos
        
        while (datetime.utcnow() - start_time).total_seconds() < timeout:
            # Verifica se task foi atualizada via webhook
            self.db.refresh(task)
            
            if task.status in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value]:
                return task.output_data or {}
            
            # Faz polling se provider suporta
            if hasattr(provider, 'get_task_status'):
                status = await provider.get_task_status(task.external_task_id)
                
                if status.get('completed'):
                    return status.get('result', {})
                
                if status.get('failed'):
                    raise Exception(status.get('error', 'Task failed in provider'))
                
                # Atualiza progresso
                if status.get('progress'):
                    await self.update_task_progress(
                        task.id, 
                        status['progress'], 
                        status.get('message')
                    )
            
            await asyncio.sleep(poll_interval)
        
        raise TimeoutError(f"Task {task.id} timed out after {timeout} seconds")
    
    async def _complete_task(self, task: MediaTask, result: Dict[str, Any]):
        """Marca task como concluída"""
        task.status = TaskStatus.COMPLETED.value
        task.completed_at = datetime.utcnow()
        task.output_data = result
        task.progress = 1.0
        task.progress_message = "Completed successfully"
        
        # Calcula duração e custo real
        if task.started_at:
            task.actual_duration = (task.completed_at - task.started_at).total_seconds()
        
        # Atualiza custo real se disponível
        if result.get('cost'):
            task.actual_cost = result['cost']
        else:
            task.actual_cost = task.estimated_cost
        
        self.db.commit()
        
        # Log de conclusão
        await self._log_task_event(
            task.id, 
            "task_completed", 
            {
                "duration": task.actual_duration,
                "cost": task.actual_cost,
                "output_size": len(str(result))
            }
        )
        
        # Notifica via webhook
        if task.webhook_url:
            await self.webhook_service.notify_task_completion(task)
        
        logger.info(f"Task {task.id} completed successfully")
    
    async def _fail_task(self, task: MediaTask, error: str):
        """Marca task como falhada"""
        task.error_message = error[:500]  # Limita tamanho
        task.error_details = {"full_error": error, "timestamp": datetime.utcnow().isoformat()}
        task.retry_count += 1
        
        # Verifica se deve tentar novamente
        if task.retry_count < task.max_retries:
            # Calcula delay exponencial
            retry_delay = min(300, 2 ** task.retry_count * 10)  # Max 5 minutos
            task.retry_after = datetime.utcnow() + timedelta(seconds=retry_delay)
            task.status = TaskStatus.RETRYING.value
            
            self.db.commit()
            
            # Log de retry
            await self._log_task_event(
                task.id, 
                "task_retry_scheduled", 
                {
                    "retry_count": task.retry_count,
                    "retry_after": task.retry_after.isoformat(),
                    "error": error
                }
            )
            
            # Reagenda na fila
            await asyncio.sleep(retry_delay)
            await self.queue_service.enqueue_task(
                task_id=task.id,
                task_type=task.task_type,
                priority=task.priority - 1  # Reduz prioridade
            )
            
            task.status = TaskStatus.QUEUED.value
            self.db.commit()
            
        else:
            # Falha definitiva
            task.status = TaskStatus.FAILED.value
            task.completed_at = datetime.utcnow()
            
            if task.started_at:
                task.actual_duration = (task.completed_at - task.started_at).total_seconds()
            
            self.db.commit()
            
            # Log de falha
            await self._log_task_event(
                task.id, 
                "task_failed", 
                {
                    "error": error,
                    "retry_count": task.retry_count
                }
            )
            
            # Notifica falha via webhook
            if task.webhook_url:
                await self.webhook_service.notify_task_completion(task)
            
            logger.error(f"Task {task.id} failed after {task.retry_count} retries: {error}")
    
    async def handle_provider_webhook(self, task_id: str, payload: Dict[str, Any]):
        """Processa webhook recebido de um provider"""
        task = self.db.query(MediaTask).filter(MediaTask.id == task_id).first()
        if not task:
            logger.warning(f"Received webhook for unknown task {task_id}")
            return
        
        # Log do webhook
        await self._log_task_event(
            task_id, 
            "webhook_received", 
            {"provider": task.provider_id, "status": payload.get("status")}
        )
        
        # Processa baseado no status
        if payload.get("status") == "completed":
            result = payload.get("result", {})
            await self._complete_task(task, result)
            
        elif payload.get("status") == "failed":
            error = payload.get("error", "Unknown error from provider")
            await self._fail_task(task, error)
            
        elif payload.get("status") == "processing":
            # Atualiza progresso
            progress = payload.get("progress", 0)
            message = payload.get("message")
            await self.update_task_progress(task_id, progress, message)
    
    async def _validate_task_input(self, task_request: TaskCreateRequest):
        """Valida entrada da task"""
        # Validações específicas por tipo
        if task_request.task_type == TaskType.IMAGE_GENERATION:
            if not task_request.input_data.get("prompt"):
                raise ValueError("Image generation requires a prompt")
                
        elif task_request.task_type == TaskType.VIDEO_GENERATION:
            if not task_request.input_data.get("prompt"):
                raise ValueError("Video generation requires a prompt")
                
        elif task_request.task_type == TaskType.AUDIO_TRANSCRIPTION:
            if not task_request.input_data.get("audio_url"):
                raise ValueError("Audio transcription requires an audio_url")
        
        # Validação de webhook
        if task_request.webhook_url and task_request.webhook_secret:
            if len(task_request.webhook_secret) < 16:
                raise ValueError("Webhook secret must be at least 16 characters")
    
    async def _log_task_event(self, task_id: str, event_type: str, event_data: Dict[str, Any]):
        """Registra evento no log da task"""
        try:
            log_entry = TaskLog(
                task_id=task_id,
                event_type=event_type,
                event_data=event_data,
                message=event_data.get("message", "")
            )
            self.db.add(log_entry)
            self.db.commit()
        except Exception as e:
            logger.error(f"Error logging task event: {e}")
    
    async def cleanup_old_tasks(self, days: int = 30):
        """Remove tasks antigas completadas/falhadas"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        old_tasks = self.db.query(MediaTask).filter(
            and_(
                MediaTask.completed_at < cutoff_date,
                MediaTask.status.in_([TaskStatus.COMPLETED.value, TaskStatus.FAILED.value, TaskStatus.CANCELLED.value])
            )
        ).all()
        
        for task in old_tasks:
            # Remove logs associados
            self.db.query(TaskLog).filter(TaskLog.task_id == task.id).delete()
            
            # Remove task
            self.db.delete(task)
        
        self.db.commit()
        
        logger.info(f"Cleaned up {len(old_tasks)} old tasks")

# Instância global (será inicializada no startup da aplicação)
universal_task_manager: Optional[UniversalTaskManager] = None

def get_universal_task_manager() -> UniversalTaskManager:
    """Obtém a instância global do task manager"""
    if universal_task_manager is None:
        raise RuntimeError("Universal task manager not initialized")
    return universal_task_manager

def set_universal_task_manager(manager: UniversalTaskManager):
    """Define a instância global do task manager"""
    global universal_task_manager
    universal_task_manager = manager 