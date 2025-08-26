"""
Main FastAPI application for the RAG admin dashboard backend.
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .routes import router as admin_router


def create_admin_app() -> FastAPI:
    """Create and configure the admin FastAPI application."""
    app = FastAPI(
        title="RAG Admin Dashboard API",
        description="Admin API for monitoring and analyzing the RAG portfolio chatbot system",
        version="1.0.0",
    )

    # CORS middleware to allow frontend access
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv(
            "ADMIN_ALLOWED_ORIGINS",
            "http://localhost:3000,http://localhost:3002,http://localhost:4321,http://localhost:4323",
        ).split(","),
        allow_credentials=True,  # now using session cookies
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routes
    app.include_router(admin_router)

    # Serve static files (for the built frontend)
    frontend_build_path = os.path.join(os.path.dirname(__file__), "../frontend/dist")
    if os.path.exists(frontend_build_path):
        # Mount assets directory for JS, CSS, and other static files
        assets_path = os.path.join(frontend_build_path, "assets")
        if os.path.exists(assets_path):
            app.mount("/assets", StaticFiles(directory=assets_path), name="assets")

        # Mount the entire dist directory as a fallback for other static files
        app.mount("/admin/static", StaticFiles(directory=frontend_build_path), name="static")

        # Serve individual static files (like vite.svg)
        @app.get("/vite.svg")
        async def serve_vite_svg():
            """Serve vite.svg."""
            vite_svg_path = os.path.join(frontend_build_path, "vite.svg")
            if os.path.isfile(vite_svg_path):
                return FileResponse(vite_svg_path)
            return FileResponse(os.path.join(frontend_build_path, "index.html"))

        @app.get("/admin/{path:path}")
        async def serve_frontend(path: str):
            """Serve the frontend application."""
            file_path = os.path.join(frontend_build_path, path)
            if os.path.isfile(file_path):
                return FileResponse(file_path)
            # For SPA routing, return index.html for non-API routes
            return FileResponse(os.path.join(frontend_build_path, "index.html"))

        @app.get("/admin")
        async def serve_admin_root():
            """Serve the admin dashboard root."""
            return FileResponse(os.path.join(frontend_build_path, "index.html"))

        @app.get("/login")
        async def serve_login():
            """Serve the login page."""
            return FileResponse(os.path.join(frontend_build_path, "index.html"))

    return app


# Create the app instance
app = create_admin_app()


if __name__ == "__main__":
    import uvicorn

    # Get port from environment or use default
    port = int(os.getenv("ADMIN_PORT", 8001))

    print(f"Starting RAG Admin Dashboard on port {port}")
    print(f"Admin API docs available at: http://localhost:{port}/docs")
    print(f"Admin Dashboard available at: http://localhost:{port}/admin")

    uvicorn.run("admin.backend.main:app", host="0.0.0.0", port=port, reload=True)
