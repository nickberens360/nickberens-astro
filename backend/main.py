import logging
import time
import re
import os
import json
from typing import List, Optional
from collections import defaultdict
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.responses import StreamingResponse, JSONResponse

from .core.config import AppConfig
from .core.data_loader import load_all_documents
from .core.llm_chain import create_multi_vector_retriever, stream_with_fallback
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from .core.illustration_service import IllustrationService
from .core.query_router import QueryRouter, QueryType
from .core.response_service import ResponseService
from .core.followup_service import FollowUpService
from langchain_core.messages import HumanMessage, AIMessage
from .scripts.build_unified_data import build_unified_data

load_dotenv()
logging.basicConfig(level=getattr(logging, AppConfig.LOG_LEVEL), format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

# --- START OF RESTORED SECURITY LOGIC ---

class SecurityValidator:
    MAX_QUERY_LENGTH = 1000
    MAX_CHAT_HISTORY_LENGTH = 10
    MAX_MESSAGE_LENGTH = 1000
    SUSPICIOUS_PATTERNS = [
        r'ignore\s+(previous|above|all)\s+instructions?',
        r'system\s*:?\s*you\s+are\s+now',
        r'forget\s+everything\s+(above|before)',
        r'new\s+instructions?\s*:',
        r'</?\s*(script|iframe|object|embed|form)',
        r'javascript\s*:',
        r'data\s*:\s*text/html',
        r'(prompt|system)\s+(injection|hack|override)',
        r'act\s+as\s+if\s+you\s+are',
        r'pretend\s+(you\s+are|to\s+be)',
    ]
    ALLOWED_MODELS = ["claude", "gemini", None]
    _user_requests = defaultdict(list)

    @classmethod
    def validate_query(cls, query, client_ip: str) -> tuple[bool, str]:
        try:
            if not query.question or not isinstance(query.question, str):
                return False, "Question is required and must be text"
            if len(query.question) > cls.MAX_QUERY_LENGTH:
                return False, f"Question too long (max {cls.MAX_QUERY_LENGTH} characters)"
            if query.chat_history:
                if len(query.chat_history) > cls.MAX_CHAT_HISTORY_LENGTH:
                    return False, f"Chat history too long (max {cls.MAX_CHAT_HISTORY_LENGTH} messages)"
                for i, msg in enumerate(query.chat_history):
                    if not isinstance(msg.text, str) or len(msg.text) > cls.MAX_MESSAGE_LENGTH:
                        return False, f"Message {i+1} invalid or too long (max {cls.MAX_MESSAGE_LENGTH} characters)"
            if query.preferred_model and query.preferred_model not in cls.ALLOWED_MODELS:
                return False, "Invalid model preference"

            combined_text = query.question.lower()
            if query.chat_history:
                combined_text += " " + " ".join([msg.text.lower() for msg in query.chat_history])
            for pattern in cls.SUSPICIOUS_PATTERNS:
                if re.search(pattern, combined_text, re.IGNORECASE):
                    logger.warning(f"Suspicious pattern detected from {client_ip}: {pattern}")
                    return False, "Content not allowed"

            # This internal rate limiting can be a secondary check to the main SlowAPI one.
            if not cls._check_rate_limit(client_ip):
                return False, "Rate limit exceeded"

            return True, ""
        except Exception as e:
            logger.error(f"Error validating query: {e}")
            return False, "Validation error"

    @classmethod
    def _check_rate_limit(cls, client_ip: str) -> bool:
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)
        # Prune old requests
        cls._user_requests[client_ip] = [req_time for req_time in cls._user_requests[client_ip] if req_time > minute_ago]
        # Check limit (e.g., 20 requests per minute)
        if len(cls._user_requests[client_ip]) >= 20:
            return False
        cls._user_requests[client_ip].append(now)
        return True

    @classmethod
    def sanitize_input(cls, text: str) -> str:
        if not isinstance(text, str): return ""
        # Remove control characters except for common whitespace
        sanitized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
        # Normalize whitespace and limit length
        return re.sub(r"\s+", " ", sanitized).strip()[:cls.MAX_QUERY_LENGTH]

