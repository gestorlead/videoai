"""
Configurações otimizadas para Celery
Baseado em análise de performance e melhores práticas
"""

# Configurações recomendadas para otimização

CELERY_OPTIMIZATIONS = {
    # Worker Configurations
    "worker_prefetch_multiplier": 4,  # Reduz para evitar que um worker pegue muitas tarefas
    "worker_max_tasks_per_child": 1000,  # Reinicia worker após N tarefas (evita memory leaks)
    "worker_disable_rate_limits": True,  # Desabilita rate limiting para melhor performance
    
    # Task Execution
    "task_acks_late": True,  # Acknowledges apenas após conclusão (mais seguro)
    "task_reject_on_worker_lost": True,  # Rejeita tarefas se worker morrer
    "task_time_limit": 300,  # 5 minutos - hard limit
    "task_soft_time_limit": 240,  # 4 minutos - soft limit (permite cleanup)
    
    # Result Backend
    "result_expires": 3600,  # Resultados expiram em 1 hora
    "result_compression": "gzip",  # Comprime resultados grandes
    "result_chord_retry_interval": 1.0,  # Intervalo de retry para chord tasks
    
    # Serialization
    "task_serializer": "json",  # Mais rápido que pickle
    "result_serializer": "json",
    "accept_content": ["json"],  # Aceita apenas JSON (mais seguro)
    
    # Broker Connection
    "broker_connection_retry": True,  # Retry automático de conexão
    "broker_connection_retry_on_startup": True,
    "broker_connection_max_retries": 10,
    "broker_pool_limit": 10,  # Pool de conexões com broker
    
    # Redis Specific (if using Redis as broker)
    "redis_max_connections": 20,
    "redis_socket_keepalive": True,
    "redis_socket_keepalive_options": {
        1: 3,  # TCP_KEEPIDLE
        2: 3,  # TCP_KEEPINTVL
        3: 3,  # TCP_KEEPCNT
    },
    
    # Performance Tuning by Queue
    "queue_optimizations": {
        "ai_processing": {
            "prefetch_multiplier": 1,  # AI tasks são pesadas, 1 por vez
            "max_retries": 3,
            "default_retry_delay": 60,
        },
        "image_processing": {
            "prefetch_multiplier": 2,
            "max_retries": 5,
            "default_retry_delay": 30,
        },
        "video_processing": {
            "prefetch_multiplier": 1,  # Vídeos são muito pesados
            "max_retries": 2,
            "default_retry_delay": 120,
        },
        "social_media": {
            "prefetch_multiplier": 10,  # Tasks leves, mais paralelismo
            "max_retries": 3,
            "default_retry_delay": 30,
        },
        "default": {
            "prefetch_multiplier": 4,
            "max_retries": 3,
            "default_retry_delay": 60,
        }
    },
    
    # Monitoring & Logging
    "worker_send_task_events": True,  # Envia eventos para monitoramento
    "task_send_sent_event": True,  # Evento quando tarefa é enviada
    "task_track_started": True,  # Track quando tarefa inicia
    
    # Beat Schedule (if using periodic tasks)
    "beat_schedule_filename": "celerybeat-schedule",
    "beat_max_loop_interval": 300,  # 5 minutos
}

# Configuração de workers por tipo de fila
WORKER_CONFIGURATIONS = {
    "ai_worker": {
        "concurrency": 2,  # Poucos workers para AI (CPU/GPU intensive)
        "pool": "prefork",  # Melhor para CPU-bound
        "queues": ["ai_processing"],
        "max_memory_per_child": 2048000,  # 2GB por processo
    },
    "image_worker": {
        "concurrency": 4,  # Médio paralelismo
        "pool": "prefork",
        "queues": ["image_processing"],
        "max_memory_per_child": 1024000,  # 1GB por processo
    },
    "video_worker": {
        "concurrency": 2,  # Poucos workers (muito pesado)
        "pool": "prefork",
        "queues": ["video_processing"],
        "max_memory_per_child": 4096000,  # 4GB por processo
    },
    "social_worker": {
        "concurrency": 10,  # Alto paralelismo (I/O bound)
        "pool": "gevent",  # Melhor para I/O-bound
        "queues": ["social_media"],
        "max_memory_per_child": 512000,  # 512MB por processo
    },
    "default_worker": {
        "concurrency": 6,
        "pool": "prefork",
        "queues": ["default"],
        "max_memory_per_child": 1024000,  # 1GB por processo
    }
}

