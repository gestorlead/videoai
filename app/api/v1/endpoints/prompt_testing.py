"""
Prompt Testing API Endpoints
Endpoints para teste A/B e refinamento de prompts
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime

from ....database.session import get_db
from ....services.prompt_testing import (
    prompt_testing_service,
    TestConfiguration,
    PromptVariant,
    TestType,
    MetricType,
    TestAnalysis
)
from ....core.auth import get_current_user
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


# Schemas para requests
class PromptVariantRequest(BaseModel):
    """Schema para criação de variante de prompt"""
    id: str
    prompt: str
    style_modifiers: List[str] = []
    technical_params: Dict[str, Any] = {}
    weight: float = 1.0
    description: str = ""
    tags: List[str] = []


class TestConfigurationRequest(BaseModel):
    """Schema para configuração de teste"""
    test_id: Optional[str] = None
    test_type: TestType
    base_prompt: str
    variants: List[PromptVariantRequest]
    target_metrics: List[MetricType]
    sample_size: int = 50
    confidence_level: float = 0.95
    max_duration_hours: int = 24
    auto_winner_threshold: float = 0.2
    metadata: Dict[str, Any] = {}


class IterativeRefinementRequest(BaseModel):
    """Schema para refinamento iterativo"""
    base_prompt: str
    target_metric: MetricType
    iterations: int = 5


class MultivariateTestRequest(BaseModel):
    """Schema para teste multivariável"""
    base_prompt: str
    style_options: List[str]
    quality_options: List[str]
    size_options: List[str]


class UserFeedbackRequest(BaseModel):
    """Schema para feedback do usuário"""
    test_id: str
    variant_id: str
    rating: float  # 1.0 - 5.0
    comments: str = ""
    preferred_aspects: List[str] = []
    suggested_improvements: List[str] = []


@router.post("/tests/ab-test", response_model=Dict[str, Any])
async def create_ab_test(
    request: TestConfigurationRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Cria um novo teste A/B de prompts"""
    try:
        # Converte request para objetos internos
        variants = [
            PromptVariant(
                id=v.id,
                prompt=v.prompt,
                style_modifiers=v.style_modifiers,
                technical_params=v.technical_params,
                weight=v.weight,
                description=v.description,
                tags=v.tags
            )
            for v in request.variants
        ]
        
        config = TestConfiguration(
            test_id=request.test_id,
            test_type=request.test_type,
            base_prompt=request.base_prompt,
            variants=variants,
            target_metrics=request.target_metrics,
            sample_size=request.sample_size,
            confidence_level=request.confidence_level,
            max_duration_hours=request.max_duration_hours,
            auto_winner_threshold=request.auto_winner_threshold,
            metadata={
                **request.metadata,
                "created_by": current_user["id"],
                "created_at": datetime.utcnow().isoformat()
            }
        )
        
        test_id = await prompt_testing_service.create_ab_test(config)
        
        return {
            "test_id": test_id,
            "status": "created",
            "variants_count": len(variants),
            "target_sample_size": request.sample_size,
            "estimated_duration_hours": request.max_duration_hours
        }
        
    except Exception as e:
        logger.error(f"Erro ao criar teste A/B: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tests/iterative", response_model=Dict[str, Any])
