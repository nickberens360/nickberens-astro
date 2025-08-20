"""
Content router component for intelligent query routing and content type detection.

This module provides focused functionality for:
- Query intent analysis and content type detection  
- Smart routing based on query patterns
- Adaptive search strategy selection
- Content type hint extraction
"""

import logging
from typing import List, Optional

from langchain.docstore.document import Document

from .config import AppConfig
from .semantic_searcher import SemanticSearcher

logger = logging.getLogger(__name__)


class ContentRouter:
    """Handles intelligent query routing and content type detection."""

    def __init__(self, semantic_searcher: SemanticSearcher):
        self.semantic_searcher = semantic_searcher

    def detect_content_types(self, query: str) -> List[str]:
        """
        Detect content types based on query patterns.

        Args:
            query: User query text

        Returns:
            List of detected content type hints
        """
        query_lower = query.lower()
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

        return content_type_hints

    def auto_route_query(self, query: str) -> List[Document]:
        """
        Automatically route query to the most relevant content.
        No manual configuration needed!

        Args:
            query: User query text

        Returns:
            List of relevant documents
        """
        content_type_hints = self.detect_content_types(query)

        # Perform search with intelligent filtering
        if content_type_hints:
            # Use generous distance thresholds to ensure good coverage
            # Since ChromaDB returns distance scores (lower=better), higher threshold = more inclusive
            initial_threshold = AppConfig.INCLUSIVE_DISTANCE_THRESHOLD  # Include good to fair matches
            k_value = AppConfig.EXPANDED_SEARCH_K  # Get more results to ensure comprehensive coverage

            # First try filtered search
            results = self.semantic_searcher.semantic_search(
                query, k=k_value, filter_content_types=content_type_hints, score_threshold=initial_threshold
            )

            # If not enough results, broaden the search with even higher threshold
            if len(results) < (AppConfig.EXPANDED_SEARCH_K // 2):
                additional_results = self.semantic_searcher.semantic_search(
                    query,
                    k=AppConfig.EXPANDED_SEARCH_K - len(results),
                    score_threshold=AppConfig.BROAD_DISTANCE_THRESHOLD,
                )
                results.extend(additional_results)
        else:
            # No specific type detected, do general search with generous distance threshold
            results = self.semantic_searcher.semantic_search(
                query, k=AppConfig.EXPANDED_SEARCH_K, score_threshold=AppConfig.INCLUSIVE_DISTANCE_THRESHOLD
            )

        return results

    def get_search_strategy(self, query: str) -> dict:
        """
        Determine the optimal search strategy for a query.

        Args:
            query: User query text

        Returns:
            Dictionary with search strategy parameters
        """
        content_types = self.detect_content_types(query)
        query_lower = query.lower()

        strategy = {
            "content_types": content_types,
            "k": AppConfig.DEFAULT_SEARCH_K,
            "score_threshold": AppConfig.DEFAULT_DISTANCE_THRESHOLD,
            "use_expansion": False,
            "strategy_name": "default",
        }

        # Specific strategies based on query patterns
        if any(term in query_lower for term in ["resume", "cv"]):
            strategy.update(
                {
                    "k": AppConfig.EXPANDED_SEARCH_K,
                    "score_threshold": AppConfig.INCLUSIVE_DISTANCE_THRESHOLD,
                    "use_expansion": True,
                    "strategy_name": "resume_focused",
                }
            )
        elif any(term in query_lower for term in ["illustration", "art", "creative"]):
            strategy.update(
                {
                    "k": AppConfig.DEFAULT_ILLUSTRATION_COUNT,
                    "score_threshold": 0.0,  # Get all creative content
                    "strategy_name": "creative_focused",
                }
            )
        elif len(content_types) > 1:
            # Multi-type queries need broader search
            strategy.update(
                {
                    "k": AppConfig.EXPANDED_SEARCH_K,
                    "score_threshold": AppConfig.INCLUSIVE_DISTANCE_THRESHOLD,
                    "use_expansion": True,
                    "strategy_name": "multi_type",
                }
            )
        elif not content_types:
            # General queries get moderate expansion
            strategy.update(
                {
                    "k": AppConfig.EXPANDED_SEARCH_K,
                    "score_threshold": AppConfig.INCLUSIVE_DISTANCE_THRESHOLD,
                    "strategy_name": "general",
                }
            )

        logger.debug(f"Query routing strategy for '{query}': {strategy['strategy_name']}")
        return strategy

    def route_with_strategy(self, query: str, custom_strategy: Optional[dict] = None) -> List[Document]:
        """
        Route query using a specific strategy.

        Args:
            query: User query text
            custom_strategy: Optional custom strategy parameters

        Returns:
            List of relevant documents
        """
        strategy = custom_strategy or self.get_search_strategy(query)

        results = self.semantic_searcher.semantic_search(
            query,
            k=strategy["k"],
            filter_content_types=strategy["content_types"] if strategy["content_types"] else None,
            score_threshold=strategy["score_threshold"],
        )

        # Apply expansion if strategy requires it and we don't have enough results
        if strategy.get("use_expansion", False) and len(results) < (strategy["k"] // 2):
            additional_results = self.semantic_searcher.semantic_search(
                query, k=strategy["k"] - len(results), score_threshold=AppConfig.BROAD_DISTANCE_THRESHOLD
            )
            results.extend(additional_results)

        logger.info(f"Routed query '{query}' using {strategy['strategy_name']} strategy: {len(results)} results")
        return results
