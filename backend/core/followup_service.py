import logging
import random
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

    def generate_followups(
        self,
        user_question: str,
        ai_response: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> List[str]:
        """
        Generate follow-up questions - always returns 1 random question.

        Args:
            user_question: The user's original question (unused in simplified version)
            ai_response: The AI's response (unused in simplified version)
            conversation_history: Previous conversation for context (unused in simplified version)

        Returns:
            List with 1 follow-up question suggestion
        """
        # Ultra-simple: just return 1 random question from our 6 static questions
        return random.sample(self.questions, 1)
