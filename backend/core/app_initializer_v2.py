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
from typing import Any, Dict, Optional, Tuple

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseLanguageModel
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from .config import AppConfig
from .smart_illustration_service import SmartIllustrationService
from .unified_retriever import UnifiedRetriever

logger = logging.getLogger(__name__)


def initialize_app_state() -> Tuple[Dict[str, Any], SmartIllustrationService, BaseLanguageModel]:
    """
    Initialize application with unified retriever system.

    No manual configuration needed - automatically discovers and indexes all content!
    """
    logger.info("Initializing application with unified retriever system...")

    # Initialize LLMs - Claude Haiku for fast indexing, Claude Sonnet for user queries
    indexing_llm = ChatAnthropic(model="claude-3-haiku-20240307", temperature=0.1)
    user_query_llm = ChatAnthropic(model=AppConfig.CLAUDE_MODEL, temperature=0.1)

    # Initialize embeddings
    embeddings = GoogleGenerativeAIEmbeddings(model=AppConfig.EMBEDDING_MODEL)

    # Create unified retriever with Gemini for fast indexing
    unified_retriever = UnifiedRetriever(embeddings, indexing_llm)

    # Auto-index all content directories
    directories_to_index = [
        "backend/knowledge",  # Knowledge base documents
        "public",  # JSON data files
        # Add more directories as needed
    ]

    total_files = 0
    total_chunks = 0

    for directory in directories_to_index:
        if os.path.exists(directory):
            files, chunks = unified_retriever.index_directory(directory)
            total_files += files
            total_chunks += chunks
            logger.info(f"Indexed {directory}: {files} files, {chunks} chunks")

    logger.info(f"Total indexed: {total_files} files, {total_chunks} chunks")

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
