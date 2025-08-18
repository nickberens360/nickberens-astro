"""
Fast follow-up service using pre-generated questions.

This service provides instant follow-up questions by using questions
that were pre-generated during the indexing phase.
"""

import json
import logging
import random
from pathlib import Path
from typing import Any, Dict, List, Optional

from .constants import STOP_WORDS

logger = logging.getLogger(__name__)

# Use absolute path for the default cache file, based on the module location
DEFAULT_CACHE_FILE = str((Path(__file__).parent.parent / ".followup_cache.json").resolve())


class PreGeneratedFollowUpService:
    """Ultra-fast follow-up service using pre-generated questions."""

    def __init__(self, cache_file: str = DEFAULT_CACHE_FILE):
        """
        Initialize the pre-generated follow-up service.

        Args:
            cache_file: Path to the pre-generated questions cache
        """
        self.cache_file = Path(cache_file)
        self.questions_db: Dict[str, List[str]] = {}
        self.content_hash: Optional[str] = None

        # Load pre-generated questions
        self._load_pregenerated_questions()

        # Context keywords for smart selection
        self.context_keywords = {
            "technical": [
                "vue",
                "javascript",
                "typescript",
                "frontend",
                "code",
                "development",
                "programming",
                "framework",
            ],
            "experience": ["experience", "work", "career", "job", "wisnet", "hillman", "role", "position"],
            "creative": ["illustration", "art", "drawing", "design", "creative", "artistic", "visual"],
            "projects": ["project", "built", "created", "developed", "portfolio", "work", "application"],
            "philosophy": ["philosophy", "approach", "process", "methodology", "thinking", "belief"],
            "skills": ["skill", "technology", "tool", "proficient", "expert", "knowledge"],
            "contact": ["contact", "email", "reach", "hire", "connect", "get in touch"],
        }

        # Fallback questions if no pre-generated ones available
        self.fallback_questions = [
            "Show me Nick's illustrations",
            "Tell me about Nick's experience",
            "What technologies does Nick work with?",
            "Show me Nick's recent projects",
            "What's Nick's development philosophy?",
            "How can I contact Nick?",
        ]

    def generate_followups(
        self,
        user_question: str,
        ai_response: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> List[str]:
        """
        Generate follow-up questions instantly using pre-generated questions.

        Args:
            user_question: The user's original question
            ai_response: The AI's response
            conversation_history: Previous conversation for context

        Returns:
            List of 3 follow-up question suggestions
        """

        # Detect context from question and response
        detected_contexts = self._detect_contexts(user_question, ai_response)

        # Get previously asked questions to avoid repetition
        asked_questions = self._get_asked_questions(user_question, conversation_history)

        # Select appropriate questions
        selected_questions = self._select_questions(detected_contexts, asked_questions)

        logger.info(f"Generated {len(selected_questions)} follow-up questions (pre-generated, instant)")
        return selected_questions

    def _load_pregenerated_questions(self) -> None:
        """Load pre-generated questions from cache file."""

        if not self.cache_file.exists():
            logger.warning(f"Pre-generated questions cache not found at {self.cache_file}")
            self.questions_db = self._get_default_questions()
            return

        try:
            with open(self.cache_file, "r") as f:
                cache_data = json.load(f)

            # Find the most recent cache entry by generated_at if present
            if cache_data:
                best_key = None
                best_ts = None
                for key, value in cache_data.items():
                    ts = value.get("generated_at")
                    if ts:
                        try:
                            current_ts = ts
                        except Exception:
                            current_ts = None
                    else:
                        current_ts = None

                    if best_ts is None and current_ts is not None:
                        best_key, best_ts = key, current_ts
                    elif current_ts is not None and current_ts > (best_ts or ""):
                        best_key, best_ts = key, current_ts

                # Fallback to first key if no timestamps
                if best_key is None:
                    best_key = next(iter(cache_data))

                latest_entry = cache_data.get(best_key, {})
                self.questions_db = latest_entry.get("questions", {})
                self.content_hash = best_key

                logger.info(f"Loaded {sum(len(qs) for qs in self.questions_db.values())} pre-generated questions")
            else:
                logger.warning("Cache file is empty, using default questions")
                self.questions_db = self._get_default_questions()

        except Exception as e:
            logger.error(f"Error loading pre-generated questions: {e}")
            self.questions_db = self._get_default_questions()

    def _detect_contexts(self, user_question: str, ai_response: str) -> List[str]:
        """Detect relevant contexts from the question and response."""

        detected = []
        combined_text = f"{user_question} {ai_response}".lower()

        # Check for context keywords
        for context, keywords in self.context_keywords.items():
            if any(keyword in combined_text for keyword in keywords):
                detected.append(context)

        # If no specific contexts detected, add general
        if not detected:
            detected.append("general")

        return detected

    def _get_asked_questions(self, current_question: str, conversation_history: Optional[List[Dict[str, str]]]) -> set:
        """Get set of previously asked questions to avoid repetition."""

        asked = {current_question.lower()}

        if conversation_history:
            for msg in conversation_history:
                if msg.get("sender") == "user":
                    asked.add(msg.get("text", "").lower())

        return asked

    def _select_questions(self, contexts: List[str], asked_questions: set) -> List[str]:
        """Select appropriate questions based on context."""

        candidates = []

        # Collect questions from relevant contexts
        for context in contexts:
            # Try exact context match first
            context_key = f"topic_{context}"
            if context_key in self.questions_db:
                candidates.extend(self.questions_db[context_key])

            # Try partial matches
            for key, questions in self.questions_db.items():
                if context in key.lower():
                    candidates.extend(questions)

        # Add general questions if we don't have enough
        if "general" in self.questions_db:
            candidates.extend(self.questions_db["general"])

        # Only include content-based questions when we have specific context beyond "general"
        # This prevents unrelated content-specific follow-ups from appearing.
        has_specific_context = any(ctx for ctx in contexts if ctx != "general")
        if has_specific_context and "content_based" in self.questions_db:
            candidates.extend(self.questions_db["content_based"])

        # If still no candidates, use fallback
        if not candidates:
            candidates = self.fallback_questions.copy()

        # Filter out similar questions
        filtered_candidates = []
        for question in candidates:
            if not self._is_similar_to_asked(question, asked_questions):
                filtered_candidates.append(question)

        # Remove duplicates while preserving order
        unique_candidates = []
        seen = set()
        for q in filtered_candidates:
            if q not in seen:
                unique_candidates.append(q)
                seen.add(q)

        # Select 3 questions
        if len(unique_candidates) <= 3:
            return unique_candidates
        else:
            # Shuffle and take 3 random questions
            random.shuffle(unique_candidates)
            return unique_candidates[:3]

    def _is_similar_to_asked(self, question: str, asked_questions: set) -> bool:
        """Check if a question is too similar to previously asked questions."""

        question_lower = question.lower()
        question_words = set(question_lower.split())

        # Remove stop words
        question_words -= STOP_WORDS

        for asked in asked_questions:
            asked_words = set(asked.split())
            asked_words -= STOP_WORDS

            if not question_words or not asked_words:
                continue

            # Check overlap
            overlap = len(question_words.intersection(asked_words))
            min_words = min(len(question_words), len(asked_words))

            if min_words > 0 and overlap / min_words > 0.6:
                return True

        return False

    def _get_default_questions(self) -> Dict[str, List[str]]:
        """Get default questions when pre-generated ones aren't available."""

        return {
            "general": [
                "Show me Nick's illustrations",
                "Tell me about Nick's experience",
                "What technologies does Nick work with?",
                "Show me Nick's recent projects",
                "What's Nick's development philosophy?",
                "How can I contact Nick?",
            ],
            "topic_technical": [
                "What Vue.js projects has Nick worked on?",
                "Tell me about Nick's JavaScript expertise",
                "How does Nick approach frontend architecture?",
                "What's Nick's experience with modern frameworks?",
                "Show me Nick's technical portfolio",
            ],
            "topic_experience": [
                "What did Nick accomplish at Wisnet?",
                "What's Nick working on at Hillman Group?",
                "Tell me about Nick's career progression",
                "What's been Nick's biggest career achievement?",
                "How has Nick's role evolved over time?",
            ],
            "topic_creative": [
                "Show me Nick's creative illustrations",
                "Tell me about Nick's artistic process",
                "What inspires Nick's creative work?",
                "Show me different art styles Nick has done",
                "How does Nick balance technical and creative work?",
            ],
            "content_based": [
                "What makes Nick unique as a developer?",
                "How does Nick approach problem-solving?",
                "What's Nick's learning philosophy?",
                "Tell me about Nick's collaboration style",
            ],
        }

    def reload_questions(self) -> bool:
        """Reload questions from cache file. Returns True if successful."""
        try:
            self._load_pregenerated_questions()
            return True
        except Exception as e:
            logger.error(f"Error reloading questions: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the loaded questions."""

        stats = {
            "total_questions": sum(len(qs) for qs in self.questions_db.values()),
            "question_categories": list(self.questions_db.keys()),
            "cache_file_exists": self.cache_file.exists(),
            "content_hash": self.content_hash,
            "using_fallback": len(self.questions_db) == 0,
        }

        # Count by category
        for category, questions in self.questions_db.items():
            stats[f"{category}_count"] = len(questions)

        return stats

    def close(self) -> None:
        """Clean up resources (no-op for pre-generated service)."""
