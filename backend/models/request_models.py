"""
Request models for the FastAPI application.

This module contains Pydantic models for validating incoming requests:
- Message: Individual chat message with sender and text
- Query: Main query request with question, chat history, and model preference
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from ..security.validator import SecurityValidator


class Message(BaseModel):
    sender: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="The sender of the message (user or assistant)",
    )
    text: str = Field(
        ...,
        min_length=1,
        max_length=SecurityValidator.MAX_MESSAGE_LENGTH,
        description="The message content",
    )


class Query(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        max_length=SecurityValidator.MAX_QUERY_LENGTH,
        description="The user's question",
    )
    chat_history: List[Message] = Field(
        default=[],
        max_length=SecurityValidator.MAX_CHAT_HISTORY_LENGTH,
        description="Previous conversation history",
    )
    preferred_model: Optional[str] = Field(default=None, description="User's preferred model (claude or gemini)")
