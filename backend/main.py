import logging
import time
import re
import os
from typing import List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Import new RAG architecture components
from .core.config import AppConfig
from .core.data_loader import load_all_documents
from .core.llm_chain import create_multi_vector_retriever, invoke_with_fallback
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from .core.illustration_service import IllustrationService
from .core.query_router import QueryRouter, QueryType
from .core.response_service import ResponseService, QueryResponse
from .core.followup_service import FollowUpService
from langchain_core.messages import HumanMessage, AIMessage

from .scripts.build_unified_data import build_unified_data

load_dotenv()

logging.basicConfig(level=getattr(logging, AppConfig.LOG_LEVEL), format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)

# --- Security Validator (unchanged) ---
class SecurityValidator:
    MAX_QUERY_LENGTH = 1000
    MAX_CHAT_HISTORY_LENGTH = 10
    MAX_MESSAGE_LENGTH = 1000
    SUSPICIOUS_PATTERNS = [r'ignore\s+instructions', r'system\s*:', r'</?\s*(script|iframe|object|embed|form)']

    @classmethod
    def validate_query(cls, query, client_ip: str) -> tuple[bool, str]:
        if not query.question or not isinstance(query.question, str) or len(query.question) > cls.MAX_QUERY_LENGTH:
            return False, "Invalid question format or length."
        if any(re.search(pattern, query.question, re.IGNORECASE) for pattern in cls.SUSPICIOUS_PATTERNS):
            logger.warning(f"Suspicious pattern detected from {client_ip}.")
            return False, "Content not allowed."
        return True, ""

    @classmethod
    def sanitize_input(cls, text: str) -> str:
        if not isinstance(text, str): return ""
        return re.sub(r"\s+", " ", text).strip()[:cls.MAX_QUERY_LENGTH]

# --- Data Models (unchanged) ---
class Message(BaseModel):
    sender: str
    text: str
class Query(BaseModel):
    question: str
    chat_history: List[Message] = Field(default=[])
    preferred_model: Optional[str] = None

# --- Application Setup ---
app = FastAPI(title=AppConfig.APP_TITLE, description=AppConfig.APP_DESCRIPTION, version=AppConfig.APP_VERSION)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- Initialize Services ---
query_router = QueryRouter()
response_service = ResponseService()
followup_service = FollowUpService()

# --- NEW Initializer for Multi-Vector RAG ---
def initialize_app_state():
    logger.info("Building structured unified data file...")
    build_unified_data()

    logger.info("Initializing application state with Multi-Vector RAG...")
    docs, illustrations_data = load_all_documents()

    # Initialize embeddings model once
    embeddings = GoogleGenerativeAIEmbeddings(model=os.getenv("EMBEDDING_MODEL", "models/embedding-001"))

    # Create the dictionary of retrievers ("resume", "about", "illustration")
    all_retrievers = create_multi_vector_retriever(docs, embeddings)

    # Initialize the illustration service with its dedicated retriever
    illustration_retriever = all_retrievers.get("illustration")
    if not illustration_retriever:
        raise RuntimeError("Illustration retriever could not be created.")

    illustration_service = IllustrationService(illustration_retriever, illustrations_data)

    is_valid, message = illustration_service.validate_data()
    logger.info(message)

    # The main "retriever" for the app is now the dictionary of all retrievers
    return all_retrievers, illustration_service

try:
    retrievers, illustration_service = initialize_app_state()
    app_initialized = True
except Exception as e:
    logger.critical(f"Application startup failed: {e}", exc_info=True)
    retrievers, illustration_service = None, None
    app_initialized = False

# --- CORS Middleware (unchanged) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=AppConfig.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# --- Request Handlers ---
def handle_image_query(query_type: QueryType, search_term: str, start_time: float, user_question: str, conversation_history: List = None) -> QueryResponse:
    if not illustration_service:
        followup_questions = followup_service.generate_followups(user_question, "No illustrations available", conversation_history)
        return response_service.build_no_images_response(start_time, followup_questions)

    if query_type == QueryType.ALL_IMAGES:
        found_images = illustration_service.get_all()
    else:
        found_images = illustration_service.search(search_term)

    ai_response = f"Here are illustrations related to '{search_term}'." if found_images else f"Sorry, I couldn't find illustrations for '{search_term}'."
    followup_questions = followup_service.generate_followups(user_question, ai_response, conversation_history)
    return response_service.build_image_response(search_term, found_images, start_time, followup_questions)

def handle_ai_query(query: Query, start_time: float) -> QueryResponse:
    if not retrievers:
        raise HTTPException(status_code=503, detail="AI service temporarily unavailable")

    formatted_chat_history = [
        HumanMessage(content=msg.text) if msg.sender == "user" else AIMessage(content=msg.text)
        for msg in query.chat_history
    ]
    conversation_history = [{"sender": msg.sender, "text": msg.text} for msg in query.chat_history]

    answer, model_used = invoke_with_fallback(retrievers, formatted_chat_history, query.question, query.preferred_model)

    followup_questions = followup_service.generate_followups(query.question, answer, conversation_history)
    return response_service.build_ai_response(answer, start_time, model_used, followup_questions, model_used)

# --- API Endpoints ---
@app.get("/")
async def root():
    return {"status": "healthy" if app_initialized else "degraded", "message": AppConfig.APP_TITLE, "version": AppConfig.APP_VERSION}

@app.get("/health")
async def health_check():
    count = illustration_service.get_all() if illustration_service else []
    return {"status": "healthy" if app_initialized else "degraded", "illustration_count": len(count)}

@app.get("/status")
async def status_check():
    return {
        "status": "online" if app_initialized else "offline",
        "app_initialized": app_initialized
    }

@app.post("/query", response_model=QueryResponse)
@limiter.limit(AppConfig.RATE_LIMIT)
async def query_endpoint(request: Request, query: Query) -> QueryResponse:
    start_time = time.time()
    is_valid, error_msg = SecurityValidator.validate_query(query, request.client.host)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    sanitized_question = SecurityValidator.sanitize_input(query.question)
    query_type, search_term = query_router.route_query(sanitized_question.lower().strip())

    conversation_history = [{"sender": msg.sender, "text": SecurityValidator.sanitize_input(msg.text)} for msg in query.chat_history]

    if query_type != QueryType.AI_TEXT_RESPONSE:
        return handle_image_query(query_type, search_term or "all", start_time, sanitized_question, conversation_history)
    else:
        return handle_ai_query(query, start_time)