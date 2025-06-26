"""
Prompt Optimizer Service
Sistema de otimização automática de prompts baseado em machine learning e análise de resultados
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import re
from enum import Enum

logger = logging.getLogger(__name__)


class OptimizationStrategy(Enum):
    """Estratégias de otimização de prompt"""
    KEYWORD_ENHANCEMENT = "keyword_enhancement"
    STYLE_REFINEMENT = "style_refinement"
    QUALITY_BOOST = "quality_boost"
    COMPOSITION_IMPROVEMENT = "composition_improvement"
    NEGATIVE_PROMPT = "negative_prompt"
    PARAMETER_TUNING = "parameter_tuning"


@dataclass
class OptimizationRule:
    """Regra de otimização de prompt"""
    name: str
    pattern: str  # Regex pattern
    replacement: str
    strategy: OptimizationStrategy
    confidence: float  # 0.0 - 1.0
    usage_count: int = 0
    success_rate: float = 0.0
    description: str = ""


@dataclass
class PromptAnalysis:
    """Análise estrutural de um prompt"""
    original_prompt: str
    subject: str
    style_keywords: List[str]
    quality_keywords: List[str]
    composition_keywords: List[str]
    technical_keywords: List[str]
    word_count: int
    complexity_score: float
    improvement_suggestions: List[str]


@dataclass
class OptimizationResult:
    """Resultado de uma otimização"""
    original_prompt: str
    optimized_prompt: str
    applied_rules: List[str]
    confidence_score: float
    expected_improvement: float
    optimization_strategy: OptimizationStrategy
    metadata: Dict[str, Any]


class PromptOptimizerService:
    """Serviço principal de otimização de prompts"""
    
    def __init__(self):
        self.optimization_rules = self._initialize_rules()
        self.learned_patterns = {}
        self.performance_history = {}
    
    def _initialize_rules(self) -> List[OptimizationRule]:
        """Inicializa regras de otimização baseadas em best practices"""
        rules = [
            # Regras de qualidade
            OptimizationRule(
                name="add_quality_keywords",
                pattern=r"^(?!.*(?:high quality|detailed|professional))(.*)",
                replacement=r"\1, high quality, detailed",
                strategy=OptimizationStrategy.QUALITY_BOOST,
                confidence=0.8,
                description="Adiciona palavras-chave de qualidade quando ausentes"
            ),
            
            OptimizationRule(
                name="enhance_resolution",
                pattern=r"(?<!8k)(?<!4k)(?<!hd)(?<!high resolution)(.*?)$",
                replacement=r"\1, 8k, high resolution",
                strategy=OptimizationStrategy.QUALITY_BOOST,
                confidence=0.7,
                description="Adiciona modificadores de resolução"
            ),
            
            # Regras de estilo
            OptimizationRule(
                name="add_artistic_style",
                pattern=r"^(?!.*(?:artistic|art style|masterpiece))(.*)",
                replacement=r"\1, artistic masterpiece",
                strategy=OptimizationStrategy.STYLE_REFINEMENT,
                confidence=0.75,
                description="Adiciona elementos artísticos"
            ),
            
            OptimizationRule(
                name="enhance_lighting",
                pattern=r"^(?!.*(?:lighting|illuminated|glow))(.*)",
                replacement=r"\1, perfect lighting, dramatic shadows",
                strategy=OptimizationStrategy.COMPOSITION_IMPROVEMENT,
                confidence=0.6,
                description="Melhora descrição de iluminação"
            ),
            
            # Regras de composição
            OptimizationRule(
                name="add_composition",
                pattern=r"^(?!.*(?:composition|framing|centered))(.*)",
                replacement=r"\1, excellent composition, rule of thirds",
                strategy=OptimizationStrategy.COMPOSITION_IMPROVEMENT,
                confidence=0.65,
                description="Adiciona elementos de composição"
            ),
            
            OptimizationRule(
                name="enhance_details",
                pattern=r"(?<!detailed)(?<!intricate)(?<!fine details)(.*?)$",
                replacement=r"\1, intricate details, fine craftsmanship",
                strategy=OptimizationStrategy.KEYWORD_ENHANCEMENT,
                confidence=0.7,
                description="Adiciona detalhamento"
            ),
            
            # Regras de limpeza
            OptimizationRule(
                name="remove_redundancy",
                pattern=r"\b(\w+)(?:\s+\1\b)+",
                replacement=r"\1",
                strategy=OptimizationStrategy.KEYWORD_ENHANCEMENT,
                confidence=0.9,
                description="Remove palavras duplicadas"
            ),
            
            OptimizationRule(
                name="fix_spacing",
                pattern=r"\s+",
                replacement=r" ",
                strategy=OptimizationStrategy.KEYWORD_ENHANCEMENT,
                confidence=1.0,
                description="Normaliza espaçamentos"
            ),
            
            # Regras específicas para tipos de imagem
            OptimizationRule(
                name="enhance_portrait",
                pattern=r"(?i)(portrait|person|face|human)(?!.*(?:professional|studio))(.*)",
                replacement=r"\1\2, professional portrait, studio lighting",
                strategy=OptimizationStrategy.STYLE_REFINEMENT,
                confidence=0.8,
                description="Melhora prompts de retrato"
            ),
            
            OptimizationRule(
                name="enhance_landscape",
                pattern=r"(?i)(landscape|nature|mountain|forest)(?!.*(?:panoramic|vista))(.*)",
                replacement=r"\1\2, panoramic vista, natural beauty",
                strategy=OptimizationStrategy.STYLE_REFINEMENT,
                confidence=0.7,
                description="Melhora prompts de paisagem"
            ),
            
            # Regras de prompt negativo
            OptimizationRule(
                name="add_negative_quality",
                pattern=r"^(.*?)$",
                replacement=r"\1 --no blurry, low quality, distorted, ugly",
                strategy=OptimizationStrategy.NEGATIVE_PROMPT,
                confidence=0.6,
                description="Adiciona prompt negativo para qualidade"
            )
        ]
        
        return rules
    
    async def analyze_prompt(self, prompt: str) -> PromptAnalysis:
        """Analisa estrutura e conteúdo de um prompt"""
        
        # Extrai componentes do prompt
        subject = self._extract_subject(prompt)
        style_keywords = self._extract_style_keywords(prompt)
        quality_keywords = self._extract_quality_keywords(prompt)
        composition_keywords = self._extract_composition_keywords(prompt)
        technical_keywords = self._extract_technical_keywords(prompt)
        
        # Métricas básicas
        word_count = len(prompt.split())
        complexity_score = self._calculate_complexity(prompt)
        
        # Gera sugestões
        improvement_suggestions = self._generate_suggestions(prompt, {
            "style": style_keywords,
            "quality": quality_keywords,
            "composition": composition_keywords,
            "technical": technical_keywords
        })
        
        return PromptAnalysis(
            original_prompt=prompt,
            subject=subject,
            style_keywords=style_keywords,
            quality_keywords=quality_keywords,
            composition_keywords=composition_keywords,
            technical_keywords=technical_keywords,
            word_count=word_count,
            complexity_score=complexity_score,
            improvement_suggestions=improvement_suggestions
        )
    
    async def optimize_prompt(self, prompt: str, 
                            strategy: Optional[OptimizationStrategy] = None,
                            aggressive: bool = False) -> OptimizationResult:
        """Otimiza um prompt aplicando regras selecionadas"""
        
        original_prompt = prompt.strip()
        optimized_prompt = original_prompt
        applied_rules = []
        total_confidence = 0.0
        
        # Seleciona regras baseadas na estratégia
        if strategy:
            rules_to_apply = [r for r in self.optimization_rules if r.strategy == strategy]
        else:
            rules_to_apply = self.optimization_rules
        
        # Aplica regras em ordem de confiança
        rules_to_apply.sort(key=lambda r: r.confidence, reverse=True)
        
        for rule in rules_to_apply:
            # Verifica se deve aplicar a regra
            if not aggressive and rule.confidence < 0.7:
                continue
            
            # Aplica transformação
            try:
                new_prompt = re.sub(rule.pattern, rule.replacement, optimized_prompt)
                
                if new_prompt != optimized_prompt:
                    optimized_prompt = new_prompt
                    applied_rules.append(rule.name)
                    total_confidence += rule.confidence
                    
                    # Atualiza estatísticas da regra
                    rule.usage_count += 1
                    
            except re.error as e:
                logger.warning(f"Erro na regra {rule.name}: {e}")
                continue
        
        # Calcula scores finais
        confidence_score = total_confidence / len(applied_rules) if applied_rules else 0.0
        expected_improvement = self._estimate_improvement(original_prompt, optimized_prompt)
        
        # Determina estratégia predominante
        strategies_used = [next(r.strategy for r in self.optimization_rules if r.name == name) 
                          for name in applied_rules]
        main_strategy = max(set(strategies_used), key=strategies_used.count) if strategies_used else OptimizationStrategy.KEYWORD_ENHANCEMENT
        
        return OptimizationResult(
            original_prompt=original_prompt,
            optimized_prompt=optimized_prompt,
            applied_rules=applied_rules,
            confidence_score=confidence_score,
            expected_improvement=expected_improvement,
            optimization_strategy=main_strategy,
            metadata={
                "word_count_change": len(optimized_prompt.split()) - len(original_prompt.split()),
                "rules_applied": len(applied_rules),
                "optimization_timestamp": datetime.utcnow().isoformat()
            }
        )
    
    async def optimize_batch(self, prompts: List[str], 
                           strategy: Optional[OptimizationStrategy] = None) -> List[OptimizationResult]:
        """Otimiza múltiplos prompts em lote"""
        results = []
        
        for prompt in prompts:
            try:
                result = await self.optimize_prompt(prompt, strategy)
                results.append(result)
            except Exception as e:
                logger.error(f"Erro ao otimizar prompt '{prompt[:50]}...': {e}")
                # Adiciona resultado de erro
                results.append(OptimizationResult(
                    original_prompt=prompt,
                    optimized_prompt=prompt,  # Mantém original
                    applied_rules=[],
                    confidence_score=0.0,
                    expected_improvement=0.0,
                    optimization_strategy=OptimizationStrategy.KEYWORD_ENHANCEMENT,
                    metadata={"error": str(e)}
                ))
        
        return results
    
    async def learn_from_results(self, prompt: str, optimized_prompt: str, 
                                performance_metrics: Dict[str, float]):
        """Aprende com resultados de testes para melhorar otimizações futuras"""
        
        # Identifica quais regras foram aplicadas
        applied_rules = self._identify_applied_rules(prompt, optimized_prompt)
        
        # Calcula score de performance geral
        performance_score = sum(performance_metrics.values()) / len(performance_metrics)
        
        # Atualiza success rate das regras
        for rule_name in applied_rules:
            rule = next((r for r in self.optimization_rules if r.name == rule_name), None)
            if rule:
                # Atualiza success rate usando média móvel
                if rule.usage_count > 0:
                    rule.success_rate = (rule.success_rate * (rule.usage_count - 1) + performance_score) / rule.usage_count
                else:
                    rule.success_rate = performance_score
        
        # Armazena padrão para aprendizado futuro
        pattern_key = self._generate_pattern_key(prompt)
        if pattern_key not in self.learned_patterns:
            self.learned_patterns[pattern_key] = []
        
        self.learned_patterns[pattern_key].append({
            "optimized_prompt": optimized_prompt,
            "performance": performance_score,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        logger.info(f"Aprendizado registrado para padrão '{pattern_key}': score={performance_score:.3f}")
    
    async def get_optimization_suggestions(self, prompt: str) -> List[Dict[str, Any]]:
        """Retorna sugestões específicas de otimização para um prompt"""
        analysis = await self.analyze_prompt(prompt)
        suggestions = []
        
        # Analisa deficiências e sugere melhorias
        if not analysis.quality_keywords:
            suggestions.append({
                "type": "quality_enhancement",
                "description": "Adicionar palavras-chave de qualidade (high quality, detailed, professional)",
                "example": f"{prompt}, high quality, detailed",
                "expected_improvement": 15,
                "strategy": OptimizationStrategy.QUALITY_BOOST.value
            })
        
        if analysis.word_count < 5:
            suggestions.append({
                "type": "detail_expansion",
                "description": "Expandir descrição com mais detalhes específicos",
                "example": f"{prompt}, intricate details, realistic textures",
                "expected_improvement": 20,
                "strategy": OptimizationStrategy.KEYWORD_ENHANCEMENT.value
            })
        
        if not analysis.style_keywords:
            suggestions.append({
                "type": "style_definition",
                "description": "Definir estilo artístico específico",
                "example": f"{prompt}, digital art, concept art style",
                "expected_improvement": 10,
                "strategy": OptimizationStrategy.STYLE_REFINEMENT.value
            })
        
        if not analysis.composition_keywords:
            suggestions.append({
                "type": "composition_improvement",
                "description": "Adicionar elementos de composição",
                "example": f"{prompt}, excellent composition, rule of thirds",
                "expected_improvement": 12,
                "strategy": OptimizationStrategy.COMPOSITION_IMPROVEMENT.value
            })
        
        # Sugestões baseadas em padrões aprendidos
        pattern_key = self._generate_pattern_key(prompt)
        if pattern_key in self.learned_patterns:
            best_pattern = max(self.learned_patterns[pattern_key], key=lambda x: x["performance"])
            suggestions.append({
                "type": "learned_pattern",
                "description": "Aplicar padrão de alta performance aprendido",
                "example": best_pattern["optimized_prompt"],
                "expected_improvement": int(best_pattern["performance"] * 25),
                "strategy": "learned_optimization"
            })
        
        return suggestions
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas das otimizações"""
        total_rules = len(self.optimization_rules)
        active_rules = len([r for r in self.optimization_rules if r.usage_count > 0])
        
        # Estatísticas por estratégia
        strategy_stats = {}
        for strategy in OptimizationStrategy:
            rules = [r for r in self.optimization_rules if r.strategy == strategy]
            strategy_stats[strategy.value] = {
                "total_rules": len(rules),
                "active_rules": len([r for r in rules if r.usage_count > 0]),
                "avg_success_rate": sum(r.success_rate for r in rules) / len(rules) if rules else 0,
                "total_usage": sum(r.usage_count for r in rules)
            }
        
        # Top regras por performance
        top_rules = sorted(
            [r for r in self.optimization_rules if r.usage_count > 0],
            key=lambda r: r.success_rate,
            reverse=True
        )[:5]
        
        return {
            "total_rules": total_rules,
            "active_rules": active_rules,
            "learned_patterns": len(self.learned_patterns),
            "strategy_stats": strategy_stats,
            "top_performing_rules": [
                {
                    "name": r.name,
                    "success_rate": r.success_rate,
                    "usage_count": r.usage_count,
                    "description": r.description
                }
                for r in top_rules
            ]
        }
    
    def _extract_subject(self, prompt: str) -> str:
        """Extrai o sujeito principal do prompt"""
        # Implementação simplificada - em produção usaria NLP mais sofisticado
        words = prompt.lower().split()
        
        # Procura por substantivos comuns como sujeitos
        subjects = ["person", "man", "woman", "cat", "dog", "car", "house", "tree", "robot", "landscape"]
        for word in words:
            if word in subjects:
                return word
        
        # Se não encontrar, usa primeira palavra
        return words[0] if words else "unknown"
    
    def _extract_style_keywords(self, prompt: str) -> List[str]:
        """Extrai palavras-chave de estilo"""
        style_keywords = [
            "realistic", "artistic", "anime", "cartoon", "photorealistic", "digital art",
            "oil painting", "watercolor", "sketch", "concept art", "3d render",
            "cinematic", "dramatic", "vintage", "modern", "abstract", "surreal"
        ]
        
        found = []
        prompt_lower = prompt.lower()
        for keyword in style_keywords:
            if keyword in prompt_lower:
                found.append(keyword)
        
        return found
    
    def _extract_quality_keywords(self, prompt: str) -> List[str]:
        """Extrai palavras-chave de qualidade"""
        quality_keywords = [
            "high quality", "detailed", "professional", "masterpiece", "8k", "4k",
            "high resolution", "sharp", "clear", "crisp", "fine details"
        ]
        
        found = []
        prompt_lower = prompt.lower()
        for keyword in quality_keywords:
            if keyword in prompt_lower:
                found.append(keyword)
        
        return found
    
    def _extract_composition_keywords(self, prompt: str) -> List[str]:
        """Extrai palavras-chave de composição"""
        composition_keywords = [
            "composition", "framing", "centered", "rule of thirds", "symmetry",
            "balance", "perspective", "depth of field", "bokeh", "close-up", "wide shot"
        ]
        
        found = []
        prompt_lower = prompt.lower()
        for keyword in composition_keywords:
            if keyword in prompt_lower:
                found.append(keyword)
        
        return found
    
    def _extract_technical_keywords(self, prompt: str) -> List[str]:
        """Extrai palavras-chave técnicas"""
        technical_keywords = [
            "lighting", "shadows", "highlights", "exposure", "contrast", "saturation",
            "color grading", "lens", "camera", "ISO", "aperture", "shutter speed"
        ]
        
        found = []
        prompt_lower = prompt.lower()
        for keyword in technical_keywords:
            if keyword in prompt_lower:
                found.append(keyword)
        
        return found
    
    def _calculate_complexity(self, prompt: str) -> float:
        """Calcula score de complexidade do prompt (0.0 - 1.0)"""
        base_score = 0.0
        
        # Fatores que aumentam complexidade
        word_count = len(prompt.split())
        base_score += min(word_count / 20, 0.3)  # Max 0.3 por palavra count
        
        # Presença de modificadores
        modifiers = ["detailed", "high quality", "artistic", "professional", "cinematic"]
        modifier_count = sum(1 for mod in modifiers if mod in prompt.lower())
        base_score += modifier_count * 0.1
        
        # Complexidade de descrição
        if "," in prompt:
            base_score += 0.2  # Prompt estruturado
        
        # Presença de parâmetros técnicos
        tech_terms = ["8k", "4k", "lighting", "composition", "style"]
        tech_count = sum(1 for term in tech_terms if term in prompt.lower())
        base_score += tech_count * 0.05
        
        return min(base_score, 1.0)
    
    def _generate_suggestions(self, prompt: str, keywords: Dict[str, List[str]]) -> List[str]:
        """Gera sugestões de melhoria"""
        suggestions = []
        
        if not keywords["quality"]:
            suggestions.append("Adicionar palavras-chave de qualidade")
        
        if not keywords["style"]:
            suggestions.append("Definir estilo artístico específico")
        
        if not keywords["composition"]:
            suggestions.append("Melhorar descrição de composição")
        
        if len(prompt.split()) < 5:
            suggestions.append("Expandir descrição com mais detalhes")
        
        if not keywords["technical"]:
            suggestions.append("Adicionar elementos técnicos (iluminação, perspectiva)")
        
        return suggestions
    
    def _estimate_improvement(self, original: str, optimized: str) -> float:
        """Estima porcentagem de melhoria esperada"""
        original_analysis = len(original.split())
        optimized_analysis = len(optimized.split())
        
        # Baseado na diferença de complexidade
        if optimized_analysis > original_analysis:
            return min((optimized_analysis - original_analysis) / original_analysis * 20, 30)
        
        return 5.0  # Melhoria mínima por limpeza/formatação
    
    def _identify_applied_rules(self, original: str, optimized: str) -> List[str]:
        """Identifica quais regras foram aplicadas na otimização"""
        applied = []
        
        for rule in self.optimization_rules:
            try:
                test_result = re.sub(rule.pattern, rule.replacement, original)
                if test_result != original and test_result in optimized:
                    applied.append(rule.name)
            except re.error:
                continue
        
        return applied
    
    def _generate_pattern_key(self, prompt: str) -> str:
        """Gera chave para padrão de prompt"""
        # Usa hash das palavras-chave principais
        words = prompt.lower().split()
        key_words = [w for w in words if len(w) > 3][:5]  # Top 5 palavras principais
        return "_".join(sorted(key_words))


# Instância global do serviço
prompt_optimizer_service = PromptOptimizerService() 