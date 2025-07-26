import logging
import random
from typing import Dict, List

logger = logging.getLogger(__name__)


class FollowUpService:
    """Service for generating smart follow-up question suggestions."""

    def __init__(self):
        # Define follow-up questions based on topics/keywords
        self.topic_suggestions = {
            # Experience & Career
            "experience": [
                "What technologies do you work with most?",
                "Tell me about your biggest career achievement",
                "What's your development philosophy?",
                "Show me your recent projects",
            ],
            "wisnet": [
                "What did you learn at Wisnet?",
                "Show me projects from your Wisnet days",
                "How did you grow as a developer there?",
                "What was your favorite Wisnet project?",
            ],
            "hillman": [
                "What's exciting about your current role?",
                "Tell me about the Vue migration project",
                "What technologies do you use at Hillman?",
                "Show me your recent work",
            ],
            # Technical Skills
            "vue": [
                "Show me your Vue.js projects",
                "How do you compare Vue vs React?",
                "What's your favorite Vue.js feature?",
                "Tell me about the Vue 2 to 3 migration",
            ],
            "javascript": [
                "What's your favorite JavaScript framework?",
                "Show me your JavaScript projects",
                "Tell me about modern JavaScript features you love",
                "What's your approach to JavaScript testing?",
            ],
            "frontend": [
                "What's your design process?",
                "Show me your UI/UX work",
                "How do you approach responsive design?",
                "Tell me about your component library work",
            ],
            "backend": [
                "Do you work with any backend technologies?",
                "How do you handle API integration?",
                "Tell me about your full-stack experience",
                "What databases have you worked with?",
            ],
            # Creative Work
            "illustration": [
                "Show me your favorite illustrations",
                "What's your artistic inspiration?",
                "Tell me about your creative process",
                "Show me different art styles you've done",
            ],
            "design": [
                "Show me your design portfolio",
                "What design tools do you use?",
                "Tell me about your UX research experience",
                "How do you balance creativity and functionality?",
            ],
            "art": [
                "Show me all your artwork",
                "What mediums do you work in?",
                "Tell me about your artistic journey",
                "Show me your recent creative projects",
            ],
            # Projects & Portfolio
            "project": [
                "Show me your most challenging project",
                "What's your favorite project you've built?",
                "Tell me about your development process",
                "Show me your GitHub repositories",
            ],
            "portfolio": [
                "Show me your best work",
                "What makes you unique as a developer?",
                "Tell me about your career journey",
                "How can I contact you for opportunities?",
            ],
            # Personal & Philosophy
            "learning": [
                "What are you learning right now?",
                "How do you stay current with technology?",
                "What's your approach to professional development?",
                "Tell me about your problem-solving process",
            ],
            "challenge": [
                "What's been your biggest technical challenge?",
                "How do you approach difficult problems?",
                "Tell me about a project that pushed your limits",
                "What would you do differently on past projects?",
            ],
        }

        # General follow-ups when no specific topic is detected
        self.general_suggestions = [
            "Show me your illustrations",
            "Tell me about your experience",
            "What technologies do you work with?",
            "Show me your recent projects",
            "What's your development philosophy?",
            "How can I contact Nick?",
        ]

        # Context-aware suggestions based on response content
        self.context_keywords = {
            "vue": ["vue", "vuex", "nuxt", "vuetify"],
            "javascript": ["javascript", "js", "typescript", "node"],
            "frontend": ["frontend", "ui", "ux", "responsive", "css"],
            "backend": ["backend", "api", "server", "database"],
            "illustration": ["illustration", "drawing", "art", "design"],
            "experience": ["experience", "work", "career", "job"],
            "project": ["project", "built", "developed", "created"],
            "learning": ["learn", "study", "research", "explore"],
        }

    def generate_followups(
        self,
        user_question: str,
        ai_response: str,
        conversation_history: List[Dict[str, str]] = None,
    ) -> List[str]:
        """
        Generate smart follow-up questions based on context.

        Args:
            user_question: The user's original question
            ai_response: The AI's response
            conversation_history: Previous conversation for context

        Returns:
            List of 2-4 follow-up question suggestions
        """
        try:
            # Analyze the content to determine relevant topics
            detected_topics = self._detect_topics(user_question, ai_response)

            # Get suggestions based on detected topics
            suggestions = self._get_topic_suggestions(detected_topics)

            # Filter out questions that are too similar to what was already asked
            filtered_suggestions = self._filter_similar_questions(suggestions, user_question, conversation_history)

            # Return 3 suggestions (or fewer if not enough unique ones)
            return filtered_suggestions[:3]

        except Exception as e:
            logger.error(f"Error generating follow-ups: {e}")
            return random.sample(self.general_suggestions, 3)

    def _detect_topics(self, user_question: str, ai_response: str) -> List[str]:
        """Detect relevant topics from the question and response."""
        detected = []
        combined_text = f"{user_question} {ai_response}".lower()

        # Check for topic keywords
        for topic, keywords in self.context_keywords.items():
            if any(keyword in combined_text for keyword in keywords):
                detected.append(topic)

        # Check for specific company/experience mentions
        if "wisnet" in combined_text:
            detected.append("wisnet")
        if "hillman" in combined_text:
            detected.append("hillman")

        # If no specific topics detected, use general categories
        if not detected:
            if any(word in combined_text for word in ["tell", "about", "experience"]):
                detected.append("experience")
            elif any(word in combined_text for word in ["show", "see", "images", "art"]):
                detected.append("illustration")
            else:
                detected.append("general")

        return detected

    def _get_topic_suggestions(self, topics: List[str]) -> List[str]:
        """Get suggestions based on detected topics."""
        all_suggestions = []

        for topic in topics:
            if topic in self.topic_suggestions:
                all_suggestions.extend(self.topic_suggestions[topic])

        # If no topic-specific suggestions, use general ones
        if not all_suggestions:
            all_suggestions = self.general_suggestions.copy()

        # Shuffle and return unique suggestions
        unique_suggestions = list(set(all_suggestions))
        random.shuffle(unique_suggestions)
        return unique_suggestions

    def _filter_similar_questions(
        self,
        suggestions: List[str],
        current_question: str,
        conversation_history: List[Dict[str, str]] = None,
    ) -> List[str]:
        """Filter out questions that are too similar to what was already asked."""
        filtered = []
        current_lower = current_question.lower()

        # Get previously asked questions
        asked_questions = set()
        if conversation_history:
            for msg in conversation_history:
                if msg.get("sender") == "user":
                    asked_questions.add(msg.get("text", "").lower())

        asked_questions.add(current_lower)

        for suggestion in suggestions:
            suggestion_lower = suggestion.lower()

            # Check if this suggestion is too similar to something already asked
            is_similar = False
            for asked in asked_questions:
                if self._are_questions_similar(suggestion_lower, asked):
                    is_similar = True
                    break

            if not is_similar:
                filtered.append(suggestion)

        return filtered

    def _are_questions_similar(self, q1: str, q2: str) -> bool:
        """Check if two questions are too similar."""
        # Simple similarity check - can be improved with more sophisticated NLP
        q1_words = set(q1.split())
        q2_words = set(q2.split())

        # Remove common words
        common_words = {
            "tell",
            "me",
            "about",
            "show",
            "your",
            "you",
            "what",
            "how",
            "do",
            "is",
            "the",
            "a",
            "an",
        }
        q1_words -= common_words
        q2_words -= common_words

        if not q1_words or not q2_words:
            return False

        # If more than 60% of words overlap, consider them similar
        overlap = len(q1_words.intersection(q2_words))
        min_words = min(len(q1_words), len(q2_words))

        return overlap / min_words > 0.6
