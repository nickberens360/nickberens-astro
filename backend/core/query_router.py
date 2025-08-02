"""
Query router module for determining query types and routing logic.

This module defines the QueryType enum and provides utilities for
routing different types of user queries to appropriate handlers.
"""

from enum import Enum


class QueryType(Enum):
    """Enumeration of different query types that can be handled by the system."""

    ALL_IMAGES = "all_images"
    IMAGE_SEARCH = "image_search"
    AI_TEXT_RESPONSE = "ai_text_response"
