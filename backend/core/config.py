import os
import logging
from typing import List

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AppConfig:
    """Centralized configuration management."""

    # LLM Configuration
    PRIMARY_LLM = os.getenv("PRIMARY_LLM", "claude")
    CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    # Search Configuration
    try:
        SEARCH_THRESHOLD = int(os.getenv("SEARCH_THRESHOLD", "55"))
    except ValueError:
        logger.error("Invalid SEARCH_THRESHOLD value. Using default value of 55.")
        SEARCH_THRESHOLD = 55

    try:
        MAX_RESULTS = int(os.getenv("MAX_RESULTS", "15"))
    except ValueError:
        logger.error("Invalid MAX_RESULTS value. Using default value of 15.")
        MAX_RESULTS = 15

    ILLUSTRATIONS_PATH = os.getenv("ILLUSTRATIONS_PATH", "public/illustrations.json")

    # Server Configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    HOST = os.getenv("HOST", "0.0.0.0")
    try:
        PORT = int(os.getenv("PORT", "8000"))
    except ValueError:
        logger.error("Invalid PORT value. Using default value of 8000.")
        PORT = 8000

    # CORS Configuration
    @staticmethod
    def get_cors_origins() -> List[str]:
        """Get CORS origins from environment with sensible defaults."""
        env_origins = os.getenv("CORS_ORIGINS")
        if env_origins:
            return [origin.strip() for origin in env_origins.split(",")]

        default_origins = [
            "http://localhost:4321",
            "http://localhost:3000",
            "http://localhost:5173",
            "https://nickberens.me",
            "https://www.nickberens.me",
            "https://nickberens360.netlify.app",
            "https://deploy-preview-14--nickberens360.netlify.app",
            "https://nickberens-astro.onrender.com",
            "https://*.netlify.app",
            "https://*.onrender.com",
        ]

        return default_origins

    # Rate Limiting
    RATE_LIMIT = os.getenv("RATE_LIMIT", "5/minute")

    # App Metadata
    APP_TITLE = "Nick Berens Portfolio API"
    APP_DESCRIPTION = "API for AI-powered responses and illustration search with Claude as primary LLM"
    APP_VERSION = "2.0.0"
