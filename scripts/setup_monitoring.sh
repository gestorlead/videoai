#!/bin/bash

# VideoAI Monitoring Setup Script
# Configura stack completa de monitoramento open source

set -e

echo "🚀 Configurando VideoAI Monitoring Stack..."

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para print colorido
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

# Verificar se Docker está rodando
print_header "Verificando Dependências"
if ! docker info > /dev/null 2>&1; then
    print_error "Docker não está rodando. Inicie o Docker primeiro."
    exit 1
fi
print_status "Docker está rodando ✓"

if ! command -v docker-compose &> /dev/null; then
    print_error "docker-compose não encontrado. Instale docker-compose primeiro."
    exit 1
fi
print_status "docker-compose encontrado ✓"

# Parar containers existentes se estiverem rodando
print_header "Parando Containers Existentes"
docker-compose -f docker-compose.monitoring.yml down 2>/dev/null || true
print_status "Containers parados ✓"

# Iniciar stack de monitoramento
print_header "Iniciando Stack de Monitoramento"
print_status "Baixando imagens Docker..."
docker-compose -f docker-compose.monitoring.yml pull

print_status "Iniciando serviços..."
docker-compose -f docker-compose.monitoring.yml up -d

# Aguardar serviços ficarem prontos
print_header "Aguardando Serviços"
print_status "Aguardando Prometheus..."
timeout 60 bash -c 'until curl -s http://localhost:9090/-/ready > /dev/null; do sleep 2; done' || {
    print_warning "Prometheus demorou para ficar pronto, mas continuando..."
}

print_status "Aguardando Grafana..."
timeout 60 bash -c 'until curl -s http://localhost:3000/api/health > /dev/null; do sleep 2; done' || {
    print_warning "Grafana demorou para ficar pronto, mas continuando..."
}

# Verificar status dos containers
print_header "Status dos Serviços"
services=(
    "videoai_prometheus:9090"
    "videoai_grafana:3000" 
    "videoai_jaeger:16686"
    "videoai_loki:3100"
    "videoai_pyroscope:4040"
    "videoai_alertmanager:9093"
)

all_healthy=true
for service in "${services[@]}"; do
    container_name=$(echo $service | cut -d: -f1)
    port=$(echo $service | cut -d: -f2)
    
    if docker ps --format "table {{.Names}}" | grep -q "$container_name"; then
        print_status "$container_name está rodando ✓"
    else
        print_error "$container_name não está rodando"
        all_healthy=false
    fi
done

# Mostrar URLs de acesso
print_header "URLs de Acesso"
echo -e "${BLUE}📊 Grafana:${NC}        http://localhost:3000 (admin/admin123)"
echo -e "${BLUE}📈 Prometheus:${NC}     http://localhost:9090"
echo -e "${BLUE}🔍 Jaeger:${NC}         http://localhost:16686"
echo -e "${BLUE}📋 Loki:${NC}           http://localhost:3100"
echo -e "${BLUE}🔥 Pyroscope:${NC}      http://localhost:4040"
echo -e "${BLUE}🚨 AlertManager:${NC}   http://localhost:9093"

if [[ "$all_healthy" == true ]]; then
    print_status "🎉 Setup completo! Todos os serviços estão rodando."
    echo ""
    print_status "Próximos passos:"
    echo "1. Acesse o Grafana em http://localhost:3000 (admin/admin123)"
    echo "2. Configure dashboards personalizados"
    echo "3. Instrumente sua aplicação VideoAI com OpenTelemetry"
    echo "4. Configure alertas no AlertManager"
else
    print_warning "⚠️  Setup concluído mas alguns serviços podem não estar funcionando corretamente."
    print_warning "Verifique os logs com: docker-compose -f docker-compose.monitoring.yml logs"
fi

print_header "Economia Estimada"
echo -e "${GREEN}💰 Custo com soluções pagas:${NC} $600-1200/ano"
echo -e "${GREEN}💰 Custo com esta solução:${NC}  $0/ano"
echo -e "${GREEN}💰 Economia anual:${NC}          $600-1200"

echo ""
print_status "VideoAI Monitoring Stack configurado com sucesso! 🚀"
