"""
Models for Prompt Testing System
Modelos SQLAlchemy para sistema de teste e refinamento de prompts
"""

from sqlalchemy import Column, String, DateTime, Text, JSON, Float, Integer, Boolean, ForeignKey, Index
from datetime import datetime
from typing import Dict, Any, Optional
import uuid

from ..database.session import Base


class PromptTest(Base):
    """Tabela principal de testes de prompts"""
    __tablename__ = "prompt_tests"
    
    # Identificação
    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(50), nullable=False)
    
    # Configuração do teste
    test_type = Column(String(20), nullable=False)  # ab_test, iterative, multivariate
    test_name = Column(String(200))
    base_prompt = Column(Text, nullable=False)
    
    # Configurações
    sample_size = Column(Integer, default=50)
    confidence_level = Column(Float, default=0.95)
    max_duration_hours = Column(Integer, default=24)
    auto_winner_threshold = Column(Float, default=0.2)
    
    # Métricas alvo
    target_metrics = Column(JSON, default=list)  # Lista de métricas
    
    # Status
    status = Column(String(20), default="active")  # active, completed, cancelled
    winner_variant_id = Column(String(50))
    
    # Resultados
    total_samples = Column(Integer, default=0)
    confidence_score = Column(Float)
    improvement_percentage = Column(Float)
    statistical_significance = Column(Boolean)
    optimal_prompt = Column(Text)
    
    # Metadados
    metadata = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # Índices para performance
    __table_args__ = (
        Index('idx_user_status', 'user_id', 'status'),
        Index('idx_test_type', 'test_type'),
        Index('idx_created_at', 'created_at'),
    )


class PromptVariant(Base):
    """Variantes de prompt para teste"""
    __tablename__ = "prompt_variants"
    
    # Identificação
    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    test_id = Column(String(50), ForeignKey("prompt_tests.id"), nullable=False)
    variant_id = Column(String(50), nullable=False)  # ID local dentro do teste
    
    # Configuração da variante
    prompt = Column(Text, nullable=False)
    style_modifiers = Column(JSON, default=list)
    technical_params = Column(JSON, default=dict)
    weight = Column(Float, default=1.0)
    description = Column(Text)
    tags = Column(JSON, default=list)
    
    # Estatísticas
    sample_count = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
    avg_generation_time = Column(Float)
    avg_quality_score = Column(Float)
    total_cost = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Índices
    __table_args__ = (
        Index('idx_test_variant', 'test_id', 'variant_id', unique=True),
    )


class PromptTestResult(Base):
    """Resultados individuais de teste de prompt"""
    __tablename__ = "prompt_test_results"
    
    # Identificação
    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    test_id = Column(String(50), ForeignKey("prompt_tests.id"), nullable=False)
    variant_id = Column(String(50), nullable=False)
    
    # Dados do resultado
    prompt_used = Column(Text, nullable=False)
    generation_time = Column(Float, nullable=False)
    output_url = Column(String(500))
    provider_id = Column(String(100))
    cost = Column(Float, default=0.0)
    
    # Métricas calculadas
    metrics = Column(JSON, default=dict)  # {metric_name: value}
    
    # Feedback do usuário
    user_rating = Column(Float)  # 1.0 - 5.0
    user_comments = Column(Text)
    preferred_aspects = Column(JSON, default=list)
    suggested_improvements = Column(JSON, default=list)
    
    # Metadados técnicos
    metadata = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Índices
    __table_args__ = (
        Index('idx_test_created', 'test_id', 'created_at'),
        Index('idx_variant_results', 'variant_id'),
    )


class PromptOptimizationRule(Base):
    """Regras de otimização de prompts"""
    __tablename__ = "prompt_optimization_rules"
    
    # Identificação
    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Configuração da regra
    name = Column(String(100), nullable=False, unique=True)
    pattern = Column(Text, nullable=False)  # Regex pattern
    replacement = Column(Text, nullable=False)
    strategy = Column(String(50), nullable=False)  # OptimizationStrategy enum
    confidence = Column(Float, default=0.5)
    description = Column(Text)
    
    # Estatísticas de uso
    usage_count = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
    avg_improvement = Column(Float, default=0.0)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime)
    
    # Índices
    __table_args__ = (
        Index('idx_strategy_active', 'strategy', 'is_active'),
        Index('idx_success_rate', 'success_rate'),
    )


class PromptLearningPattern(Base):
    """Padrões aprendidos de otimização"""
    __tablename__ = "prompt_learning_patterns"
    
    # Identificação
    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Padrão
    pattern_key = Column(String(200), nullable=False, index=True)
    base_prompt = Column(Text, nullable=False)
    optimized_prompt = Column(Text, nullable=False)
    
    # Performance
    performance_score = Column(Float, nullable=False)
    metrics_improvement = Column(JSON, default=dict)
    
    # Contexto
    applied_rules = Column(JSON, default=list)
    test_id = Column(String(50), ForeignKey("prompt_tests.id"))
    
    # Uso
    usage_count = Column(Integer, default=1)
    last_used = Column(DateTime, default=datetime.utcnow)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Índices
    __table_args__ = (
        Index('idx_pattern_performance', 'pattern_key', 'performance_score'),
    )


class PromptAnalytics(Base):
    """Analytics agregados de testes de prompts"""
    __tablename__ = "prompt_analytics"
    
    # Identificação
    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(50), nullable=False)
    
    # Período
    date = Column(DateTime, nullable=False)
    period_type = Column(String(20), default="daily")  # daily, weekly, monthly
    
    # Métricas agregadas
    total_tests = Column(Integer, default=0)
    total_results = Column(Integer, default=0)
    avg_improvement = Column(Float, default=0.0)
    success_rate = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)
    
    # Distribuição por tipo
    test_types_distribution = Column(JSON, default=dict)
    metrics_performance = Column(JSON, default=dict)
    
    # Top performers
    best_prompts = Column(JSON, default=list)
    most_effective_rules = Column(JSON, default=list)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Índices
    __table_args__ = (
        Index('idx_user_date', 'user_id', 'date', unique=True),
        Index('idx_period_type', 'period_type'),
    )


# Relacionamentos implícitos através de foreign keys
# PromptTest -> PromptVariant (1:N)
# PromptTest -> PromptTestResult (1:N)
# PromptOptimizationRule -> PromptLearningPattern (1:N, através de applied_rules) 