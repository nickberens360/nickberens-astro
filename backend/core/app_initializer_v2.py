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
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from .config import AppConfig
from .settings_manager import get_settings_manager
from .smart_illustration_service import SmartIllustrationService
from .unified_retriever import UnifiedRetriever

logger = logging.getLogger(__name__)


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

    # Ensure logs directory exists during app initialization
    backend_dir = Path(__file__).parent.parent.resolve()
    logs_dir = backend_dir / "logs"
    logs_dir.mkdir(exist_ok=True)

    # Initialize LLMs - Claude Haiku for fast indexing, configurable Claude model for user queries
    indexing_llm = ChatAnthropic(model_name="claude-3-haiku-20240307", temperature=0.1, timeout=60.0, stop=[])
    user_query_llm = ChatAnthropic(model_name=AppConfig.CLAUDE_MODEL, temperature=0.1, timeout=60.0, stop=[])

    # Initialize embeddings
    embeddings = GoogleGenerativeAIEmbeddings(model=AppConfig.EMBEDDING_MODEL)

    # Create unified retriever with Claude Haiku for fast indexing
    unified_retriever = UnifiedRetriever(embeddings, indexing_llm)

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
