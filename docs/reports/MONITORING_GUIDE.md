# Guia de Monitoramento - VideoAI

Este guia descreve como monitorar RabbitMQ e Redis usando suas interfaces nativas.

## 📊 RabbitMQ Management

### Acesso à Interface Web

O RabbitMQ Management está disponível em: **http://localhost:15672**

**Credenciais padrão:**
- Username: `guest`
- Password: `guest`

### Principais Métricas a Monitorar

1. **Overview (Página Inicial)**
   - Taxa de mensagens (msg/s)
   - Número de conexões ativas
   - Uso de memória e disco

2. **Queues Tab**
   - `ai_processing` - Fila de alta prioridade (AI)
   - `image_processing` - Fila de prioridade média
   - `video_processing` - Fila de baixa prioridade
   - `social_media` - Fila de baixa prioridade
   - `default` - Fila padrão

   **Métricas por fila:**
   - Messages ready (mensagens aguardando processamento)
   - Messages unacked (mensagens sendo processadas)
   - Message rates (taxa de entrada/saída)

3. **Connections Tab**
   - Conexões ativas dos workers Celery
   - Taxa de transferência por conexão

### Comandos CLI Úteis

```bash
# Verificar status do RabbitMQ
docker exec -it rabbitmq rabbitmqctl status

# Listar filas
docker exec -it rabbitmq rabbitmqctl list_queues name messages consumers

# Listar exchanges
docker exec -it rabbitmq rabbitmqctl list_exchanges

# Ver estatísticas detalhadas de uma fila
docker exec -it rabbitmq rabbitmqctl list_queues name messages_ready messages_unacknowledged
```

## 🔴 Redis Monitoring

### Redis CLI

Acesse o Redis CLI:
```bash
docker exec -it redis redis-cli
```

### Comandos Essenciais

```bash
# Informações gerais do servidor
INFO

# Estatísticas de memória
INFO memory

# Número de clientes conectados
INFO clients

# Estatísticas de persistência
INFO persistence

# Listar todas as keys (cuidado em produção!)
KEYS *

# Ver tipo de uma key
TYPE key_name

# Ver TTL de uma key
TTL key_name

# Tamanho de uma lista/set
LLEN celery  # para listas
SCARD key_name  # para sets

# Monitor em tempo real (cuidado - verbose!)
MONITOR
```

### Monitoramento de Filas Celery

```bash
# Ver tamanho das filas no Redis
docker exec -it redis redis-cli LLEN celery

# Ver keys relacionadas ao Celery
docker exec -it redis redis-cli KEYS "celery*"

# Ver resultado de uma task específica
docker exec -it redis redis-cli GET celery-task-meta-{task-id}
```

## 🌸 Flower (Celery Monitoring)

O Flower já está configurado e disponível em: **http://localhost:5555**

### Principais Recursos

1. **Dashboard**
   - Workers ativos
   - Tarefas em execução
   - Taxa de processamento

2. **Tasks**
   - Histórico de tarefas
   - Status (SUCCESS, FAILURE, PENDING)
   - Tempo de execução
   - Resultados e exceções

3. **Workers**
   - Workers online/offline
   - Consumo de CPU/memória por worker
   - Tarefas processadas por worker

4. **Broker**
   - Estatísticas das filas
   - Mensagens pendentes

## 📝 Checklist de Monitoramento

### Verificações Diárias

- [ ] RabbitMQ: Verificar se todas as filas estão sendo consumidas
- [ ] RabbitMQ: Checar taxa de crescimento das filas
- [ ] Redis: Verificar uso de memória (< 75%)
- [ ] Flower: Confirmar todos os workers online
- [ ] Flower: Revisar tarefas com falha

### Alertas para Configurar (Futuro)

1. **Fila crescendo demais**: Mais de 1000 mensagens pendentes
2. **Worker offline**: Algum worker parou
3. **Memória Redis**: Uso acima de 80%
4. **Taxa de falha**: Mais de 5% de tarefas falhando

## 🚀 Scripts de Monitoramento Rápido

### status_check.sh

```bash
#!/bin/bash
echo "=== RabbitMQ Status ==="
docker exec -it rabbitmq rabbitmqctl list_queues name messages consumers

echo -e "\n=== Redis Memory ==="
docker exec -it redis redis-cli INFO memory | grep used_memory_human

echo -e "\n=== Celery Workers ==="
docker exec -it videoai_app celery -A app.core.celery inspect active

echo -e "\n=== Container Status ==="
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

### URLs de Acesso Rápido

- **RabbitMQ Management**: http://localhost:15672 (guest/guest)
- **Flower (Celery)**: http://localhost:5555
- **Redis Commander** (se instalar): http://localhost:8081

## 📊 Métricas Importantes

### Performance
- **Throughput**: Mensagens processadas por segundo
- **Latência**: Tempo médio de processamento por tarefa
- **Queue Depth**: Tamanho das filas (deve ser baixo)

### Saúde
- **Worker Availability**: Todos os workers devem estar online
- **Memory Usage**: Redis < 75%, RabbitMQ < 80%
- **Error Rate**: Taxa de falha < 1%

### Capacidade
- **Active Connections**: Número de conexões ativas
- **Task Backlog**: Tarefas aguardando processamento
- **Processing Time**: Tempo médio por tipo de tarefa

---

Este monitoramento básico é suficiente para acompanhar a saúde do sistema. Para ambientes de produção, considere ferramentas mais avançadas como Prometheus + Grafana. 