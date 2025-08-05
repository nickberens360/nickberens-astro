"""
Cache management endpoints.

This module provides endpoints for managing and monitoring the response cache.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from ..core.cache_preloader import CachePreloader
from ..core.llm_chain import CacheManager
from ..dependencies import get_services

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/cache", tags=["cache"])


@router.get("/status")
async def get_cache_status():
    """Get the current cache status for configured queries."""
    queries = CachePreloader.get_preload_queries()

    cached_queries = 0
    query_statuses = []

    for query in queries:
        cache_key = CacheManager.get_cache_key(query)
        is_cached = bool(cache_key and CacheManager.get_cached_response(cache_key))

        query_statuses.append({"query": query, "cached": is_cached, "cache_key": cache_key})

        if is_cached:
            cached_queries += 1

    status = {"configured_queries": len(queries), "cached_queries": cached_queries, "queries": query_statuses}

    return JSONResponse(content=status)


@router.post("/preload")
async def preload_cache(services: dict = Depends(get_services)):
    """Manually trigger cache pre-loading."""
    retrievers = services.get("retrievers")

    if not retrievers:
        raise HTTPException(status_code=503, detail="Retrievers not available")

    try:
        # Run pre-loading
        await CachePreloader.preload_query_cache(retrievers)

        # Get status after pre-loading
        queries = CachePreloader.get_preload_queries()
        cached_count = 0
        for query in queries:
            cache_key = CacheManager.get_cache_key(query)
            if cache_key and CacheManager.get_cached_response(cache_key):
                cached_count += 1

        return JSONResponse(
            content={
                "message": "Cache pre-loading completed",
                "total_queries": len(queries),
                "cached_queries": cached_count,
            }
        )

    except Exception as e:
        logger.error(f"Cache pre-loading failed: {e}")
        raise HTTPException(status_code=500, detail="Cache pre-loading failed")


@router.delete("/clear")
async def clear_cache():
    """Clear all cached responses."""
    # Import here to avoid circular imports
    from ..core import llm_chain

    # Clear both caches
    cleared_responses = len(llm_chain._response_cache)
    cleared_retrievals = len(llm_chain._retrieval_cache)

    llm_chain._response_cache.clear()
    llm_chain._retrieval_cache.clear()

    return JSONResponse(
        content={
            "message": "Cache cleared",
            "cleared_responses": cleared_responses,
            "cleared_retrievals": cleared_retrievals,
        }
    )


@router.get("/stats")
async def get_cache_stats():
    """Get detailed cache statistics."""
    # Import here to avoid circular imports
    from ..core import llm_chain

    response_cache_keys = list(llm_chain._response_cache.keys())
    retrieval_cache_keys = list(llm_chain._retrieval_cache.keys())

    return JSONResponse(
        content={
            "response_cache": {
                "size": len(response_cache_keys),
                "keys": response_cache_keys[:10],  # Show first 10 keys
            },
            "retrieval_cache": {
                "size": len(retrieval_cache_keys),
                "keys": retrieval_cache_keys[:10],  # Show first 10 keys
            },
            "settings": {
                "enabled": llm_chain.ENABLE_CACHING,
                "ttl_seconds": llm_chain.CACHE_TTL,
                "max_size": llm_chain.MAX_CACHE_SIZE,
            },
        }
    )
