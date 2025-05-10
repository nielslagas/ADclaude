from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.init_db import init_db
import logging
from app.utils.embeddings import validate_api_connection

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8080", "*"],  # Vue.js dev server defaults and any origin for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"]  # Important for file downloads
)

@app.on_event("startup")
def on_startup():
    """
    Initialize resources when the application starts
    """
    # Initialize the database and vector store
    init_db()
    
    # Validate Google API connection on startup
    if settings.GOOGLE_API_KEY:
        logger.info("Validating Google API connection on startup...")
        api_working = validate_api_connection()
        if api_working:
            logger.info("Google Gemini API connection verified successfully")
        else:
            logger.warning("Google Gemini API connection validation failed, will use fallback methods")

@app.get("/")
async def root():
    return {"message": "AD-Rapport Generator API", "version": "1.0.0"}
    
@app.get("/api/health")
async def health_check():
    """Health check endpoint that also validates API connections"""
    status = {
        "status": "healthy",
        "database": True,
        "gemini_api": False
    }
    
    # Check Gemini API
    if settings.GOOGLE_API_KEY:
        api_status = validate_api_connection()
        status["gemini_api"] = api_status
        if not api_status:
            status["gemini_message"] = "API connection failed, using fallback methods"
    else:
        status["gemini_message"] = "No API key provided, using fallback methods"
        
    return status

# Import and include routers
from app.api.v1.router import api_router
app.include_router(api_router, prefix=settings.API_V1_STR)
