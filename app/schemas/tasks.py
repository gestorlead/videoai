from pydantic import BaseModel, Field, validator
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

# Enums duplicados dos modelos para uso nos schemas
class TaskTypeSchema(str, Enum):
    IMAGE_GENERATION = "image_generation"
    IMAGE_OPTIMIZATION = "image_optimization"
    IMAGE_ANALYSIS = "image_analysis"
    VIDEO_GENERATION = "video_generation"
    VIDEO_EDITING = "video_editing"
    VIDEO_TRIM_JOIN = "video_trim_join"
    AUDIO_TRANSCRIPTION = "audio_transcription"
    AUDIO_GENERATION = "audio_generation"
    SUBTITLE_GENERATION = "subtitle_generation"
    SUBTITLE_TRANSLATION = "subtitle_translation"

class TaskStatusSchema(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"

class OptimizationLevel(str, Enum):
    NONE = "none"
    BASIC = "basic"
    ADVANCED = "advanced"
    EXPERIMENTAL = "experimental"

# Schema base para criação de tasks
class TaskCreateRequest(BaseModel):
    """Base schema para criar qualquer tipo de task"""
    task_type: TaskTypeSchema
    input_data: Dict[str, Any]
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    priority: int = Field(5, ge=1, le=10)
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    
    @validator('webhook_url')
    def validate_webhook_url(cls, v):
        if v and not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError('Webhook URL must start with http:// or https://')
        return v

# Response schema para tasks
class TaskResponse(BaseModel):
    """Schema de resposta para qualquer task"""
    id: str
    user_id: str
    task_type: str
    status: str
    
    # Progress
    progress: float = Field(0.0, ge=0.0, le=1.0)
    progress_message: Optional[str] = None
    
    # Dados
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]] = None
    
    # Estimativas e custos
    estimated_duration: Optional[float] = None
    actual_duration: Optional[float] = None
    estimated_cost: float = 0.0
    actual_cost: float = 0.0
    
    # Timestamps
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    # Erro
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    
    # Metadados extras
    provider_id: Optional[str] = None
    external_task_id: Optional[str] = None
    queue_position: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    tags: List[str] = []
    
    class Config:
        orm_mode = True

# Schemas específicos para cada tipo de mídia

# IMAGENS
class ImageGenerationData(BaseModel):
    """Dados de input para geração de imagem"""
    prompt: str = Field(..., min_length=1, max_length=5000)
    negative_prompt: Optional[str] = None
    width: int = Field(1024, ge=256, le=4096)
    height: int = Field(1024, ge=256, le=4096)
    num_images: int = Field(1, ge=1, le=10)
    
    # Provider e otimização
    provider_id: Optional[str] = None
    optimization_level: OptimizationLevel = OptimizationLevel.BASIC
    use_prompt_optimization: bool = True
    force_original_prompt: bool = False
    
    # Parâmetros de geração
    style: Optional[str] = None
    seed: Optional[int] = None
    guidance_scale: float = Field(7.5, ge=1.0, le=20.0)
    steps: int = Field(30, ge=10, le=150)
    
    # Parâmetros extras específicos do provider
    extra_params: Optional[Dict[str, Any]] = None

class ImageGenerationRequest(TaskCreateRequest):
    """Request para gerar imagem"""
    task_type: TaskTypeSchema = TaskTypeSchema.IMAGE_GENERATION
    input_data: ImageGenerationData

class ImageAnalysisData(BaseModel):
    """Dados para análise de imagem (GPT-4 Vision, etc)"""
    image_urls: List[str] = Field(..., min_items=1, max_items=10)
    analysis_prompt: str
    generate_from_analysis: bool = False
    provider_id: Optional[str] = "openai"

class ImageAnalysisRequest(TaskCreateRequest):
    """Request para analisar imagem"""
    task_type: TaskTypeSchema = TaskTypeSchema.IMAGE_ANALYSIS
    input_data: ImageAnalysisData

# VÍDEOS
class VideoGenerationData(BaseModel):
    """Dados para geração de vídeo"""
    prompt: str = Field(..., min_length=1, max_length=5000)
    duration: float = Field(5.0, ge=1.0, le=60.0)  # segundos
    fps: int = Field(30, ge=24, le=60)
    resolution: str = Field("1080p", pattern="^(720p|1080p|4k)$")
    aspect_ratio: str = Field("16:9", pattern="^(16:9|9:16|1:1|4:3)$")
    provider_id: Optional[str] = None
    style: Optional[str] = None
    extra_params: Optional[Dict[str, Any]] = None

