"""
FastAPI application entry point.

This is the main entry point for the FastAPI application that:
- Initializes application state
- Creates the configured FastAPI app
- Sets up global state for routes
"""

import logging

from dotenv import load_dotenv


from .core.app_factory import create_app
from .core.app_initializer import initialize_app_state
from .core.config import AppConfig
from .core.followup_service import FollowUpService
from .core.query_router import QueryRouter
from .core.response_service import ResponseService

load_dotenv(dotenv_path="../.env")

logging.basicConfig(
    level=getattr(logging, AppConfig.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize application state
try:
    retrievers, illustration_service = initialize_app_state()
    app_initialized = True
except Exception as e:
    logger.critical(f"Application startup failed: {e}", exc_info=True)
    retrievers, illustration_service = None, None
    app_initialized = False

# Initialize singleton services
query_router = QueryRouter()
response_service = ResponseService()
followup_service = FollowUpService()

# Create the FastAPI app
app = create_app()

# Store state in app.state for dependency injection
app.state.app_initialized = app_initialized
app.state.retrievers = retrievers
app.state.illustration_service = illustration_service
app.state.query_router = query_router
app.state.response_service = response_service
app.state.followup_service = followup_service
