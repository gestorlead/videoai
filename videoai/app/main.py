"""
VideoAI FastAPI Application
AI Video Creation & Social Media Platform
"""
import os
import redis
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time

from app.core.config import settings
from app.core.celery import celery_app
from app.api.router import api_router

# Sistema de Tarefas de Mídia
from app.services.webhook_service import webhook_service
from app.services.provider_registry import provider_registry
from app.database.session import create_tables

# Sistema de Compliance GDPR
from app.core.privacy import init_privacy_manager
from app.services.compliance.content_moderation import init_content_moderation_service
from app.services.compliance.audit_logger import init_audit_logger
from app.middleware.compliance.privacy_middleware import PrivacyMiddleware
from app.api.compliance_routes import router as compliance_router


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename=settings.LOG_FILE
)
logger = logging.getLogger(__name__)


# Redis connection
redis_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    global redis_client
    try:
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        await redis_client.ping()
        logger.info("✅ Redis connection established")
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        
    # Check Celery connectivity
    try:
        celery_inspect = celery_app.control.inspect()
        active = celery_inspect.active()
        logger.info(f"✅ Celery workers status: {len(active) if active else 0} workers")
    except Exception as e:
        logger.warning(f"⚠️ Celery inspection failed: {e}")
    
    # Inicializar Sistema de Tarefas de Mídia
    try:
        # Criar tabelas do banco de dados
        create_tables()
        logger.info("✅ Database tables created/verified")
        
        # Iniciar webhook service
        webhook_service.start_delivery_worker()
        logger.info("✅ Webhook service started")
        
        # Health check dos provedores
        provider_health = await provider_registry.health_check_all()
        active_providers = sum(1 for status in provider_health.values() if status.value == "active")
        logger.info(f"✅ Provider registry: {active_providers} providers active")
        
        logger.info("🎭 Media Tasks System initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Media Tasks System initialization failed: {e}")
    
    # Inicializar Sistema de Compliance GDPR
    try:
        if redis_client:
            # Inicializar serviços de compliance
            init_privacy_manager(redis_client)
            init_content_moderation_service(redis_client)
            init_audit_logger(redis_client)
            logger.info("🔒 Compliance system initialized successfully")
            logger.info("✅ GDPR privacy protection active")
            logger.info("✅ AI content moderation active")
            logger.info("✅ Audit logging active")
        else:
            logger.warning("⚠️ Compliance system not initialized - Redis unavailable")
    except Exception as e:
        logger.error(f"❌ Compliance system initialization failed: {e}")
    
    logger.info("🚀 VideoAI application started")
    
    yield
    
    # Shutdown
    try:
        # Parar webhook service
        webhook_service.stop_delivery_worker()
        logger.info("✅ Webhook service stopped")
        
        # Cleanup
        webhook_service.cleanup_old_deliveries(days=1)
        logger.info("✅ Webhook cleanup completed")
        
    except Exception as e:
        logger.warning(f"⚠️ Shutdown cleanup failed: {e}")
    
    if redis_client:
        await redis_client.close()
    logger.info("👋 VideoAI application stopped")


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

    
# Add middleware
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["*"]  # Configure properly in production
)

# Add compliance middleware for GDPR protection
app.add_middleware(PrivacyMiddleware, enable_logging=True)


# Custom middleware for request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.4f}s"
    )
    return response


# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Include compliance router
app.include_router(compliance_router)


# Health check endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check Redis
        redis_status = "connected"
        if redis_client:
            await redis_client.ping()
        else:
            redis_status = "disconnected"
            
        # Check Celery
        celery_status = "unknown"
        try:
            celery_inspect = celery_app.control.inspect()
            active = celery_inspect.active()
            celery_status = "connected" if active is not None else "disconnected"
        except:
            celery_status = "disconnected"
        
        # Check Media Tasks System
        webhook_stats = webhook_service.get_webhooks_stats()
        provider_stats = provider_registry.get_registry_stats()
        
        media_tasks_status = {
            "webhook_worker": "running" if webhook_stats["worker_running"] else "stopped",
            "active_providers": f"{provider_stats['active_providers']}/{provider_stats['total_providers']}",
            "webhook_success_rate": f"{webhook_stats['success_rate']*100:.1f}%"
        }
        
        # Check Compliance System
        compliance_status = {
            "privacy_manager": "active",
            "content_moderation": "active", 
            "audit_logger": "active",
            "gdpr_compliant": True
        }
        try:
            from app.core.privacy import get_privacy_manager
            from app.services.compliance.content_moderation import get_content_moderation_service
            from app.services.compliance.audit_logger import get_audit_logger
            
            # Test if services are working
            get_privacy_manager()
            get_content_moderation_service()
            get_audit_logger()
        except Exception as e:
            compliance_status = {
                "privacy_manager": "error",
                "content_moderation": "error",
                "audit_logger": "error", 
                "gdpr_compliant": False,
                "error": str(e)
            }
            
        return {
            "status": "healthy",
            "service": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "redis": redis_status,
            "celery": celery_status,
            "media_tasks": media_tasks_status,
            "compliance": compliance_status,
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "description": settings.DESCRIPTION,
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/health",
        "features": [
            "Image Generation",
            "Video Creation", 
            "Audio Transcription",
            "Subtitle Generation",
            "Async Task Processing",
            "Webhook Notifications",
            "Batch Processing",
            "GDPR Compliance",
            "AI Content Moderation",
            "Privacy Protection",
            "Audit Logging"
        ]
    }


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
