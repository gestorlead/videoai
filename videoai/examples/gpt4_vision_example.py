"""
Exemplo de uso do GPT-4 Vision com o serviço de geração de imagens
"""

import asyncio
import base64
from typing import List
import aiohttp

# Configuração da API
API_URL = "http://localhost:8000/api/v1/images"
API_KEY = "YOUR_API_KEY"

async def analyze_image(image_url: str):
    """Exemplo 1: Apenas analisar uma imagem"""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{API_URL}/generate",
            headers={"Authorization": f"Bearer {API_KEY}"},
            json={
                "prompt": "Please analyze this image and describe what you see in detail. Include colors, objects, composition, and mood.",
                "provider_id": "openai_default",
                "extra_params": {
                    "mode": "vision",
                    "input_images": [image_url],
                    "generate_from_analysis": False
                }
            }
        ) as response:
            result = await response.json()
            print("=== Image Analysis ===")
            print(result['metadata']['analysis'])
            print(f"Cost: ${result['cost']}")
            return result

async def generate_from_image(image_url: str, style: str = "cyberpunk"):
    """Exemplo 2: Analisar imagem e gerar nova versão em estilo diferente"""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{API_URL}/generate",
            headers={"Authorization": f"Bearer {API_KEY}"},
            json={
                "prompt": f"Analyze this image and create a new version in {style} style, maintaining the main elements but transforming the aesthetic",
                "width": 1024,
                "height": 1024,
                "provider_id": "openai_default",
                "extra_params": {
                    "mode": "vision",
                    "input_images": [image_url],
                    "generate_from_analysis": True,
                    "dalle_model": "dall-e-3"
                }
            }
        ) as response:
            result = await response.json()
            print(f"\n=== Generated {style.title()} Version ===")
            print(f"Analysis: {result['metadata']['vision_analysis'][:200]}...")
            print(f"Enhanced Prompt: {result['metadata']['enhanced_prompt'][:200]}...")
            print(f"Generated Image URL: {result['image_urls'][0]}")
            print(f"Total Cost: ${result['cost']}")
            return result

async def compare_images(image_urls: List[str]):
    """Exemplo 3: Comparar múltiplas imagens e gerar fusão"""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{API_URL}/generate",
            headers={"Authorization": f"Bearer {API_KEY}"},
            json={
                "prompt": "Compare these images, identify the best elements from each, and create a new image that combines the strongest features of all images into a cohesive composition",
                "width": 1024,
                "height": 1024,
                "provider_id": "openai_default",
                "extra_params": {
                    "mode": "vision",
                    "input_images": image_urls,
                    "generate_from_analysis": True
                }
            }
        ) as response:
            result = await response.json()
            print("\n=== Image Comparison & Fusion ===")
            print(f"Analysis: {result['metadata']['vision_analysis'][:300]}...")
            print(f"Generated Fusion: {result['image_urls'][0]}")
            print(f"Cost: ${result['cost']}")
            return result

async def image_to_prompt(image_path: str):
    """Exemplo 4: Converter imagem local em prompt detalhado para DALL-E"""
    # Ler imagem local
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    
    async with aiohttp.ClientSession() as session:
        # Primeiro, analisa a imagem para extrair prompt
        async with session.post(
            f"{API_URL}/generate",
            headers={"Authorization": f"Bearer {API_KEY}"},
            json={
                "prompt": "Analyze this image and create a detailed DALL-E prompt that would recreate a similar image. Include style, composition, colors, lighting, and all visual elements.",
                "provider_id": "openai_default",
                "extra_params": {
                    "mode": "vision",
                    "input_images": [image_bytes],
                    "generate_from_analysis": False
                }
            }
        ) as response:
            analysis_result = await response.json()
            extracted_prompt = analysis_result['metadata']['analysis']
            
        print(f"\n=== Extracted Prompt ===")
        print(extracted_prompt)
        
        # Agora usa o prompt extraído para gerar nova imagem
        async with session.post(
            f"{API_URL}/generate",
            headers={"Authorization": f"Bearer {API_KEY}"},
            json={
                "prompt": extracted_prompt,
                "width": 1024,
                "height": 1024,
                "provider_id": "openai_default"
            }
        ) as response:
            generation_result = await response.json()
            print(f"\nGenerated Similar Image: {generation_result['image_urls'][0]}")
            print(f"Total Cost: ${analysis_result['cost'] + generation_result['cost']}")

async def style_transfer(content_image: str, style_reference: str):
    """Exemplo 5: Transferência de estilo entre imagens"""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{API_URL}/generate",
            headers={"Authorization": f"Bearer {API_KEY}"},
            json={
                "prompt": "Analyze the first image (content) and the second image (style reference). Create a new image that applies the artistic style, color palette, and visual techniques from the second image to the subject matter of the first image.",
                "width": 1024,
                "height": 1024,
                "provider_id": "openai_default",
                "extra_params": {
                    "mode": "vision",
                    "input_images": [content_image, style_reference],
                    "generate_from_analysis": True,
                    "dalle_model": "dall-e-3"
                }
            }
        ) as response:
            result = await response.json()
            print("\n=== Style Transfer ===")
            print(f"Content: {content_image}")
            print(f"Style: {style_reference}")
            print(f"Result: {result['image_urls'][0]}")
            print(f"Cost: ${result['cost']}")
            return result

async def main():
    """Executa exemplos"""
    # URLs de exemplo (substitua por URLs reais)
    example_image = "https://example.com/landscape.jpg"
    example_images = [
        "https://example.com/image1.jpg",
        "https://example.com/image2.jpg",
        "https://example.com/image3.jpg"
    ]
    
    print("GPT-4 Vision Examples\n" + "="*50)
    
    # Exemplo 1: Análise simples
    await analyze_image(example_image)
    
    # Exemplo 2: Geração com estilo
    await generate_from_image(example_image, "steampunk")
    
    # Exemplo 3: Comparação e fusão
    await compare_images(example_images)
    
    # Exemplo 4: Imagem para prompt (requer arquivo local)
    # await image_to_prompt("local_image.jpg")
    
    # Exemplo 5: Transferência de estilo
    await style_transfer(
        "https://example.com/portrait.jpg",
        "https://example.com/vangogh-style.jpg"
    )

if __name__ == "__main__":
    asyncio.run(main())
