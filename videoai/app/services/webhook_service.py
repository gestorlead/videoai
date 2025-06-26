"""
Webhook Service
Sistema de notificações assíncronas via webhooks
"""

import asyncio
import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import aiohttp
from dataclasses import dataclass
from enum import Enum
import hashlib
import hmac
import time

from ..models.base_task import TaskStatus
from ..schemas.tasks import WebhookPayload

logger = logging.getLogger(__name__)


class WebhookEventType(Enum):
    """Tipos de eventos de webhook"""
    TASK_CREATED = "task.created"
    TASK_STARTED = "task.started"
    TASK_PROGRESS = "task.progress"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_CANCELLED = "task.cancelled"
    BATCH_COMPLETED = "batch.completed"
    BATCH_FAILED = "batch.failed"


@dataclass
class WebhookAttempt:
    """Tentativa de entrega de webhook"""
    attempt_number: int
    timestamp: datetime
    response_status: Optional[int] = None
    response_time: Optional[float] = None
    error_message: Optional[str] = None
    success: bool = False


@dataclass
class WebhookDelivery:
    """Registro de entrega de webhook"""
    webhook_id: str
    url: str
    event_type: WebhookEventType
    payload: Dict[str, Any]
    created_at: datetime
    attempts: List[WebhookAttempt]
    max_attempts: int = 5
    next_retry: Optional[datetime] = None
    
    @property
    def is_delivered(self) -> bool:
        return any(attempt.success for attempt in self.attempts)
    
    @property
    def is_expired(self) -> bool:
        return len(self.attempts) >= self.max_attempts
    
    @property
    def should_retry(self) -> bool:
        if self.is_delivered or self.is_expired:
            return False
        if not self.next_retry:
            return True
        return datetime.utcnow() >= self.next_retry