# --- END OF RESTORED SECURITY LOGIC ---

class Message(BaseModel):
    sender: str
    text: str
class Query(BaseModel):
    question: str
    chat_history: List[Message] = Field(default=[])
    preferred_model: Optional[str] = None

app = FastAPI(title=AppConfig.APP_TITLE, description=AppConfig.APP_DESCRIPTION, version=AppConfig.APP_VERSION)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

query_router = QueryRouter()
response_service = ResponseService()
followup_service = FollowUpService()

def initialize_app_state():
    logger.info("Building structured unified data file...")
    build_unified_data()
    logger.info("Initializing application state with Multi-Vector RAG...")
    docs, illustrations_data = load_all_documents()
    embeddings = GoogleGenerativeAIEmbeddings(model=os.getenv("EMBEDDING_MODEL", "models/embedding-001"))
    all_retrievers = create_multi_vector_retriever(docs, embeddings)
    illustration_service = IllustrationService(all_retrievers.get("illustration"), illustrations_data)
    is_valid, message = illustration_service.validate_data()
    logger.info(message)
    return all_retrievers, illustration_service

try:
    retrievers, illustration_service = initialize_app_state()
    app_initialized = True
except Exception as e:
    logger.critical(f"Application startup failed: {e}", exc_info=True)
    retrievers, illustration_service = None, None
    app_initialized = False

app.add_middleware(CORSMiddleware, allow_origins=AppConfig.get_cors_origins(), allow_credentials=True, allow_methods=["*"], allow_headers=["*"], expose_headers=["X-Model-Used", "X-Followup-Questions"])

@app.get("/")
async def root(): return {"status": "healthy" if app_initialized else "degraded"}

@app.get("/status")
async def status_check():
    return {
        "status": "online" if app_initialized else "offline",
        "app_initialized": app_initialized
    }

@app.get("/health")
async def health_check():
    count = illustration_service.get_all() if illustration_service else []
    return {"status": "healthy" if app_initialized else "degraded", "illustration_count": len(count)}

@app.post("/query")
@limiter.limit(AppConfig.RATE_LIMIT)
async def query_endpoint(request: Request, query: Query):
    # Restore validation and sanitization calls
    client_ip = get_remote_address(request)
    is_valid, error_msg = SecurityValidator.validate_query(query, client_ip)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    sanitized_question = SecurityValidator.sanitize_input(query.question)

    # Sanitize chat history as well
    sanitized_history = [
        {"sender": msg.sender, "text": SecurityValidator.sanitize_input(msg.text)}
        for msg in query.chat_history
    ]

    query_type, search_term = query_router.route_query(sanitized_question.lower().strip())

    if query_type != QueryType.AI_TEXT_RESPONSE:
        start_time = time.time()
        if query_type == QueryType.ALL_IMAGES:
            found_images = illustration_service.get_all()
        else:
            found_images = illustration_service.search(search_term)
        ai_response = f"Here are illustrations for '{search_term}'." if found_images else f"Sorry, no illustrations found for '{search_term}'."
        followup_questions = followup_service.generate_followups(sanitized_question, ai_response, sanitized_history)
        response_data = response_service.build_image_response(search_term, found_images, start_time, followup_questions)
        return JSONResponse(content=response_data.model_dump())

    if not retrievers:
        raise HTTPException(status_code=503, detail="AI service temporarily unavailable")

    formatted_chat_history = [
        HumanMessage(content=msg["text"]) if msg["sender"] == "user" else AIMessage(content=msg["text"])
        for msg in sanitized_history
    ]

    text_stream = stream_with_fallback(retrievers, formatted_chat_history, sanitized_question, query.preferred_model)

    primary_llm = os.getenv("PRIMARY_LLM", "claude")
    model_used = query.preferred_model if query.preferred_model in ["claude", "gemini"] else primary_llm
    followup_questions = followup_service.generate_followups(sanitized_question, "", sanitized_history)

    headers = {
        "X-Model-Used": model_used,
        "X-Followup-Questions": json.dumps(followup_questions),
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "no-cache"
    }

    return StreamingResponse(text_stream, media_type="text/plain", headers=headers)