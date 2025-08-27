"""
Unified retriever orchestrator using component-based architecture.

This module provides a clean facade over the specialized components:
- ContentIndexer: File processing and metadata extraction
- SemanticSearcher: Vector store operations and similarity search
- ContentRouter: Query routing and content type detection

The UnifiedRetriever now acts as a coordinator/facade that maintains backward compatibility
while delegating responsibilities to focused components.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from langchain.docstore.document import Document
from langchain_core.language_models import BaseLanguageModel
from langchain_core.retrievers import BaseRetriever

from .content_indexer import ContentIndexer
from .content_router import ContentRouter
from .semantic_searcher import SemanticSearcher

logger = logging.getLogger(__name__)


class UnifiedRetriever:
    """
    Orchestrates content indexing, semantic search, and intelligent routing.

    This class acts as a facade over specialized components, maintaining backward
    compatibility while providing a clean separation of concerns.
    """

    def __init__(self, embeddings: Any, llm: BaseLanguageModel, persist_dir: str = "backend/.unified_chroma"):
        self.embeddings = embeddings
        self.llm = llm
        self.persist_dir = persist_dir

        # Initialize component-based architecture
        self.content_indexer = ContentIndexer(llm, persist_dir)
        self.semantic_searcher = SemanticSearcher(embeddings, persist_dir)
        self.content_router = ContentRouter(self.semantic_searcher)

        logger.info("UnifiedRetriever initialized with component-based architecture")

    def index_directory(self, directory: str, force_reindex: bool = False) -> Tuple[int, int]:
        """
        Automatically discover and index all content in a directory.

        Returns:
            Tuple of (files_indexed, total_chunks)
        """
        logger.info(f"Indexing directory: {directory} (force_reindex={force_reindex})")

        # Process directory using ContentIndexer
        documents, files_processed, total_chunks = self.content_indexer.process_directory(directory, force_reindex)

        # Add processed documents to vector store using SemanticSearcher
        if documents:
            self.semantic_searcher.add_documents(documents)
            logger.info(f"Added {len(documents)} documents to vector store")

        logger.info(f"Indexing complete: {files_processed} files, {total_chunks} chunks")
        return files_processed, total_chunks

    def reindex_file(self, file_path: str) -> bool:
        """
        Reindex a specific file by removing existing entries and re-adding it.

        Args:
            file_path: Path to the file to reindex

        Returns:
            bool: True if reindexing was successful, False otherwise
        """
        try:
            import json
            from pathlib import Path

            from ..ingest.chunking import splitter_for_ext
            from ..ingest.loaders import load_doc

            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                logger.error(f"File does not exist: {file_path}")
                return False

            logger.info(f"Reindexing file: {file_path}")

            # Remove existing documents with this file path from vector store
            if hasattr(self.semantic_searcher.vector_store, "_collection"):
                collection = self.semantic_searcher.vector_store._collection
                # Delete documents with matching source metadata (this is what the loaders set)
                try:
                    collection.delete(where={"source": str(file_path_obj)})
                    logger.info(f"Removed existing entries for: {file_path}")
                except Exception as e:
                    logger.warning(f"Could not remove existing entries: {e}")

            # Process the file like in process_directory
            docs = load_doc(file_path_obj)
            if not docs:
                logger.warning(f"No documents loaded from {file_path}")
                return False

            # Use appropriate splitter based on file type
            splitter = splitter_for_ext(file_path_obj.suffix)
            chunks = splitter.split_documents(docs)

            # Add rich metadata to each chunk
            for chunk in chunks:
                base_metadata = self.content_indexer.extract_content_metadata(chunk, file_path_obj)
                chunk.metadata.update(base_metadata)

            # Add to vector store
            if chunks:
                self.semantic_searcher.add_documents(chunks)
                logger.info(f"Successfully reindexed {file_path}: {len(chunks)} chunks")

                # Update the index metadata to mark as processed
                index_metadata_path = Path(self.persist_dir) / "index_metadata.json"
                indexed_files = {}
                if index_metadata_path.exists():
                    with open(index_metadata_path, "r") as f:
                        indexed_files = json.load(f)

                # Update hash
                file_hash = self.content_indexer.compute_file_hash(file_path_obj)
                indexed_files[str(file_path_obj)] = file_hash

                # Save updated metadata
                Path(self.persist_dir).mkdir(parents=True, exist_ok=True)
                with open(index_metadata_path, "w") as f:
                    json.dump(indexed_files, f)

                return True
            else:
                logger.warning(f"No chunks created from {file_path}")
                return False

        except Exception as e:
            logger.error(f"Failed to reindex file {file_path}: {e}")
            return False

    def get_retriever(
        self, search_kwargs: Optional[Dict[str, Any]] = None, filter_content_types: Optional[List[str]] = None
    ) -> BaseRetriever:
        """
        Get a retriever with optional filtering.

        Args:
            search_kwargs: Additional search parameters (e.g., k=5)
            filter_content_types: Filter by content types (e.g., ['technical', 'experience'])
        """
        return self.semantic_searcher.get_retriever(search_kwargs, filter_content_types)

    def get_relevant_documents(
        self, query: str, k: Optional[int] = None, filter_content_types: Optional[List[str]] = None
    ) -> List[Document]:
        """
        Get relevant documents for a query (compatibility method).

        This method provides compatibility with LangChain's retriever interface.
        """
        return self.semantic_search(query, k, filter_content_types)

    def semantic_search(
        self,
        query: str,
        k: Optional[int] = None,
        filter_content_types: Optional[List[str]] = None,
        score_threshold: Optional[float] = None,
    ) -> List[Document]:
        """
        Perform semantic search with optional filtering and scoring.

        Args:
            query: Search query text
            k: Number of results to return (defaults to AppConfig.DEFAULT_SEARCH_K)
            filter_content_types: Optional list of content types to filter by
            score_threshold: Distance threshold for filtering results (defaults to AppConfig.DEFAULT_DISTANCE_THRESHOLD)

        Returns:
            List of Document objects ranked by similarity (best matches first)
        """
        return self.semantic_searcher.semantic_search(query, k, filter_content_types, score_threshold)

    def auto_route_query(self, query: str) -> List[Document]:
        """
        Automatically route query to the most relevant content.
        No manual configuration needed!

        Uses ContentRouter for intelligent routing based on query analysis.
        """
        return self.content_router.auto_route_query(query)

    def get_search_strategy(self, query: str) -> Dict[str, Any]:
        """
        Get the optimal search strategy for a query.

        Delegates to ContentRouter for strategy determination.
        """
        return self.content_router.get_search_strategy(query)

    def route_with_strategy(self, query: str, custom_strategy: Optional[Dict[str, Any]] = None) -> List[Document]:
        """
        Route query using a specific strategy.

        Delegates to ContentRouter for strategy-based routing.
        """
        return self.content_router.route_with_strategy(query, custom_strategy)

    # Convenience methods for accessing component functionality

    def enhance_chunk_with_context(self, chunk: Document, document_context: str) -> Document:
        """Enhance a document chunk with contextual information."""
        return self.content_indexer.enhance_chunk_with_context(chunk, document_context)

    def generate_document_context(self, documents: List[Document], file_path: Path) -> str:
        """Generate or retrieve cached document context using LLM."""
        return self.content_indexer.generate_document_context(documents, file_path)

    def get_collection_count(self) -> int:
        """Get the number of documents in the vector store."""
        return self.semantic_searcher.get_collection_count()

    def reset_store(self) -> None:
        """Reset and reinitialize the vector store."""
        self.semantic_searcher.reset_store()
        logger.info("UnifiedRetriever vector store reset")

    # Legacy compatibility methods (deprecated but maintained for backward compatibility)

    def _initialize_store(self):
        """Legacy method - now handled by SemanticSearcher."""
        logger.warning("_initialize_store is deprecated - initialization handled automatically")

    def _compute_file_hash(self, file_path: Path) -> str:
        """Legacy method - delegates to ContentIndexer."""
        logger.warning("_compute_file_hash is deprecated - use content_indexer.compute_file_hash")
        return self.content_indexer.compute_file_hash(file_path)

    def _extract_content_metadata(self, doc: Document, file_path: Path) -> Dict:
        """Legacy method - delegates to ContentIndexer."""
        logger.warning("_extract_content_metadata is deprecated - use content_indexer.extract_content_metadata")
        return self.content_indexer.extract_content_metadata(doc, file_path)

    @property
    def vector_store(self):
        """Legacy property access to vector store."""
        return self.semantic_searcher.vector_store

    # Component access for advanced usage

    @property
    def indexer(self) -> ContentIndexer:
        """Access to the content indexer component."""
        return self.content_indexer

    @property
    def searcher(self) -> SemanticSearcher:
        """Access to the semantic searcher component."""
        return self.semantic_searcher

    @property
    def router(self) -> ContentRouter:
        """Access to the content router component."""
        return self.content_router
