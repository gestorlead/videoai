#!/bin/bash

echo "🐳 Iniciando VideoAI no Docker com Health Checks..."

# Função para parar todos os processos em caso de interrupção
cleanup() {
    echo "🛑 Parando todos os processos..."
    kill $AUDIO_WORKER_PID $VIDEO_WORKER_PID $APP_PID 2>/dev/null
    exit 0
}

# Capturar sinais para limpeza
trap cleanup SIGINT SIGTERM

# Função para aguardar RabbitMQ estar pronto
wait_for_rabbitmq() {
    echo "⏳ Aguardando RabbitMQ estar pronto..."
    
    local rabbitmq_host="${RABBITMQ_HOST:-rabbitmq}"
    local rabbitmq_port="${RABBITMQ_PORT:-5672}"
    local rabbitmq_user="${RABBITMQ_USER:-admin}"
    local rabbitmq_pass="${RABBITMQ_PASS:-admin123}"
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        echo "🔄 Tentativa $attempt/$max_attempts de conexão com RabbitMQ..."
        
        # Tentar conectar usando Python
        python3 -c "
import socket
import sys

try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    result = s.connect_ex(('$rabbitmq_host', $rabbitmq_port))
    s.close()
    sys.exit(0 if result == 0 else 1)
except Exception:
    sys.exit(1)
" 2>/dev/null
        
        if [ $? -eq 0 ]; then
            echo "✅ RabbitMQ está respondendo na porta $rabbitmq_port"
            
            # Aguardar mais alguns segundos para garantir que o RabbitMQ está totalmente inicializado
            echo "⏳ Aguardando inicialização completa do RabbitMQ..."
            sleep 5
            return 0
        fi
        
        echo "❌ RabbitMQ não está pronto ainda. Aguardando 2 segundos..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo "🚨 RabbitMQ não ficou pronto após $max_attempts tentativas"
    return 1
}

# Função para aguardar Redis estar pronto
wait_for_redis() {
    echo "⏳ Aguardando Redis estar pronto..."
    
    local redis_host="${REDIS_HOST:-redis}"
    local redis_port="${REDIS_PORT:-6379}"
    local max_attempts=15
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        echo "🔄 Tentativa $attempt/$max_attempts de conexão com Redis..."
        
        python3 -c "
import socket
import sys

try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    result = s.connect_ex(('$redis_host', $redis_port))
    s.close()
    sys.exit(0 if result == 0 else 1)
except Exception:
    sys.exit(1)
" 2>/dev/null
        
        if [ $? -eq 0 ]; then
            echo "✅ Redis está respondendo na porta $redis_port"
            return 0
        fi
        
        echo "❌ Redis não está pronto ainda. Aguardando 2 segundos..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo "🚨 Redis não ficou pronto após $max_attempts tentativas"
    return 1
}

# Aguardar dependências estarem prontas
wait_for_redis
if [ $? -ne 0 ]; then
    echo "🚨 Falha ao conectar com Redis. Abortando..."
    exit 1
fi

wait_for_rabbitmq
if [ $? -ne 0 ]; then
    echo "🚨 Falha ao conectar com RabbitMQ. Abortando..."
    exit 1
fi

# Aguardar mais um pouco para garantir estabilidade
echo "⏳ Aguardando estabilização dos serviços..."
sleep 3

# Iniciar worker de áudio
echo "🎵 Iniciando worker de áudio..."
python3 worker.py &
AUDIO_WORKER_PID=$!

# Aguardar um pouco antes de iniciar o próximo worker
sleep 3

# Iniciar worker de vídeo
echo "🎥 Iniciando worker de vídeo..."
python3 video_worker.py &
VIDEO_WORKER_PID=$!

# Aguardar um pouco antes de iniciar a aplicação
sleep 3

# Iniciar aplicação principal
echo "🚀 Iniciando aplicação principal..."
if [ "$1" = "dev" ]; then
    # Modo desenvolvimento
    python3 app.py &
    APP_PID=$!
else
    # Modo produção com gunicorn
    gunicorn app:app --bind 0.0.0.0:5000 --timeout 300 --workers 2 &
    APP_PID=$!
fi

echo "✅ Todos os processos iniciados:"
echo "   - Worker de áudio (PID: $AUDIO_WORKER_PID)"
echo "   - Worker de vídeo (PID: $VIDEO_WORKER_PID)"
echo "   - Aplicação principal (PID: $APP_PID)"
echo "   - VideoAI rodando em http://localhost:5000"

# Aguardar todos os processos
wait $AUDIO_WORKER_PID $VIDEO_WORKER_PID $APP_PID 