import logging
import threading
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class FollowUpService:
    """Service for generating smart follow-up question suggestions."""

    def __init__(self) -> None:
        # Simple static follow-up questions - always the same 6 questions
        # Using tuple to prevent accidental mutation
        self.questions: Tuple[str, ...] = (
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

    def generate_followups(
        self,
        user_question: str,
        ai_response: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> List[str]:
        """
        Generate a single follow-up question in sequential order (wrap-around).

        Args:
            user_question: The user's original question (currently unused; reserved for future use).
            ai_response: The AI's response (currently unused; reserved for future use).
            conversation_history: Previous conversation for context (currently unused).

        Returns:
            A list containing exactly one follow-up question.
        """
        # Guard against empty questions list
        if not self.questions:
            logger.warning("FollowUpService.questions is empty; returning no follow-ups")
            return []

        # Return current question and advance to next position (thread-safe)
        with self._lock:
            current_question = self.questions[self.current_index]
            logger.debug("FollowUpService: index=%d -> %r", self.current_index, current_question)
            self.current_index = (self.current_index + 1) % len(self.questions)
        return [current_question]
