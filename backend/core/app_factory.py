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
from .settings_manager import get_settings_manager


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


# Check if we're in testing environment to disable rate limiting
import os

_is_testing = os.getenv("TESTING", "false").lower() == "true" or "pytest" in os.environ.get("_", "")

# Create limiter - use dummy storage during testing to effectively disable rate limiting
if _is_testing:
    from slowapi.util import get_remote_address

    limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
else:
    limiter = Limiter(key_func=_safe_key_func)


async def maintenance_mode_middleware(request: Request, call_next):
    """Middleware to check for maintenance mode feature flag."""
    try:
        settings_manager = get_settings_manager()
        if settings_manager.is_feature_enabled("enable_maintenance_mode"):
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=503,
                content={
                    "detail": "System is under maintenance. Please try again later.",
                    "message": "We're performing scheduled maintenance to improve your experience.",
                },
            )
    except Exception as e:
        # If feature flag check fails, log but continue normally
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to check maintenance mode feature flag: {e}")

    return await call_next(request)


async def dynamic_rate_limit_middleware(request: Request, call_next):
    """Middleware to apply dynamic rate limiting based on security settings."""
    # Skip rate limiting during testing
    if _is_testing:
        return await call_next(request)

    # Skip rate limiting for admin routes except login endpoint - they have session-based auth protection
    if (
        request.url.path.startswith("/admin/") or request.url.path.startswith("/api/admin/")
    ) and request.url.path != "/api/admin/auth/login":
        return await call_next(request)

    try:
        settings_manager = get_settings_manager()
        security_settings = settings_manager.get_security_settings()

        if not security_settings.enable_rate_limiting:
            # Rate limiting disabled, skip
            return await call_next(request)

        # Get client IP for rate limiting
        client_ip = _safe_key_func(request)

        # Create a simple in-memory rate limiter check
        # This is a basic implementation - in production you'd want Redis or similar
        import time

        # Check if we have a rate limit store in app state
        if not hasattr(request.app.state, "rate_limit_store"):
            request.app.state.rate_limit_store = {}

        store = request.app.state.rate_limit_store
        current_time = time.time()
        window_start = current_time - security_settings.rate_limit_window

        # Clean old entries
        store[client_ip] = [req_time for req_time in store.get(client_ip, []) if req_time > window_start]

        # Check if rate limit exceeded
        if len(store[client_ip]) >= security_settings.rate_limit_requests:
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Please try again later.",
                    "retry_after": security_settings.rate_limit_window,
                },
            )

        # Add current request to store
        store[client_ip].append(current_time)

    except Exception as e:
        # If rate limit check fails, log but continue normally
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to apply dynamic rate limiting: {e}")

    return await call_next(request)


def configure_cors(app: FastAPI):
    """Configure CORS with hardcoded origins from AppConfig."""
    # Always use hardcoded CORS origins from AppConfig
    app.add_middleware(
        CORSMiddleware,
        allow_origins=AppConfig.get_cors_origins(),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type"],
        expose_headers=["X-Model-Used", "X-Followup-Questions"],
    )


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

    # Add maintenance mode middleware
    app.middleware("http")(maintenance_mode_middleware)

    # Add dynamic rate limiting middleware
    app.middleware("http")(dynamic_rate_limit_middleware)

    # Add CORS middleware with hardcoded configuration
    configure_cors(app)

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
