"""
Response cache warmer for follow-up questions.

This module warms the response cache at startup by pre-generating
answers for common follow-up questions, ensuring instant responses
when users click them.
"""

import asyncio
import logging
from typing import Dict, List, Optional

from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)


class ResponseCacheWarmer:
    """Warms the response cache with common follow-up questions."""

    def __init__(self):
        self.warmed_questions: List[str] = []
        self.warming_complete = False

    async def warm_cache(
        self,
        questions: List[str],
        retrievers: Dict,
        app_state,
    ) -> None:
        """
        Warm the cache with responses for the given questions.

        Args:
            questions: List of questions to pre-cache
            retrievers: Dictionary of retrievers for RAG
            app_state: FastAPI app state containing services
        """
        if not questions:
            logger.info("No questions to warm cache with")
            return

        logger.info(f"Starting cache warming for {len(questions)} questions...")

        try:
            from ..core.llm_chain import stream_with_fallback

            successful_warmups = 0
            failed_warmups = 0

            for i, question in enumerate(questions, 1):
                try:
                    logger.debug(f"Warming cache [{i}/{len(questions)}]: {question}")

                    # Create chat history with just the question
                    chat_history = [HumanMessage(content=question)]

                    # Call stream_with_fallback which will automatically cache the response
                    text_stream, model_used, metadata = await stream_with_fallback(
                        retrievers,
                        chat_history,
                        question,
                        preferred_model=None,
                    )

                    # Consume the stream to ensure caching happens
                    response_text = ""
                    async for chunk in text_stream:
                        response_text += chunk

                    if response_text:
                        successful_warmups += 1
                        self.warmed_questions.append(question)
                        logger.debug(f"Successfully cached response for: {question[:50]}...")
                    else:
                        failed_warmups += 1
                        logger.warning(f"Empty response for question: {question}")

                except Exception as e:
                    failed_warmups += 1
                    logger.error(f"Failed to warm cache for question '{question}': {e}")

                # Small delay between questions to avoid overwhelming the LLM
                if i < len(questions):
                    await asyncio.sleep(0.5)

            self.warming_complete = True
            logger.info(
                f"Cache warming complete: {successful_warmups} successful, "
                f"{failed_warmups} failed out of {len(questions)} total"
            )

        except Exception as e:
            logger.error(f"Cache warming failed: {e}")
            self.warming_complete = True

    def get_warmed_questions(self) -> List[str]:
        """Get the list of successfully warmed questions."""
        return self.warmed_questions.copy()

    def is_warming_complete(self) -> bool:
        """Check if cache warming is complete."""
        return self.warming_complete


# Global cache warmer instance
_cache_warmer: Optional[ResponseCacheWarmer] = None


def get_cache_warmer() -> ResponseCacheWarmer:
    """Get or create the global cache warmer instance."""
    global _cache_warmer
    if _cache_warmer is None:
        _cache_warmer = ResponseCacheWarmer()
    return _cache_warmer


async def start_cache_warming(retrievers: Dict, app_state) -> None:
    """
    Start cache warming in the background.

    This function starts cache warming and returns immediately,
    allowing the app to start serving requests while warming happens.
    """
    from ..core.config import AppConfig

    if not AppConfig.CACHE_FOLLOWUP_RESPONSES:
        logger.info("Follow-up response caching is disabled")
        return

    # Get the follow-up service to extract general questions
    followup_service = app_state.followup_service
    if not followup_service:
        logger.warning("No follow-up service available for cache warming")
        return

    # Get the static questions (all 6 questions)
    questions_to_warm = followup_service.questions.copy()

    if not questions_to_warm:
        logger.info("No general follow-up questions found for cache warming")
        return

    # Get or create cache warmer
    warmer = get_cache_warmer()

    # Start warming in the background
    logger.info(f"Starting background cache warming for {len(questions_to_warm)} general questions")
    asyncio.create_task(warmer.warm_cache(questions_to_warm, retrievers, app_state))
