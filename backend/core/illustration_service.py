import json
import os
import logging
from typing import List, Dict, Any, Optional
from thefuzz import process

logger = logging.getLogger(__name__)

class IllustrationService:
    """Service for managing and searching illustration data."""

    def __init__(self, illustrations_path: str, search_threshold: int = 55, max_results: int = 15):
        self.illustrations_path = illustrations_path
        self.search_threshold = search_threshold
        self.max_results = max_results
        self.illustrations_data = []
        self._load_illustrations()

    def _load_illustrations(self) -> None:
        """Load illustrations data from JSON file with error handling."""
        try:
            with open(self.illustrations_path, "r", encoding="utf-8") as f:
                self.illustrations_data = json.load(f)
                logger.info(f"Loaded {len(self.illustrations_data)} illustrations")
        except FileNotFoundError:
            logger.warning(f"Illustrations file not found at {self.illustrations_path}")
            self.illustrations_data = []
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in illustrations file: {e}")
            self.illustrations_data = []
        except Exception as e:
            logger.error(f"Unexpected error loading illustrations: {e}")
            self.illustrations_data = []

    def validate_data(self) -> tuple[bool, str]:
        """Validate the loaded illustrations data structure."""
        if not self.illustrations_data:
            message = "❌ No illustrations data loaded"
            logger.warning(message)
            return False, message

        valid_count = 0
        issues = []

        for i, img in enumerate(self.illustrations_data):
            if not isinstance(img, dict):
                issues.append(f"Item {i}: Not a dictionary")
                continue

            if 'file' not in img:
                issues.append(f"Item {i}: Missing 'file' field")
                continue

            if not img.get('title') and not img.get('tags'):
                issues.append(f"Item {i}: No title or tags for searching")
                continue

            valid_count += 1

        if issues:
            logger.warning(f"Illustrations validation issues: {issues[:5]}...")

        message = f"✅ Illustrations: {valid_count}/{len(self.illustrations_data)} valid entries"
        logger.info(message)

        if valid_count == 0:
            error_msg = "❌ No valid illustration entries found!"
            logger.error(error_msg)
            return False, error_msg
        elif valid_count < len(self.illustrations_data):
            warning_msg = f"⚠️ Some illustration entries are missing required fields"
            logger.warning(warning_msg)

        return valid_count > 0, message

    def search(self, search_term: str) -> List[Dict[str, str]]:
        """
        Search illustrations using fuzzy matching.

        Args:
            search_term: The search term to match against illustrations

        Returns:
            List of dictionaries containing file paths of matching illustrations
        """
        try:
            if not self.illustrations_data:
                logger.warning("No illustrations data available")
                return []

            if not search_term or search_term.lower().strip() in ["all", ""]:
                logger.info(f"Returning all {len(self.illustrations_data)} illustrations")
                return [{"file": img["file"]} for img in self.illustrations_data
                        if isinstance(img, dict) and "file" in img]

            search_term = search_term.strip().lower()
            logger.info(f"Searching illustrations for term: '{search_term}'")

            # Handle multiple search terms joined by "and"
            if " and " in search_term:
                terms = [term.strip() for term in search_term.split(" and ") if term.strip()]
                logger.info(f"Multi-term search with {len(terms)} terms: {terms}")

                all_matches = []
                for term in terms:
                    matches = self._search_single_term(term)
                    all_matches.extend(matches)

                # Deduplicate while preserving order
                unique_files = list(dict.fromkeys(all_matches))
                results = [{"file": file} for file in unique_files[:self.max_results]]
                logger.info(f"Multi-term search returned {len(results)} results")
                return results
            else:
                # Single-term search
                matches = self._search_single_term(search_term)
                results = [{"file": file} for file in matches[:self.max_results]]
                logger.info(f"Single-term search returned {len(results)} results")
                return results

        except Exception as e:
            logger.error(f"Error searching illustrations for '{search_term}': {e}")
            return []

    def _search_single_term(self, term: str) -> List[str]:
        """Helper function to search for a single term."""
        try:
            # Create searchable content for each illustration
            choices = {}
            for img in self.illustrations_data:
                if not isinstance(img, dict) or 'file' not in img:
                    continue

                # Combine title and tags for searching
                title = img.get('title', '').lower()
                tags = ' '.join(img.get('tags', [])).lower()
                searchable_content = f"{title} {tags}".strip()

                if searchable_content:  # Only include if there's content to search
                    choices[img["file"]] = searchable_content

            if not choices:
                logger.warning("No searchable content found in illustrations")
                return []

            # Handle singular/plural forms
            search_terms = [term]
            if term.endswith('s'):
                # Add singular form (remove trailing 's')
                search_terms.append(term[:-1])
            else:
                # Add plural form (add 's')
                search_terms.append(term + 's')

            logger.debug(f"Searching with terms: {search_terms}")

            all_matches = []
            for search_term in search_terms:
                # Use fuzzy matching
                found_matches = process.extract(search_term, choices, limit=15)

                # Filter by threshold
                for match_text, score, file_key in found_matches:
                    if score >= self.search_threshold:
                        all_matches.append((file_key, score))
                        logger.debug(f"Match: {file_key} (score: {score})")

            # Remove duplicates while keeping highest score
            unique_matches = {}
            for file_key, score in all_matches:
                if file_key not in unique_matches or score > unique_matches[file_key]:
                    unique_matches[file_key] = score

            high_quality_matches = list(unique_matches.keys())

            logger.info(f"Found {len(high_quality_matches)} unique matches above threshold {self.search_threshold}")
            return high_quality_matches

        except Exception as e:
            logger.error(f"Error in single term search for '{term}': {e}")
            return []

    def get_all(self) -> List[Dict[str, str]]:
        """Get all illustrations as file references."""
        return [{"file": img["file"]} for img in self.illustrations_data
                if isinstance(img, dict) and "file" in img]

    def get_count(self) -> int:
        """Get the total number of illustrations."""
        return len(self.illustrations_data)

    def reload(self) -> bool:
        """Reload illustrations data from file."""
        try:
            self._load_illustrations()
            return True
        except Exception as e:
            logger.error(f"Failed to reload illustrations: {e}")
            return False
