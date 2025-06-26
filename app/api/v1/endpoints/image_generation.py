from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid
from datetime import datetime

from ....core.database import get_db
from ....services.image_generation import (
    ImageProviderManager,
    ImageGenerationRequest,
    ProviderError,
    RateLimitError,
    InsufficientCreditsError
)
from ....services.image_generation.batch_processor import BatchProcessor, BatchJob, BatchStatus
from ....services.image_generation.batch_monitor import BatchMonitor
from ....services.image_generation.batch_cache import BatchCache
from ....models.image_provider import ProviderType
from ....core.auth import get_current_user
from ....models.user import User

router = APIRouter()

# Instâncias globais dos componentes de batch processing
batch_processor: Optional[BatchProcessor] = None
batch_monitor: Optional[BatchMonitor] = None
batch_cache: Optional[BatchCache] = None

async def initialize_batch_system(db: Session):
    """Inicializa sistema de batch processing"""
    global batch_processor, batch_monitor, batch_cache
    
    if batch_processor is None:
        # Inicializa cache
        batch_cache = BatchCache(
            redis_url=None,  # Configure Redis URL se disponível
            local_cache_dir="cache/images",
            max_memory_items=1000,
            ttl_hours=24
        )
        await batch_cache.start()
        
        # Inicializa processor
        provider_manager = ImageProviderManager(db)
        batch_processor = BatchProcessor(
            provider_manager=provider_manager,
            max_concurrent=5,
            max_retries=3
        )
        await batch_processor.start()
        
        # Inicializa monitor
        batch_monitor = BatchMonitor(batch_processor)
        await batch_monitor.start()

# Schemas Pydantic
class ImageGenerationRequestSchema(BaseModel):
    prompt: str = Field(..., description="Text prompt for image generation")
    negative_prompt: Optional[str] = Field(None, description="What to avoid in the image")
    width: int = Field(1024, ge=256, le=4096, description="Image width")
    height: int = Field(1024, ge=256, le=4096, description="Image height")
    num_images: int = Field(1, ge=1, le=10, description="Number of images to generate")
    provider_id: Optional[str] = Field(None, description="Specific provider to use")
    style: Optional[str] = Field(None, description="Style preset (realistic, anime, artistic)")
    seed: Optional[int] = Field(None, description="Seed for reproducible generation")
    guidance_scale: float = Field(7.5, ge=1.0, le=20.0, description="Guidance scale")
    steps: int = Field(30, ge=10, le=150, description="Number of inference steps")
    extra_params: Optional[Dict[str, Any]] = Field(None, description="Provider-specific parameters")

class BatchImageGenerationRequestSchema(BaseModel):
    requests: List[ImageGenerationRequestSchema] = Field(..., description="List of generation requests")
    provider_id: Optional[str] = Field(None, description="Specific provider to use for all")

class BatchJobRequestSchema(BaseModel):
    requests: List[ImageGenerationRequestSchema] = Field(..., description="List of generation requests")
    provider_id: Optional[str] = Field(None, description="Specific provider to use for all")
    priority: int = Field(0, ge=0, le=10, description="Job priority (0=lowest, 10=highest)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional job metadata")

class BatchJobStatusSchema(BaseModel):
    job_id: str
    status: str
    progress: Dict[str, int]
    total_items: int
    completed_items: int
    failed_items: int
    total_cost: float
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    estimated_time_remaining: Optional[float] = None
    
class BatchMetricsSchema(BaseModel):
    total_processed: int
    total_failed: int
    total_cost: float
    avg_generation_time: float
    active_jobs: int
    queue_sizes: Dict[str, int]
    cache_metrics: Dict[str, Any]

class ProviderConfigSchema(BaseModel):
    provider_type: ProviderType
    name: str
    api_key: str
    config: Optional[Dict[str, Any]] = None
    is_default: bool = False

class ImageGenerationResponseSchema(BaseModel):
    job_id: str
    status: str
    image_urls: List[str]
    cost: float
    generation_time: float
    provider: str
    metadata: Optional[Dict[str, Any]] = None

class BatchJobRequestSchema(BaseModel):
    requests: List[ImageGenerationRequestSchema] = Field(..., description="List of generation requests")
    provider_id: Optional[str] = Field(None, description="Specific provider to use for all")
    priority: int = Field(0, ge=0, le=10, description="Job priority (0=lowest, 10=highest)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional job metadata")

class BatchJobStatusSchema(BaseModel):
    job_id: str
    status: str
    progress: Dict[str, int]
    total_items: int
    completed_items: int
    failed_items: int
    total_cost: float
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    estimated_time_remaining: Optional[float] = None
    
class BatchMetricsSchema(BaseModel):
    total_processed: int
    total_failed: int
    total_cost: float
    avg_generation_time: float
    active_jobs: int
    queue_sizes: Dict[str, int]
    cache_metrics: Dict[str, Any]

