"""
Unified retriever system with automatic content discovery and intelligent routing.

This module provides a single, intelligent retriever that automatically:
- Discovers and indexes all content
- Adds rich metadata for filtering
- Routes queries based on semantic similarity
- Maintains performance through smart caching
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from langchain.docstore.document import Document
from langchain_core.retrievers import BaseRetriever

# Prefer the newer Chroma package
try:
    from langchain_chroma import Chroma
except ImportError:
    # Fallback to community version if new package not available
    from langchain_community.vectorstores import Chroma

from ..ingest.chunking import splitter_for_ext
from ..ingest.loaders import load_doc

logger = logging.getLogger(__name__)


from langchain_core.language_models import BaseLanguageModel

from .llm_utils import extract_topics_with_llm


class UnifiedRetriever:
    """A single retriever that intelligently handles all content types."""

    def __init__(self, embeddings: Any, llm: BaseLanguageModel, persist_dir: str = "backend/.unified_chroma"):
        self.embeddings = embeddings
        self.llm = llm
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

    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _extract_content_metadata(self, doc: Document, file_path: Path) -> Dict:
        """Extract intelligent metadata from document content using an LLM."""
        content = doc.page_content

        # Use LLM to extract topics for dynamic content tagging
        content_types = extract_topics_with_llm(self.llm, content)

        # Special handling for illustration JSON files
        is_illustration_data = file_path.name == "illustrations.json"
        illustration_file = None

        if is_illustration_data:
            content_types.append("creative")  # Ensure creative tag for illustrations
            # Extract file name from JSON content for frontend display
            try:
                if "file" in content:
                    # This is an individual illustration entry - parse JSON directly
                    data = json.loads(doc.page_content)
                    if isinstance(data, dict):
                        illustration_file = data.get("file")
            except json.JSONDecodeError:
                logger.warning(f"Could not parse JSON to find illustration file in doc from {file_path.name}")

        metadata = {
            "file_path": str(file_path),
            "file_name": file_path.name,
            "file_type": file_path.suffix.lower(),
            "content_types": ",".join(list(set(content_types))),  # Use set to remove duplicates
            "content_length": len(content),
            "has_code": "```" in doc.page_content or "function" in content.lower(),
            "is_illustration_data": is_illustration_data,
        }

        # Add illustration file path for frontend display
        if illustration_file:
            metadata["illustration_file"] = illustration_file
            metadata["display_path"] = f"/illustrations/{illustration_file}"

        return metadata

    def index_directory(self, directory: str, force_reindex: bool = False) -> Tuple[int, int]:
        """
        Automatically discover and index all content in a directory.

        Returns:
            Tuple of (files_indexed, total_chunks)
        """
        base_path = Path(directory)
        if not base_path.exists():
            logger.warning(f"Directory {directory} does not exist")
            return 0, 0

        # Track indexed files
        index_metadata_path = Path(self.persist_dir) / "index_metadata.json"
        indexed_files = {}

        if index_metadata_path.exists() and not force_reindex:
            with open(index_metadata_path, "r") as f:
                indexed_files = json.load(f)

        files_indexed = 0
        total_chunks = 0

        # Discover all files
        for file_path in base_path.rglob("*"):
            if file_path.is_file() and not file_path.name.startswith("."):
                file_hash = self._compute_file_hash(file_path)

                # Skip if already indexed and unchanged
                if str(file_path) in indexed_files and indexed_files[str(file_path)] == file_hash:
                    continue

                # Load and process the document
                try:
                    docs = load_doc(file_path)
                    if not docs:
                        continue

                    # Use appropriate splitter based on file type
                    splitter = splitter_for_ext(file_path.suffix)
                    chunks = splitter.split_documents(docs)

                    # Add rich metadata to each chunk
                    for chunk in chunks:
                        base_metadata = self._extract_content_metadata(chunk, file_path)
                        chunk.metadata.update(base_metadata)

                    # Add to vector store
                    if chunks and self.vector_store is not None:
                        self.vector_store.add_documents(chunks)
                        files_indexed += 1
                        total_chunks += len(chunks)
                        indexed_files[str(file_path)] = file_hash
                        logger.info(f"Indexed {file_path.name}: {len(chunks)} chunks")

                except Exception as e:
                    logger.error(f"Failed to index {file_path}: {e}")

        # Save index metadata
        with open(index_metadata_path, "w") as f:
            json.dump(indexed_files, f)

        return files_indexed, total_chunks

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
            search_kwargs = {"k": 8}

        # Note: We'll do filtering at retrieval time instead of at the vector store level
        # This is more compatible across different Chroma versions

        if self.vector_store is None:
            raise ValueError("Vector store not initialized")
        return self.vector_store.as_retriever(search_kwargs=search_kwargs)  # type: ignore[no-any-return]

    def semantic_search(
        self, query: str, k: int = 8, filter_content_types: Optional[List[str]] = None, score_threshold: float = 0.5
    ) -> List[Document]:
        """
        Perform semantic search with optional filtering and scoring.
        """
        # Get more results than needed for filtering and reranking
        search_k = k * 3

        # Get documents with scores
        if self.vector_store is None:
            raise ValueError("Vector store not initialized")
        docs_and_scores = self.vector_store.similarity_search_with_score(query, k=search_k)

        # Filter by score threshold
        filtered_docs = [doc for doc, score in docs_and_scores if score >= score_threshold]

        # Apply content type filtering if specified
        if filter_content_types:
            content_filtered_docs = []
            for doc in filtered_docs:
                if "content_types" in doc.metadata:
                    doc_content_types = doc.metadata["content_types"].split(",")
                    # Check if any of the document's content types match our filter
                    if any(content_type.strip() in filter_content_types for content_type in doc_content_types):
                        content_filtered_docs.append(doc)
            filtered_docs = content_filtered_docs

        # Return top k results
        return filtered_docs[:k]

    def auto_route_query(self, query: str) -> List[Document]:
        """
        Automatically route query to the most relevant content.
        No manual configuration needed!
        """
        query_lower = query.lower()

        # Intelligent content type detection based on query
        content_type_hints = []

        if any(term in query_lower for term in ["experience", "work", "job", "role", "company", "resume", "cv"]):
            content_type_hints.append("experience")

        if any(term in query_lower for term in ["skill", "technology", "expertise", "know"]):
            content_type_hints.append("skills")

        if any(term in query_lower for term in ["about", "who", "background", "interest"]):
            content_type_hints.append("about")

        if any(term in query_lower for term in ["illustration", "art", "design", "creative"]):
            content_type_hints.append("creative")

        if any(term in query_lower for term in ["project", "built", "created", "developed"]):
            content_type_hints.append("project")

        # Perform search with intelligent filtering
        if content_type_hints:
            # First try filtered search
            results = self.semantic_search(query, filter_content_types=content_type_hints, score_threshold=0.4)

            # If not enough results, broaden the search
            if len(results) < 4:
                additional_results = self.semantic_search(query, k=8 - len(results), score_threshold=0.5)
                results.extend(additional_results)
        else:
            # No specific type detected, do general search
            results = self.semantic_search(query, score_threshold=0.5)

        return results
