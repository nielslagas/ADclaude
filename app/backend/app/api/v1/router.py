from fastapi import APIRouter

api_router = APIRouter()

# Import and include route modules
from app.api.v1.endpoints import auth, cases, documents, reports, audio, profiles, comments
from app.api.v1.endpoints import test_audio

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(cases.router, prefix="/cases", tags=["cases"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(audio.router, prefix="/audio", tags=["audio"])
api_router.include_router(profiles.router, prefix="/profiles", tags=["profiles"])
api_router.include_router(comments.router, prefix="/comments", tags=["comments"])
api_router.include_router(test_audio.router, prefix="/test-audio", tags=["test-audio"])
