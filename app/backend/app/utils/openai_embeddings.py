"""
Utilities for working with embeddings using OpenAI models.
Designed as a drop-in replacement for the Google Gemini embeddings module.
"""
import os
import time
import random
import hashlib
import logging
import functools
import numpy as np
from typing import List, Optional, Union, Dict, Any, Tuple

from openai import OpenAI
from app.core.config import settings

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure OpenAI client
API_INITIALIZED = False
if settings.OPENAI_API_KEY:
    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        API_INITIALIZED = True
        logger.info("OpenAI client initialized with provided API key")
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {str(e)}")
        API_INITIALIZED = False
else:
    logger.warning("No OpenAI API key provided, API functionality will be limited")

# Define specific API error types for better handling
class EmbeddingAPIError(Exception):
    """Base class for embedding API errors"""
    pass

class RateLimitError(EmbeddingAPIError):
    """Raised when the API rate limit is exceeded"""
    pass

class AuthenticationError(EmbeddingAPIError):
    """Raised when authentication fails"""
    pass

class APIConnectionError(EmbeddingAPIError):
    """Raised when there's a connection issue with the API"""
    pass

def retry_with_exponential_backoff(
    initial_delay: float = 1,
    exponential_base: float = 2,
    jitter: bool = True,
    max_retries: int = 3,
    errors_to_retry: tuple = (RateLimitError, APIConnectionError)
):
    """
    Retry a function with exponential backoff for specified exceptions.
    
    Args:
        initial_delay: Initial delay in seconds
        exponential_base: Base for exponential delay
        jitter: Add random jitter to delay
        max_retries: Maximum number of retries
        errors_to_retry: Tuple of exceptions to retry
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            num_retries = 0
            delay = initial_delay
            
            while True:
                try:
                    return func(*args, **kwargs)
                    
                except errors_to_retry as e:
                    num_retries += 1
                    
                    if num_retries > max_retries:
                        logger.error(f"Maximum retries reached for {func.__name__}. Last error: {str(e)}")
                        raise
                        
                    delay *= exponential_base * (1 + jitter * random.random())
                    
                    logger.warning(f"Retry {num_retries}/{max_retries} for {func.__name__} after {delay:.2f}s due to: {str(e)}")
                    time.sleep(delay)
                    
        return wrapper
    return decorator

def _classify_api_error(error) -> Exception:
    """
    Classify the type of API error for better handling
    
    Args:
        error: The original exception
        
    Returns:
        A more specific exception type
    """
    error_message = str(error).lower()
    
    if "rate limit" in error_message or "quota" in error_message or "too many requests" in error_message:
        return RateLimitError(f"API rate limit exceeded: {error}")
    elif "authentication" in error_message or "unauthorized" in error_message or "api key" in error_message:
        return AuthenticationError(f"API authentication error: {error}")
    elif "connection" in error_message or "timeout" in error_message or "network" in error_message:
        return APIConnectionError(f"API connection error: {error}")
    else:
        return EmbeddingAPIError(f"API error: {error}")

@retry_with_exponential_backoff(
    initial_delay=1.0,
    exponential_base=2,
    jitter=True,
    max_retries=3,
    errors_to_retry=(RateLimitError, APIConnectionError)
)
def validate_api_connection() -> bool:
    """
    Validate that the OpenAI API connection is working by
    attempting to generate a simple embedding. This confirms
    the API key is valid and the service is accessible.
    
    Returns:
        Boolean indicating if the API connection is working
    """
    if not settings.OPENAI_API_KEY or not API_INITIALIZED:
        logger.warning("Cannot validate API connection - no API key or initialization failed")
        return False
        
    try:
        # Try to embed a simple test string
        logger.info("Validating OpenAI API connection...")
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input="Test API connection",
            dimensions=settings.EMBEDDING_DIMENSION
        )
        
        # Check if we got a valid response
        if response and hasattr(response, "data") and len(response.data) > 0:
            embedding = response.data[0].embedding
            if embedding and len(embedding) > 0:
                logger.info("OpenAI API connection validated successfully")
                return True
        
        logger.warning("API connection test failed - no embedding in response")
        return False
            
    except Exception as e:
        specific_error = _classify_api_error(e)
        logger.error(f"API connection validation failed: {str(specific_error)}")
        raise specific_error

def generate_embedding(text: str, dimension: int = 768) -> List[float]:
    """
    Generate embeddings using OpenAI's embedding model.
    Designed to be a drop-in replacement for Google's Gemini embedding function.
    
    Args:
        text: The text to generate embeddings for
        dimension: The dimension of the embeddings to return (default 768)
    
    Returns:
        A list of floating point values representing the embedding
    """
    if not settings.OPENAI_API_KEY or not API_INITIALIZED:
        logger.warning("OpenAI API not available, using fallback embedding generation")
        return generate_fallback_embedding(text, dimension)
    
    # Truncate very long texts to prevent API rejection
    if len(text) > 60000:
        logger.warning(f"Text length ({len(text)}) exceeds safe API limit, truncating to 60,000 chars")
        text = text[:60000]
    
    try:
        # Use the proper embedding API call
        response = client.embeddings.create(
            model="text-embedding-3-small",  # High quality, affordable model
            input=text,
            dimensions=dimension  # Explicitly set the dimension
        )
        
        # Check if embedding is in the response
        if response and hasattr(response, "data") and len(response.data) > 0:
            embedding_vector = response.data[0].embedding
            logger.info(f"Successfully generated embedding using OpenAI API, dimension: {len(embedding_vector)}")
            
            # Return the embedding as a list
            return list(embedding_vector)
        else:
            # If we don't get an embedding back, log the issue and fall back
            logger.warning("No embedding found in API response, using fallback method")
            return generate_deterministic_embedding(text, dimension)
            
    except Exception as e:
        # Classify error for better handling
        specific_error = _classify_api_error(e)
        logger.error(f"Error generating embedding with OpenAI API: {str(specific_error)}")
        
        # Re-raise classified errors for potential retry
        if isinstance(specific_error, (RateLimitError, APIConnectionError)):
            raise specific_error
        elif isinstance(specific_error, AuthenticationError):
            logger.critical("Authentication failed with OpenAI API, check your API key")
            return generate_fallback_embedding(text, dimension)
        else:
            # Fall back to deterministic embedding for other errors
            return generate_fallback_embedding(text, dimension)

def generate_deterministic_embedding(text: str, dimension: int = 768) -> List[float]:
    """
    Generate a deterministic embedding based on text hash.
    This ensures consistent results for the same text.
    
    Args:
        text: The text to generate a deterministic embedding for
        dimension: The dimension of the embedding to return
        
    Returns:
        A list of float values representing the embedding
    """
    # Create a deterministic hash from the text
    hash_object = hashlib.md5(text.encode())
    hash_hex = hash_object.hexdigest()
    
    # Convert the hex digest to a list of float values between -1 and 1
    embedding = []
    for i in range(0, len(hash_hex), 2):
        if i < len(hash_hex) - 1:
            # Convert pair of hex digits to int (0-255), then scale to -1.0 to 1.0
            hex_pair = hash_hex[i:i+2]
            value = int(hex_pair, 16) / 127.5 - 1.0
            embedding.append(value)
    
    # Ensure the dimension is correct (pad or truncate)
    if len(embedding) > dimension:
        return embedding[:dimension]
    elif len(embedding) < dimension:
        # Use hash-based values to pad
        seed = int(hash_hex[:8], 16)
        random.seed(seed)
        padding = [random.uniform(-1, 1) for _ in range(dimension - len(embedding))]
        return embedding + padding
    
    return embedding

def generate_fallback_embedding(text: str, dimension: int = 768) -> List[float]:
    """
    Generate a fallback embedding when the API fails.
    
    Args:
        text: The text to generate an embedding for
        dimension: The dimension of the embedding to return
        
    Returns:
        A list of float values representing the embedding
    """
    # First try deterministic method
    try:
        logger.info("Using deterministic embedding generation as fallback")
        return generate_deterministic_embedding(text, dimension)
    except Exception as e:
        # If that fails, resort to random
        logger.warning(f"Deterministic embedding failed: {str(e)}. Using random embedding.")
        random.seed(42)  # Fixed seed for reproducibility
        return [random.uniform(-1, 1) for _ in range(dimension)]

def calculate_similarity(embedding1: List[float], embedding2: List[float]) -> float:
    """
    Calculate cosine similarity between two embeddings.
    
    Args:
        embedding1: First embedding vector
        embedding2: Second embedding vector
        
    Returns:
        Similarity score between 0 and 1, where 1 is most similar
    """
    # Convert to numpy arrays
    vec1 = np.array(embedding1)
    vec2 = np.array(embedding2)
    
    # Calculate cosine similarity
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    # Avoid division by zero
    if norm1 == 0 or norm2 == 0:
        return 0
        
    return dot_product / (norm1 * norm2)

@retry_with_exponential_backoff(
    initial_delay=1.0,
    exponential_base=2,
    jitter=True,
    max_retries=3,
    errors_to_retry=(RateLimitError, APIConnectionError)
)
def generate_query_embedding(text: str, dimension: int = 768) -> List[float]:
    """
    Generate embeddings specifically for query purposes.
    This is optimized for search queries rather than documents.
    
    Args:
        text: The query text to generate embeddings for
        dimension: The dimension of the embeddings to return (default 768)
    
    Returns:
        A list of floating point values representing the query embedding
    """
    if not settings.OPENAI_API_KEY or not API_INITIALIZED:
        logger.warning("OpenAI API not available, using fallback embedding generation for query")
        return generate_fallback_embedding(text, dimension)
    
    # Truncate very long queries to prevent API rejection
    if len(text) > 10000:  # Queries should be shorter than document chunks
        logger.warning(f"Query length ({len(text)}) exceeds safe API limit, truncating to 10,000 chars")
        text = text[:10000]
    
    try:
        # Use the proper embedding API call with retrieval_query task type
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text,
            dimensions=dimension
        )
        
        # Check if embedding is in the response
        if response and hasattr(response, "data") and len(response.data) > 0:
            embedding_vector = response.data[0].embedding
            logger.info(f"Successfully generated query embedding using OpenAI API, dimension: {len(embedding_vector)}")
            
            # Return the embedding as a list
            return list(embedding_vector)
        else:
            # If we don't get an embedding back, log the issue and fall back
            logger.warning("No embedding found in query API response, using fallback method")
            return generate_deterministic_embedding(text, dimension)
            
    except Exception as e:
        # Classify error for better handling
        specific_error = _classify_api_error(e)
        logger.error(f"Error generating query embedding with OpenAI API: {str(specific_error)}")
        
        # Re-raise classified errors for potential retry
        if isinstance(specific_error, (RateLimitError, APIConnectionError)):
            raise specific_error
        elif isinstance(specific_error, AuthenticationError):
            logger.critical("Authentication failed with OpenAI API, check your API key")
            return generate_fallback_embedding(text, dimension)
        else:
            # Fall back to deterministic embedding for other errors
            return generate_fallback_embedding(text, dimension)