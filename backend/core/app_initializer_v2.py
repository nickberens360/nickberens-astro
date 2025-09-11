"""
Simplified application initialization with unified retriever.

This module provides a cleaner initialization process that:
- Automatically discovers and indexes all content
- Uses a single, intelligent retriever
- Maintains backward compatibility
- Improves performance through unified indexing
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseLanguageModel
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

from .config import AppConfig
from .settings_manager import get_settings_manager
from .smart_illustration_service import SmartIllustrationService
from .taxonomy_loader import get_topic_taxonomy
from .unified_retriever import UnifiedRetriever

logger = logging.getLogger(__name__)


def create_processing_llm() -> BaseLanguageModel:
    """
    Create the appropriate LLM for background processing operations.

    Uses processing_llm setting - optimized for indexing, reformulation, etc.
    Fallback chain: Database settings → Environment → Fast Claude default
    """
    # Import API key management
    try:
        from .api_key_manager import api_key_manager

        API_KEY_MANAGER_AVAILABLE = True
    except ImportError:
        API_KEY_MANAGER_AVAILABLE = False

    def get_api_key_for_provider(provider_type: str) -> Optional[str]:
        """Get API key for a provider, preferring database over environment."""
        if API_KEY_MANAGER_AVAILABLE:
            try:
                api_key = api_key_manager.get_api_key_by_type(provider_type)
                if api_key:
                    return api_key
            except Exception as e:
                logger.warning(f"Failed to get {provider_type} API key from database: {e}")

        # Fallback to environment
        env_var_map = {"anthropic": "ANTHROPIC_API_KEY", "google": "GOOGLE_API_KEY"}
        env_var = env_var_map.get(provider_type)
        if env_var:
            return os.getenv(env_var)
        return None

    try:
        # Try to get settings from database
        settings_manager = get_settings_manager()
        processing_llm = settings_manager.get_processing_llm()
        processing_model_name = settings_manager.get_processing_model_name()

        if processing_llm == "gemini":
            google_api_key = get_api_key_for_provider("google")

            if google_api_key:
                logger.info(f"Creating Gemini processing LLM: {processing_model_name}")
                return ChatGoogleGenerativeAI(
                    model=processing_model_name, temperature=0.1, timeout=60.0, google_api_key=google_api_key
                )
            else:
                logger.warning("No Google API key found for processing LLM, falling back to Claude")

        # For claude or claude_haiku processing
        if processing_llm in ["claude", "claude_haiku"]:
            anthropic_api_key = get_api_key_for_provider("anthropic")

            if anthropic_api_key:
                logger.info(f"Creating Claude processing LLM: {processing_model_name}")
                return ChatAnthropic(
                    model=processing_model_name, temperature=0.1, timeout=60.0, stop=[], api_key=anthropic_api_key
                )
            else:
                logger.warning("No Anthropic API key found for processing LLM, trying environment fallback")
        else:
            logger.warning(f"Unknown processing LLM in database: {processing_llm}, falling back to fast default")
    except Exception as e:
        logger.debug(f"Could not get processing LLM settings from database: {e}, using fast default")

    # Fallback to fast Claude model for background processing
    logger.info("Creating fast Claude processing LLM from environment: claude-3-haiku-20240307")
    anthropic_key = get_api_key_for_provider("anthropic")
    if anthropic_key:
        return ChatAnthropic(
            model="claude-3-haiku-20240307", temperature=0.1, timeout=60.0, stop=[], api_key=anthropic_key
        )
    else:
        # Last resort - try without explicit API key (may use environment)
        return ChatAnthropic(model="claude-3-haiku-20240307", temperature=0.1, timeout=60.0, stop=[])


def create_response_llm() -> BaseLanguageModel:
    """
    Create the appropriate LLM for user query responses based on database settings.

    Uses response_llm setting - what users see in the chat interface.
    Fallback chain: Database settings → Environment → Default Claude
    """
    # Import API key management
    try:
        from .api_key_manager import api_key_manager

        API_KEY_MANAGER_AVAILABLE = True
    except ImportError:
        API_KEY_MANAGER_AVAILABLE = False

    def get_api_key_for_provider(provider_type: str) -> Optional[str]:
        """Get API key for a provider, preferring database over environment."""
        if API_KEY_MANAGER_AVAILABLE:
            try:
                api_key = api_key_manager.get_api_key_by_type(provider_type)
                if api_key:
                    return api_key
            except Exception as e:
                logger.warning(f"Failed to get {provider_type} API key from database: {e}")

        # Fallback to environment
        env_var_map = {"anthropic": "ANTHROPIC_API_KEY", "google": "GOOGLE_API_KEY"}
        env_var = env_var_map.get(provider_type)
        if env_var:
            return os.getenv(env_var)
        return None

    try:
        # Try to get settings from database
        settings_manager = get_settings_manager()
        response_llm = settings_manager.get_response_llm()
        response_model_name = settings_manager.get_response_model_name()

        if response_llm == "gemini":
            google_api_key = get_api_key_for_provider("google")

            if google_api_key:
                logger.info(f"Creating Gemini response LLM: {response_model_name}")
                return ChatGoogleGenerativeAI(
                    model=response_model_name, temperature=0.1, timeout=60.0, google_api_key=google_api_key
                )
            else:
                logger.warning("No Google API key found, falling back to Claude")

        elif response_llm == "claude":
            anthropic_api_key = get_api_key_for_provider("anthropic")

            if anthropic_api_key:
                logger.info(f"Creating Claude response LLM: {response_model_name}")
                return ChatAnthropic(
                    model=response_model_name, temperature=0.1, timeout=60.0, stop=[], api_key=anthropic_api_key
                )
            else:
                logger.warning("No Anthropic API key found, trying environment fallback")
        else:
            logger.warning(f"Unknown response LLM in database: {response_llm}, falling back to environment")
    except Exception as e:
        logger.debug(f"Could not get LLM settings from database: {e}, using environment fallback")

    # Fallback to environment configuration
    logger.info(f"Creating Claude LLM from environment config: {AppConfig.CLAUDE_MODEL}")
    anthropic_key = get_api_key_for_provider("anthropic")
    if anthropic_key:
        return ChatAnthropic(
            model=AppConfig.CLAUDE_MODEL, temperature=0.1, timeout=60.0, stop=[], api_key=anthropic_key
        )
    else:
        # Last resort - try without explicit API key (may use environment)
        return ChatAnthropic(model=AppConfig.CLAUDE_MODEL, temperature=0.1, timeout=60.0, stop=[])


def initialize_app_state() -> Tuple[Dict[str, Any], SmartIllustrationService, BaseLanguageModel]:
    """
    Initialize application with unified retriever system.

    No manual configuration needed - automatically discovers and indexes all content!

    Returns:
        Tuple[Dict[str, Any], SmartIllustrationService, BaseLanguageModel]:
            - app_state: dict containing 'unified_retriever' and other state
            - illustration_service: SmartIllustrationService for image search
            - llm: BaseLanguageModel for user-facing queries
    """
    logger.info("🚀 Initializing application with unified retriever system...")

    # Log taxonomy status for observability
    try:
        tax = get_topic_taxonomy()
        if tax and isinstance(tax.get("categories"), dict):
            cats = [str(k) for k in tax["categories"].keys()]
            logger.info(
                "📚 Topic taxonomy loaded: %d categories -> %s",
                len(cats),
                ", ".join(cats[:8]) + (" …" if len(cats) > 8 else ""),
            )
        else:
            logger.info("📚 Topic taxonomy not found/invalid; using fallback heuristics")
    except Exception as e:
        logger.warning(f"⚠️ Could not load topic taxonomy: {e}")

    # Ensure logs directory exists during app initialization
    backend_dir = Path(__file__).parent.parent.resolve()
    logs_dir = backend_dir / "logs"
    logs_dir.mkdir(exist_ok=True)

    # Initialize LLMs - database-configured processing LLM for indexing, response LLM for user queries
    indexing_llm = create_processing_llm()
    user_query_llm = create_response_llm()

    # Initialize embeddings
    embeddings = GoogleGenerativeAIEmbeddings(model=AppConfig.EMBEDDING_MODEL)

    # Create unified retriever with Claude Haiku for fast indexing
    unified_retriever = UnifiedRetriever(
        embeddings, indexing_llm, use_fast_classifier=True, classification_mode="hybrid"
    )
    # Respect environment flag for heterogeneity fallback (default OFF)
    try:
        env_flag = os.getenv("ENABLE_HETEROGENEITY_FALLBACK", "false").lower() in ("1", "true", "yes")
        unified_retriever.content_indexer.enable_heterogeneity_fallback = env_flag
        logger.info(f"Heterogeneity fallback enabled: {env_flag}")
    except Exception:
        logger.debug("Could not configure heterogeneity fallback on content indexer")

    # Auto-index all content directories
    directories_to_index = [
        "backend/knowledge",  # Knowledge base documents
        "public",  # JSON data files
        # Add more directories as needed
    ]

    total_files = 0
    total_chunks = 0

    # Check if we should force rebuild
    force_rebuild = os.getenv("FORCE_REBUILD_DATA", "false").lower() == "true"

    # Check for admin-triggered refresh flag
    refresh_flag_file = backend_dir / ".refresh_required"
    if refresh_flag_file.exists():
        logger.info("🔄 Admin refresh flag detected - forcing rebuild")
        force_rebuild = True
        # Remove the flag file after processing
        try:
            refresh_flag_file.unlink()
            logger.info("✅ Admin refresh flag processed and removed")
        except Exception as e:
            logger.warning(f"⚠️ Could not remove refresh flag file: {e}")

    for directory in directories_to_index:
        if os.path.exists(directory):
            files, chunks = unified_retriever.index_directory(directory, force_reindex=force_rebuild)
            total_files += files
            total_chunks += chunks
            logger.info(f"📁 Indexed {directory}: {files} files, {chunks} chunks")

    # Log concise metrics after indexing
    try:
        metrics = unified_retriever.content_indexer.get_metrics()
        logger.info(
            "✅ Total indexed: %d files, %d chunks | LLM file classifications: %d | Per-chunk fallbacks: %d",
            total_files,
            total_chunks,
            metrics.get("llm_classifications_performed", 0),
            metrics.get("llm_classifications_fallback_chunk", 0),
        )
    except Exception:
        logger.info(f"✅ Total indexed: {total_files} files, {total_chunks} chunks")

    # Follow-up pregeneration removed in simplification - using static questions only
    logger.info("⚡ Using static follow-up questions for instant responses")

    # Create retriever dictionary with only the unified retriever
    all_retrievers = {
        "unified": unified_retriever.get_retriever(),
    }

    # Initialize smart illustration service (no unified_data.json needed!)
    smart_illustration_service = SmartIllustrationService(unified_retriever)

    is_valid, message = smart_illustration_service.validate_data()
    if not is_valid:
        logger.warning(f"⚠️ {message}")
    else:
        logger.info(f"✅ {message}")

    # Store unified retriever for direct access if needed
    all_retrievers["_unified_retriever"] = unified_retriever  # type: ignore[assignment]

    # Warmup settings cache during app initialization
    try:
        settings_manager = get_settings_manager()
        settings_manager.warmup_cache()
        logger.info("✅ Settings cache warmed up during app initialization")
    except Exception as e:
        logger.warning(f"⚠️ Failed to warm up settings cache: {e}")

    return all_retrievers, smart_illustration_service, user_query_llm


def get_unified_retriever(all_retrievers: Dict[str, Any]) -> Optional[UnifiedRetriever]:
    """Helper to get the unified retriever instance."""
    return all_retrievers.get("_unified_retriever")
