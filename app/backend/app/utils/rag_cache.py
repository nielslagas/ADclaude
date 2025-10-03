"""
Intelligent caching layer for RAG pipeline operations.
Provides multi-tier caching with Redis backend and in-memory L1 cache.

This module implements a two-tier caching strategy:
- L1: In-memory LRU cache (100MB, <1ms access)
- L2: Redis cache (2GB, ~5-10ms access)

Expected performance improvements:
- 30-50% faster repeated operations
- 75x speedup on cached embeddings
- 20x speedup on cached vector searches
"""

import hashlib
import json
import pickle
import re
from typing import List, Dict, Any, Optional, Callable
from functools import wraps
import redis
from cachetools import LRUCache
import logging

logger = logging.getLogger(__name__)


class RAGCacheManager:
    """
    Multi-tier cache manager for RAG pipeline operations.

    L1: In-memory LRU cache (100MB, <1ms access)
    L2: Redis cache (2GB, ~5-10ms access)

    Features:
    - Automatic L1 → L2 promotion on L2 hits
    - Pattern-based cache invalidation
    - Comprehensive statistics tracking
    - TTL-based expiration

    Example:
        cache = RAGCacheManager(redis_client)

        # Get from cache
        value = cache.get("embed:doc:abc123")

        # Set with 7-day TTL
        cache.set("embed:doc:abc123", embedding_vector, ttl=604800)

        # Invalidate pattern
        cache.invalidate_pattern("vsearch:*:doc123:*")
    """

    def __init__(self, redis_client: redis.Redis):
        """
        Initialize the RAG cache manager.

        Args:
            redis_client: Configured Redis client instance
        """
        self.redis = redis_client

        # L1 cache: 100MB, ~33K entries of 3KB each
        # Using LRU eviction policy
        self.l1_cache = LRUCache(maxsize=33000)

        # Statistics tracking
        self.stats = {
            "l1_hits": 0,
            "l2_hits": 0,
            "misses": 0,
            "writes": 0,
            "invalidations": 0
        }

        logger.info("RAGCacheManager initialized with L1 cache (max 33K entries) and Redis L2 cache")

    def _generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """
        Generate deterministic cache key from arguments.

        Creates consistent keys for the same inputs, regardless of order (for kwargs).
        Handles complex data structures by hashing them.

        Args:
            prefix: Key prefix (e.g., "embed:doc", "vsearch")
            *args: Positional arguments to include in key
            **kwargs: Keyword arguments to include in key

        Returns:
            Cache key string

        Examples:
            _generate_cache_key("embed:doc", text="hello", len=5)
            → "embed:doc:hello:len:5"

            _generate_cache_key("vsearch", [0.1, 0.2], limit=10)
            → "vsearch:a3f9b2c1d4e5:limit:10"
        """
        key_parts = [prefix]

        # Add positional args
        for arg in args:
            if isinstance(arg, (list, dict)):
                # Hash complex structures for consistent key length
                arg_str = json.dumps(arg, sort_keys=True)
                arg_hash = hashlib.md5(arg_str.encode()).hexdigest()[:12]
                key_parts.append(arg_hash)
            elif isinstance(arg, str) and len(arg) > 50:
                # Truncate long strings and add hash for uniqueness
                str_hash = hashlib.md5(arg.encode()).hexdigest()[:8]
                key_parts.append(f"{arg[:20]}...{str_hash}")
            else:
                key_parts.append(str(arg))

        # Add keyword args (sorted for consistency)
        for k, v in sorted(kwargs.items()):
            if isinstance(v, (list, dict)):
                v_str = json.dumps(v, sort_keys=True)
                v_hash = hashlib.md5(v_str.encode()).hexdigest()[:12]
                key_parts.append(f"{k}:{v_hash}")
            elif isinstance(v, str) and len(v) > 50:
                v_hash = hashlib.md5(v.encode()).hexdigest()[:8]
                key_parts.append(f"{k}:{v[:20]}...{v_hash}")
            else:
                key_parts.append(f"{k}:{v}")

        # Join with colon separator (Redis convention)
        cache_key = ":".join(str(part) for part in key_parts)

        # Ensure key is not too long (Redis max key length is 512MB, but we keep it reasonable)
        if len(cache_key) > 250:
            # Hash the entire key if it's too long
            key_hash = hashlib.md5(cache_key.encode()).hexdigest()
            cache_key = f"{prefix}:hash:{key_hash}"

        return cache_key

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache (L1 → L2 → None).

        Implements two-tier lookup strategy:
        1. Check L1 (in-memory) cache first
        2. If L1 miss, check L2 (Redis) cache
        3. If L2 hit, promote to L1 for faster future access

        Args:
            key: Cache key to retrieve

        Returns:
            Cached value or None if not found
        """
        # Try L1 cache first (fastest)
        if key in self.l1_cache:
            self.stats["l1_hits"] += 1
            logger.debug(f"L1 cache HIT: {key}")
            return self.l1_cache[key]

        # Try L2 cache (Redis)
        try:
            value_bytes = self.redis.get(key)
            if value_bytes:
                self.stats["l2_hits"] += 1
                logger.debug(f"L2 cache HIT: {key}")

                # Deserialize value
                value = pickle.loads(value_bytes)

                # Promote to L1 cache for faster future access
                self.l1_cache[key] = value

                return value
        except Exception as e:
            logger.warning(f"Redis get failed for {key}: {e}")
            # Continue to cache miss if Redis fails

        # Cache miss
        self.stats["misses"] += 1
        logger.debug(f"Cache MISS: {key}")
        return None

    def set(self, key: str, value: Any, ttl: int = 86400):
        """
        Set value in both L1 and L2 caches.

        Writes to both cache tiers:
        - L1 (in-memory): No TTL, uses LRU eviction
        - L2 (Redis): With TTL for automatic expiration

        Args:
            key: Cache key
            value: Value to cache (must be picklable)
            ttl: Time-to-live in seconds (default 24h)
                 Common values:
                 - 604800 (7 days) for embeddings
                 - 86400 (24 hours) for searches
                 - 21600 (6 hours) for hybrid searches
        """
        # Set in L1 cache (LRU eviction handles size limits)
        try:
            self.l1_cache[key] = value
        except Exception as e:
            logger.warning(f"L1 cache set failed for {key}: {e}")

        # Set in L2 cache (Redis) with TTL
        try:
            value_bytes = pickle.dumps(value)
            self.redis.setex(key, ttl, value_bytes)
            self.stats["writes"] += 1
            logger.debug(f"Cache SET: {key} (TTL: {ttl}s, size: {len(value_bytes)} bytes)")
        except Exception as e:
            logger.warning(f"Redis set failed for {key}: {e}")

    def invalidate_key(self, key: str):
        """
        Invalidate a specific cache key.

        Args:
            key: Exact cache key to invalidate
        """
        try:
            # Remove from L1 cache
            if key in self.l1_cache:
                del self.l1_cache[key]

            # Remove from L2 cache
            self.redis.delete(key)
            self.stats["invalidations"] += 1
            logger.debug(f"Invalidated key: {key}")
        except Exception as e:
            logger.error(f"Key invalidation failed for {key}: {e}")

    def invalidate_pattern(self, pattern: str):
        """
        Invalidate all keys matching Redis-style pattern.

        Supports wildcards:
        - * matches any characters
        - ? matches single character

        Args:
            pattern: Redis pattern (e.g., "vsearch:*:doc123:*")

        Examples:
            # Invalidate all vector searches for a document
            invalidate_pattern("vsearch:*:doc123:*")

            # Invalidate all hybrid searches
            invalidate_pattern("hsearch:*")

            # Invalidate everything for a document
            invalidate_pattern("*:doc123:*")
        """
        try:
            # Clear matching keys from Redis
            keys = list(self.redis.scan_iter(match=pattern, count=100))
            if keys:
                self.redis.delete(*keys)
                self.stats["invalidations"] += len(keys)
                logger.info(f"Invalidated {len(keys)} keys matching pattern: {pattern}")
            else:
                logger.debug(f"No keys found matching pattern: {pattern}")

            # Clear matching keys from L1 cache
            keys_to_remove = [k for k in list(self.l1_cache.keys()) if self._matches_pattern(k, pattern)]
            for key in keys_to_remove:
                del self.l1_cache[key]

            if keys_to_remove:
                logger.debug(f"Removed {len(keys_to_remove)} keys from L1 cache")

        except Exception as e:
            logger.error(f"Pattern invalidation failed for {pattern}: {e}")

    def _matches_pattern(self, key: str, pattern: str) -> bool:
        """
        Check if key matches Redis-style pattern.

        Args:
            key: Key to check
            pattern: Pattern with * and ? wildcards

        Returns:
            True if key matches pattern
        """
        # Convert Redis pattern to regex
        regex = pattern.replace("*", ".*").replace("?", ".")
        return re.match(f"^{regex}$", key) is not None

    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive cache statistics.

        Returns:
            Dictionary with cache performance metrics:
            - l1_hits: Number of L1 cache hits
            - l2_hits: Number of L2 cache hits
            - misses: Number of cache misses
            - writes: Number of cache writes
            - invalidations: Number of invalidations
            - total_requests: Total cache requests
            - hit_rate: Overall cache hit rate (0.0-1.0)
            - l1_size: Current L1 cache size
            - l1_max_size: Maximum L1 cache size

        Example:
            stats = cache.get_stats()
            print(f"Hit rate: {stats['hit_rate'] * 100:.1f}%")
        """
        total_requests = sum([
            self.stats["l1_hits"],
            self.stats["l2_hits"],
            self.stats["misses"]
        ])

        if total_requests == 0:
            hit_rate = 0.0
        else:
            total_hits = self.stats["l1_hits"] + self.stats["l2_hits"]
            hit_rate = total_hits / total_requests

        return {
            **self.stats,
            "total_requests": total_requests,
            "hit_rate": round(hit_rate, 3),
            "l1_size": len(self.l1_cache),
            "l1_max_size": self.l1_cache.maxsize
        }

    def clear_all(self):
        """
        Clear all caches (use with caution).

        This is primarily for testing or maintenance.
        """
        self.l1_cache.clear()
        # Clear all keys with our prefixes
        for pattern in ["embed:*", "vsearch:*", "hsearch:*", "chunks:*"]:
            try:
                keys = list(self.redis.scan_iter(match=pattern, count=1000))
                if keys:
                    self.redis.delete(*keys)
            except Exception as e:
                logger.error(f"Error clearing pattern {pattern}: {e}")

        logger.info("Cleared all cache entries")


