"""
Main query endpoint for handling user questions and requests.

This module contains the primary query endpoint that:
- Validates and sanitizes user input
- Routes queries to appropriate handlers (images vs text)
- Handles streaming responses for AI text generation
- Applies rate limiting and security validation
"""

import json
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage
from slowapi.util import get_remote_address

from ..core.app_factory import limiter
from ..core.config import AppConfig
from ..core.llm_chain import stream_with_fallback
from ..core.query_router import QueryType
from ..dependencies import get_services
from ..models.request_models import Query
from ..security.validator import SecurityValidator

# Initialize router
router = APIRouter()


@router.post("/query")
@limiter.limit(AppConfig.RATE_LIMIT)
async def query_endpoint(request: Request, query: Query, services: dict = Depends(get_services)):
    # Restore validation and sanitization calls
    client_ip = get_remote_address(request)
    is_valid, error_msg = SecurityValidator.validate_query(query, client_ip)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    sanitized_question = SecurityValidator.sanitize_input(query.question)

    # Sanitize chat history as well
    sanitized_history = [
        {"sender": msg.sender, "text": SecurityValidator.sanitize_input(msg.text)} for msg in query.chat_history
    ]

    query_type, search_term = services["query_router"].route_query(sanitized_question.lower().strip())

    if query_type not in [QueryType.AI_TEXT_RESPONSE, QueryType.COMMIT_QUERY]:
        start_time = time.time()
        if query_type == QueryType.ALL_IMAGES:
            found_images = services["illustration_service"].get_all()
        else:
            found_images = services["illustration_service"].search(search_term)
        ai_response = (
            f"Here are illustrations for '{search_term}'."
            if found_images
            else f"Sorry, no illustrations found for '{search_term}'."
        )
        followup_questions = services["followup_service"].generate_followups(
            sanitized_question, ai_response, sanitized_history
        )
        response_data = services["response_service"].build_image_response(
            search_term, found_images, start_time, followup_questions
        )
        return JSONResponse(content=response_data.model_dump())

    if not services["retrievers"]:
        raise HTTPException(status_code=503, detail="AI service temporarily unavailable")

    formatted_chat_history = [
        (HumanMessage(content=msg["text"]) if msg["sender"] == "user" else AIMessage(content=msg["text"]))
        for msg in sanitized_history
    ]

    text_stream, actual_model_used = await stream_with_fallback(
        services["retrievers"], formatted_chat_history, sanitized_question, query.preferred_model
    )

    followup_questions = services["followup_service"].generate_followups(sanitized_question, "", sanitized_history)

    headers = {
        "X-Model-Used": actual_model_used,
        "X-Followup-Questions": json.dumps(followup_questions),
    }

    return StreamingResponse(text_stream, media_type="text/plain", headers=headers)
