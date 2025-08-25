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
from starlette.requests import Request

from ..middleware.security import add_security_headers
from .config import AppConfig


# Initialize the limiter - centralized application-wide rate limiting
# Use a test-safe key function that gracefully handles missing client info.
def _safe_key_func(request: Request) -> str:
    try:
        # Prefer Starlette client host if available
        client = getattr(request, "client", None)
        if client and getattr(client, "host", None):
            return client.host
        # Fall back to X-Forwarded-For when behind proxies
        fwd = request.headers.get("x-forwarded-for") if hasattr(request, "headers") else None
        if fwd:
            return fwd.split(",")[0].strip()
    except Exception:
        pass
    # Final fallback for test transports without client info
    return "local-test"


limiter = Limiter(key_func=_safe_key_func)


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
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
        expose_headers=["X-Model-Used", "X-Followup-Questions"],
    )

    # Register routers - import here to avoid circular imports
    from ..routes import (
        admin_refresh,
        auth,
        content,
        health,
        knowledge,
        performance,
        queries,
        query,
        query_logs,
        smart_query,
        stats,
    )

    app.include_router(health.router)
    app.include_router(query.router)
    app.include_router(query_logs.router, prefix="/admin")
    app.include_router(smart_query.router, prefix="/api")
    app.include_router(content.router, prefix="/api")
    app.include_router(knowledge.router)
    app.include_router(knowledge.router, prefix="/admin")  # Also include under /admin for admin dashboard
    app.include_router(admin_refresh.router)
    app.include_router(auth.router, prefix="/admin/api")  # Authentication for admin dashboard

    # Add missing admin API endpoints that the frontend expects
    app.include_router(health.router, prefix="/admin/api")  # For /admin/api/health
    app.include_router(queries.router, prefix="/admin/api")  # For /admin/api/queries
    app.include_router(stats.router, prefix="/admin/api")  # For /admin/api/stats/overview
    app.include_router(performance.router, prefix="/admin/api")  # For /admin/api/performance endpoints

    return app
