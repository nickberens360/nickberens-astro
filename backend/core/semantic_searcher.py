"""
Semantic searcher component for handling vector store operations and similarity search.

This module provides focused functionality for:
- Vector store initialization and management
- Semantic similarity search with filtering
- Document retrieval and scoring
- LangChain retriever interface compatibility
"""

import json
import logging
import os
import shutil
from concurrent.futures import ThreadPoolExecutor, TimeoutError
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

# Chroma error type (optional import, we will fall back to string-matching)
try:
    from chromadb.errors import InternalError as ChromaInternalError  # type: ignore
except Exception:  # pragma: no cover - not present in all environments
    ChromaInternalError = Exception  # type: ignore

from .config import AppConfig

logger = logging.getLogger(__name__)

# Import settings manager for dynamic RAG configuration
try:
    from .settings_manager import get_settings_manager

    SETTINGS_MANAGER_AVAILABLE = True
except ImportError:
    SETTINGS_MANAGER_AVAILABLE = False


class SemanticSearcher:
    """Handles vector store operations and semantic similarity search."""

    def __init__(self, embeddings: Any, persist_dir: str = "backend/.unified_chroma"):
        self.embeddings = embeddings
        self.persist_dir = persist_dir
        self.vector_store: Optional[Chroma] = None
        self._initialize_store()

    @staticmethod
    def _sanitize_metadata(meta: Dict[str, Any]) -> Dict[str, Union[str, int, float, bool, None]]:
        """Sanitize metadata to ensure compatibility with ChromaDB's primitive type requirements.

        ChromaDB only accepts str, int, float, bool, or None as metadata values.
        This method converts complex types (lists, dicts) to JSON strings for robust storage.

        Args:
            meta: Raw metadata dictionary that may contain complex types

        Returns:
            Sanitized metadata dictionary with only primitive types
        """
        compatible: Dict[str, Union[str, int, float, bool, None]] = {}
        for k, v in (meta or {}).items():
            # Allow primitives as-is
            if isinstance(v, (str, int, float, bool)) or v is None:
                compatible[k] = v
                continue
            # Convert lists and dicts to JSON strings for robust storage
            if isinstance(v, (list, dict)):
                compatible[k] = json.dumps(v, ensure_ascii=False)
                continue
            # Fallback for other non-primitive types
            compatible[k] = str(v)
        return compatible

    def _get_rag_config_settings(self):
        """Get RAG configuration settings dynamically from the settings manager."""
        if not SETTINGS_MANAGER_AVAILABLE:
            logger.debug("Settings manager not available, using static config")
            return None

        try:
            settings_manager = get_settings_manager()
            rag_settings = settings_manager.get_rag_config_settings()
            logger.debug(f"Retrieved RAG settings: score_threshold={rag_settings.rag_score_threshold}")
            return rag_settings
        except Exception as e:
            logger.warning(f"Failed to get RAG settings, falling back to static config: {e}")
            return None

    def _get_search_retrieval_settings(self):
        """Get SearchRetrievalSettings dynamically (max results, timeout, fuzzy toggles, etc.)."""
        if not SETTINGS_MANAGER_AVAILABLE:
            return None
        try:
            from .settings_manager import get_settings_manager

            settings_manager = get_settings_manager()
            return settings_manager.get_search_retrieval_settings()
        except Exception as e:
            logger.debug(f"Failed to get search retrieval settings: {e}")
            return None

    def _initialize_store(self):
        """Initialize or load the unified vector store."""
        Path(self.persist_dir).mkdir(parents=True, exist_ok=True)
        self.vector_store = Chroma(
            collection_name="unified_knowledge",
            persist_directory=self.persist_dir,
            embedding_function=self.embeddings,
        )

    def _reset_store(self) -> None:
        """Safely reset the persistent vector store directory and reinitialize."""
        try:
            persist_path = Path(self.persist_dir)
            # Safety check: ensure we only ever delete within the project tree
            if persist_path.is_dir() and str(persist_path).startswith("backend/"):
                shutil.rmtree(persist_path, ignore_errors=True)
                logger.warning(f"Resetting Chroma vector store due to corruption at {persist_path}")
            Path(self.persist_dir).mkdir(parents=True, exist_ok=True)
            self._initialize_store()
        except Exception as e:
            logger.error(f"Failed to reset vector store: {e}")
            raise

    def add_documents(self, documents: List[Document]) -> None:
        """Add documents to the vector store."""
        if not documents or self.vector_store is None:
            return
        try:
            # Chroma only accepts primitive metadata types. Sanitize before upsert.
            sanitized_docs: List[Document] = []
            for doc in documents:
                sanitized_meta = self._sanitize_metadata(doc.metadata)
                # Reuse the same content, replace metadata with sanitized version
                sanitized_docs.append(Document(page_content=doc.page_content, metadata=sanitized_meta))

            self.vector_store.add_documents(sanitized_docs)
            logger.info(f"Added {len(documents)} documents to vector store")
        except Exception as e:
            # Detect malformed underlying DB and auto-recover when allowed
            message = str(e).lower()
            force_rebuild = os.getenv("FORCE_REBUILD_DATA", "false").lower() in {"1", "true", "yes"}
            is_malformed = "database disk image is malformed" in message or "is malformed" in message
            if (isinstance(e, ChromaInternalError) and is_malformed) or (is_malformed and force_rebuild):
                logger.error(f"Chroma store appears corrupted: {e}. Force rebuild: {force_rebuild}")
                if force_rebuild:
                    # Reset the store and retry once
                    self._reset_store()
                    self.vector_store.add_documents(documents)
                    logger.info(f"Recovered vector store and added {len(documents)} documents after reset")
                    return
            # If not recoverable, re-raise
            raise

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
        return self.semantic_search(query=query, k=k, filter_content_types=filter_content_types)

    def semantic_search(
        self,
        query: str,
        k: int = None,
        filter_content_types: Optional[List[str]] = None,
        score_threshold: float = None,
        use_mmr: bool = None,
    ) -> List[Document]:
        """
        Perform semantic search with optional filtering and scoring.

        Args:
            query: Search query text
            k: Number of results to return (defaults to AppConfig.DEFAULT_SEARCH_K)
            filter_content_types: Optional list of content types to filter by
            score_threshold: Distance threshold for filtering results (defaults to AppConfig.DEFAULT_DISTANCE_THRESHOLD)
            use_mmr: Whether to use MMR (Maximum Marginal Relevance) for diversity (defaults to AppConfig.RAG_USE_MMR)
                           - ChromaDB returns DISTANCE scores (lower = better similarity)
                           - Typical range: 0.0-2.0 with L2 distance
                           - Use 0.0 for no filtering, 0.5-1.0 for good matches, 1.0+ for broader results

        Returns:
            List of Document objects ranked by similarity (best matches first)
        """
        # Apply defaults from config (with dynamic RAG settings support)
        rag_settings = self._get_rag_config_settings()
        sr_settings = self._get_search_retrieval_settings()

        # Derive desired number of results from SearchRetrievalSettings.max_search_results when available
        if k is None:
            if sr_settings and getattr(sr_settings, "max_search_results", None):
                k = int(sr_settings.max_search_results)
            else:
                k = AppConfig.DEFAULT_SEARCH_K
        if score_threshold is None:
            if rag_settings:
                score_threshold = rag_settings.rag_score_threshold
                logger.debug(f"Using dynamic score threshold: {score_threshold}")
            else:
                score_threshold = AppConfig.DEFAULT_DISTANCE_THRESHOLD
        if use_mmr is None:
            if rag_settings:
                use_mmr = rag_settings.rag_use_mmr
                logger.debug(f"Using dynamic MMR setting: {use_mmr}")
            else:
                use_mmr = AppConfig.RAG_USE_MMR

        # Get more results than needed for filtering and reranking
        search_k = k * AppConfig.SEARCH_EXPANSION_MULTIPLIER

        # Get documents with scores
        if self.vector_store is None:
            raise ValueError("Vector store not initialized")

        def _run_retrieval() -> List[tuple[Document, float]]:
            # Perform search with MMR or standard similarity search
            if use_mmr:
                try:
                    # Use MMR search for diversity (with dynamic settings support)
                    if rag_settings:
                        fetch_k = max(search_k, rag_settings.rag_mmr_fetch_k)
                        lambda_mult = rag_settings.rag_mmr_lambda_mult
                        logger.debug(f"Using dynamic MMR params: fetch_k={fetch_k}, lambda_mult={lambda_mult}")
                    else:
                        fetch_k = max(search_k, AppConfig.RAG_MMR_FETCH_K)
                        lambda_mult = AppConfig.RAG_MMR_LAMBDA_MULT

                    docs = self.vector_store.max_marginal_relevance_search(
                        query, k=search_k, fetch_k=fetch_k, lambda_mult=lambda_mult
                    )
                    # Convert to docs_and_scores format for consistent processing
                    return [(doc, 0.0) for doc in docs]  # MMR doesn't return scores
                except Exception as e:
                    logger.warning(f"MMR search failed, falling back to similarity search: {e}")
                    return self.vector_store.similarity_search_with_score(query, k=search_k)
            else:
                # Standard similarity search
                return self.vector_store.similarity_search_with_score(query, k=search_k)

        # Enforce retrieval timeout if configured
        docs_and_scores: List[tuple[Document, float]] = []
        timeout_seconds: Optional[int] = None
        if sr_settings and getattr(sr_settings, "search_timeout_seconds", None):
            timeout_seconds = int(sr_settings.search_timeout_seconds)

        if timeout_seconds and timeout_seconds > 0:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_run_retrieval)
                try:
                    docs_and_scores = future.result(timeout=timeout_seconds)
                except TimeoutError:
                    logger.warning(f"Semantic search timed out after {timeout_seconds}s; returning empty results")
                    docs_and_scores = []
                except Exception as e:
                    logger.error(f"Semantic search failed: {e}")
                    docs_and_scores = []
        else:
            docs_and_scores = _run_retrieval()

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

        # Apply additional post-filter by semantic similarity threshold if provided
        # (convert distance to pseudo-similarity)
        # We map distance d to similarity s = 1 / (1 + d), ensuring s in (0,1].
        try:
            if sr_settings and getattr(sr_settings, "semantic_similarity_threshold", None) is not None:
                sim_thr = float(sr_settings.semantic_similarity_threshold)
                if sim_thr > 0.0:

                    def _sim_from_distance(d: float) -> float:
                        try:
                            return 1.0 / (1.0 + float(d))
                        except Exception:
                            return 0.0

                    # Recompute docs_and_scores to include distance for filtering
                    if score_threshold == 0.0:
                        # We didn't keep scores when MMR path used; rebuild with similarity_search_with_score if needed
                        # Only if we have no scores at all
                        if use_mmr and self.vector_store is not None and filtered_docs:
                            # Skip re-query to avoid extra cost; approximate by keeping filtered_docs
                            pass
                        else:
                            pass
                    filtered_docs = [doc for (doc, dist) in docs_and_scores if _sim_from_distance(dist) >= sim_thr]
        except Exception as e:
            logger.debug(f"Similarity post-filter skipped: {e}")

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
                # ChromaDB count doesn't support where parameter in current version
                # Fetch only IDs for efficiency
                results = self.vector_store._collection.get(where=where, include=["ids"])
                ids = results.get("ids", []) if isinstance(results, dict) else getattr(results, "ids", [])
                return len(ids)
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
            # Use the standardized sanitization for consistent metadata handling
            sanitized_metadata = self._sanitize_metadata(metadata)
            self.vector_store._collection.update(ids=[document_id], metadatas=[sanitized_metadata])
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
            # Use the standardized sanitization for consistent metadata handling
            compatible_metadatas = [self._sanitize_metadata(metadata) for metadata in metadatas]
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
