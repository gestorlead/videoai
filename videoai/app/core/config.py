"""
VideoAI Core Configuration
"""

import os
from typing import List, Optional, Union
from pydantic import AnyHttpUrl, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    VideoAI application settings
    """
    
    # Basic app configuration
    PROJECT_NAME: str = "VideoAI"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "AI Video Creation & Social Media Platform"
    DEBUG: bool = False
    
    # API configuration
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "your-secret-key-here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    # Server configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database configuration
    DATABASE_URL: Optional[str] = None
    
    @validator("DATABASE_URL", pre=True)
    def assemble_db_connection(cls, v: Optional[str], values: dict) -> str:
        if isinstance(v, str):
            return v
        return "sqlite:///./videoai.db"
    
    # Redis configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    
    # RabbitMQ/Celery configuration
    RABBITMQ_URL: str = "amqp://admin:admin123@localhost:5672"
    CELERY_BROKER_URL: str = RABBITMQ_URL
    CELERY_RESULT_BACKEND: str = REDIS_URL
    
    # AI Services configuration
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    STABILITY_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    
    # Social Media APIs
    TWITTER_API_KEY: Optional[str] = None
    TWITTER_API_SECRET: Optional[str] = None
    INSTAGRAM_ACCESS_TOKEN: Optional[str] = None
    FACEBOOK_ACCESS_TOKEN: Optional[str] = None
    YOUTUBE_API_KEY: Optional[str] = None
    TIKTOK_CLIENT_KEY: Optional[str] = None
    
    # File upload configuration
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    ALLOWED_EXTENSIONS: List[str] = [
        "mp4", "avi", "mov", "mkv", "wmv", "flv",
        "jpg", "jpeg", "png", "gif", "webp",
        "mp3", "wav", "flac", "aac"
    ]
    
    # Processing configuration
    MAX_VIDEO_LENGTH: int = 600  # 10 minutes in seconds
    MAX_CONCURRENT_JOBS: int = 5
    JOB_TIMEOUT: int = 3600  # 1 hour
    
    # CORS configuration
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []
    
    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Logging configuration
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "videoai.log"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
 