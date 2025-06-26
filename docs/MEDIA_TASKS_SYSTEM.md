# Sistema de Tarefas de Mídia - VideoAI

## Visão Geral

O Sistema de Tarefas de Mídia é uma arquitetura assíncrona unificada que suporta processamento de múltiplos tipos de mídia (imagens, vídeos, áudio, legendas) com recursos avançados de monitoramento, webhooks e gerenciamento de provedores.

## 🎯 Características Principais

### ✅ **Implementado na Tarefa 3.2**

- ✅ **API Unificada**: Endpoints consistentes para todos os tipos de mídia
- ✅ **Processamento Assíncrono**: Tasks não-bloqueantes com status em tempo real
- ✅ **Sistema de Webhooks**: Notificações automáticas de progresso e conclusão
- ✅ **Provider Registry**: Gerenciamento inteligente de provedores de IA
- ✅ **Filas Inteligentes**: Sistema de prioridades e balanceamento de carga
- ✅ **Monitoramento Completo**: Métricas, logs e health checks
- ✅ **Batch Processing**: Processamento em lote otimizado
- ✅ **Retry Logic**: Sistema robusto de tentativas com exponential backoff
- ✅ **Cache Multicamadas**: Otimização de performance com Redis/memória/disco

## 🏗️ Arquitetura

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   API Gateway   │────│  Task Manager   │────│ Provider Registry│
│  (FastAPI)      │    │  (Universal)    │    │   (Multi-AI)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Queue Service  │    │ Webhook Service │    │  Database       │
│  (Redis/Memory) │    │  (Async notify) │    │  (PostgreSQL)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📊 Tipos de Mídia Suportados

| Tipo | Endpoint | Providers | Status |
|------|----------|-----------|--------|
| **Imagens** | `/v1/media/images/generate` | OpenAI DALL-E, Stability AI | ✅ |
| **Vídeos** | `/v1/media/videos/generate` | RunwayML, Pika Labs | ✅ |
| **Áudio** | `/v1/media/audio/transcribe` | OpenAI Whisper, AssemblyAI | ✅ |
| **Legendas** | `/v1/media/subtitles/generate` | OpenAI GPT, Custom NLP | ✅ |

## 🚀 Início Rápido

### 1. Instalação e Setup

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Configurar banco de dados
python scripts/init_media_tasks.py

# 3. Executar migração Alembic
alembic upgrade head

# 4. Iniciar API
uvicorn app.main:app --reload
```

### 2. Configuração de Environment

```bash
# .env
DATABASE_URL=postgresql://user:pass@localhost/videoai
REDIS_URL=redis://localhost:6379/0

# API Keys (configure conforme provedores desejados)
OPENAI_API_KEY=sk-...
STABILITY_API_KEY=sk-...
ASSEMBLYAI_API_KEY=...
```

### 3. Primeiro Uso

```python
import aiohttp

# 1. Obter token de autenticação
token = "your-jwt-token"

# 2. Criar tarefa de imagem
async with aiohttp.ClientSession() as session:
    async with session.post(
        "http://localhost:8000/api/v1/media/images/generate",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "prompt": "Um gato robô futurista",
            "style": "realistic",
            "size": "1024x1024",
            "webhook_url": "https://myapp.com/webhook"
        }
    ) as response:
        task = await response.json()
        print(f"Tarefa criada: {task['id']}")
```

## 📡 API Reference

### Endpoints Principais

#### Geração de Imagens
```http
POST /api/v1/media/images/generate
Content-Type: application/json
Authorization: Bearer <token>

{
  "prompt": "string",
  "style": "realistic|artistic|anime",
  "size": "512x512|1024x1024|1024x1792",
  "quality": "standard|hd",
  "n": 1,
  "webhook_url": "https://example.com/webhook",
  "priority": "low|medium|high|urgent",
  "metadata": {}
}
```

#### Geração de Vídeos
```http
POST /api/v1/media/videos/generate
Content-Type: application/json
Authorization: Bearer <token>

{
  "prompt": "string",
  "duration": 5,
  "style": "cinematic|documentary|artistic",
  "fps": 24,
  "resolution": "720p|1080p|4k",
  "webhook_url": "https://example.com/webhook",
  "priority": "medium",
  "metadata": {}
}
```

#### Transcrição de Áudio
```http
POST /api/v1/media/audio/transcribe
Content-Type: application/json
Authorization: Bearer <token>

