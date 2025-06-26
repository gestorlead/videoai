"""
Provider Registry Service
Sistema central de registro e gerenciamento de provedores de mídia
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Type, Union
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta
import json

from ..models.base_task import TaskType, TaskStatus

logger = logging.getLogger(__name__)


class ProviderStatus(Enum):
    """Status dos provedores"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"


@dataclass
class ProviderCapability:
    """Capacidades de um provedor"""
    task_type: TaskType
    max_concurrent: int = 10
    rate_limit_per_minute: int = 60
    supports_batch: bool = False
    max_batch_size: int = 10
    estimated_processing_time: float = 30.0  # segundos
    cost_per_unit: float = 0.0  # custo em créditos
    quality_score: float = 0.8  # 0.0 - 1.0


@dataclass
class ProviderMetrics:
    """Métricas de um provedor"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    last_request_time: Optional[datetime] = None
    rate_limit_remaining: int = 0
    rate_limit_reset: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests
    
    @property
    def is_rate_limited(self) -> bool:
        if not self.rate_limit_reset:
            return False
        return datetime.utcnow() < self.rate_limit_reset


class BaseProvider(ABC):
    """Classe base para todos os provedores"""
    
    def __init__(self, name: str, api_key: str, config: Dict[str, Any] = None):
        self.name = name
        self.api_key = api_key
        self.config = config or {}
        self.status = ProviderStatus.ACTIVE
        self.capabilities: List[ProviderCapability] = []
        self.metrics = ProviderMetrics()
        self._setup_capabilities()
    
    @abstractmethod
    def _setup_capabilities(self):
        """Setup das capacidades do provedor"""
        pass
    
    @abstractmethod
    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Processa uma tarefa"""
        pass
    
    @abstractmethod
    async def validate_config(self) -> bool:
        """Valida a configuração do provedor"""
        pass
    
    @abstractmethod
    async def get_status(self) -> ProviderStatus:
        """Obtém o status atual do provedor"""
        pass
    
    def supports_task_type(self, task_type: TaskType) -> bool:
        """Verifica se suporta um tipo de tarefa"""
        return any(cap.task_type == task_type for cap in self.capabilities)
    
    def get_capability(self, task_type: TaskType) -> Optional[ProviderCapability]:
        """Obtém capacidade para um tipo de tarefa"""
        for cap in self.capabilities:
            if cap.task_type == task_type:
                return cap
        return None
    
    def update_metrics(self, success: bool, response_time: float, remaining_rate_limit: int = None):
        """Atualiza métricas do provedor"""
        self.metrics.total_requests += 1
        if success:
            self.metrics.successful_requests += 1
        else:
            self.metrics.failed_requests += 1
        
        # Atualiza tempo de resposta médio
        if self.metrics.total_requests == 1:
            self.metrics.avg_response_time = response_time
        else:
            self.metrics.avg_response_time = (
                (self.metrics.avg_response_time * (self.metrics.total_requests - 1) + response_time) 
                / self.metrics.total_requests
            )
        
        self.metrics.last_request_time = datetime.utcnow()
        
        if remaining_rate_limit is not None:
            self.metrics.rate_limit_remaining = remaining_rate_limit


class ImageGenerationProvider(BaseProvider):
    """Provedor de geração de imagens"""
    
    def _setup_capabilities(self):
        self.capabilities = [
            ProviderCapability(
                task_type=TaskType.IMAGE_GENERATION,
                max_concurrent=5,
                rate_limit_per_minute=30,
                supports_batch=True,
                max_batch_size=5,
                estimated_processing_time=15.0,
                cost_per_unit=0.1,
                quality_score=0.9
            )
        ]

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "demo", "message": "Demo image generation provider"}

    async def validate_config(self) -> bool:
        return bool(self.api_key and self.api_key != "demo_api_key")

    async def get_status(self) -> ProviderStatus:
        return ProviderStatus.ACTIVE if await self.validate_config() else ProviderStatus.INACTIVE

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Processa uma tarefa de geração de imagem"""
        # Implementação placeholder - será substituída por provedores reais
        return {"status": "demo", "message": "Demo image generation provider"}

    async def validate_config(self) -> bool:
        """Valida a configuração do provedor"""
        return bool(self.api_key and self.api_key != "demo_api_key")

    async def get_status(self) -> ProviderStatus:
        """Obtém o status atual do provedor"""
        return ProviderStatus.ACTIVE if await self.validate_config() else ProviderStatus.INACTIVE


class VideoGenerationProvider(BaseProvider):
    """Provedor de geração de vídeos"""
    
    def _setup_capabilities(self):
        self.capabilities = [
            ProviderCapability(
                task_type=TaskType.VIDEO_GENERATION,
                max_concurrent=2,
                rate_limit_per_minute=10,
                supports_batch=False,
                max_batch_size=1,
                estimated_processing_time=120.0,
                cost_per_unit=1.0,
                quality_score=0.8
            )
        ]

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Processa uma tarefa de geração de vídeo"""
        return {"status": "demo", "message": "Demo video generation provider"}

    async def validate_config(self) -> bool:
        """Valida a configuração do provedor"""
        return bool(self.api_key and self.api_key != "demo_api_key")

    async def get_status(self) -> ProviderStatus:
        """Obtém o status atual do provedor"""
        return ProviderStatus.ACTIVE if await self.validate_config() else ProviderStatus.INACTIVE