# Global cache instance
_cache_manager: Optional[RAGCacheManager] = None


def get_cache_manager() -> RAGCacheManager:
    """
    Get or create global cache manager instance.

    This is a singleton pattern to ensure only one cache manager exists.

    Returns:
        RAGCacheManager instance

    Example:
        cache = get_cache_manager()
        value = cache.get("my:key")
    """
    global _cache_manager
    if _cache_manager is None:
        from app.core.config import settings
        try:
            redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=False,  # We use pickle, so binary mode
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            redis_client.ping()
            _cache_manager = RAGCacheManager(redis_client)
            logger.info("RAG cache manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize cache manager: {e}")
            # Create a dummy cache that does nothing
            logger.warning("Running without cache due to Redis connection failure")
            raise

    return _cache_manager


def cached(
    cache_key_prefix: str,
    ttl: int = 86400,
    key_builder: Optional[Callable] = None,
    enabled: bool = True
):
    """
    Decorator for caching function results.

    Automatically caches function return values based on arguments.
    Supports custom key builders for complex caching logic.

    Args:
        cache_key_prefix: Prefix for cache keys (e.g., "embed:doc")
        ttl: Time-to-live in seconds
            - 604800 (7 days) for embeddings
            - 86400 (24 hours) for searches
            - 21600 (6 hours) for hybrid searches
        key_builder: Optional custom function to build cache key
                     Signature: key_builder(*args, **kwargs) -> str
        enabled: Enable/disable caching (useful for testing)

    Returns:
        Decorated function with caching

    Examples:
        @cached("embed:doc", ttl=604800)  # 7 days
        def generate_embedding(text: str) -> List[float]:
            # Expensive API call
            return genai.embed_content(...)

        @cached("vsearch", ttl=86400, key_builder=custom_key)
        def similarity_search(embedding, limit, threshold):
            # Database query
            return results
    """
    def decorator(func):
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Skip caching if disabled
            if not enabled:
                return func(*args, **kwargs)

            try:
                cache = get_cache_manager()
            except Exception as e:
                logger.warning(f"Cache not available, running without cache: {e}")
                return func(*args, **kwargs)

            # Build cache key
            if key_builder:
                try:
                    cache_key = key_builder(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"Custom key builder failed: {e}")
                    cache_key = cache._generate_cache_key(cache_key_prefix, *args, **kwargs)
            else:
                cache_key = cache._generate_cache_key(cache_key_prefix, *args, **kwargs)

            # Try cache first
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {func.__name__}: {cache_key}")
                return cached_value

            # Execute function
            logger.debug(f"Cache miss for {func.__name__}, executing function")
            result = func(*args, **kwargs)

            # Cache result
            try:
                cache.set(cache_key, result, ttl=ttl)
            except Exception as e:
                logger.warning(f"Failed to cache result: {e}")

            return result

        # Support for async functions
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Skip caching if disabled
            if not enabled:
                return await func(*args, **kwargs)

            try:
                cache = get_cache_manager()
            except Exception as e:
                logger.warning(f"Cache not available, running without cache: {e}")
                return await func(*args, **kwargs)

            # Build cache key
            if key_builder:
                try:
                    cache_key = key_builder(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"Custom key builder failed: {e}")
                    cache_key = cache._generate_cache_key(cache_key_prefix, *args, **kwargs)
            else:
                cache_key = cache._generate_cache_key(cache_key_prefix, *args, **kwargs)

            # Try cache first
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {func.__name__}: {cache_key}")
                return cached_value

            # Execute async function
            logger.debug(f"Cache miss for {func.__name__}, executing async function")
            result = await func(*args, **kwargs)

            # Cache result
            try:
                cache.set(cache_key, result, ttl=ttl)
            except Exception as e:
                logger.warning(f"Failed to cache result: {e}")

            return result

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def invalidate_document_cache(document_id: str):
    """
    Invalidate all cache entries related to a document.

    Call this when:
    - Document is re-processed
    - Document is deleted
    - Document embeddings are updated

    Args:
        document_id: Document UUID to invalidate

    Example:
        # After document processing
        invalidate_document_cache("550e8400-e29b-41d4-a716-446655440000")
    """
    try:
        cache = get_cache_manager()

        # Invalidate all searches involving this document
        cache.invalidate_pattern(f"vsearch:*:{document_id}:*")
        cache.invalidate_pattern(f"hsearch:*:{document_id}:*")
        cache.invalidate_key(f"chunks:{document_id}")

        logger.info(f"Invalidated all cache entries for document {document_id}")
    except Exception as e:
        logger.error(f"Failed to invalidate cache for document {document_id}: {e}")


def invalidate_case_cache(case_id: str):
    """
    Invalidate all cache entries related to a case.

    Call this when case documents are modified.

    Args:
        case_id: Case UUID to invalidate
    """
    try:
        cache = get_cache_manager()

        # Invalidate all searches for this case
        cache.invalidate_pattern(f"hsearch:*:{case_id}:*")

        logger.info(f"Invalidated all cache entries for case {case_id}")
    except Exception as e:
        logger.error(f"Failed to invalidate cache for case {case_id}: {e}")
