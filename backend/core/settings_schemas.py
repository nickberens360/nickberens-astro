"""
Settings schema definitions for DB-driven runtime configuration.
All settings that can be modified via admin interface are defined here.
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from typing import Dict, List

logger = logging.getLogger(__name__)


@dataclass
class FollowUpSettings:
    """Configuration for follow-up question generation."""

    enabled: bool = True
    service_type: str = "static"  # static, dynamic, contextual
    max_questions: int = 1
    relevance_threshold: float = 0.7
    include_technical: bool = True
    include_personal: bool = True
    include_creative: bool = True
    question_style: str = "conversational"  # formal, conversational, exploratory
    custom_questions: Dict[str, List[str]] = field(default_factory=dict)  # Custom questions by category

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "FollowUpSettings":
        """Create from dictionary with validation."""
        # Validate and set defaults for missing keys
        defaults = cls()
        validated_data = {}

        for key, default_value in asdict(defaults).items():
            if key in data:
                validated_data[key] = data[key]
            else:
                validated_data[key] = default_value

        # Type validation
        if not isinstance(validated_data["enabled"], bool):
            validated_data["enabled"] = str(validated_data["enabled"]).lower() == "true"

        if not isinstance(validated_data["max_questions"], int):
            try:
                validated_data["max_questions"] = int(validated_data["max_questions"])
            except (ValueError, TypeError):
                validated_data["max_questions"] = defaults.max_questions

        # Ensure max_questions is within reasonable bounds
        validated_data["max_questions"] = max(1, min(5, validated_data["max_questions"]))

        if not isinstance(validated_data["relevance_threshold"], float):
            try:
                validated_data["relevance_threshold"] = float(validated_data["relevance_threshold"])
            except (ValueError, TypeError):
                validated_data["relevance_threshold"] = defaults.relevance_threshold

        # Ensure relevance_threshold is within bounds
        validated_data["relevance_threshold"] = max(0.1, min(1.0, validated_data["relevance_threshold"]))

        # Validate service_type
        valid_service_types = ["static", "dynamic", "contextual"]
        if validated_data["service_type"] not in valid_service_types:
            validated_data["service_type"] = defaults.service_type

        # Validate question_style
        valid_styles = ["formal", "conversational", "exploratory"]
        if validated_data["question_style"] not in valid_styles:
            validated_data["question_style"] = defaults.question_style

        # Validate custom_questions
        if "custom_questions" in validated_data and validated_data["custom_questions"]:
            custom_questions = validated_data["custom_questions"]
            if not isinstance(custom_questions, dict):
                validated_data["custom_questions"] = {}
            else:
                # Validate categories and questions
                valid_categories = ["technical", "personal", "creative"]
                cleaned_questions = {}
                for category, questions in custom_questions.items():
                    if category in valid_categories and isinstance(questions, list):
                        # Filter and validate individual questions
                        valid_questions = []
                        for q in questions:
                            if isinstance(q, str) and q.strip() and len(q.strip()) <= 200:
                                valid_questions.append(q.strip())
                        if valid_questions:
                            cleaned_questions[category] = valid_questions[:20]  # Max 20 questions per category
                validated_data["custom_questions"] = cleaned_questions
        else:
            validated_data["custom_questions"] = {}

        return cls(**validated_data)

    def to_json(self) -> str:
        """Convert to JSON string for database storage."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "FollowUpSettings":
        """Create from JSON string with error handling."""
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning(f"Failed to parse follow-up settings from JSON: {e}")
            return cls()  # Return defaults on error


