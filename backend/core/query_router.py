import logging
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)

class QueryType(Enum):
    """Types of queries the system can handle."""
    SPECIFIC_IMAGE_SEARCH = "specific_image_search"
    SHOW_ME_PATTERN = "show_me_pattern"
    ALL_IMAGES = "all_images"
    GENERAL_IMAGE_PATTERN = "general_image_pattern"
    AI_TEXT_RESPONSE = "ai_text_response"

class QueryRouter:
    """Service for routing and parsing different types of user queries."""

    def __init__(self):
        # Define patterns and keywords
        self.image_keywords = [
            "image", "images", "illustration", "illustrations", "drawing", "drawings",
            "art", "design", "designs", "pic", "pics", "picture", "pictures"
        ]

        self.specific_image_keywords = [
            "images of", "image of", "drawings of", "drawing of",
            "illustrations of", "illustration of", "art about", "art of"
        ]

        self.show_me_patterns = [
            "show me", "show", "find", "get", "display"
        ]

        self.image_indicators = [
            "images", "image", "illustrations", "illustration", "drawings", "drawing", "art", "pics", "pictures"
        ]

        self.ignore_words = {
            "show", "me", "get", "find", "display", "see", "view", "look", "at",
            "the", "a", "an", "some", "any", "all", "your", "of", "for"
        }

        self.all_image_phrases = [
            "show me all illustrations", "show all illustrations", "show me your illustrations",
            "show me all your art", "show me all images", "show me images", "show your art",
            "all images", "all illustrations", "all art", "show me everything"
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

        # Route to "show me X" patterns
        search_term = self._check_show_me_pattern(question)
        if search_term:
            return QueryType.SHOW_ME_PATTERN, search_term

        # Route to show all images
        if self._check_all_images_pattern(question):
            return QueryType.ALL_IMAGES, "all"

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
                remaining_text = question[len(show_pattern):].strip()

                # Check if it contains image indicators
                for img_indicator in self.image_indicators:
                    if img_indicator in remaining_text:
                        search_term = self._extract_search_term_from_show_pattern(
                            remaining_text, img_indicator
                        )
                        if search_term:
                            logger.info(f"Show me pattern detected: '{search_term}'")
                            return search_term
        return None

    def _extract_search_term_from_show_pattern(self, remaining_text: str, img_indicator: str) -> Optional[str]:
        """Extract search term from 'show me X images' pattern."""
        # Extract the search term (everything before the image indicator)
        parts = remaining_text.split(img_indicator)
        if len(parts) > 1:
            search_term = parts[0].strip()
        else:
            # Handle cases like "show me doug images" where the term comes before
            words = remaining_text.split()
            if img_indicator in words:
                idx = words.index(img_indicator)
                search_term = " ".join(words[:idx]).strip()
            else:
                search_term = remaining_text.replace(img_indicator, "").strip()

        return search_term if search_term else None

    def _check_all_images_pattern(self, question: str) -> bool:
        """Check for patterns that request all images."""
        return question in self.all_image_phrases

    def _check_general_image_pattern(self, question: str) -> Optional[str]:
        """Check for general patterns like 'X images' or 'X art'."""
        words = question.split()
        for img_indicator in self.image_indicators:
            if img_indicator in words:
                # Get the index of the image indicator
                idx = words.index(img_indicator)

                # Extract words before and after the image indicator
                words_before = words[:idx]
                words_after = words[idx+1:]

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