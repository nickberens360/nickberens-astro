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

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from ..scripts.build_unified_data import build_unified_data
from .config import AppConfig
from .data_loader import load_all_documents
from .illustration_service import IllustrationService
from .llm_chain import create_multi_vector_retriever

logger = logging.getLogger(__name__)


def initialize_app_state():
    """
    Initialize application state with Multi-Vector RAG.

    Returns:
        tuple: (all_retrievers, illustration_service) - The initialized retrievers and illustration service
    """
    # Check if we should force rebuild data sources
    force_rebuild = os.getenv("FORCE_REBUILD_DATA", "false").lower() == "true"

    if force_rebuild:
        logger.info("Force rebuild enabled via FORCE_REBUILD_DATA environment variable")

    logger.info("Checking for data source modifications...")
    build_unified_data(force_rebuild=force_rebuild)
    logger.info("Initializing application state with Multi-Vector RAG...")
    docs, illustrations_data = load_all_documents()
    embeddings = GoogleGenerativeAIEmbeddings(model=AppConfig.EMBEDDING_MODEL)
    all_retrievers = create_multi_vector_retriever(docs, embeddings)
    illustration_service = IllustrationService(all_retrievers.get("illustration"), illustrations_data)
    is_valid, message = illustration_service.validate_data()
    if not is_valid:
        logger.warning(message)
    else:
        logger.info(message)
    return all_retrievers, illustration_service
