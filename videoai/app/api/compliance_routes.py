"""
Compliance API Routes

Endpoints para gestão de compliance, direitos do usuário e auditoria.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from videoai.app.core.privacy import get_privacy_manager
from videoai.app.services.compliance.content_moderation import get_content_moderation_service, ContentCategory

logger = logging.getLogger(__name__)

# Modelos Pydantic
class DataExportRequest(BaseModel):
    """Request para exportação de dados do usuário"""
    user_id: str = Field(..., description="ID do usuário")
    include_audit_logs: bool = Field(True, description="Incluir logs de auditoria")
    include_moderation_history: bool = Field(True, description="Incluir histórico de moderação")

class DataDeletionRequest(BaseModel):
    """Request para deleção de dados do usuário"""
    user_id: str = Field(..., description="ID do usuário")
    confirmation: str = Field(..., description="Confirmação 'DELETE_MY_DATA'")

class ModerationRequest(BaseModel):
    """Request para moderação de conteúdo"""
    content: str = Field(..., description="Conteúdo para moderação")
    content_type: str = Field(..., description="Tipo de conteúdo")
    user_id: str = Field(..., description="ID do usuário")

class PrivacySettingsUpdate(BaseModel):
    """Update de configurações de privacidade"""
    user_id: str = Field(..., description="ID do usuário")
    data_retention_days: Optional[int] = Field(None, description="Dias de retenção customizados")
    allow_analytics: bool = Field(True, description="Permitir analytics")
    allow_marketing: bool = Field(False, description="Permitir marketing")

# Router
router = APIRouter(prefix="/api/v1/compliance", tags=["compliance"])

@router.get("/health")
async def compliance_health_check():
    """Health check do sistema de compliance"""
    try:
        privacy_manager = get_privacy_manager()
        moderation_service = get_content_moderation_service()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "privacy_manager": "active",
                "content_moderation": "active"
            }
        }
    except Exception as e:
        logger.error(f"Compliance health check failed: {e}")
        raise HTTPException(status_code=503, detail="Compliance services unavailable")

@router.post("/data/export")
async def export_user_data(request: DataExportRequest, background_tasks: BackgroundTasks):
    """
    Exporta dados do usuário (GDPR Art. 15 - Right to Access)
    
    Retorna todos os dados pessoais processados sobre o usuário.
    """
    try:
        privacy_manager = get_privacy_manager()
        moderation_service = get_content_moderation_service()
        
        # Coletar dados do privacy manager
        user_data = privacy_manager.get_user_data(request.user_id)
        
        # Adicionar histórico de moderação se solicitado
        if request.include_moderation_history:
            moderation_history = await moderation_service.get_user_moderation_history(request.user_id)
            user_data['data_categories']['moderation_history'] = moderation_history
        
        # Log da exportação
        privacy_manager.log_data_processing(
            user_id=request.user_id,
            operation='data_export',
            data_type='user_data_export',
            metadata={
                'export_timestamp': datetime.utcnow().isoformat(),
                'include_audit_logs': request.include_audit_logs,
                'include_moderation_history': request.include_moderation_history
            }
        )
        
        return {
            "status": "success",
            "message": "User data exported successfully",
            "data": user_data
        }
        
    except Exception as e:
        logger.error(f"Data export failed for user {request.user_id}: {e}")
        raise HTTPException(status_code=500, detail="Data export failed")

@router.post("/data/delete")
async def delete_user_data(request: DataDeletionRequest, background_tasks: BackgroundTasks):
    """
    Deleta dados do usuário (GDPR Art. 17 - Right to Erasure)
    
    Remove permanentemente todos os dados pessoais do usuário.
    """
    try:
        # Verificar confirmação
        if request.confirmation != "DELETE_MY_DATA":
            raise HTTPException(
                status_code=400, 
                detail="Invalid confirmation. Must be 'DELETE_MY_DATA'"
            )
        
        privacy_manager = get_privacy_manager()
        
        # Executar deleção
        deletion_result = privacy_manager.delete_user_data(request.user_id)
        
        return {
            "status": "success",
            "message": "User data deleted successfully",
            "deletion_result": deletion_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Data deletion failed for user {request.user_id}: {e}")
        raise HTTPException(status_code=500, detail="Data deletion failed")

@router.post("/content/moderate")
async def moderate_content(request: ModerationRequest):
    """
    Modera conteúdo usando o sistema de moderação
    
    Analisa conteúdo para violações de política e conformidade.
    """
    try:
        moderation_service = get_content_moderation_service()
        
        # Validar tipo de conteúdo
        try:
            content_type = ContentCategory(request.content_type)
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid content type. Must be one of: {[c.value for c in ContentCategory]}"
            )
        
        # Executar moderação
        moderation_result = await moderation_service.moderate_content(
            content=request.content,
            content_type=content_type,
            user_id=request.user_id
        )
        
        return {
            "status": "success",
            "moderation_result": moderation_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Content moderation failed: {e}")
        raise HTTPException(status_code=500, detail="Content moderation failed")

@router.get("/moderation/stats")
async def get_moderation_stats(hours: int = Query(24, ge=1, le=168)):
    """
    Obtém estatísticas de moderação
    
    Retorna métricas de moderação para o período especificado.
    """
    try:
        moderation_service = get_content_moderation_service()
        
        stats = await moderation_service.get_moderation_stats(hours=hours)
        
        return {
            "status": "success",
            "period_hours": hours,
            "stats": stats,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get moderation stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get moderation stats")

@router.get("/user/{user_id}/moderation-history")
async def get_user_moderation_history(
    user_id: str, 
    limit: int = Query(50, ge=1, le=200)
):
    """
    Obtém histórico de moderação do usuário
    
    Retorna histórico de moderação de conteúdo para o usuário específico.
    """
    try:
        moderation_service = get_content_moderation_service()
        
        history = await moderation_service.get_user_moderation_history(
            user_id=user_id,
            limit=limit
        )
        
        return {
            "status": "success",
            "user_id": user_id,
            "history": history,
            "count": len(history)
        }
        
    except Exception as e:
        logger.error(f"Failed to get user moderation history: {e}")
        raise HTTPException(status_code=500, detail="Failed to get moderation history")

@router.get("/privacy/policy")
async def get_privacy_policy():
    """
    Retorna política de privacidade em formato estruturado
    
    Fornece informações sobre coleta, uso e retenção de dados.
    """
    return {
        "policy_version": "1.0",
        "last_updated": "2025-01-27",
        "data_controller": {
            "name": "VideoAI Platform",
            "contact": "privacy@videoai.com"
        },
        "data_categories": {
            "raw_prompts": {
                "retention_period": "1 hour",
                "purpose": "Content generation",
                "legal_basis": "Legitimate interest"
            },
            "generated_images": {
                "retention_period": "30 days",
                "purpose": "Service delivery",
                "legal_basis": "Contract performance"
            },
            "user_metadata": {
                "retention_period": "90 days",
                "purpose": "Service improvement",
                "legal_basis": "Legitimate interest"
            },
            "audit_logs": {
                "retention_period": "3 years",
                "purpose": "Legal compliance",
                "legal_basis": "Legal obligation"
            }
        },
        "user_rights": [
            "Right to access (Art. 15)",
            "Right to rectification (Art. 16)",
            "Right to erasure (Art. 17)",
            "Right to restrict processing (Art. 18)",
            "Right to data portability (Art. 20)",
            "Right to object (Art. 21)"
        ],
        "automated_decision_making": {
            "used": True,
            "description": "Content moderation using AI models",
            "human_review_available": True
        }
    }

@router.post("/privacy/settings")
async def update_privacy_settings(request: PrivacySettingsUpdate):
    """
    Atualiza configurações de privacidade do usuário
    
    Permite ao usuário controlar como seus dados são processados.
    """
    try:
        privacy_manager = get_privacy_manager()
        
        # Log da atualização de configurações
        privacy_manager.log_data_processing(
            user_id=request.user_id,
            operation='privacy_settings_update',
            data_type='user_preferences',
            metadata={
                'data_retention_days': request.data_retention_days,
                'allow_analytics': request.allow_analytics,
                'allow_marketing': request.allow_marketing,
                'updated_at': datetime.utcnow().isoformat()
            }
        )
        
        return {
            "status": "success",
            "message": "Privacy settings updated successfully",
            "settings": {
                "data_retention_days": request.data_retention_days,
                "allow_analytics": request.allow_analytics,
                "allow_marketing": request.allow_marketing
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to update privacy settings for user {request.user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update privacy settings")

@router.get("/audit/summary")
async def get_audit_summary(hours: int = Query(24, ge=1, le=168)):
    """
    Obtém resumo de auditoria do sistema
    
    Retorna métricas de compliance e auditoria para o período especificado.
    """
    try:
        moderation_service = get_content_moderation_service()
        
        # Obter estatísticas de moderação
        moderation_stats = await moderation_service.get_moderation_stats(hours=hours)
        
        # Calcular métricas de compliance
        total_content = moderation_stats.get('total_moderated', 0)
        rejected_content = moderation_stats.get('rejected', 0)
        compliance_rate = ((total_content - rejected_content) / total_content * 100) if total_content > 0 else 100
        
        return {
            "status": "success",
            "period_hours": hours,
            "summary": {
                "total_content_processed": total_content,
                "compliance_rate_percent": round(compliance_rate, 2),
                "content_rejected": rejected_content,
                "high_risk_content": moderation_stats.get('threat_levels', {}).get('high', 0),
                "critical_threats": moderation_stats.get('threat_levels', {}).get('critical', 0)
            },
            "detailed_stats": moderation_stats,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get audit summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to get audit summary")
