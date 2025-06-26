"""
Prompt Testing and Refinement Service
Sistema completo de testes A/B e refinamento iterativo de prompts
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import json
import statistics
import hashlib
from abc import ABC, abstractmethod

from ..models.base_task import TaskType
from ..services.provider_registry import provider_registry
from ..database.session import get_db

logger = logging.getLogger(__name__)


class TestType(Enum):
    """Tipos de teste de prompt"""
    AB_TEST = "ab_test"
    MULTIVARIATE = "multivariate"
    ITERATIVE = "iterative"
    PERFORMANCE = "performance"
    QUALITY = "quality"


class MetricType(Enum):
    """Tipos de métricas para avaliação"""
    GENERATION_TIME = "generation_time"
    IMAGE_QUALITY = "image_quality"
    PROMPT_ADHERENCE = "prompt_adherence"
    AESTHETIC_SCORE = "aesthetic_score"
    SAFETY_SCORE = "safety_score"
    USER_SATISFACTION = "user_satisfaction"
    COST_EFFICIENCY = "cost_efficiency"


@dataclass
class PromptVariant:
    """Variante de prompt para teste"""
    id: str
    prompt: str
    style_modifiers: List[str]
    technical_params: Dict[str, Any]
    weight: float = 1.0
    description: str = ""
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class TestResult:
    """Resultado de um teste de prompt"""
    variant_id: str
    prompt: str
    generation_time: float
    output_url: str
    metrics: Dict[str, float]
    metadata: Dict[str, Any]
    timestamp: datetime
    provider_id: str
    cost: float = 0.0
    user_feedback: Optional[Dict[str, Any]] = None


@dataclass
class TestConfiguration:
    """Configuração de um teste A/B"""
    test_id: str
    test_type: TestType
    base_prompt: str
    variants: List[PromptVariant]
    target_metrics: List[MetricType]
    sample_size: int
    confidence_level: float = 0.95
    max_duration_hours: int = 24
    auto_winner_threshold: float = 0.2  # 20% de melhoria para declarar vencedor
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class TestAnalysis:
    """Análise estatística de um teste"""
    test_id: str
    winner_variant_id: Optional[str]
    confidence_score: float
    improvement_percentage: float
    statistical_significance: bool
    metrics_analysis: Dict[str, Any]
    recommendations: List[str]
    optimal_prompt: str
    generated_at: datetime


class BaseMetricCalculator(ABC):
    """Classe base para calculadores de métricas"""
    
    @abstractmethod
    async def calculate(self, result: TestResult) -> float:
        """Calcula a métrica para um resultado"""
        pass
    
    @abstractmethod
    def get_metric_name(self) -> str:
        """Nome da métrica"""
        pass


class GenerationTimeCalculator(BaseMetricCalculator):
    """Calculador de tempo de geração"""
    
    async def calculate(self, result: TestResult) -> float:
        return result.generation_time
    
    def get_metric_name(self) -> str:
        return MetricType.GENERATION_TIME.value


class ImageQualityCalculator(BaseMetricCalculator):
    """Calculador de qualidade de imagem (simulado)"""
    
    async def calculate(self, result: TestResult) -> float:
        # Em um sistema real, usaria análise de imagem com CLIP ou outros modelos
        # Por agora, simulamos baseado em parâmetros
        base_score = 0.7
        
        # Fatores que aumentam qualidade
        if "high quality" in result.prompt.lower():
            base_score += 0.1
        if "detailed" in result.prompt.lower():
            base_score += 0.05
        if "professional" in result.prompt.lower():
            base_score += 0.1
        
        # Penalidades
        if result.generation_time < 5:  # Muito rápido pode ser baixa qualidade
            base_score -= 0.1
        
        return min(1.0, max(0.0, base_score))
    
    def get_metric_name(self) -> str:
        return MetricType.IMAGE_QUALITY.value


class AestheticScoreCalculator(BaseMetricCalculator):
    """Calculador de score estético"""
    
    async def calculate(self, result: TestResult) -> float:
        # Simulação baseada em palavras-chave estéticas
        aesthetic_keywords = [
            "beautiful", "elegant", "artistic", "stunning", "gorgeous",
            "masterpiece", "cinematic", "dramatic", "vibrant", "harmonious"
        ]
        
        score = 0.5
        prompt_lower = result.prompt.lower()
        
        for keyword in aesthetic_keywords:
            if keyword in prompt_lower:
                score += 0.05
        
        return min(1.0, score)
    
    def get_metric_name(self) -> str:
        return MetricType.AESTHETIC_SCORE.value


class CostEfficiencyCalculator(BaseMetricCalculator):
    """Calculador de eficiência de custo"""
    
    async def calculate(self, result: TestResult) -> float:
        if result.cost <= 0:
            return 1.0
        
        # Eficiência = qualidade / custo
        quality = result.metrics.get("image_quality", 0.7)
        efficiency = quality / result.cost
        
        # Normaliza para 0-1
        return min(1.0, efficiency / 10)  # Assume que 10 é eficiência máxima
    
    def get_metric_name(self) -> str:
        return MetricType.COST_EFFICIENCY.value


class PromptTestingService:
    """Serviço principal de teste e refinamento de prompts"""
    
    def __init__(self):
        self.active_tests: Dict[str, TestConfiguration] = {}
        self.test_results: Dict[str, List[TestResult]] = {}
        self.metric_calculators: Dict[MetricType, BaseMetricCalculator] = {
            MetricType.GENERATION_TIME: GenerationTimeCalculator(),
            MetricType.IMAGE_QUALITY: ImageQualityCalculator(),
            MetricType.AESTHETIC_SCORE: AestheticScoreCalculator(),
            MetricType.COST_EFFICIENCY: CostEfficiencyCalculator(),
        }
    
    async def create_ab_test(self, config: TestConfiguration) -> str:
        """Cria um novo teste A/B"""
        test_id = config.test_id or f"test_{int(datetime.utcnow().timestamp())}"
        config.test_id = test_id
        
        # Valida configuração
        await self._validate_test_config(config)
        
        # Registra teste
        self.active_tests[test_id] = config
        self.test_results[test_id] = []
        
        logger.info(f"Teste A/B criado: {test_id} com {len(config.variants)} variantes")
        return test_id
    
    async def run_test_iteration(self, test_id: str, user_id: str) -> Dict[str, Any]:
        """Executa uma iteração do teste"""
        if test_id not in self.active_tests:
            raise ValueError(f"Teste {test_id} não encontrado")
        
        config = self.active_tests[test_id]
        
        # Seleciona variante para teste
        variant = await self._select_test_variant(config)
        
        # Executa geração com a variante
        result = await self._execute_generation(variant, config, user_id)
        
        # Calcula métricas
        await self._calculate_metrics(result, config.target_metrics)
        
        # Armazena resultado
        self.test_results[test_id].append(result)
        
        # Verifica se deve declarar vencedor
        analysis = await self._check_for_winner(test_id)
        
        return {
            "test_id": test_id,
            "variant_tested": variant.id,
            "result": asdict(result),
            "total_samples": len(self.test_results[test_id]),
            "target_samples": config.sample_size,
            "analysis": asdict(analysis) if analysis else None
        }
    
    async def get_test_status(self, test_id: str) -> Dict[str, Any]:
        """Obtém status detalhado de um teste"""
        if test_id not in self.active_tests:
            raise ValueError(f"Teste {test_id} não encontrado")
        
        config = self.active_tests[test_id]
        results = self.test_results[test_id]
        
        # Estatísticas por variante
        variant_stats = {}
        for variant in config.variants:
            variant_results = [r for r in results if r.variant_id == variant.id]
            if variant_results:
                variant_stats[variant.id] = await self._calculate_variant_stats(variant_results)
        
        return {
            "test_id": test_id,
            "config": asdict(config),
            "total_samples": len(results),
            "samples_by_variant": {v.id: len([r for r in results if r.variant_id == v.id]) 
                                 for v in config.variants},
            "variant_stats": variant_stats,
            "is_complete": len(results) >= config.sample_size,
            "created_at": config.metadata.get("created_at", "unknown")
        }
    
    async def analyze_test_results(self, test_id: str) -> TestAnalysis:
        """Analisa resultados e determina vencedor"""
        if test_id not in self.active_tests:
            raise ValueError(f"Teste {test_id} não encontrado")
        
        config = self.active_tests[test_id]
        results = self.test_results[test_id]
        
        if len(results) < 10:  # Mínimo para análise
            raise ValueError("Dados insuficientes para análise")
        
        # Analisa cada métrica
        metrics_analysis = {}
        variant_scores = {}
        
        for metric_type in config.target_metrics:
            metric_analysis = await self._analyze_metric(results, metric_type, config.variants)
            metrics_analysis[metric_type.value] = metric_analysis
            
            # Acumula scores por variante
            for variant_id, score in metric_analysis["variant_scores"].items():
                if variant_id not in variant_scores:
                    variant_scores[variant_id] = []
                variant_scores[variant_id].append(score)
        
        # Calcula score final por variante (média das métricas)
        final_scores = {
            variant_id: statistics.mean(scores) 
            for variant_id, scores in variant_scores.items()
        }
        
        # Determina vencedor
        winner_id = max(final_scores.keys(), key=lambda k: final_scores[k])
        winner_score = final_scores[winner_id]
        
        # Calcula melhoria vs baseline (primeira variante)
        baseline_id = config.variants[0].id
        baseline_score = final_scores.get(baseline_id, 0)
        improvement = ((winner_score - baseline_score) / baseline_score * 100) if baseline_score > 0 else 0
        
        # Significância estatística (simplificada)
        significance = improvement >= config.auto_winner_threshold * 100
        confidence = min(0.99, 0.5 + (improvement / 100))
        
        # Gera recomendações
        recommendations = await self._generate_recommendations(config, metrics_analysis, winner_id)
        
        # Cria prompt otimizado
        winner_variant = next(v for v in config.variants if v.id == winner_id)
        optimal_prompt = await self._optimize_prompt(winner_variant, metrics_analysis)
        
        return TestAnalysis(
            test_id=test_id,
            winner_variant_id=winner_id,
            confidence_score=confidence,
            improvement_percentage=improvement,
            statistical_significance=significance,
            metrics_analysis=metrics_analysis,
            recommendations=recommendations,
            optimal_prompt=optimal_prompt,
            generated_at=datetime.utcnow()
        )
    
    async def create_iterative_refinement(self, base_prompt: str, target_metric: MetricType, 
                                        iterations: int = 5) -> str:
        """Cria teste de refinamento iterativo"""
        
        # Gera variantes incrementais
        variants = await self._generate_iterative_variants(base_prompt, iterations)
        
        config = TestConfiguration(
            test_id=f"iterative_{int(datetime.utcnow().timestamp())}",
            test_type=TestType.ITERATIVE,
            base_prompt=base_prompt,
            variants=variants,
            target_metrics=[target_metric],
            sample_size=iterations * 3,  # 3 amostras por iteração
            confidence_level=0.90
        )
        
        return await self.create_ab_test(config)
    
    async def create_multivariate_test(self, base_prompt: str, 
                                     style_options: List[str],
                                     quality_options: List[str],
                                     size_options: List[str]) -> str:
        """Cria teste multivariável combinando diferentes parâmetros"""
        
        variants = []
        variant_id = 0
        
        for style in style_options:
            for quality in quality_options:
                for size in size_options:
                    variant_id += 1
                    
                    # Constrói prompt com modificadores
                    enhanced_prompt = f"{base_prompt}, {style} style"
                    
                    variant = PromptVariant(
                        id=f"var_{variant_id}",
                        prompt=enhanced_prompt,
                        style_modifiers=[style],
                        technical_params={
                            "quality": quality,
                            "size": size
                        },
                        description=f"Style: {style}, Quality: {quality}, Size: {size}",
                        tags=[style, quality, size]
                    )
                    variants.append(variant)
        
        config = TestConfiguration(
            test_id=f"multivariate_{int(datetime.utcnow().timestamp())}",
            test_type=TestType.MULTIVARIATE,
            base_prompt=base_prompt,
            variants=variants,
            target_metrics=[MetricType.IMAGE_QUALITY, MetricType.AESTHETIC_SCORE, MetricType.GENERATION_TIME],
            sample_size=len(variants) * 2  # 2 amostras por combinação
        )
        
        return await self.create_ab_test(config)
    
    async def _validate_test_config(self, config: TestConfiguration):
        """Valida configuração do teste"""
        if len(config.variants) < 2:
            raise ValueError("Teste deve ter pelo menos 2 variantes")
        
        if config.sample_size < 10:
            raise ValueError("Tamanho da amostra deve ser pelo menos 10")
        
        if not config.target_metrics:
            raise ValueError("Deve especificar pelo menos uma métrica alvo")
        
        # Verifica se todas as métricas são suportadas
        for metric in config.target_metrics:
            if metric not in self.metric_calculators:
                raise ValueError(f"Métrica {metric} não é suportada")
    
    async def _select_test_variant(self, config: TestConfiguration) -> PromptVariant:
        """Seleciona variante para testar baseado em pesos e balanceamento"""
        results = self.test_results[config.test_id]
        
        # Conta amostras por variante
        variant_counts = {v.id: 0 for v in config.variants}
        for result in results:
            variant_counts[result.variant_id] += 1
        
        # Seleciona variante com menos amostras (balanceamento)
        min_count = min(variant_counts.values())
        candidates = [v for v in config.variants if variant_counts[v.id] == min_count]
        
        # Se empate, considera peso
        if len(candidates) > 1:
            return max(candidates, key=lambda v: v.weight)
        
        return candidates[0]
    
    async def _execute_generation(self, variant: PromptVariant, 
                                config: TestConfiguration, user_id: str) -> TestResult:
        """Executa geração com uma variante"""
        start_time = datetime.utcnow()
        
        # Obtém provider para imagem
        providers = provider_registry.get_providers_for_task_type(TaskType.IMAGE_GENERATION)
        if not providers:
            raise RuntimeError("Nenhum provider de imagem disponível")
        
        provider = providers[0]  # Usa primeiro provider disponível
        
        # Prepara dados de entrada
        input_data = {
            "prompt": variant.prompt,
            **variant.technical_params
        }
        
        try:
            # Simula geração (em produção, chamaria provider real)
            await asyncio.sleep(0.5)  # Simula tempo de processamento
            
            generation_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Simula resultado
            result = TestResult(
                variant_id=variant.id,
                prompt=variant.prompt,
                generation_time=generation_time,
                output_url=f"https://example.com/generated_{variant.id}_{int(start_time.timestamp())}.jpg",
                metrics={},
                metadata={
                    "provider": provider.name,
                    "user_id": user_id,
                    "technical_params": variant.technical_params
                },
                timestamp=datetime.utcnow(),
                provider_id=provider.name,
                cost=0.1  # Custo simulado
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Erro na geração para variante {variant.id}: {e}")
            raise
    
    async def _calculate_metrics(self, result: TestResult, target_metrics: List[MetricType]):
        """Calcula métricas para um resultado"""
        for metric_type in target_metrics:
            if metric_type in self.metric_calculators:
                calculator = self.metric_calculators[metric_type]
                value = await calculator.calculate(result)
                result.metrics[metric_type.value] = value
    
    async def _check_for_winner(self, test_id: str) -> Optional[TestAnalysis]:
        """Verifica se já pode declarar um vencedor"""
        config = self.active_tests[test_id]
        results = self.test_results[test_id]
        
        # Verifica se atingiu tamanho mínimo
        if len(results) < config.sample_size:
            return None
        
        # Executa análise completa
        try:
            analysis = await self.analyze_test_results(test_id)
            
            # Verifica se melhoria é significativa
            if analysis.improvement_percentage >= config.auto_winner_threshold * 100:
                logger.info(f"Vencedor declarado para teste {test_id}: {analysis.winner_variant_id}")
                return analysis
        
        except Exception as e:
            logger.warning(f"Erro na análise automática do teste {test_id}: {e}")
        
        return None
    
    async def _calculate_variant_stats(self, variant_results: List[TestResult]) -> Dict[str, Any]:
        """Calcula estatísticas para uma variante"""
        if not variant_results:
            return {}
        
        # Coleta todas as métricas
        all_metrics = set()
        for result in variant_results:
            all_metrics.update(result.metrics.keys())
        
        stats = {}
        for metric in all_metrics:
            values = [r.metrics.get(metric, 0) for r in variant_results if metric in r.metrics]
            if values:
                stats[metric] = {
                    "mean": statistics.mean(values),
                    "median": statistics.median(values),
                    "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
                    "min": min(values),
                    "max": max(values),
                    "count": len(values)
                }
        
        # Estatísticas gerais
        generation_times = [r.generation_time for r in variant_results]
        costs = [r.cost for r in variant_results]
        
        stats["general"] = {
            "samples": len(variant_results),
            "avg_generation_time": statistics.mean(generation_times),
            "total_cost": sum(costs),
            "avg_cost": statistics.mean(costs),
            "success_rate": 1.0  # Assumindo que todos os resultados são sucessos
        }
        
        return stats
    
    async def _analyze_metric(self, results: List[TestResult], metric_type: MetricType, 
                            variants: List[PromptVariant]) -> Dict[str, Any]:
        """Analisa uma métrica específica"""
        metric_name = metric_type.value
        
        # Agrupa resultados por variante
        variant_values = {}
        for variant in variants:
            values = [
                r.metrics.get(metric_name, 0) 
                for r in results 
                if r.variant_id == variant.id and metric_name in r.metrics
            ]
            if values:
                variant_values[variant.id] = values
        
        # Calcula scores médios
        variant_scores = {
            variant_id: statistics.mean(values) 
            for variant_id, values in variant_values.items()
        }
        
        # Encontra melhor e pior
        if variant_scores:
            best_variant = max(variant_scores.keys(), key=lambda k: variant_scores[k])
            worst_variant = min(variant_scores.keys(), key=lambda k: variant_scores[k])
            
            improvement = ((variant_scores[best_variant] - variant_scores[worst_variant]) / 
                         variant_scores[worst_variant] * 100) if variant_scores[worst_variant] > 0 else 0
        else:
            best_variant = worst_variant = None
            improvement = 0
        
        return {
            "metric": metric_name,
            "variant_scores": variant_scores,
            "best_variant": best_variant,
            "worst_variant": worst_variant,
            "improvement_percentage": improvement,
            "sample_sizes": {variant_id: len(values) for variant_id, values in variant_values.items()}
        }
    
    async def _generate_recommendations(self, config: TestConfiguration, 
                                      metrics_analysis: Dict[str, Any], 
                                      winner_id: str) -> List[str]:
        """Gera recomendações baseadas na análise"""
        recommendations = []
        
        winner_variant = next(v for v in config.variants if v.id == winner_id)
        
        # Recomendações baseadas na variante vencedora
        recommendations.append(f"Use prompt base: '{winner_variant.prompt}'")
        
        if winner_variant.style_modifiers:
            recommendations.append(f"Aplique modificadores de estilo: {', '.join(winner_variant.style_modifiers)}")
        
        if winner_variant.technical_params:
            params_str = ', '.join([f"{k}={v}" for k, v in winner_variant.technical_params.items()])
            recommendations.append(f"Configure parâmetros técnicos: {params_str}")
        
        # Recomendações baseadas nas métricas
        for metric_name, analysis in metrics_analysis.items():
            if analysis["improvement_percentage"] > 20:
                recommendations.append(
                    f"Métrica {metric_name} mostrou melhoria significativa de "
                    f"{analysis['improvement_percentage']:.1f}% - priorize esta otimização"
                )
        
        # Recomendações para próximos testes
        if config.test_type == TestType.AB_TEST:
            recommendations.append("Considere teste multivariável para explorar combinações de parâmetros")
        
        recommendations.append("Execute testes de validação com usuários reais para confirmar resultados")
        
        return recommendations
    
    async def _optimize_prompt(self, winner_variant: PromptVariant, 
                             metrics_analysis: Dict[str, Any]) -> str:
        """Cria versão otimizada do prompt vencedor"""
        base_prompt = winner_variant.prompt
        
        # Adiciona modificadores baseados nas métricas de melhor performance
        optimizations = []
        
        # Se qualidade de imagem foi alta, adiciona modificadores de qualidade
        quality_analysis = metrics_analysis.get("image_quality", {})
        if quality_analysis.get("improvement_percentage", 0) > 15:
            optimizations.append("high quality, detailed")
        
        # Se score estético foi alto, adiciona modificadores estéticos
        aesthetic_analysis = metrics_analysis.get("aesthetic_score", {})
        if aesthetic_analysis.get("improvement_percentage", 0) > 15:
            optimizations.append("beautiful, artistic composition")
        
        # Combina otimizações
        if optimizations:
            optimized_prompt = f"{base_prompt}, {', '.join(optimizations)}"
        else:
            optimized_prompt = base_prompt
        
        return optimized_prompt
    
    async def _generate_iterative_variants(self, base_prompt: str, iterations: int) -> List[PromptVariant]:
        """Gera variantes para refinamento iterativo"""
        variants = []
        
        # Variante base
        variants.append(PromptVariant(
            id="base",
            prompt=base_prompt,
            style_modifiers=[],
            technical_params={},
            description="Prompt original"
        ))
        
        # Variantes com melhorias incrementais
        improvements = [
            ("detailed", "detailed, intricate"),
            ("quality", "high quality, professional"),
            ("artistic", "artistic, masterpiece"),
            ("lighting", "perfect lighting, dramatic shadows"),
            ("composition", "excellent composition, rule of thirds")
        ]
        
        for i, (suffix, modifier) in enumerate(improvements[:iterations-1]):
            variants.append(PromptVariant(
                id=f"iter_{i+1}_{suffix}",
                prompt=f"{base_prompt}, {modifier}",
                style_modifiers=[modifier],
                technical_params={},
                description=f"Iteração {i+1}: {suffix}"
            ))
        
        return variants
    
    def get_test_history(self) -> Dict[str, Any]:
        """Retorna histórico de todos os testes"""
        return {
            "active_tests": len(self.active_tests),
            "total_results": sum(len(results) for results in self.test_results.values()),
            "tests": {
                test_id: {
                    "config": asdict(config),
                    "results_count": len(self.test_results.get(test_id, []))
                }
                for test_id, config in self.active_tests.items()
            }
        }


# Instância global do serviço
prompt_testing_service = PromptTestingService() 