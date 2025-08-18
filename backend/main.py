"""
FastAPI application entry point.

This is the main entry point for the FastAPI application that:
- Initializes application state
- Creates the configured FastAPI app
- Sets up global state for routes
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from langchain_core.language_models import BaseLanguageModel

from .core.app_factory import create_app
from .core.app_initializer_v2 import initialize_app_state
from .core.config import AppConfig
from .core.followup_service_pregenerated import PreGeneratedFollowUpService
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

# Always use pre-generated follow-up service (no dynamic generation at request time)
followup_service: PreGeneratedFollowUpService = PreGeneratedFollowUpService()

query_logger = get_query_logger()

# Create the FastAPI app
app = create_app()

# Store state in app.state for dependency injection
app.state.app_initialized = app_initialized
app.state.retrievers = retrievers
app.state.illustration_service = illustration_service
app.state.llm = llm
app.state.query_router = query_router
app.state.response_service = response_service
app.state.followup_service = followup_service
app.state.query_logger = query_logger


# Ensure graceful shutdown of background resources (e.g., thread pools)
@app.on_event("shutdown")
async def _shutdown_cleanup():
    svc = app.state.followup_service
    if hasattr(svc, "close"):
        try:
            svc.close()
        except Exception:
            logger.exception("Failed to close follow-up service cleanly")
