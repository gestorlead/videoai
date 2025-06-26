# Image Generation Service

## Overview

O serviço de geração de imagens permite criar imagens usando múltiplos provedores de IA, com suporte a fallback automático, monitoramento de custos e créditos.

## Provedores Suportados

### 1. **OpenAI (DALL-E 2/3 e GPT-4 Vision)**
- **DALL-E 2**: $0.016-$0.020 por imagem
- **DALL-E 3**: $0.040-$0.080 por imagem
- **GPT-4 Vision**: $0.01 base + $0.005 por imagem analisada
- **Qualidade**: Alta, especialmente para prompts complexos
- **Tamanhos**: 256x256, 512x512, 1024x1024 (DALL-E 2); 1024x1024, 1024x1792, 1792x1024 (DALL-E 3)
- **Vantagens**: 
  - Melhor entendimento de texto
  - Qualidade consistente
  - GPT-4 Vision permite análise de imagens e geração baseada em análise

### 2. **PiAPI Platform**
- **Custo**: ~$0.009 por imagem
- **Serviços**: Midjourney, Flux (txt2img, img2img, inpaint, upscale), Faceswap
- **Vantagens**: Múltiplos modelos em uma API, webhooks, WebSocket para progresso
- **Batch**: Até 10 imagens

### 3. **Stable-Diffusion.com**
- **Custo**: $0.0067-$0.010 por imagem (mais barato do mercado)
- **Modelos**: SD 1.5, SDXL, Realistic Vision, Anime, DreamShaper
- **Vantagens**: ControlNet, upscaler 4x, face-fix, batch até 4 imagens
- **Rate Limit**: 180-400 RPM

## API Endpoints

### 1. Gerar Imagem
```bash
POST /api/v1/images/generate
Authorization: Bearer YOUR_API_KEY

{
  "prompt": "A beautiful sunset over mountains",
  "negative_prompt": "blurry, low quality",
  "width": 1024,
  "height": 1024,
  "num_images": 1,
  "provider_id": "piapi_default",  # Opcional
  "style": "realistic",
  "guidance_scale": 7.5,
  "steps": 30,
  "extra_params": {
    "service": "midjourney"  # Para PiAPI
  }
}
```

### 2. Gerar em Batch
```bash
POST /api/v1/images/batch-generate
Authorization: Bearer YOUR_API_KEY

{
  "requests": [
    {"prompt": "A cat playing piano", "width": 1024, "height": 1024},
    {"prompt": "A dog reading newspaper", "width": 1024, "height": 1024}
  ],
  "provider_id": "stable_diffusion_default"
}
```

### 3. Listar Provedores
```bash
GET /api/v1/images/providers
Authorization: Bearer YOUR_API_KEY

Response:
[
  {
    "id": "openai_default",
    "name": "OpenAI Default",
    "type": "openai",
    "is_active": true,
    "is_default": true,
    "cost_per_image": 0.020,
    "credits_remaining": null
  },
  {
    "id": "piapi_default",
    "name": "PiAPI Default",
    "type": "piapi",
    "is_active": true,
    "is_default": false,
    "cost_per_image": 0.009,
    "credits_remaining": 1250.5
  }
]
```

### 4. Configurar Provedor (Admin)
```bash
POST /api/v1/images/providers
Authorization: Bearer YOUR_API_KEY

{
  "provider_type": "piapi",
  "name": "PiAPI Midjourney",
  "api_key": "YOUR_PIAPI_KEY",
  "config": {
    "default_service": "midjourney",
    "use_websocket": true
  },
  "is_default": false
}
```

### 5. Verificar Créditos
```bash
GET /api/v1/images/providers/{provider_id}/credits
Authorization: Bearer YOUR_API_KEY

Response:
{
  "provider_id": "piapi_default",
  "credits": 1250.5,
  "has_credits": true
}
```

### 6. Estimar Custo
```bash
POST /api/v1/images/estimate-cost
Authorization: Bearer YOUR_API_KEY

{
  "prompt": "A beautiful landscape",
  "width": 1024,
  "height": 1024,
  "num_images": 5,
  "provider_id": "stable_diffusion_default"
}

Response:
{
  "estimated_cost": 0.05,
  "provider_id": "stable_diffusion_default",
  "num_images": 5
}
```

## Configuração

### 1. Variáveis de Ambiente
```env
# OpenAI
OPENAI_API_KEY=sk-...

# PiAPI
PIAPI_API_KEY=piapi_...

# Stable Diffusion
STABLE_DIFFUSION_API_KEY=sd_...

# Encryption key (gerada automaticamente)
# Armazenada em videoai/.encryption_key
```