async def create_iterative_refinement(
    request: IterativeRefinementRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Cria teste de refinamento iterativo"""
    try:
        test_id = await prompt_testing_service.create_iterative_refinement(
            base_prompt=request.base_prompt,
            target_metric=request.target_metric,
            iterations=request.iterations
        )
        
        return {
            "test_id": test_id,
            "status": "created",
            "type": "iterative_refinement",
            "iterations": request.iterations,
            "target_metric": request.target_metric.value
        }
        
    except Exception as e:
        logger.error(f"Erro ao criar refinamento iterativo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tests/multivariate", response_model=Dict[str, Any])
async def create_multivariate_test(
    request: MultivariateTestRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Cria teste multivariável"""
    try:
        test_id = await prompt_testing_service.create_multivariate_test(
            base_prompt=request.base_prompt,
            style_options=request.style_options,
            quality_options=request.quality_options,
            size_options=request.size_options
        )
        
        total_combinations = len(request.style_options) * len(request.quality_options) * len(request.size_options)
        
        return {
            "test_id": test_id,
            "status": "created",
            "type": "multivariate",
            "total_combinations": total_combinations,
            "style_options": request.style_options,
            "quality_options": request.quality_options,
            "size_options": request.size_options
        }
        
    except Exception as e:
        logger.error(f"Erro ao criar teste multivariável: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tests/{test_id}/run-iteration")
async def run_test_iteration(
    test_id: str,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Executa uma iteração de teste"""
    try:
        result = await prompt_testing_service.run_test_iteration(
            test_id=test_id,
            user_id=current_user["id"]
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao executar iteração do teste {test_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tests/{test_id}/status")
async def get_test_status(
    test_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Obtém status detalhado de um teste"""
    try:
        status = await prompt_testing_service.get_test_status(test_id)
        return status
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao obter status do teste {test_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tests/{test_id}/analysis")
async def analyze_test_results(
    test_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Analisa resultados de um teste e determina vencedor"""
    try:
        analysis = await prompt_testing_service.analyze_test_results(test_id)
        
        # Converte para dicionário para resposta JSON
        return {
            "test_id": analysis.test_id,
            "winner_variant_id": analysis.winner_variant_id,
            "confidence_score": analysis.confidence_score,
            "improvement_percentage": analysis.improvement_percentage,
            "statistical_significance": analysis.statistical_significance,
            "metrics_analysis": analysis.metrics_analysis,
            "recommendations": analysis.recommendations,
            "optimal_prompt": analysis.optimal_prompt,
            "generated_at": analysis.generated_at.isoformat()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao analisar teste {test_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tests/{test_id}/feedback")
async def submit_user_feedback(
    test_id: str,
    feedback: UserFeedbackRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Submete feedback do usuário sobre resultado de teste"""
    try:
        # Em um sistema real, armazenaria feedback no banco de dados
        # Por agora, apenas registra nos logs
        
        logger.info(f"Feedback recebido para teste {test_id}, variante {feedback.variant_id}: "
                   f"rating={feedback.rating}, comments='{feedback.comments}'")
        
        return {
            "status": "feedback_received",
            "test_id": test_id,
            "variant_id": feedback.variant_id,
            "rating": feedback.rating,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erro ao processar feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tests", response_model=Dict[str, Any])
async def list_tests(
    test_type: Optional[TestType] = Query(None, description="Filtrar por tipo de teste"),
    limit: int = Query(50, ge=1, le=100, description="Limite de resultados"),
    offset: int = Query(0, ge=0, description="Offset para paginação"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Lista testes do usuário"""
    try:
        history = prompt_testing_service.get_test_history()
        
        # Filtra testes do usuário
        user_tests = {}
        for test_id, test_info in history["tests"].items():
            if test_info["config"]["metadata"].get("created_by") == current_user["id"]:
                if not test_type or test_info["config"]["test_type"] == test_type.value:
                    user_tests[test_id] = test_info
        
        # Aplica paginação
        test_items = list(user_tests.items())
        paginated_tests = dict(test_items[offset:offset + limit])
        
        return {
            "tests": paginated_tests,
            "total": len(user_tests),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Erro ao listar testes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics", response_model=List[Dict[str, str]])
async def get_available_metrics():
    """Lista métricas disponíveis para teste"""
    return [
        {
            "name": metric.value,
            "description": _get_metric_description(metric)
        }
        for metric in MetricType
    ]


@router.get("/templates/quick-test")
async def get_quick_test_template():
    """Retorna template para teste rápido A/B"""
    return {
        "template_name": "quick_ab_test",
        "description": "Template para teste A/B rápido com 2 variantes",
        "sample_config": {
            "test_type": "ab_test",
            "base_prompt": "a beautiful landscape",
            "variants": [
                {
                    "id": "variant_a",
                    "prompt": "a beautiful landscape",
                    "style_modifiers": [],
                    "technical_params": {"quality": "standard"},
                    "description": "Prompt original"
                },
                {
                    "id": "variant_b", 
                    "prompt": "a beautiful landscape, high quality, detailed, artistic",
                    "style_modifiers": ["artistic", "detailed"],
                    "technical_params": {"quality": "hd"},
                    "description": "Prompt otimizado"
                }
            ],
            "target_metrics": ["image_quality", "aesthetic_score"],
            "sample_size": 20
        }
    }


@router.get("/templates/iterative")
async def get_iterative_template():
    """Retorna template para refinamento iterativo"""
    return {
        "template_name": "iterative_refinement",
        "description": "Template para refinamento iterativo de prompt",
        "sample_config": {
            "base_prompt": "a futuristic robot in a garden",
            "target_metric": "image_quality",
            "iterations": 5
        },
        "expected_improvements": [
            "Adição de modificadores de qualidade",
            "Refinamento de descrições visuais",
            "Otimização de parâmetros técnicos",
            "Melhoria da composição",
            "Ajuste de iluminação e detalhes"
        ]
    }


@router.post("/batch/auto-optimize")
async def auto_optimize_prompts(
    prompts: List[str],
    target_metric: MetricType = MetricType.IMAGE_QUALITY,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Otimiza automaticamente uma lista de prompts"""
    try:
        if len(prompts) > 10:
            raise HTTPException(status_code=400, detail="Máximo de 10 prompts por vez")
        
        optimization_results = []
        
        for i, prompt in enumerate(prompts):
            # Cria teste iterativo para cada prompt
            test_id = await prompt_testing_service.create_iterative_refinement(
                base_prompt=prompt,
                target_metric=target_metric,
                iterations=3  # Otimização rápida
            )
            
            optimization_results.append({
                "original_prompt": prompt,
                "test_id": test_id,
                "status": "optimization_started"
            })
        
        return {
            "batch_id": f"batch_{int(datetime.utcnow().timestamp())}",
            "prompts_count": len(prompts),
            "target_metric": target_metric.value,
            "results": optimization_results,
            "estimated_completion": "5-10 minutes"
        }
        
    except Exception as e:
        logger.error(f"Erro na otimização em lote: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_testing_statistics(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Obtém estatísticas dos testes do usuário"""
    try:
        history = prompt_testing_service.get_test_history()
        
        # Filtra por usuário
        user_tests = []
        for test_id, test_info in history["tests"].items():
            if test_info["config"]["metadata"].get("created_by") == current_user["id"]:
                user_tests.append(test_info)
        
        # Calcula estatísticas
        total_tests = len(user_tests)
        total_results = sum(test["results_count"] for test in user_tests)
        
        # Tipos de teste
        test_types = {}
        for test in user_tests:
            test_type = test["config"]["test_type"]
            test_types[test_type] = test_types.get(test_type, 0) + 1
        
        return {
            "user_id": current_user["id"],
            "total_tests": total_tests,
            "total_results": total_results,
            "avg_results_per_test": total_results / total_tests if total_tests > 0 else 0,
            "test_types": test_types,
            "last_activity": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _get_metric_description(metric: MetricType) -> str:
    """Retorna descrição de uma métrica"""
    descriptions = {
        MetricType.GENERATION_TIME: "Tempo de geração da imagem (menor é melhor)",
        MetricType.IMAGE_QUALITY: "Qualidade técnica da imagem (0.0 - 1.0)",
        MetricType.PROMPT_ADHERENCE: "Aderência da imagem ao prompt (0.0 - 1.0)",
        MetricType.AESTHETIC_SCORE: "Score estético da composição (0.0 - 1.0)",
        MetricType.SAFETY_SCORE: "Score de segurança do conteúdo (0.0 - 1.0)",
        MetricType.USER_SATISFACTION: "Satisfação do usuário (1.0 - 5.0)",
        MetricType.COST_EFFICIENCY: "Eficiência de custo (qualidade/custo)"
    }
    return descriptions.get(metric, "Métrica customizada") 