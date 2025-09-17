import ipaddress
import logging
import os
import re
import secrets
from typing import List
from urllib.parse import urlparse

# Set up logging
logger = logging.getLogger(__name__)


def sanitize_error_message(error: Exception, user_message: str = "An error occurred") -> str:
    """
    Sanitize error messages for production use.

    Args:
        error: The exception that occurred
        user_message: Safe message to show to users in production

    Returns:
        str: Sanitized error message
    """
    # In development or debug mode, show detailed errors
    if not AppConfig.IS_PRODUCTION or AppConfig.DEBUG_MODE:
        return str(error)

    # In production, return generic message and log actual error
    logger.error(f"Error sanitized for production: {str(error)}", exc_info=True)
    return user_message


class AppConfig:
    """Centralized configuration management with enhanced security."""

    # Environment detection for security
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
    IS_PRODUCTION = ENVIRONMENT == "production"
    DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true" and not IS_PRODUCTION

    # LLM Configuration - keep it simple for now
    PRIMARY_LLM = os.getenv("PRIMARY_LLM", "claude")
    CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/embedding-001")

    # Follow-up generation configuration
    # Simplified - now only using static follow-up service
    CACHE_FOLLOWUP_RESPONSES = os.getenv("CACHE_FOLLOWUP_RESPONSES", "true").lower() == "true"

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

    # RAG Best Practices Configuration - Feature Flags
    RAG_USE_MMR = os.getenv("RAG_USE_MMR", "false").lower() == "true"
    RAG_USE_HEADING_SPLITTER = os.getenv("RAG_USE_HEADING_SPLITTER", "false").lower() == "true"
    RAG_ENABLE_DELETE = os.getenv("RAG_ENABLE_DELETE", "false").lower() == "true"
    RAG_SAFE_DELETE = os.getenv("RAG_SAFE_DELETE", "true").lower() == "true"

    # RAG Score Threshold (distance - lower is better)
    try:
        RAG_SCORE_THRESHOLD = float(os.getenv("RAG_SCORE_THRESHOLD", "0.2"))
        if RAG_SCORE_THRESHOLD < 0.0 or RAG_SCORE_THRESHOLD > 1.0:
            logger.error("Invalid RAG_SCORE_THRESHOLD value. Using default value of 0.2.")
            RAG_SCORE_THRESHOLD = 0.2
    except ValueError:
        logger.error("Invalid RAG_SCORE_THRESHOLD value. Using default value of 0.2.")
        RAG_SCORE_THRESHOLD = 0.2

    # RAG Index Directories
    RAG_INDEX_DIRS = os.getenv("RAG_INDEX_DIRS", "backend/knowledge,public").split(",")
    RAG_INDEX_DIRS = [dir.strip() for dir in RAG_INDEX_DIRS if dir.strip()]

    # MMR Configuration
    try:
        RAG_MMR_K = int(os.getenv("RAG_MMR_K", "4"))
        if RAG_MMR_K < 1:
            RAG_MMR_K = 4
    except ValueError:
        RAG_MMR_K = 4

    try:
        RAG_MMR_FETCH_K = int(os.getenv("RAG_MMR_FETCH_K", "20"))
        if RAG_MMR_FETCH_K < RAG_MMR_K:
            RAG_MMR_FETCH_K = max(20, RAG_MMR_K * 2)
    except ValueError:
        RAG_MMR_FETCH_K = 20

    try:
        RAG_MMR_LAMBDA_MULT = float(os.getenv("RAG_MMR_LAMBDA_MULT", "0.5"))
        if RAG_MMR_LAMBDA_MULT < 0.0 or RAG_MMR_LAMBDA_MULT > 1.0:
            RAG_MMR_LAMBDA_MULT = 0.5
    except ValueError:
        RAG_MMR_LAMBDA_MULT = 0.5

    ILLUSTRATIONS_PATH = os.getenv("ILLUSTRATIONS_PATH", "backend/knowledge/illustrations.json")

    # Default Statistics Configuration
    try:
        DEFAULT_CACHE_HIT_RATE = float(os.getenv("DEFAULT_CACHE_HIT_RATE", "0.85"))
        if DEFAULT_CACHE_HIT_RATE < 0.0 or DEFAULT_CACHE_HIT_RATE > 1.0:
            logger.error("Invalid DEFAULT_CACHE_HIT_RATE value. Using default value of 0.85.")
            DEFAULT_CACHE_HIT_RATE = 0.85
    except ValueError:
        logger.error("Invalid DEFAULT_CACHE_HIT_RATE value. Using default value of 0.85.")
        DEFAULT_CACHE_HIT_RATE = 0.85

    try:
        DEFAULT_TOTAL_SOURCES = int(os.getenv("DEFAULT_TOTAL_SOURCES", "15"))
        if DEFAULT_TOTAL_SOURCES < 1:
            logger.error("Invalid DEFAULT_TOTAL_SOURCES value. Using default value of 15.")
            DEFAULT_TOTAL_SOURCES = 15
    except ValueError:
        logger.error("Invalid DEFAULT_TOTAL_SOURCES value. Using default value of 15.")
        DEFAULT_TOTAL_SOURCES = 15

    try:
        DEFAULT_TOTAL_TOPICS = int(os.getenv("DEFAULT_TOTAL_TOPICS", "8"))
        if DEFAULT_TOTAL_TOPICS < 1:
            logger.error("Invalid DEFAULT_TOTAL_TOPICS value. Using default value of 8.")
            DEFAULT_TOTAL_TOPICS = 8
    except ValueError:
        logger.error("Invalid DEFAULT_TOTAL_TOPICS value. Using default value of 8.")
        DEFAULT_TOTAL_TOPICS = 8

    # Query Logger Configuration
    try:
        LOW_SIMILARITY_THRESHOLD = float(os.getenv("LOW_SIMILARITY_THRESHOLD", "0.7"))
        if LOW_SIMILARITY_THRESHOLD < 0.0 or LOW_SIMILARITY_THRESHOLD > 1.0:
            logger.error("Invalid LOW_SIMILARITY_THRESHOLD value. Using default value of 0.7.")
            LOW_SIMILARITY_THRESHOLD = 0.7
    except ValueError:
        logger.error("Invalid LOW_SIMILARITY_THRESHOLD value. Using default value of 0.7.")
        LOW_SIMILARITY_THRESHOLD = 0.7

    # Dynamic attributes that will be set at module load time
    ENABLE_SMART_MODEL_SELECTION: bool
    RETRIEVAL_SCORE_THRESHOLD: float
    CACHE_TTL: int
    MAX_CACHE_SIZE: int
    EXCLUDED_IPS: List[str]
    IP_HASH_SALT: str

    # Smart Model Selection Configuration
    @classmethod
    def is_smart_model_selection_enabled(cls) -> bool:
        """Toggle smart model selection based on query complexity."""
        return os.getenv("ENABLE_SMART_MODEL_SELECTION", "true").lower() == "true"

    @classmethod
    def get_retrieval_score_threshold(cls) -> float:
        """
        Threshold for retrieval relevance scoring (0..1).

        IMPORTANT: This is a SIMILARITY score threshold where HIGHER values = BETTER matches.
        - 0.3 = keep documents with similarity >= 30% (loose matching)
        - 0.7 = keep documents with similarity >= 70% (strict matching)
        - Documents with scores ABOVE this threshold are kept
        """
        try:
            val = float(os.getenv("RETRIEVAL_SCORE_THRESHOLD", "0.3"))
            if 0.0 <= val <= 1.0:
                return val
        except ValueError:
            pass
        logger.warning("Invalid RETRIEVAL_SCORE_THRESHOLD; defaulting to 0.3")
        return 0.3

    @classmethod
    def get_cache_ttl(cls) -> int:
        """Cache TTL in seconds."""
        try:
            val = int(os.getenv("CACHE_TTL", "3600"))
            if val > 0:
                return val
        except ValueError:
            pass
        logger.warning("Invalid CACHE_TTL; defaulting to 3600")
        return 3600

    @classmethod
    def get_max_cache_size(cls) -> int:
        """Maximum cache entries."""
        try:
            val = int(os.getenv("MAX_CACHE_SIZE", "1000"))
            if val > 0:
                return val
        except ValueError:
            pass
        logger.warning("Invalid MAX_CACHE_SIZE; defaulting to 1000")
        return 1000

    # These will be computed at module load time using validated classmethods

    # Search & Retrieval Configuration
    DEFAULT_SEARCH_K = int(os.getenv("DEFAULT_SEARCH_K", "8"))  # Default number of search results
    EXPANDED_SEARCH_K = int(os.getenv("EXPANDED_SEARCH_K", "12"))  # Expanded search for comprehensive results
    SEARCH_EXPANSION_MULTIPLIER = int(os.getenv("SEARCH_EXPANSION_MULTIPLIER", "3"))  # Multiply k for initial search

    # Distance Threshold Configuration
    DEFAULT_DISTANCE_THRESHOLD = float(os.getenv("DEFAULT_DISTANCE_THRESHOLD", "0.5"))  # Default similarity threshold
    INCLUSIVE_DISTANCE_THRESHOLD = float(os.getenv("INCLUSIVE_DISTANCE_THRESHOLD", "1.0"))  # More inclusive threshold
    BROAD_DISTANCE_THRESHOLD = float(os.getenv("BROAD_DISTANCE_THRESHOLD", "1.2"))  # Very broad threshold

    # Query Processing Configuration
    DEFAULT_MAX_CONTEXT_LENGTH = int(os.getenv("DEFAULT_MAX_CONTEXT_LENGTH", "2000"))  # Token limit for context
    MAX_CONTEXT_DOCUMENTS = int(os.getenv("MAX_CONTEXT_DOCUMENTS", "3"))  # Max docs in context
    CONTEXT_FILL_RATIO = float(os.getenv("CONTEXT_FILL_RATIO", "0.7"))  # Fill ratio before truncation
    CONTENT_FINGERPRINT_LENGTH = int(os.getenv("CONTENT_FINGERPRINT_LENGTH", "100"))  # Length for deduplication
    LENGTH_PENALTY_DIVISOR = int(os.getenv("LENGTH_PENALTY_DIVISOR", "1000"))  # For document length penalty

    # Illustration Search Configuration
    DEFAULT_ILLUSTRATION_COUNT = int(os.getenv("DEFAULT_ILLUSTRATION_COUNT", "10"))  # Default illustrations returned
    MAX_ILLUSTRATION_SEARCH = int(os.getenv("MAX_ILLUSTRATION_SEARCH", "200"))  # Max illustrations to search

    # Fuzzy Matching Configuration
    SHORT_TERM_LENGTH = int(os.getenv("FUZZY_SHORT_TERM_LENGTH", "6"))  # Character threshold for short terms
    MEDIUM_TERM_LENGTH = int(os.getenv("FUZZY_MEDIUM_TERM_LENGTH", "10"))  # Character threshold for medium terms
    SHORT_TERM_FUZZY_THRESHOLD = float(
        os.getenv("SHORT_TERM_FUZZY_THRESHOLD", "0.45")
    )  # Fuzzy threshold for short terms
    MEDIUM_TERM_FUZZY_THRESHOLD = float(
        os.getenv("MEDIUM_TERM_FUZZY_THRESHOLD", "0.5")
    )  # Fuzzy threshold for medium terms
    LONG_TERM_FUZZY_THRESHOLD = float(os.getenv("LONG_TERM_FUZZY_THRESHOLD", "0.55"))  # Fuzzy threshold for long terms
    DEFAULT_FUZZY_THRESHOLD = float(os.getenv("DEFAULT_FUZZY_THRESHOLD", "0.7"))  # Default fuzzy matching threshold

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

        # Allow wildcard only when not in production
        if origin == "*":
            # Determine production dynamically: prefer ENVIRONMENT override for tests, fallback to AppConfig
            env = os.getenv("ENVIRONMENT")
            if env is not None:
                is_prod = env.lower() in ["production", "prod"]
            else:
                is_prod = AppConfig.is_production()

            if not is_prod:
                logger.warning("Wildcard CORS origin allowed in development mode")
                return True
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

            # Enforce HTTPS for public domains (allow HTTP for local/private networks)
            netloc_lower = parsed.netloc.lower()
            host = parsed.hostname or ""
            is_private_ip = False
            try:
                ip_obj = ipaddress.ip_address(host)
                is_private_ip = ip_obj.is_private or ip_obj.is_loopback
            except ValueError:
                # Not an IP address
                is_private_ip = False

            is_localhost = host.startswith("localhost") or host.startswith("127.0.0.1")
            if not is_localhost and not is_private_ip:
                if parsed.scheme != "https":
                    logger.warning(f"Non-HTTPS origin for production/public domain: {origin}")
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
            "https://nickberens-astro-development.up.railway.app",
        ]

        development_origins = [
            "http://localhost:4321",
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:3002",
            "http://localhost:3003",
            "http://localhost:5173",
            "http://localhost:8000",
            "http://localhost:8001",
            "http://localhost:8002",
            "http://localhost:8003",
        ]

        if environment in ["production", "prod"]:
            return production_origins
        else:
            return production_origins + development_origins

    # Rate Limiting
    RATE_LIMIT = os.getenv("RATE_LIMIT", "5/minute")

    # Query Logging Configuration
    @classmethod
    def is_production(cls) -> bool:
        """Convenience method for tests to patch production mode."""
        return cls.IS_PRODUCTION

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

    # IP Anonymization Settings (GDPR/CCPA compliance)
    ANONYMIZE_IPS = os.getenv("ANONYMIZE_IPS", "true").lower() == "true"  # Enable IP anonymization by default

    @classmethod
    def get_ip_hash_salt(cls) -> str:
        """Get IP hash salt with secure default generation.

        Uses AppConfig production detection for consistency across the codebase.
        """
        salt = os.getenv("IP_HASH_SALT", "")

        if not salt:
            if cls.IS_PRODUCTION:
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

    # App Metadata
    APP_TITLE = "Nick Berens Portfolio API"
    APP_DESCRIPTION = """
Intelligent API for Nick Berens' Portfolio and Knowledge Base

This API provides AI-powered access to Nick's professional experience, skills, projects, and creative work using advanced RAG (Retrieval-Augmented Generation) technology.

🚀 Key Features:
• AI-Powered Queries: Ask questions about Nick's experience, skills, and projects
• Smart Illustration Search: Find and browse Nick's creative artwork and illustrations
• Intelligent Routing: Automatically determines whether you're asking about text content or images
• Real-time AI Responses: Streaming responses using Claude (Anthropic) and Gemini (Google)
• Comprehensive Admin Dashboard: Complete analytics and management interface
• Advanced Security: Rate limiting, input validation, and secure authentication

📖 Getting Started:

1. Basic Query:
   POST /query with {"question": "What is Nick's professional background?"}

2. Request Illustrations:
   POST /query with {"question": "Show me some creative illustrations"}

3. Admin Authentication:
   POST /api/admin/auth/login with {"username": "admin", "password": "your-password"}

🔒 Authentication:
• Public Endpoints: No authentication required for basic queries
• Admin Endpoints: Session-based authentication with secure HTTPOnly cookies
• Rate Limiting: 100 requests per minute per IP address

📊 Available Data:
• Professional Experience: Work history, roles, companies (Calendly, etc.)
• Technical Skills: Vue.js, Python, FastAPI, full-stack development
• Creative Work: Digital illustrations, artwork, and visual projects
• Personal Projects: Open source contributions, side projects

🛠️ Admin Features:
• Query Analytics: Monitor usage patterns and popular questions
• Performance Metrics: Track response times and system health
• Content Management: Manage knowledge base and illustration metadata
• User Management: Admin user creation and role management
• Security Monitoring: Audit logs and security event tracking

🔧 Technical Details:
• AI Models: Claude 3.5 Sonnet (primary), Gemini 1.5 Flash (fallback)
• Vector Database: ChromaDB for semantic search
• Security: Input validation, rate limiting, CSRF protection
• Monitoring: Comprehensive logging and health checks
• Performance: Response caching, smart context management

Built with ❤️ by Nick Berens using FastAPI, Vue.js, and modern AI technologies.
    """
    APP_VERSION = "2.1.0"


# Compute complex properties at module load time using validated classmethods
AppConfig.ENABLE_SMART_MODEL_SELECTION = AppConfig.is_smart_model_selection_enabled()
AppConfig.RETRIEVAL_SCORE_THRESHOLD = AppConfig.get_retrieval_score_threshold()
AppConfig.CACHE_TTL = AppConfig.get_cache_ttl()
AppConfig.MAX_CACHE_SIZE = AppConfig.get_max_cache_size()
AppConfig.EXCLUDED_IPS = AppConfig.get_excluded_ips()
# AppConfig.QUERY_LOG_AUTH_TOKEN assignment removed - using session-based auth only
AppConfig.IP_HASH_SALT = AppConfig.get_ip_hash_salt()
