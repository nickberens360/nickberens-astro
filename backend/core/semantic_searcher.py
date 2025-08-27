"""
Semantic searcher component for handling vector store operations and similarity search.

This module provides focused functionality for:
- Vector store initialization and management
- Semantic similarity search with filtering
- Document retrieval and scoring
- LangChain retriever interface compatibility
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain.docstore.document import Document
from langchain_core.retrievers import BaseRetriever

# Prefer the newer Chroma package
try:
    from langchain_chroma import Chroma
except ImportError:
    # Fallback to community version if new package not available
    from langchain_community.vectorstores import Chroma

from .config import AppConfig

logger = logging.getLogger(__name__)


class SemanticSearcher:
    """Handles vector store operations and semantic similarity search."""

    def __init__(self, embeddings: Any, persist_dir: str = "backend/.unified_chroma"):
        self.embeddings = embeddings
        self.persist_dir = persist_dir
        self.vector_store: Optional[Chroma] = None
        self._initialize_store()

    def _initialize_store(self):
        """Initialize or load the unified vector store."""
        Path(self.persist_dir).mkdir(parents=True, exist_ok=True)
        self.vector_store = Chroma(
            collection_name="unified_knowledge",
            persist_directory=self.persist_dir,
            embedding_function=self.embeddings,
        )

    def add_documents(self, documents: List[Document]) -> None:
        """Add documents to the vector store."""
        if documents and self.vector_store is not None:
            self.vector_store.add_documents(documents)
            logger.info(f"Added {len(documents)} documents to vector store")

    def get_retriever(
        self, search_kwargs: Optional[Dict] = None, filter_content_types: Optional[List[str]] = None
    ) -> BaseRetriever:
        """
        Get a retriever with optional filtering.

        Args:
            search_kwargs: Additional search parameters (e.g., k=5)
            filter_content_types: Filter by content types (e.g., ['technical', 'experience'])
        """
        if search_kwargs is None:
            search_kwargs = {"k": AppConfig.DEFAULT_SEARCH_K}

        # Note: We'll do filtering at retrieval time instead of at the vector store level
        # This is more compatible across different Chroma versions

        if self.vector_store is None:
            raise ValueError("Vector store not initialized")
        return self.vector_store.as_retriever(search_kwargs=search_kwargs)  # type: ignore[no-any-return]

    def get_relevant_documents(
        self, query: str, k: int = None, filter_content_types: Optional[List[str]] = None
    ) -> List[Document]:
        """
        Get relevant documents for a query (compatibility method).

        This method provides compatibility with LangChain's retriever interface.
        """
        return self.semantic_search(query, k, filter_content_types)

    def semantic_search(
        self, query: str, k: int = None, filter_content_types: Optional[List[str]] = None, score_threshold: float = None
    ) -> List[Document]:
        """
        Perform semantic search with optional filtering and scoring.

        Args:
            query: Search query text
            k: Number of results to return (defaults to AppConfig.DEFAULT_SEARCH_K)
            filter_content_types: Optional list of content types to filter by
            score_threshold: Distance threshold for filtering results (defaults to AppConfig.DEFAULT_DISTANCE_THRESHOLD)
                           - ChromaDB returns DISTANCE scores (lower = better similarity)
                           - Typical range: 0.0-2.0 with L2 distance
                           - Use 0.0 for no filtering, 0.5-1.0 for good matches, 1.0+ for broader results

        Returns:
            List of Document objects ranked by similarity (best matches first)
        """
        # Apply defaults from config
        if k is None:
            k = AppConfig.DEFAULT_SEARCH_K
        if score_threshold is None:
            score_threshold = AppConfig.DEFAULT_DISTANCE_THRESHOLD

        # Get more results than needed for filtering and reranking
        search_k = k * AppConfig.SEARCH_EXPANSION_MULTIPLIER

        # Get documents with scores
        if self.vector_store is None:
            raise ValueError("Vector store not initialized")
        docs_and_scores = self.vector_store.similarity_search_with_score(query, k=search_k)

        logger.debug(f"Raw search returned {len(docs_and_scores)} documents")
        if docs_and_scores:
            logger.debug(
                f"Score range: {min(score for _, score in docs_and_scores):.3f} - "
                f"{max(score for _, score in docs_and_scores):.3f}"
            )

        # Filter by distance score threshold
        # IMPORTANT: ChromaDB's similarity_search_with_score returns DISTANCE scores where:
        # - LOWER scores = HIGHER similarity (closer vectors in embedding space)
        # - Typical L2 distance range: 0.0-2.0 (with normalization)
        # - Good matches usually have scores < 1.0
        # - We use <= because we want documents with distance AT OR BELOW the threshold

        if score_threshold == 0.0:
            # Special case: threshold=0.0 means "get all results" (no filtering)
            filtered_docs = [doc for doc, score in docs_and_scores]
        else:
            # Normal case: filter by distance threshold (keep documents with distance <= threshold)
            filtered_docs = [doc for doc, score in docs_and_scores if score <= score_threshold]
        logger.debug(f"After score threshold ({score_threshold}): {len(filtered_docs)} documents")

        # Apply content type filtering if specified
        if filter_content_types:
            content_filtered_docs = []
            for doc in filtered_docs:
                if "content_types" in doc.metadata:
                    doc_content_types = doc.metadata["content_types"].split(",")
                    logger.debug(f"Doc content types: {doc_content_types}, looking for: {filter_content_types}")
                    # Check if any of the document's content types match our filter
                    if any(content_type.strip() in filter_content_types for content_type in doc_content_types):
                        content_filtered_docs.append(doc)
                        logger.debug(f"✅ Match found: {doc_content_types}")
                    else:
                        logger.debug(f"❌ No match: {doc_content_types}")
            filtered_docs = content_filtered_docs
            logger.debug(f"After content type filtering: {len(filtered_docs)} documents")

        # Return top k results
        return filtered_docs[:k]

    def similarity_search_with_score(self, query: str, k: int = None) -> List[tuple]:
        """
        Perform similarity search and return documents with scores.

        Args:
            query: Search query text
            k: Number of results to return

        Returns:
            List of (document, score) tuples
        """
        if k is None:
            k = AppConfig.DEFAULT_SEARCH_K

        if self.vector_store is None:
            raise ValueError("Vector store not initialized")

        return self.vector_store.similarity_search_with_score(query, k=k)

    def get_collection_count(self) -> int:
        """Get the number of documents in the vector store."""
        if self.vector_store is None:
            return 0
        try:
            return self.vector_store._collection.count()
        except Exception as e:
            logger.warning(f"Could not get collection count: {e}")
            return 0

    def get_documents(
        self, where: Optional[Dict[str, Any]] = None, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get documents from the vector store with optional filtering.

        Args:
            where: Optional filter conditions for metadata
            limit: Maximum number of documents to return
            offset: Number of documents to skip (for pagination)

        Returns:
            List of document dictionaries with metadata and content
        """
        if self.vector_store is None:
            raise ValueError("Vector store not initialized")

        try:
            # Use ChromaDB's get() method which is the proper public interface
            collection = self.vector_store._collection
            result = collection.get(where=where, limit=limit, offset=offset, include=["metadatas", "documents", "ids"])

            # Format the results consistently
            documents = []
            for i in range(len(result["ids"])):
                doc = {
                    "id": result["ids"][i],
                    "content": result["documents"][i] if i < len(result["documents"]) else "",
                    "metadata": result["metadatas"][i] if i < len(result["metadatas"]) else {},
                }
                documents.append(doc)

            return documents
        except Exception as e:
            logger.error(f"Error getting documents: {e}")
            return []

    def delete_collection(self) -> None:
        """Delete the vector store collection (for testing/cleanup)."""
        if self.vector_store is not None:
            try:
                self.vector_store.delete_collection()
                logger.info("Vector store collection deleted")
            except Exception as e:
                logger.warning(f"Could not delete collection: {e}")

    def delete_where(self, where: Dict[str, Any]) -> None:
        """Delete documents from the underlying store by metadata filter."""
        if hasattr(self.vector_store, "delete"):
            # LangChain vector stores commonly expose delete(where=...) for Chroma
            try:
                self.vector_store.delete(where=where)  # type: ignore[attr-defined]
                return
            except Exception as e:
                logger.warning("Vector store delete(where=...) failed: %s", e, exc_info=True)
        # ChromaDB collection fallback
        if hasattr(self.vector_store, "_collection"):
            try:
                self.vector_store._collection.delete(where=where)  # type: ignore[attr-defined]
                return
            except Exception as e:
                logger.warning("Chroma _collection.delete failed: %s", e, exc_info=True)
        raise RuntimeError("Delete not supported by current vector store")

    def reset_store(self) -> None:
        """Reset and reinitialize the vector store."""
        self.delete_collection()
        self._initialize_store()
        logger.info("Vector store reset and reinitialized")