class VideoGenerationRequest(TaskCreateRequest):
    """Request para gerar vídeo"""
    task_type: TaskTypeSchema = TaskTypeSchema.VIDEO_GENERATION
    input_data: VideoGenerationData

class VideoEditingData(BaseModel):
    """Dados para edição de vídeo"""
    video_url: str
    operations: List[Dict[str, Any]]  # Lista de operações de edição
    output_format: str = "mp4"
    output_quality: str = "high"
    provider_id: Optional[str] = None

class VideoEditingRequest(TaskCreateRequest):
    """Request para editar vídeo"""
    task_type: TaskTypeSchema = TaskTypeSchema.VIDEO_EDITING
    input_data: VideoEditingData

class VideoTrimJoinData(BaseModel):
    """Dados para cortar/juntar vídeos"""
    videos: List[Dict[str, Any]]  # Lista de vídeos com pontos de corte
    output_format: str = "mp4"
    transition: Optional[str] = None
    audio_track: Optional[str] = None

class VideoTrimJoinRequest(TaskCreateRequest):
    """Request para cortar/juntar vídeos"""
    task_type: TaskTypeSchema = TaskTypeSchema.VIDEO_TRIM_JOIN
    input_data: VideoTrimJoinData

# ÁUDIO
class AudioTranscriptionData(BaseModel):
    """Dados para transcrição de áudio"""
    audio_url: str
    language: Optional[str] = "auto"
    format: str = Field("srt", pattern="^(srt|vtt|json|text)$")
    provider_id: Optional[str] = "openai"
    extra_params: Optional[Dict[str, Any]] = None

class AudioTranscriptionRequest(TaskCreateRequest):
    """Request para transcrever áudio"""
    task_type: TaskTypeSchema = TaskTypeSchema.AUDIO_TRANSCRIPTION
    input_data: AudioTranscriptionData

class AudioGenerationData(BaseModel):
    """Dados para geração de áudio (TTS)"""
    text: str = Field(..., min_length=1, max_length=10000)
    voice_id: Optional[str] = None
    language: str = "pt-BR"
    speed: float = Field(1.0, ge=0.5, le=2.0)
    provider_id: Optional[str] = None

class AudioGenerationRequest(TaskCreateRequest):
    """Request para gerar áudio"""
    task_type: TaskTypeSchema = TaskTypeSchema.AUDIO_GENERATION
    input_data: AudioGenerationData

# LEGENDAS
class SubtitleGenerationData(BaseModel):
    """Dados para gerar legendas"""
    video_url: str
    language: str = "pt-BR"
    style: str = Field("default", pattern="^(default|minimal|full)$")
    burn_in: bool = False  # Se deve queimar as legendas no vídeo
    provider_id: Optional[str] = None

class SubtitleGenerationRequest(TaskCreateRequest):
    """Request para gerar legendas"""
    task_type: TaskTypeSchema = TaskTypeSchema.SUBTITLE_GENERATION
    input_data: SubtitleGenerationData

class SubtitleTranslationData(BaseModel):
    """Dados para traduzir legendas"""
    subtitle_url: str
    source_language: str
    target_language: str
    preserve_timing: bool = True
    provider_id: Optional[str] = None

class SubtitleTranslationRequest(TaskCreateRequest):
    """Request para traduzir legendas"""
    task_type: TaskTypeSchema = TaskTypeSchema.SUBTITLE_TRANSLATION
    input_data: SubtitleTranslationData

# Schemas para listagem e filtros
class TaskListFilters(BaseModel):
    """Filtros para listar tasks"""
    status: Optional[TaskStatusSchema] = None
    task_type: Optional[TaskTypeSchema] = None
    provider_id: Optional[str] = None
    tags: Optional[List[str]] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    limit: int = Field(50, ge=1, le=100)
    offset: int = Field(0, ge=0)

# Schema para webhook payload
class WebhookPayload(BaseModel):
    """Payload enviado via webhook quando task completa"""
    task_id: str
    status: str
    task_type: str
    output_data: Optional[Dict[str, Any]] = None
    cost: float = 0.0
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

# Schema para estatísticas
class TaskStatistics(BaseModel):
    """Estatísticas de tasks do usuário"""
    total_tasks: int
    tasks_by_status: Dict[str, int]
    tasks_by_type: Dict[str, int]
    total_cost: float
    average_duration: float
    success_rate: float 