### 2. Configuração Inicial
O sistema detecta automaticamente as API keys disponíveis e configura os provedores na primeira execução:

- Se `OPENAI_API_KEY` existe → OpenAI como padrão
- Se `PIAPI_API_KEY` existe → PiAPI como fallback
- Se `STABLE_DIFFUSION_API_KEY` existe → SD como segundo fallback

### 3. Estratégia de Roteamento

#### Por Qualidade/Estilo:
- **Alta qualidade/Realismo**: OpenAI DALL-E 3 ou Stable Diffusion SDXL
- **Arte/Criatividade**: PiAPI Midjourney
- **Anime/Manga**: Stable Diffusion com modelo Anything-v5
- **Volume/Baixo custo**: Stable-Diffusion.com ou GetIMG.ai

#### Por Feature:
- **ControlNet**: Stable-Diffusion.com
- **Inpainting/Edição**: PiAPI Flux
- **Faceswap**: PiAPI
- **Upscaling**: Stable-Diffusion.com ou PiAPI

## Exemplos de Uso

### 1. Geração Simples com OpenAI
```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/images/generate",
    headers={"Authorization": "Bearer YOUR_API_KEY"},
    json={
        "prompt": "A futuristic city at night",
        "provider_id": "openai_default"
    }
)

data = response.json()
print(f"Images: {data['image_urls']}")
print(f"Cost: ${data['cost']}")
```

### 2. Batch com Fallback
```python
# Sem especificar provider, usa padrão com fallback automático
response = requests.post(
    "http://localhost:8000/api/v1/images/batch-generate",
    headers={"Authorization": "Bearer YOUR_API_KEY"},
    json={
        "requests": [
            {"prompt": f"Product photo {i}"} for i in range(5)
        ]
    }
)
```

### 3. Usando PiAPI Midjourney
```python
response = requests.post(
    "http://localhost:8000/api/v1/images/generate",
    headers={"Authorization": "Bearer YOUR_API_KEY"},
    json={
        "prompt": "ethereal fantasy landscape, highly detailed",
        "provider_id": "piapi_default",
        "extra_params": {
            "service": "midjourney",
            "chaos": 50,
            "stylize": 1000
        }
    }
)
```

### 4. ControlNet com Stable Diffusion
```python
response = requests.post(
    "http://localhost:8000/api/v1/images/generate",
    headers={"Authorization": "Bearer YOUR_API_KEY"},
    json={
        "prompt": "modern house, architectural photography",
        "provider_id": "stable_diffusion_default",
        "extra_params": {
            "controlnet": True,
            "controlnet_model": "canny",
            "init_image": "base64_encoded_image_here"
        }
    }
)
```

### 5. GPT-4 Vision - Análise de Imagem
```python
# Apenas análise de imagem
response = requests.post(
    "http://localhost:8000/api/v1/images/generate",
    headers={"Authorization": "Bearer YOUR_API_KEY"},
    json={
        "prompt": "Analyze this image and describe what you see",
        "provider_id": "openai_default",
        "extra_params": {
            "mode": "vision",
            "input_images": ["https://example.com/image.jpg"],
            "generate_from_analysis": False
        }
    }
)

# Resposta contém análise no metadata
analysis = response.json()['metadata']['analysis']
```

### 6. GPT-4 Vision - Análise + Geração
```python
# Analisa imagem e gera nova baseada na análise
response = requests.post(
    "http://localhost:8000/api/v1/images/generate",
    headers={"Authorization": "Bearer YOUR_API_KEY"},
    json={
        "prompt": "Create a similar image but in cyberpunk style",
        "width": 1024,
        "height": 1024,
        "provider_id": "openai_default",
        "extra_params": {
            "mode": "vision",
            "input_images": ["https://example.com/city.jpg"],
            "generate_from_analysis": True,
            "dalle_model": "dall-e-3"
        }
    }
)

# Resposta contém imagem gerada e análise original
result = response.json()
print(f"Analysis: {result['metadata']['vision_analysis']}")
print(f"Enhanced prompt: {result['metadata']['enhanced_prompt']}")
print(f"Generated image: {result['image_urls'][0]}")
```

