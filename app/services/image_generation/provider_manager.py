import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json
from cryptography.fernet import Fernet
import asyncio
from sqlalchemy.orm import Session

from .base_provider import BaseImageProvider, ImageGenerationRequest, ImageGenerationResponse
from .openai_provider import OpenAIProvider
from .piapi_provider import PiAPIProvider
from .stablediffusion_provider import StableDiffusionProvider
from ...models.image_provider import ImageProviderConfig, ProviderType
from ...core.database import get_db

@dataclass
class ProviderRegistry:
    """Registro de providers disponíveis"""
    provider_class: type
    name: str
    description: str
    default_config: Dict[str, Any]
    supports_batch: bool = True
    supports_webhook: bool = False

class ImageProviderManager:
    """Gerenciador central de providers de geração de imagem"""
    
    # Registro de providers disponíveis
    PROVIDERS = {
        ProviderType.OPENAI: ProviderRegistry(
            provider_class=OpenAIProvider,
            name="OpenAI DALL-E",
            description="High quality image generation with DALL-E 2/3 and GPT-4 Vision",
            default_config={
                "model": "dall-e-2",
                "quality": "standard",
                "vision_model": "gpt-4-vision-preview"
            },
            supports_batch=False,
            supports_webhook=False
        ),
        ProviderType.PIAPI: ProviderRegistry(
            provider_class=PiAPIProvider,
            name="PiAPI Platform",
            description="Unified AI platform with Midjourney, Flux, and more",
            default_config={
                "default_service": "midjourney",
                "use_websocket": False
            },
            supports_batch=True,
            supports_webhook=True
        ),
        ProviderType.STABLE_DIFFUSION: ProviderRegistry(
            provider_class=StableDiffusionProvider,
            name="Stable-Diffusion.com",
            description="Cost-effective Stable Diffusion API with many models",
            default_config={
                "model_type": "sdxl",
                "model_id": "stable-diffusion-xl-v1-0"
            },
            supports_batch=True,
            supports_webhook=True
        )
    }
    
    def __init__(self, db: Session):
        self.db = db
        self._providers_cache: Dict[str, BaseImageProvider] = {}
        self._encryption_key = self._get_or_create_encryption_key()
        self._cipher = Fernet(self._encryption_key)
    
    def _get_or_create_encryption_key(self) -> bytes:
        """Obtém ou cria chave de criptografia para API keys"""
        key_file = "videoai/.encryption_key"
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            os.makedirs(os.path.dirname(key_file), exist_ok=True)
            with open(key_file, 'wb') as f:
                f.write(key)
            # Protege o arquivo
            os.chmod(key_file, 0o600)
            return key
    
    def encrypt_api_key(self, api_key: str) -> str:
        """Criptografa uma API key para armazenamento"""
        return self._cipher.encrypt(api_key.encode()).decode()
    
    def decrypt_api_key(self, encrypted_key: str) -> str:
        """Descriptografa uma API key"""
        return self._cipher.decrypt(encrypted_key.encode()).decode()
    
    async def create_provider_config(
        self,
        provider_type: ProviderType,
        name: str,
        api_key: str,
        config: Dict[str, Any] = None,
        is_default: bool = False
    ) -> ImageProviderConfig:
        """Cria uma nova configuração de provider"""
        # Se for marcado como default, remove flag de outros
        if is_default:
            self.db.query(ImageProviderConfig).update({ImageProviderConfig.is_default: False})
        
        # Criptografa API key
        encrypted_key = self.encrypt_api_key(api_key)
        
        # Mescla com configuração padrão
        registry = self.PROVIDERS.get(provider_type)
        if not registry:
            raise ValueError(f"Provider type {provider_type} not supported")
        
        final_config = registry.default_config.copy()
        if config:
            final_config.update(config)
        
        # Cria configuração
        provider_config = ImageProviderConfig(
            id=f"{provider_type.value}_{name.lower().replace(' ', '_')}",
            provider_type=provider_type,
            name=name,
            api_key=encrypted_key,
            is_active=True,
            is_default=is_default,
            settings=final_config,
            rate_limit_rpm=config.get('rate_limit_rpm', 60),
            max_batch_size=config.get('max_batch_size', 1)
        )
        
        # Define custos estimados
        if provider_type == ProviderType.OPENAI:
            provider_config.cost_per_image = 0.020  # DALL-E 2 1024x1024
        elif provider_type == ProviderType.PIAPI:
            provider_config.cost_per_image = 0.009  # Midjourney
        elif provider_type == ProviderType.STABLE_DIFFUSION:
            provider_config.cost_per_image = 0.010  # SDXL
        
        self.db.add(provider_config)
        self.db.commit()
        
        return provider_config
    
    async def get_provider(self, provider_id: str = None) -> BaseImageProvider:
        """Obtém uma instância de provider configurada"""
        # Se não especificado, usa o padrão
        if not provider_id:
            default_config = self.db.query(ImageProviderConfig).filter_by(
                is_default=True, is_active=True
            ).first()
            
            if not default_config:
                raise ValueError("No default provider configured")
            
            provider_id = default_config.id
        
        # Verifica cache
        if provider_id in self._providers_cache:
            return self._providers_cache[provider_id]
        
        # Busca configuração
        config = self.db.query(ImageProviderConfig).filter_by(
            id=provider_id, is_active=True
        ).first()
        
        if not config:
            raise ValueError(f"Provider {provider_id} not found or inactive")
        
        # Cria instância do provider
        registry = self.PROVIDERS.get(config.provider_type)
        if not registry:
            raise ValueError(f"Provider type {config.provider_type} not supported")
        
        # Descriptografa API key
        api_key = self.decrypt_api_key(config.api_key)
        
        # Cria provider
        provider = registry.provider_class(
            api_key=api_key,
            config=config.settings or {}
        )
        
        # Cache
        self._providers_cache[provider_id] = provider
        
        return provider
    
    async def generate_image(
        self,
        request: ImageGenerationRequest,
        provider_id: Optional[str] = None,
        fallback_providers: List[str] = None
    ) -> ImageGenerationResponse:
        """Gera imagem usando provider especificado ou padrão com fallback"""
        providers_to_try = [provider_id] if provider_id else []
        
        # Adiciona fallbacks
        if fallback_providers:
            providers_to_try.extend(fallback_providers)
        
        # Se nenhum especificado, tenta todos ativos em ordem de prioridade
        if not providers_to_try:
            active_configs = self.db.query(ImageProviderConfig).filter_by(
                is_active=True
            ).order_by(ImageProviderConfig.is_default.desc()).all()
            
            providers_to_try = [cfg.id for cfg in active_configs]
        
        last_error = None
        
        for pid in providers_to_try:
            try:
                provider = await self.get_provider(pid)
                
                # Tenta gerar
                response = await provider.generate(request)
                
                # Atualiza estatísticas de sucesso
                await self._update_provider_stats(pid, success=True, cost=response.cost)
                
                return response
                
            except Exception as e:
                last_error = e
                # Log do erro
                print(f"Provider {pid} failed: {str(e)}")
                
                # Atualiza estatísticas de falha
                await self._update_provider_stats(pid, success=False)
                
                # Continua para próximo provider
                continue
        
        # Se todos falharam, lança último erro
        if last_error:
            raise last_error
        else:
            raise ValueError("No providers available")
    
    async def batch_generate_images(
        self,
        requests: List[ImageGenerationRequest],
        provider_id: Optional[str] = None
    ) -> List[ImageGenerationResponse]:
        """Gera múltiplas imagens em batch"""
        provider = await self.get_provider(provider_id)
        
        # Verifica se provider suporta batch
        registry = self.PROVIDERS.get(provider.__class__.__name__)
        if not registry or not registry.supports_batch:
            # Executa em paralelo se não suporta batch nativo
            tasks = [provider.generate(req) for req in requests]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filtra erros
            valid_responses = []
            for resp in responses:
                if isinstance(resp, Exception):
                    raise resp
                valid_responses.append(resp)
            
            return valid_responses
        
        # Usa batch nativo
        return await provider.batch_generate(requests)
    
    async def estimate_cost(
        self,
        request: ImageGenerationRequest,
        provider_id: Optional[str] = None
    ) -> float:
        """Estima custo de geração"""
        provider = await self.get_provider(provider_id)
        return provider.estimate_cost(request)
    
    async def check_provider_credits(self, provider_id: Optional[str] = None) -> Optional[float]:
        """Verifica créditos disponíveis do provider"""
        provider = await self.get_provider(provider_id)
        credits = await provider.get_remaining_credits()
        
        # Atualiza no banco
        if credits is not None and provider_id:
            config = self.db.query(ImageProviderConfig).filter_by(id=provider_id).first()
            if config:
                config.credits_remaining = credits
                config.last_credit_check = datetime.utcnow()
                self.db.commit()
        
        return credits
    
    async def _update_provider_stats(self, provider_id: str, success: bool, cost: float = 0):
        """Atualiza estatísticas de uso do provider"""
        # TODO: Implementar tabela de estatísticas
        pass
    
    def get_available_providers(self) -> List[Dict[str, Any]]:
        """Lista todos os providers configurados"""
        configs = self.db.query(ImageProviderConfig).all()
        
        result = []
        for config in configs:
            result.append({
                "id": config.id,
                "name": config.name,
                "type": config.provider_type.value,
                "is_active": config.is_active,
                "is_default": config.is_default,
                "credits_remaining": config.credits_remaining,
                "cost_per_image": config.cost_per_image,
                "last_credit_check": config.last_credit_check.isoformat() if config.last_credit_check else None
            })
        
        return result
    
    async def setup_initial_providers(self):
        """Configura providers iniciais para desenvolvimento"""
        # Verifica se já existem providers
        if self.db.query(ImageProviderConfig).count() > 0:
            return
        
        # Cria OpenAI como padrão (se houver API key)
        openai_key = os.getenv('OPENAI_API_KEY')
        if openai_key:
            await self.create_provider_config(
                provider_type=ProviderType.OPENAI,
                name="OpenAI Default",
                api_key=openai_key,
                config={"model": "dall-e-2"},
                is_default=True
            )
        
        # Adiciona outros se tiverem keys
        piapi_key = os.getenv('PIAPI_API_KEY')
        if piapi_key:
            await self.create_provider_config(
                provider_type=ProviderType.PIAPI,
                name="PiAPI Default",
                api_key=piapi_key,
                config={"default_service": "midjourney"},
                is_default=not bool(openai_key)  # Default se OpenAI não estiver configurado
            )
        
        sd_key = os.getenv('STABLE_DIFFUSION_API_KEY')
        if sd_key:
            await self.create_provider_config(
                provider_type=ProviderType.STABLE_DIFFUSION,
                name="Stable Diffusion Default",
                api_key=sd_key,
                config={"model_type": "sdxl"},
                is_default=not bool(openai_key) and not bool(piapi_key)
            )
