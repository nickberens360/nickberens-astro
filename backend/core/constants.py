"""Shared constants for the backend core services."""

# LLM Configuration Constants
# Standard parameters used across all ChatAnthropic and ChatGoogleGenerativeAI instances
LLM_TEMPERATURE = 0.1  # Low temperature for consistent, focused responses
LLM_TIMEOUT = 60.0  # 60-second timeout for API requests
LLM_STOP_TOKENS: list[str] = []  # No specific stop tokens

# ChatAnthropic common parameters
ANTHROPIC_COMMON_PARAMS = {
    "temperature": LLM_TEMPERATURE,
    "timeout": LLM_TIMEOUT,
    "stop": LLM_STOP_TOKENS,
}

# ChatGoogleGenerativeAI common parameters
GOOGLE_COMMON_PARAMS = {
    "temperature": LLM_TEMPERATURE,
    "timeout": LLM_TIMEOUT,
}

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