class WebhookService:
    """Serviço de gerenciamento de webhooks"""
    
    def __init__(self):
        self.deliveries: Dict[str, WebhookDelivery] = {}
        self.secret_key = "webhook_secret_key_change_in_production"
        self.timeout_seconds = 30
        self.retry_delays = [30, 300, 1800, 7200, 86400]  # 30s, 5m, 30m, 2h, 24h
        self._delivery_worker_running = False
    
    def start_delivery_worker(self):
        """Inicia worker de entrega de webhooks"""
        if not self._delivery_worker_running:
            self._delivery_worker_running = True
            asyncio.create_task(self._delivery_worker())
            logger.info("Webhook delivery worker iniciado")
    
    def stop_delivery_worker(self):
        """Para worker de entrega de webhooks"""
        self._delivery_worker_running = False
        logger.info("Webhook delivery worker parado")
    
    async def _delivery_worker(self):
        """Worker que processa entregas pendentes"""
        while self._delivery_worker_running:
            try:
                await self._process_pending_deliveries()
                await asyncio.sleep(30)  # Verifica a cada 30 segundos
            except Exception as e:
                logger.error(f"Erro no webhook delivery worker: {e}")
                await asyncio.sleep(60)
    
    async def _process_pending_deliveries(self):
        """Processa todas as entregas pendentes"""
        pending_deliveries = [
            delivery for delivery in self.deliveries.values()
            if delivery.should_retry
        ]
        
        if not pending_deliveries:
            return
        
        logger.info(f"Processando {len(pending_deliveries)} entregas pendentes")
        
        # Processa em lotes para não sobrecarregar
        batch_size = 10
        for i in range(0, len(pending_deliveries), batch_size):
            batch = pending_deliveries[i:i + batch_size]
            await asyncio.gather(
                *[self._attempt_delivery(delivery) for delivery in batch],
                return_exceptions=True
            )
    
    async def _attempt_delivery(self, delivery: WebhookDelivery):
        """Tenta entregar um webhook"""
        attempt_number = len(delivery.attempts) + 1
        attempt = WebhookAttempt(
            attempt_number=attempt_number,
            timestamp=datetime.utcnow()
        )
        
        try:
            start_time = time.time()
            
            # Prepara headers
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "VideoAI-Webhook/1.0",
                "X-Webhook-Event": delivery.event_type.value,
                "X-Webhook-Delivery": delivery.webhook_id,
                "X-Webhook-Timestamp": str(int(delivery.created_at.timestamp()))
            }
            
            # Adiciona assinatura HMAC se configurada
            if self.secret_key:
                payload_str = json.dumps(delivery.payload, sort_keys=True)
                signature = self._generate_signature(payload_str)
                headers["X-Webhook-Signature"] = f"sha256={signature}"
            
            # Faz a requisição
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout_seconds)) as session:
                async with session.post(
                    delivery.url,
                    json=delivery.payload,
                    headers=headers
                ) as response:
                    attempt.response_status = response.status
                    attempt.response_time = time.time() - start_time
                    
                    # Considera sucesso códigos 2xx
                    if 200 <= response.status < 300:
                        attempt.success = True
                        logger.info(f"Webhook entregue com sucesso: {delivery.webhook_id} -> {delivery.url}")
                    else:
                        response_text = await response.text()
                        attempt.error_message = f"HTTP {response.status}: {response_text[:200]}"
                        logger.warning(f"Webhook falhou: {delivery.webhook_id} -> {delivery.url} ({response.status})")
        
        except asyncio.TimeoutError:
            attempt.response_time = self.timeout_seconds
            attempt.error_message = "Timeout na requisição"
            logger.warning(f"Webhook timeout: {delivery.webhook_id} -> {delivery.url}")
        
        except Exception as e:
            attempt.response_time = time.time() - start_time if 'start_time' in locals() else 0
            attempt.error_message = str(e)
            logger.error(f"Erro ao entregar webhook: {delivery.webhook_id} -> {delivery.url}: {e}")
        
        # Adiciona tentativa ao registro
        delivery.attempts.append(attempt)
        
        # Agenda próxima tentativa se necessário
        if not attempt.success and not delivery.is_expired:
            retry_index = min(len(delivery.attempts) - 1, len(self.retry_delays) - 1)
            delay_seconds = self.retry_delays[retry_index]
            delivery.next_retry = datetime.utcnow() + timedelta(seconds=delay_seconds)
            logger.info(f"Webhook agendado para retry em {delay_seconds}s: {delivery.webhook_id}")
    
    def _generate_signature(self, payload: str) -> str:
        """Gera assinatura HMAC SHA256 do payload"""
        return hmac.new(
            self.secret_key.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    async def send_webhook(
        self,
        url: str,
        event_type: WebhookEventType,
        task_id: str,
        task_data: Dict[str, Any],
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Envia webhook assíncrono
        Retorna ID do webhook para tracking
        """
        webhook_id = f"wh_{int(time.time())}_{hash(url + task_id) % 1000000}"
        
        # Cria payload padronizado
        payload = WebhookPayload(
            event_type=event_type.value,
            task_id=task_id,
            timestamp=datetime.utcnow(),
            data=task_data,
            user_id=user_id,
            metadata=metadata or {}
        ).dict()
        
        # Cria registro de entrega
        delivery = WebhookDelivery(
            webhook_id=webhook_id,
            url=url,
            event_type=event_type,
            payload=payload,
            created_at=datetime.utcnow(),
            attempts=[]
        )
        
        self.deliveries[webhook_id] = delivery
        
        # Inicia worker se não estiver rodando
        if not self._delivery_worker_running:
            self.start_delivery_worker()
        
        logger.info(f"Webhook agendado: {webhook_id} -> {url} ({event_type.value})")
        return webhook_id
    
    def get_webhook_status(self, webhook_id: str) -> Optional[Dict[str, Any]]:
        """Obtém status de entrega de um webhook"""
        delivery = self.deliveries.get(webhook_id)
        if not delivery:
            return None
        
        return {
            "webhook_id": webhook_id,
            "url": delivery.url,
            "event_type": delivery.event_type.value,
            "created_at": delivery.created_at.isoformat(),
            "is_delivered": delivery.is_delivered,
            "is_expired": delivery.is_expired,
            "attempts": len(delivery.attempts),
            "max_attempts": delivery.max_attempts,
            "next_retry": delivery.next_retry.isoformat() if delivery.next_retry else None,
            "last_attempt": {
                "timestamp": delivery.attempts[-1].timestamp.isoformat(),
                "success": delivery.attempts[-1].success,
                "response_status": delivery.attempts[-1].response_status,
                "response_time": delivery.attempts[-1].response_time,
                "error_message": delivery.attempts[-1].error_message
            } if delivery.attempts else None
        }
    
    def get_webhooks_stats(self) -> Dict[str, Any]:
        """Obtém estatísticas dos webhooks"""
        total_webhooks = len(self.deliveries)
        delivered = sum(1 for d in self.deliveries.values() if d.is_delivered)
        pending = sum(1 for d in self.deliveries.values() if d.should_retry)
        expired = sum(1 for d in self.deliveries.values() if d.is_expired)
        
        # Estatísticas por tipo de evento
        event_stats = {}
        for delivery in self.deliveries.values():
            event_type = delivery.event_type.value
            if event_type not in event_stats:
                event_stats[event_type] = {"total": 0, "delivered": 0, "failed": 0}
            
            event_stats[event_type]["total"] += 1
            if delivery.is_delivered:
                event_stats[event_type]["delivered"] += 1
            elif delivery.is_expired:
                event_stats[event_type]["failed"] += 1
        
        # Tempos de resposta médios
        successful_attempts = [
            attempt for delivery in self.deliveries.values()
            for attempt in delivery.attempts if attempt.success
        ]
        avg_response_time = (
            sum(a.response_time for a in successful_attempts) / len(successful_attempts)
            if successful_attempts else 0
        )
        
        return {
            "total_webhooks": total_webhooks,
            "delivered": delivered,
            "pending": pending,
            "expired": expired,
            "success_rate": delivered / total_webhooks if total_webhooks > 0 else 0,
            "avg_response_time": avg_response_time,
            "by_event_type": event_stats,
            "worker_running": self._delivery_worker_running
        }
    
    def cleanup_old_deliveries(self, days: int = 7):
        """Remove registros antigos de entrega"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        old_webhooks = [
            wh_id for wh_id, delivery in self.deliveries.items()
            if delivery.created_at < cutoff_date and (delivery.is_delivered or delivery.is_expired)
        ]
        
        for wh_id in old_webhooks:
            del self.deliveries[wh_id]
        
        if old_webhooks:
            logger.info(f"Removidos {len(old_webhooks)} registros antigos de webhook")
        
        return len(old_webhooks)


# Instância global do serviço de webhooks
webhook_service = WebhookService() 