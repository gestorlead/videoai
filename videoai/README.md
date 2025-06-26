# AutoSub - API de Processamento de Áudio e Vídeo

![Versão](https://img.shields.io/badge/versão-1.1.0-blue)
![Licença](https://img.shields.io/badge/licença-MIT-green)
![Status](https://img.shields.io/badge/status-ativo-brightgreen)

## 📝 Descrição

O **AutoSub** é uma API robusta para processamento automático de áudio e vídeo com as seguintes funcionalidades:

- **🎵 Processamento de Áudio**: Transcrição automática e tradução de áudios
- **🎬 Processamento de Vídeo**: Aplicação de legendas, logos e overlays
- **✂️ Edição de Vídeo**: Corte e junção automática de múltiplos vídeos
- **🔄 Sistema Assíncrono**: Processamento em fila com monitoramento em tempo real
- **🔐 Autenticação**: Sistema de API Keys para acesso seguro

## 🚀 Início Rápido

### 1. Iniciar a API

```bash
# Clone o repositório
git clone https://github.com/gestorlead/autosub.git
cd autosub

# Inicie com Docker
docker-compose up -d

# A API estará disponível em http://localhost:5000
```

### 2. Obter API Key

```bash
# Execute dentro do container
docker exec -it autosub_app_1 python create_admin_api_key.py

# Sua API Key será exibida - GUARDE-A!
# Exemplo: ak_eZM2SRS6eHHQ37Gl6qPnJkKzoWu29FuJ
```

### 3. Primeiro Teste

```bash
curl -X GET http://localhost:5000/health
# Deve retornar: {"status":"ok","database":true}
```

## 📚 Endpoints da API

### 🔧 Sistema

| Endpoint | Método | Descrição | Auth |
|----------|--------|-----------|------|
| `/health` | GET | Status da aplicação | ❌ |
| `/api/v1/health` | GET | Status detalhado dos serviços | ✅ |

### 🎵 Processamento de Áudio

| Endpoint | Método | Descrição | Auth |
|----------|--------|-----------|------|
| `/api/v1/audio/process` | POST | Processa áudio (transcrição + tradução) | ✅ |
| `/api/v1/audio/status/{job_id}` | GET | Verifica status do processamento | ✅ |
| `/api/v1/audio/download/{job_id}` | GET | Download das legendas | ✅ |
| `/api/v1/audio/job/{job_id}` | DELETE | Remove job | ✅ |

### 🎬 Processamento de Vídeo

| Endpoint | Método | Descrição | Auth |
|----------|--------|-----------|------|
| `/api/v1/video/process-with-overlay` | POST | Adiciona legendas/logo ao vídeo | ✅ |
| `/api/v1/video/status/{job_id}` | GET | Verifica status do processamento | ✅ |
| `/api/v1/video/download/{job_id}` | GET | Download do vídeo processado | ✅ |

### ✂️ Corte e Junção de Vídeos

| Endpoint | Método | Descrição | Auth |
|----------|--------|-----------|------|
| `/api/v1/video/trim-join` | POST | Corta e junta múltiplos vídeos | ✅ |
| `/api/v1/video/trim-join/status/{job_id}` | GET | Verifica status do processamento | ✅ |
| `/api/v1/video/trim-join/download/{job_id}` | GET | Download do vídeo final | ✅ |

### 📥 Download Público

| Endpoint | Método | Descrição | Auth |
|----------|--------|-----------|------|
| `/api/v1/public/video/{job_id}` | GET | Download público (sem API key) | ❌ |

## 💡 Exemplos de Uso

### 🎵 Processamento de Áudio

#### 1. Enviar Áudio para Processamento
```bash
curl -X POST http://localhost:5000/api/v1/audio/process \
  -H "X-API-Key: sua_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "audio_url": "https://example.com/audio.mp3",
    "target_language": "pt"
  }'
```

**Resposta:**
```json
{
  "job_id": "abc123",
  "status": "queued",
  "message": "Áudio enviado para processamento com sucesso"
}
```

#### 2. Verificar Status
```bash
curl -X GET http://localhost:5000/api/v1/audio/status/abc123 \
  -H "X-API-Key: sua_api_key"
```

**Resposta:**
```json
{
  "job_id": "abc123",
  "status": "completed",
  "progress": 100,
  "result": {
    "subtitles": {
      "en": {"content": "...", "path": "..."},
      "pt": {"content": "...", "path": "..."}
    }
  }
}
```

#### 3. Download das Legendas
```bash
curl -X GET http://localhost:5000/api/v1/audio/download/abc123?lang=pt \
  -H "X-API-Key: sua_api_key" \
  -o legendas.srt
```

### 🎬 Processamento de Vídeo com Overlay

#### 1. Enviar Vídeo para Processamento
```bash
curl -X POST http://localhost:5000/api/v1/video/process-with-overlay \
  -H "X-API-Key: sua_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://example.com/video.mp4",
    "caption_id": "abc123",
    "language": "pt",
    "position": "bottom",
    "font_size": 24,
    "font_color": "#FFFFFF",
    "background_color": "#000000",
    "background_opacity": 0.7
  }'
```

#### 2. Com Conteúdo de Legenda Direto
```bash
curl -X POST http://localhost:5000/api/v1/video/process-with-overlay \
  -H "X-API-Key: sua_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "https://example.com/video.mp4",
    "subtitle_content": "1\n00:00:00,000 --> 00:00:03,000\nOlá mundo!",
    "position": "bottom"
  }'
```

### ✂️ Corte e Junção de Vídeos

#### 1. Processar Multiple Takes
```bash
curl -X POST http://localhost:5000/api/v1/video/trim-join \
  -H "X-API-Key: sua_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "processed_takes": [
      {
        "take_number": 1,
        "video_url": "https://example.com/take1.mp4",
        "final_clip_duration": 4.5
      },
      {
        "take_number": 2,
        "video_url": "https://example.com/take2.mp4", 
        "final_clip_duration": 3.2
      }
    ]
  }'
```

**Resposta:**
```json
{
  "job_id": "def456",
  "status": "queued",
  "message": "Vídeos enviados para corte e junção com sucesso",
  "estimated_time": "20-40 segundos",
  "takes_count": 2,
  "public_download_url": "/api/v1/public/video/def456"
}
```

### 📊 Monitoramento de Progresso

```bash
# Verificar status
curl -X GET http://localhost:5000/api/v1/video/trim-join/status/def456 \
  -H "X-API-Key: sua_api_key"

# Resposta com progresso
{
  "job_id": "def456",
  "status": "processing",
  "progress": 45,
  "updated_at": "2024-01-01T10:30:00"
}
```

## 🔐 Autenticação

Todas as rotas da API (exceto públicas) requerem autenticação via API Key:

```bash
# Header obrigatório
X-API-Key: sua_chave_api
```

**Como obter API Key:**
```bash
# Dentro do container
docker exec -it autosub_app_1 python create_admin_api_key.py
```

## ⚙️ Configuração

### Variáveis de Ambiente

```bash
# .env
OPENAI_API_KEY=sk-...                    # Para transcrição
DATABASE_URL=postgresql://...            # Banco de dados
REDIS_URL=redis://redis:6379             # Cache e jobs
RABBITMQ_URL=amqp://admin:admin123@...   # Fila de processamento
UPLOAD_FOLDER=/app/uploads               # Pasta de uploads
```

### Parâmetros de Vídeo

| Parâmetro | Tipo | Descrição | Padrão |
|-----------|------|-----------|--------|
| `position` | string | Posição da legenda (top/center/bottom) | bottom |
| `font_size` | number | Tamanho da fonte | 20 |
| `font_color` | string | Cor da fonte (hex) | #FFFFFF |
| `background_color` | string | Cor do fundo (hex) | #000000 |
| `background_opacity` | number | Opacidade do fundo (0-1) | 0.5 |
| `outline_width` | number | Largura da borda | 2 |
| `outline_color` | string | Cor da borda (hex) | #000000 |
| `subtitle_height` | number/string | Altura personalizada | auto |

## 🐳 Docker

### Iniciar Todos os Serviços
```bash
docker-compose up -d
```

### Verificar Status
```bash
docker ps
# Deve mostrar: app, db, rabbitmq, redis
```

### Logs
```bash
# Logs da aplicação
docker logs -f autosub_app_1

# Logs do worker
docker exec autosub_app_1 tail -f /var/log/worker.log
```

### Reiniciar
```bash
# Reiniciar apenas a aplicação
docker restart autosub_app_1

# Reiniciar tudo
docker-compose restart
```

## 📊 Monitoramento

### Health Check
```bash
curl http://localhost:5000/health
```

### Status dos Serviços
```bash
curl -H "X-API-Key: sua_chave" http://localhost:5000/api/v1/health
```

### Interface do RabbitMQ
- URL: http://localhost:15672
- Usuário: admin
- Senha: admin123

## 🔧 Desenvolvimento

### Estrutura do Projeto
```
autosub/
├── api/                    # Módulos da API
│   ├── routes.py          # Endpoints
│   ├── queue_service.py   # Gerenciamento de filas
│   ├── redis_service.py   # Cache e status
│   ├── audio_processor.py # Processamento de áudio
│   └── video_processor.py # Processamento de vídeo
├── src/                   # Código principal
│   ├── models/           # Modelos de dados
│   ├── utils/            # Utilitários
│   └── migrations/       # Migrações do banco
├── docs/                 # Documentação
├── uploads/              # Arquivos processados
├── worker.py            # Worker de áudio
├── video_worker.py      # Worker de vídeo
└── app.py              # Aplicação principal
```

### Adicionando Novos Endpoints
1. Edite `api/routes.py`
2. Adicione validação de entrada
3. Implemente processamento assíncrono
4. Atualize documentação

### Debugging
```bash
# Logs detalhados
docker logs --tail 50 autosub_app_1

# Executar comandos no container
docker exec -it autosub_app_1 bash

# Verificar filas
docker exec -it autosub_rabbitmq_1 rabbitmqctl list_queues
```

## 🚨 Solução de Problemas

### Erro de Conectividade com RabbitMQ
```bash
# Verificar se o RabbitMQ está rodando
docker ps | grep rabbitmq

# Verificar credenciais no .env
cat .env | grep RABBITMQ_URL

# Deve ser: amqp://admin:admin123@rabbitmq:5672/
```

### Erro 404 Not Found
- Verifique se a API key está correta
- Confirme se o endpoint existe (consulte esta documentação)
- Verifique se o container está rodando

### Job Fica "Stuck"
```bash
# Verificar workers
docker exec autosub_app_1 ps aux | grep worker

# Reiniciar se necessário
docker restart autosub_app_1
```

## 📄 Licença

MIT License - veja [LICENSE](LICENSE) para detalhes.

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request

---

**🎉 Pronto para usar! A API está documentada e funcionando.**
