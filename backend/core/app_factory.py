"""
FastAPI application factory for creating and configuring the app instance.

This module handles:
- FastAPI app instantiation with metadata
- CORS middleware configuration
- Rate limiter setup and exception handling
- Router registration
- Security middleware application
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from ..middleware.security import add_security_headers
from .config import AppConfig

# Initialize the limiter - centralized application-wide rate limiting
limiter = Limiter(key_func=get_remote_address)


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application instance.

    Returns:
        FastAPI: Configured FastAPI application
    """
    # Create FastAPI app with metadata
    app = FastAPI(
        title=AppConfig.APP_TITLE,
        description=AppConfig.APP_DESCRIPTION,
        version=AppConfig.APP_VERSION,
    )

    # Setup rate limiter - use the centralized limiter instance
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Add security middleware
    app.middleware("http")(add_security_headers)

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=AppConfig.get_cors_origins(),
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
        expose_headers=["X-Model-Used", "X-Followup-Questions"],
    )

    # Register routers - import here to avoid circular imports
    from ..routes import health, query

    app.include_router(health.router)
    app.include_router(query.router)

    return app
