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

class StableDiffusionProvider(BaseImageProvider):
    """Provider para stable-diffusion.com API - Melhor custo-benefício"""
    
    BASE_URL = "https://stablediffusionapi.com/api/v3"
    
    # Endpoints disponíveis
    ENDPOINTS = {
        "txt2img": "/text2img",
        "img2img": "/img2img", 
        "inpainting": "/inpaint",
        "upscale": "/super_resolution",
        "controlnet": "/controlnet",
        "remove_bg": "/remove_bg"
    }
    
    # Preços por imagem (em USD) - Mais barato do mercado
    PRICING = {
        "sd1.5": 0.0067,  # $10 por 1500 imagens
        "sdxl": 0.010,    # $10 por 1000 imagens
        "upscale": 0.005,
        "inpainting": 0.008,
        "controlnet": 0.012,
        "remove_bg": 0.006
    }
    
    # Modelos disponíveis
    MODELS = {
        "sd1.5": "stable-diffusion-v1-5",
        "sdxl": "stable-diffusion-xl-v1-0",
        "realistic": "realistic-vision-v5",
        "anime": "anything-v5",
        "artistic": "dreamshaper-8"
    }
    
    def __init__(self, api_key: str, config: Dict[str, Any] = None):
        super().__init__(api_key, config)
        self.model_type = config.get('model_type', 'sdxl')  # sd1.5 ou sdxl
        self.model_id = config.get('model_id', self.MODELS.get(self.model_type, 'sdxl'))
        self.use_webhook = config.get('use_webhook', False)
        self.webhook_url = config.get('webhook_url')
        
    async def generate(self, request: ImageGenerationRequest) -> ImageGenerationResponse:
        """Gera imagens usando Stable Diffusion API"""
        await self.validate_request(request)
        
        # Estima custo
        cost = self.estimate_cost(request)
        await self.check_credits(cost)
        
        start_time = time.time()
        
        # Prepara payload
        payload = {
            "key": self.api_key,
            "model_id": self.model_id,
            "prompt": request.prompt,
            "negative_prompt": request.negative_prompt or "",
            "width": str(request.width),
            "height": str(request.height),
            "samples": str(request.num_images),
            "num_inference_steps": str(request.steps),
            "guidance_scale": request.guidance_scale,
            "enhance_prompt": "yes",  # Melhora automaticamente o prompt
            "safety_checker": "yes",  # Filtro de conteúdo
            "multi_lingual": "yes",   # Suporte multi-idioma
            "panorama": "no",
            "self_attention": "yes",
            "upscale": "no",
            "embeddings_model": None,
            "lora_model": None,
            "tomesd": "yes",  # Otimização de velocidade
            "clip_skip": "1",
            "use_karras_sigmas": "yes",
            "vae": None,
            "lora_strength": None,
            "scheduler": "DDPMScheduler"
        }
        
        # Seed opcional
        if request.seed:
            payload["seed"] = str(request.seed)
        
        # Webhook opcional
        if self.use_webhook and self.webhook_url:
            payload["webhook"] = self.webhook_url
            payload["track_id"] = f"img_{int(time.time())}"
        
        # Parâmetros extras
        if request.extra_params:
            # ControlNet
            if 'controlnet' in request.extra_params:
                payload["controlnet"] = "yes"
                payload["controlnet_model"] = request.extra_params.get('controlnet_model', 'canny')
                if 'init_image' in request.extra_params:
                    payload["init_image"] = request.extra_params['init_image']
            
            # LoRA
            if 'lora_model' in request.extra_params:
                payload["lora_model"] = request.extra_params['lora_model']
                payload["lora_strength"] = str(request.extra_params.get('lora_strength', 0.7))
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.BASE_URL}{self.ENDPOINTS['txt2img']}",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=90)
                ) as response:
                    if response.status == 429:
                        raise RateLimitError("Stable Diffusion API rate limit exceeded")
                    
                    if response.status == 402:
                        raise InsufficientCreditsError("Insufficient credits")
                    
                    if response.status != 200:
                        error_data = await response.json()
                        raise ProviderError(f"Stable Diffusion API error: {error_data}")
                    
                    data = await response.json()
                    
                    # Verifica status
                    if data.get('status') == 'error':
                        raise ProviderError(f"Generation failed: {data.get('message', 'Unknown error')}")
                    
                    # Se usando webhook, retorna ID para tracking
                    if self.use_webhook and 'id' in data:
                        return ImageGenerationResponse(
                            images=[],
                            image_urls=[],
                            cost=cost,
                            generation_time=time.time() - start_time,
                            provider=self.get_provider_name(),
                            metadata={
                                "generation_id": data['id'],
                                "status": "processing",
                                "eta": data.get('eta', 30)
                            }
                        )
                    
                    # Processamento síncrono - extrai imagens
                    images = []
                    image_urls = data.get('output', [])
                    
                    # Baixa as imagens
                    for url in image_urls:
                        img_bytes = await self._download_image(session, url)
                        images.append(img_bytes)
                    
                    generation_time = time.time() - start_time
                    
                    return ImageGenerationResponse(
                        images=images,
                        image_urls=image_urls,
                        cost=cost,
                        generation_time=generation_time,
                        provider=self.get_provider_name(),
                        metadata={
                            "model": self.model_id,
                            "steps": request.steps,
                            "seed": data.get('meta', {}).get('seed')
                        }
                    )
                    
        except asyncio.TimeoutError:
            raise ProviderError("Stable Diffusion API request timeout")
        except Exception as e:
            raise ProviderError(f"Stable Diffusion generation failed: {str(e)}")
    
    async def _download_image(self, session: aiohttp.ClientSession, url: str) -> bytes:
        """Baixa imagem da URL"""
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    raise ProviderError(f"Failed to download image from {url}")
                return await response.read()
        except Exception as e:
            raise ProviderError(f"Image download failed: {str(e)}")
    
    async def batch_generate(self, requests: List[ImageGenerationRequest]) -> List[ImageGenerationResponse]:
        """Stable Diffusion suporta batch nativo até 4 imagens por request"""
        # Agrupa requests em batches de até 4
        batch_size = 4
        results = []
        
        for i in range(0, len(requests), batch_size):
            batch = requests[i:i+batch_size]
            
            # Cria um request combinado
            combined_request = ImageGenerationRequest(
                prompt=batch[0].prompt,  # Usa o primeiro prompt
                negative_prompt=batch[0].negative_prompt,
                width=batch[0].width,
                height=batch[0].height,
                num_images=len(batch),
                seed=batch[0].seed,
                guidance_scale=batch[0].guidance_scale,
                steps=batch[0].steps,
                style=batch[0].style,
                extra_params=batch[0].extra_params
            )
            
            # Gera o batch
            response = await self.generate(combined_request)
            
            # Divide a resposta para cada request original
            for j, req in enumerate(batch):
                if j < len(response.images):
                    individual_response = ImageGenerationResponse(
                        images=[response.images[j]],
                        image_urls=[response.image_urls[j]] if j < len(response.image_urls) else [],
                        cost=response.cost / len(batch),
                        generation_time=response.generation_time,
                        provider=response.provider,
                        metadata=response.metadata
                    )
                    results.append(individual_response)
        
        return results
    
    def estimate_cost(self, request: ImageGenerationRequest) -> float:
        """Estima custo baseado no modelo e número de imagens"""
        base_price = self.PRICING.get(self.model_type, 0.01)
        
        # Ajusta preço para recursos extras
        if request.extra_params:
            if 'controlnet' in request.extra_params:
                base_price = self.PRICING.get('controlnet', 0.012)
            elif 'upscale' in request.extra_params:
                base_price = self.PRICING.get('upscale', 0.005)
        
        return base_price * request.num_images
    
    async def get_remaining_credits(self) -> Optional[float]:
        """Obtém créditos restantes na conta"""
        # Verifica cache primeiro
        cached = await self._get_cached_credits()
        if cached is not None:
            return cached
        
        headers = {
            "Content-Type": "application/json"
        }
        
        payload = {
            "key": self.api_key
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://stablediffusionapi.com/api/v3/get_balance",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        return None
                    
                    data = await response.json()
                    
                    # Converte créditos em valor aproximado de imagens
                    # Assumindo que 1 crédito = 1 imagem SDXL
                    credits = float(data.get('balance', 0))
                    
                    # Cache o resultado
                    self._cache_credits(credits)
                    
                    return credits
        except:
            return None
    
    def get_provider_name(self) -> str:
        return f"Stable-Diffusion.com ({self.model_type.upper()})"
    
    def get_supported_sizes(self) -> List[Tuple[int, int]]:
        """Retorna tamanhos suportados"""
        # SD 1.5 e SDXL suportam tamanhos customizados
        # mas estes são os mais otimizados
        return [
            (512, 512), (768, 768), (1024, 1024),
            (512, 768), (768, 512),
            (576, 1024), (1024, 576),
            (768, 1344), (1344, 768),
            (1024, 1792), (1792, 1024),
            (2048, 2048), (4096, 4096)  # Com upscale
        ]
    
    def get_max_batch_size(self) -> int:
        """Retorna máximo de imagens por request"""
        return 4  # API suporta até 4 samples por request
