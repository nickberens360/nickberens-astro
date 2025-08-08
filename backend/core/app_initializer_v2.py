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
from typing import Dict, Tuple

from langchain_core.retrievers import BaseRetriever
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from .config import AppConfig
from .smart_illustration_service import SmartIllustrationService
from .unified_retriever import UnifiedRetriever

logger = logging.getLogger(__name__)


def initialize_app_state() -> Tuple[Dict[str, BaseRetriever], SmartIllustrationService]:
    """
    Initialize application with unified retriever system.

    No manual configuration needed - automatically discovers and indexes all content!
    """
    logger.info("Initializing application with unified retriever system...")

    # Initialize embeddings
    embeddings = GoogleGenerativeAIEmbeddings(model=AppConfig.EMBEDDING_MODEL)

    # Create unified retriever
    unified_retriever = UnifiedRetriever(embeddings)

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

    # Create backward-compatible retriever dictionary
    # This maintains compatibility with existing code
    all_retrievers = {
        "unified": unified_retriever.get_retriever(),
        # Create virtual retrievers for backward compatibility
        "resume": unified_retriever.get_retriever(filter_content_types=["experience", "skills"]),
        "about": unified_retriever.get_retriever(filter_content_types=["about"]),
        "project": unified_retriever.get_retriever(filter_content_types=["project"]),
        "illustration": unified_retriever.get_retriever(filter_content_types=["creative"]),
        "knowledge": unified_retriever.get_retriever(),  # General knowledge
    }

    # Initialize smart illustration service (no unified_data.json needed!)
    smart_illustration_service = SmartIllustrationService(unified_retriever)

    is_valid, message = smart_illustration_service.validate_data()
    if not is_valid:
        logger.warning(message)
    else:
        logger.info(message)

    # Store unified retriever for direct access if needed
    all_retrievers["_unified_retriever"] = unified_retriever

    return all_retrievers, smart_illustration_service


def get_unified_retriever(all_retrievers: Dict[str, BaseRetriever]) -> UnifiedRetriever:
    """Helper to get the unified retriever instance."""
    return all_retrievers.get("_unified_retriever")
