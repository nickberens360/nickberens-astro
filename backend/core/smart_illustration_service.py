"""
Smart illustration service using unified retriever.

This service replaces the old illustration service and unified_data.json dependency
with intelligent illustration search using the unified retriever system.
"""

import json
import logging
from difflib import SequenceMatcher
from typing import Dict, List, Tuple

from .config import AppConfig
from .unified_retriever import UnifiedRetriever

logger = logging.getLogger(__name__)


class SmartIllustrationService:
    """Smart illustration service that uses unified retriever for image search."""

    def __init__(self, unified_retriever: UnifiedRetriever):
        self.unified_retriever = unified_retriever
        # Cache illustrations data to avoid repeated file I/O
        self._illustrations_cache = self._load_illustrations_data()

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
            # Fuzzy fallback: if we didn't get enough results, try matching against titles/tags
            if len(illustrations) < top_k:
                try:
                    fuzzy_needed = top_k - len(illustrations)
                    extra = self._fuzzy_fallback(search_term, fuzzy_needed, seen_files)
                    illustrations.extend(extra)
                    logger.info(
                        f"Fuzzy fallback added {len(extra)} results; total now {len(illustrations)} for '{search_term}'"
                    )
                except Exception:
                    logger.warning("Fuzzy fallback failed", exc_info=True)

            return illustrations[:top_k]

        except Exception:
            logger.error("Smart illustration search failed", exc_info=True)
            return []

    # --- Internal helpers ---
    def _load_illustrations_data(self) -> List[Dict[str, str]]:
        """Load illustrations from configured JSON file."""
        path = AppConfig.ILLUSTRATIONS_PATH
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            logger.warning(f"Unable to load illustrations from {path}", exc_info=True)
        return []

    def _score_entry(self, search: str, entry: Dict[str, str]) -> float:
        """Compute a fuzzy score for an entry using title, tags, and filename."""
        s = search.lower().strip()
        title = (entry.get("title") or "").lower()
        tags = " ".join(entry.get("tags") or [])
        file_name = (entry.get("file") or "").lower()

        scores: List[float] = []
        if title:
            scores.append(SequenceMatcher(None, s, title).ratio())
        if tags:
            scores.append(SequenceMatcher(None, s, tags).ratio())
        if file_name:
            scores.append(SequenceMatcher(None, s, file_name).ratio())

        # Bonus for simple containment
        if s and (s in title or s in tags or s in file_name):
            scores.append(1.0)

        return max(scores) if scores else 0.0

    def _fuzzy_fallback(self, search_term: str, limit: int, seen_files: set) -> List[Dict[str, str]]:
        """Return additional matches using fuzzy title/tag matching."""
        entries = self._illustrations_cache
        if not entries:
            return []

        scored: List[Tuple[float, Dict[str, str]]] = []
        for e in entries:
            score = self._score_entry(search_term, e)
            if score >= 0.6:  # reasonable threshold for typos
                scored.append((score, e))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        results: List[Dict[str, str]] = []
        for _, e in scored:
            file_key = e.get("file")
            if not file_key or file_key in seen_files:
                continue
            results.append({"file": f"/illustrations/{file_key}"})
            seen_files.add(file_key)
            if len(results) >= limit:
                break

        return results
