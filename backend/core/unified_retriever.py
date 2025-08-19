"""
Unified retriever system with automatic content discovery and intelligent routing.

This module provides a single, intelligent retriever that automatically:
- Discovers and indexes all content
- Adds rich metadata for filtering
- Routes queries based on semantic similarity
- Maintains performance through smart caching
"""

import asyncio
import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from langchain.docstore.document import Document

# Use the newer langchain_chroma package
from langchain_chroma import Chroma
from langchain_core.language_models import BaseLanguageModel
from langchain_core.retrievers import BaseRetriever

from ..ingest.chunking import splitter_for_ext
from ..ingest.loaders import load_doc
from .llm_utils import extract_topics_with_llm, generate_document_context

logger = logging.getLogger(__name__)


class UnifiedRetriever:
    """A single retriever that intelligently handles all content types."""

    def __init__(self, embeddings: Any, llm: BaseLanguageModel, persist_dir: str = "backend/.unified_chroma"):
        self.embeddings = embeddings
        self.llm = llm
        self.persist_dir = persist_dir
        self.vector_store: Optional[Chroma] = None
        self._document_contexts: Dict[str, str] = {}  # Cache for document contexts

        # Enhanced caching system
        self._retrieval_cache: Dict[str, Dict[str, Any]] = {}  # Cache for retrieval results
        self._embedding_cache: Dict[str, List[float]] = {}  # Cache for embeddings
        self._cache_ttl = 3600  # 1 hour cache TTL
        self._max_cache_size = 1000  # Maximum cache entries

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
        """Extract metadata using LLM topics plus deterministic fallbacks.

        Heuristics ensure key content remains discoverable even if LLM topic extraction fails.
        """
        content = doc.page_content

        # Use LLM to extract topics for dynamic content tagging (may fallback to ["general"])
        content_types = extract_topics_with_llm(self.llm, content)

        # Deterministic heuristics
        fname = file_path.name.lower()
        text_lc = content.lower()
        heuristic_tags: List[str] = []

        # Filename-based tags
        if "about" in fname:
            heuristic_tags.append("about")
        if "resume" in fname:
            heuristic_tags.extend(["experience", "skills"])
        if "project" in fname:
            heuristic_tags.append("project")
        if "illustration" in fname or "illustrations" in fname:
            heuristic_tags.append("creative")

        # Content keyword-based tags (covers queries like "artistic inspiration")
        creative_keywords = [
            "art",
            "artistic",
            "inspiration",
            "illustration",
            "illustrations",
            "design",
            "creative",
            "cartoon",
            "cartoons",
        ]
        if any(k in text_lc for k in creative_keywords):
            heuristic_tags.append("creative")

        about_keywords = ["about", "background", "bio", "who is nick", "who am i"]
        if any(k in text_lc for k in about_keywords):
            heuristic_tags.append("about")

        # Special handling for illustration JSON files
        is_illustration_data = file_path.name == "illustrations.json"
        illustration_file = None

        if is_illustration_data:
            heuristic_tags.append("creative")  # Ensure creative tag for illustrations
            # Extract file name from JSON content for frontend display
            try:
                if '"file"' in doc.page_content:
                    data = json.loads(doc.page_content)
                    if isinstance(data, dict) and "file" in data:
                        illustration_file = data.get("file")
                        logger.info(f"Found illustration file: {illustration_file}")
            except json.JSONDecodeError:
                logger.warning(f"Could not parse JSON to find illustration file in doc from {file_path.name}")

        # Merge, dedupe, normalize
        merged_types = sorted({t.strip().lower() for t in (content_types + heuristic_tags) if t and t.strip()})

        metadata = {
            "file_path": str(file_path),
            "file_name": file_path.name,
            "file_type": file_path.suffix.lower(),
            "content_types": ",".join(merged_types),
            "content_length": len(content),
            "has_code": "```" in doc.page_content or "function" in text_lc,
            "is_illustration_data": is_illustration_data,
        }

        # Add illustration file path for frontend display
        if illustration_file:
            metadata["illustration_file"] = illustration_file
            metadata["display_path"] = f"/illustrations/{illustration_file}"

        return metadata

    def _generate_document_context(self, docs: List[Document], file_path: Path) -> str:
        """
        Generate or retrieve cached document context for contextual retrieval.

        This creates a brief summary of the document that will be prepended to each chunk
        to provide better context during retrieval.
        """
        file_key = str(file_path)

        # Check cache first
        if file_key in self._document_contexts:
            return self._document_contexts[file_key]

        # Combine all document content for context generation
        full_content = "\n\n".join([doc.page_content for doc in docs])

        # Generate context using LLM
        context = generate_document_context(self.llm, full_content, file_path.name, file_path.suffix)

        # Cache the context
        self._document_contexts[file_key] = context
        logger.info(f"Generated document context for {file_path.name}: {context[:100]}...")

        return context

    def _enhance_chunk_with_context(self, chunk: Document, document_context: str) -> Document:
        """
        Enhance a chunk by prepending document context for better retrieval.

        This is a key part of contextual retrieval - each chunk gets the document's
        context prepended so it can be found more accurately during search.
        """
        # Create enhanced content with document context
        enhanced_content = f"DOCUMENT CONTEXT: {document_context}\n\nCONTENT: {chunk.page_content}"

        # Create new document with enhanced content but preserve all metadata
        enhanced_chunk = Document(
            page_content=enhanced_content,
            metadata={
                **chunk.metadata,
                "has_document_context": True,
                "original_content_length": len(chunk.page_content),
                "document_context": document_context,
            },
        )

        return enhanced_chunk

    def _generate_cache_key(
        self, query: str, k: int, filter_content_types: Optional[List[str]], score_threshold: float
    ) -> str:
        """Generate a cache key for retrieval results."""
        filter_str = ",".join(sorted(filter_content_types)) if filter_content_types else ""
        cache_input = f"{query}:{k}:{filter_str}:{score_threshold}"
        return hashlib.sha256(cache_input.encode()).hexdigest()[:16]

    def _is_cache_valid(self, cache_entry: Dict[str, Any]) -> bool:
        """Check if a cache entry is still valid."""
        return bool(time.time() - cache_entry["timestamp"] < self._cache_ttl)

    def _cleanup_cache(self, cache_dict: Dict[str, Any]) -> None:
        """Remove expired entries and enforce size limits."""
        current_time = time.time()

        # Remove expired entries
        expired_keys = [key for key, value in cache_dict.items() if current_time - value["timestamp"] > self._cache_ttl]
        for key in expired_keys:
            del cache_dict[key]

        # Enforce size limits (LRU eviction)
        if len(cache_dict) > self._max_cache_size:
            # Sort by timestamp and remove oldest entries
            sorted_items = sorted(cache_dict.items(), key=lambda x: x[1]["timestamp"])
            items_to_remove = len(cache_dict) - self._max_cache_size + 10  # Remove extra for breathing room

            for i in range(items_to_remove):
                del cache_dict[sorted_items[i][0]]

    async def _get_embedding_async(self, text: str) -> List[float]:
        """Get embedding for text with caching and async support."""
        # Check embedding cache first
        cache_key = hashlib.sha256(text.encode()).hexdigest()[:16]

        if cache_key in self._embedding_cache:
            logger.debug(f"Embedding cache hit for key: {cache_key}")
            return self._embedding_cache[cache_key]

        # Generate embedding asynchronously if possible
        try:
            if hasattr(self.embeddings, "aembed_query"):
                # Use async embedding if available
                embedding = await self.embeddings.aembed_query(text)
                logger.debug("Generated embedding using async method")
            elif hasattr(self.embeddings, "embed_query"):
                # Fallback to sync embedding in executor to avoid blocking
                loop = asyncio.get_event_loop()
                embedding = await loop.run_in_executor(None, self.embeddings.embed_query, text)
                logger.debug("Generated embedding using sync method in executor")
            else:
                raise ValueError("Embeddings object has no embed_query method")

            # Cache the result
            self._cleanup_cache(self._embedding_cache)
            self._embedding_cache[cache_key] = embedding
            logger.debug(f"Cached embedding for key: {cache_key}")

            return list(embedding) if embedding else []

        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise

    async def semantic_search_async(
        self, query: str, k: int = 8, filter_content_types: Optional[List[str]] = None, score_threshold: float = 0.5
    ) -> List[Document]:
        """
        Async version of semantic search with enhanced caching.
        """
        import logging

        logger = logging.getLogger(__name__)

        # Generate cache key for retrieval results
        cache_key = self._generate_cache_key(query, k, filter_content_types, score_threshold)

        # Check retrieval cache first
        if cache_key in self._retrieval_cache and self._is_cache_valid(self._retrieval_cache[cache_key]):
            logger.info(f"Retrieval cache hit for key: {cache_key}")
            cached_docs = self._retrieval_cache[cache_key]["documents"]
            return list(cached_docs) if isinstance(cached_docs, list) else []

        logger.debug(f"Retrieval cache miss for key: {cache_key}")

        # Get more results than needed for filtering and reranking
        search_k = k * 3

        if self.vector_store is None:
            raise ValueError("Vector store not initialized")

        # Perform the search asynchronously using executor
        # This prevents blocking the event loop with the synchronous ChromaDB call
        loop = asyncio.get_event_loop()
        docs_and_scores = await loop.run_in_executor(
            None, self.vector_store.similarity_search_with_score, query, search_k
        )

        logger.info(f"Async raw search returned {len(docs_and_scores)} documents for query: '{query[:50]}...'")
        if docs_and_scores:
            score_min = min(score for _, score in docs_and_scores)
            score_max = max(score for _, score in docs_and_scores)
            logger.info(f"Async score range: {score_min:.3f} - {score_max:.3f} (threshold: {score_threshold})")

        # Filter by similarity score threshold
        filtered_docs = [doc for doc, score in docs_and_scores if score <= score_threshold]
        logger.info(
            f"Async: After score threshold ({score_threshold}): {len(filtered_docs)} documents from {len(docs_and_scores)} raw results"
        )

        # Apply content type filtering if specified
        if filter_content_types:
            content_filtered_docs = []
            for doc in filtered_docs:
                if "content_types" in doc.metadata:
                    doc_content_types = doc.metadata["content_types"].split(",")
                    if any(content_type.strip() in filter_content_types for content_type in doc_content_types):
                        content_filtered_docs.append(doc)
            filtered_docs = content_filtered_docs
            logger.debug(f"After content type filtering: {len(filtered_docs)} documents")

        # Return top k results
        final_docs = filtered_docs[:k]

        # Cache the results
        self._cleanup_cache(self._retrieval_cache)
        self._retrieval_cache[cache_key] = {"documents": final_docs, "timestamp": time.time()}
        logger.debug(f"Cached {len(final_docs)} documents for key: {cache_key}")

        return final_docs

    def _should_index_file(self, file_path: Path) -> bool:
        """Check if a file should be indexed based on its name and type."""
        # Skip system/config files that aren't content
        skip_files = {"robots.txt", "sitemap.xml", ".htaccess", "favicon.ico", "manifest.json"}

        if file_path.name.lower() in skip_files:
            logger.debug(f"Skipping system file: {file_path}")
            return False

        return True

    def _should_skip_file(
        self, file_path: Path, file_hash: str, indexed_files: Dict[str, str], force_reindex: bool
    ) -> bool:
        """Check if a file should be skipped during indexing."""
        return str(file_path) in indexed_files and indexed_files[str(file_path)] == file_hash and not force_reindex

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
            if file_path.is_file() and not file_path.name.startswith(".") and self._should_index_file(file_path):
                logger.info(f"Processing file: {file_path}")
                file_hash = self._compute_file_hash(file_path)

                # Skip if already indexed and unchanged
                should_skip = self._should_skip_file(file_path, file_hash, indexed_files, force_reindex)
                if should_skip:
                    logger.info(f"Skipping {file_path} - already indexed (force_reindex={force_reindex})")
                    continue
                else:
                    logger.info(f"Will process {file_path} (force_reindex={force_reindex})")

                # Load and process the document
                try:
                    docs = load_doc(file_path)
                    if not docs:
                        logger.info(f"No documents loaded from {file_path}")
                        continue

                    # Generate document context for contextual retrieval
                    document_context = self._generate_document_context(docs, file_path)

                    # Use appropriate splitter based on file type
                    splitter = splitter_for_ext(file_path.suffix)
                    chunks = splitter.split_documents(docs)

                    # Enhanced chunks with document context and metadata
                    enhanced_chunks = []
                    for chunk in chunks:
                        # Add rich metadata to each chunk
                        base_metadata = self._extract_content_metadata(chunk, file_path)
                        chunk.metadata.update(base_metadata)

                        # Enhance chunk with document context for better retrieval
                        enhanced_chunk = self._enhance_chunk_with_context(chunk, document_context)
                        enhanced_chunks.append(enhanced_chunk)

                    # Add to vector store
                    if enhanced_chunks and self.vector_store is not None:
                        self.vector_store.add_documents(enhanced_chunks)
                        files_indexed += 1
                        total_chunks += len(enhanced_chunks)
                        indexed_files[str(file_path)] = file_hash
                        logger.info(f"Indexed {file_path.name}: {len(enhanced_chunks)} contextual chunks")

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
        return self.vector_store.as_retriever(search_kwargs=search_kwargs)

    def get_relevant_documents(
        self, query: str, k: int = 8, filter_content_types: Optional[List[str]] = None
    ) -> List[Document]:
        """
        Get relevant documents for a query (compatibility method).

        This method provides compatibility with LangChain's retriever interface.
        """
        return self.semantic_search(query, k, filter_content_types)

    def semantic_search(
        self, query: str, k: int = 8, filter_content_types: Optional[List[str]] = None, score_threshold: float = 0.5
    ) -> List[Document]:
        """
        Perform semantic search with optional filtering and scoring.
        """
        import logging

        logger = logging.getLogger(__name__)

        # Get more results than needed for filtering and reranking
        search_k = k * 3

        # Get documents with scores
        if self.vector_store is None:
            raise ValueError("Vector store not initialized")
        docs_and_scores = self.vector_store.similarity_search_with_score(query, k=search_k)

        logger.debug(f"Raw search returned {len(docs_and_scores)} documents")
        if docs_and_scores:
            logger.debug(
                f"Score range: {min(score for _, score in docs_and_scores):.3f} - {max(score for _, score in docs_and_scores):.3f}"
            )

        # Filter by similarity score threshold (lower score = more similar in distance-based metrics)
        # Using <= because ChromaDB returns distance scores where lower values mean higher similarity
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

        # Creative/inspiration queries
        if any(
            term in query_lower for term in ["illustration", "art", "design", "creative", "inspiration", "artistic"]
        ):
            content_type_hints.append("creative")
        if "inspiration" in query_lower or "artistic" in query_lower:
            # Inspiration often overlaps with bio/about content
            content_type_hints.append("about")

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

    async def auto_route_query_async(self, query: str) -> List[Document]:
        """
        Async version of auto_route_query with enhanced performance.
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

        # Creative/inspiration queries
        if any(
            term in query_lower for term in ["illustration", "art", "design", "creative", "inspiration", "artistic"]
        ):
            content_type_hints.append("creative")
        if "inspiration" in query_lower or "artistic" in query_lower:
            # Inspiration often overlaps with bio/about content
            content_type_hints.append("about")

        if any(term in query_lower for term in ["project", "built", "created", "developed"]):
            content_type_hints.append("project")

        # Perform async search with intelligent filtering
        # Using a more lenient threshold for async to match typical ChromaDB scores
        if content_type_hints:
            # First try filtered search with appropriate threshold
            results = await self.semantic_search_async(
                query, filter_content_types=content_type_hints, score_threshold=0.85
            )

            # If not enough results, broaden the search
            if len(results) < 4:
                additional_results = await self.semantic_search_async(query, k=8 - len(results), score_threshold=0.85)
                results.extend(additional_results)
        else:
            # No specific type detected, do general search
            results = await self.semantic_search_async(query, score_threshold=0.85)

        return results
