#!/bin/bash

# Script de monitoramento rápido para VideoAI
# Verifica status de RabbitMQ, Redis, Celery e containers

echo "========================================="
echo "   VideoAI - Status Check"
echo "   $(date)"
echo "========================================="

echo -e "\n📊 RabbitMQ Queue Status:"
echo "-----------------------------------------"
docker exec rabbitmq rabbitmqctl list_queues name messages consumers 2>/dev/null || echo "RabbitMQ não está acessível"

echo -e "\n🔴 Redis Memory Usage:"
echo "-----------------------------------------"
docker exec redis redis-cli INFO memory 2>/dev/null | grep -E "used_memory_human|used_memory_peak_human|maxmemory_human" || echo "Redis não está acessível"

echo -e "\n📦 Redis Keys Summary:"
echo "-----------------------------------------"
docker exec redis redis-cli --scan --pattern "*" 2>/dev/null | wc -l | xargs echo "Total de keys:" || echo "Não foi possível contar keys"
docker exec redis redis-cli KEYS "celery*" 2>/dev/null | wc -l | xargs echo "Keys do Celery:" || echo "0"

echo -e "\n👷 Celery Workers Status:"
echo "-----------------------------------------"
docker exec videoai_app celery -A app.core.celery inspect stats 2>/dev/null | grep -A 5 "celery@" || echo "Workers não estão acessíveis"

echo -e "\n🐳 Container Status:"
echo "-----------------------------------------"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "videoai|rabbitmq|redis|postgres"

echo -e "\n🌐 Service URLs:"
echo "-----------------------------------------"
echo "RabbitMQ Management: http://localhost:15672 (guest/guest)"
echo "Flower (Celery):     http://localhost:5555"
echo "FastAPI:             http://localhost:8000"
echo "API Docs:            http://localhost:8000/docs"

echo -e "\n✅ Quick Health Check:"
echo "-----------------------------------------"
# Verificar se os serviços principais estão rodando
services=("rabbitmq" "redis" "postgres" "videoai_app")
all_healthy=true

for service in "${services[@]}"; do
    if docker ps | grep -q "$service"; then
        echo "✅ $service está rodando"
    else
        echo "❌ $service NÃO está rodando"
        all_healthy=false
    fi
done

if [ "$all_healthy" = true ]; then
    echo -e "\n🎉 Todos os serviços estão operacionais!"
else
    echo -e "\n⚠️  Alguns serviços precisam de atenção!"
fi

echo -e "\n=========================================" 