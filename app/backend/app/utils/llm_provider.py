"""
Dynamic LLM provider switching based on configuration.
This module provides a consistent interface regardless of which underlying LLM provider is used.
"""
import logging
from app.core.config import settings

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize provider-specific modules
if settings.LLM_PROVIDER == "openai":
    logger.info("Using OpenAI as LLM provider")
    from app.utils.openai_llm import GenerativeModel, configure
    configure(api_key=settings.OPENAI_API_KEY)
    
elif settings.LLM_PROVIDER == "anthropic":
    logger.info("Using Anthropic Claude as LLM provider")
    from app.utils.claude_llm import GenerativeModel, configure
    configure(api_key=settings.ANTHROPIC_API_KEY)
    
else:
    logger.warning(f"Unknown LLM provider '{settings.LLM_PROVIDER}', defaulting to Anthropic")
    from app.utils.claude_llm import GenerativeModel, configure
    configure(api_key=settings.ANTHROPIC_API_KEY)

# Initialize embedding modules - always use OpenAI for embeddings
logger.info("Using OpenAI for embeddings")
from app.utils.openai_embeddings import (
    generate_embedding, 
    generate_query_embedding,
    calculate_similarity
)

# Standard safety settings that work across providers
def get_safety_settings(dangerous_content_level="BLOCK_NONE"):
    """
    Get standardized safety settings that work across providers.
    
    Args:
        dangerous_content_level: Level for dangerous content filtering
        
    Returns:
        Dictionary of safety settings
    """
    return {
        "HARASSMENT": "BLOCK_ONLY_HIGH",
        "HATE_SPEECH": "BLOCK_ONLY_HIGH",
        "SEXUALLY_EXPLICIT": "BLOCK_ONLY_HIGH", 
        "DANGEROUS_CONTENT": dangerous_content_level
    }

# Standard generation config that works across providers
def get_generation_config(temperature=0.1, max_tokens=4096):
    """
    Get standardized generation configuration that works across providers.
    
    Args:
        temperature: Temperature parameter for generation (0.0-1.0)
        max_tokens: Maximum number of tokens to generate
        
    Returns:
        Dictionary of generation parameters
    """
    return {
        "temperature": temperature,
        "max_output_tokens": max_tokens,
        "top_p": 0.95,
        "top_k": 40
    }

def get_llm_model_name():
    """
    Get the appropriate model name based on the configured provider.
    
    Returns:
        String with the model name for the current provider
    """
    if settings.LLM_PROVIDER == "google":
        return "gemini-1.5-pro"
    elif settings.LLM_PROVIDER == "openai":
        return settings.OPENAI_MODEL
    elif settings.LLM_PROVIDER == "anthropic":
        return settings.ANTHROPIC_MODEL
    else:
        return "gemini-1.5-pro"  # Default fallback

def create_llm_instance(temperature=0.1, max_tokens=4096, dangerous_content_level="BLOCK_NONE"):
    """
    Create a standardized LLM instance with the configured provider.
    
    Args:
        temperature: Temperature parameter for generation
        max_tokens: Maximum number of tokens to generate
        dangerous_content_level: Level for dangerous content filtering
        
    Returns:
        LLM instance ready to use
    """
    safety_settings = get_safety_settings(dangerous_content_level)
    generation_config = get_generation_config(temperature, max_tokens)
    model_name = get_llm_model_name()
    
    return GenerativeModel(
        model_name=model_name,
        safety_settings=safety_settings,
        generation_config=generation_config
    )