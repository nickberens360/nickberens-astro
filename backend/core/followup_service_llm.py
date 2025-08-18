"""
Enhanced follow-up service that uses LLM to generate context-aware questions.

This service generates follow-up questions dynamically based on:
1. The current conversation context
2. Available content in the vector store
3. Topics that haven't been covered yet
"""

import logging
import random
from typing import Any, Dict, List, Optional

from langchain_core.language_models import BaseLanguageModel
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field

from .config import AppConfig

logger = logging.getLogger(__name__)


class FollowUpQuestions(BaseModel):
    """Schema for follow-up questions."""

    questions: List[str] = Field(description="List of 3-4 follow-up questions")
    reasoning: str = Field(description="Brief reasoning for why these questions were chosen")


class LLMFollowUpService:
    """Service for generating smart follow-up questions using LLM and vector store context."""

    def __init__(self, llm: BaseLanguageModel, unified_retriever: Any):
        """
        Initialize the LLM-based follow-up service.

        Args:
            llm: Language model for generating questions
            unified_retriever: Unified retriever for checking available content
        """
        self.llm = llm
        self.unified_retriever = unified_retriever
        self.parser = JsonOutputParser(pydantic_object=FollowUpQuestions)

        # Create the prompt template for follow-up generation
        self.prompt = PromptTemplate(
            template="""You are an AI assistant helping to generate relevant follow-up questions for Nick Berens' portfolio chatbot.

Based on the conversation so far and the available content in the knowledge base, suggest 3-4 follow-up questions that:
1. Are directly answerable from the indexed content
2. Explore different aspects not yet covered in the conversation
3. Would be interesting and valuable to the user
4. Are diverse in topic (mix technical, creative, experience-based questions)

Current Question: {user_question}
AI Response Summary: {response_summary}
Available Topics in Knowledge Base: {available_topics}
Topics Already Discussed: {discussed_topics}

The knowledge base contains information about:
- Nick's work experience at Wisnet and Hillman Group
- Technical skills (Vue.js, JavaScript, frontend development)
- Creative work (illustrations, art, design)
- Projects and portfolio pieces
- Development philosophy and approach
- Contact information and resume

Generate follow-up questions that can be answered from this content.

{format_instructions}

Response:""",
            input_variables=[
                "user_question",
                "response_summary",
                "available_topics",
                "discussed_topics",
                "format_instructions",
            ],
        )

        # Fallback questions if LLM generation fails
        self.fallback_questions = [
            "Show me Nick's illustrations",
            "Tell me about Nick's experience at Hillman Group",
            "What Vue.js projects has Nick worked on?",
            "What's Nick's development philosophy?",
            "Show me Nick's recent projects",
            "How can I contact Nick?",
        ]

    def generate_followups(
        self,
        user_question: str,
        ai_response: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> List[str]:
        """
        Generate smart follow-up questions using LLM and vector store context.

        Args:
            user_question: The user's original question
            ai_response: The AI's response
            conversation_history: Previous conversation for context

        Returns:
            List of 3-4 follow-up question suggestions
        """
        try:
            # Get available topics from vector store
            available_topics = self._get_available_topics()

            # Extract discussed topics from conversation
            discussed_topics = self._extract_discussed_topics(user_question, ai_response, conversation_history)

            # Summarize the response for context
            response_summary = self._summarize_response(ai_response)

            # Format the prompt
            format_instructions = self.parser.get_format_instructions()
            prompt_value = self.prompt.format(
                user_question=user_question,
                response_summary=response_summary,
                available_topics=", ".join(available_topics),
                discussed_topics=", ".join(discussed_topics) if discussed_topics else "None yet",
                format_instructions=format_instructions,
            )

            # Generate follow-ups using LLM
            response = self.llm.invoke(prompt_value)

            # Parse the response
            if hasattr(response, "content"):
                content = response.content
            else:
                content = str(response)

            parsed_response = self.parser.parse(content)

            # Validate questions are answerable
            if hasattr(parsed_response, "questions"):
                questions = getattr(parsed_response, "questions")
            elif isinstance(parsed_response, dict):
                questions = parsed_response.get("questions", [])
            else:
                questions = []
            validated_questions = self._validate_questions(questions)

            if validated_questions and len(validated_questions) >= 3:
                logger.info(f"Generated {len(validated_questions)} follow-up questions using LLM")
                return validated_questions[:4]  # Return up to 4 questions
            else:
                logger.warning("Not enough valid questions generated, using hybrid approach")
                return self._generate_hybrid_followups(available_topics, discussed_topics)

        except Exception as e:
            logger.error(f"Error generating LLM follow-ups: {e}")
            return self._generate_hybrid_followups([], [])

    def _get_available_topics(self) -> List[str]:
        """Extract available topics from the vector store metadata."""
        try:
            # Get a sample of documents to understand available content
            sample_query = "Tell me about Nick"
            results = self.unified_retriever.get_relevant_documents(sample_query, k=20)

            topics = set()
            for doc in results:
                if hasattr(doc, "metadata"):
                    # Extract topics from metadata
                    if "topic" in doc.metadata:
                        topics.add(doc.metadata["topic"])
                    if "tags" in doc.metadata:
                        topics.update(doc.metadata.get("tags", []))
                    if "source" in doc.metadata:
                        source = doc.metadata["source"]
                        if "experience" in source.lower():
                            topics.add("work experience")
                        if "project" in source.lower():
                            topics.add("projects")
                        if "skill" in source.lower():
                            topics.add("technical skills")
                        if "illustration" in source.lower():
                            topics.add("creative work")

            # Add known topics from the knowledge base structure
            known_topics = [
                "Vue.js expertise",
                "JavaScript development",
                "Frontend architecture",
                "Wisnet experience",
                "Hillman Group work",
                "Illustrations and art",
                "Development philosophy",
                "Recent projects",
                "Technical skills",
                "Career journey",
            ]

            topics.update(known_topics)
            return list(topics)

        except Exception as e:
            logger.error(f"Error getting available topics: {e}")
            return [
                "experience",
                "technical skills",
                "projects",
                "illustrations",
                "philosophy",
            ]

    def _extract_discussed_topics(
        self,
        current_question: str,
        current_response: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> List[str]:
        """Extract topics that have been discussed in the conversation."""
        discussed = []
        all_text = f"{current_question} {current_response}".lower()

        # Add previous conversation context
        if conversation_history:
            for msg in conversation_history:
                all_text += f" {msg.get('text', '')}".lower()

        # Check for specific topics
        topic_keywords = {
            "Vue.js": ["vue", "vuex", "nuxt", "composition api"],
            "JavaScript": ["javascript", "typescript", "node", "npm"],
            "Wisnet": ["wisnet", "madison"],
            "Hillman": ["hillman", "fasteners"],
            "Illustrations": ["illustration", "art", "drawing", "creative"],
            "Experience": ["experience", "career", "work", "role"],
            "Projects": ["project", "built", "developed", "created"],
        }

        for topic, keywords in topic_keywords.items():
            if any(keyword in all_text for keyword in keywords):
                discussed.append(topic)

        return discussed

    def _summarize_response(self, ai_response: str) -> str:
        """Create a brief summary of the AI response for context."""
        # Take first 200 characters or first 2 sentences
        if len(ai_response) <= 200:
            return ai_response

        sentences = ai_response.split(". ")[:2]
        return ". ".join(sentences) + "..."

    def _validate_questions(self, questions: List[str]) -> List[str]:
        """Validate that questions can be answered from the vector store."""
        validated = []
        try:
            score_threshold = float(AppConfig.FOLLOWUP_VALIDATION_SCORE_THRESHOLD)
        except (AttributeError, ValueError, TypeError):
            score_threshold = 0.5

        for question in questions:
            try:
                # Use similarity_search_with_score to get actual scores
                if hasattr(self.unified_retriever, "vector_store") and self.unified_retriever.vector_store is not None:
                    results_with_scores = self.unified_retriever.vector_store.similarity_search_with_score(
                        question, k=1
                    )

                    if results_with_scores:
                        # ChromaDB returns distance, so lower score = better match
                        _doc, score = results_with_scores[0]
                        if score <= score_threshold:
                            validated.append(question)
                            logger.debug(f"Validated question: '{question}' with score {score:.2f}")
                        else:
                            logger.debug(f"Question '{question}' has low relevance score: {score:.2f}")
                    else:
                        logger.debug(f"No results for question: {question}")
                else:
                    # Fallback: if no vector store access, use basic retrieval check
                    results = self.unified_retriever.get_relevant_documents(question, k=1)
                    if results and len(results) > 0:
                        validated.append(question)
                        logger.debug(f"Validated question (fallback): {question}")
                    else:
                        logger.debug(f"No results for question: {question}")

            except Exception as e:
                logger.error(f"Error validating question '{question}': {e}")

        return validated

    def _generate_hybrid_followups(self, available_topics: List[str], discussed_topics: List[str]) -> List[str]:
        """Generate follow-ups using a hybrid approach when LLM generation fails."""
        questions: List[str] = []

        # Topic-based questions for undiscussed topics
        topic_questions = {
            "Vue.js expertise": "What Vue.js projects has Nick worked on?",
            "JavaScript development": "Tell me about Nick's JavaScript expertise",
            "Wisnet experience": "What did Nick accomplish at Wisnet?",
            "Hillman Group work": "What's Nick working on at Hillman Group?",
            "Illustrations and art": "Show me Nick's creative illustrations",
            "Development philosophy": "What's Nick's approach to software development?",
            "Recent projects": "What are Nick's most recent projects?",
            "Technical skills": "What technologies does Nick specialize in?",
            "Career journey": "Tell me about Nick's career progression",
        }

        # Add questions for topics not yet discussed
        for topic, question in topic_questions.items():
            if topic not in discussed_topics and len(questions) < 4:
                questions.append(question)

        # If not enough questions, add some general ones
        if len(questions) < 3:
            general = [
                "Show me Nick's portfolio",
                "How can I contact Nick?",
                "What makes Nick unique as a developer?",
                "Tell me about Nick's problem-solving approach",
            ]
            random.shuffle(general)
            questions.extend(general[: 3 - len(questions)])

        return questions[:4]
