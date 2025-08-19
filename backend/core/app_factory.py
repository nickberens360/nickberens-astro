"""
FastAPI application factory for creating and configuring the app instance.

This module handles:
- FastAPI app instantiation with metadata
- CORS middleware configuration
- Rate limiter setup and exception handling
- Router registration
- Security middleware application
"""

from typing import AsyncContextManager, Callable, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from ..middleware.security import add_security_headers
from .config import AppConfig

# Initialize the limiter - centralized application-wide rate limiting
limiter = Limiter(key_func=get_remote_address)


def create_app(lifespan: Optional[Callable[[FastAPI], AsyncContextManager]] = None) -> FastAPI:
    """
    Create and configure the FastAPI application instance.

    Args:
        lifespan: Optional lifespan context manager for startup/shutdown events

    Returns:
        FastAPI: Configured FastAPI application
    """
    # Create FastAPI app with metadata
    app = FastAPI(
        title=AppConfig.APP_TITLE,
        description=AppConfig.APP_DESCRIPTION,
        version=AppConfig.APP_VERSION,
        lifespan=lifespan,
    )

    # Setup rate limiter - use the centralized limiter instance
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

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
    from ..routes import health, query, query_logs, smart_query

    app.include_router(health.router)
    app.include_router(query.router)
    app.include_router(query_logs.router, prefix="/admin")
    app.include_router(smart_query.router, prefix="/api")

    return app
