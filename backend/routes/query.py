"""
Main query endpoint for handling user questions and requests.

This module contains the primary query endpoint that:
- Validates and sanitizes user input
- Routes queries to appropriate handlers (images vs text)
- Handles streaming responses for AI text generation
- Applies rate limiting and security validation
- Manages LLM rate limit status and fallback
"""

import json
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage

from ..core.app_factory import limiter
from ..core.config import AppConfig
from ..core.llm_chain import stream_with_fallback, get_rate_limit_status
from ..core.query_router import QueryType
from ..dependencies import get_services
from ..models.request_models import Query
from ..security.validator import SecurityValidator

# Initialize router
router = APIRouter()


@router.get("/rate-limits")
async def get_rate_limits():
    """Get current rate limit status for all LLM providers"""
    try:
        status = get_rate_limit_status()
        return JSONResponse(content={"rate_limits": status})
    except Exception as e:
        print(f"Error getting rate limits: {e}")
        return JSONResponse(
            content={"error": "Failed to get rate limit status", "rate_limits": {}},
            status_code=500
        )


@router.post("/query")
@limiter.limit(AppConfig.RATE_LIMIT)
async def query_endpoint(request: Request, query: Query, services: dict = Depends(get_services)):
    from slowapi.util import get_remote_address

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

    # Handle image queries
    if query_type != QueryType.AI_TEXT_RESPONSE:
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

        # Add rate limit status to image responses too
        rate_limits = get_rate_limit_status()
        response_dict = response_data.model_dump()
        response_dict["rate_limits"] = rate_limits

        return JSONResponse(content=response_dict)

    # Handle AI text responses
    if not services["retrievers"]:
        raise HTTPException(status_code=503, detail="AI service temporarily unavailable")

    formatted_chat_history = [
        (HumanMessage(content=msg["text"]) if msg["sender"] == "user" else AIMessage(content=msg["text"]))
        for msg in sanitized_history
    ]

    # Get current rate limit status before processing
    current_rate_limits = get_rate_limit_status()

    # If user's preferred model is rate limited, log a warning and let the system fallback
    if query.preferred_model and current_rate_limits.get(query.preferred_model, False):
        from logging import getLogger
        logger = getLogger(__name__)
        logger.warning(f"User requested {query.preferred_model} but it's rate limited. Will fallback to available model.")

    text_stream, actual_model_used, metadata = await stream_with_fallback(
        services["retrievers"], formatted_chat_history, sanitized_question, query.preferred_model
    )

    followup_questions = services["followup_service"].generate_followups(
        sanitized_question, "", sanitized_history
    )

    # Include rate limit status in headers
    headers = {
        "X-Model-Used": actual_model_used,
        "X-Followup-Questions": json.dumps(followup_questions),
        "X-Rate-Limits": json.dumps(metadata.get("rate_limit_status", {})),
    }

    return StreamingResponse(text_stream, media_type="text/plain", headers=headers)
