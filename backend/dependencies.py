"""
FastAPI dependencies for accessing application state.

This module provides dependency functions that access application state
stored in app.state, following FastAPI best practices for dependency injection.
"""

from fastapi import Request


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
        "query_router": getattr(request.app.state, "query_router", None),
        "response_service": getattr(request.app.state, "response_service", None),
        "followup_service": getattr(request.app.state, "followup_service", None),
    }
