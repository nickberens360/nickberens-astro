import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class FollowUpService:
    """Service for generating smart follow-up question suggestions."""

    def __init__(self):
        # Simple static follow-up questions - always the same 6 questions
        self.questions = [
            "Show me your illustrations",
            "Tell me about your experience",
            "What inspires your artwork?",
            "What technologies do you work with?",
            "What's your development philosophy?",
            "How can I contact Nick?",
        ]
        # Track current position for sequential ordering
        self.current_index = 0

    def generate_followups(
        self,
        user_question: str,
        ai_response: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> List[str]:
        """
        Generate follow-up questions - returns 1 question in sequential order.

        Args:
            user_question: The user's original question (unused in simplified version)
            ai_response: The AI's response (unused in simplified version)
            conversation_history: Previous conversation for context (unused in simplified version)

        Returns:
            List with 1 follow-up question suggestion
        """
        # Return current question and advance to next position
        current_question = self.questions[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.questions)
        return [current_question]
