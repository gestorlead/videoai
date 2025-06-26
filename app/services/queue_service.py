import asyncio
import json
import logging
from collections import defaultdict, deque
from typing import Dict, List, Optional, Tuple
from datetime import datetime

try:
    import aioredis
except ImportError:  # Segurança caso aioredis não esteja instalado
    aioredis = None

logger = logging.getLogger(__name__)

class QueueService:
    """Serviço de filas com suporte opcional a Redis.

    Estrutura de chave no Redis:
    - Lista ordenada por prioridade:  media_queue:{task_type}:{priority}
    - Hash para metadados        :  media_task_meta:{task_id} -> {"priority": int, "created_at": iso}
    """
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url
        self.redis = None  # type: ignore
        self._local_queues: Dict[str, Dict[int, deque]] = defaultdict(lambda: defaultdict(deque))
        self._lock = asyncio.Lock()
        self.max_priority = 10
        # Start Redis connection lazily

    async def _init_redis(self):
        if self.redis_url and aioredis and not self.redis:
            try:
                self.redis = await aioredis.from_url(self.redis_url, decode_responses=True)
                logger.info("Connected to Redis queue")
            except Exception as e:
                logger.warning(f"Could not connect to Redis ({self.redis_url}): {e}")
                self.redis = None

    # ---------------------------------------------------------------------
    # API pública
    # ---------------------------------------------------------------------
    async def enqueue_task(self, task_id: str, task_type: str, priority: int = 5):
        """Enfileira task com prioridade (1-10)."""
        priority = max(1, min(self.max_priority, priority))
        await self._init_redis()

        if self.redis:
            await self._enqueue_redis(task_id, task_type, priority)
        else:
            await self._enqueue_memory(task_id, task_type, priority)

    async def dequeue_task(self, task_type: str, timeout: int = 1) -> Optional[str]:
        """Remove uma task da fila respeitando prioridades."""
        await self._init_redis()

        if self.redis:
            return await self._dequeue_redis(task_type)
        else:
            return await self._dequeue_memory(task_type)

    async def dequeue_batch(self, task_type: str, batch_size: int = 1) -> List[str]:
        tasks = []
        for _ in range(batch_size):
            task_id = await self.dequeue_task(task_type)
            if not task_id:
                break
            tasks.append(task_id)
        return tasks

    async def remove_from_queue(self, task_id: str):
        """Remove task de qualquer fila se ainda estiver enfileirada."""
        await self._init_redis()

        if self.redis:
            await self._remove_redis(task_id)
        else:
            await self._remove_memory(task_id)

    async def get_position(self, task_id: str) -> Optional[int]:
        """Retorna posição aproximada na fila (0 = próximo)."""
        await self._init_redis()
        if self.redis:
            return await self._position_redis(task_id)
        return await self._position_memory(task_id)

    # ------------------------------------------------------------------
    # Implementação em memória
    # ------------------------------------------------------------------
    async def _enqueue_memory(self, task_id: str, task_type: str, priority: int):
        async with self._lock:
            self._local_queues[task_type][priority].append(task_id)

    async def _dequeue_memory(self, task_type: str) -> Optional[str]:
        async with self._lock:
            priority_levels = sorted(self._local_queues[task_type].keys(), reverse=True)
            for p in priority_levels:
                if self._local_queues[task_type][p]:
                    return self._local_queues[task_type][p].popleft()
        return None

    async def _remove_memory(self, task_id: str):
        async with self._lock:
            for task_type, pq in self._local_queues.items():
                for p, dq in pq.items():
                    if task_id in dq:
                        dq.remove(task_id)
                        return

    async def _position_memory(self, task_id: str) -> Optional[int]:
        async with self._lock:
            pos = 0
            for task_type, pq in self._local_queues.items():
                for p in sorted(pq.keys(), reverse=True):
                    for tid in pq[p]:
                        if tid == task_id:
                            return pos
                        pos += 1
        return None

    # ------------------------------------------------------------------
    # Implementação Redis
    # ------------------------------------------------------------------
    async def _enqueue_redis(self, task_id: str, task_type: str, priority: int):
        ts = datetime.utcnow().isoformat()
        pipe = self.redis.pipeline()
        list_key = f"media_queue:{task_type}:{priority}"
        pipe.rpush(list_key, task_id)
        pipe.hset(f"media_task_meta:{task_id}", mapping={"priority": priority, "created_at": ts, "task_type": task_type})
        await pipe.execute()

    async def _dequeue_redis(self, task_type: str) -> Optional[str]:
        # Percorre prioridades da maior para menor
        for priority in range(self.max_priority, 0, -1):
            list_key = f"media_queue:{task_type}:{priority}"
            task_id = await self.redis.lpop(list_key)
            if task_id:
                await self.redis.delete(f"media_task_meta:{task_id}")
                return task_id
        return None

    async def _remove_redis(self, task_id: str):
        meta = await self.redis.hgetall(f"media_task_meta:{task_id}")
        if not meta:
            return
        priority = meta.get("priority")
        task_type = meta.get("task_type")
        list_key = f"media_queue:{task_type}:{priority}"
        await self.redis.lrem(list_key, 0, task_id)
        await self.redis.delete(f"media_task_meta:{task_id}")

    async def _position_redis(self, task_id: str) -> Optional[int]:
        meta = await self.redis.hgetall(f"media_task_meta:{task_id}")
        if not meta:
            return None
        priority = int(meta.get("priority", 5))
        task_type = meta.get("task_type")
        list_key = f"media_queue:{task_type}:{priority}"
        queue = await self.redis.lrange(list_key, 0, -1)
        try:
            return queue.index(task_id)
        except ValueError:
            return None 