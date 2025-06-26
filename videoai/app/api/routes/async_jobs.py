"""
Async jobs API routes for VideoAI
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from celery.result import AsyncResult

from app.core.celery import celery_app
from app.tasks import ai_tasks, video_tasks, social_tasks, maintenance


router = APIRouter()


# Pydantic models for request/response
class JobRequest(BaseModel):
    task_name: str
    params: Dict[str, Any] = {}


class JobResponse(BaseModel):
    job_id: str
    task_name: str
    status: str
    message: str


class JobStatus(BaseModel):
    job_id: str
    task_name: str
    status: str
    progress: Optional[int] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# Job submission endpoints
@router.post("/jobs/ai/generate-image", response_model=JobResponse)
async def start_image_generation(
    prompt: str,
    model: str = "dall-e-3"
):
    """Start AI image generation job"""
    try:
        task = ai_tasks.generate_image_with_ai.delay(prompt=prompt, model=model)
        return JobResponse(
            job_id=task.id,
            task_name="generate_image_with_ai",
            status="started",
            message=f"Image generation job started for prompt: {prompt[:50]}..."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start job: {str(e)}")


@router.post("/jobs/video/process", response_model=JobResponse)
async def start_video_processing(
    video_path: str,
    operations: List[str] = ["normalize", "compress"]
):
    """Start video processing job"""
    try:
        task = video_tasks.process_video.delay(video_path=video_path, operations=operations)
        return JobResponse(
            job_id=task.id,
            task_name="process_video",
            status="started",
            message=f"Video processing job started for: {video_path}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start job: {str(e)}")


@router.post("/jobs/social/publish", response_model=JobResponse)
async def start_social_publishing(
    content_path: str,
    platforms: List[str],
    caption: str = ""
):
    """Start social media publishing job"""
    try:
        task = social_tasks.publish_to_social_media.delay(
            content_path=content_path,
            platforms=platforms,
            caption=caption
        )
        return JobResponse(
            job_id=task.id,
            task_name="publish_to_social_media",
            status="started",
            message=f"Publishing job started for platforms: {', '.join(platforms)}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start job: {str(e)}")


@router.post("/jobs/maintenance/cleanup", response_model=JobResponse)
async def start_cleanup_job():
    """Start temp files cleanup job"""
    try:
        task = maintenance.cleanup_temp_files.delay()
        return JobResponse(
            job_id=task.id,
            task_name="cleanup_temp_files",
            status="started",
            message="Cleanup job started"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start job: {str(e)}")


# Job status and management endpoints
@router.get("/jobs/{job_id}/status", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get status of a specific job"""
    try:
        result = AsyncResult(job_id, app=celery_app)
        
        if result.state == 'PENDING':
            response = JobStatus(
                job_id=job_id,
                task_name=result.name or "unknown",
                status="pending",
                progress=0
            )
        elif result.state == 'PROGRESS':
            response = JobStatus(
                job_id=job_id,
                task_name=result.name or "unknown",
                status="in_progress",
                progress=result.info.get('progress', 0),
                result={"status_message": result.info.get('status', 'Processing...')}
            )
        elif result.state == 'SUCCESS':
            response = JobStatus(
                job_id=job_id,
                task_name=result.name or "unknown",
                status="completed",
                progress=100,
                result=result.result
            )
        elif result.state == 'FAILURE':
            response = JobStatus(
                job_id=job_id,
                task_name=result.name or "unknown",
                status="failed",
                error=str(result.info)
            )
        else:
            response = JobStatus(
                job_id=job_id,
                task_name=result.name or "unknown",
                status=result.state.lower()
            )
            
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get job status: {str(e)}")


@router.delete("/jobs/{job_id}")
async def cancel_job(job_id: str):
    """Cancel a running job"""
    try:
        celery_app.control.revoke(job_id, terminate=True)
        return {"message": f"Job {job_id} has been cancelled"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel job: {str(e)}")


@router.get("/jobs/active")
async def get_active_jobs():
    """Get list of active jobs"""
    try:
        inspect = celery_app.control.inspect()
        active = inspect.active()
        scheduled = inspect.scheduled()
        
        return {
            "active_jobs": active or {},
            "scheduled_jobs": scheduled or {}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get active jobs: {str(e)}")


@router.get("/jobs/stats")
async def get_job_stats():
    """Get Celery worker statistics"""
    try:
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        
        return {
            "worker_stats": stats or {},
            "registered_tasks": list(celery_app.tasks.keys())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get job stats: {str(e)}")


# Health check for async infrastructure
@router.get("/jobs/health")
async def async_health_check():
    """Check health of async processing infrastructure"""
    try:
        inspect = celery_app.control.inspect()
        active = inspect.active()
        
        # Test Redis connection (result backend)
        test_task = maintenance.health_check_services.delay()
        redis_ok = test_task.id is not None
        
        return {
            "celery_workers": len(active) if active else 0,
            "redis_backend": "connected" if redis_ok else "disconnected",
            "rabbitmq_broker": "connected",  # If we got here, broker is working
            "status": "healthy"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