class AudioTranscriptionProvider(BaseProvider):
    """Provedor de transcrição de áudio"""
    
    def _setup_capabilities(self):
        self.capabilities = [
            ProviderCapability(
                task_type=TaskType.AUDIO_TRANSCRIPTION,
                max_concurrent=10,
                rate_limit_per_minute=100,
                supports_batch=True,
                max_batch_size=10,
                estimated_processing_time=30.0,
                cost_per_unit=0.05,
                quality_score=0.95
            )
        ]

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Processa uma tarefa de transcrição de áudio"""
        return {"status": "demo", "message": "Demo audio transcription provider"}

    async def validate_config(self) -> bool:
        """Valida a configuração do provedor"""
        return bool(self.api_key and self.api_key != "demo_api_key")

    async def get_status(self) -> ProviderStatus:
        """Obtém o status atual do provedor"""
        return ProviderStatus.ACTIVE if await self.validate_config() else ProviderStatus.INACTIVE


class SubtitleGenerationProvider(BaseProvider):
    """Provedor de geração de legendas"""
    
    def _setup_capabilities(self):
        self.capabilities = [
            ProviderCapability(
                task_type=TaskType.SUBTITLE_GENERATION,
                max_concurrent=15,
                rate_limit_per_minute=200,
                supports_batch=True,
                max_batch_size=20,
                estimated_processing_time=10.0,
                cost_per_unit=0.02,
                quality_score=0.9
            )
        ]

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Processa uma tarefa de geração de legendas"""
        return {"status": "demo", "message": "Demo subtitle generation provider"}

    async def validate_config(self) -> bool:
        """Valida a configuração do provedor"""
        return bool(self.api_key and self.api_key != "demo_api_key")

    async def get_status(self) -> ProviderStatus:
        """Obtém o status atual do provedor"""
        return ProviderStatus.ACTIVE if await self.validate_config() else ProviderStatus.INACTIVE