### 7. GPT-4 Vision - Múltiplas Imagens
```python
import base64

# Análise de múltiplas imagens
with open("image1.jpg", "rb") as f:
    img1_bytes = f.read()

response = requests.post(
    "http://localhost:8000/api/v1/images/generate",
    headers={"Authorization": "Bearer YOUR_API_KEY"},
    json={
        "prompt": "Compare these images and create a fusion combining the best elements",
        "provider_id": "openai_default",
        "extra_params": {
            "mode": "vision",
            "input_images": [
                "https://example.com/image1.jpg",
                img1_bytes,  # Pode enviar bytes diretamente
                "https://example.com/image2.jpg"
            ],
            "generate_from_analysis": True
        }
    }
)
```

## Monitoramento e Custos

### Tracking de Custos
Todos os jobs são salvos no banco com informações de custo:
```sql
SELECT 
    provider_id,
    COUNT(*) as total_images,
    SUM(cost) as total_cost,
    AVG(generation_time) as avg_time
FROM image_generation_jobs
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY provider_id;
```

### Alertas de Créditos
O sistema verifica créditos antes de cada geração e alerta quando:
- Créditos < 10% do último check
- Falha por créditos insuficientes
- Provider indisponível

## Migração do Banco

```bash
# Criar tabelas
cd videoai
alembic upgrade head

# Ou manualmente
python -c "
from app.core.database import engine
from app.models.image_provider import Base
Base.metadata.create_all(bind=engine)
"
```

## Troubleshooting

### Erro: "No default provider configured"
- Verifique se há pelo menos uma API key configurada
- Execute o setup inicial ou configure manualmente via API

### Erro: "Insufficient credits"
- Verifique saldo do provider
- Configure fallback para outro provider
- Recarregue créditos na plataforma

### Erro: "Rate limit exceeded"
- Sistema tentará automaticamente próximo provider
- Configure rate limits apropriados por provider
- Use batch para otimizar requests

## Batch Processing Avançado

O sistema inclui funcionalidades avançadas para processamento em batch com alta performance:

### Funcionalidades

#### Sistema de Cache Inteligente
- **Cache em múltiplas camadas**: Memória, Redis e disco local
- **TTL configurável**: Controle de expiração de cache
- **Deduplicação automática**: Evita gerar imagens idênticas
- **Métricas de hit rate**: Monitoramento de eficiência

#### Processamento Paralelo
- **Workers dinâmicos**: Ajusta automaticamente baseado na carga
- **Rate limiting por provider**: Respeita limites de API
- **Fallback automático**: Troca de provider em caso de falha
- **Retry logic**: Reprocessamento inteligente de falhas

#### Monitoramento em Tempo Real
- **Métricas de performance**: Tempo médio, taxa de sucesso, custos
- **Alertas automáticos**: Rate limit, créditos baixos, filas grandes
- **Dashboard de status**: Progresso detalhado dos jobs
- **Analytics por provider**: Comparação de performance

### Endpoints de Batch Avançado

#### Submeter Job em Batch
```http
POST /api/v1/images/batch
```

```json
{
  "requests": [
    {
      "prompt": "A beautiful sunset",
      "width": 1024,
      "height": 1024,
      "num_images": 1
    }
  ],
  "provider_id": "openai",
  "priority": 5,
  "metadata": {
    "description": "Marketing campaign images"
  }
}
```

#### Verificar Status do Batch
```http
GET /api/v1/images/batch/{job_id}
```

#### Métricas do Sistema
```http
GET /api/v1/images/metrics
```

#### Estatísticas de Cache
```http
GET /api/v1/images/cache/stats
```

#### Performance por Provider
```http
GET /api/v1/images/providers/{provider_id}/performance?hours=24
```

#### Alertas do Sistema
```http
GET /api/v1/images/monitor/alerts
```

### Configuração Avançada

#### Variables de Ambiente para Batch
```bash
# Cache
REDIS_URL=redis://localhost:6379
BATCH_CACHE_TTL_HOURS=24
BATCH_CACHE_MAX_MEMORY_ITEMS=1000

# Processing
BATCH_MAX_CONCURRENT=10
BATCH_MAX_RETRIES=3
BATCH_RETRY_DELAY=2.0

# Monitoring
BATCH_MONITOR_INTERVAL=30
ALERT_HIGH_FAILURE_RATE=0.2
ALERT_SLOW_RESPONSE_TIME=30.0
```

## Próximos Passos

1. **Storage permanente**: Upload para S3/Cloudinary após geração
2. ✅ **Cache de imagens**: Sistema completo implementado
3. **Webhook handlers**: Processar callbacks assíncronos
4. **Fine-tuning**: Suporte a modelos customizados
5. **Análise de prompts**: Otimização automática de prompts
6. ✅ **Batch processing**: Sistema avançado implementado
