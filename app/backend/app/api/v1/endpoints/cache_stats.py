"""
Cache statistics and management endpoints.

Provides monitoring and control over the RAG pipeline caching system.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging

from app.utils.rag_cache import (
    get_cache_manager,
    invalidate_document_cache,
    invalidate_case_cache
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/stats")
async def get_cache_statistics():
    """
    Get comprehensive RAG cache statistics.

    Returns cache performance metrics including:
    - Hit rates (L1 and L2)
    - Cache sizes
    - Performance impact estimates

    Returns:
        Dictionary with cache statistics and performance metrics

    Example response:
        {
            "l1_cache": {
                "hits": 1250,
                "size": 8432,
                "max_size": 33000,
                "utilization": "25.6%"
            },
            "l2_cache": {
                "hits": 3421
            },
            "overall": {
                "total_requests": 5987,
                "cache_misses": 1316,
                "hit_rate": "78.0%",
                "writes": 1316
            },
            "performance_impact": {
                "estimated_time_saved_seconds": 242.65,
                "estimated_api_calls_saved": 4671,
                "estimated_cost_saved_usd": 0.47
            }
        }
    """
    try:
        cache = get_cache_manager()
        stats = cache.get_stats()

        # Calculate utilization
        l1_utilization = (stats["l1_size"] / stats["l1_max_size"]) * 100 if stats["l1_max_size"] > 0 else 0

        # Calculate performance impact
        # L1 hit saves ~148ms (150ms API call - 2ms cache)
        # L2 hit saves ~145ms (150ms API call - 5ms cache)
        time_saved_l1 = stats["l1_hits"] * 0.148
        time_saved_l2 = stats["l2_hits"] * 0.145
        total_time_saved = time_saved_l1 + time_saved_l2

        # Estimate API calls saved (1 embedding = 1 API call)
        api_calls_saved = stats["l1_hits"] + stats["l2_hits"]

        # Estimate cost saved (Gemini embedding: ~$0.0001 per call)
        cost_saved = api_calls_saved * 0.0001

        return {
            "l1_cache": {
                "hits": stats["l1_hits"],
                "size": stats["l1_size"],
                "max_size": stats["l1_max_size"],
                "utilization": f"{l1_utilization:.1f}%"
            },
            "l2_cache": {
                "hits": stats["l2_hits"]
            },
            "overall": {
                "total_requests": stats["total_requests"],
                "cache_misses": stats["misses"],
                "hit_rate": f"{stats['hit_rate'] * 100:.1f}%",
                "writes": stats["writes"],
                "invalidations": stats["invalidations"]
            },
            "performance_impact": {
                "estimated_time_saved_seconds": round(total_time_saved, 2),
                "estimated_time_saved_minutes": round(total_time_saved / 60, 2),
                "estimated_api_calls_saved": api_calls_saved,
                "estimated_cost_saved_usd": round(cost_saved, 2)
            },
            "status": "healthy"
        }

    except Exception as e:
        logger.error(f"Error retrieving cache statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve cache statistics: {str(e)}")


@router.get("/health")
async def check_cache_health():
    """
    Check cache system health.

    Verifies that both L1 and L2 caches are operational.

    Returns:
        Health status with cache availability

    Example response:
        {
            "status": "healthy",
            "l1_cache": "operational",
            "l2_cache": "operational",
            "message": "All cache systems operational"
        }
    """
    try:
        cache = get_cache_manager()

        # Test L1 cache
        l1_status = "operational" if cache.l1_cache is not None else "unavailable"

        # Test L2 cache (Redis)
        l2_status = "unavailable"
        try:
            cache.redis.ping()
            l2_status = "operational"
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")

        # Overall status
        if l1_status == "operational" and l2_status == "operational":
            status = "healthy"
            message = "All cache systems operational"
        elif l1_status == "operational":
            status = "degraded"
            message = "L1 cache operational, L2 cache unavailable"
        else:
            status = "unhealthy"
            message = "Cache systems unavailable"

        return {
            "status": status,
            "l1_cache": l1_status,
            "l2_cache": l2_status,
            "message": message
        }

    except Exception as e:
        logger.error(f"Error checking cache health: {e}")
        return {
            "status": "unhealthy",
            "l1_cache": "unknown",
            "l2_cache": "unknown",
            "message": f"Health check failed: {str(e)}"
        }


@router.post("/invalidate/document/{document_id}")
async def invalidate_document(document_id: str):
    """
    Invalidate all cache entries for a specific document.

    Use this endpoint when:
    - Document is re-processed
    - Document embeddings are updated
    - Document is modified

    Args:
        document_id: UUID of the document to invalidate

    Returns:
        Confirmation of invalidation

    Example:
        POST /api/v1/cache/invalidate/document/550e8400-e29b-41d4-a716-446655440000
    """
    try:
        invalidate_document_cache(document_id)
        logger.info(f"API: Invalidated cache for document {document_id}")

        return {
            "status": "success",
            "message": f"Cache invalidated for document {document_id}",
            "document_id": document_id
        }

    except Exception as e:
        logger.error(f"Error invalidating document cache: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to invalidate document cache: {str(e)}"
        )


@router.post("/invalidate/case/{case_id}")
async def invalidate_case(case_id: str):
    """
    Invalidate all cache entries for a specific case.

    Use this endpoint when case documents are modified.

    Args:
        case_id: UUID of the case to invalidate

    Returns:
        Confirmation of invalidation

    Example:
        POST /api/v1/cache/invalidate/case/550e8400-e29b-41d4-a716-446655440000
    """
    try:
        invalidate_case_cache(case_id)
        logger.info(f"API: Invalidated cache for case {case_id}")

        return {
            "status": "success",
            "message": f"Cache invalidated for case {case_id}",
            "case_id": case_id
        }

    except Exception as e:
        logger.error(f"Error invalidating case cache: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to invalidate case cache: {str(e)}"
        )


@router.post("/invalidate/pattern")
async def invalidate_pattern(
    pattern: str = Query(..., description="Redis-style pattern (e.g., vsearch:*:doc123:*)")
):
    """
    Invalidate cache entries matching a pattern.

    Advanced endpoint for pattern-based cache invalidation.
    Supports Redis-style wildcards (* and ?).

    Args:
        pattern: Redis pattern to match (e.g., "vsearch:*:doc123:*")

    Returns:
        Confirmation with number of invalidated entries

    Example:
        POST /api/v1/cache/invalidate/pattern?pattern=vsearch:*:doc123:*

    Warning:
        Use with caution. Overly broad patterns may invalidate large portions of cache.
    """
    try:
        cache = get_cache_manager()

        # Get count before invalidation
        keys_before = len(list(cache.redis.scan_iter(match=pattern, count=100)))

        cache.invalidate_pattern(pattern)

        logger.info(f"API: Invalidated cache pattern: {pattern} ({keys_before} keys)")

        return {
            "status": "success",
            "message": f"Cache entries matching pattern invalidated",
            "pattern": pattern,
            "keys_invalidated": keys_before
        }

    except Exception as e:
        logger.error(f"Error invalidating cache pattern: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to invalidate cache pattern: {str(e)}"
        )


@router.delete("/clear")
async def clear_cache(
    confirm: bool = Query(False, description="Must be true to clear cache")
):
    """
    Clear all cache entries.

    **WARNING**: This clears the entire cache and should only be used for
    maintenance or testing purposes.

    Args:
        confirm: Must be set to true to confirm cache clearing

    Returns:
        Confirmation of cache clearing

    Example:
        DELETE /api/v1/cache/clear?confirm=true
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Cache clear requires confirmation. Set confirm=true parameter."
        )

    try:
        cache = get_cache_manager()
        cache.clear_all()

        logger.warning("API: CLEARED ALL CACHE ENTRIES")

        return {
            "status": "success",
            "message": "All cache entries cleared",
            "warning": "Cache is now empty. Performance will be degraded until cache is rebuilt."
        }

    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear cache: {str(e)}"
        )


