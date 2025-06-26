from enum import Enum
from sqlalchemy import Column, String, DateTime, Text, JSON, Float, Integer, ForeignKey, Boolean, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from typing import Dict, Any, Optional
import uuid

from ..database.session import Base

class TaskType(Enum):
    """Tipos de tasks suportadas pelo sistema"""
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

class TaskStatus(Enum):
    """Status possíveis de uma task"""
    PENDING = "pending"          # Criada mas não enfileirada
    QUEUED = "queued"           # Na fila aguardando processamento
    PROCESSING = "processing"    # Sendo processada
    COMPLETED = "completed"      # Concluída com sucesso
    FAILED = "failed"           # Falhou definitivamente
    CANCELLED = "cancelled"      # Cancelada pelo usuário
    RETRYING = "retrying"       # Aguardando retry após falha

class TaskPriority(Enum):
    """Níveis de prioridade"""
    LOW = 1
    NORMAL = 5
    HIGH = 8
    URGENT = 10

class MediaTask(Base):
    """Tabela principal de tasks assíncronas"""
    __tablename__ = "media_tasks"
    
    # Identificação
    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(50), ForeignKey("users.id"), nullable=False)
    
    # Tipo e status
    task_type = Column(String(50), nullable=False)  # Usando String em vez de Enum para flexibilidade
    status = Column(String(20), default=TaskStatus.PENDING.value)
    
    # Dados da requisição
    input_data = Column(JSON, nullable=False)  # Parâmetros da task
    output_data = Column(JSON)  # Resultado quando completo
    
    # Processamento
    provider_id = Column(String(100))  # Qual provedor está processando
    external_task_id = Column(String(200))  # ID no sistema externo (se aplicável)
    
    # Webhooks e notificações
    webhook_url = Column(String(500))  # URL para notificar conclusão
    webhook_secret = Column(String(100))  # Secret para validar webhook
    webhook_attempts = Column(Integer, default=0)
    webhook_last_attempt = Column(DateTime)
    webhook_status = Column(String(20))  # success, failed, pending
    
    # Metadados e controle
    priority = Column(Integer, default=TaskPriority.NORMAL.value)
    estimated_duration = Column(Float)  # Segundos estimados
    actual_duration = Column(Float)  # Tempo real gasto
    estimated_cost = Column(Float, default=0.0)
    actual_cost = Column(Float, default=0.0)
    
    # Progress tracking
    progress = Column(Float, default=0.0)  # 0.0 a 1.0
    progress_message = Column(String(500))  # Mensagem de status atual
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    expires_at = Column(DateTime)  # Para limpar tasks antigas
    
    # Controle de erro e retry
    error_message = Column(Text)
    error_details = Column(JSON)  # Stack trace, código de erro, etc
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    retry_after = Column(DateTime)  # Quando tentar novamente
    
    # Metadados adicionais
    task_metadata = Column(JSON, default=dict)  # Dados extras específicos do tipo
    tags = Column(JSON, default=list)  # Tags para organização
    
    # Índices para performance
    __table_args__ = (
        Index('idx_user_status', 'user_id', 'status'),
        Index('idx_task_type_status', 'task_type', 'status'),
        Index('idx_created_at', 'created_at'),
        Index('idx_priority_status', 'priority', 'status'),
    )

class TaskLog(Base):
    """Log de eventos das tasks"""
    __tablename__ = "task_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(50), ForeignKey("media_tasks.id"), nullable=False)
    
    event_type = Column(String(50), nullable=False)  # status_change, error, retry, etc
    event_data = Column(JSON)
    message = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Índice para busca rápida
    __table_args__ = (
        Index('idx_task_id_created', 'task_id', 'created_at'),
    )

class TaskDependency(Base):
    """Dependências entre tasks"""
    __tablename__ = "task_dependencies"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    dependent_task_id = Column(String(50), ForeignKey("media_tasks.id"), nullable=False)
    required_task_id = Column(String(50), ForeignKey("media_tasks.id"), nullable=False)
    
    # Tipo de dependência
    dependency_type = Column(String(20), default="completion")  # completion, success, any
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Evita duplicatas
    __table_args__ = (
        Index('idx_unique_dependency', 'dependent_task_id', 'required_task_id', unique=True),
    ) 