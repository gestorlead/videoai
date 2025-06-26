"""
FastAPI Application with Monitoring Integration

Exemplo de como integrar o sistema de monitoramento com a aplicação VideoAI.
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# Import monitoring components
from app.observability import setup_telemetry, TracingMiddleware, get_metrics
from app.observability.middleware import HealthCheckMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events for the application"""
    
    # Startup
    logger.info("Starting VideoAI with monitoring...")
    
    # Setup OpenTelemetry
    setup_telemetry(
        service_name="videoai",
        service_version="1.0.0",
        jaeger_endpoint=os.getenv("JAEGER_ENDPOINT", "http://localhost:14268/api/traces"),
        prometheus_port=int(os.getenv("PROMETHEUS_PORT", "8000")),
        enable_console_export=os.getenv("ENVIRONMENT") == "development"
    )
    
    logger.info("Monitoring setup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down VideoAI...")

# Create FastAPI app with monitoring
app = FastAPI(
    title="VideoAI API",
    description="AI-powered video and image generation platform",
    version="1.0.0",
    lifespan=lifespan
)

# Add monitoring middleware
app.add_middleware(HealthCheckMiddleware)
app.add_middleware(TracingMiddleware, exclude_paths=["/health", "/metrics", "/docs", "/openapi.json"])

# Metrics endpoint
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "videoai",
        "version": "1.0.0"
    }

# Alert webhook endpoint
@app.post("/api/v1/alerts/webhook")
async def alert_webhook(request: Request):
    """Webhook para receber alertas do AlertManager"""
    try:
        alert_data = await request.json()
        
        # Process alerts (log, send notifications, etc.)
        logger.warning(f"Alert received: {alert_data}")
        
        # Here you could:
        # - Send to Slack/Discord
        # - Send email notifications
        # - Trigger auto-scaling
        # - Store in database
        
        return {"status": "received"}
    
    except Exception as e:
        logger.error(f"Error processing alert: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to process alert"}
        )

# Example instrumented endpoint
@app.get("/api/v1/status")
async def get_status():
    """Get system status with custom metrics"""
    metrics = get_metrics()
    
    # Record custom business metric
    metrics.update_active_users(42)  # Example: 42 active users
    
    return {
        "status": "running",
        "monitoring": "enabled",
        "services": {
            "api": "healthy",
            "database": "healthy",
            "cache": "healthy",
            "queue": "healthy"
        }
    }

# Include existing VideoAI routes
# from app.api.v1.api import api_router
# app.include_router(api_router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    
    # Run with monitoring enabled
    uvicorn.run(
        "main_monitoring:app",
        host="0.0.0.0",
        port=5000,
        reload=True,
        log_level="info"
    )
