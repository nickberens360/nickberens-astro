"""
Smart query handler that uses unified retriever for intelligent responses.

This module provides intelligent query handling without manual configuration:
- Automatic query understanding
- Smart content routing
- Performance optimization through caching
- Better context selection
"""

import logging
from typing import Any, Dict, List, Optional

from langchain.schema import Document
from langchain_core.language_models import BaseLanguageModel

from .config import AppConfig
from .llm_utils import analyze_query_with_llm
from .unified_retriever import UnifiedRetriever

logger = logging.getLogger(__name__)


class SmartQueryHandler:
    """Handles queries intelligently using the unified retriever."""

    def __init__(self, unified_retriever: UnifiedRetriever, llm: BaseLanguageModel):
        self.unified_retriever = unified_retriever
        self.llm = llm
        self._query_cache: Dict[str, List[Document]] = {}  # Simple cache for repeated queries

    async def get_relevant_context_async(
        self, query: str, chat_history: Optional[List[Dict]] = None, max_context_length: int = 2000
    ) -> List[Document]:
        """
        Async version of get_relevant_context with enhanced performance.
        """
        # Check cache first
        cache_key = f"{query}:{len(chat_history) if chat_history else 0}"
        if cache_key in self._query_cache:
            logger.info("Using cached results for query")
            return self._query_cache[cache_key]

        # Use unified retriever's async smart routing
        docs = await self.unified_retriever.auto_route_query_async(query)

        # Post-process documents for quality
        processed_docs = self._post_process_documents(docs, query, max_context_length)

        # Cache results
        self._query_cache[cache_key] = processed_docs

        # Limit cache size
        if len(self._query_cache) > AppConfig.MAX_CACHE_SIZE:
            # Remove oldest entries
            oldest_key = next(iter(self._query_cache))
            del self._query_cache[oldest_key]

        return processed_docs

    def get_relevant_context(
        self, query: str, chat_history: Optional[List[Dict]] = None, max_context_length: int = 2000
    ) -> List[Document]:
        """
        Get the most relevant context for a query.

        This method:
        1. Analyzes the query to understand intent
        2. Retrieves relevant documents
        3. Ranks and filters for quality
        4. Ensures context fits within token limits
        """
        # Check cache first
        cache_key = f"{query}:{len(chat_history) if chat_history else 0}"
        if cache_key in self._query_cache:
            logger.info("Using cached results for query")
            return self._query_cache[cache_key]

        # Use unified retriever's smart routing
        docs = self.unified_retriever.auto_route_query(query)

        # Post-process documents for quality
        processed_docs = self._post_process_documents(docs, query, max_context_length)

        # Cache results
        self._query_cache[cache_key] = processed_docs

        # Limit cache size
        if len(self._query_cache) > AppConfig.MAX_CACHE_SIZE:
            # Remove oldest entries
            oldest_key = next(iter(self._query_cache))
            del self._query_cache[oldest_key]

        return processed_docs

    def _post_process_documents(self, docs: List[Document], query: str, max_context_length: int) -> List[Document]:
        """
        Post-process documents to ensure quality and fit within limits.
        Optimized for speed and context efficiency.
        """
        if not docs:
            return []

        # Quick deduplication based on content similarity
        unique_docs = []
        seen_content = set()

        for doc in docs:
            # Create a content fingerprint
            content_fingerprint = doc.page_content[:100].lower().strip()
            if content_fingerprint not in seen_content:
                unique_docs.append(doc)
                seen_content.add(content_fingerprint)

        # Skip expensive LLM re-ranking for speed - use simple relevance scoring instead
        # This saves 1-2 seconds per request
        scored_docs = []
        query_words = set(query.lower().split())

        for doc in unique_docs:
            # Simple relevance score based on query word overlap
            doc_words = set(doc.page_content.lower().split())
            overlap_score = len(query_words.intersection(doc_words))

            # Boost score for shorter, more focused documents
            length_penalty = len(doc.page_content) / 1000  # Penalty for very long docs
            relevance_score = overlap_score - (length_penalty * 0.1)

            scored_docs.append((relevance_score, doc))

        # Sort by relevance score (highest first)
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        reranked_docs = [doc for _, doc in scored_docs]

        # Smart context selection - prioritize quality over quantity
        selected_docs = []
        current_length = 0
        target_docs = min(3, len(reranked_docs))  # Limit to top 3 most relevant docs

        for doc in reranked_docs[:target_docs]:
            doc_length = len(doc.page_content)

            if current_length + doc_length <= max_context_length:
                selected_docs.append(doc)
                current_length += doc_length
            elif current_length < max_context_length * 0.7:  # If we have less than 70% filled
                # Intelligently truncate the document to essential parts
                remaining_space = max_context_length - current_length

                # Try to keep the most relevant parts (first and last parts often most important)
                if doc_length > remaining_space:
                    first_half = remaining_space // 2
                    second_half = remaining_space - first_half

                    truncated_content = doc.page_content[:first_half] + "\n...\n" + doc.page_content[-second_half:]

                    truncated_doc = Document(
                        page_content=truncated_content, metadata={**doc.metadata, "truncated": True}
                    )
                    selected_docs.append(truncated_doc)
                    break
            else:
                # We have enough context
                break

        return selected_docs

    def analyze_query_with_llm(self, query: str) -> Dict[str, Any]:
        """
        Analyze query to understand user intent using an LLM.
        """
        return analyze_query_with_llm(self.llm, query)
