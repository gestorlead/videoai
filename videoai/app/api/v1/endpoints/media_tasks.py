"""
Media Tasks API Endpoints
Endpoints unificados para tarefas de mídia assíncrona
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime

from ....database.session import get_db
# from ....services.task_manager import universal_task_manager
from ....services.webhook_service import webhook_service, WebhookEventType
from ....services.provider_registry import provider_registry
from ....schemas.tasks import (
    TaskCreateRequest,
    TaskResponse,
    TaskListFilters,
    TaskStatistics,
    ImageGenerationRequest,
    VideoGenerationRequest,
    AudioTranscriptionRequest,
    SubtitleGenerationRequest,
    WebhookPayload
)
from ....models.base_task import TaskType, TaskStatus, TaskPriority
from ....core.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/images/generate", response_model=TaskResponse)
async def create_image_generation_task(
    request: ImageGenerationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Cria uma nova tarefa de geração de imagem"""
    try:
        # TODO: Implementar após corrigir universal_task_manager
        raise HTTPException(status_code=501, detail="Endpoint temporariamente desabilitado")
        
        # # Converte para TaskCreateRequest
        # task_request = TaskCreateRequest(
        #     task_type=TaskType.IMAGE_GENERATION,
        #     input_data=request.dict(),
        #     webhook_url=request.webhook_url,
        #     priority=request.priority or TaskPriority.MEDIUM,
        #     metadata=request.metadata or {}
        # )
        
        # # Cria a tarefa
        # task = await universal_task_manager.create_task(
        #     task_request=task_request,
        #     user_id=current_user["id"],
        #     db=db
        # )
        
        # # Envia webhook de criação se configurado
        # if request.webhook_url:
        #     background_tasks.add_task(
        #         webhook_service.send_webhook,
        #         url=request.webhook_url,
        #         event_type=WebhookEventType.TASK_CREATED,
        #         task_id=task.id,
        #         task_data={"status": task.status.value, "type": task.task_type.value},
        #         user_id=current_user["id"]
        #     )
        
        # return TaskResponse.from_orm(task)
        
    except Exception as e:
        logger.error(f"Erro ao criar tarefa de geração de imagem: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/videos/generate", response_model=TaskResponse)
