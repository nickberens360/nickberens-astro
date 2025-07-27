"""
FastAPI dependencies for accessing application state.

This module provides dependency functions that access application state
stored in app.state, following FastAPI best practices for dependency injection.
"""

from fastapi import Request

from .core.followup_service import FollowUpService
from .core.query_router import QueryRouter
from .core.response_service import ResponseService


def get_app_state(request: Request):
    """
    Dependency to get current app state.

    Args:
        request: FastAPI request object containing app state

    Returns:
        dict: Dictionary containing app initialization status and illustration service
    """
    return {
        "app_initialized": getattr(request.app.state, "app_initialized", False),
        "illustration_service": getattr(request.app.state, "illustration_service", None),
    }


def get_services(request: Request):
    """
    Dependency to get current services state.

    Args:
        request: FastAPI request object containing app state

    Returns:
        dict: Dictionary containing all services needed for query processing
    """
    return {
        "retrievers": getattr(request.app.state, "retrievers", None),
        "illustration_service": getattr(request.app.state, "illustration_service", None),
        "query_router": QueryRouter(),
        "response_service": ResponseService(),
        "followup_service": FollowUpService(),
    }
