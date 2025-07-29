"""
Application initialization module.

This module handles the initialization of the application state, including:
- Building unified data files
- Loading documents and illustrations
- Creating multi-vector retrievers
- Setting up the illustration service
"""

import logging
import os
from typing import Optional, Tuple

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from ..scripts.build_unified_data import build_unified_data, should_rebuild_unified_data
from .config import AppConfig
from .data_loader import load_all_documents
from .illustration_service import IllustrationService
from .llm_chain import create_multi_vector_retriever

logger = logging.getLogger(__name__)


def initialize_app_state() -> Tuple[Optional[dict], Optional[IllustrationService]]:
    """
    Initialize application state with Multi-Vector RAG.

    Returns:
        tuple: (all_retrievers, illustration_service) - The initialized retrievers and illustration service
               Returns (None, None) if Google credentials are not available
    """
    # Only rebuild if necessary
    if should_rebuild_unified_data():
        logger.info("Data sources have changed. Building structured unified data file...")
        build_unified_data()
    else:
        logger.info("Unified data is up to date. Skipping rebuild.")

    logger.info("Initializing application state with Multi-Vector RAG...")

    # Check for Google API key
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        logger.error("GOOGLE_API_KEY environment variable not found. Cannot initialize embeddings.")
        logger.error("Please set GOOGLE_API_KEY in your .env file to use Google Generative AI embeddings.")
        return None, None

    try:
        docs, illustrations_data = load_all_documents()
        embeddings = GoogleGenerativeAIEmbeddings(model=AppConfig.EMBEDDING_MODEL, google_api_key=google_api_key)
        all_retrievers = create_multi_vector_retriever(docs, embeddings)
        illustration_service = IllustrationService(all_retrievers.get("illustration"), illustrations_data)
        is_valid, message = illustration_service.validate_data()
        if not is_valid:
            logger.warning(message)
        else:
            logger.info(message)
        return all_retrievers, illustration_service
    except Exception as e:
        logger.error(f"Failed to initialize embeddings with Google API: {e}")
        logger.error("Please check your GOOGLE_API_KEY and ensure it has the necessary permissions.")
        return None, None
