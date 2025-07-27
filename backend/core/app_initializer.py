"""
Application initialization module.

This module handles the initialization of the application state, including:
- Building unified data files
- Loading documents and illustrations
- Creating multi-vector retrievers
- Setting up the illustration service
"""

import logging

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
    logger.info("Building structured unified data file...")
    build_unified_data()
    logger.info("Initializing application state with Multi-Vector RAG...")
    docs, illustrations_data = load_all_documents()
    embeddings = GoogleGenerativeAIEmbeddings(model=AppConfig.EMBEDDING_MODEL)
    all_retrievers = create_multi_vector_retriever(docs, embeddings)
    illustration_service = IllustrationService(all_retrievers.get("illustration"), illustrations_data)
    is_valid, message = illustration_service.validate_data()
    logger.info(message)
    return all_retrievers, illustration_service
