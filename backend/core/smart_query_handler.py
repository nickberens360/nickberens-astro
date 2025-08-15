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

from .llm_utils import analyze_query_with_llm, rerank_documents_with_llm
from .unified_retriever import UnifiedRetriever

logger = logging.getLogger(__name__)


class SmartQueryHandler:
    """Handles queries intelligently using the unified retriever."""

    def __init__(self, unified_retriever: UnifiedRetriever, llm: BaseLanguageModel):
        self.unified_retriever = unified_retriever
        self.llm = llm
        self._query_cache: Dict[str, List[Document]] = {}  # Simple cache for repeated queries

    def get_relevant_context(
        self, query: str, chat_history: Optional[List[Dict]] = None, max_context_length: int = 4000
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
        if len(self._query_cache) > 100:
            # Remove oldest entries
            oldest_key = next(iter(self._query_cache))
            del self._query_cache[oldest_key]

        return processed_docs

    def _post_process_documents(self, docs: List[Document], query: str, max_context_length: int) -> List[Document]:
        """
        Post-process documents to ensure quality and fit within limits.
        """
        # Remove duplicates based on content similarity
        unique_docs = []
        seen_content = set()

        for doc in docs:
            # Create a content fingerprint
            content_fingerprint = doc.page_content[:100].lower().strip()
            if content_fingerprint not in seen_content:
                unique_docs.append(doc)
                seen_content.add(content_fingerprint)

        # Use LLM to re-rank documents for relevance
        reranked_docs = rerank_documents_with_llm(self.llm, query, unique_docs)

        # Select documents that fit within context length
        selected_docs = []
        current_length = 0

        for doc in reranked_docs:
            doc_length = len(doc.page_content)
            if current_length + doc_length <= max_context_length:
                selected_docs.append(doc)
                current_length += doc_length
            elif current_length < max_context_length / 2:
                # If we have very little context, truncate the document
                remaining_space = max_context_length - current_length
                truncated_doc = Document(page_content=doc.page_content[:remaining_space], metadata=doc.metadata)
                selected_docs.append(truncated_doc)
                break

        return selected_docs

    def analyze_query_with_llm(self, query: str) -> Dict[str, Any]:
        """
        Analyze query to understand user intent using an LLM.
        """
        return analyze_query_with_llm(self.llm, query)
