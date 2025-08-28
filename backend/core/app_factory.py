"""
FastAPI application factory for creating and configuring the app instance.

This module handles:
- FastAPI app instantiation with metadata
- CORS middleware configuration
- Rate limiter setup and exception handling
- Router registration
- Security middleware application
"""

from pathlib import Path
from typing import AsyncContextManager, Callable, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request

from .config import AppConfig
from .security_middleware import add_security_middleware


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
    add_security_middleware(app)

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=AppConfig.get_cors_origins(),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type"],
        expose_headers=["X-Model-Used", "X-Followup-Questions"],
    )

    # Register routers - import here to avoid circular imports
    from ..routes import (
        admin,
        admin_refresh,
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

    # Core public routes (no prefix)
    app.include_router(health.router)
    app.include_router(query.router)

    # Public API routes
    app.include_router(smart_query.router, prefix="/api/public")
    app.include_router(content.router, prefix="/api/public")
    app.include_router(stats.router, prefix="/api/public")
    app.include_router(performance.router, prefix="/api/public")
    app.include_router(knowledge.router, prefix="/api/public")

    # Admin API routes - consolidated under /api/admin
    app.include_router(admin.router, prefix="/api/admin")
    app.include_router(query_logs.router, prefix="/api/admin")
    app.include_router(admin_refresh.router, prefix="/api/admin")
    app.include_router(queries.router, prefix="/api/admin")
    app.include_router(knowledge.router, prefix="/api/admin")  # Admin write operations

    # Serve admin frontend static files (mount after API routes to avoid conflicts)
    admin_static_path = Path(__file__).parent.parent.parent / "admin" / "frontend" / "dist"
    if admin_static_path.exists():
        # Mount static files at /admin/dashboard to avoid API route conflicts
        app.mount("/admin/dashboard", StaticFiles(directory=str(admin_static_path), html=True), name="admin_frontend")

    return app
