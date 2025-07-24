import logging
import time
import re
import os
import json
from typing import List, Optional, Iterator
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
# FIX 1: Import the missing function 'create_multi_vector_retriever'
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

class Message(BaseModel):
    sender: str
    text: str
class Query(BaseModel):
    question: str
    chat_history: List[Message] = Field(default=[])
    preferred_model: Optional[str] = None
class SecurityValidator:
    @staticmethod
    def validate_query(query): return True, ""
    @staticmethod
    def sanitize_input(text: str): return text

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
# FIX 2: Add 'request: Request' to the function signature for the rate limiter
async def query_endpoint(request: Request, query: Query):
    is_valid, error_msg = SecurityValidator.validate_query(query)
    if not is_valid: raise HTTPException(status_code=400, detail=error_msg)

    sanitized_question = SecurityValidator.sanitize_input(query.question)
    query_type, search_term = query_router.route_query(sanitized_question.lower().strip())
    conversation_history = [{"sender": msg.sender, "text": msg.text} for msg in query.chat_history]

    if query_type != QueryType.AI_TEXT_RESPONSE:
        start_time = time.time()
        if query_type == QueryType.ALL_IMAGES:
            found_images = illustration_service.get_all()
        else:
            found_images = illustration_service.search(search_term)
        ai_response = f"Here are illustrations for '{search_term}'." if found_images else f"Sorry, no illustrations found for '{search_term}'."
        followup_questions = followup_service.generate_followups(sanitized_question, ai_response, conversation_history)
        response_data = response_service.build_image_response(search_term, found_images, start_time, followup_questions)
        return JSONResponse(content=response_data.model_dump())

    if not retrievers:
        raise HTTPException(status_code=503, detail="AI service temporarily unavailable")

    formatted_chat_history = [HumanMessage(content=msg.text) if msg.sender == "user" else AIMessage(content=msg.text) for msg in query.chat_history]

    text_stream = stream_with_fallback(retrievers, formatted_chat_history, sanitized_question, query.preferred_model)

    primary_llm = os.getenv("PRIMARY_LLM", "claude")
    model_used = query.preferred_model if query.preferred_model in ["claude", "gemini"] else primary_llm
    followup_questions = followup_service.generate_followups(sanitized_question, "", conversation_history)

    headers = {
        "X-Model-Used": model_used,
        "X-Followup-Questions": json.dumps(followup_questions),
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "no-cache"
    }

    return StreamingResponse(text_stream, media_type="text/plain", headers=headers)