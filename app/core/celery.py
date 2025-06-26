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