{
  "audio_url": "https://example.com/audio.mp3",
  "language": "pt|en|es|fr",
  "model": "whisper-1|best",
  "response_format": "json|text|srt|vtt",
  "webhook_url": "https://example.com/webhook",
  "priority": "medium",
  "metadata": {}
}
```

#### Geração de Legendas
```http
POST /api/v1/media/subtitles/generate
Content-Type: application/json
Authorization: Bearer <token>

{
  "text": "string",
  "target_language": "en|es|fr|de",
  "format": "srt|vtt|ass",
  "timing_mode": "auto|manual",
  "webhook_url": "https://example.com/webhook",
  "priority": "low",
  "metadata": {}
}
```

### Monitoramento

#### Status da Tarefa
```http
GET /api/v1/media/tasks/{task_id}
Authorization: Bearer <token>
```

#### Listar Tarefas
```http
GET /api/v1/media/tasks?task_type=image_generation&status=completed&limit=50
Authorization: Bearer <token>
```

#### Estatísticas
```http
GET /api/v1/media/statistics
Authorization: Bearer <token>
```

#### Health Check
```http
GET /api/v1/media/health
```

### Batch Processing

#### Criar Lote
```http
POST /api/v1/media/batch
Content-Type: application/json
Authorization: Bearer <token>

[
  {
    "task_type": "image_generation",
    "input_data": {...},
    "priority": "medium"
  },
  // ... até 50 tarefas
]
```

## 🔔 Sistema de Webhooks

### Configuração

```python
# Ao criar tarefa, especifique webhook_url
{
    "prompt": "...",
    "webhook_url": "https://myapp.com/webhook",
    "webhook_secret": "optional-secret-for-verification"
}
```

### Eventos Suportados

| Evento | Descrição |
|--------|-----------|
| `task.created` | Tarefa criada |
| `task.started` | Processamento iniciado |
| `task.progress` | Atualização de progresso |
| `task.completed` | Tarefa concluída com sucesso |
| `task.failed` | Tarefa falhou |
| `task.cancelled` | Tarefa cancelada |

### Payload do Webhook

```json
{
  "event_type": "task.completed",
  "task_id": "task_123",
  "timestamp": "2024-01-01T12:00:00Z",
  "data": {
    "status": "completed",
    "type": "image_generation",
    "progress": 1.0,
    "output_data": {
      "image_url": "https://...",
      "metadata": {}
    }
  },
  "user_id": "user_123",
  "metadata": {}
}
```

### Verificação de Assinatura

```python
import hmac
import hashlib

def verify_webhook(payload, signature, secret):
    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(f"sha256={expected}", signature)
```

## 🔧 Configuração de Provedores

### Provider Registry

```python
from app.services.provider_registry import provider_registry

# Registrar provedor customizado
custom_provider = MyCustomProvider(
    name="my_provider",
    api_key="secret",
    config={"model": "custom-v1"}
)

provider_registry.register_provider(custom_provider)
```

### Estratégias de Seleção

- **Quality**: Melhor qualidade de output
- **Speed**: Menor tempo de processamento
- **Cost**: Menor custo por tarefa
- **Reliability**: Maior taxa de sucesso
- **Load Balancing**: Distribuição de carga

## 📈 Monitoramento e Métricas

### Métricas Disponíveis

- **Taxa de Sucesso**: % de tarefas concluídas com sucesso
- **Tempo Médio**: Duração média por tipo de tarefa
- **Custo Total**: Gastos acumulados por provedor
- **Fila**: Tarefas pendentes por prioridade
- **Provider Health**: Status de cada provedor

### Logs Estruturados

```python
import logging

logger = logging.getLogger("videoai.tasks")

# Logs automáticos incluem:
# - Task lifecycle events
# - Provider responses
# - Webhook deliveries
# - Error details com stack traces
```

### Health Checks

```bash
# Verificar status geral
curl http://localhost:8000/api/v1/media/health

# Verificar provedores específicos
curl http://localhost:8000/api/v1/media/providers
```

## 🔄 Sistema de Retry

### Configuração Automática

- **Exponential Backoff**: 30s → 5m → 30m → 2h → 24h
- **Max Retries**: 3 tentativas por padrão
- **Retry Conditions**: Falhas temporárias, rate limits, timeouts
- **Skip Conditions**: Erros de validação, problemas de autenticação

### Retry Manual

```http
POST /api/v1/media/tasks/{task_id}/retry
Authorization: Bearer <token>
```

## 💾 Cache Multicamadas

### Estratégia de Cache

1. **L1 - Memória**: Resultados frequentes (TTL: 1h)
2. **L2 - Redis**: Cache distribuído (TTL: 24h) 
3. **L3 - Disco**: Cache persistente (TTL: 7d)

### Invalidação

```python
# Cache é invalidado automaticamente quando:
# - Parâmetros de entrada mudam
# - TTL expira
# - Cache fica cheio (LRU eviction)
```

## 🧪 Testes

### Executar Testes

```bash
# Setup inicial
python scripts/init_media_tasks.py