# Comandos para iniciar workers otimizados
WORKER_COMMANDS = {
    "ai_worker": """
    celery -A app.core.celery worker \
        --loglevel=info \
        --concurrency=2 \
        --pool=prefork \
        --queues=ai_processing \
        --max-memory-per-child=2048000 \
        --prefetch-multiplier=1 \
        -n ai_worker@%h
    """,
    
    "image_worker": """
    celery -A app.core.celery worker \
        --loglevel=info \
        --concurrency=4 \
        --pool=prefork \
        --queues=image_processing \
        --max-memory-per-child=1024000 \
        --prefetch-multiplier=2 \
        -n image_worker@%h
    """,
    
    "video_worker": """
    celery -A app.core.celery worker \
        --loglevel=info \
        --concurrency=2 \
        --pool=prefork \
        --queues=video_processing \
        --max-memory-per-child=4096000 \
        --prefetch-multiplier=1 \
        -n video_worker@%h
    """,
    
    "social_worker": """
    celery -A app.core.celery worker \
        --loglevel=info \
        --concurrency=10 \
        --pool=gevent \
        --queues=social_media \
        --max-memory-per-child=512000 \
        --prefetch-multiplier=10 \
        -n social_worker@%h
    """,
    
    "default_worker": """
    celery -A app.core.celery worker \
        --loglevel=info \
        --concurrency=6 \
        --pool=prefork \
        --queues=default \
        --max-memory-per-child=1024000 \
        --prefetch-multiplier=4 \
        -n default_worker@%h
    """
}

# RabbitMQ Optimizations
RABBITMQ_OPTIMIZATIONS = """
# Adicionar ao rabbitmq.conf:

# Performance
vm_memory_high_watermark.relative = 0.6
disk_free_limit.absolute = 5GB

# Networking
tcp_listen_options.backlog = 512
tcp_listen_options.nodelay = true
tcp_listen_options.linger.on = true
tcp_listen_options.linger.timeout = 0

# Management Plugin
management.rates_mode = basic
"""

# Redis Optimizations  
REDIS_OPTIMIZATIONS = """
# Adicionar ao redis.conf:

# Persistence (escolher um)
# Para performance máxima (risco de perda de dados):
save ""
appendonly no

# Para balance entre performance e durabilidade:
save 900 1
save 300 10
save 60 10000
appendonly yes
appendfsync everysec

# Memory
maxmemory 2gb
maxmemory-policy allkeys-lru

# Performance
tcp-keepalive 60
timeout 300

# Disable slow commands in production
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command KEYS ""
"""

def get_optimized_celery_config():
    """Retorna configuração otimizada do Celery"""
    from app.core.config import settings
    
    config = {
        "broker_url": settings.CELERY_BROKER_URL,
        "result_backend": settings.CELERY_RESULT_BACKEND,
        **CELERY_OPTIMIZATIONS
    }
    
    # Remove queue_optimizations do config principal
    config.pop("queue_optimizations", None)
    
    return config

def print_optimization_summary():
    """Imprime resumo das otimizações"""
    print("🚀 OTIMIZAÇÕES CELERY RECOMENDADAS")
    print("=" * 50)
    
    print("\n📊 Configurações por Tipo de Worker:")
    for worker_type, config in WORKER_CONFIGURATIONS.items():
        print(f"\n{worker_type}:")
        print(f"  - Concorrência: {config['concurrency']}")
        print(f"  - Pool: {config['pool']}")
        print(f"  - Filas: {config['queues']}")
        print(f"  - Memória máxima: {config['max_memory_per_child'] / 1024000:.1f}GB")
    
    print("\n\n💡 Principais Otimizações:")
    print("1. Workers especializados por tipo de tarefa")
    print("2. Prefetch multiplier ajustado por carga")
    print("3. Memory limits para evitar leaks")
    print("4. Pool types otimizados (prefork vs gevent)")
    print("5. Task timeouts configurados")
    print("6. Serialização JSON (mais rápida)")
    
    print("\n\n📝 Para aplicar:")
    print("1. Atualize app/core/celery.py com as configurações")
    print("2. Use os comandos de worker otimizados")
    print("3. Configure RabbitMQ e Redis conforme sugerido")
    print("4. Monitore com Flower após as mudanças")

if __name__ == "__main__":
    print_optimization_summary() 