@router.get("/metrics/detailed")
async def get_detailed_metrics():
    """
    Get detailed cache metrics for monitoring and optimization.

    Provides granular statistics for performance tuning and analysis.

    Returns:
        Detailed metrics including hit rates by cache tier

    Example response:
        {
            "cache_tiers": {
                "l1": {
                    "hits": 1250,
                    "hit_rate": "52.3%",
                    "size": 8432,
                    "avg_access_time_ms": 0.8
                },
                "l2": {
                    "hits": 620,
                    "hit_rate": "25.9%",
                    "avg_access_time_ms": 6.2
                },
                "miss": {
                    "count": 520,
                    "rate": "21.8%",
                    "avg_fetch_time_ms": 152.3
                }
            },
            "efficiency": {
                "overall_hit_rate": "78.2%",
                "cache_effectiveness": "high",
                "recommendation": "Cache performing well"
            }
        }
    """
    try:
        cache = get_cache_manager()
        stats = cache.get_stats()

        total_requests = stats["total_requests"]

        # Calculate individual hit rates
        l1_hit_rate = (stats["l1_hits"] / total_requests * 100) if total_requests > 0 else 0
        l2_hit_rate = (stats["l2_hits"] / total_requests * 100) if total_requests > 0 else 0
        miss_rate = (stats["misses"] / total_requests * 100) if total_requests > 0 else 0

        # Determine cache effectiveness
        overall_hit_rate = stats["hit_rate"] * 100
        if overall_hit_rate >= 70:
            effectiveness = "excellent"
            recommendation = "Cache performing optimally"
        elif overall_hit_rate >= 50:
            effectiveness = "good"
            recommendation = "Cache performing well"
        elif overall_hit_rate >= 30:
            effectiveness = "fair"
            recommendation = "Consider increasing TTLs or cache size"
        else:
            effectiveness = "poor"
            recommendation = "Review caching strategy and TTL configuration"

        return {
            "cache_tiers": {
                "l1": {
                    "hits": stats["l1_hits"],
                    "hit_rate": f"{l1_hit_rate:.1f}%",
                    "size": stats["l1_size"],
                    "max_size": stats["l1_max_size"],
                    "avg_access_time_ms": 0.8  # Typical L1 access time
                },
                "l2": {
                    "hits": stats["l2_hits"],
                    "hit_rate": f"{l2_hit_rate:.1f}%",
                    "avg_access_time_ms": 6.2  # Typical Redis access time
                },
                "miss": {
                    "count": stats["misses"],
                    "rate": f"{miss_rate:.1f}%",
                    "avg_fetch_time_ms": 152.3  # Typical API/DB fetch time
                }
            },
            "operations": {
                "writes": stats["writes"],
                "invalidations": stats["invalidations"],
                "total_requests": total_requests
            },
            "efficiency": {
                "overall_hit_rate": f"{overall_hit_rate:.1f}%",
                "cache_effectiveness": effectiveness,
                "recommendation": recommendation
            },
            "timestamp": "current"
        }

    except Exception as e:
        logger.error(f"Error retrieving detailed metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve detailed metrics: {str(e)}"
        )
