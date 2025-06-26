"""
Privacy Middleware for GDPR Compliance

Middleware para interceptar e processar requests aplicando regras de privacidade.
"""

import logging
import time
from typing import Dict, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from videoai.app.core.privacy import get_privacy_manager, DataCategory

logger = logging.getLogger(__name__)

class PrivacyMiddleware(BaseHTTPMiddleware):
    """
    Middleware para aplicação automática de regras de privacidade
    
    Intercepta requests e aplica:
    - Detecção de dados pessoais
    - Redação automática
    - Logging de auditoria
    - Agendamento de deleção
    """
    
    # Endpoints que processam dados sensíveis
    SENSITIVE_ENDPOINTS = [
        "/api/v1/generate",
        "/api/v1/prompt/optimize",
        "/api/v1/batch/process",
        "/api/v1/user/profile"
    ]
    
    def __init__(self, app, enable_logging: bool = True):
        super().__init__(app)
        self.enable_logging = enable_logging
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Processa request aplicando regras de privacidade
        
        Args:
            request: Request HTTP
            call_next: Próximo middleware/handler
            
        Returns:
            Response processada
        """
        start_time = time.time()
        
        # Verificar se endpoint é sensível
        if self._is_sensitive_endpoint(request.url.path):
            # Processar dados de entrada
            privacy_result = await self._process_request_privacy(request)
            
            if privacy_result.get('blocked'):
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "Privacy violation detected",
                        "message": "Request contains prohibited personal data",
                        "details": privacy_result
                    }
                )
        
        # Processar request normalmente
        response = await call_next(request)
        
        # Log de auditoria se habilitado
        if self.enable_logging:
            await self._log_request_audit(request, response, start_time)
        
        # Adicionar headers de privacidade
        self._add_privacy_headers(response)
        
        return response
    
    def _is_sensitive_endpoint(self, path: str) -> bool:
        """
        Verifica se endpoint processa dados sensíveis
        
        Args:
            path: Caminho do endpoint
            
        Returns:
            bool: True se sensível
        """
        return any(sensitive in path for sensitive in self.SENSITIVE_ENDPOINTS)
    
    async def _process_request_privacy(self, request: Request) -> Dict[str, Any]:
        """
        Processa dados de entrada aplicando regras de privacidade
        
        Args:
            request: Request HTTP
            
        Returns:
            Dict com resultado do processamento
        """
        try:
            privacy_manager = get_privacy_manager()
            
            # Extrair dados do request
            request_data = await self._extract_request_data(request)
            
            if not request_data:
                return {'processed': False, 'blocked': False}
            
            # Obter user_id (pode vir de header, token, etc.)
            user_id = self._extract_user_id(request)
            
            privacy_result = {
                'processed': True,
                'blocked': False,
                'personal_data_detected': False,
                'redacted_fields': []
            }
            
            # Processar cada campo de texto
            for field_name, field_value in request_data.items():
                if isinstance(field_value, str) and field_value.strip():
                    # Processar com privacy manager
                    result = privacy_manager.process_prompt(field_value, user_id)
                    
                    if result['personal_data_detected']:
                        privacy_result['personal_data_detected'] = True
                        privacy_result['redacted_fields'].append(field_name)
                        
                        # Bloquear se dados pessoais críticos
                        if 'emails' in result['personal_data_types'] or 'cpfs' in result['personal_data_types']:
                            privacy_result['blocked'] = True
                            privacy_result['reason'] = f"Critical personal data detected in field: {field_name}"
                            break
            
            return privacy_result
            
        except Exception as e:
            logger.error(f"Privacy processing failed: {e}")
            return {'processed': False, 'blocked': False, 'error': str(e)}
    
    async def _extract_request_data(self, request: Request) -> Dict[str, Any]:
        """
        Extrai dados do request para análise
        
        Args:
            request: Request HTTP
            
        Returns:
            Dict com dados extraídos
        """
        try:
            # Tentar extrair JSON body
            if request.headers.get('content-type', '').startswith('application/json'):
                body = await request.body()
                if body:
                    import json
                    return json.loads(body)
            
            # Tentar extrair form data
            elif request.headers.get('content-type', '').startswith('application/x-www-form-urlencoded'):
                form = await request.form()
                return dict(form)
            
            # Query parameters
            return dict(request.query_params)
            
        except Exception as e:
            logger.error(f"Failed to extract request data: {e}")
            return {}
    
    def _extract_user_id(self, request: Request) -> str:
        """
        Extrai user_id do request
        
        Args:
            request: Request HTTP
            
        Returns:
            User ID ou 'anonymous'
        """
        # Tentar extrair de headers
        user_id = request.headers.get('x-user-id')
        if user_id:
            return user_id
        
        # Tentar extrair de Authorization header (JWT)
        auth_header = request.headers.get('authorization')
        if auth_header and auth_header.startswith('Bearer '):
            # Aqui você poderia decodificar o JWT para extrair o user_id
            # Por simplicidade, usamos o hash do token
            import hashlib
            token = auth_header[7:]  # Remove 'Bearer '
            return hashlib.md5(token.encode()).hexdigest()[:8]
        
        # Fallback para IP do cliente
        client_ip = request.client.host if request.client else 'unknown'
        return f"ip_{client_ip.replace('.', '_')}"
    
    async def _log_request_audit(self, request: Request, response: Response, start_time: float):
        """
        Log de auditoria do request
        
        Args:
            request: Request HTTP
            response: Response HTTP
            start_time: Timestamp de início
        """
        try:
            privacy_manager = get_privacy_manager()
            
            processing_time = time.time() - start_time
            user_id = self._extract_user_id(request)
            
            audit_data = {
                'method': request.method,
                'path': request.url.path,
                'status_code': response.status_code,
                'processing_time_ms': round(processing_time * 1000, 2),
                'user_agent': request.headers.get('user-agent', 'unknown'),
                'content_length': response.headers.get('content-length', 0)
            }
            
            # Log via privacy manager
            privacy_manager.log_data_processing(
                user_id=user_id,
                operation='api_request',
                data_type='http_request',
                metadata=audit_data
            )
            
        except Exception as e:
            logger.error(f"Audit logging failed: {e}")
    
    def _add_privacy_headers(self, response: Response):
        """
        Adiciona headers de privacidade à response
        
        Args:
            response: Response HTTP
        """
        # Headers de privacidade e segurança
        privacy_headers = {
            'X-Privacy-Policy': 'GDPR-Compliant',
            'X-Data-Retention': 'Minimized',
            'X-Content-Security-Policy': "default-src 'self'",
            'X-Frame-Options': 'DENY',
            'X-Content-Type-Options': 'nosniff'
        }
        
        for header, value in privacy_headers.items():
            response.headers[header] = value

class DataRetentionMiddleware(BaseHTTPMiddleware):
    """
    Middleware para aplicação de regras de retenção de dados
    
    Verifica se dados expiraram antes de processamento.
    """
    
    def __init__(self, app):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Verifica retenção de dados antes do processamento
        
        Args:
            request: Request HTTP
            call_next: Próximo middleware/handler
            
        Returns:
            Response processada
        """
        # Verificar se request contém IDs de dados que podem ter expirado
        data_ids = self._extract_data_ids(request)
        
        if data_ids:
            expired_ids = await self._check_data_expiration(data_ids)
            
            if expired_ids:
                return JSONResponse(
                    status_code=410,  # Gone
                    content={
                        "error": "Data expired",
                        "message": "Requested data has been deleted due to retention policy",
                        "expired_ids": expired_ids
                    }
                )
        
        return await call_next(request)
    
    def _extract_data_ids(self, request: Request) -> list:
        """
        Extrai IDs de dados do request
        
        Args:
            request: Request HTTP
            
        Returns:
            Lista de IDs de dados
        """
        data_ids = []
        
        # Extrair de path parameters
        path_parts = request.url.path.split('/')
        for part in path_parts:
            if part.isdigit() or (len(part) == 32 and part.isalnum()):  # ID ou hash
                data_ids.append(part)
        
        # Extrair de query parameters
        for key, value in request.query_params.items():
            if 'id' in key.lower() or 'hash' in key.lower():
                data_ids.append(value)
        
        return data_ids
    
    async def _check_data_expiration(self, data_ids: list) -> list:
        """
        Verifica se dados expiraram
        
        Args:
            data_ids: Lista de IDs de dados
            
        Returns:
            Lista de IDs expirados
        """
        try:
            privacy_manager = get_privacy_manager()
            expired_ids = []
            
            for data_id in data_ids:
                # Verificar diferentes categorias de dados
                for category in DataCategory:
                    if privacy_manager.retention_manager.is_expired(data_id, category):
                        expired_ids.append(data_id)
                        break
            
            return expired_ids
            
        except Exception as e:
            logger.error(f"Data expiration check failed: {e}")
            return []