@dataclass
class ResponseSettings:
    """Configuration for response generation behavior."""

    # Context and caching settings (existing)
    max_context_length: int = 2000
    max_context_documents: int = 3
    context_fill_ratio: float = 0.7
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600

    # Response generation settings (new)
    preferred_response_length: str = "medium"  # brief, medium, detailed, comprehensive
    response_style: str = "conversational"  # professional, conversational, technical, casual
    include_sources: bool = True
    source_format: str = "numbered"  # numbered, bulleted, inline
    max_sources: int = 5
    enable_markdown: bool = True
    enable_code_highlighting: bool = True

    # Smart model selection settings (new)
    response_llm: str = "claude"  # claude, gemini
    enable_smart_selection: bool = True  # Enable smart model selection within family

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ResponseSettings":
        """Create from dictionary with validation."""
        defaults = cls()
        validated_data = {}

        for key, default_value in asdict(defaults).items():
            if key in data:
                validated_data[key] = data[key]
            else:
                validated_data[key] = default_value

        # Validate max_context_length
        if not isinstance(validated_data["max_context_length"], int):
            try:
                validated_data["max_context_length"] = int(validated_data["max_context_length"])
            except (ValueError, TypeError):
                validated_data["max_context_length"] = defaults.max_context_length

        # Ensure within bounds
        validated_data["max_context_length"] = max(100, min(10000, validated_data["max_context_length"]))

        # Validate max_context_documents
        if not isinstance(validated_data["max_context_documents"], int):
            try:
                validated_data["max_context_documents"] = int(validated_data["max_context_documents"])
            except (ValueError, TypeError):
                validated_data["max_context_documents"] = defaults.max_context_documents

        validated_data["max_context_documents"] = max(1, min(10, validated_data["max_context_documents"]))

        # Validate context_fill_ratio
        if not isinstance(validated_data["context_fill_ratio"], float):
            try:
                validated_data["context_fill_ratio"] = float(validated_data["context_fill_ratio"])
            except (ValueError, TypeError):
                validated_data["context_fill_ratio"] = defaults.context_fill_ratio

        validated_data["context_fill_ratio"] = max(0.1, min(1.0, validated_data["context_fill_ratio"]))

        # Validate boolean fields
        for bool_field in [
            "enable_caching",
            "include_sources",
            "enable_markdown",
            "enable_code_highlighting",
            "enable_smart_selection",
        ]:
            if not isinstance(validated_data[bool_field], bool):
                validated_data[bool_field] = str(validated_data[bool_field]).lower() == "true"

        # Validate cache_ttl_seconds
        if not isinstance(validated_data["cache_ttl_seconds"], int):
            try:
                validated_data["cache_ttl_seconds"] = int(validated_data["cache_ttl_seconds"])
            except (ValueError, TypeError):
                validated_data["cache_ttl_seconds"] = defaults.cache_ttl_seconds

        validated_data["cache_ttl_seconds"] = max(60, min(86400, validated_data["cache_ttl_seconds"]))

        # Validate response length preference
        valid_lengths = ["brief", "medium", "detailed", "comprehensive"]
        if validated_data["preferred_response_length"] not in valid_lengths:
            validated_data["preferred_response_length"] = "medium"

        # Validate response style preference
        valid_styles = ["professional", "conversational", "technical", "casual"]
        if validated_data["response_style"] not in valid_styles:
            validated_data["response_style"] = "conversational"

        # Validate source format preference
        valid_formats = ["numbered", "bulleted", "inline"]
        if validated_data["source_format"] not in valid_formats:
            validated_data["source_format"] = "numbered"

        # Validate max_sources
        if not isinstance(validated_data["max_sources"], int):
            try:
                validated_data["max_sources"] = int(validated_data["max_sources"])
            except (ValueError, TypeError):
                validated_data["max_sources"] = defaults.max_sources

        validated_data["max_sources"] = max(0, min(20, validated_data["max_sources"]))

        # Validate response_llm preference
        valid_llms = ["claude", "gemini"]
        if validated_data["response_llm"] not in valid_llms:
            validated_data["response_llm"] = "claude"

        return cls(**validated_data)

    def to_json(self) -> str:
        """Convert to JSON string for database storage."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "ResponseSettings":
        """Create from JSON string with error handling."""
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning(f"Failed to parse response settings from JSON: {e}")
            return cls()  # Return defaults on error


@dataclass
class QueryRoutingSettings:
    """Configuration for query routing and processing."""

    # Smart routing configuration
    enable_smart_routing: bool = True
    confidence_threshold: float = 0.75
    fallback_strategy: str = (
        "comprehensive_search"  # comprehensive_search, semantic_similarity, keyword_matching, default_response
    )

    # Caching configuration
    enable_caching: bool = True
    cache_ttl_seconds: int = 300  # 5 minutes

    # Processing configuration
    enable_parallel_processing: bool = True
    max_retries: int = 3

    # Search configuration (existing)
    similarity_threshold: float = 0.3
    max_search_results: int = 15
    enable_fuzzy_matching: bool = True
    fuzzy_threshold: float = 0.7

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "QueryRoutingSettings":
        """Create from dictionary with validation."""
        defaults = cls()
        validated_data = {}

        for key, default_value in asdict(defaults).items():
            if key in data:
                validated_data[key] = data[key]
            else:
                validated_data[key] = default_value

        # Validate boolean fields
        for bool_field in [
            "enable_smart_routing",
            "enable_fuzzy_matching",
            "enable_caching",
            "enable_parallel_processing",
        ]:
            if not isinstance(validated_data[bool_field], bool):
                validated_data[bool_field] = str(validated_data[bool_field]).lower() == "true"

        # Validate similarity_threshold
        if not isinstance(validated_data["similarity_threshold"], float):
            try:
                validated_data["similarity_threshold"] = float(validated_data["similarity_threshold"])
            except (ValueError, TypeError):
                validated_data["similarity_threshold"] = defaults.similarity_threshold

        validated_data["similarity_threshold"] = max(0.0, min(1.0, validated_data["similarity_threshold"]))

        # Validate max_search_results
        if not isinstance(validated_data["max_search_results"], int):
            try:
                validated_data["max_search_results"] = int(validated_data["max_search_results"])
            except (ValueError, TypeError):
                validated_data["max_search_results"] = defaults.max_search_results

        validated_data["max_search_results"] = max(1, min(100, validated_data["max_search_results"]))

        # Validate fuzzy_threshold
        if not isinstance(validated_data["fuzzy_threshold"], float):
            try:
                validated_data["fuzzy_threshold"] = float(validated_data["fuzzy_threshold"])
            except (ValueError, TypeError):
                validated_data["fuzzy_threshold"] = defaults.fuzzy_threshold

        validated_data["fuzzy_threshold"] = max(0.0, min(1.0, validated_data["fuzzy_threshold"]))

        # Validate confidence_threshold
        if not isinstance(validated_data["confidence_threshold"], float):
            try:
                validated_data["confidence_threshold"] = float(validated_data["confidence_threshold"])
            except (ValueError, TypeError):
                validated_data["confidence_threshold"] = defaults.confidence_threshold

        validated_data["confidence_threshold"] = max(0.0, min(1.0, validated_data["confidence_threshold"]))

        # Validate fallback_strategy
        valid_strategies = ["comprehensive_search", "semantic_similarity", "keyword_matching", "default_response"]
        if validated_data["fallback_strategy"] not in valid_strategies:
            validated_data["fallback_strategy"] = "comprehensive_search"

        # Validate cache_ttl_seconds
        if not isinstance(validated_data["cache_ttl_seconds"], int):
            try:
                validated_data["cache_ttl_seconds"] = int(validated_data["cache_ttl_seconds"])
            except (ValueError, TypeError):
                validated_data["cache_ttl_seconds"] = defaults.cache_ttl_seconds

        validated_data["cache_ttl_seconds"] = max(60, min(3600, validated_data["cache_ttl_seconds"]))

        # Validate max_retries
        if not isinstance(validated_data["max_retries"], int):
            try:
                validated_data["max_retries"] = int(validated_data["max_retries"])
            except (ValueError, TypeError):
                validated_data["max_retries"] = defaults.max_retries

        validated_data["max_retries"] = max(0, min(10, validated_data["max_retries"]))

        return cls(**validated_data)

    def to_json(self) -> str:
        """Convert to JSON string for database storage."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "QueryRoutingSettings":
        """Create from JSON string with error handling."""
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning(f"Failed to parse query routing settings from JSON: {e}")
            return cls()  # Return defaults on error


