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
from .routes import health, query

# Load environment variables and setup logging
load_dotenv()
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

# Create the FastAPI app
app = create_app()

# Set global state for routes
health.set_app_state(app_initialized, illustration_service)
query.set_services(retrievers, illustration_service)
