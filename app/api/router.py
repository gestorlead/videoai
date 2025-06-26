"""
VideoAI API Router
"""

from fastapi import APIRouter
from app.api.routes import image, video, social, auth, async_jobs
from app.api.v1.endpoints import image_generation
# from app.api.v1.endpoints import prompt_testing
# from app.api.v1.endpoints import media_tasks


api_router = APIRouter()

# Include route modules
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(image.router, prefix="/image", tags=["image-generation"])
api_router.include_router(video.router, prefix="/video", tags=["video-creation"])
api_router.include_router(social.router, prefix="/social", tags=["social-media"])
api_router.include_router(async_jobs.router, prefix="/async", tags=["async-jobs"])

# Sistema de tarefas de mídia unificado (v1) - Temporariamente desabilitado
# api_router.include_router(media_tasks.router, prefix="/v1/media", tags=["media-tasks"])

# Sistema de teste e refinamento de prompts (v1) - Temporariamente desabilitado
# api_router.include_router(prompt_testing.router, prefix="/v1/prompt-testing", tags=["prompt-testing"])

# Sistema avançado de geração de imagens (v1)
api_router.include_router(image_generation.router, prefix="/v1/images", tags=["ai-image-generation"])
