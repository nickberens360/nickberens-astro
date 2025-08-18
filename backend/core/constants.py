"""Shared constants for the backend core services."""

# Common stop words to filter out when analyzing questions and search terms
# These are words that don't add semantic meaning for similarity calculations
STOP_WORDS = {
    # Articles, pronouns, prepositions
    "the",
    "a",
    "an",
    "at",
    "of",
    "for",
    "in",
    "on",
    "to",
    "with",
    "your",
    "you",
    "me",
    "some",
    "any",
    "all",
    # Action words that don't indicate topic
    "show",
    "tell",
    "get",
    "find",
    "display",
    "see",
    "view",
    "look",
    "please",
    # Question words
    "what",
    "how",
    "do",
    "does",
    "did",
    "is",
    "are",
    "have",
    "about",
}
