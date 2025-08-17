"""
Smart illustration service using unified retriever.

This service replaces the old illustration service and unified_data.json dependency
with intelligent illustration search using the unified retriever system.
"""

import logging
from typing import Dict, List

from .unified_retriever import UnifiedRetriever

logger = logging.getLogger(__name__)


class SmartIllustrationService:
    """Smart illustration service that uses unified retriever for image search."""

    def __init__(self, unified_retriever: UnifiedRetriever):
        self.unified_retriever = unified_retriever

    def validate_data(self):
        """Validate that illustration data is available."""
        try:
            # Test search for illustrations to see if data exists
            test_results = self.search("illustration", top_k=1)
            if test_results:
                return True, "✅ Smart illustration system ready with unified retriever."
            else:
                return False, "❌ No illustration data found in unified retriever."
        except Exception as e:
            logger.warning(f"Illustration validation failed: {e}")
            return False, f"❌ Illustration validation failed: {e}"

    def get_all(self) -> List[Dict[str, str]]:
        """Return all illustrations using metadata filtering."""
        try:
            logger.info("Attempting to get all illustrations using metadata filtering...")

            # Use semantic search with creative content type filter
            docs = self.unified_retriever.semantic_search(
                query="illustration art design creative",
                k=200,  # High enough to get all illustrations
                filter_content_types=["creative"],
                score_threshold=2.0,  # Generous threshold to include all illustrations
            )

            logger.info(f"Semantic search returned {len(docs)} documents")
            for i, doc in enumerate(docs[:5]):  # Debug first 5 docs
                logger.info(f"Doc {i}: metadata = {doc.metadata}")

            illustrations: List[Dict[str, str]] = []
            seen_files = set()

            for doc in docs:
                is_illustration = doc.metadata.get("is_illustration_data")
                logger.info(
                    f"Processing doc: is_illustration_data={is_illustration}, metadata keys={list(doc.metadata.keys())}"
                )

                if is_illustration:
                    display_path = doc.metadata.get("display_path")
                    file_key = doc.metadata.get("illustration_file")
                    logger.info(f"Found illustration: display_path={display_path}, file_key={file_key}")

                    if display_path and file_key not in seen_files:
                        illustrations.append({"file": display_path})
                        seen_files.add(file_key)

            logger.info(f"Found {len(illustrations)} illustrations via metadata filtering")
            return illustrations

        except Exception:
            logger.error("Failed to get all illustrations", exc_info=True)
            return []

    def search(self, search_term: str, top_k: int = 10) -> List[Dict[str, str]]:
        """
        Search illustrations using smart retriever.

        Args:
            search_term: The user's search query
            top_k: Maximum number of results

        Returns:
            List of illustration file paths for frontend display
        """
        if not search_term or not isinstance(search_term, str):
            logger.warning("Invalid search term provided to illustration search.")
            return []

        logger.info(f"Smart illustration search for: '{search_term}'")

        try:
            # Use semantic search with creative content type filter and search term
            docs = self.unified_retriever.semantic_search(
                query=f"{search_term} illustration art creative character",
                k=top_k * 2,  # Get more docs to allow filtering
                filter_content_types=["creative"],
                score_threshold=2.0,  # Same generous threshold as get_all()
            )

            illustrations: List[Dict[str, str]] = []
            seen_files = set()

            for doc in docs:
                if len(illustrations) >= top_k:
                    break

                if doc.metadata.get("is_illustration_data"):
                    # Check if search term matches content for specific searches
                    content_lower = doc.page_content.lower()
                    search_lower = search_term.lower()

                    if search_term == "all" or search_lower in content_lower:
                        display_path = doc.metadata.get("display_path")
                        file_key = doc.metadata.get("illustration_file")

                        if display_path and file_key not in seen_files:
                            illustrations.append({"file": display_path})
                            seen_files.add(file_key)
                            logger.info(f"Found illustration via search: {file_key} -> {display_path}")

            logger.info(f"Smart illustration search returned {len(illustrations)} results for '{search_term}'")
            return illustrations

        except Exception:
            logger.error("Smart illustration search failed", exc_info=True)
            return []
