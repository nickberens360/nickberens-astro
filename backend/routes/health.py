"""
Health check endpoints for monitoring application status.

This module contains health-related endpoints:
- Root endpoint for basic status
- Status endpoint with detailed information
- Health check endpoint with service validation
- Rate limits endpoint for LLM status monitoring
"""

import time

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from ..core.config import AppConfig
from ..dependencies import get_app_state

router = APIRouter()


@router.get("/")
async def root(state: dict = Depends(get_app_state)):
    return {"status": "healthy" if state["app_initialized"] else "degraded"}


@router.get("/status")
async def status(state: dict = Depends(get_app_state)):
    """Status check with rate limit information."""
    try:
        # Import here to avoid circular imports
        from ..core.llm_chain import get_rate_limit_status

        rate_limits = get_rate_limit_status()
    except Exception as e:
        # Fallback if rate limit checking fails
        rate_limits = {"claude": False, "gemini": False}
        print(f"Error getting rate limits: {e}")

    return {
        "status": "online",
        "timestamp": time.time(),
        "primary_llm": AppConfig.PRIMARY_LLM,
        "app_initialized": state["app_initialized"],
        "rate_limits": rate_limits,
    }


@router.get("/health")
async def health_check(state: dict = Depends(get_app_state)):
    count = state["illustration_service"].get_all() if state["illustration_service"] else []
    return {
        "status": "healthy" if state["app_initialized"] else "degraded",
        "illustration_count": len(count),
    }


@router.get("/rate-limits")
async def get_rate_limits():
    """Get current rate limit status for all LLM providers."""
    try:
        # Import here to avoid circular imports
        from ..core.llm_chain import get_rate_limit_status

        rate_limits = get_rate_limit_status()

        return JSONResponse(content={"rate_limits": rate_limits})
    except Exception as e:
        print(f"Error getting rate limits: {e}")
        return JSONResponse(
            content={"error": "Failed to get rate limit status", "rate_limits": {"claude": False, "gemini": False}},
            status_code=500,
        )
