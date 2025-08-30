import logging
import threading
from typing import Dict, List, Optional, Tuple

from .admin_database import admin_db_manager
from .config import FollowUpSettings

logger = logging.getLogger(__name__)


class FollowUpService:
    """Service for generating smart follow-up question suggestions with configurable settings."""

    def __init__(self) -> None:
        # Question pools for different categories
        self.question_pools = {
            "technical": [
                "What technologies do you work with?",
                "Tell me about your development philosophy?",
                "Show me your coding projects",
                "What frameworks do you prefer?",
                "How do you approach problem solving?",
            ],
            "personal": [
                "Tell me about your experience",
                "What's your background?",
                "How can I contact Nick?",
                "What motivates you?",
                "Tell me about your journey",
            ],
            "creative": [
                "Show me your illustrations",
                "What inspires your artwork?",
                "Tell me about your creative process",
                "Show me your design work",
                "What art styles do you enjoy?",
            ],
        }

        # Default static questions (fallback)
        self.default_questions: Tuple[str, ...] = (
            "Show me your illustrations",
            "Tell me about your experience",
            "What inspires your artwork?",
            "What technologies do you work with?",
            "What's your development philosophy?",
            "How can I contact Nick?",
        )

        # Track current position for sequential ordering
        self.current_index: int = 0
        # Thread lock for concurrent access protection
        self._lock = threading.Lock()
        # Cache settings to avoid frequent database calls
        self._cached_settings: Optional[FollowUpSettings] = None
        self._settings_cache_timestamp: float = 0

    def _get_settings(self) -> FollowUpSettings:
        """Get current settings with caching."""
        import time

        current_time = time.time()
        # Cache settings for 60 seconds to reduce database calls
        if self._cached_settings is None or current_time - self._settings_cache_timestamp > 60:

            try:
                settings_json = admin_db_manager.get_admin_setting("followup_settings")
                if settings_json:
                    self._cached_settings = FollowUpSettings.from_json(settings_json)
                else:
                    self._cached_settings = FollowUpSettings()
                self._settings_cache_timestamp = current_time
                logger.info(f"FollowUpService: Loaded follow-up settings: {self._cached_settings.to_dict()}")
            except Exception as e:
                logger.warning(f"Failed to load follow-up settings, using defaults: {e}")
                self._cached_settings = FollowUpSettings()
                self._settings_cache_timestamp = current_time

        return self._cached_settings

    def _build_question_pool(self, settings: FollowUpSettings) -> List[str]:
        """Build question pool based on settings."""
        questions = []

        # Add questions from enabled categories
        if settings.include_technical:
            questions.extend(self.question_pools["technical"])
        if settings.include_personal:
            questions.extend(self.question_pools["personal"])
        if settings.include_creative:
            questions.extend(self.question_pools["creative"])

        # If no categories enabled, use defaults
        if not questions:
            questions = list(self.default_questions)

        return questions

    def _generate_static_questions(self, settings: FollowUpSettings) -> List[str]:
        """Generate questions using static/sequential method."""
        questions_pool = self._build_question_pool(settings)

        if not questions_pool:
            logger.warning("FollowUpService: No questions available, returning empty list")
            return []

        # Return sequential questions with wrap-around
        with self._lock:
            selected_questions = []
            for i in range(settings.max_questions):
                question_index = (self.current_index + i) % len(questions_pool)
                selected_questions.append(questions_pool[question_index])

            # Advance index for next call
            self.current_index = (self.current_index + settings.max_questions) % len(questions_pool)
            logger.debug(f"FollowUpService static: selected {len(selected_questions)} questions")

        return selected_questions

    def _generate_dynamic_questions(
        self, settings: FollowUpSettings, user_question: str, ai_response: str
    ) -> List[str]:
        """Generate questions using dynamic method based on context."""
        # For now, this is similar to static but could be enhanced with AI analysis
        # TODO: Implement smart context-based question selection
        questions_pool = self._build_question_pool(settings)

        if not questions_pool:
            return []

        # Simple implementation: prefer questions that aren't too similar to current query
        # This could be enhanced with semantic similarity in the future
        import random

        random.seed(hash(user_question.lower()) % 1000)  # Deterministic randomness based on question

        selected = random.sample(questions_pool, min(settings.max_questions, len(questions_pool)))

        logger.debug(f"FollowUpService dynamic: selected {len(selected)} questions")
        return selected

    def _generate_contextual_questions(
        self,
        settings: FollowUpSettings,
        user_question: str,
        ai_response: str,
        conversation_history: Optional[List[Dict[str, str]]],
    ) -> List[str]:
        """Generate questions using contextual analysis (most advanced)."""
        # For now, this is the same as dynamic but could be enhanced with conversation analysis
        # TODO: Implement conversation-aware question generation
        return self._generate_dynamic_questions(settings, user_question, ai_response)

    def generate_followups(
        self,
        user_question: str,
        ai_response: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> List[str]:
        """
        Generate follow-up questions based on current settings and context.

        Args:
            user_question: The user's original question.
            ai_response: The AI's response.
            conversation_history: Previous conversation for context.

        Returns:
            A list of follow-up questions.
        """
        try:
            settings = self._get_settings()

            # If disabled, return no questions
            if not settings.enabled:
                logger.debug("Follow-up questions disabled in settings")
                return []

            # Generate based on service type
            if settings.service_type == "static":
                return self._generate_static_questions(settings)
            elif settings.service_type == "dynamic":
                return self._generate_dynamic_questions(settings, user_question, ai_response)
            elif settings.service_type == "contextual":
                return self._generate_contextual_questions(settings, user_question, ai_response, conversation_history)
            else:
                logger.warning(f"Unknown service type: {settings.service_type}, using static")
                return self._generate_static_questions(settings)

        except Exception as e:
            logger.error(f"Error generating follow-ups: {e}", exc_info=True)
            # Fallback to simple static behavior
            return [self.default_questions[self.current_index % len(self.default_questions)]]

    def reload_settings(self) -> None:
        """Force reload of settings from database."""
        self._cached_settings = None
        self._settings_cache_timestamp = 0
        logger.info("Follow-up settings cache cleared, will reload on next request")
