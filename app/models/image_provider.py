from sqlalchemy import Column, String, Boolean, Float, JSON, DateTime, Enum as SQLEnum, Integer, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum
from sqlalchemy.orm import relationship

Base = declarative_base()

class ProviderType(enum.Enum):
    OPENAI = "openai"
    PIAPI = "piapi" 
    GETIMG = "getimg"
    REPLICATE = "replicate"

class ImageProviderConfig(Base):
    __tablename__ = 'image_provider_configs'
    
    id = Column(String, primary_key=True)
    provider_type = Column(SQLEnum(ProviderType), nullable=False)
    name = Column(String, nullable=False)
    api_key = Column(String)  # Será criptografado
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    
    # Configurações específicas do provider
    endpoint_url = Column(String)  # Para custom endpoints
    model_id = Column(String)  # ID do modelo específico
    settings = Column(JSON)  # Configurações adicionais (steps, cfg_scale, etc)
    
    # Informações de custo
    cost_per_image = Column(Float)  # Custo estimado por imagem
    credits_remaining = Column(Float)  # Créditos restantes (quando aplicável)
    last_credit_check = Column(DateTime)
    
    # Limites
    rate_limit_rpm = Column(Integer, default=60)  # Requests por minuto
    max_batch_size = Column(Integer, default=1)  # Tamanho máximo do batch
    
    # Metadados
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<ImageProviderConfig {self.name} ({self.provider_type.value})>"

class ImageGenerationJob(Base):
    __tablename__ = 'image_generation_jobs'
    
    id = Column(String, primary_key=True)
    provider_id = Column(String, ForeignKey('image_provider_configs.id'))
    
    # Parâmetros da geração
    prompt = Column(String, nullable=False)
    negative_prompt = Column(String)
    width = Column(Integer, default=1024)
    height = Column(Integer, default=1024)
    num_images = Column(Integer, default=1)
    settings = Column(JSON)  # steps, guidance_scale, seed, etc
    
    # Status
    status = Column(String, default='pending')  # pending, processing, completed, failed
    error_message = Column(String)
    
    # Resultados
    image_urls = Column(JSON)  # Lista de URLs das imagens geradas
    cost = Column(Float)  # Custo real da geração
    generation_time = Column(Float)  # Tempo de geração em segundos
    
    # Metadados
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    provider = relationship("ImageProviderConfig", backref="jobs")