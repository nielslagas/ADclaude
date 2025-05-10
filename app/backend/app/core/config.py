import os
from typing import Any, Dict, Optional

from pydantic import BaseModel, PostgresDsn, field_validator
from pydantic import ConfigDict

class Settings(BaseModel):
    model_config = ConfigDict(
        case_sensitive=True,
        env_file=".env",
        extra="ignore"
    )
    
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "AD-Rapport Generator"
    
    # Supabase Configuration
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "http://localhost:8000")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0")
    
    # Database Configuration
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "db")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "postgres")
    
    # LLM Provider Configuration
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "google")  # Options: google, openai, anthropic
    
    # Google AI Configuration
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    
    # Anthropic Configuration
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-3-7-sonnet-20250219")
    
    # Redis Configuration
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Application Specific Settings
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    STORAGE_PATH: str = os.getenv("STORAGE_PATH", "/app/storage")
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "768"))  # Default to 768
    
    # RAG Pipeline Settings
    DB_OPERATION_TIMEOUT: int = int(os.getenv("DB_OPERATION_TIMEOUT", "30"))  # seconds
    EMBEDDING_BATCH_SIZE: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "5"))
    API_TIMEOUT: int = int(os.getenv("API_TIMEOUT", "20"))  # seconds
    CHUNKING_TIMEOUT: int = int(os.getenv("CHUNKING_TIMEOUT", "30"))  # seconds
    MAX_RETRY_ATTEMPTS: int = int(os.getenv("MAX_RETRY_ATTEMPTS", "3"))
    
    # Hybrid Approach Settings
    HYBRID_APPROACH: bool = os.getenv("HYBRID_APPROACH", "1").lower() in ["1", "true", "yes", "y"]
    DIRECT_LLM_MODE: bool = os.getenv("DIRECT_LLM_MODE", "0").lower() in ["1", "true", "yes", "y"]
    MAX_DIRECT_DOCUMENT_LENGTH: int = int(os.getenv("MAX_DIRECT_DOCUMENT_LENGTH", "80000"))
    
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

settings = Settings()