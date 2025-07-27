"""
Health check endpoints for monitoring application status.

This module contains health-related endpoints:
- Root endpoint for basic status
- Status endpoint with detailed information
- Health check endpoint with service validation
"""

import time

from fastapi import APIRouter, Depends

from ..core.config import AppConfig
from ..dependencies import get_app_state

router = APIRouter()


@router.get("/")
async def root(state: dict = Depends(get_app_state)):
    return {"status": "healthy" if state["app_initialized"] else "degraded"}


@router.get("/status")
async def status(state: dict = Depends(get_app_state)):
    """Simple status check."""
    return {
        "status": "online",
        "timestamp": time.time(),
        "primary_llm": AppConfig.PRIMARY_LLM,
        "app_initialized": state["app_initialized"],
    }


@router.get("/health")
async def health_check(state: dict = Depends(get_app_state)):
    count = state["illustration_service"].get_all() if state["illustration_service"] else []
    return {
        "status": "healthy" if state["app_initialized"] else "degraded",
        "illustration_count": len(count),
    }