class ProviderRegistry:
    """Registry central de provedores"""
    
    def __init__(self):
        self.providers: Dict[str, BaseProvider] = {}
        self.task_type_providers: Dict[TaskType, List[str]] = {
            task_type: [] for task_type in TaskType
        }
        self._setup_default_providers()
    
    def _setup_default_providers(self):
        """Setup dos provedores padrão do sistema"""
        # Registra provedores fictícios para demonstração
        # Em produção, estes seriam provedores reais como OpenAI, PiAPI, etc.
        
        default_providers = [
            ("openai_dalle", ImageGenerationProvider, {"model": "dall-e-3"}),
            ("runwayml", VideoGenerationProvider, {"model": "gen-2"}),
            ("openai_whisper", AudioTranscriptionProvider, {"model": "whisper-1"}),
            ("assemblyai", AudioTranscriptionProvider, {"model": "best"}),
            ("openai_gpt", SubtitleGenerationProvider, {"model": "gpt-4"}),
        ]
        
        for name, provider_class, config in default_providers:
            provider = provider_class(name, "demo_api_key", config)
            self.register_provider(provider)
    
    def register_provider(self, provider: BaseProvider) -> bool:
        """Registra um novo provedor"""
        try:
            self.providers[provider.name] = provider
            
            # Atualiza mapeamento por tipo de tarefa
            for capability in provider.capabilities:
                if provider.name not in self.task_type_providers[capability.task_type]:
                    self.task_type_providers[capability.task_type].append(provider.name)
            
            logger.info(f"Provedor {provider.name} registrado com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao registrar provedor {provider.name}: {e}")
            return False
    
    def unregister_provider(self, provider_name: str) -> bool:
        """Remove um provedor do registry"""
        if provider_name not in self.providers:
            return False
        
        provider = self.providers[provider_name]
        
        # Remove dos mapeamentos por tipo
        for capability in provider.capabilities:
            if provider_name in self.task_type_providers[capability.task_type]:
                self.task_type_providers[capability.task_type].remove(provider_name)
        
        # Remove do registry principal
        del self.providers[provider_name]
        
        logger.info(f"Provedor {provider_name} removido do registry")
        return True
    
    def get_provider(self, provider_name: str) -> Optional[BaseProvider]:
        """Obtém um provedor específico"""
        return self.providers.get(provider_name)
    
    def get_providers_for_task_type(self, task_type: TaskType) -> List[BaseProvider]:
        """Obtém todos os provedores que suportam um tipo de tarefa"""
        provider_names = self.task_type_providers.get(task_type, [])
        return [self.providers[name] for name in provider_names if name in self.providers]
    
    def get_best_provider(self, task_type: TaskType, criteria: str = "quality") -> Optional[BaseProvider]:
        """
        Seleciona o melhor provedor para um tipo de tarefa
        Critérios: quality, speed, cost, reliability
        """
        providers = self.get_providers_for_task_type(task_type)
        if not providers:
            return None
        
        # Filtra provedores ativos e não rate-limited
        available_providers = [
            p for p in providers 
            if p.status == ProviderStatus.ACTIVE and not p.metrics.is_rate_limited
        ]
        
        if not available_providers:
            return None
        
        if criteria == "quality":
            return max(available_providers, 
                      key=lambda p: p.get_capability(task_type).quality_score)
        elif criteria == "speed":
            return min(available_providers, 
                      key=lambda p: p.get_capability(task_type).estimated_processing_time)
        elif criteria == "cost":
            return min(available_providers, 
                      key=lambda p: p.get_capability(task_type).cost_per_unit)
        elif criteria == "reliability":
            return max(available_providers, key=lambda p: p.metrics.success_rate)
        else:
            # Default: balanceamento entre qualidade e velocidade
            return min(available_providers, 
                      key=lambda p: (
                          p.get_capability(task_type).estimated_processing_time / 
                          p.get_capability(task_type).quality_score
                      ))
    
    def get_provider_load_balancing(self, task_type: TaskType) -> Optional[BaseProvider]:
        """Seleciona provedor baseado em load balancing"""
        providers = self.get_providers_for_task_type(task_type)
        if not providers:
            return None
        
        # Filtra provedores disponíveis
        available_providers = [
            p for p in providers 
            if p.status == ProviderStatus.ACTIVE and not p.metrics.is_rate_limited
        ]
        
        if not available_providers:
            return None
        
        # Seleciona o provedor com menor carga (baseado em requests recentes)
        return min(available_providers, key=lambda p: p.metrics.total_requests)
    
    async def health_check_all(self) -> Dict[str, ProviderStatus]:
        """Executa health check em todos os provedores"""
        results = {}
        
        for name, provider in self.providers.items():
            try:
                status = await provider.get_status()
                provider.status = status
                results[name] = status
            except Exception as e:
                logger.error(f"Health check falhou para {name}: {e}")
                provider.status = ProviderStatus.ERROR
                results[name] = ProviderStatus.ERROR
        
        return results
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Obtém estatísticas do registry"""
        total_providers = len(self.providers)
        active_providers = sum(1 for p in self.providers.values() 
                             if p.status == ProviderStatus.ACTIVE)
        
        stats_by_type = {}
        for task_type in TaskType:
            providers = self.get_providers_for_task_type(task_type)
            active_count = sum(1 for p in providers if p.status == ProviderStatus.ACTIVE)
            stats_by_type[task_type.value] = {
                "total": len(providers),
                "active": active_count
            }
        
        return {
            "total_providers": total_providers,
            "active_providers": active_providers,
            "provider_status": {name: p.status.value for name, p in self.providers.items()},
            "by_task_type": stats_by_type,
            "overall_metrics": {
                name: {
                    "success_rate": p.metrics.success_rate,
                    "avg_response_time": p.metrics.avg_response_time,
                    "total_requests": p.metrics.total_requests
                }
                for name, p in self.providers.items()
            }
        }


# Instância global do registry
provider_registry = ProviderRegistry() 