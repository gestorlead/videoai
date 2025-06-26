#!/bin/bash

# Script para iniciar workers Celery otimizados
# Cada worker é configurado especificamente para seu tipo de tarefa

echo "🚀 Iniciando Workers Celery Otimizados"
echo "====================================="

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Função para verificar se um processo está rodando
check_process() {
    if pgrep -f "$1" > /dev/null; then
        echo -e "${GREEN}✅ $2 está rodando${NC}"
        return 0
    else
        echo -e "${RED}❌ $2 não está rodando${NC}"
        return 1
    fi
}

# Parar workers existentes
echo -e "\n${YELLOW}Parando workers existentes...${NC}"
pkill -f "celery worker" || true
sleep 2

# Verificar se RabbitMQ e Redis estão rodando
echo -e "\n${YELLOW}Verificando dependências...${NC}"
if ! docker ps | grep -q "rabbitmq"; then
    echo -e "${RED}❌ RabbitMQ não está rodando!${NC}"
    exit 1
fi

if ! docker ps | grep -q "redis"; then
    echo -e "${RED}❌ Redis não está rodando!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Dependências OK${NC}"

# Diretório do projeto
cd /app

# Iniciar workers especializados
echo -e "\n${YELLOW}Iniciando workers especializados...${NC}"

# AI Worker - Poucos workers, tasks pesadas
echo -e "\n1. Iniciando AI Worker (2 workers, prefetch=1)..."
celery -A app.core.celery worker \
    --loglevel=info \
    --concurrency=2 \
    --pool=prefork \
    --queues=ai_processing \
    --max-memory-per-child=2048000 \
    --prefetch-multiplier=1 \
    -n ai_worker@%h &

sleep 2

# Image Worker - Médio paralelismo
echo -e "\n2. Iniciando Image Worker (4 workers, prefetch=2)..."
celery -A app.core.celery worker \
    --loglevel=info \
    --concurrency=4 \
    --pool=prefork \
    --queues=image_processing \
    --max-memory-per-child=1024000 \
    --prefetch-multiplier=2 \
    -n image_worker@%h &

sleep 2

# Video Worker - Poucos workers, muito pesado
echo -e "\n3. Iniciando Video Worker (2 workers, prefetch=1)..."
celery -A app.core.celery worker \
    --loglevel=info \
    --concurrency=2 \
    --pool=prefork \
    --queues=video_processing \
    --max-memory-per-child=4096000 \
    --prefetch-multiplier=1 \
    -n video_worker@%h &

sleep 2

# Social Media Worker - Alto paralelismo, I/O bound
echo -e "\n4. Iniciando Social Media Worker (8 workers, prefetch=10)..."
celery -A app.core.celery worker \
    --loglevel=info \
    --concurrency=8 \
    --pool=prefork \
    --queues=social_media \
    --max-memory-per-child=512000 \
    --prefetch-multiplier=10 \
    -n social_worker@%h &

sleep 2

# Default Worker - Configuração balanceada
echo -e "\n5. Iniciando Default Worker (6 workers, prefetch=4)..."
celery -A app.core.celery worker \
    --loglevel=info \
    --concurrency=6 \
    --pool=prefork \
    --queues=default \
    --max-memory-per-child=1024000 \
    --prefetch-multiplier=4 \
    -n default_worker@%h &

sleep 3

# Verificar status dos workers
echo -e "\n${YELLOW}Verificando status dos workers...${NC}"
check_process "ai_worker" "AI Worker"
check_process "image_worker" "Image Worker"
check_process "video_worker" "Video Worker"
check_process "social_worker" "Social Worker"
check_process "default_worker" "Default Worker"

# Iniciar Flower para monitoramento
echo -e "\n${YELLOW}Iniciando Flower (monitoramento)...${NC}"
celery -A app.core.celery flower \
    --port=5555 \
    --url_prefix=flower &

sleep 2

if check_process "flower" "Flower"; then
    echo -e "\n${GREEN}🌸 Flower disponível em: http://localhost:5555${NC}"
fi

# Resumo
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Workers Celery Otimizados Iniciados!${NC}"
echo -e "${GREEN}========================================${NC}"

echo -e "\n📊 Configuração dos Workers:"
echo "   - AI Worker: 2 workers (prefetch=1)"
echo "   - Image Worker: 4 workers (prefetch=2)"  
echo "   - Video Worker: 2 workers (prefetch=1)"
echo "   - Social Worker: 8 workers (prefetch=10)"
echo "   - Default Worker: 6 workers (prefetch=4)"

echo -e "\n💡 Total: 22 worker processes"
echo -e "\n📍 URLs de Monitoramento:"
echo "   - Flower: http://localhost:5555"
echo "   - RabbitMQ: http://localhost:15672"

echo -e "\n⚡ Para parar todos os workers:"
echo "   pkill -f 'celery worker'"

# Manter script rodando
echo -e "\n${YELLOW}Workers rodando em background. Use Ctrl+C para sair.${NC}"
wait 