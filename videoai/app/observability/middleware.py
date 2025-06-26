"""
FastAPI Middleware for Observability

Middleware personalizado para adicionar tracing e métricas às requisições HTTP.
"""

import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from .telemetry import get_tracer
from .metrics import get_metrics

class TracingMiddleware(BaseHTTPMiddleware):
    """
    Middleware para adicionar tracing e métricas automáticas às requisições
    """
    
    def __init__(self, app, exclude_paths: list = None):
        super().__init__(app)
        self.tracer = get_tracer()
        self.metrics = get_metrics()
        self.exclude_paths = exclude_paths or ["/health", "/metrics", "/docs", "/openapi.json"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip monitoring for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        # Generate correlation ID
        correlation_id = str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        
        # Extract user information if available
        user_id = getattr(request.state, 'user_id', None)
        
        # Start timing
        start_time = time.time()
        
        # Create span for the request
        with self.tracer.start_as_current_span(
            f"{request.method} {request.url.path}",
            attributes={
                "http.method": request.method,
                "http.url": str(request.url),
                "http.scheme": request.url.scheme,
                "http.host": request.url.hostname,
                "http.target": request.url.path,
                "http.user_agent": request.headers.get("user-agent", ""),
                "http.correlation_id": correlation_id,
                "user.id": user_id if user_id else "anonymous",
            }
        ) as span:
            
            try:
                # Process request
                response = await call_next(request)
                
                # Calculate duration
                duration = time.time() - start_time
                
                # Add response attributes to span
                span.set_attributes({
                    "http.status_code": response.status_code,
                    "http.response.size": response.headers.get("content-length", 0),
                    "http.duration": duration
                })
                
                # Record metrics
                self.metrics.record_http_request(
                    method=request.method,
                    endpoint=request.url.path,
                    status_code=response.status_code,
                    duration=duration,
                    user_id=user_id
                )
                
                # Add correlation ID to response headers
                response.headers["X-Correlation-ID"] = correlation_id
                
                return response
                
            except Exception as e:
                # Calculate duration for failed requests
                duration = time.time() - start_time
                
                # Add error attributes to span
                span.set_attributes({
                    "http.status_code": 500,
                    "error": True,
                    "error.type": type(e).__name__,
                    "error.message": str(e),
                    "http.duration": duration
                })
                
                # Record exception in span
                span.record_exception(e)
                
                # Record error metrics
                self.metrics.record_http_request(
                    method=request.method,
                    endpoint=request.url.path,
                    status_code=500,
                    duration=duration,
                    user_id=user_id
                )
                
                # Re-raise the exception
                raise

class HealthCheckMiddleware(BaseHTTPMiddleware):
    """
    Middleware para health checks simples
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path == "/health":
            return Response(
                content='{"status": "healthy", "service": "videoai"}',
                media_type="application/json",
                status_code=200
            )
        
        return await call_next(request)

class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware dedicado apenas para coleta de métricas (mais leve)
    """
    
    def __init__(self, app, exclude_paths: list = None):
        super().__init__(app)
        self.metrics = get_metrics()
        self.exclude_paths = exclude_paths or ["/health", "/metrics"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        start_time = time.time()
        user_id = getattr(request.state, 'user_id', None)
        
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            self.metrics.record_http_request(
                method=request.method,
                endpoint=request.url.path,
                status_code=response.status_code,
                duration=duration,
                user_id=user_id
            )
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            
            self.metrics.record_http_request(
                method=request.method,
                endpoint=request.url.path,
                status_code=500,
                duration=duration,
                user_id=user_id
            )
            
            raise
