import asyncio
import hashlib
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import logging
import aioredis
from pathlib import Path

from .base_provider import ImageGenerationRequest, ImageGenerationResponse

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """Entrada no cache"""
    key: str
    response: ImageGenerationResponse
    timestamp: datetime
    provider_id: str
    access_count: int = 0
    last_accessed: datetime = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário serializável"""
        return {
            'key': self.key,
            'response': asdict(self.response),
            'timestamp': self.timestamp.isoformat(),
            'provider_id': self.provider_id,
            'access_count': self.access_count,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CacheEntry':
        """Cria instância a partir de dicionário"""
        response_data = data['response']
        response = ImageGenerationResponse(**response_data)
        
        return cls(
            key=data['key'],
            response=response,
            timestamp=datetime.fromisoformat(data['timestamp']),
            provider_id=data['provider_id'],
            access_count=data.get('access_count', 0),
            last_accessed=datetime.fromisoformat(data['last_accessed']) if data.get('last_accessed') else None
        )

class BatchCache:
    """Sistema de cache para otimizar batch processing"""
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        local_cache_dir: Optional[str] = None,
        max_memory_items: int = 1000,
        ttl_hours: int = 24,
        compression_enabled: bool = True
    ):
        # Configurações
        self.redis_url = redis_url
        self.local_cache_dir = Path(local_cache_dir) if local_cache_dir else Path("cache/images")
        self.max_memory_items = max_memory_items
        self.ttl = timedelta(hours=ttl_hours)
        self.compression_enabled = compression_enabled
        
        # Cache em memória
        self.memory_cache: Dict[str, CacheEntry] = {}
        
        # Cliente Redis
        self.redis_client: Optional[aioredis.Redis] = None
        
        # Métricas
        self.metrics = {
            'hits': 0,
            'misses': 0,
            'writes': 0,
            'evictions': 0,
            'errors': 0
        }
        
        # Lock para operações
        self.lock = asyncio.Lock()
        
        # Task de limpeza
        self.cleanup_task: Optional[asyncio.Task] = None
        self.running = False
    
    async def start(self):
        """Inicializa o sistema de cache"""
        if self.running:
            return
        
        # Conecta ao Redis se configurado
        if self.redis_url:
            try:
                self.redis_client = await aioredis.from_url(self.redis_url)
                await self.redis_client.ping()
                logger.info("Connected to Redis cache")
            except Exception as e:
                logger.warning(f"Could not connect to Redis: {e}")
                self.redis_client = None
        
        # Cria diretório local
        self.local_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Carrega cache local existente
        await self._load_local_cache()
        
        # Inicia task de limpeza
        self.running = True
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        logger.info("Batch cache system started")
    
    async def stop(self):
        """Para o sistema de cache"""
        self.running = False
        
        # Para task de limpeza
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Salva cache local
        await self._save_local_cache()
        
        # Fecha conexão Redis
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("Batch cache system stopped")
    
    def _generate_cache_key(self, request: ImageGenerationRequest, provider_id: str) -> str:
        """Gera chave única para a request"""
        # Serializa request de forma determinística
        request_dict = asdict(request)
        # Remove campos que não afetam o resultado
        request_dict.pop('webhook_url', None)
        request_dict.pop('request_id', None)
        
        # Inclui provider no hash
        request_dict['provider_id'] = provider_id
        
        # Gera hash
        request_str = json.dumps(request_dict, sort_keys=True)
        return hashlib.sha256(request_str.encode()).hexdigest()[:16]
    
    async def get(self, request: ImageGenerationRequest, provider_id: str) -> Optional[ImageGenerationResponse]:
        """Busca no cache"""
        cache_key = self._generate_cache_key(request, provider_id)
        
        try:
            # Busca em memória primeiro
            if cache_key in self.memory_cache:
                entry = self.memory_cache[cache_key]
                
                # Verifica se não expirou
                if datetime.utcnow() - entry.timestamp < self.ttl:
                    entry.access_count += 1
                    entry.last_accessed = datetime.utcnow()
                    self.metrics['hits'] += 1
                    logger.debug(f"Cache hit (memory): {cache_key}")
                    return entry.response
                else:
                    # Remove entrada expirada
                    del self.memory_cache[cache_key]
            
            # Busca no Redis
            if self.redis_client:
                redis_key = f"img_cache:{cache_key}"
                cached_data = await self.redis_client.get(redis_key)
                
                if cached_data:
                    try:
                        entry_dict = json.loads(cached_data)
                        entry = CacheEntry.from_dict(entry_dict)
                        
                        # Verifica se não expirou
                        if datetime.utcnow() - entry.timestamp < self.ttl:
                            # Adiciona de volta à memória
                            entry.access_count += 1
                            entry.last_accessed = datetime.utcnow()
                            self.memory_cache[cache_key] = entry
                            
                            self.metrics['hits'] += 1
                            logger.debug(f"Cache hit (Redis): {cache_key}")
                            return entry.response
                        else:
                            # Remove entrada expirada
                            await self.redis_client.delete(redis_key)
                    except Exception as e:
                        logger.error(f"Error deserializing cache entry: {e}")
            
            # Busca no cache local
            local_file = self.local_cache_dir / f"{cache_key}.json"
            if local_file.exists():
                try:
                    with open(local_file, 'r') as f:
                        entry_dict = json.load(f)
                    
                    entry = CacheEntry.from_dict(entry_dict)
                    
                    # Verifica se não expirou
                    if datetime.utcnow() - entry.timestamp < self.ttl:
                        # Adiciona de volta à memória
                        entry.access_count += 1
                        entry.last_accessed = datetime.utcnow()
                        self.memory_cache[cache_key] = entry
                        
                        self.metrics['hits'] += 1
                        logger.debug(f"Cache hit (local): {cache_key}")
                        return entry.response
                    else:
                        # Remove arquivo expirado
                        local_file.unlink()
                        
                except Exception as e:
                    logger.error(f"Error reading local cache: {e}")
            
            self.metrics['misses'] += 1
            return None
            
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            self.metrics['errors'] += 1
            return None
    
    async def set(self, request: ImageGenerationRequest, provider_id: str, response: ImageGenerationResponse):
        """Armazena no cache"""
        cache_key = self._generate_cache_key(request, provider_id)
        
        try:
            async with self.lock:
                # Cria entrada
                entry = CacheEntry(
                    key=cache_key,
                    response=response,
                    timestamp=datetime.utcnow(),
                    provider_id=provider_id,
                    last_accessed=datetime.utcnow()
                )
                
                # Adiciona à memória
                self.memory_cache[cache_key] = entry
                
                # Verifica limite de memória
                await self._evict_if_needed()
                
                # Salva no Redis
                if self.redis_client:
                    try:
                        redis_key = f"img_cache:{cache_key}"
                        entry_json = json.dumps(entry.to_dict())
                        await self.redis_client.setex(
                            redis_key,
                            int(self.ttl.total_seconds()),
                            entry_json
                        )
                    except Exception as e:
                        logger.error(f"Redis save error: {e}")
                
                # Salva localmente (async)
                asyncio.create_task(self._save_entry_local(entry))
                
                self.metrics['writes'] += 1
                logger.debug(f"Cache set: {cache_key}")
                
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            self.metrics['errors'] += 1
    
    async def _evict_if_needed(self):
        """Remove entradas antigas se necessário"""
        if len(self.memory_cache) <= self.max_memory_items:
            return
        
        # Remove as menos acessadas
        entries_by_access = sorted(
            self.memory_cache.items(),
            key=lambda x: (x[1].access_count, x[1].last_accessed or x[1].timestamp)
        )
        
        to_remove = len(self.memory_cache) - self.max_memory_items + 100  # Remove 100 extras
        
        for i in range(to_remove):
            if i < len(entries_by_access):
                key = entries_by_access[i][0]
                del self.memory_cache[key]
                self.metrics['evictions'] += 1
    
    async def _save_entry_local(self, entry: CacheEntry):
        """Salva entrada no cache local"""
        try:
            local_file = self.local_cache_dir / f"{entry.key}.json"
            with open(local_file, 'w') as f:
                json.dump(entry.to_dict(), f)
        except Exception as e:
            logger.error(f"Local save error: {e}")
    
    async def _load_local_cache(self):
        """Carrega cache local existente"""
        try:
            if not self.local_cache_dir.exists():
                return
            
            loaded = 0
            for cache_file in self.local_cache_dir.glob("*.json"):
                try:
                    with open(cache_file, 'r') as f:
                        entry_dict = json.load(f)
                    
                    entry = CacheEntry.from_dict(entry_dict)
                    
                    # Verifica se não expirou
                    if datetime.utcnow() - entry.timestamp < self.ttl:
                        self.memory_cache[entry.key] = entry
                        loaded += 1
                    else:
                        # Remove arquivo expirado
                        cache_file.unlink()
                        
                except Exception as e:
                    logger.error(f"Error loading cache file {cache_file}: {e}")
                    # Remove arquivo corrompido
                    try:
                        cache_file.unlink()
                    except:
                        pass
            
            logger.info(f"Loaded {loaded} entries from local cache")
            
        except Exception as e:
            logger.error(f"Error loading local cache: {e}")
    
    async def _save_local_cache(self):
        """Salva cache atual no disco"""
        try:
            # Salva apenas as entradas mais recentes
            recent_entries = {
                k: v for k, v in self.memory_cache.items()
                if datetime.utcnow() - v.timestamp < self.ttl
            }
            
            for entry in recent_entries.values():
                await self._save_entry_local(entry)
            
            logger.info(f"Saved {len(recent_entries)} entries to local cache")
            
        except Exception as e:
            logger.error(f"Error saving local cache: {e}")
    
    async def _cleanup_loop(self):
        """Loop de limpeza do cache"""
        while self.running:
            try:
                await asyncio.sleep(3600)  # Executa a cada hora
                
                # Remove entradas expiradas da memória
                expired_keys = []
                for key, entry in self.memory_cache.items():
                    if datetime.utcnow() - entry.timestamp >= self.ttl:
                        expired_keys.append(key)
                
                for key in expired_keys:
                    del self.memory_cache[key]
                
                # Limpa cache local
                if self.local_cache_dir.exists():
                    for cache_file in self.local_cache_dir.glob("*.json"):
                        try:
                            # Verifica modificação do arquivo
                            mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
                            if datetime.utcnow() - mtime >= self.ttl:
                                cache_file.unlink()
                        except Exception:
                            pass
                
                if expired_keys:
                    logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
    
    async def invalidate(self, request: ImageGenerationRequest, provider_id: str):
        """Invalida entrada específica do cache"""
        cache_key = self._generate_cache_key(request, provider_id)
        
        # Remove da memória
        self.memory_cache.pop(cache_key, None)
        
        # Remove do Redis
        if self.redis_client:
            try:
                redis_key = f"img_cache:{cache_key}"
                await self.redis_client.delete(redis_key)
            except Exception as e:
                logger.error(f"Redis invalidate error: {e}")
        
        # Remove local
        local_file = self.local_cache_dir / f"{cache_key}.json"
        if local_file.exists():
            try:
                local_file.unlink()
            except Exception as e:
                logger.error(f"Local invalidate error: {e}")
    
    async def clear(self):
        """Limpa todo o cache"""
        # Limpa memória
        self.memory_cache.clear()
        
        # Limpa Redis
        if self.redis_client:
            try:
                async for key in self.redis_client.scan_iter(match="img_cache:*"):
                    await self.redis_client.delete(key)
            except Exception as e:
                logger.error(f"Redis clear error: {e}")
        
        # Limpa local
        if self.local_cache_dir.exists():
            for cache_file in self.local_cache_dir.glob("*.json"):
                try:
                    cache_file.unlink()
                except Exception:
                    pass
        
        # Reset métricas
        for key in self.metrics:
            self.metrics[key] = 0
        
        logger.info("Cache cleared")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Retorna métricas do cache"""
        total_requests = self.metrics['hits'] + self.metrics['misses']
        hit_rate = self.metrics['hits'] / total_requests if total_requests > 0 else 0
        
        return {
            **self.metrics,
            'hit_rate': hit_rate,
            'memory_entries': len(self.memory_cache),
            'memory_usage_mb': sum(len(str(entry.response.images)) for entry in self.memory_cache.values()) / (1024 * 1024)
        }
    
    async def get_cache_info(self) -> Dict[str, Any]:
        """Retorna informações detalhadas do cache"""
        # Informações por provider
        provider_stats = {}
        for entry in self.memory_cache.values():
            provider_id = entry.provider_id
            if provider_id not in provider_stats:
                provider_stats[provider_id] = {'count': 0, 'total_cost': 0.0}
            
            provider_stats[provider_id]['count'] += 1
            provider_stats[provider_id]['total_cost'] += entry.response.cost
        
        # Informações de storage
        local_files = len(list(self.local_cache_dir.glob("*.json"))) if self.local_cache_dir.exists() else 0
        
        redis_keys = 0
        if self.redis_client:
            try:
                redis_keys = len([key async for key in self.redis_client.scan_iter(match="img_cache:*")])
            except Exception:
                pass
        
        return {
            'metrics': self.get_metrics(),
            'provider_stats': provider_stats,
            'storage': {
                'memory_entries': len(self.memory_cache),
                'local_files': local_files,
                'redis_keys': redis_keys
            },
            'config': {
                'max_memory_items': self.max_memory_items,
                'ttl_hours': self.ttl.total_seconds() / 3600,
                'redis_enabled': self.redis_client is not None,
                'local_cache_dir': str(self.local_cache_dir)
            }
        } 