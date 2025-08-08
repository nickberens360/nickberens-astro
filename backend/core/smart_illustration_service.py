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
                return True, f"✅ Smart illustration system ready with unified retriever."
            else:
                return False, "❌ No illustration data found in unified retriever."
        except Exception as e:
            logger.warning(f"Illustration validation failed: {e}")
            return False, f"❌ Illustration validation failed: {e}"

    def get_all(self) -> List[Dict[str, str]]:
        """Return all illustrations by searching for creative content."""
        try:
            # Debug: Try multiple approaches to find illustration data
            logger.info("Attempting to get all illustrations...")

            # First, try to get all documents with illustration metadata
            all_docs = self.unified_retriever.vector_store.similarity_search("", k=100)
            logger.info(f"Total documents in vector store: {len(all_docs)}")

            illustrations = []
            seen_files = set()

            # Check all documents for illustration data
            illustration_docs_found = 0
            for doc in all_docs:
                if doc.metadata.get("is_illustration_data", False):
                    illustration_docs_found += 1
                    # Use display_path which already has the correct format
                    display_path = doc.metadata.get("display_path")
                    illustration_file = doc.metadata.get("illustration_file")  # Just for tracking duplicates
                    logger.info(
                        f"Found illustration doc: {illustration_file} -> {display_path} in {doc.metadata.get('file_name')}"
                    )

                    if display_path and illustration_file not in seen_files:
                        illustrations.append({"file": display_path})
                        seen_files.add(illustration_file)

            logger.info(f"Found {illustration_docs_found} illustration documents, {len(illustrations)} unique files")

            # If no results, try alternative approach - search more broadly
            if not illustrations:
                logger.info("No illustrations found with metadata, trying broader search...")
                broader_docs = self.unified_retriever.semantic_search(
                    "illustration file art image creative design character",
                    k=100,
                    score_threshold=0.0,  # Very low threshold
                )

                for doc in broader_docs:
                    # Check if content contains illustration file references
                    if '"file"' in doc.page_content and ".jpg" in doc.page_content or ".png" in doc.page_content:
                        # Extract file name from content
                        import re

                        matches = re.findall(r'"file":\s*"([^"]+\.(jpg|png|jpeg))"', doc.page_content)
                        for match in matches:
                            filename = match[0]
                            if filename not in seen_files:
                                # Build correct path from filename
                                file_path = f"/illustrations/{filename}"
                                illustrations.append({"file": file_path})
                                seen_files.add(filename)
                                logger.info(f"Found illustration via content parsing: {filename}")

            logger.info(f"Final result: {len(illustrations)} illustrations for 'get all'")
            return illustrations

        except Exception as e:
            logger.error(f"Failed to get all illustrations: {e}")
            import traceback

            logger.error(f"Stack trace: {traceback.format_exc()}")
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
            # Use the same logic as get_all but filter by search term
            all_docs = self.unified_retriever.vector_store.similarity_search(
                f"{search_term} illustration art creative character", k=50
            )

            illustrations = []
            seen_files = set()

            for doc in all_docs:
                if len(illustrations) >= top_k:
                    break

                # Check content for file references and search term matches
                content_lower = doc.page_content.lower()
                search_lower = search_term.lower()

                # Look for illustration files in content
                if '"file"' in doc.page_content and (search_lower in content_lower or search_term == "all"):
                    import re

                    matches = re.findall(r'"file":\s*"([^"]+\.(jpg|png|jpeg))"', doc.page_content)
                    for match in matches:
                        filename = match[0]
                        if filename not in seen_files:
                            # For specific searches, check if the search term appears in the content
                            if search_term == "all" or search_lower in content_lower:
                                file_path = f"/illustrations/{filename}"
                                illustrations.append({"file": file_path})
                                seen_files.add(filename)
                                logger.info(f"Found illustration: {filename} (matched: {search_term})")

            # Also check metadata-based approach
            for doc in all_docs:
                if len(illustrations) >= top_k:
                    break

                if doc.metadata.get("is_illustration_data"):
                    display_path = doc.metadata.get("display_path")
                    illustration_file = doc.metadata.get("illustration_file")
                    if display_path and illustration_file not in seen_files:
                        content_lower = doc.page_content.lower()
                        if search_term == "all" or search_term.lower() in content_lower:
                            illustrations.append({"file": display_path})
                            seen_files.add(illustration_file)
                            logger.info(f"Found illustration via metadata: {illustration_file} -> {display_path}")

            logger.info(f"Smart illustration search returned {len(illustrations)} results for '{search_term}'")
            return illustrations

        except Exception as e:
            logger.error(f"Smart illustration search failed: {e}")
            import traceback

            logger.error(f"Stack trace: {traceback.format_exc()}")
            return []
