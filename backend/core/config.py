import logging
import os
import re
from typing import List
from urllib.parse import urlparse

# Set up logging
logger = logging.getLogger(__name__)


class AppConfig:
    """Centralized configuration management with enhanced security."""

    # LLM Configuration - keep it simple for now
    PRIMARY_LLM = os.getenv("PRIMARY_LLM", "claude")
    CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/embedding-001")

    # Search Configuration with basic validation
    try:
        SEARCH_THRESHOLD = int(os.getenv("SEARCH_THRESHOLD", "55"))
        if SEARCH_THRESHOLD < 0 or SEARCH_THRESHOLD > 100:
            logger.error("Invalid SEARCH_THRESHOLD value. Using default value of 55.")
            SEARCH_THRESHOLD = 55
    except ValueError:
        logger.error("Invalid SEARCH_THRESHOLD value. Using default value of 55.")
        SEARCH_THRESHOLD = 55

    try:
        MAX_RESULTS = int(os.getenv("MAX_RESULTS", "15"))
        if MAX_RESULTS < 1 or MAX_RESULTS > 100:
            logger.error("Invalid MAX_RESULTS value. Using default value of 15.")
            MAX_RESULTS = 15
    except ValueError:
        logger.error("Invalid MAX_RESULTS value. Using default value of 15.")
        MAX_RESULTS = 15

    ILLUSTRATIONS_PATH = os.getenv("ILLUSTRATIONS_PATH", "public/illustrations.json")

    # Server Configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    HOST = os.getenv("HOST", "0.0.0.0")

    try:
        PORT = int(os.getenv("PORT", "8000"))
        if PORT < 1024 or PORT > 65535:
            logger.error("Invalid PORT value. Using default value of 8000.")
            PORT = 8000
    except ValueError:
        logger.error("Invalid PORT value. Using default value of 8000.")
        PORT = 8000

    # CORS Configuration with enhanced security
    @staticmethod
    def _is_valid_origin(origin: str) -> bool:
        """Validate a single CORS origin URL."""
        if not origin or not isinstance(origin, str):
            return False

        # Allow wildcard only in development
        if origin == "*":
            env = os.getenv("ENVIRONMENT", "development").lower()
            if env in ["development", "dev", "local"]:
                logger.warning("Wildcard CORS origin allowed in development mode")
                return True
            else:
                logger.error("Wildcard CORS origin not allowed in production")
                return False

        # Basic URL validation
        try:
            parsed = urlparse(origin)

            # Must have scheme and netloc
            if not parsed.scheme or not parsed.netloc:
                logger.warning(f"Invalid CORS origin format: {origin}")
                return False

            # Only allow http/https
            if parsed.scheme not in ["http", "https"]:
                logger.warning(f"Invalid CORS origin scheme: {origin}")
                return False

            # Enforce HTTPS for production domains (not localhost)
            netloc_lower = parsed.netloc.lower()
            if not netloc_lower.startswith("localhost") and not netloc_lower.startswith("127.0.0.1"):
                if parsed.scheme != "https":
                    logger.warning(f"Non-HTTPS origin for production domain: {origin}")
                    return False

            # Check domain format - basic validation
            domain_part = parsed.netloc.split(":")[0]  # Remove port
            # More strict domain validation: no consecutive dots, no leading/trailing dots
            domain_format_valid = re.match(
                r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*$", domain_part
            ) is not None or domain_part in [
                "localhost",
                "127.0.0.1",
            ]  # Allow special local addresses
            if not domain_format_valid:
                logger.warning(f"Invalid domain format: {domain_part}")
                return False

            # Block obviously malicious domains
            suspicious = ["malware", "phishing", "hack", "exploit", "evil"]
            is_malicious = any(keyword in netloc_lower for keyword in suspicious)
            if is_malicious:
                logger.error(f"Suspicious domain blocked: {origin}")
                return False

            # If we reach here, domain format is valid and not malicious
            return True

        except Exception as e:
            logger.warning(f"Error validating CORS origin {origin}: {e}")
            return False

    @staticmethod
    def get_cors_origins() -> List[str]:
        """Get CORS origins from environment with sensible defaults."""
        env_origins = os.getenv("CORS_ORIGINS")

        if env_origins:
            logger.info("Using CORS origins from environment variable")
            origins = []
            for origin in env_origins.split(","):
                origin = origin.strip()
                if AppConfig._is_valid_origin(origin):
                    origins.append(origin)
                else:
                    logger.warning(f"Invalid CORS origin ignored: {origin}")

            if origins:
                return origins
            else:
                logger.error("No valid CORS origins in environment, using defaults")

        # Default origins based on environment
        environment = os.getenv("ENVIRONMENT", "development").lower()

        production_origins = [
            "https://nickberens.me",
            "https://www.nickberens.me",
            "https://nickberens360.netlify.app",
            "https://nickberens-astro.onrender.com",
            "https://nickberens-astro-production.up.railway.app",
        ]

        development_origins = [
            "http://localhost:4321",
            "http://localhost:3000",
            "http://localhost:5173",
        ]

        if environment in ["production", "prod"]:
            return production_origins
        else:
            return production_origins + development_origins

    # Rate Limiting
    RATE_LIMIT = os.getenv("RATE_LIMIT", "5/minute")

    # App Metadata
    APP_TITLE = "Nick Berens Portfolio API"
    APP_DESCRIPTION = "API for AI-powered responses and illustration search with Claude as primary LLM"
    APP_VERSION = "2.1.0"
