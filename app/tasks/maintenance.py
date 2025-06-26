"""
Maintenance and utility Celery tasks for VideoAI
"""
import os
import time
import shutil
from pathlib import Path
from typing import Dict, Any
from celery import current_task
from app.core.celery import celery_app


@celery_app.task(bind=True, name="cleanup_temp_files")
def cleanup_temp_files(self) -> Dict[str, Any]:
    """
    Clean up temporary files older than 1 hour
    """
    try:
        current_task.update_state(
            state='PROGRESS',
            meta={'progress': 20, 'status': 'Scanning for temporary files...'}
        )
        
        temp_dirs = ['temp', 'uploads/temp', 'uploads/processing']
        cleaned_files = []
        total_size_freed = 0
        
        for temp_dir in temp_dirs:
            if os.path.exists(temp_dir):
                for file_path in Path(temp_dir).rglob('*'):
                    if file_path.is_file():
                        # Check if file is older than 1 hour
                        if time.time() - file_path.stat().st_mtime > 3600:
                            size = file_path.stat().st_size
                            file_path.unlink()
                            cleaned_files.append(str(file_path))
                            total_size_freed += size
        
        result = {
            'files_cleaned': len(cleaned_files),
            'size_freed_mb': round(total_size_freed / (1024 * 1024), 2),
            'cleaned_files': cleaned_files[:10],  # Show first 10 files
            'task_id': self.request.id,
            'status': 'completed'
        }
        
        return result
        
    except Exception as exc:
        current_task.update_state(
            state='FAILURE',
            meta={'error': str(exc), 'status': 'failed'}
        )
        raise exc


@celery_app.task(bind=True, name="backup_database")
def backup_database(self) -> Dict[str, Any]:
    """
    Create database backup
    """
    try:
        current_task.update_state(
            state='PROGRESS',
            meta={'progress': 30, 'status': 'Creating database backup...'}
        )
        
        # Simulate backup process
        time.sleep(3)
        
        backup_filename = f'videoai_backup_{int(time.time())}.sql'
        backup_path = f'/backups/{backup_filename}'
        
        result = {
            'backup_file': backup_filename,
            'backup_path': backup_path,
            'size_mb': 45.2,
            'timestamp': time.time(),
            'task_id': self.request.id,
            'status': 'completed'
        }
        
        return result
        
    except Exception as exc:
        current_task.update_state(
            state='FAILURE',
            meta={'error': str(exc), 'status': 'failed'}
        )
        raise exc


@celery_app.task(bind=True, name="health_check_services")
def health_check_services(self) -> Dict[str, Any]:
    """
    Check health of external services
    """
    try:
        current_task.update_state(
            state='PROGRESS',
            meta={'progress': 25, 'status': 'Checking service health...'}
        )
        
        services = ['redis', 'rabbitmq', 'database', 'ai_api', 'social_apis']
        service_status = {}
        
        for service in services:
            # Simulate health check
            time.sleep(0.5)
            service_status[service] = {
                'status': 'healthy',
                'response_time_ms': 120,
                'last_check': time.time()
            }
        
        result = {
            'services_checked': len(services),
            'all_healthy': all(s['status'] == 'healthy' for s in service_status.values()),
            'service_status': service_status,
            'task_id': self.request.id,
            'status': 'completed'
        }
        
        return result
        
    except Exception as exc:
        current_task.update_state(
            state='FAILURE',
            meta={'error': str(exc), 'status': 'failed'}
        )
        raise exc


@celery_app.task(bind=True, name="generate_analytics_report")
def generate_analytics_report(self, period: str = "daily") -> Dict[str, Any]:
    """
    Generate analytics report for specified period
    """
    try:
        current_task.update_state(
            state='PROGRESS',
            meta={'progress': 30, 'status': f'Generating {period} analytics report...'}
        )
        
        # Simulate report generation
        time.sleep(2)
        
        # Mock analytics data
        analytics = {
            'period': period,
            'total_videos_processed': 145,
            'total_images_generated': 892,
            'social_posts_published': 67,
            'total_users': 234,
            'active_users': 89,
            'top_features': ['image_generation', 'video_editing', 'social_posting'],
            'report_generated_at': time.time(),
            'task_id': self.request.id,
            'status': 'completed'
        }
        
        return analytics
        
    except Exception as exc:
        current_task.update_state(
            state='FAILURE',
            meta={'error': str(exc), 'status': 'failed'}
        )
        raise exc
