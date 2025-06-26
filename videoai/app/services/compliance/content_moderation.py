"""
Content Moderation Service - Open Source Implementation

Sistema gratuito de moderação de conteúdo usando Detoxify e outras ferramentas OSS.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import hashlib
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class ModerationResult(Enum):
    """Resultado da moderação"""
    APPROVED = "approved"
    REJECTED = "rejected"
    FLAGGED = "flagged"
    REQUIRES_REVIEW = "requires_review"

class ContentCategory(Enum):
    """Categorias de conteúdo"""
    TEXT_PROMPT = "text_prompt"
    GENERATED_IMAGE = "generated_image"
    USER_UPLOAD = "user_upload"

class ThreatLevel(Enum):
    """Níveis de ameaça"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class OpenSourceModerator:
    """
    Moderador baseado em ferramentas open source
    
    Usa Detoxify para análise de toxicidade em texto.
    """
    
    def __init__(self):
        self.detoxify_model = None
        self._load_models()
    
    def _load_models(self):
        """Carrega modelos de moderação"""
        try:
            # Importar Detoxify apenas quando necessário
            from detoxify import Detoxify
            self.detoxify_model = Detoxify('original')
            logger.info("Detoxify model loaded successfully")
        except ImportError:
            logger.warning("Detoxify not available. Install with: pip install detoxify")
        except Exception as e:
            logger.error(f"Failed to load Detoxify model: {e}")
    
    def analyze_text_toxicity(self, text: str) -> Dict[str, float]:
        """
        Analisa toxicidade do texto usando Detoxify
        
        Args:
            text: Texto para análise
            
        Returns:
            Dict com scores de toxicidade
        """
        if not self.detoxify_model:
            return self._fallback_text_analysis(text)
        
        try:
            results = self.detoxify_model.predict(text)
            return {
                'toxicity': float(results.get('toxicity', 0)),
                'severe_toxicity': float(results.get('severe_toxicity', 0)),
                'obscene': float(results.get('obscene', 0)),
                'threat': float(results.get('threat', 0)),
                'insult': float(results.get('insult', 0)),
                'identity_attack': float(results.get('identity_attack', 0))
            }
        except Exception as e:
            logger.error(f"Detoxify analysis failed: {e}")
            return self._fallback_text_analysis(text)
    
    def _fallback_text_analysis(self, text: str) -> Dict[str, float]:
        """
        Análise básica de fallback usando palavras-chave
        
        Args:
            text: Texto para análise
            
        Returns:
            Dict com scores básicos
        """
        # Lista básica de palavras problemáticas
        problematic_words = [
            'hate', 'kill', 'death', 'violence', 'terrorist', 'bomb',
            'weapon', 'drug', 'illegal', 'nude', 'sexual', 'explicit'
        ]
        
        text_lower = text.lower()
        found_count = sum(1 for word in problematic_words if word in text_lower)
        
        # Score básico baseado na proporção de palavras problemáticas
        toxicity_score = min(found_count / len(text.split()) * 10, 1.0)
        
        return {
            'toxicity': toxicity_score,
            'severe_toxicity': toxicity_score * 0.5,
            'obscene': toxicity_score * 0.3,
            'threat': toxicity_score * 0.4,
            'insult': toxicity_score * 0.3,
            'identity_attack': toxicity_score * 0.2
        }

