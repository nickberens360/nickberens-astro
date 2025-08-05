"""
Application initialization module.

This module handles the initialization of the application state, including:
- Building unified data files
- Loading documents and illustrations
- Creating multi-vector retrievers
- Setting up the illustration service
- Pre-loading common queries into cache
"""

import asyncio
import logging

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from ..scripts.build_unified_data import build_unified_data
from .cache_preloader import CachePreloader
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
    logger.info("Checking for data source modifications...")
    build_unified_data()
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

    # Pre-load common queries into cache
    logger.info("Pre-loading common queries into cache...")
    try:
        asyncio.create_task(CachePreloader.preload_query_cache(all_retrievers))
        logger.info("Cache pre-loading task started")
    except Exception as e:
        logger.warning(f"Failed to start cache pre-loading: {e}")

    return all_retrievers, illustration_service
