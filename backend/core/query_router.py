import logging
from enum import Enum
from typing import Optional, Tuple

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

    # Class constants for illustration query patterns
    ILLUSTRATION_SHOW_ALL_PATTERNS = [
        "illustrations",
        "illustrations done",
        "illustrations done?",
        "illustrations created",
        "illustrations created?",
        "done",
        "done?",
        "created",
        "created?",
    ]

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
            "pics of",
            "pic of",
            "pictures of",
            "picture of",
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

        self.ignore_words = {
            "show",
            "me",
            "tell",
            "describe",
            "explain",
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
            "about",
            "please",
            "describe",
            "for",
            "more",  # Added "more" to ignore words
            "details",  # Added "details" to ignore words
            # Question words that should be filtered out when extracting search terms
            "what",
            "are",
            "is",
            "do",
            "does",
            "did",
            "have",
            "has",
            "had",
            "you",
            "they",
            "we",
            "i",
            "can",
            "could",
            "would",
            "should",
            "will",
            "shall",
            "may",
            "might",
            "been",
            "being",
            "done",
            "made",
            "created",
            "different",
            "various",
            "which",
            "that",
            "this",
            "these",
            "those",
            "there",
            "here",
            "when",
            "where",
            "why",
            "how",
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
            "find illustrations",
            "find images",
            "find art",
            "find pictures",
            "find drawings",
            "get illustrations",
            "get images",
            "get art",
            "get pictures",
            "get drawings",
            "display illustrations",
            "display images",
            "display art",
            "display pictures",
            "display drawings",
            # Question patterns that are asking to see all illustrations
            "what illustrations",
            "what illustrations have you done",
            "what illustrations you have done",
            "what different illustrations",
            "what different illustrations have you done",
            "what different illustrations you have done",
            "what are different illustrations",
            "what are different illustrations have you done",
            "what are different illustrations you have done",
            "illustrations",
            "illustrations have you done",
            "illustrations you have done",
            "different illustrations",
            "different illustrations have you done",
            "different illustrations you have done",
            # "Show me" patterns asking for variety/styles (show all)
            "show me different art styles you have done",
            "show me different art styles you've done",
            "show me different art styles",
            "show me art styles",
            "show me styles",
            "different art styles",
            "art styles",
        ]

    @staticmethod
    def _clean_word(word: str) -> str:
        """Strip leading/trailing punctuation and quotes from a word."""
        if not word:
            return word
        strip_chars = "\"'()[]{}.,!?;:"
        return word.strip(strip_chars)

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
                found_image_indicator = False
                for img_indicator in self.image_indicators:
                    if img_indicator in remaining_text:
                        found_image_indicator = True
                        search_term = self._extract_search_term_from_show_pattern(remaining_text, img_indicator)
                        if search_term:
                            logger.info(f"Show me pattern detected: '{search_term}'")
                            return search_term

                # If we found an image indicator but no valid search term (only ignore words),
                # return None to let it fall through to other patterns
                if found_image_indicator:
                    return None
        return None

    def _extract_search_term_from_show_pattern(self, remaining_text: str, img_indicator: str) -> Optional[str]:
        """Extract search term from 'show me X images' pattern."""
        # Check if the remaining text is exactly just the image indicator
        # This handles cases like "show me images" or "find illustrations" where we want to show all
        if remaining_text.strip() == img_indicator:
            return None

        # Split into words to handle whole word matching
        words = [self._clean_word(w) for w in remaining_text.split()]

        # Find the image indicator word and remove it, keeping other words
        search_words = []
        for word in words:
            if word != img_indicator:
                search_words.append(word)

        if not search_words:
            return None

        # Filter out common words that are not part of the search term
        filtered_words = [word for word in search_words if word and word not in self.ignore_words]
        search_term = " ".join(filtered_words).strip()

        # If the search term is empty after filtering ignore words, return None
        # This handles cases like "show me the images" where "the" gets filtered out
        # but preserves cases like "find illustrations" where there are no ignore words to filter
        if not search_term:
            return None

        # If the search term consists only of image indicators, return None
        if search_term in self.image_indicators:
            return None

        return search_term

    def _check_all_images_pattern(self, question: str) -> bool:
        """Check for patterns that request all images."""
        # First check exact match
        if question in self.all_image_phrases:
            return True

        # Then check with ignore words filtered out
        words = question.split()
        filtered_words = [word for word in words if word not in self.ignore_words]
        filtered_question = " ".join(filtered_words)

        if filtered_question in self.all_image_phrases:
            return True

        # Special case: if the filtered question is just punctuation or empty after filtering,
        # but contains illustration keywords, treat it as "show all"
        if filtered_question.strip() in self.ILLUSTRATION_SHOW_ALL_PATTERNS:
            return True

        return False

    def _check_general_image_pattern(self, question: str) -> Optional[str]:
        """Check for general patterns like 'X images' or 'X art'."""
        original_words = question.split()
        words = [self._clean_word(w) for w in original_words]
        for img_indicator in self.image_indicators:
            if img_indicator in words:
                # Get the index of the image indicator
                idx = words.index(img_indicator)

                # Extract words before and after the image indicator
                words_before = words[:idx]
                words_after = words[idx + 1 :]

                # Filter out ignore words
                search_terms_before = [w for w in words_before if w and w not in self.ignore_words]
                search_terms_after = [w for w in words_after if w and w not in self.ignore_words]

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