class ContentModerationService:
    """
    Serviço principal de moderação de conteúdo
    
    Implementa pipeline completo de moderação usando ferramentas gratuitas.
    """
    
    # Thresholds de moderação
    TOXICITY_THRESHOLDS = {
        ThreatLevel.LOW: 0.3,
        ThreatLevel.MEDIUM: 0.5,
        ThreatLevel.HIGH: 0.7,
        ThreatLevel.CRITICAL: 0.9
    }
    
    # Palavras-chave proibidas (básico)
    PROHIBITED_KEYWORDS = [
        # Violência
        'terrorist', 'terrorism', 'bomb', 'explosive', 'weapon', 'gun',
        'violence', 'kill', 'murder', 'death', 'suicide',
        
        # Conteúdo sexual explícito
        'nude', 'naked', 'sex', 'sexual', 'explicit', 'porn', 'erotic',
        
        # Drogas ilegais
        'cocaine', 'heroin', 'meth', 'drug dealing', 'illegal drugs',
        
        # Discurso de ódio
        'hate speech', 'racist', 'nazi', 'fascist',
        
        # Atividades ilegais
        'money laundering', 'fraud', 'scam', 'illegal activity'
    ]
    
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.moderator = OpenSourceModerator()
        
    async def moderate_content(self, content: str, content_type: ContentCategory, user_id: str) -> Dict[str, Any]:
        """
        Modera conteúdo usando pipeline completo
        
        Args:
            content: Conteúdo para moderação
            content_type: Tipo de conteúdo
            user_id: ID do usuário
            
        Returns:
            Dict com resultado da moderação
        """
        moderation_id = hashlib.md5(f"{content}{user_id}{datetime.utcnow()}".encode()).hexdigest()
        
        # 1. Análise de palavras-chave
        keyword_check = self._check_prohibited_keywords(content)
        
        # 2. Análise de toxicidade (apenas para texto)
        toxicity_scores = {}
        if content_type == ContentCategory.TEXT_PROMPT:
            toxicity_scores = self.moderator.analyze_text_toxicity(content)
        
        # 3. Determinar resultado da moderação
        result = self._determine_moderation_result(keyword_check, toxicity_scores)
        
        # 4. Calcular nível de ameaça
        threat_level = self._calculate_threat_level(keyword_check, toxicity_scores)
        
        # 5. Gerar relatório de moderação
        moderation_report = {
            'moderation_id': moderation_id,
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': user_id,
            'content_type': content_type.value,
            'content_hash': hashlib.sha256(content.encode()).hexdigest(),
            'result': result.value,
            'threat_level': threat_level.value,
            'keyword_check': keyword_check,
            'toxicity_scores': toxicity_scores,
            'approved': result == ModerationResult.APPROVED
        }
        
        # 6. Armazenar relatório (TTL de 30 dias)
        await self._store_moderation_report(moderation_report)
        
        # 7. Log para auditoria
        logger.info(f"Content moderation completed: {moderation_id} - {result.value}")
        
        return moderation_report
    
    def _check_prohibited_keywords(self, content: str) -> Dict[str, Any]:
        """
        Verifica palavras-chave proibidas
        
        Args:
            content: Conteúdo para verificação
            
        Returns:
            Dict com resultado da verificação
        """
        content_lower = content.lower()
        found_keywords = []
        
        for keyword in self.PROHIBITED_KEYWORDS:
            if keyword in content_lower:
                found_keywords.append(keyword)
        
        return {
            'found_keywords': found_keywords,
            'keyword_count': len(found_keywords),
            'has_prohibited_content': len(found_keywords) > 0
        }
    
    def _determine_moderation_result(self, keyword_check: Dict, toxicity_scores: Dict) -> ModerationResult:
        """
        Determina resultado final da moderação
        
        Args:
            keyword_check: Resultado da verificação de palavras-chave
            toxicity_scores: Scores de toxicidade
            
        Returns:
            Resultado da moderação
        """
        # Rejeitar imediatamente se palavras-chave proibidas
        if keyword_check['has_prohibited_content']:
            return ModerationResult.REJECTED
        
        # Verificar toxicidade se disponível
        if toxicity_scores:
            max_toxicity = max(toxicity_scores.values())
            
            if max_toxicity >= self.TOXICITY_THRESHOLDS[ThreatLevel.CRITICAL]:
                return ModerationResult.REJECTED
            elif max_toxicity >= self.TOXICITY_THRESHOLDS[ThreatLevel.HIGH]:
                return ModerationResult.REQUIRES_REVIEW
            elif max_toxicity >= self.TOXICITY_THRESHOLDS[ThreatLevel.MEDIUM]:
                return ModerationResult.FLAGGED
        
        return ModerationResult.APPROVED
    
    def _calculate_threat_level(self, keyword_check: Dict, toxicity_scores: Dict) -> ThreatLevel:
        """
        Calcula nível de ameaça
        
        Args:
            keyword_check: Resultado da verificação de palavras-chave
            toxicity_scores: Scores de toxicidade
            
        Returns:
            Nível de ameaça
        """
        # Palavras-chave proibidas = nível crítico
        if keyword_check['keyword_count'] > 2:
            return ThreatLevel.CRITICAL
        elif keyword_check['has_prohibited_content']:
            return ThreatLevel.HIGH
        
        # Verificar toxicidade
        if toxicity_scores:
            max_toxicity = max(toxicity_scores.values())
            
            if max_toxicity >= self.TOXICITY_THRESHOLDS[ThreatLevel.CRITICAL]:
                return ThreatLevel.CRITICAL
            elif max_toxicity >= self.TOXICITY_THRESHOLDS[ThreatLevel.HIGH]:
                return ThreatLevel.HIGH
            elif max_toxicity >= self.TOXICITY_THRESHOLDS[ThreatLevel.MEDIUM]:
                return ThreatLevel.MEDIUM
        
        return ThreatLevel.LOW
    
    async def _store_moderation_report(self, report: Dict[str, Any]):
        """
        Armazena relatório de moderação no Redis
        
        Args:
            report: Relatório de moderação
        """
        try:
            key = f"moderation:report:{report['moderation_id']}"
            # TTL de 30 dias
            ttl = 30 * 24 * 60 * 60
            
            self.redis_client.setex(key, ttl, json.dumps(report))
            
            # Índice por usuário
            user_key = f"moderation:user:{report['user_id']}"
            self.redis_client.lpush(user_key, report['moderation_id'])
            self.redis_client.expire(user_key, ttl)
            
        except Exception as e:
            logger.error(f"Failed to store moderation report: {e}")
    
    async def get_user_moderation_history(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Obtém histórico de moderação do usuário
        
        Args:
            user_id: ID do usuário
            limit: Limite de registros
            
        Returns:
            Lista de relatórios de moderação
        """
        try:
            user_key = f"moderation:user:{user_id}"
            moderation_ids = self.redis_client.lrange(user_key, 0, limit - 1)
            
            reports = []
            for mod_id in moderation_ids:
                report_key = f"moderation:report:{mod_id.decode()}"
                report_data = self.redis_client.get(report_key)
                if report_data:
                    reports.append(json.loads(report_data))
            
            return reports
            
        except Exception as e:
            logger.error(f"Failed to get user moderation history: {e}")
            return []
    
    async def get_moderation_stats(self, hours: int = 24) -> Dict[str, Any]:
        """
        Obtém estatísticas de moderação
        
        Args:
            hours: Período em horas
            
        Returns:
            Dict com estatísticas
        """
        try:
            # Buscar todos os relatórios recentes
            pattern = "moderation:report:*"
            keys = self.redis_client.keys(pattern)
            
            stats = {
                'total_moderated': 0,
                'approved': 0,
                'rejected': 0,
                'flagged': 0,
                'requires_review': 0,
                'threat_levels': {level.value: 0 for level in ThreatLevel},
                'content_types': {cat.value: 0 for cat in ContentCategory}
            }
            
            cutoff_time = datetime.utcnow().timestamp() - (hours * 3600)
            
            for key in keys:
                report_data = self.redis_client.get(key)
                if report_data:
                    report = json.loads(report_data)
                    report_time = datetime.fromisoformat(report['timestamp']).timestamp()
                    
                    if report_time >= cutoff_time:
                        stats['total_moderated'] += 1
                        stats[report['result']] += 1
                        stats['threat_levels'][report['threat_level']] += 1
                        stats['content_types'][report['content_type']] += 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get moderation stats: {e}")
            return {}

# Instância global
content_moderation_service: Optional[ContentModerationService] = None

def get_content_moderation_service() -> ContentModerationService:
    """Retorna instância global do serviço de moderação"""
    global content_moderation_service
    if content_moderation_service is None:
        raise RuntimeError("Content moderation service not initialized")
    return content_moderation_service

def init_content_moderation_service(redis_client):
    """Inicializa serviço de moderação global"""
    global content_moderation_service
    content_moderation_service = ContentModerationService(redis_client)