@dataclass
class FeatureFlags:
    """Feature flags for enabling/disabling system features."""

    enable_followup_questions: bool = True
    enable_smart_routing: bool = True
    enable_caching: bool = True
    enable_analytics: bool = True
    enable_debug_mode: bool = False
    enable_maintenance_mode: bool = False
    enable_rate_limiting: bool = True
    enable_api_versioning: bool = False
    # Legacy flags (for backward compatibility)
    enable_illustrations: bool = True
    enable_geolocation: bool = True
    enable_response_caching: bool = True
    enable_query_preprocessing: bool = True

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "FeatureFlags":
        """Create from dictionary with validation."""
        defaults = cls()
        validated_data = {}

        for key, default_value in asdict(defaults).items():
            if key in data:
                validated_data[key] = data[key]
            else:
                validated_data[key] = default_value

        # Validate all boolean fields
        for field_name in asdict(defaults).keys():
            if not isinstance(validated_data[field_name], bool):
                validated_data[field_name] = str(validated_data[field_name]).lower() == "true"

        return cls(**validated_data)

    def to_json(self) -> str:
        """Convert to JSON string for database storage."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "FeatureFlags":
        """Create from JSON string with error handling."""
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning(f"Failed to parse feature flags from JSON: {e}")
            return cls()  # Return defaults on error


@dataclass
class SystemConfigurationSettings:
    """Configuration for core system settings."""

    # LLM Configuration (Legacy - use response_llm instead)
    primary_llm: str = "claude"  # claude, gemini (DEPRECATED: maps to response_llm)
    claude_model: str = "claude-3-5-sonnet-20241022"
    gemini_model: str = "gemini-1.5-flash"
    embedding_model: str = "models/embedding-001"

    # User-Facing Response LLM (what chatbot uses to respond)
    response_llm: str = "claude"  # claude, gemini
    response_claude_model: str = "claude-3-5-sonnet-20241022"
    response_gemini_model: str = "gemini-1.5-flash"

    # Background Processing LLM (indexing, reformulation, etc.)
    processing_llm: str = "claude_haiku"  # claude_haiku, claude, gemini
    processing_claude_model: str = "claude-3-haiku-20240307"
    processing_gemini_model: str = "gemini-1.5-flash"

    # Smart Selection Settings
    enable_response_smart_selection: bool = True  # Allow complexity-based switching within response model family

    # Performance Settings
    cache_ttl_seconds: int = 3600
    max_cache_size: int = 1000
    rate_limit: str = "100/minute"

    # Search Configuration
    search_similarity_threshold: float = 0.55  # Percentage converted to 0-100 scale in UI
    max_search_results: int = 15
    retrieval_score_threshold: float = 0.3

    # Cache & Performance
    enable_smart_model_selection: bool = True
    default_search_k: int = 8
    expanded_search_k: int = 12

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def _migrate_legacy_llm_settings(
        cls, validated_data: dict, defaults: "SystemConfigurationSettings", original_data: dict
    ) -> None:
        """
        Migrate legacy LLM settings to new structure for backward compatibility.

        If new LLM fields are missing from database, populate them from legacy primary_llm.
        """
        # Check if this is a legacy configuration (missing new fields in original data)
        new_fields = [
            "response_llm",
            "processing_llm",
            "response_claude_model",
            "response_gemini_model",
            "processing_claude_model",
            "processing_gemini_model",
        ]

        is_legacy = any(field not in original_data for field in new_fields)

        if is_legacy:
            logger.info("Migrating legacy LLM configuration to new structure")

            # Populate new fields from legacy primary_llm
            legacy_primary = validated_data.get("primary_llm", defaults.primary_llm)

            # Response LLM inherits from primary_llm
            if "response_llm" not in original_data:
                validated_data["response_llm"] = legacy_primary
                logger.info(f"Migrated response_llm to: {legacy_primary}")

            # Processing LLM defaults to fast model for background operations
            if "processing_llm" not in validated_data:
                validated_data["processing_llm"] = "claude_haiku"  # Always fast for background

            # Response model variants inherit from legacy models
            if "response_claude_model" not in validated_data:
                validated_data["response_claude_model"] = validated_data.get("claude_model", defaults.claude_model)

            if "response_gemini_model" not in validated_data:
                validated_data["response_gemini_model"] = validated_data.get("gemini_model", defaults.gemini_model)

            # Processing model variants use optimized defaults
            if "processing_claude_model" not in validated_data:
                validated_data["processing_claude_model"] = "claude-3-haiku-20240307"  # Fast model

            if "processing_gemini_model" not in validated_data:
                validated_data["processing_gemini_model"] = validated_data.get("gemini_model", defaults.gemini_model)

            # Smart selection setting inherits from enable_smart_model_selection
            if "enable_response_smart_selection" not in validated_data:
                validated_data["enable_response_smart_selection"] = validated_data.get(
                    "enable_smart_model_selection", defaults.enable_smart_model_selection
                )

    # === CONVENIENCE METHODS FOR BACKWARD COMPATIBILITY ===

    def get_response_model_name(self) -> str:
        """Get the specific model name for the response LLM."""
        if self.response_llm == "claude":
            return self.response_claude_model
        elif self.response_llm == "gemini":
            return self.response_gemini_model
        else:
            # Fallback to legacy if response_llm is invalid
            return self.claude_model if self.primary_llm == "claude" else self.gemini_model

    def get_processing_model_name(self) -> str:
        """Get the specific model name for the processing LLM."""
        if self.processing_llm == "claude" or self.processing_llm == "claude_haiku":
            return self.processing_claude_model
        elif self.processing_llm == "gemini":
            return self.processing_gemini_model
        else:
            # Default to fast Claude model
            return "claude-3-haiku-20240307"

    @property
    def effective_primary_llm(self) -> str:
        """Get the effective primary LLM (response_llm with fallback to primary_llm for compatibility)."""
        return self.response_llm if hasattr(self, "response_llm") else self.primary_llm

    @classmethod
    def from_dict(cls, data: dict) -> "SystemConfigurationSettings":
        """Create from dictionary with validation."""
        defaults = cls()
        validated_data = {}

        for key, default_value in asdict(defaults).items():
            if key in data:
                validated_data[key] = data[key]
            else:
                validated_data[key] = default_value

        # Validate primary_llm
        valid_llms = ["claude", "gemini"]
        if validated_data["primary_llm"] not in valid_llms:
            validated_data["primary_llm"] = defaults.primary_llm

        # Validate Claude model
        valid_claude_models = ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-opus-20240229"]
        if validated_data["claude_model"] not in valid_claude_models:
            validated_data["claude_model"] = defaults.claude_model

        # Validate Gemini model
        valid_gemini_models = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]
        if validated_data["gemini_model"] not in valid_gemini_models:
            validated_data["gemini_model"] = defaults.gemini_model

        # === NEW LLM CONFIGURATION VALIDATION ===

        # Backward compatibility: if new fields missing, populate from legacy fields
        cls._migrate_legacy_llm_settings(validated_data, defaults, data)

        # Validate response_llm
        valid_response_llms = ["claude", "gemini"]
        if validated_data["response_llm"] not in valid_response_llms:
            validated_data["response_llm"] = defaults.response_llm

        # Validate processing_llm
        valid_processing_llms = ["claude_haiku", "claude", "gemini"]
        if validated_data["processing_llm"] not in valid_processing_llms:
            validated_data["processing_llm"] = defaults.processing_llm

        # Validate response model variants
        if validated_data["response_claude_model"] not in valid_claude_models:
            validated_data["response_claude_model"] = defaults.response_claude_model

        if validated_data["response_gemini_model"] not in valid_gemini_models:
            validated_data["response_gemini_model"] = defaults.response_gemini_model

        # Validate processing model variants
        if validated_data["processing_claude_model"] not in valid_claude_models:
            validated_data["processing_claude_model"] = defaults.processing_claude_model

        if validated_data["processing_gemini_model"] not in valid_gemini_models:
            validated_data["processing_gemini_model"] = defaults.processing_gemini_model

        # Validate numeric fields with bounds
        numeric_validations = {
            "cache_ttl_seconds": (60, 86400),  # 1 minute to 1 day
            "max_cache_size": (10, 10000),  # 10 to 10k entries
            "max_search_results": (1, 100),
            "default_search_k": (1, 50),
            "expanded_search_k": (1, 50),
        }

        for field, (min_val, max_val) in numeric_validations.items():
            if not isinstance(validated_data[field], int):
                try:
                    validated_data[field] = int(validated_data[field])
                except (ValueError, TypeError):
                    validated_data[field] = getattr(defaults, field)
            validated_data[field] = max(min_val, min(max_val, validated_data[field]))

        # Validate float fields with bounds
        float_validations = {"search_similarity_threshold": (0.0, 1.0), "retrieval_score_threshold": (0.0, 1.0)}

        for field, (min_val, max_val) in float_validations.items():
            if not isinstance(validated_data[field], float):
                try:
                    validated_data[field] = float(validated_data[field])
                except (ValueError, TypeError):
                    validated_data[field] = getattr(defaults, field)
            validated_data[field] = max(min_val, min(max_val, validated_data[field]))

        # Validate boolean fields
        for bool_field in ["enable_smart_model_selection", "enable_response_smart_selection"]:
            if not isinstance(validated_data[bool_field], bool):
                validated_data[bool_field] = str(validated_data[bool_field]).lower() == "true"

        # Validate rate_limit format
        import re

        rate_pattern = r"^\d+/(minute|hour|day)$"
        if not isinstance(validated_data["rate_limit"], str) or not re.match(
            rate_pattern, validated_data["rate_limit"]
        ):
            validated_data["rate_limit"] = defaults.rate_limit

        return cls(**validated_data)

    def to_json(self) -> str:
        """Convert to JSON string for database storage."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "SystemConfigurationSettings":
        """Create from JSON string with error handling."""
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning(f"Failed to parse system configuration settings from JSON: {e}")
            return cls()  # Return defaults on error


