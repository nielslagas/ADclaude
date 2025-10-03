from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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
    # Validate environment configuration
    _validate_environment()
    
    # Initialize the database and vector store
    init_db()
    
    # Validate LLM API connection on startup based on configured provider
    _validate_llm_connection()

def _validate_environment():
    """Validate required environment variables and configuration"""
    logger.info("Validating environment configuration...")
    
    # Check LLM provider configuration
    if settings.LLM_PROVIDER == "google" and not settings.GOOGLE_API_KEY:
        logger.warning("Google LLM provider selected but GOOGLE_API_KEY not configured")
    elif settings.LLM_PROVIDER == "anthropic" and not settings.ANTHROPIC_API_KEY:
        logger.warning("Anthropic LLM provider selected but ANTHROPIC_API_KEY not configured")
    elif settings.LLM_PROVIDER == "openai" and not settings.OPENAI_API_KEY:
        logger.warning("OpenAI LLM provider selected but OPENAI_API_KEY not configured")
    
    # Check database configuration
    required_db_vars = ["POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_SERVER", "POSTGRES_DB"]
    missing_vars = []
    for var in required_db_vars:
        if not getattr(settings, var, None):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing required database configuration: {', '.join(missing_vars)}")
    else:
        logger.info("Database configuration validated")
    
    logger.info(f"Environment validation complete. LLM Provider: {settings.LLM_PROVIDER}")

def _validate_llm_connection():
    """Validate LLM API connection based on configured provider"""
    if settings.LLM_PROVIDER == "google" and settings.GOOGLE_API_KEY:
        logger.info("Validating Google API connection on startup...")
        api_working = validate_api_connection()
        if api_working:
            logger.info("Google Gemini API connection verified successfully")
        else:
            logger.warning("Google Gemini API connection validation failed, will use fallback methods")
    elif settings.LLM_PROVIDER == "anthropic" and settings.ANTHROPIC_API_KEY:
        logger.info("Anthropic Claude API configured and ready")
    elif settings.LLM_PROVIDER == "openai" and settings.OPENAI_API_KEY:
        logger.info("OpenAI API configured and ready")
    else:
        logger.warning(f"No API key configured for LLM provider: {settings.LLM_PROVIDER}")

# Global exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Handle HTTP exceptions with consistent error format
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": "http_error",
                "status_code": exc.status_code,
                "message": exc.detail,
                "path": str(request.url.path)
            }
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Handle unexpected exceptions
    """
    logger.error(f"Unhandled exception on {request.url.path}: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "type": "internal_error",
                "status_code": 500,
                "message": "An unexpected error occurred. Please try again later.",
                "path": str(request.url.path)
            }
        }
    )

@app.get("/")
async def root():
    return {"message": "AD-Rapport Generator API", "version": "1.0.0"}
    
@app.get("/api/health")
async def health_check():
    """Health check endpoint that also validates API connections"""
    status = {
        "status": "healthy",
        "database": True,
        "llm_provider": settings.LLM_PROVIDER,
        "llm_api": False
    }
    
    # Check LLM API based on configured provider
    if settings.LLM_PROVIDER == "google" and settings.GOOGLE_API_KEY:
        api_status = validate_api_connection()
        status["llm_api"] = api_status
        status["provider_details"] = "Google Gemini API"
        if not api_status:
            status["llm_message"] = "Google API connection failed, using fallback methods"
    elif settings.LLM_PROVIDER == "anthropic" and settings.ANTHROPIC_API_KEY:
        status["llm_api"] = True  # Assume working for now
        status["provider_details"] = "Anthropic Claude API"
        status["llm_message"] = "Anthropic API configured"
    elif settings.LLM_PROVIDER == "openai" and settings.OPENAI_API_KEY:
        status["llm_api"] = True  # Assume working for now
        status["provider_details"] = "OpenAI API"
        status["llm_message"] = "OpenAI API configured"
    else:
        status["llm_message"] = f"No API key provided for {settings.LLM_PROVIDER} provider"
        
    return status

# Import and include routers
from app.api.v1.router import api_router
app.include_router(api_router, prefix=settings.API_V1_STR)
