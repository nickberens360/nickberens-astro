"""
Smart query handler that uses unified retriever for intelligent responses.

This module provides intelligent query handling without manual configuration:
- Automatic query understanding
- Smart content routing
- Performance optimization through caching
- Better context selection
"""

import logging
from typing import Dict, List, Optional

from langchain.schema import Document
from langchain_core.retrievers import BaseRetriever

from .unified_retriever import UnifiedRetriever

logger = logging.getLogger(__name__)


class SmartQueryHandler:
    """Handles queries intelligently using the unified retriever."""

    def __init__(self, unified_retriever: UnifiedRetriever):
        self.unified_retriever = unified_retriever
        self._query_cache = {}  # Simple cache for repeated queries

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

        # Sort by relevance (documents are already sorted by vector similarity)
        # But we can add additional scoring based on metadata
        scored_docs = []
        for doc in unique_docs:
            score = 1.0  # Base score from vector similarity

            # Boost score based on content type matches
            if "content_types" in doc.metadata:
                query_lower = query.lower()
                content_types = doc.metadata["content_types"].split(",")
                for content_type in content_types:
                    if content_type.strip() in query_lower:
                        score *= 1.2

            # Boost recent documents slightly
            if "mtime" in doc.metadata:
                # Recent documents get a small boost
                score *= 1.05

            scored_docs.append((score, doc))

        # Sort by score
        scored_docs.sort(key=lambda x: x[0], reverse=True)

        # Select documents that fit within context length
        selected_docs = []
        current_length = 0

        for score, doc in scored_docs:
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

    def analyze_query_intent(self, query: str) -> Dict[str, any]:
        """
        Analyze query to understand user intent.

        Returns a dictionary with:
        - intent_type: The primary intent (question, request, etc.)
        - topics: Detected topics in the query
        - complexity: Estimated complexity level
        - suggested_approach: How to handle this query
        """
        query_lower = query.lower()

        # Detect intent type
        if any(word in query_lower for word in ["what", "who", "when", "where", "why", "how"]):
            intent_type = "question"
        elif any(word in query_lower for word in ["show", "list", "display", "find"]):
            intent_type = "retrieval"
        elif any(word in query_lower for word in ["explain", "describe", "tell"]):
            intent_type = "explanation"
        else:
            intent_type = "general"

        # Detect topics
        topics = []
        topic_keywords = {
            "technical": ["code", "api", "function", "technical", "implementation"],
            "experience": ["experience", "work", "job", "company", "role"],
            "skills": ["skill", "expertise", "technology", "language", "framework"],
            "personal": ["about", "interest", "passion", "philosophy"],
            "creative": ["illustration", "art", "design", "creative"],
            "project": ["project", "built", "created", "developed"],
        }

        for topic, keywords in topic_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                topics.append(topic)

        # Estimate complexity
        word_count = len(query.split())
        if word_count < 5:
            complexity = "simple"
        elif word_count < 15:
            complexity = "moderate"
        else:
            complexity = "complex"

        # Suggest approach
        if len(topics) > 2 or complexity == "complex":
            suggested_approach = "comprehensive"
        elif intent_type == "retrieval":
            suggested_approach = "list"
        else:
            suggested_approach = "focused"

        return {
            "intent_type": intent_type,
            "topics": topics,
            "complexity": complexity,
            "suggested_approach": suggested_approach,
        }
