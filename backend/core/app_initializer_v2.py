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
from .followup_pregeneration import FollowupPreGenerator
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
    logger.info("Initializing application with unified retriever system...")

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

    for directory in directories_to_index:
        if os.path.exists(directory):
            files, chunks = unified_retriever.index_directory(directory, force_reindex=force_rebuild)
            total_files += files
            total_chunks += chunks
            logger.info(f"Indexed {directory}: {files} files, {chunks} chunks")

    logger.info(f"Total indexed: {total_files} files, {total_chunks} chunks")

    # Pre-generate follow-up questions based on indexed content (configurable)
    if AppConfig.ENABLE_FOLLOWUP_PREGENERATION:
        logger.info("Pre-generating follow-up questions...")
        followup_pregenerator = FollowupPreGenerator(indexing_llm)
        pregenerated_questions = followup_pregenerator.analyze_and_generate(unified_retriever)

        question_count = sum(len(qs) for qs in pregenerated_questions.values())
        logger.info(f"Pre-generated {question_count} follow-up questions for instant responses")
    else:
        logger.info("Follow-up pregeneration disabled - skipping to reduce cold-start time")

    # Create retriever dictionary with only the unified retriever
    all_retrievers = {
        "unified": unified_retriever.get_retriever(),
    }

    # Initialize smart illustration service (no unified_data.json needed!)
    smart_illustration_service = SmartIllustrationService(unified_retriever)

    is_valid, message = smart_illustration_service.validate_data()
    if not is_valid:
        logger.warning(message)
    else:
        logger.info(message)

    # Store unified retriever for direct access if needed
    all_retrievers["_unified_retriever"] = unified_retriever  # type: ignore[assignment]

    return all_retrievers, smart_illustration_service, user_query_llm


def get_unified_retriever(all_retrievers: Dict[str, Any]) -> Optional[UnifiedRetriever]:
    """Helper to get the unified retriever instance."""
    return all_retrievers.get("_unified_retriever")
