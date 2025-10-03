"""
Utilities for working with embeddings using Google Gemini models.
"""
import google.generativeai as genai
import numpy as np
from typing import List, Optional, Union, Dict, Any, Tuple
import hashlib
import random
import time
import functools
from app.core.config import settings
from app.utils.rag_cache import cached
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Google AI API
API_INITIALIZED = False
if settings.GOOGLE_API_KEY:
    try:
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        API_INITIALIZED = True
        logger.info("Google Generative AI SDK initialized with provided API key")
    except Exception as e:
        logger.error(f"Failed to initialize Google Generative AI SDK: {str(e)}")
        API_INITIALIZED = False
else:
    logger.warning("No Google API key provided, API functionality will be limited")

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
    Validate that the Google API connection is working by
    attempting to generate a simple embedding. This confirms
    the API key is valid and the service is accessible.
    
    Returns:
        Boolean indicating if the API connection is working
    """
    if not settings.GOOGLE_API_KEY or not API_INITIALIZED:
        logger.warning("Cannot validate API connection - no API key or initialization failed")
        return False
        
    try:
        # Try to embed a simple test string
        logger.info("Validating Google API connection...")
        result = genai.embed_content(
            model="models/embedding-001",
            content="Test API connection",
            task_type="retrieval_document"
        )
        
        # Check if we got a valid response
        if (hasattr(result, "embedding") and result.embedding) or (
            isinstance(result, dict) and "embedding" in result
        ):
            logger.info("Google API connection validated successfully")
            return True
        else:
            logger.warning("API connection test failed - no embedding in response")
            return False
            
    except Exception as e:
        specific_error = _classify_api_error(e)
        logger.error(f"API connection validation failed: {str(specific_error)}")
        return False

@cached("embed:doc", ttl=604800)  # 7 days
def generate_embedding(text: str, dimension: int = 768, task_type: str = "RETRIEVAL_DOCUMENT") -> List[float]:
    """
    Generate embeddings using Google's Gemini embedding model.
    
    Args:
        text: The text to generate embeddings for
        dimension: The dimension of the embeddings to return (default 768)
        task_type: The type of embedding task (default "RETRIEVAL_DOCUMENT")
    
    Returns:
        A list of floating point values representing the embedding
    """
    # TODO: Cache document embeddings based on text hash
    if not settings.GOOGLE_API_KEY or not API_INITIALIZED:
        logger.warning("Google API not available, using fallback embedding generation")
        return generate_fallback_embedding(text, dimension)
    
    # Truncate very long texts to prevent API rejection (typical limit is 50k-60k tokens)
    if len(text) > 60000:
        logger.warning(f"Text length ({len(text)}) exceeds safe API limit, truncating to 60,000 chars")
        text = text[:60000]
    
    try:
        # Use the proper embedding API call
        result = genai.embed_content(
            model="models/embedding-001",
            content=text,
            task_type="retrieval_document",
            title="document chunk"
        )
        
        # Check if embedding is in the response
        if hasattr(result, "embedding") and result.embedding:
            logger.info(f"Successfully generated embedding using Gemini API, dimension: {len(result.embedding)}")
            embedding_vector = result.embedding
            
            # Ensure the dimension is correct
            if len(embedding_vector) > dimension:
                return embedding_vector[:dimension]
            elif len(embedding_vector) < dimension:
                # Pad with zeros
                return list(embedding_vector) + [0.0] * (dimension - len(embedding_vector))
            return list(embedding_vector)
        elif isinstance(result, dict) and "embedding" in result:
            # Handle case where result is a dictionary
            logger.info(f"Successfully generated embedding using Gemini API (dict format), dimension: {len(result['embedding'])}")
            embedding_vector = result["embedding"]
            
            # Ensure the dimension is correct
            if len(embedding_vector) > dimension:
                return embedding_vector[:dimension]
            elif len(embedding_vector) < dimension:
                # Pad with zeros
                return list(embedding_vector) + [0.0] * (dimension - len(embedding_vector))
            return list(embedding_vector)
        else:
            # If we don't get an embedding back, log the issue and fall back
            logger.warning("No embedding found in API response, using fallback method")
            logger.debug(f"API response structure: {type(result).__name__}, {dir(result)}")
            return generate_deterministic_embedding(text, dimension)
            
    except Exception as e:
        # Classify error for better handling
        specific_error = _classify_api_error(e)
        logger.error(f"Error generating embedding with Gemini API: {str(specific_error)}")
        
        # Re-raise classified errors for potential retry
        if isinstance(specific_error, (RateLimitError, APIConnectionError)):
            raise specific_error
        elif isinstance(specific_error, AuthenticationError):
            logger.critical("Authentication failed with Gemini API, check your API key")
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
@cached("embed:query", ttl=604800)  # 7 days
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
    # TODO: Cache query embeddings based on text hash
    if not settings.GOOGLE_API_KEY or not API_INITIALIZED:
        logger.warning("Google API not available, using fallback embedding generation for query")
        return generate_fallback_embedding(text, dimension)
    
    # Truncate very long queries to prevent API rejection
    if len(text) > 10000:  # Queries should be shorter than document chunks
        logger.warning(f"Query length ({len(text)}) exceeds safe API limit, truncating to 10,000 chars")
        text = text[:10000]
    
    try:
        # Use the proper embedding API call with retrieval_query task type
        result = genai.embed_content(
            model="models/embedding-001",
            content=text,
            task_type="retrieval_query"  # Use query-specific embedding
        )
        
        # Check if embedding is in the response
        if hasattr(result, "embedding") and result.embedding:
            logger.info(f"Successfully generated query embedding using Gemini API, dimension: {len(result.embedding)}")
            embedding_vector = result.embedding
            
            # Ensure the dimension is correct
            if len(embedding_vector) > dimension:
                return embedding_vector[:dimension]
            elif len(embedding_vector) < dimension:
                # Pad with zeros
                return list(embedding_vector) + [0.0] * (dimension - len(embedding_vector))
            return list(embedding_vector)
        elif isinstance(result, dict) and "embedding" in result:
            # Handle case where result is a dictionary
            logger.info(f"Successfully generated query embedding using Gemini API (dict format), dimension: {len(result['embedding'])}")
            embedding_vector = result["embedding"]
            
            # Ensure the dimension is correct
            if len(embedding_vector) > dimension:
                return embedding_vector[:dimension]
            elif len(embedding_vector) < dimension:
                # Pad with zeros
                return list(embedding_vector) + [0.0] * (dimension - len(embedding_vector))
            return list(embedding_vector)
        else:
            # If we don't get an embedding back, log the issue and fall back
            logger.warning("No embedding found in query API response, using fallback method")
            logger.debug(f"API response structure: {type(result).__name__}, {dir(result)}")
            return generate_deterministic_embedding(text, dimension)
            
    except Exception as e:
        # Classify error for better handling
        specific_error = _classify_api_error(e)
        logger.error(f"Error generating query embedding with Gemini API: {str(specific_error)}")
        
        # Re-raise classified errors for potential retry
        if isinstance(specific_error, (RateLimitError, APIConnectionError)):
            raise specific_error
        elif isinstance(specific_error, AuthenticationError):
            logger.critical("Authentication failed with Gemini API, check your API key")
            return generate_fallback_embedding(text, dimension)
        else:
            # Fall back to deterministic embedding for other errors
            return generate_fallback_embedding(text, dimension)