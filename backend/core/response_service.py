import time
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class QueryResponse(BaseModel):
    answer: str
    images: Optional[List[str]] = None
    followup_questions: Optional[List[str]] = None  # New field
    processing_time: Optional[float] = None
    llm_used: Optional[str] = None

class ResponseService:
    """Service for building consistent API responses."""

    def __init__(self, base_image_url: str = "/illustrations/"):
        self.base_image_url = base_image_url

    def build_image_response(
            self,
            search_term: str,
            found_images: List[Dict[str, str]],
            start_time: float,
            followup_questions: Optional[List[str]] = None,
            success_message_template: str = "Here are the illustrations I found for '{}':"
    ) -> QueryResponse:
        """Build a response for successful image searches."""
        if found_images:
            image_urls = [f"{self.base_image_url}{img['file']}" for img in found_images]
            processing_time = time.time() - start_time

            # Customize message based on search term
            if search_term == "all":
                answer = "Of course! Here are some of my illustrations:"
            else:
                answer = success_message_template.format(search_term)

            logger.info(f"Image search completed in {processing_time:.3f}s")
            return QueryResponse(
                answer=answer,
                images=image_urls,
                followup_questions=followup_questions,
                processing_time=processing_time,
                llm_used="image_search"
            )
        else:
            processing_time = time.time() - start_time
            return QueryResponse(
                answer=f"Sorry, I couldn't find any illustrations matching '{search_term}'. You can ask to see all of my art.",
                followup_questions=followup_questions,
                processing_time=processing_time,
                llm_used="image_search"
            )

    def build_no_images_response(
            self,
            start_time: float,
            followup_questions: Optional[List[str]] = None
    ) -> QueryResponse:
        """Build a response when no images are available."""
        processing_time = time.time() - start_time
        return QueryResponse(
            answer="I couldn't find any illustrations at the moment.",
            followup_questions=followup_questions,
            processing_time=processing_time,
            llm_used="image_search"
        )

    def build_ai_response(
            self,
            answer: str,
            start_time: float,
            llm_used: str,
            followup_questions: Optional[List[str]] = None
    ) -> QueryResponse:
        """Build a response for AI-generated text."""
        processing_time = time.time() - start_time
        logger.info(f"Query processed successfully in {processing_time:.3f}s using {llm_used}")

        return QueryResponse(
            answer=answer,
            followup_questions=followup_questions,
            processing_time=processing_time,
            llm_used=llm_used
        )

    def build_error_response(
            self,
            error_message: str,
            start_time: float,
            llm_used: str = "fallback",
            followup_questions: Optional[List[str]] = None
    ) -> QueryResponse:
        """Build a response for errors."""
        processing_time = time.time() - start_time

        return QueryResponse(
            answer=error_message,
            followup_questions=followup_questions,
            processing_time=processing_time,
            llm_used=llm_used
        )