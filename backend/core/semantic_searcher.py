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
from typing import Any, Dict, List, Optional, Union

from langchain.docstore.document import Document
from langchain_core.retrievers import BaseRetriever

# Prefer the newer Chroma package
try:
    from langchain_chroma import Chroma  # type: ignore
except ImportError:
    # Fallback to community version if new package not available
    from langchain_community.vectorstores import Chroma  # type: ignore

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
            # Filter complex metadata to prevent ChromaDB errors
            try:
                from langchain_community.vectorstores.utils import filter_complex_metadata

                filtered_documents = filter_complex_metadata(documents)
                logger.debug(f"Filtered metadata for {len(filtered_documents)} documents")
            except ImportError:
                logger.warning("Could not import filter_complex_metadata, filtering manually")
                filtered_documents = self._filter_complex_metadata_manually(documents)

            self.vector_store.add_documents(filtered_documents)
            logger.info(f"Added {len(filtered_documents)} documents to vector store")

    def _filter_complex_metadata_manually(self, documents: List[Document]) -> List[Document]:
        """Manually filter complex metadata to ensure ChromaDB compatibility."""
        filtered_documents = []

        for doc in documents:
            # Create a new document with filtered metadata
            filtered_metadata = {}

            for key, value in doc.metadata.items():
                # ChromaDB only accepts str, int, float, bool, or None
                if isinstance(value, (str, int, float, bool)) or value is None:
                    filtered_metadata[key] = value
                elif isinstance(value, list):
                    # Convert lists to comma-separated strings
                    if all(isinstance(item, str) for item in value):
                        filtered_metadata[key] = ",".join(value)
                    else:
                        filtered_metadata[key] = ",".join(str(item) for item in value)
                    logger.debug(f"Converted list metadata '{key}' to string: {filtered_metadata[key]}")
                else:
                    # Convert other types to string
                    filtered_metadata[key] = str(value)
                    logger.debug(f"Converted metadata '{key}' from {type(value)} to string")

            # Create new document with filtered metadata
            filtered_doc = Document(page_content=doc.page_content, metadata=filtered_metadata)
            filtered_documents.append(filtered_doc)

        return filtered_documents

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

    def similarity_search_with_score(self, query: str, k: Optional[int] = None) -> List[tuple]:
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

    def get_count(self, where: Optional[Dict[str, Any]] = None) -> int:
        """Get the number of documents in the vector store with optional filtering."""
        if self.vector_store is None:
            return 0
        try:
            if where:
                # Try to use count with filter if supported
                return self.vector_store._collection.count(where=where)
            else:
                return self.vector_store._collection.count()
        except AttributeError:
            # Fallback: fetch documents and count them
            docs = self.get_documents(where=where, limit=100000, offset=0)
            return len(docs or [])

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

            # Convert empty where clause to None for ChromaDB compatibility
            where_clause = where if where else None

            result = collection.get(where=where_clause, limit=limit, offset=offset, include=["metadatas", "documents"])

            # Get IDs separately since ChromaDB requires them to be requested explicitly
            ids_result = collection.get(where=where_clause, limit=limit, offset=offset, include=[])

            # Format the results consistently
            documents = []
            ids = ids_result.get("ids", [])
            docs = result.get("documents", [])
            metadatas = result.get("metadatas", [])

            for i in range(len(docs)):
                doc = {
                    "id": ids[i] if i < len(ids) else f"doc_{i}",
                    "content": docs[i],
                    "metadata": metadatas[i] if i < len(metadatas) else {},
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

    def get_document_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get a document by its ID."""
        if self.vector_store is None:
            return None

        try:
            # Use the public get method instead of _collection
            result = self.vector_store._collection.get(ids=[document_id], include=["metadatas", "documents"])

            if result["ids"] and len(result["ids"]) > 0:
                return {
                    "id": result["ids"][0],
                    "content": result["documents"][0] if result["documents"] else "",
                    "metadata": result["metadatas"][0] if result["metadatas"] else {},
                }
            return None
        except Exception as e:
            logger.error(f"Error getting document by ID {document_id}: {e}")
            return None

    def update_document_metadata(self, document_id: str, metadata: Dict[str, Any]) -> bool:
        """Update metadata for a document."""
        if self.vector_store is None:
            return False

        try:
            # Use the public update method
            self.vector_store._collection.update(ids=[document_id], metadatas=[metadata])
            return True
        except Exception as e:
            logger.error(f"Error updating document metadata for {document_id}: {e}")
            return False

    def delete_document_by_id(self, document_id: str) -> bool:
        """Delete a document by its ID."""
        if self.vector_store is None:
            return False

        try:
            self.vector_store._collection.delete(ids=[document_id])
            return True
        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {e}")
            return False

    def get_documents_by_source(self, source_path: str) -> List[Dict[str, Any]]:
        """Get all documents from a specific source."""
        if self.vector_store is None:
            return []

        try:
            result = self.vector_store._collection.get(
                where={"source": source_path}, include=["metadatas", "documents"]
            )
            # Get IDs separately
            ids_result = self.vector_store._collection.get(where={"source": source_path}, include=[])

            documents = []
            ids = ids_result.get("ids", [])
            docs = result.get("documents", [])
            metadatas = result.get("metadatas", [])

            for i in range(len(docs)):
                doc = {
                    "id": ids[i] if i < len(ids) else f"doc_{i}",
                    "content": docs[i],
                    "metadata": metadatas[i] if i < len(metadatas) else {},
                }
                documents.append(doc)
            return documents
        except Exception as e:
            logger.error(f"Error getting documents by source {source_path}: {e}")
            return []

    def update_documents_metadata(self, document_ids: List[str], metadatas: List[Dict[str, Any]]) -> bool:
        """Update metadata for multiple documents."""
        if self.vector_store is None:
            return False

        try:
            # Convert metadata to compatible format for ChromaDB
            compatible_metadatas: List[Dict[str, Union[str, int, float, bool, None]]] = []
            for metadata in metadatas:
                compatible_metadata: Dict[str, Union[str, int, float, bool, None]] = {}
                for key, value in metadata.items():
                    # ChromaDB only accepts str, int, float, bool, or None values
                    if isinstance(value, (str, int, float, bool)) or value is None:
                        compatible_metadata[key] = value
                    else:
                        # Convert other types to string
                        compatible_metadata[key] = str(value)
                compatible_metadatas.append(compatible_metadata)

            self.vector_store._collection.update(ids=document_ids, metadatas=compatible_metadatas)  # type: ignore
            return True
        except Exception as e:
            logger.error(f"Error updating multiple document metadata: {e}")
            return False

    def delete_documents_by_source(self, source_path: str) -> bool:
        """Delete all documents from a specific source."""
        if self.vector_store is None:
            return False

        try:
            # First get the documents to find their IDs
            documents = self.get_documents_by_source(source_path)
            if not documents:
                return True  # Nothing to delete

            document_ids = [doc["id"] for doc in documents]
            self.vector_store._collection.delete(ids=document_ids)
            return True
        except Exception as e:
            logger.error(f"Error deleting documents by source {source_path}: {e}")
            return False