@dataclass
class SecuritySettings:
    """Configuration for security and privacy settings."""

    # IP Management
    excluded_ips: List[str] = field(default_factory=list)
    anonymize_ips: bool = True

    # CORS Configuration
    cors_origins: List[str] = field(default_factory=list)  # Empty means use defaults

    # Query Logging
    enable_query_logging: bool = True
    low_similarity_threshold: float = 0.7
    query_log_retention_days: int = 30

    # Authentication & Sessions
    session_timeout_minutes: int = 480  # 8 hours
    enable_session_fingerprinting: bool = True
    enable_audit_logging: bool = True

    # Rate Limiting & Protection
    enable_rate_limiting: bool = True
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds
    max_requests_per_minute: int = 100  # Legacy field for backward compatibility
    enable_input_validation: bool = True

    # CORS Policy
    enable_cors: bool = True
    allowed_origins: List[str] = field(default_factory=lambda: ["http://localhost:3000", "http://localhost:4321"])

    # Authentication Security
    enable_api_keys: bool = False
    require_https: bool = True
    session_timeout: int = 86400  # seconds (24 hours)
    max_login_attempts: int = 5
    lockout_duration: int = 300  # seconds (5 minutes)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SecuritySettings":
        """Create from dictionary with validation."""
        defaults = cls()
        validated_data = {}

        for key, default_value in asdict(defaults).items():
            if key in data:
                validated_data[key] = data[key]
            else:
                validated_data[key] = default_value

        # Validate IP addresses
        if isinstance(validated_data["excluded_ips"], list):
            import ipaddress

            valid_ips = []
            for ip in validated_data["excluded_ips"]:
                if isinstance(ip, str) and ip.strip():
                    try:
                        ipaddress.ip_address(ip.strip())
                        valid_ips.append(ip.strip())
                    except ValueError:
                        logger.warning(f"Invalid IP address ignored: {ip}")
            validated_data["excluded_ips"] = valid_ips[:50]  # Max 50 IPs
        else:
            validated_data["excluded_ips"] = []

        # Validate CORS origins (legacy field)
        if isinstance(validated_data["cors_origins"], list):
            from urllib.parse import urlparse

            valid_origins = []
            for origin in validated_data["cors_origins"]:
                if isinstance(origin, str) and origin.strip():
                    origin = origin.strip()
                    # Basic URL validation
                    try:
                        parsed = urlparse(origin)
                        if parsed.scheme in ["http", "https"] and parsed.netloc:
                            valid_origins.append(origin)
                    except Exception:
                        logger.warning(f"Invalid CORS origin ignored: {origin}")
            validated_data["cors_origins"] = valid_origins[:20]  # Max 20 origins
        else:
            validated_data["cors_origins"] = []

        # Validate allowed_origins (new field)
        if isinstance(validated_data["allowed_origins"], list):
            from urllib.parse import urlparse

            valid_origins = []
            for origin in validated_data["allowed_origins"]:
                if isinstance(origin, str) and origin.strip():
                    origin = origin.strip()
                    # Basic URL validation
                    try:
                        parsed = urlparse(origin)
                        if parsed.scheme in ["http", "https"] and parsed.netloc:
                            valid_origins.append(origin)
                    except Exception:
                        logger.warning(f"Invalid allowed origin ignored: {origin}")
            validated_data["allowed_origins"] = valid_origins[:20]  # Max 20 origins
        else:
            validated_data["allowed_origins"] = ["http://localhost:3000"]  # Default

        # Validate numeric fields with bounds
        numeric_validations = {
            "query_log_retention_days": (1, 365),  # 1 day to 1 year
            "session_timeout_minutes": (30, 1440),  # 30 minutes to 24 hours
            "max_requests_per_minute": (1, 1000),  # 1 to 1000 requests per minute
            "rate_limit_requests": (1, 10000),  # 1 to 10,000 requests
            "rate_limit_window": (1, 3600),  # 1 second to 1 hour
            "session_timeout": (300, 604800),  # 5 minutes to 7 days
            "max_login_attempts": (1, 100),  # 1 to 100 attempts
            "lockout_duration": (60, 86400),  # 1 minute to 1 day
        }

        for field, (min_val, max_val) in numeric_validations.items():
            if not isinstance(validated_data[field], int):
                try:
                    validated_data[field] = int(validated_data[field])
                except (ValueError, TypeError):
                    validated_data[field] = getattr(defaults, field)
            validated_data[field] = max(min_val, min(max_val, validated_data[field]))

        # Validate float fields
        if not isinstance(validated_data["low_similarity_threshold"], float):
            try:
                validated_data["low_similarity_threshold"] = float(validated_data["low_similarity_threshold"])
            except (ValueError, TypeError):
                validated_data["low_similarity_threshold"] = defaults.low_similarity_threshold
        validated_data["low_similarity_threshold"] = max(0.0, min(1.0, validated_data["low_similarity_threshold"]))

        # Validate boolean fields
        bool_fields = [
            "anonymize_ips",
            "enable_query_logging",
            "enable_session_fingerprinting",
            "enable_audit_logging",
            "enable_rate_limiting",
            "enable_input_validation",
            "enable_cors",
            "enable_api_keys",
            "require_https",
        ]
        for bool_field in bool_fields:
            if not isinstance(validated_data[bool_field], bool):
                validated_data[bool_field] = str(validated_data[bool_field]).lower() == "true"

        return cls(**validated_data)

    def to_json(self) -> str:
        """Convert to JSON string for database storage."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "SecuritySettings":
        """Create from JSON string with error handling."""
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning(f"Failed to parse security settings from JSON: {e}")
            return cls()  # Return defaults on error


@dataclass
class SystemSettings:
    """Unified container for all DB-driven runtime settings."""

    followup: "FollowUpSettings" = field(default_factory=lambda: None)  # Import from config.py
    response: ResponseSettings = field(default_factory=ResponseSettings)
    routing: QueryRoutingSettings = field(default_factory=QueryRoutingSettings)
    features: FeatureFlags = field(default_factory=FeatureFlags)
    system_config: SystemConfigurationSettings = field(default_factory=SystemConfigurationSettings)
    security: SecuritySettings = field(default_factory=SecuritySettings)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {}
        if self.followup:
            result["followup"] = self.followup.to_dict()
        result["response"] = self.response.to_dict()
        result["routing"] = self.routing.to_dict()
        result["features"] = self.features.to_dict()
        result["system_config"] = self.system_config.to_dict()
        result["security"] = self.security.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "SystemSettings":
        """Create from dictionary with validation."""
        # Import here to avoid circular import

        followup_data = data.get("followup", {})
        response_data = data.get("response", {})
        routing_data = data.get("routing", {})
        features_data = data.get("features", {})
        system_config_data = data.get("system_config", {})
        security_data = data.get("security", {})

        return cls(
            followup=FollowUpSettings.from_dict(followup_data) if followup_data else FollowUpSettings(),
            response=ResponseSettings.from_dict(response_data),
            routing=QueryRoutingSettings.from_dict(routing_data),
            features=FeatureFlags.from_dict(features_data),
            system_config=SystemConfigurationSettings.from_dict(system_config_data),
            security=SecuritySettings.from_dict(security_data),
        )

    def to_json(self) -> str:
        """Convert to JSON string for database storage."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "SystemSettings":
        """Create from JSON string with error handling."""
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.warning(f"Failed to parse system settings from JSON: {e}")
            return cls()  # Return defaults on error


# Setting key constants
class SettingKeys:
    """Constants for setting keys used in database."""

    FOLLOWUP_SETTINGS = "followup_settings"
    RESPONSE_SETTINGS = "response_settings"
    ROUTING_SETTINGS = "routing_settings"
    FEATURE_FLAGS = "feature_flags"
    SYSTEM_CONFIG_SETTINGS = "system_config_settings"
    SECURITY_SETTINGS = "security_settings"
    SYSTEM_SETTINGS = "system_settings"  # For unified storage (future use)
