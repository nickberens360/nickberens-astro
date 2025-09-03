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
    # Create FastAPI app with enhanced metadata and documentation
    app = FastAPI(
        title=AppConfig.APP_TITLE,
        description=AppConfig.APP_DESCRIPTION,
        version=AppConfig.APP_VERSION,
        lifespan=lifespan,
        contact={
            "name": "Nick Berens",
            "url": "https://nickberens.me",
            "email": "hello@nickberens.me",
        },
        license_info={
            "name": "MIT",
        },
        tags_metadata=[
            {
                "name": "Health",
                "description": "System health and status endpoints",
            },
            {
                "name": "Query",
                "description": "AI-powered query endpoints for retrieving information from Nick's knowledge base. Uses Claude and advanced RAG (Retrieval-Augmented Generation) to provide intelligent responses.",
            },
            {
                "name": "Public API",
                "description": "Public endpoints for accessing content, performance metrics, and analytics. No authentication required.",
            },
            {
                "name": "Admin Authentication",
                "description": "Admin login, logout, and user management endpoints. **Authentication required** for all admin operations.",
            },
            {
                "name": "Admin Management",
                "description": "Administrative endpoints for system management, monitoring, and configuration. **Admin authentication required**.",
            },
            {
                "name": "Admin Analytics",
                "description": "Query analytics, performance metrics, and system insights for administrators. **Admin access required**.",
            },
        ],
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
        knowledge_public,
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
    app.include_router(knowledge_public.router, prefix="/api/public")

    # Admin API routes - consolidated under /api/admin
    app.include_router(admin.router, prefix="/api/admin")
    app.include_router(query_logs.router, prefix="/api/admin")
    app.include_router(admin_refresh.router, prefix="/api/admin")
    app.include_router(queries.router, prefix="/api/admin")
    app.include_router(knowledge.router, prefix="/api/admin")  # Admin operations (read + write)

    # Serve admin frontend static files (mount after API routes to avoid conflicts)
    admin_static_path = Path(__file__).parent.parent.parent / "admin" / "frontend" / "dist"
    if admin_static_path.exists():

        # Mount static assets first (more specific route)
        app.mount("/assets", StaticFiles(directory=str(admin_static_path / "assets")), name="admin_assets")

        # Custom admin SPA handler that properly serves index.html for all admin routes
        class SPAStaticFiles(StaticFiles):
            async def get_response(self, path: str, scope):
                try:
                    return await super().get_response(path, scope)
                except Exception:
                    # If the path doesn't exist, serve index.html for client-side routing
                    return await super().get_response("index.html", scope)

        # Mount admin frontend with custom SPA handler
        app.mount("/admin", SPAStaticFiles(directory=str(admin_static_path), html=True), name="admin_frontend")

    return app