async def create_video_generation_task(
    request: VideoGenerationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Cria uma nova tarefa de geração de vídeo"""
    try:
        task_request = TaskCreateRequest(
            task_type=TaskType.VIDEO_GENERATION,
            input_data=request.dict(),
            webhook_url=request.webhook_url,
            priority=request.priority or TaskPriority.MEDIUM,
            metadata=request.metadata or {}
        )
        
        task = await universal_task_manager.create_task(
            task_request=task_request,
            user_id=current_user["id"],
            db=db
        )
        
        if request.webhook_url:
            background_tasks.add_task(
                webhook_service.send_webhook,
                url=request.webhook_url,
                event_type=WebhookEventType.TASK_CREATED,
                task_id=task.id,
                task_data={"status": task.status.value, "type": task.task_type.value},
                user_id=current_user["id"]
            )
        
        return TaskResponse.from_orm(task)
        
    except Exception as e:
        logger.error(f"Erro ao criar tarefa de geração de vídeo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/audio/transcribe", response_model=TaskResponse)
async def create_audio_transcription_task(
    request: AudioTranscriptionRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Cria uma nova tarefa de transcrição de áudio"""
    try:
        task_request = TaskCreateRequest(
            task_type=TaskType.AUDIO_TRANSCRIPTION,
            input_data=request.dict(),
            webhook_url=request.webhook_url,
            priority=request.priority or TaskPriority.MEDIUM,
            metadata=request.metadata or {}
        )
        
        task = await universal_task_manager.create_task(
            task_request=task_request,
            user_id=current_user["id"],
            db=db
        )
        
        if request.webhook_url:
            background_tasks.add_task(
                webhook_service.send_webhook,
                url=request.webhook_url,
                event_type=WebhookEventType.TASK_CREATED,
                task_id=task.id,
                task_data={"status": task.status.value, "type": task.task_type.value},
                user_id=current_user["id"]
            )
        
        return TaskResponse.from_orm(task)
        
    except Exception as e:
        logger.error(f"Erro ao criar tarefa de transcrição: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/subtitles/generate", response_model=TaskResponse)
async def create_subtitle_generation_task(
    request: SubtitleGenerationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Cria uma nova tarefa de geração de legendas"""
    try:
        task_request = TaskCreateRequest(
            task_type=TaskType.SUBTITLE_GENERATION,
            input_data=request.dict(),
            webhook_url=request.webhook_url,
            priority=request.priority or TaskPriority.MEDIUM,
            metadata=request.metadata or {}
        )
        
        task = await universal_task_manager.create_task(
            task_request=task_request,
            user_id=current_user["id"],
            db=db
        )
        
        if request.webhook_url:
            background_tasks.add_task(
                webhook_service.send_webhook,
                url=request.webhook_url,
                event_type=WebhookEventType.TASK_CREATED,
                task_id=task.id,
                task_data={"status": task.status.value, "type": task.task_type.value},
                user_id=current_user["id"]
            )
        
        return TaskResponse.from_orm(task)
        
    except Exception as e:
        logger.error(f"Erro ao criar tarefa de geração de legendas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task_status(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Obtém o status detalhado de uma tarefa"""
    try:
        task = await universal_task_manager.get_task_status(
            task_id=task_id,
            user_id=current_user["id"],
            db=db
        )
        
        if not task:
            raise HTTPException(status_code=404, detail="Tarefa não encontrada")
        
        return TaskResponse.from_orm(task)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter status da tarefa {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks", response_model=List[TaskResponse])
async def list_user_tasks(
    task_type: Optional[TaskType] = Query(None, description="Filtrar por tipo de tarefa"),
    status: Optional[TaskStatus] = Query(None, description="Filtrar por status"),
    priority: Optional[TaskPriority] = Query(None, description="Filtrar por prioridade"),
    limit: int = Query(50, ge=1, le=100, description="Limite de resultados"),
    offset: int = Query(0, ge=0, description="Offset para paginação"),
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Lista as tarefas do usuário com filtros opcionais"""
    try:
        filters = TaskListFilters(
            task_type=task_type,
            status=status,
            priority=priority,
            limit=limit,
            offset=offset
        )
        
        tasks = await universal_task_manager.list_user_tasks(
            user_id=current_user["id"],
            filters=filters,
            db=db
        )
        
        return [TaskResponse.from_orm(task) for task in tasks]
        
    except Exception as e:
        logger.error(f"Erro ao listar tarefas do usuário: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Cancela uma tarefa"""
    try:
        success = await universal_task_manager.cancel_task(
            task_id=task_id,
            user_id=current_user["id"],
            db=db
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Tarefa não encontrada ou não pode ser cancelada")
        
        # Obtém tarefa atualizada para webhook
        task = await universal_task_manager.get_task_status(task_id, current_user["id"], db)
        if task and task.webhook_url:
            background_tasks.add_task(
                webhook_service.send_webhook,
                url=task.webhook_url,
                event_type=WebhookEventType.TASK_CANCELLED,
                task_id=task.id,
                task_data={"status": task.status.value, "type": task.task_type.value},
                user_id=current_user["id"]
            )
        
        return {"message": "Tarefa cancelada com sucesso", "task_id": task_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao cancelar tarefa {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics", response_model=TaskStatistics)
async def get_task_statistics(
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Obtém estatísticas das tarefas do usuário"""
    try:
        stats = await universal_task_manager.get_user_statistics(
            user_id=current_user["id"],
            db=db
        )
        
        return stats
        
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/providers", response_model=Dict[str, Any])
async def get_provider_status():
    """Obtém status dos provedores de mídia"""
    try:
        return provider_registry.get_registry_stats()
    except Exception as e:
        logger.error(f"Erro ao obter status dos provedores: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/webhooks/{webhook_id}/status")
async def get_webhook_status(webhook_id: str):
    """Obtém status de entrega de um webhook"""
    try:
        status = webhook_service.get_webhook_status(webhook_id)
        if not status:
            raise HTTPException(status_code=404, detail="Webhook não encontrado")
        
        return status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter status do webhook {webhook_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/webhooks/statistics")
async def get_webhook_statistics():
    """Obtém estatísticas dos webhooks"""
    try:
        return webhook_service.get_webhooks_stats()
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas dos webhooks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Endpoints para batch processing (compatibilidade com sistema existente)
@router.post("/batch", response_model=Dict[str, Any])
async def create_batch_tasks(
    requests: List[TaskCreateRequest],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Cria múltiplas tarefas em lote"""
    try:
        if len(requests) > 50:
            raise HTTPException(status_code=400, detail="Máximo de 50 tarefas por lote")
        
        batch_id = f"batch_{int(datetime.utcnow().timestamp())}"
        tasks = []
        
        for req in requests:
            task = await universal_task_manager.create_task(
                task_request=req,
                user_id=current_user["id"],
                db=db
            )
            tasks.append(task)
            
            # Webhook de criação se configurado
            if req.webhook_url:
                background_tasks.add_task(
                    webhook_service.send_webhook,
                    url=req.webhook_url,
                    event_type=WebhookEventType.TASK_CREATED,
                    task_id=task.id,
                    task_data={"status": task.status.value, "type": task.task_type.value},
                    user_id=current_user["id"],
                    metadata={"batch_id": batch_id}
                )
        
        return {
            "batch_id": batch_id,
            "total_tasks": len(tasks),
            "task_ids": [task.id for task in tasks],
            "message": f"Criadas {len(tasks)} tarefas em lote"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao criar lote de tarefas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Health check endpoint
@router.get("/health")
async def health_check():
    """Health check do sistema de tarefas"""
    try:
        # Verifica status dos provedores
        provider_health = await provider_registry.health_check_all()
        
        # Verifica serviços
        webhook_stats = webhook_service.get_webhooks_stats()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "task_manager": "active",
                "webhook_service": "active" if webhook_stats["worker_running"] else "inactive",
                "provider_registry": "active"
            },
            "providers": provider_health,
            "metrics": {
                "total_webhooks": webhook_stats["total_webhooks"],
                "webhook_success_rate": webhook_stats["success_rate"]
            }
        }
    except Exception as e:
        logger.error(f"Erro no health check: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        ) 