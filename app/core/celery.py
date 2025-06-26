"""
Celery configuration for VideoAI async task processing
Optimized for performance based on load testing
"""
import os
from celery import Celery
from kombu import Queue

# Get configuration from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://admin:admin123@localhost:5672")

# Create Celery instance
celery_app = Celery(
    "videoai",
    broker=RABBITMQ_URL,
    backend=REDIS_URL,
    include=[
        "app.tasks.image_tasks",
        "app.tasks.video_tasks", 
        "app.tasks.social_tasks",
        "app.tasks.ai_tasks",
        "app.tasks.simple_tasks"
    ]
)

# Celery configuration with performance optimizations
celery_app.conf.update(
    # Task routing
    task_routes={
        'app.tasks.image_tasks.*': {'queue': 'image_processing'},
        'app.tasks.video_tasks.*': {'queue': 'video_processing'},
        'app.tasks.social_tasks.*': {'queue': 'social_media'},
        'app.tasks.ai_tasks.*': {'queue': 'ai_processing'},
        'simple_*': {'queue': 'default'},
    },
    
    # Define queues with priorities
    task_queues=[
        Queue('ai_processing', routing_key='ai_processing', priority=3),
        Queue('image_processing', routing_key='image_processing', priority=2),
        Queue('video_processing', routing_key='video_processing', priority=1),
        Queue('social_media', routing_key='social_media', priority=1),
        Queue('default', routing_key='default', priority=2),
    ],
    
    # Task serialization - JSON is faster than pickle
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    
    # Task execution optimizations
    timezone='UTC',
    enable_utc=True,
    task_time_limit=300,  # 5 minutes hard limit
    task_soft_time_limit=240,  # 4 minutes soft limit
    task_acks_late=True,  # Acknowledge only after completion
    task_reject_on_worker_lost=True,  # Reject tasks if worker dies
    
    # Result backend optimizations
    result_expires=3600,  # 1 hour
    result_compression='gzip',  # Compress large results
    result_backend_transport_options={
        'master_name': 'mymaster',
        'visibility_timeout': 3600,
        'fanout_prefix': True,
        'fanout_patterns': True,
    },
    
    # Worker optimizations
    worker_prefetch_multiplier=4,  # Adjusted for better throughput
    worker_max_tasks_per_child=1000,  # Prevent memory leaks
    worker_disable_rate_limits=True,  # Better performance
    worker_send_task_events=True,  # For monitoring
    
    # Connection pool optimizations
    broker_pool_limit=10,
    broker_connection_retry=True,
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=10,
    
    # Redis specific optimizations
    redis_max_connections=20,
    redis_socket_keepalive=True,
    redis_socket_keepalive_options={
        1: 3,  # TCP_KEEPIDLE
        2: 3,  # TCP_KEEPINTVL
        3: 3,  # TCP_KEEPCNT
    },
    
    # Task retry settings per queue type
    task_annotations={
        'app.tasks.ai_tasks.*': {
            'max_retries': 3,
            'default_retry_delay': 60,
        },
        'app.tasks.video_tasks.*': {
            'max_retries': 2,
            'default_retry_delay': 120,
        },
        'app.tasks.image_tasks.*': {
            'max_retries': 5,
            'default_retry_delay': 30,
        },
        'app.tasks.social_tasks.*': {
            'max_retries': 3,
            'default_retry_delay': 30,
        },
    },
    
    # Default retry settings
    task_default_retry_delay=60,
    task_max_retries=3,
    
    # Monitoring optimizations
    task_track_started=True,
    task_send_sent_event=True,
    
    # Beat schedule (for periodic tasks)
    beat_schedule={
        'cleanup-temp-files': {
            'task': 'app.tasks.maintenance.cleanup_temp_files',
            'schedule': 300.0,  # Every 5 minutes
        },
        'update-social-tokens': {
            'task': 'app.tasks.social_tasks.refresh_tokens',
            'schedule': 3600.0,  # Every hour
        },
        'health-check': {
            'task': 'app.tasks.maintenance.health_check_services',
            'schedule': 60.0,  # Every minute
        },
    },
    
    # Beat optimization
    beat_schedule_filename='celerybeat-schedule',
    beat_max_loop_interval=300,  # 5 minutes
)

# Queue-specific worker prefetch configuration
QUEUE_PREFETCH_CONFIG = {
    'ai_processing': 1,      # Heavy AI tasks - one at a time
    'video_processing': 1,   # Heavy video tasks - one at a time  
    'image_processing': 2,   # Medium weight - 2 prefetch
    'social_media': 10,      # Light I/O tasks - high prefetch
    'default': 4,           # Default prefetch
}

# Auto-discover tasks
celery_app.autodiscover_tasks()

if __name__ == '__main__':
    celery_app.start()
 