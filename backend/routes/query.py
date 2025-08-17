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
import logging
import time
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
import uuid
from fastapi.responses import JSONResponse, StreamingResponse
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from ..core.app_factory import limiter
from ..core.config import AppConfig
from ..core.llm_chain import get_rate_limit_status, stream_with_fallback
from ..core.query_logger import get_query_logger
from ..core.query_router import QueryType
from ..dependencies import get_services
from ..models.request_models import Query
from ..security.validator import SecurityValidator

# Initialize router and logger
router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/query")
@limiter.limit(AppConfig.RATE_LIMIT)
async def query_endpoint(request: Request, query: Query, services: dict = Depends(get_services)):
    from slowapi.util import get_remote_address

    # Get client IP and query logger
    client_ip = get_remote_address(request)

    # Check for proxy headers to get the real client IP.
    # Note: This assumes the service is behind a trusted proxy.
    forwarded_for = request.headers.get("X-Forwarded-For")
    real_ip = request.headers.get("X-Real-IP")

    if forwarded_for:
        # Use the first IP in the chain (original client)
        client_ip = forwarded_for.split(",")[0].strip()
    elif real_ip:
        client_ip = real_ip.strip()

    query_logger = get_query_logger()
    request_id = str(uuid.uuid4())
    start_time = time.time()

    # Restore validation and sanitization calls
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
        illustration_service = services.get("illustration_service")
        if illustration_service is None:
            found_images = []
            logger.warning("Illustration service not available - returning empty results")
        else:
            if query_type == QueryType.ALL_IMAGES:
                found_images = illustration_service.get_all()
            else:
                found_images = illustration_service.search(search_term)

        ai_response = (
            f"Here are illustrations for '{search_term}'."
            if found_images
            else f"Sorry, no illustrations found for '{search_term}'."
        )

        followup_service = services.get("followup_service")
        followup_questions = (
            followup_service.generate_followups(sanitized_question, ai_response, sanitized_history)
            if followup_service
            else []
        )

        response_service = services.get("response_service")
        if response_service is None:
            logger.error("Response service not available - cannot build image response")
            raise HTTPException(status_code=503, detail="Image service temporarily unavailable")

        response_data = response_service.build_image_response(search_term, found_images, start_time, followup_questions)

        # Add rate limit status to image responses too
        rate_limits = get_rate_limit_status()
        response_dict = response_data.model_dump()
        response_dict["rate_limits"] = rate_limits

        # Log the image query
        response_time = time.time() - start_time
        query_logger.log_query(
            client_ip=client_ip,
            question=sanitized_question,
            response=ai_response,
            model_used="image_search",
            query_type="image",
            response_time=response_time,
            metadata={
                "search_term": search_term,
                "images_found": len(found_images),
                "query_type_enum": query_type.value,
            },
        )

        return JSONResponse(content=response_dict)

    # Handle AI text responses using smart retriever
    formatted_chat_history: List[BaseMessage] = [
        (HumanMessage(content=msg["text"]) if msg["sender"] == "user" else AIMessage(content=msg["text"]))
        for msg in sanitized_history
    ]

    # Get current rate limit status before processing
    current_rate_limits = get_rate_limit_status()

    # If user's preferred model is rate limited, log a warning and let the system fallback
    if query.preferred_model and current_rate_limits.get(query.preferred_model, False):
        logger.warning(
            f"User requested {query.preferred_model} but it's rate limited. Will fallback to available model."
        )

    # Use the enhanced retriever system (now with smart routing built-in)
    try:
        # Log smart routing info for debugging if unified retriever is available
        from ..core.app_initializer_v2 import get_unified_retriever
        from ..core.smart_query_handler import SmartQueryHandler

        unified_retriever = get_unified_retriever(services["retrievers"])
        if unified_retriever:
            llm = request.app.state.llm
            if not llm:
                logger.error("LLM not initialized, skipping smart query analysis.")
            else:
                smart_handler = SmartQueryHandler(unified_retriever, llm)
                intent_analysis = smart_handler.analyze_query_with_llm(sanitized_question)
                logger.info(
                    f"Smart routing: Query '{sanitized_question}' -> Topics: {intent_analysis.get('topics', [])} | Complexity: {intent_analysis.get('complexity')}"
                )

        text_stream, actual_model_used, metadata = await stream_with_fallback(
            services["retrievers"],
            formatted_chat_history,
            sanitized_question,
            query.preferred_model,
            client_ip=client_ip,
            question=sanitized_question,
            request_id=request_id,
        )

        # If we get here, the LLM fallback succeeded, so return 200
    except Exception as e:
        # Only return 503 if both retrievers and LLM fallback fail
        logger.error(f"Both retrievers and LLM fallback failed: {e}")
        raise HTTPException(status_code=503, detail="AI service temporarily unavailable")

    followup_service = services.get("followup_service")
    followup_questions = (
        followup_service.generate_followups(sanitized_question, "", sanitized_history) if followup_service else []
    )

    # Log the streaming text query (response will be marked as [STREAMING])
    response_time = time.time() - start_time
    query_logger.log_streaming_query(
        client_ip=client_ip,
        question=sanitized_question,
        model_used=actual_model_used,
        response_time=response_time,
        metadata={
            "preferred_model": query.preferred_model,
            "chat_history_length": len(sanitized_history),
            "followup_questions": followup_questions,
            **metadata,
        },
        request_id=request_id,
    )

    # Include rate limit status in headers
    headers = {
        "X-Model-Used": actual_model_used,
        "X-Followup-Questions": json.dumps(followup_questions),
        "X-Rate-Limits": json.dumps(metadata.get("rate_limit_status", {})),
    }

    return StreamingResponse(text_stream, media_type="text/plain", headers=headers)
