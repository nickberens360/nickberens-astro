"""
Dependencies module for FastAPI dependency injection.

This module provides service instances for the application including:
- Illustration service for managing and searching illustrations
- Query router for routing different types of queries
- Response service for building API responses
- Followup service for generating followup questions
"""

import json
import os
from typing import Any, Dict, List


class IllustrationService:
    """Service for managing and searching illustrations."""

    def __init__(self, illustrations_file: str = "public/illustrations.json"):
        """Initialize the illustration service with the illustrations data file."""
        self.illustrations_file = illustrations_file
        self._illustrations = self._load_illustrations()

    def _load_illustrations(self) -> List[Dict[str, Any]]:
        """Load illustrations from the JSON file."""
        try:
            if os.path.exists(self.illustrations_file):
                with open(self.illustrations_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Type check: ensure we have a list
                if not isinstance(data, list):
                    print(f"Error: illustrations.json should contain a list, got {type(data)}")
                    return []

                # Validate each item is a dictionary
                illustrations: List[Dict[str, Any]] = []
                for item in data:
                    if isinstance(item, dict):
                        illustrations.append(item)
                    else:
                        print(f"Warning: Skipping non-dictionary item in illustrations.json: {item}")

                return illustrations
            return []
        except Exception as e:
            print(f"Error loading illustrations: {e}")
            return []

    def get_all(self) -> List[Dict[str, Any]]:
        """Return ALL illustrations without any limit."""
        return self._illustrations

    def search(self, search_term: str) -> List[Dict[str, Any]]:
        """Search illustrations by tags, title, or filename."""
        if not search_term:
            return self.get_all()

        search_term = search_term.lower()
        results = []

        for illustration in self._illustrations:
            # Search in title
            if search_term in illustration.get("title", "").lower():
                results.append(illustration)
                continue

            # Search in filename
            if search_term in illustration.get("file", "").lower():
                results.append(illustration)
                continue

            # Search in tags
            tags = illustration.get("tags", [])
            if any(search_term in tag.lower() for tag in tags):
                results.append(illustration)
                continue

        return results


class QueryRouter:
    """Service for routing different types of queries."""

    def route_query(self, question: str):
        """Route the query to appropriate handler."""
        from .core.query_router import QueryType

        question_lower = question.lower().strip()

        # Check for "all illustrations" or similar requests
        if any(
                phrase in question_lower
                for phrase in [
                    "all illustrations",
                    "show me all",
                    "all artwork",
                    "all images",
                    "every illustration",
                    "complete collection",
                ]
        ):
            return QueryType.ALL_IMAGES, ""

        # Check for specific illustration searches - only when explicitly requesting visual content
        visual_request_patterns = [
            "show me",
            "display",
            "find",
            "see",
            "view",
            "look at",
            "get me",
            "give me",
            "i want",
            "i need",
            "can you show",
            "can you find",
            "can you get"
        ]

        visual_content_words = ["illustration", "artwork", "image", "drawing"]

        # Only return images if the query contains both a visual request pattern AND visual content words
        has_visual_request = any(pattern in question_lower for pattern in visual_request_patterns)
        has_visual_content = any(word in question_lower for word in visual_content_words)

        if has_visual_request and has_visual_content:
            # Extract search terms (simple implementation)
            search_terms = question_lower.replace("show me", "").replace("illustrations", "").strip()
            return QueryType.IMAGE_SEARCH, search_terms

        # Default to AI text response
        return QueryType.AI_TEXT_RESPONSE, question


class ResponseService:
    """Service for building API responses."""

    def build_image_response(
            self, search_term: str, images: List[Dict[str, Any]], start_time: float, followup_questions: List[str]
    ):
        """Build response for image queries."""
        import time

        try:
            from pydantic import BaseModel

            class ImageResponse(BaseModel):
                search_term: str
                images: List[Dict[str, Any]]
                count: int
                processing_time: float
                followup_questions: List[str]

            return ImageResponse(
                search_term=search_term,
                images=images,
                count=len(images),
                processing_time=time.time() - start_time,
                followup_questions=followup_questions,
            )
        except ImportError:
            # Fallback to dict if pydantic is not available
            return {
                "search_term": search_term,
                "images": images,
                "count": len(images),
                "processing_time": time.time() - start_time,
                "followup_questions": followup_questions,
            }


class FollowupService:
    """Service for generating followup questions."""

    def generate_followups(self, question: str, response: str, history: List[Dict[str, Any]]) -> List[str]:
        """Generate followup questions based on the query and response."""
        # Simple implementation - return some generic followups for illustrations
        if "illustration" in question.lower() or "artwork" in question.lower():
            return [
                "Can you show me illustrations with specific themes?",
                "What's the story behind these illustrations?",
                "Do you have any character illustrations?",
            ]
        return [
            "Can you tell me more about this?",
            "What else would you like to know?",
            "Is there anything specific you're looking for?",
        ]


# Service instances
_illustration_service = None
_query_router = None
_response_service = None
_followup_service = None


def get_services() -> Dict[str, Any]:
    """Get all service instances for dependency injection."""
    global _illustration_service, _query_router, _response_service, _followup_service

    if _illustration_service is None:
        _illustration_service = IllustrationService()

    if _query_router is None:
        _query_router = QueryRouter()

    if _response_service is None:
        _response_service = ResponseService()

    if _followup_service is None:
        _followup_service = FollowupService()

    return {
        "illustration_service": _illustration_service,
        "query_router": _query_router,
        "response_service": _response_service,
        "followup_service": _followup_service,
        "retrievers": None,  # RAG retrievers - not needed for illustration queries
    }