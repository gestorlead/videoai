"""
Audit Logger for Compliance

Sistema de auditoria para tracking de operações e compliance.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum
import hashlib
import redis

logger = logging.getLogger(__name__)

class AuditEventType(Enum):
    """Tipos de eventos de auditoria"""
    USER_ACCESS = "user_access"
    DATA_PROCESSING = "data_processing"
    CONTENT_GENERATION = "content_generation"
    CONTENT_MODERATION = "content_moderation"
    DATA_EXPORT = "data_export"
    DATA_DELETION = "data_deletion"
    PRIVACY_SETTINGS = "privacy_settings"
    SYSTEM_ERROR = "system_error"
    SECURITY_VIOLATION = "security_violation"

class ComplianceLevel(Enum):
    """Níveis de compliance"""
    COMPLIANT = "compliant"
    WARNING = "warning"
    VIOLATION = "violation"
    CRITICAL = "critical"

class AuditLogger:
    """
    Logger de auditoria para compliance
    
    Registra todos os eventos relevantes para auditoria e compliance.
    """
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        
    def log_event(
        self,
        event_type: AuditEventType,
        user_id: str,
        compliance_level: ComplianceLevel = ComplianceLevel.COMPLIANT,
        details: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        Registra evento de auditoria
        
        Args:
            event_type: Tipo do evento
            user_id: ID do usuário
            compliance_level: Nível de compliance
            details: Detalhes do evento
            metadata: Metadados adicionais
            
        Returns:
            ID do evento de auditoria
        """
        try:
            timestamp = datetime.utcnow()
            event_id = hashlib.md5(
                f"{event_type.value}{user_id}{timestamp.isoformat()}".encode()
            ).hexdigest()
            
            audit_event = {
                'event_id': event_id,
                'timestamp': timestamp.isoformat(),
                'event_type': event_type.value,
                'user_id': user_id,
                'compliance_level': compliance_level.value,
                'details': details or {},
                'metadata': metadata or {},
                'source': 'videoai_platform'
            }
            
            # Armazenar no Redis com TTL de 3 anos (requisito legal)
            ttl_seconds = 3 * 365 * 24 * 60 * 60
            
            # Chave principal do evento
            event_key = f"audit:event:{event_id}"
            self.redis_client.setex(event_key, ttl_seconds, json.dumps(audit_event))
            
            # Índice por usuário
            user_index_key = f"audit:user:{user_id}"
            self.redis_client.lpush(user_index_key, event_id)
            self.redis_client.expire(user_index_key, ttl_seconds)
            
            # Índice por tipo de evento
            type_index_key = f"audit:type:{event_type.value}"
            self.redis_client.lpush(type_index_key, event_id)
            self.redis_client.expire(type_index_key, ttl_seconds)
            
            # Índice por nível de compliance
            compliance_index_key = f"audit:compliance:{compliance_level.value}"
            self.redis_client.lpush(compliance_index_key, event_id)
            self.redis_client.expire(compliance_index_key, ttl_seconds)
            
            # Índice temporal (para relatórios)
            date_key = timestamp.strftime("%Y-%m-%d")
            daily_index_key = f"audit:daily:{date_key}"
            self.redis_client.lpush(daily_index_key, event_id)
            self.redis_client.expire(daily_index_key, ttl_seconds)
            
            logger.info(f"Audit event logged: {event_id} - {event_type.value}")
            return event_id
            
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
            return ""
    
    def get_user_audit_trail(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Obtém trilha de auditoria do usuário
        
        Args:
            user_id: ID do usuário
            limit: Limite de eventos
            
        Returns:
            Lista de eventos de auditoria
        """
        try:
            user_index_key = f"audit:user:{user_id}"
            event_ids = self.redis_client.lrange(user_index_key, 0, limit - 1)
            
            events = []
            for event_id in event_ids:
                event_key = f"audit:event:{event_id.decode()}"
                event_data = self.redis_client.get(event_key)
                if event_data:
                    events.append(json.loads(event_data))
            
            return sorted(events, key=lambda x: x['timestamp'], reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to get user audit trail: {e}")
            return []
    
    def get_compliance_violations(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Obtém violações de compliance recentes
        
        Args:
            hours: Período em horas
            
        Returns:
            Lista de violações
        """
        try:
            violations = []
            
            # Buscar violações e eventos críticos
            for level in [ComplianceLevel.VIOLATION, ComplianceLevel.CRITICAL]:
                compliance_key = f"audit:compliance:{level.value}"
                event_ids = self.redis_client.lrange(compliance_key, 0, 1000)
                
                cutoff_time = datetime.utcnow() - timedelta(hours=hours)
                
                for event_id in event_ids:
                    event_key = f"audit:event:{event_id.decode()}"
                    event_data = self.redis_client.get(event_key)
                    if event_data:
                        event = json.loads(event_data)
                        event_time = datetime.fromisoformat(event['timestamp'])
                        
                        if event_time >= cutoff_time:
                            violations.append(event)
            
            return sorted(violations, key=lambda x: x['timestamp'], reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to get compliance violations: {e}")
            return []
    
    def generate_compliance_report(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Gera relatório de compliance para período
        
        Args:
            start_date: Data de início
            end_date: Data de fim
            
        Returns:
            Relatório de compliance
        """
        try:
            report = {
                'report_id': hashlib.md5(f"{start_date}{end_date}".encode()).hexdigest(),
                'period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'generated_at': datetime.utcnow().isoformat(),
                'summary': {
                    'total_events': 0,
                    'compliance_levels': {level.value: 0 for level in ComplianceLevel},
                    'event_types': {event_type.value: 0 for event_type in AuditEventType},
                    'unique_users': set()
                },
                'violations': [],
                'trends': {}
            }
            
            # Iterar por dias no período
            current_date = start_date.date()
            end_date_only = end_date.date()
            
            daily_counts = {}
            
            while current_date <= end_date_only:
                date_key = current_date.strftime("%Y-%m-%d")
                daily_index_key = f"audit:daily:{date_key}"
                
                event_ids = self.redis_client.lrange(daily_index_key, 0, -1)
                daily_count = 0
                
                for event_id in event_ids:
                    event_key = f"audit:event:{event_id.decode()}"
                    event_data = self.redis_client.get(event_key)
                    if event_data:
                        event = json.loads(event_data)
                        event_time = datetime.fromisoformat(event['timestamp'])
                        
                        # Verificar se está no período
                        if start_date <= event_time <= end_date:
                            report['summary']['total_events'] += 1
                            report['summary']['compliance_levels'][event['compliance_level']] += 1
                            report['summary']['event_types'][event['event_type']] += 1
                            report['summary']['unique_users'].add(event['user_id'])
                            daily_count += 1
                            
                            # Adicionar violações
                            if event['compliance_level'] in ['violation', 'critical']:
                                report['violations'].append(event)
                
                daily_counts[date_key] = daily_count
                current_date = current_date + timedelta(days=1)
            
            # Converter set para count
            report['summary']['unique_users'] = len(report['summary']['unique_users'])
            
            # Adicionar tendências
            report['trends']['daily_events'] = daily_counts
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate compliance report: {e}")
            return {}
    
    def log_data_access(self, user_id: str, data_type: str, operation: str, metadata: Dict[str, Any] = None):
        """Registra acesso a dados"""
        self.log_event(
            event_type=AuditEventType.DATA_PROCESSING,
            user_id=user_id,
            compliance_level=ComplianceLevel.COMPLIANT,
            details={
                'data_type': data_type,
                'operation': operation
            },
            metadata=metadata
        )
    
    def log_content_generation(self, user_id: str, prompt_hash: str, model_used: str, metadata: Dict[str, Any] = None):
        """Registra geração de conteúdo"""
        self.log_event(
            event_type=AuditEventType.CONTENT_GENERATION,
            user_id=user_id,
            compliance_level=ComplianceLevel.COMPLIANT,
            details={
                'prompt_hash': prompt_hash,
                'model_used': model_used
            },
            metadata=metadata
        )
    
    def log_moderation_result(self, user_id: str, moderation_result: str, threat_level: str, metadata: Dict[str, Any] = None):
        """Registra resultado de moderação"""
        # Determinar nível de compliance baseado no resultado
        compliance_level = ComplianceLevel.COMPLIANT
        if moderation_result == 'rejected':
            compliance_level = ComplianceLevel.VIOLATION
        elif threat_level in ['high', 'critical']:
            compliance_level = ComplianceLevel.WARNING
        
        self.log_event(
            event_type=AuditEventType.CONTENT_MODERATION,
            user_id=user_id,
            compliance_level=compliance_level,
            details={
                'moderation_result': moderation_result,
                'threat_level': threat_level
            },
            metadata=metadata
        )
    
    def log_privacy_operation(self, user_id: str, operation: str, metadata: Dict[str, Any] = None):
        """Registra operações de privacidade"""
        event_type_map = {
            'data_export': AuditEventType.DATA_EXPORT,
            'data_deletion': AuditEventType.DATA_DELETION,
            'privacy_settings_update': AuditEventType.PRIVACY_SETTINGS
        }
        
        event_type = event_type_map.get(operation, AuditEventType.DATA_PROCESSING)
        
        self.log_event(
            event_type=event_type,
            user_id=user_id,
            compliance_level=ComplianceLevel.COMPLIANT,
            details={'operation': operation},
            metadata=metadata
        )

# Instância global
audit_logger: Optional[AuditLogger] = None

def get_audit_logger() -> AuditLogger:
    """Retorna instância global do audit logger"""
    global audit_logger
    if audit_logger is None:
        raise RuntimeError("Audit logger not initialized")
    return audit_logger

def init_audit_logger(redis_client: redis.Redis):
    """Inicializa audit logger global"""
    global audit_logger
    audit_logger = AuditLogger(redis_client)
