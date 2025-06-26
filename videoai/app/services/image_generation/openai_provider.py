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
    RateLimitError
)

class OpenAIProvider(BaseImageProvider):
    """Provider para OpenAI DALL-E e GPT-4 Vision"""
    
    BASE_URL = "https://api.openai.com/v1"
    
    # Preços por imagem (em USD)
    PRICING = {
        "dall-e-2": {
            (256, 256): 0.016,
            (512, 512): 0.018,
            (1024, 1024): 0.020
        },
        "dall-e-3": {
            (1024, 1024): 0.040,
            (1024, 1792): 0.080,
            (1792, 1024): 0.080
        },
        "gpt-4-vision-preview": {
            "base": 0.01,  # Custo base por request
            "per_image": 0.005  # Custo adicional por imagem analisada
        }
    }
    
    def __init__(self, api_key: str, config: Dict[str, Any] = None):
        super().__init__(api_key, config)
        self.model = config.get('model', 'dall-e-2')  # dall-e-2, dall-e-3 ou gpt-4-vision-preview
        self.quality = config.get('quality', 'standard')  # standard ou hd (apenas dall-e-3)
        self.vision_model = config.get('vision_model', 'gpt-4-vision-preview')  # Modelo para análise de imagem
        
    async def generate(self, request: ImageGenerationRequest) -> ImageGenerationResponse:
        """Gera imagens usando OpenAI DALL-E ou analisa/gera com GPT-4 Vision"""
        # Se for GPT-4 Vision, usa método específico
        if self.model == 'gpt-4-vision-preview' or (request.extra_params and request.extra_params.get('mode') == 'vision'):
            return await self._generate_with_vision(request)
        
        await self.validate_request(request)
        
        # Estima custo
        cost = self.estimate_cost(request)
        await self.check_credits(cost)
        
        start_time = time.time()
        
        # Prepara payload
        payload = {
            "model": self.model,
            "prompt": request.prompt,
            "n": request.num_images,
            "size": f"{request.width}x{request.height}",
            "response_format": "b64_json"  # Retorna base64 direto
        }
        
        if self.model == "dall-e-3":
            payload["quality"] = self.quality
            if request.style:
                payload["style"] = request.style  # natural ou vivid
        
        # Headers
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.BASE_URL}/images/generations",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 429:
                        raise RateLimitError("OpenAI rate limit exceeded")
                    
                    if response.status != 200:
                        error_data = await response.json()
                        raise ProviderError(f"OpenAI API error: {error_data}")
                    
                    data = await response.json()
                    
                    # Extrai imagens
                    images = []
                    image_urls = []
                    
                    for img_data in data['data']:
                        # Decodifica base64
                        img_bytes = base64.b64decode(img_data['b64_json'])
                        images.append(img_bytes)
                        
                        # OpenAI não retorna URLs permanentes em b64_json
                        image_urls.append("")
                    
                    generation_time = time.time() - start_time
                    
                    return ImageGenerationResponse(
                        images=images,
                        image_urls=image_urls,
                        cost=cost,
                        generation_time=generation_time,
                        provider=self.get_provider_name(),
                        metadata={
                            "model": self.model,
                            "quality": self.quality if self.model == "dall-e-3" else "standard"
                        }
                    )
                    
        except asyncio.TimeoutError:
            raise ProviderError("OpenAI request timeout")
        except Exception as e:
            raise ProviderError(f"OpenAI generation failed: {str(e)}")
    
    async def _generate_with_vision(self, request: ImageGenerationRequest) -> ImageGenerationResponse:
        """Usa GPT-4 Vision para analisar imagens e gerar novas baseadas na análise"""
        start_time = time.time()
        
        # Prepara mensagens para o GPT-4 Vision
        messages = [{
            "role": "system",
            "content": "You are an AI assistant that analyzes images and helps generate new images based on the analysis."
        }]
        
        # Se há imagens para analisar
        if request.extra_params and 'input_images' in request.extra_params:
            content = [{"type": "text", "text": request.prompt}]
            
            # Adiciona imagens para análise
            for img in request.extra_params['input_images']:
                if isinstance(img, str) and img.startswith('http'):
                    # URL da imagem
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": img}
                    })
                elif isinstance(img, bytes):
                    # Imagem em bytes - converte para base64
                    img_b64 = base64.b64encode(img).decode('utf-8')
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}
                    })
            
            messages.append({
                "role": "user",
                "content": content
            })
        else:
            # Apenas texto
            messages.append({
                "role": "user",
                "content": request.prompt
            })
        
        # Headers
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                # Primeiro, usa GPT-4 Vision para analisar/processar
                vision_payload = {
                    "model": self.vision_model,
                    "messages": messages,
                    "max_tokens": 1000
                }
                
                async with session.post(
                    f"{self.BASE_URL}/chat/completions",
                    json=vision_payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status != 200:
                        error_data = await response.json()
                        raise ProviderError(f"GPT-4 Vision error: {error_data}")
                    
                    vision_data = await response.json()
                    analysis = vision_data['choices'][0]['message']['content']
                
                # Se solicitado, gera nova imagem baseada na análise
                if request.extra_params and request.extra_params.get('generate_from_analysis', True):
                    # Usa a análise como prompt melhorado
                    enhanced_prompt = f"{request.prompt}\n\nBased on analysis: {analysis}"
                    
                    # Gera imagem com DALL-E
                    dalle_model = request.extra_params.get('dalle_model', 'dall-e-3')
                    generation_payload = {
                        "model": dalle_model,
                        "prompt": enhanced_prompt[:4000],  # Limite de caracteres
                        "n": request.num_images,
                        "size": f"{request.width}x{request.height}",
                        "response_format": "b64_json"
                    }
                    
                    if dalle_model == "dall-e-3":
                        generation_payload["quality"] = self.quality
                    
                    async with session.post(
                        f"{self.BASE_URL}/images/generations",
                        json=generation_payload,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=60)
                    ) as response:
                        if response.status != 200:
                            error_data = await response.json()
                            raise ProviderError(f"DALL-E generation error: {error_data}")
                        
                        dalle_data = await response.json()
                        
                        # Processa imagens geradas
                        images = []
                        image_urls = []
                        
                        for img_data in dalle_data['data']:
                            img_bytes = base64.b64decode(img_data['b64_json'])
                            images.append(img_bytes)
                            image_urls.append("")
                        
                        generation_time = time.time() - start_time
                        
                        return ImageGenerationResponse(
                            images=images,
                            image_urls=image_urls,
                            cost=self.estimate_cost(request),
                            generation_time=generation_time,
                            provider=self.get_provider_name(),
                            metadata={
                                "model": "gpt-4-vision + " + dalle_model,
                                "vision_analysis": analysis,
                                "enhanced_prompt": enhanced_prompt
                            }
                        )
                else:
                    # Retorna apenas a análise
                    generation_time = time.time() - start_time
                    
                    return ImageGenerationResponse(
                        images=[],
                        image_urls=[],
                        cost=self.PRICING['gpt-4-vision-preview']['base'],
                        generation_time=generation_time,
                        provider=self.get_provider_name(),
                        metadata={
                            "model": self.vision_model,
                            "analysis": analysis,
                            "mode": "analysis_only"
                        }
                    )
                    
        except Exception as e:
            raise ProviderError(f"GPT-4 Vision generation failed: {str(e)}")
    
    async def batch_generate(self, requests: List[ImageGenerationRequest]) -> List[ImageGenerationResponse]:
        """OpenAI não suporta batch nativo, executa em paralelo"""
        tasks = [self.generate(req) for req in requests]
        return await asyncio.gather(*tasks)
    
    def estimate_cost(self, request: ImageGenerationRequest) -> float:
        """Estima custo baseado no modelo e tamanho"""
        if self.model == 'gpt-4-vision-preview' or (request.extra_params and request.extra_params.get('mode') == 'vision'):
            # Custo do GPT-4 Vision
            base_cost = self.PRICING['gpt-4-vision-preview']['base']
            
            # Adiciona custo por imagem analisada
            if request.extra_params and 'input_images' in request.extra_params:
                num_input_images = len(request.extra_params['input_images'])
                base_cost += num_input_images * self.PRICING['gpt-4-vision-preview']['per_image']
            
            # Se vai gerar imagem também
            if request.extra_params and request.extra_params.get('generate_from_analysis', True):
                dalle_model = request.extra_params.get('dalle_model', 'dall-e-3')
                if dalle_model == 'dall-e-3':
                    base_cost += self.PRICING['dall-e-3'].get((request.width, request.height), 0.04)
                else:
                    base_cost += self.PRICING['dall-e-2'].get((request.width, request.height), 0.02)
            
            return base_cost * request.num_images
        
        # Custo normal do DALL-E
        size = (request.width, request.height)
        model_pricing = self.PRICING.get(self.model, {})
        
        if size not in model_pricing:
            # Retorna preço máximo se tamanho não encontrado
            return max(model_pricing.values()) * request.num_images
        
        return model_pricing[size] * request.num_images
    
    async def get_remaining_credits(self) -> Optional[float]:
        """OpenAI não tem sistema de créditos, retorna None"""
        # OpenAI usa billing mensal, não créditos pré-pagos
        return None
    
    def get_provider_name(self) -> str:
        if self.model == 'gpt-4-vision-preview':
            return "OpenAI (GPT-4 Vision)"
        return f"OpenAI ({self.model})"
    
    def get_supported_sizes(self) -> List[Tuple[int, int]]:
        """Retorna tamanhos suportados pelo modelo"""
        if self.model == "dall-e-2":
            return [(256, 256), (512, 512), (1024, 1024)]
        elif self.model == "dall-e-3":
            return [(1024, 1024), (1024, 1792), (1792, 1024)]
        else:  # gpt-4-vision-preview
            # GPT-4 Vision suporta todos os tamanhos do DALL-E
            return [(256, 256), (512, 512), (1024, 1024), (1024, 1792), (1792, 1024)]
    
    def get_max_batch_size(self) -> int:
        """Retorna máximo de imagens por request"""
        if self.model == "dall-e-2":
            return 10
        else:  # dall-e-3 ou gpt-4-vision
            return 1  # DALL-E 3 e GPT-4 Vision só suportam 1 imagem por vez
