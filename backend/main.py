"""
FastAPI application entry point.

This is the main entry point for the FastAPI application that:
- Initializes application state
- Creates the configured FastAPI app
- Sets up global state for routes
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from fastapi import FastAPI
from langchain_core.language_models import BaseLanguageModel

from .core.app_factory import create_app
from .core.app_initializer_v2 import initialize_app_state
from .core.config import AppConfig
from .core.followup_service_optimized import OptimizedFollowUpService
from .core.query_logger import get_query_logger
from .core.query_router import QueryRouter
from .core.response_service import ResponseService
from .core.smart_illustration_service import SmartIllustrationService

project_root = Path(__file__).resolve().parent.parent

load_dotenv(project_root / ".env")

logging.basicConfig(
    level=getattr(logging, AppConfig.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
# Initialize application state
retrievers: Optional[Dict[str, Any]] = None
illustration_service: Optional[SmartIllustrationService] = None
llm: Optional[BaseLanguageModel] = None
try:
    retrievers, illustration_service, llm = initialize_app_state()
    app_initialized = True
except Exception as e:
    logger.critical(f"Application startup failed: {e}", exc_info=True)
    retrievers = None
    illustration_service = None
    llm = None
    app_initialized = False

# Initialize singleton services
query_router = QueryRouter()
response_service = ResponseService()


# Create follow-up service based on configuration
def create_followup_service():
    followup_mode = AppConfig.get_followup_mode()

    if followup_mode == "static":
        from .core.followup_service import FollowUpService

        return FollowUpService()
    elif followup_mode == "pre_generated":
        from .core.followup_service_pregenerated import PreGeneratedFollowUpService

        return PreGeneratedFollowUpService()
    elif followup_mode == "optimized":
        if llm and retrievers:
            from .core.app_initializer_v2 import get_unified_retriever

            unified_retriever = get_unified_retriever(retrievers)
            if unified_retriever:
                return OptimizedFollowUpService(
                    llm=llm,
                    unified_retriever=unified_retriever,
                    llm_timeout=3.0,  # Quick timeout to maintain responsiveness
                    use_llm_enhancement=AppConfig.FOLLOWUP_USE_LLM_ENHANCEMENT,
                )
        # Fallback to pre-generated if initialization fails
        logger.warning(
            "Optimized followup mode requested but LLM/retrievers not available, falling back to pre-generated"
        )
        from .core.followup_service_pregenerated import PreGeneratedFollowUpService

        return PreGeneratedFollowUpService()
    else:
        logger.error(f"Unknown followup mode: {followup_mode}, defaulting to pre-generated")
        from .core.followup_service_pregenerated import PreGeneratedFollowUpService

        return PreGeneratedFollowUpService()


followup_service = create_followup_service()

query_logger = get_query_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup: Store state in app.state for dependency injection
    app.state.app_initialized = app_initialized
    app.state.retrievers = retrievers
    app.state.illustration_service = illustration_service
    app.state.llm = llm
    app.state.query_router = query_router
    app.state.response_service = response_service
    app.state.followup_service = followup_service
    app.state.query_logger = query_logger

    yield

    # Shutdown: Ensure graceful shutdown of background resources (e.g., thread pools)
    svc = app.state.followup_service
    if hasattr(svc, "close"):
        try:
            svc.close()
        except Exception:
            logger.exception("Failed to close follow-up service cleanly")


# Create the FastAPI app with lifespan context manager
app = create_app(lifespan=lifespan)

# Ensure app.state has expected attributes for tests that patch them
# These are set definitively during lifespan startup, but we predefine them here
# so patch.object(app.state, ...) works even before startup runs.
if not hasattr(app.state, "retrievers"):
    app.state.retrievers = None  # type: ignore[attr-defined]
if not hasattr(app.state, "illustration_service"):
    app.state.illustration_service = None  # type: ignore[attr-defined]
if not hasattr(app.state, "response_service"):
    app.state.response_service = None  # type: ignore[attr-defined]
if not hasattr(app.state, "followup_service"):
    app.state.followup_service = None  # type: ignore[attr-defined]
if not hasattr(app.state, "llm"):
    app.state.llm = None  # type: ignore[attr-defined]
