"""
Privacy and Data Retention Management for GDPR Compliance

Sistema gratuito de gestão de privacidade e retenção de dados.
"""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List
from enum import Enum
import redis
import json
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class DataCategory(Enum):
    """Categorias de dados para retenção GDPR"""
    RAW_PROMPT = "raw_prompt"
    GENERATED_IMAGE = "generated_image" 
    USER_METADATA = "user_metadata"
    AUDIT_LOG = "audit_log"
    SYSTEM_LOG = "system_log"
    PERSONAL_DATA = "personal_data"

class RetentionManager:
    """
    Gerenciador de retenção de dados conforme GDPR
    
    Implementa regras de retenção automática e minimização de dados.
    """
    
    # Regras de retenção GDPR
    RETENTION_RULES = {
        DataCategory.RAW_PROMPT: timedelta(hours=1),        # Deletar ASAP
        DataCategory.GENERATED_IMAGE: timedelta(days=30),   # Necessidade de negócio
        DataCategory.USER_METADATA: timedelta(days=90),     # Análise de uso
        DataCategory.AUDIT_LOG: timedelta(days=1095),       # Requisito legal (3 anos)
        DataCategory.SYSTEM_LOG: timedelta(days=365),       # Troubleshooting
        DataCategory.PERSONAL_DATA: timedelta(hours=24),    # Minimização máxima
    }
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        
    def schedule_deletion(self, obj_id: str, category: DataCategory, custom_ttl: Optional[timedelta] = None) -> bool:
        """
        Agenda deleção automática de dados
        
        Args:
            obj_id: ID único do objeto
            category: Categoria de dados
            custom_ttl: TTL customizado (opcional)
            
        Returns:
            bool: Sucesso da operação
        """
        try:
            ttl = custom_ttl or self.RETENTION_RULES[category]
            ttl_seconds = int(ttl.total_seconds())
            
            # Agendar deleção no Redis
            key = f"retention:{category.value}:{obj_id}"
            self.redis_client.setex(key, ttl_seconds, "scheduled_for_deletion")
            
            logger.info(f"Scheduled deletion for {obj_id} in {ttl}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to schedule deletion for {obj_id}: {e}")
            return False
    
    def is_expired(self, obj_id: str, category: DataCategory) -> bool:
        """Verifica se dados expiraram"""
        key = f"retention:{category.value}:{obj_id}"
        return not self.redis_client.exists(key)

class PersonalDataDetector:
    """
    Detector de dados pessoais em prompts e conteúdo
    
    Usa regex patterns para identificar dados pessoais básicos.
    """
    
    # Patterns para detecção de dados pessoais (básico)
    PERSONAL_DATA_PATTERNS = {
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
        'cpf': r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b',
        'name_patterns': [
            r'\b(?:nome|name|called|chamado)\s+(?:é|is|:)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'\b([A-Z][a-z]+\s+[A-Z][a-z]+)\s+(?:nasceu|born|b\.)',
        ]
    }
    
    def detect_personal_data(self, text: str) -> Dict[str, List[str]]:
        """
        Detecta dados pessoais em texto
        
        Args:
            text: Texto para análise
            
        Returns:
            Dict com tipos de dados encontrados
        """
        import re
        
        found_data = {}
        
        # Verificar email
        emails = re.findall(self.PERSONAL_DATA_PATTERNS['email'], text, re.IGNORECASE)
        if emails:
            found_data['emails'] = emails
        
        # Verificar telefone
        phones = re.findall(self.PERSONAL_DATA_PATTERNS['phone'], text)
        if phones:
            found_data['phones'] = phones
        
        # Verificar CPF
        cpfs = re.findall(self.PERSONAL_DATA_PATTERNS['cpf'], text)
        if cpfs:
            found_data['cpfs'] = cpfs
        
        return found_data
    
    def redact_personal_data(self, text: str) -> str:
        """
        Remove/redige dados pessoais do texto
        
        Args:
            text: Texto original
            
        Returns:
            Texto com dados pessoais removidos
        """
        import re
        
        redacted_text = text
        
        # Redação de emails
        redacted_text = re.sub(
            self.PERSONAL_DATA_PATTERNS['email'], 
            '[EMAIL_REDACTED]', 
            redacted_text, 
            flags=re.IGNORECASE
        )
        
        # Redação de telefones
        redacted_text = re.sub(
            self.PERSONAL_DATA_PATTERNS['phone'], 
            '[PHONE_REDACTED]', 
            redacted_text
        )
        
        # Redação de CPFs
        redacted_text = re.sub(
            self.PERSONAL_DATA_PATTERNS['cpf'], 
            '[CPF_REDACTED]', 
            redacted_text
        )
        
        return redacted_text

class PrivacyManager:
    """
    Gerenciador principal de privacidade
    
    Coordena retenção, detecção e direitos do titular.
    """
    
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client
        self.retention_manager = RetentionManager(redis_client)
        self.personal_data_detector = PersonalDataDetector()
    
    def process_prompt(self, prompt: str, user_id: str) -> Dict[str, Any]:
        """
        Processa prompt aplicando regras de privacidade
        
        Args:
            prompt: Prompt original
            user_id: ID do usuário
            
        Returns:
            Dict com prompt processado e metadados
        """
        # Detectar dados pessoais
        personal_data = self.personal_data_detector.detect_personal_data(prompt)
        
        # Redação se necessário
        processed_prompt = prompt
        if personal_data:
            processed_prompt = self.personal_data_detector.redact_personal_data(prompt)
            logger.warning(f"Personal data detected and redacted for user {user_id}")
        
        # Hash do prompt original (para auditoria)
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
        
        # Agendar deleção do prompt original
        self.retention_manager.schedule_deletion(
            prompt_hash, 
            DataCategory.RAW_PROMPT
        )
        
        # Se contém dados pessoais, agendar deleção mais rápida
        if personal_data:
            self.retention_manager.schedule_deletion(
                prompt_hash,
                DataCategory.PERSONAL_DATA
            )
        
        return {
            'processed_prompt': processed_prompt,
            'original_hash': prompt_hash,
            'personal_data_detected': bool(personal_data),
            'personal_data_types': list(personal_data.keys()) if personal_data else [],
            'redacted': prompt != processed_prompt
        }

# Instância global (será configurada na inicialização da app)
privacy_manager: Optional[PrivacyManager] = None

def get_privacy_manager() -> PrivacyManager:
    """Retorna instância global do privacy manager"""
    global privacy_manager
    if privacy_manager is None:
        raise RuntimeError("Privacy manager not initialized")
    return privacy_manager

def init_privacy_manager(redis_client: redis.Redis):
    """Inicializa privacy manager global"""
    global privacy_manager
    privacy_manager = PrivacyManager(redis_client)
