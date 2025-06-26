import asyncio
import aiohttp
import base64
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import time
import json

from .base_provider import (
    BaseImageProvider, 
    ImageGenerationRequest, 
    ImageGenerationResponse,
    ProviderError,
    RateLimitError,
    InsufficientCreditsError
)

class PiAPIProvider(BaseImageProvider):
    """Provider para PiAPI - Plataforma unificada de APIs de IA"""
    
    BASE_URL = "https://api.piapi.ai"
    
    # Endpoints por serviço
    ENDPOINTS = {
        "midjourney": "/mj/v2/imagine",
        "flux_txt2img": "/flux/v1/txt2img", 
        "flux_img2img": "/flux/v1/img2img",
        "flux_inpaint": "/flux/v1/inpaint",
        "flux_upscale": "/flux/v1/superresolution",
        "faceswap": "/face/v1/swap",
        "upscale": "/enhance/v1/upscale",
        "remove_bg": "/enhance/v1/removebg"
    }
    
    # Preços estimados por operação (em USD)
    PRICING = {
        "midjourney": 0.009,
        "flux_txt2img": 0.007,
        "flux_img2img": 0.008,
        "flux_inpaint": 0.008,
        "flux_upscale": 0.005,
        "faceswap": 0.010,
        "upscale": 0.005,
        "remove_bg": 0.006
    }
    
    def __init__(self, api_key: str, config: Dict[str, Any] = None):
        super().__init__(api_key, config)
        self.default_service = config.get('default_service', 'midjourney')
        self.webhook_url = config.get('webhook_url')
        self.use_websocket = config.get('use_websocket', False)
        
    async def generate(self, request: ImageGenerationRequest) -> ImageGenerationResponse:
        """Gera imagens usando o serviço selecionado do PiAPI"""
        await self.validate_request(request)
        
        # Determina qual serviço usar
        service = request.extra_params.get('service', self.default_service) if request.extra_params else self.default_service
        
        # Estima custo
        cost = self.estimate_cost(request, service)
        await self.check_credits(cost)
        
        start_time = time.time()
        
        # Prepara payload baseado no serviço
        if service == "midjourney":
            response = await self._generate_midjourney(request)
        elif service.startswith("flux"):
            response = await self._generate_flux(request, service)
        else:
            raise ProviderError(f"Service {service} not supported")
        
        response.generation_time = time.time() - start_time
        response.cost = cost
        response.provider = self.get_provider_name()
        
        return response
    
    async def _generate_midjourney(self, request: ImageGenerationRequest) -> ImageGenerationResponse:
        """Gera imagem usando Midjourney via PiAPI"""
        payload = {
            "prompt": request.prompt,
            "process_mode": "fast",  # fast, relax, turbo
            "aspect_ratio": f"{request.width}:{request.height}",
            "webhook_endpoint": self.webhook_url,
            "webhook_secret": self.config.get('webhook_secret', '')
        }
        
        # Parâmetros opcionais do Midjourney
        if request.extra_params:
            if 'chaos' in request.extra_params:
                payload['chaos'] = request.extra_params['chaos']
            if 'stylize' in request.extra_params:
                payload['stylize'] = request.extra_params['stylize']
            if 'version' in request.extra_params:
                payload['version'] = request.extra_params['version']
        
        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                # Submete job
                async with session.post(
                    f"{self.BASE_URL}{self.ENDPOINTS['midjourney']}",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 429:
                        raise RateLimitError("PiAPI rate limit exceeded")
                    
                    if response.status == 402:
                        raise InsufficientCreditsError("Insufficient PiAPI credits")
                    
                    if response.status != 200:
                        error_data = await response.json()
                        raise ProviderError(f"PiAPI Midjourney error: {error_data}")
                    
                    data = await response.json()
                    task_id = data['task_id']
                
                # Aguarda conclusão (polling ou webhook)
                if self.webhook_url:
                    # Se webhook configurado, retorna task_id para processamento assíncrono
                    return ImageGenerationResponse(
                        images=[],
                        image_urls=[],
                        cost=0,
                        generation_time=0,
                        provider=self.get_provider_name(),
                        metadata={"task_id": task_id, "status": "processing"}
                    )
                else:
                    # Polling até conclusão
                    result = await self._poll_task_status(session, task_id, headers)
                    
                    # Baixa imagens
                    images = []
                    for url in result['image_urls']:
                        img_bytes = await self._download_image(session, url)
                        images.append(img_bytes)
                    
                    return ImageGenerationResponse(
                        images=images,
                        image_urls=result['image_urls'],
                        cost=0,
                        generation_time=0,
                        provider=self.get_provider_name(),
                        metadata={"service": "midjourney", "task_id": task_id}
                    )
                    
        except asyncio.TimeoutError:
            raise ProviderError("PiAPI request timeout")
        except Exception as e:
            raise ProviderError(f"PiAPI generation failed: {str(e)}")
    
    async def _generate_flux(self, request: ImageGenerationRequest, service: str) -> ImageGenerationResponse:
        """Gera imagem usando Flux APIs"""
        endpoint = self.ENDPOINTS.get(service, self.ENDPOINTS['flux_txt2img'])
        
        payload = {
            "prompt": request.prompt,
            "width": request.width,
            "height": request.height,
            "num_inference_steps": request.steps,
            "guidance_scale": request.guidance_scale,
            "num_images": request.num_images
        }
        
        if request.negative_prompt:
            payload["negative_prompt"] = request.negative_prompt
        
        if request.seed:
            payload["seed"] = request.seed
        
        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.BASE_URL}{endpoint}",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status != 200:
                        error_data = await response.json()
                        raise ProviderError(f"PiAPI Flux error: {error_data}")
                    
                    data = await response.json()
                    
                    # Flux retorna imagens em base64
                    images = []
                    image_urls = []
                    
                    for img_data in data.get('images', []):
                        if 'base64' in img_data:
                            img_bytes = base64.b64decode(img_data['base64'])
                            images.append(img_bytes)
                        if 'url' in img_data:
                            image_urls.append(img_data['url'])
                    
                    return ImageGenerationResponse(
                        images=images,
                        image_urls=image_urls,
                        cost=0,
                        generation_time=0,
                        provider=self.get_provider_name(),
                        metadata={"service": service}
                    )
                    
        except Exception as e:
            raise ProviderError(f"PiAPI Flux generation failed: {str(e)}")
    
    async def _poll_task_status(self, session: aiohttp.ClientSession, task_id: str, headers: Dict) -> Dict:
        """Faz polling do status da task até conclusão"""
        status_url = f"{self.BASE_URL}/mj/v2/status/{task_id}"
        max_attempts = 60  # 5 minutos max
        
        for attempt in range(max_attempts):
            async with session.get(status_url, headers=headers) as response:
                if response.status != 200:
                    raise ProviderError(f"Failed to get task status: {await response.text()}")
                
                data = await response.json()
                status = data.get('status')
                
                if status == 'completed':
                    return data
                elif status == 'failed':
                    raise ProviderError(f"Task failed: {data.get('error', 'Unknown error')}")
                
                # Aguarda antes do próximo poll
                await asyncio.sleep(5)
        
        raise ProviderError("Task timeout - generation took too long")
    
    async def _download_image(self, session: aiohttp.ClientSession, url: str) -> bytes:
        """Baixa imagem da URL temporária S3"""
        async with session.get(url) as response:
            if response.status != 200:
                raise ProviderError(f"Failed to download image from {url}")
            return await response.read()
    
    async def batch_generate(self, requests: List[ImageGenerationRequest]) -> List[ImageGenerationResponse]:
        """PiAPI suporta batch em algumas APIs"""
        # Por simplicidade, executa em paralelo
        tasks = [self.generate(req) for req in requests]
        return await asyncio.gather(*tasks)
    
    def estimate_cost(self, request: ImageGenerationRequest, service: str = None) -> float:
        """Estima custo baseado no serviço"""
        if not service:
            service = request.extra_params.get('service', self.default_service) if request.extra_params else self.default_service
        
        base_cost = self.PRICING.get(service, 0.01)
        return base_cost * request.num_images
    
    async def get_remaining_credits(self) -> Optional[float]:
        """Obtém créditos restantes na conta PiAPI"""
        # Verifica cache primeiro
        cached = await self._get_cached_credits()
        if cached is not None:
            return cached
        
        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.BASE_URL}/user/balance",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        return None
                    
                    data = await response.json()
                    credits = data.get('credits', 0)
                    
                    # Cache o resultado
                    self._cache_credits(credits)
                    
                    return credits
        except:
            return None
    
    def get_provider_name(self) -> str:
        return f"PiAPI ({self.default_service})"
    
    def get_supported_sizes(self) -> List[Tuple[int, int]]:
        """Retorna tamanhos suportados (varia por serviço)"""
        # Tamanhos comuns suportados pela maioria dos serviços
        return [
            (512, 512), (768, 768), (1024, 1024),
            (512, 768), (768, 512),
            (1024, 768), (768, 1024),
            (1024, 1792), (1792, 1024)
        ]
    
    def get_max_batch_size(self) -> int:
        """Retorna máximo de imagens por request"""
        return 10  # PiAPI geralmente suporta até 10 imagens
