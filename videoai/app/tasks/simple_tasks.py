"""
Simple Celery tasks for testing (without task context dependencies)
"""
import time
from app.core.celery import celery_app


@celery_app.task(name="simple_add")
def simple_add(x, y):
    """Simple addition task for testing"""
    time.sleep(1)  # Simulate some work
    result = x + y
    return {
        'operation': 'addition',
        'x': x,
        'y': y,
        'result': result,
        'status': 'completed'
    }


@celery_app.task(name="simple_multiply")
def simple_multiply(x, y):
    """Simple multiplication task for testing"""
    time.sleep(2)  # Simulate more work
    result = x * y
    return {
        'operation': 'multiplication',
        'x': x,
        'y': y,
        'result': result,
        'status': 'completed'
    }


@celery_app.task(name="simple_hello")
def simple_hello(name="World"):
    """Simple hello task for testing"""
    time.sleep(0.5)
    return {
        'message': f'Hello, {name}!',
        'timestamp': time.time(),
        'status': 'completed'
    }