@router.post("/generate", response_model=ImageGenerationResponseSchema)
async def generate_image(
    request: ImageGenerationRequestSchema,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate a single image or multiple images"""
    manager = ImageProviderManager(db)
    
    # Converte schema para request interno
    generation_request = ImageGenerationRequest(
        prompt=request.prompt,
        negative_prompt=request.negative_prompt,
        width=request.width,
        height=request.height,
        num_images=request.num_images,
        seed=request.seed,
        guidance_scale=request.guidance_scale,
        steps=request.steps,
        style=request.style,
        extra_params=request.extra_params
    )
    
    try:
        # Gera imagem
        response = await manager.generate_image(
            generation_request,
            provider_id=request.provider_id
        )
        
        # TODO: Salvar job no banco de dados
        job_id = str(uuid.uuid4())
        
        # TODO: Upload das imagens para S3/storage
        # Por enquanto retorna URLs temporárias do provider
        
        return ImageGenerationResponseSchema(
            job_id=job_id,
            status="completed",
            image_urls=response.image_urls,
            cost=response.cost,
            generation_time=response.generation_time,
            provider=response.provider,
            metadata=response.metadata
        )
        
    except InsufficientCreditsError as e:
        raise HTTPException(status_code=402, detail=str(e))
    except RateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except ProviderError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.post("/batch-generate", response_model=List[ImageGenerationResponseSchema])
async def batch_generate_images(
    request: BatchImageGenerationRequestSchema,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate multiple images in batch"""
    manager = ImageProviderManager(db)
    
    # Converte requests
    generation_requests = []
    for req in request.requests:
        generation_requests.append(ImageGenerationRequest(
            prompt=req.prompt,
            negative_prompt=req.negative_prompt,
            width=req.width,
            height=req.height,
            num_images=req.num_images,
            seed=req.seed,
            guidance_scale=req.guidance_scale,
            steps=req.steps,
            style=req.style,
            extra_params=req.extra_params
        ))
    
    try:
        # Gera imagens em batch
        responses = await manager.batch_generate_images(
            generation_requests,
            provider_id=request.provider_id
        )
        
        # Converte respostas
        result = []
        for response in responses:
            job_id = str(uuid.uuid4())
            result.append(ImageGenerationResponseSchema(
                job_id=job_id,
                status="completed",
                image_urls=response.image_urls,
                cost=response.cost,
                generation_time=response.generation_time,
                provider=response.provider,
                metadata=response.metadata
            ))
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/providers")
async def list_providers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all configured image generation providers"""
    manager = ImageProviderManager(db)
    return manager.get_available_providers()

@router.post("/providers")
async def create_provider(
    config: ProviderConfigSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new provider configuration (admin only)"""
    # TODO: Add admin check
    manager = ImageProviderManager(db)
    
    try:
        provider_config = await manager.create_provider_config(
            provider_type=config.provider_type,
            name=config.name,
            api_key=config.api_key,
            config=config.config,
            is_default=config.is_default
        )
        
        return {
            "id": provider_config.id,
            "name": provider_config.name,
            "type": provider_config.provider_type.value,
            "is_default": provider_config.is_default
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/providers/{provider_id}/credits")
async def check_provider_credits(
    provider_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check remaining credits for a provider"""
    manager = ImageProviderManager(db)
    
    try:
        credits = await manager.check_provider_credits(provider_id)
        return {
            "provider_id": provider_id,
            "credits": credits,
            "has_credits": credits is None or credits > 0
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/estimate-cost")
async def estimate_generation_cost(
    request: ImageGenerationRequestSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Estimate the cost of image generation before executing"""
    manager = ImageProviderManager(db)
    
    generation_request = ImageGenerationRequest(
        prompt=request.prompt,
        negative_prompt=request.negative_prompt,
        width=request.width,
        height=request.height,
        num_images=request.num_images,
        seed=request.seed,
        guidance_scale=request.guidance_scale,
        steps=request.steps,
        style=request.style,
        extra_params=request.extra_params
    )
    
    try:
        cost = await manager.estimate_cost(
            generation_request,
            provider_id=request.provider_id
        )
        
        return {
            "estimated_cost": cost,
            "provider_id": request.provider_id,
            "num_images": request.num_images
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/job/{job_id}")
async def get_generation_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get status and results of a generation job"""
    # TODO: Implementar busca no banco de dados
    raise HTTPException(status_code=501, detail="Not implemented yet")

@router.post("/batch", response_model=BatchJobStatusSchema)
async def submit_batch_job(
    request: BatchJobRequestSchema,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit advanced batch job for processing"""
    await initialize_batch_system(db)
    
    if not batch_processor:
        raise HTTPException(status_code=500, detail="Batch system not initialized")
    
    # Converte requests
    generation_requests = []
    for req in request.requests:
        # Verifica cache primeiro
        cache_response = None
        if batch_cache:
            generation_request = ImageGenerationRequest(
                prompt=req.prompt,
                negative_prompt=req.negative_prompt,
                width=req.width,
                height=req.height,
                num_images=req.num_images,
                seed=req.seed,
                guidance_scale=req.guidance_scale,
                steps=req.steps,
                style=req.style,
                extra_params=req.extra_params
            )
            cache_response = await batch_cache.get(generation_request, request.provider_id or "default")
        
        # Adiciona à lista apenas se não estiver em cache
        if not cache_response:
            generation_requests.append(generation_request)
    
    if not generation_requests:
        # Todas as requests estavam em cache
        return BatchJobStatusSchema(
            job_id=str(uuid.uuid4()),
            status="completed",
            progress={"completed": len(request.requests)},
            total_items=len(request.requests),
            completed_items=len(request.requests),
            failed_items=0,
            total_cost=0.0,
            created_at=datetime.utcnow().isoformat()
        )
    
    try:
        # Submete batch
        job = await batch_processor.submit_batch(
            requests=generation_requests,
            provider_id=request.provider_id,
            priority=request.priority,
            metadata=request.metadata
        )
        
        return BatchJobStatusSchema(
            job_id=job.id,
            status=job.status.value,
            progress=job.progress,
            total_items=len(job.items),
            completed_items=job.progress.get("completed", 0),
            failed_items=job.progress.get("failed", 0),
            total_cost=job.total_cost,
            created_at=job.created_at.isoformat(),
            started_at=job.started_at.isoformat() if job.started_at else None,
            completed_at=job.completed_at.isoformat() if job.completed_at else None
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/batch/{job_id}", response_model=BatchJobStatusSchema)
async def get_batch_status(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get status of a batch job"""
    await initialize_batch_system(db)
    
    if not batch_processor:
        raise HTTPException(status_code=500, detail="Batch system not initialized")
    
    job = await batch_processor.get_batch_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Batch job not found")
    
    # Calcula tempo estimado restante
    estimated_time = None
    if job.status == BatchStatus.PROCESSING and job.started_at:
        elapsed = (datetime.utcnow() - job.started_at).total_seconds()
        completed = job.progress.get("completed", 0)
        total = len(job.items)
        
        if completed > 0:
            avg_time_per_item = elapsed / completed
            remaining_items = total - completed - job.progress.get("failed", 0)
            estimated_time = avg_time_per_item * remaining_items
    
    return BatchJobStatusSchema(
        job_id=job.id,
        status=job.status.value,
        progress=job.progress,
        total_items=len(job.items),
        completed_items=job.progress.get("completed", 0),
        failed_items=job.progress.get("failed", 0),
        total_cost=job.total_cost,
        created_at=job.created_at.isoformat(),
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        estimated_time_remaining=estimated_time
    )

@router.delete("/batch/{job_id}")
async def cancel_batch_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel a batch job"""
    await initialize_batch_system(db)
    
    if not batch_processor:
        raise HTTPException(status_code=500, detail="Batch system not initialized")
    
    success = await batch_processor.cancel_batch(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Batch job not found")
    
    return {"message": "Batch job cancelled successfully"}

@router.get("/metrics", response_model=BatchMetricsSchema)
async def get_batch_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get batch processing metrics"""
    await initialize_batch_system(db)
    
    if not batch_processor or not batch_monitor or not batch_cache:
        raise HTTPException(status_code=500, detail="Batch system not initialized")
    
    processor_metrics = batch_processor.get_metrics()
    cache_metrics = batch_cache.get_metrics()
    
    return BatchMetricsSchema(
        total_processed=processor_metrics['total_processed'],
        total_failed=processor_metrics['total_failed'],
        total_cost=processor_metrics['total_cost'],
        avg_generation_time=processor_metrics['avg_generation_time'],
        active_jobs=processor_metrics['active_jobs'],
        queue_sizes=processor_metrics['queue_sizes'],
        cache_metrics=cache_metrics
    )

@router.get("/monitor/alerts")
async def get_system_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get active system alerts"""
    await initialize_batch_system(db)
    
    if not batch_monitor:
        raise HTTPException(status_code=500, detail="Batch monitor not initialized")
    
    alerts = batch_monitor.get_active_alerts()
    return {"alerts": alerts}

@router.post("/monitor/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Resolve a system alert"""
    await initialize_batch_system(db)
    
    if not batch_monitor:
        raise HTTPException(status_code=500, detail="Batch monitor not initialized")
    
    success = batch_monitor.resolve_alert(alert_id)
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return {"message": "Alert resolved successfully"}

@router.get("/cache/stats")
async def get_cache_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed cache statistics"""
    await initialize_batch_system(db)
    
    if not batch_cache:
        raise HTTPException(status_code=500, detail="Cache system not initialized")
    
    cache_info = await batch_cache.get_cache_info()
    return cache_info

@router.delete("/cache")
async def clear_cache(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Clear all cached images"""
    await initialize_batch_system(db)
    
    if not batch_cache:
        raise HTTPException(status_code=500, detail="Cache system not initialized")
    
    await batch_cache.clear()
    return {"message": "Cache cleared successfully"}

@router.get("/providers/{provider_id}/performance")
async def get_provider_performance(
    provider_id: str,
    hours: int = 24,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get performance statistics for a specific provider"""
    await initialize_batch_system(db)
    
    if not batch_monitor:
        raise HTTPException(status_code=500, detail="Batch monitor not initialized")
    
    performance = batch_monitor.get_provider_performance(provider_id, hours)
    return {
        "provider_id": provider_id,
        "hours": hours,
        "performance": performance
    }
