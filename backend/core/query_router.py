import logging
from enum import Enum
from typing import Optional, Tuple

from .config import AppConfig

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Types of queries the system can handle."""

    SPECIFIC_IMAGE_SEARCH = "specific_image_search"
    SHOW_ME_PATTERN = "show_me_pattern"
    ALL_IMAGES = "all_images"
    GENERAL_IMAGE_PATTERN = "general_image_pattern"
    COMMIT_QUERY = "commit_query"
    AI_TEXT_RESPONSE = "ai_text_response"


class QueryRouter:
    """Service for routing and parsing different types of user queries."""

    def __init__(self):
        # Define patterns and keywords
        self.image_keywords = [
            "image",
            "images",
            "illustration",
            "illustrations",
            "drawing",
            "drawings",
            "art",
            "design",
            "designs",
            "pic",
            "pics",
            "picture",
            "pictures",
        ]

        self.specific_image_keywords = [
            "images of",
            "image of",
            "drawings of",
            "drawing of",
            "illustrations of",
            "illustration of",
            "art about",
            "art of",
        ]

        self.show_me_patterns = ["show me", "show", "find", "get", "display"]

        self.image_indicators = [
            "images",
            "image",
            "illustrations",
            "illustration",
            "drawings",
            "drawing",
            "art",
            "pics",
            "pictures",
        ]

        self.commit_keywords = AppConfig.COMMIT_KEYWORDS

        self.ignore_words = {
            "show",
            "me",
            "get",
            "find",
            "display",
            "see",
            "view",
            "look",
            "at",
            "the",
            "a",
            "an",
            "some",
            "any",
            "all",
            "your",
            "of",
            "for",
        }

        self.all_image_phrases = [
            "show me all illustrations",
            "show all illustrations",
            "show me your illustrations",
            "show me all your art",
            "show me all images",
            "show me images",
            "show your art",
            "all images",
            "all illustrations",
            "all art",
            "show me everything",
            "show me illustrations",
            "show me art",
            "show me pictures",
            "show me drawings",
        ]

    def route_query(self, question: str) -> Tuple[QueryType, Optional[str]]:
        """
        Route a query to determine its type and extract search terms.

        Args:
            question: The user's question (should be lowercased and stripped)

        Returns:
            Tuple of (QueryType, search_term or None)
        """
        # Route to specific image search
        search_term = self._check_specific_image_search(question)
        if search_term:
            return QueryType.SPECIFIC_IMAGE_SEARCH, search_term

        # Route to show all images BEFORE checking show me patterns
        # This prevents "show me images" from being incorrectly parsed as "show me 's'"
        if self._check_all_images_pattern(question):
            return QueryType.ALL_IMAGES, "all"

        # Route to commit queries
        if self._check_commit_query(question):
            return QueryType.COMMIT_QUERY, "commits"

        # Route to "show me X" patterns
        search_term = self._check_show_me_pattern(question)
        if search_term:
            return QueryType.SHOW_ME_PATTERN, search_term

        # Route to general image patterns
        search_term = self._check_general_image_pattern(question)
        if search_term:
            return QueryType.GENERAL_IMAGE_PATTERN, search_term

        # Default to AI text response
        return QueryType.AI_TEXT_RESPONSE, None

    def _check_specific_image_search(self, question: str) -> Optional[str]:
        """Check for specific image search patterns like 'images of X'."""
        for trigger in self.specific_image_keywords:
            if trigger in question:
                search_term = question.split(trigger, 1)[1].strip()
                if search_term:
                    logger.info(f"Specific image search detected: '{search_term}'")
                    return search_term
        return None

    def _check_show_me_pattern(self, question: str) -> Optional[str]:
        """Check for 'show me X images/illustrations' patterns."""
        for show_pattern in self.show_me_patterns:
            if question.startswith(show_pattern):
                remaining_text = question[len(show_pattern) :].strip()

                # Check if it contains image indicators
                for img_indicator in self.image_indicators:
                    if img_indicator in remaining_text:
                        search_term = self._extract_search_term_from_show_pattern(remaining_text, img_indicator)
                        if search_term:
                            logger.info(f"Show me pattern detected: '{search_term}'")
                            return search_term
        return None

    def _extract_search_term_from_show_pattern(self, remaining_text: str, img_indicator: str) -> Optional[str]:
        """Extract search term from 'show me X images' pattern."""
        # Check if the remaining text is exactly just the image indicator
        # This handles cases like "show me images" where we want to show all images
        if remaining_text.strip() == img_indicator:
            return None

        # This logic handles terms appearing before or after the image indicator.
        search_term = " ".join(remaining_text.split(img_indicator)).strip()

        if not search_term:
            return None

        # For better accuracy, filter out common words that are not part of the search term.
        words = search_term.split()
        filtered_words = [word for word in words if word not in self.ignore_words]
        search_term = " ".join(filtered_words).strip()

        return search_term if search_term else None

    def _check_all_images_pattern(self, question: str) -> bool:
        """Check for patterns that request all images."""
        return question in self.all_image_phrases

    def _check_commit_query(self, question: str) -> bool:
        """Check for commit-related queries."""
        return any(keyword in question for keyword in self.commit_keywords)

    def _check_general_image_pattern(self, question: str) -> Optional[str]:
        """Check for general patterns like 'X images' or 'X art'."""
        words = question.split()
        for img_indicator in self.image_indicators:
            if img_indicator in words:
                # Get the index of the image indicator
                idx = words.index(img_indicator)

                # Extract words before and after the image indicator
                words_before = words[:idx]
                words_after = words[idx + 1 :]

                # Filter out ignore words
                search_terms_before = [w for w in words_before if w not in self.ignore_words]
                search_terms_after = [w for w in words_after if w not in self.ignore_words]

                # Combine the search terms
                search_term = " ".join(search_terms_before + search_terms_after).strip()

                if search_term:
                    logger.info(f"General image pattern detected: '{search_term}'")
                    return search_term

        return None

    def is_image_query(self, question: str) -> bool:
        """Check if a query is asking for images/illustrations."""
        query_type, _ = self.route_query(question)
        return query_type != QueryType.AI_TEXT_RESPONSE
