from fastapi import APIRouter

api_router = APIRouter()

# Import and include route modules
from app.api.v1.endpoints import auth, cases, documents, reports, audio, profiles, comments
from app.api.v1.endpoints import smart_documents, optimized_rag, context_aware_prompts, quality_control, multimodal_rag, monitoring
from app.api.v1.endpoints import optimized_ad_reports, cache_stats

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(cases.router, prefix="/cases", tags=["cases"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(audio.router, prefix="/audio", tags=["audio"])
api_router.include_router(profiles.router, prefix="/profiles", tags=["profiles"])
api_router.include_router(comments.router, prefix="/comments", tags=["comments"])
api_router.include_router(smart_documents.router, prefix="/smart", tags=["smart-documents"])
api_router.include_router(optimized_rag.router, prefix="/optimized-rag", tags=["optimized-rag"])
api_router.include_router(context_aware_prompts.router, prefix="/context-prompts", tags=["context-prompts"])
api_router.include_router(quality_control.router, prefix="/quality", tags=["quality-control"])
api_router.include_router(multimodal_rag.router, prefix="/multimodal", tags=["multimodal-rag"])
api_router.include_router(monitoring.router, prefix="/monitoring", tags=["monitoring"])
api_router.include_router(optimized_ad_reports.router, prefix="/ad-reports", tags=["ad-reports"])
api_router.include_router(cache_stats.router, prefix="/cache", tags=["cache"])