# Testes de integração
python examples/media_tasks_example.py

# Testes unitários
python -m pytest tests/
```

### Exemplo Completo

```python
# Ver: examples/media_tasks_example.py
# Inclui:
# - Criação de tarefas
# - Monitoramento de progresso
# - Processamento em lote
# - Servidor webhook
# - Tratamento de erros
```

## 🚀 Deployment

### Docker

```dockerfile
# Dockerfile já configurado
FROM python:3.11-slim

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose

```yaml
# docker-compose.yml atualizado inclui:
# - API Service
# - PostgreSQL
# - Redis
# - Workers assíncronos
```

### Produção

```bash
# 1. Configurar environment variables
export DATABASE_URL=postgresql://...
export REDIS_URL=redis://...
export OPENAI_API_KEY=...

# 2. Executar migrações
alembic upgrade head

# 3. Iniciar serviços
docker-compose up -d

# 4. Verificar health
curl http://localhost:8000/api/v1/media/health
```

## 📚 Exemplos de Uso

### Integração com Frontend

```javascript
// React/Next.js
const createImageTask = async (prompt) => {
  const response = await fetch('/api/v1/media/images/generate', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      prompt,
      webhook_url: `${window.location.origin}/webhook`
    })
  });
  
  return response.json();
};
```

### Webhook Handler

```python
# FastAPI webhook receiver
@app.post("/webhook")
async def handle_webhook(payload: WebhookPayload):
    if payload.event_type == "task.completed":
        # Notificar usuário via WebSocket
        await websocket_manager.send_message(
            payload.user_id,
            {"type": "task_completed", "data": payload.data}
        )
    
    return {"status": "received"}
```

## 🔒 Segurança

### Autenticação

- **JWT Tokens**: Autenticação baseada em tokens
- **Rate Limiting**: Limite por usuário/endpoint
- **Webhook Signatures**: Verificação HMAC SHA256

### Validação

- **Input Sanitization**: Validação rigorosa de entradas
- **File Size Limits**: Limites de tamanho para uploads
- **Content Filtering**: Filtros de conteúdo inapropriado

## 📖 Roadmap

### Próximas Funcionalidades

- [ ] **Multi-tenancy**: Isolamento completo por tenant
- [ ] **Advanced Scheduling**: Agendamento de tarefas
- [ ] **Cost Analytics**: Dashboard de custos detalhado
- [ ] **A/B Testing**: Testes de provedores automáticos
- [ ] **Custom Models**: Suporte a modelos fine-tuned
- [ ] **Workflow Engine**: Pipelines de processamento complexos

## 🆘 Troubleshooting

### Problemas Comuns

#### Tarefas ficam presas em "processing"
```bash
# Verificar health dos provedores
curl http://localhost:8000/api/v1/media/providers

# Verificar logs
docker logs videoai-api

# Reiniciar workers
docker-compose restart worker
```

#### Webhooks não chegam
```bash
# Verificar status de entrega
curl http://localhost:8000/api/v1/media/webhooks/{webhook_id}/status

# Verificar webhook worker
curl http://localhost:8000/api/v1/media/webhooks/statistics
```

#### Performance lenta
```bash
# Verificar cache
curl http://localhost:8000/api/v1/media/cache/stats

# Monitorar Redis
redis-cli monitor
```

## 📞 Suporte

- **Documentação**: `/docs` (Swagger UI)
- **Health Check**: `/api/v1/media/health`
- **Logs**: `docker logs videoai-api`
- **Métricas**: `/api/v1/media/statistics`

---

**Sistema implementado com sucesso na Tarefa 3.2! 🎉**

**Componentes entregues:**
- ✅ API unificada com 4 tipos de mídia
- ✅ Sistema assíncrono completo
- ✅ Webhooks robustos com retry
- ✅ Provider registry inteligente
- ✅ Monitoramento completo
- ✅ Batch processing otimizado
- ✅ Documentação completa
- ✅ Exemplos funcionais 