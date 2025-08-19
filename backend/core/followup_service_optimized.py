"""
Optimized follow-up service with better performance characteristics.

This service provides multiple strategies for follow-up generation:
1. Fast static fallback for immediate responses
2. Async LLM generation for enhanced experiences
3. Caching to avoid repeated LLM calls
"""

import asyncio
import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.language_models import BaseLanguageModel

from .followup_service import FollowUpService
from .followup_service_llm import LLMFollowUpService

logger = logging.getLogger(__name__)


class OptimizedFollowUpService:
    """
    High-performance follow-up service with multiple generation strategies.

    Features:
    - Instant static fallback for fast responses
    - Optional LLM enhancement for better quality
    - Caching to avoid repeated expensive calls
    - Configurable timeout for LLM generation
    """

    def __init__(
        self,
        llm: Optional[BaseLanguageModel] = None,
        unified_retriever: Optional[Any] = None,
        llm_timeout: float = 5.0,
        use_llm_enhancement: bool = False,
    ):
        """
        Initialize optimized follow-up service.

        Args:
            llm: Language model for enhanced generation
            unified_retriever: Retriever for content validation
            llm_timeout: Maximum time to spend on LLM generation (seconds)
            use_llm_enhancement: Whether to use LLM for enhanced follow-ups
        """
        self.llm_timeout = llm_timeout
        self.use_llm_enhancement = use_llm_enhancement

        # Initialize services
        self.static_service = FollowUpService()

        self.llm_service: Optional[LLMFollowUpService] = None
        if llm and unified_retriever and use_llm_enhancement:
            self.llm_service = LLMFollowUpService(llm, unified_retriever)

        # Cache for LLM-generated follow-ups
        self.cache: Dict[str, List[str]] = {}
        self.cache_size_limit = 100

        # Thread pool for async LLM calls
        self.executor = ThreadPoolExecutor(max_workers=2)

    def generate_followups(
        self,
        user_question: str,
        ai_response: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        prefer_fast: bool = False,
    ) -> List[str]:
        """
        Generate follow-up questions with performance optimization.

        Args:
            user_question: The user's original question
            ai_response: The AI's response
            conversation_history: Previous conversation for context
            prefer_fast: If True, skip LLM generation and use static fallback

        Returns:
            List of follow-up question suggestions
        """

        # Always start with fast static generation
        static_followups = self.static_service.generate_followups(user_question, ai_response, conversation_history)

        # If fast response preferred or no LLM service, return static
        if prefer_fast or not self.llm_service:
            logger.info("Using fast static follow-up generation")
            return static_followups

        # Check cache first
        cache_key = self._generate_cache_key(user_question, ai_response)
        if cache_key in self.cache:
            logger.info("Using cached LLM follow-up questions")
            return self.cache[cache_key]

        # Try LLM generation with timeout
        try:
            logger.info(f"Attempting LLM follow-up generation (timeout: {self.llm_timeout}s)")

            # Use threading to implement timeout
            future = self.executor.submit(
                self.llm_service.generate_followups, user_question, ai_response, conversation_history
            )

            # Wait for result with timeout
            llm_followups = future.result(timeout=self.llm_timeout)

            # Cache successful results
            if llm_followups and len(llm_followups) >= 2:
                self._add_to_cache(cache_key, llm_followups)
                logger.info(f"LLM generated {len(llm_followups)} follow-up questions")
                return llm_followups
            else:
                logger.warning("LLM generated insufficient follow-ups, using static fallback")
                return static_followups

        except Exception as e:
            logger.warning(f"LLM follow-up generation failed/timed out: {e}, using static fallback")
            return static_followups

    def generate_followups_async(
        self, user_question: str, ai_response: str, conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Tuple[List[str], Optional[asyncio.Task]]:
        """
        Generate follow-ups with immediate static response and optional async LLM enhancement.

        Returns:
            Tuple of (immediate_followups, optional_llm_task)
        """

        # Immediate static response
        static_followups = self.static_service.generate_followups(user_question, ai_response, conversation_history)

        # Start async LLM enhancement if available
        llm_task = None
        if self.llm_service:
            # Check cache first
            cache_key = self._generate_cache_key(user_question, ai_response)
            if cache_key not in self.cache:
                llm_task = asyncio.create_task(
                    self._async_llm_generation(user_question, ai_response, conversation_history, cache_key)
                )

        return static_followups, llm_task

    async def _async_llm_generation(
        self, user_question: str, ai_response: str, conversation_history: Optional[List[Dict[str, str]]], cache_key: str
    ) -> Optional[List[str]]:
        """Async LLM follow-up generation."""
        try:
            loop = asyncio.get_event_loop()

            # Run LLM generation in thread pool
            if self.llm_service:
                llm_followups = await loop.run_in_executor(
                    self.executor, self.llm_service.generate_followups, user_question, ai_response, conversation_history
                )

                if llm_followups and len(llm_followups) >= 2:
                    self._add_to_cache(cache_key, llm_followups)
                    logger.info(f"Async LLM generated {len(llm_followups)} follow-up questions")
                    return llm_followups

        except Exception as e:
            logger.warning(f"Async LLM follow-up generation failed: {e}")

        return None

    def _generate_cache_key(self, user_question: str, ai_response: str) -> str:
        """Generate cache key for a question/response pair."""
        # Use first 200 chars of response to avoid huge keys
        response_snippet = ai_response[:200]
        content = f"{user_question}|{response_snippet}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    def _add_to_cache(self, key: str, followups: List[str]) -> None:
        """Add follow-ups to cache with size management."""
        if len(self.cache) >= self.cache_size_limit:
            # Remove oldest entry (simple FIFO)
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]

        self.cache[key] = followups

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring."""
        return {
            "cache_size": len(self.cache),
            "cache_limit": self.cache_size_limit,
            "llm_service_available": self.llm_service is not None,
            "llm_timeout": self.llm_timeout,
            "use_llm_enhancement": self.use_llm_enhancement,
        }

    def clear_cache(self) -> None:
        """Clear the follow-up cache."""
        self.cache.clear()
        logger.info("Follow-up cache cleared")

    def close(self) -> None:
        """Explicitly cleanup thread pool resources."""
        if hasattr(self, "executor"):
            try:
                self.executor.shutdown(wait=False)
                logger.info("OptimizedFollowUpService executor shut down")
            except Exception as e:
                logger.warning(f"Failed to shut down executor: {e}")
