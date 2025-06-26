from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import asyncio
from datetime import datetime

@dataclass
class ImageGenerationRequest:
    """Requisição de geração de imagem"""
    prompt: str
    negative_prompt: Optional[str] = None
    width: int = 1024
    height: int = 1024
    num_images: int = 1
    seed: Optional[int] = None
    guidance_scale: float = 7.5
    steps: int = 30
    style: Optional[str] = None  # realistic, anime, artistic, etc
    extra_params: Dict[str, Any] = None

@dataclass
class ImageGenerationResponse:
    """Resposta da geração de imagem"""
    images: List[bytes]  # Lista de imagens em bytes
    image_urls: List[str]  # URLs das imagens (quando disponível)
    cost: float  # Custo real da geração
    generation_time: float  # Tempo de geração em segundos
    provider: str  # Nome do provider usado
    metadata: Dict[str, Any] = None  # Metadados adicionais

class BaseImageProvider(ABC):
    """Interface base para provedores de geração de imagem"""
    
    def __init__(self, api_key: str, config: Dict[str, Any] = None):
        self.api_key = api_key
        self.config = config or {}
        self.rate_limiter = None
        self._credits_cache = None
        self._last_credit_check = None
    
    @abstractmethod
    async def generate(self, request: ImageGenerationRequest) -> ImageGenerationResponse:
        """Gera uma ou mais imagens baseado na requisição"""
        pass
    
    @abstractmethod
    async def batch_generate(self, requests: List[ImageGenerationRequest]) -> List[ImageGenerationResponse]:
        """Gera múltiplas imagens em batch"""
        pass
    
    @abstractmethod
    def estimate_cost(self, request: ImageGenerationRequest) -> float:
        """Estima o custo da geração antes de executar"""
        pass
    
    @abstractmethod
    async def get_remaining_credits(self) -> Optional[float]:
        """Obtém créditos/saldo restante do provider"""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Retorna o nome do provider"""
        pass
    
    @abstractmethod
    def get_supported_sizes(self) -> List[Tuple[int, int]]:
        """Retorna lista de tamanhos suportados (width, height)"""
        pass
    
    @abstractmethod
    def get_max_batch_size(self) -> int:
        """Retorna tamanho máximo de batch suportado"""
        pass
    
    async def validate_request(self, request: ImageGenerationRequest) -> bool:
        """Valida se a requisição é suportada pelo provider"""
        sizes = self.get_supported_sizes()
        if (request.width, request.height) not in sizes:
            raise ValueError(f"Size {request.width}x{request.height} not supported. Supported sizes: {sizes}")
        
        if request.num_images > self.get_max_batch_size():
            raise ValueError(f"Number of images ({request.num_images}) exceeds max batch size ({self.get_max_batch_size()})")
        
        return True
    
    async def check_credits(self, estimated_cost: float) -> bool:
        """Verifica se há créditos suficientes para a geração"""
        credits = await self.get_remaining_credits()
        if credits is not None and credits < estimated_cost:
            raise ValueError(f"Insufficient credits. Need {estimated_cost}, have {credits}")
        return True
    
    def _cache_credits(self, credits: float):
        """Cache de créditos para evitar muitas chamadas à API"""
        self._credits_cache = credits
        self._last_credit_check = datetime.utcnow()
    
    async def _get_cached_credits(self) -> Optional[float]:
        """Retorna créditos do cache se ainda válido (5 minutos)"""
        if self._credits_cache is not None and self._last_credit_check:
            delta = (datetime.utcnow() - self._last_credit_check).total_seconds()
            if delta < 300:  # 5 minutos
                return self._credits_cache
        return None

class ProviderError(Exception):
    """Erro específico de provider"""
    pass

class RateLimitError(ProviderError):
    """Erro de rate limit excedido"""
    pass

class InsufficientCreditsError(ProviderError):
    """Erro de créditos insuficientes"""
    pass
