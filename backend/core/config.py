import ipaddress
import logging
import os
import re
import secrets
from pathlib import Path
from typing import List, Optional
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

    # Follow-up generation configuration
    @classmethod
    def get_followup_mode(cls) -> str:
        """Return follow-up mode: pre_generated | optimized | static."""
        mode = os.getenv("FOLLOWUP_MODE", "pre_generated").strip().lower()
        if mode not in {"pre_generated", "optimized", "static"}:
            logger.warning(f"Invalid FOLLOWUP_MODE '{mode}', defaulting to 'pre_generated'")
            return "pre_generated"
        return mode

    @classmethod
    def is_followup_pregeneration_enabled(cls) -> bool:
        """Toggle pre-generation during startup to control cold-start costs."""
        return os.getenv("ENABLE_FOLLOWUP_PREGENERATION", "true").lower() == "true"

    @classmethod
    def get_followup_validation_score_threshold(cls) -> float:
        """Threshold for validating follow-up relevance (0..1)."""
        try:
            val = float(os.getenv("FOLLOWUP_VALIDATION_SCORE_THRESHOLD", "0.5"))
            if 0.0 <= val <= 1.0:
                return val
        except ValueError:
            pass
        logger.warning("Invalid FOLLOWUP_VALIDATION_SCORE_THRESHOLD; defaulting to 0.5")
        return 0.5

    @classmethod
    def is_followup_llm_enhancement_enabled(cls) -> bool:
        """Enable LLM enhancement for follow-up generation (may cause timeouts)."""
        return os.getenv("FOLLOWUP_USE_LLM_ENHANCEMENT", "false").lower() == "true"

    # Backward-compatible class-level properties
    class classproperty(property):
        def __get__(self, obj, owner):  # type: ignore[override]
            return self.fget(owner)  # type: ignore[misc]

    @classproperty
    def FOLLOWUP_MODE(cls) -> str:
        return cls.get_followup_mode()

    @classproperty
    def ENABLE_FOLLOWUP_PREGENERATION(cls) -> bool:
        return cls.is_followup_pregeneration_enabled()

    @classproperty
    def FOLLOWUP_VALIDATION_SCORE_THRESHOLD(cls) -> float:
        return cls.get_followup_validation_score_threshold()

    @classproperty
    def FOLLOWUP_USE_LLM_ENHANCEMENT(cls) -> bool:
        return cls.is_followup_llm_enhancement_enabled()

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

    ILLUSTRATIONS_PATH = os.getenv("ILLUSTRATIONS_PATH", "backend/knowledge/illustrations.json")

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

    # Query Logging Configuration
    @classmethod
    def get_excluded_ips(cls) -> List[str]:
        """Get and validate excluded IPs from environment."""
        excluded_ips_str = os.getenv("EXCLUDED_IPS", "")
        if not excluded_ips_str:
            return []

        excluded_ips = []
        for ip in excluded_ips_str.split(","):
            ip = ip.strip()
            if ip:
                try:
                    # Validate IP address format
                    ipaddress.ip_address(ip)
                    excluded_ips.append(ip)
                except ValueError:
                    logger.warning(f"Invalid IP address in EXCLUDED_IPS: {ip}")

        return excluded_ips

    @classproperty
    def EXCLUDED_IPS(cls):
        return cls.get_excluded_ips()

    # Query Log Authentication
    @classmethod
    def get_query_log_auth_token(cls) -> Optional[str]:
        """Get query log auth token with production enforcement."""
        token = os.getenv("QUERY_LOG_AUTH_TOKEN", "")
        environment = os.getenv("ENV", "development").lower()

        if environment in ["production", "prod"] and not token:
            raise ValueError(
                "QUERY_LOG_AUTH_TOKEN must be set in production environments. "
                "Generate a secure token and set it as an environment variable."
            )

        return token if token else None

    @classproperty
    def QUERY_LOG_AUTH_TOKEN(cls) -> Optional[str]:
        return cls.get_query_log_auth_token()

    # IP Anonymization Settings (GDPR/CCPA compliance)
    ANONYMIZE_IPS = os.getenv("ANONYMIZE_IPS", "true").lower() == "true"  # Enable IP anonymization by default

    @classmethod
    def get_ip_hash_salt(cls) -> str:
        """Get IP hash salt with secure default generation."""
        salt = os.getenv("IP_HASH_SALT", "")
        environment = os.getenv("ENV", "development").lower()

        if not salt:
            if environment in ["production", "prod"]:
                raise ValueError(
                    "IP_HASH_SALT must be explicitly set in production environments. "
                    "Generate a secure salt using: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
                )
            else:
                # Generate a secure random salt for development
                salt = secrets.token_urlsafe(32)
                logger.warning(
                    f"Using generated IP_HASH_SALT for development: {salt[:8]}... "
                    "Set IP_HASH_SALT environment variable for consistent hashing."
                )

        return salt

    @classproperty
    def IP_HASH_SALT(cls) -> str:
        return cls.get_ip_hash_salt()

    # Query Log storage
    @classmethod
    def get_query_log_file(cls) -> str:
        """Return the log file path, overridable via QUERY_LOG_FILE.

        Use this to point logs at a persistent volume path in production
        (e.g., "/data/query_logs/query_logs.json" on Railway with a mounted volume).
        """
        env_path = os.getenv("QUERY_LOG_FILE")
        if env_path and env_path.strip():
            return env_path.strip()

        # Default to logs directory (directory creation handled during app initialization)
        backend_dir = Path(__file__).parent.parent.resolve()  # Make it absolute
        logs_dir = backend_dir / "logs"
        log_file_path = str(logs_dir / "query_logs.json")
        logger.info(f"Query log file path: {log_file_path}")
        return log_file_path

    @classproperty
    def QUERY_LOG_FILE(cls) -> str:
        return cls.get_query_log_file()

    # App Metadata
    APP_TITLE = "Nick Berens Portfolio API"
    APP_DESCRIPTION = "API for AI-powered responses and illustration search with Claude as primary LLM"
    APP_VERSION = "2.1.0"
