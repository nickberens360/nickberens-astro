# backend/main.py
import logging
import time
from typing import List, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Import rate limiting components
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Import your custom modules
from .core.config import AppConfig
from .core.data_loader import load_all_documents
from .core.llm_chain import create_full_retrieval_chain, invoke_with_fallback
from .core.illustration_service import IllustrationService
from .core.query_router import QueryRouter, QueryType
from .core.response_service import ResponseService, QueryResponse
from .core.followup_service import FollowUpService
from langchain_core.messages import HumanMessage, AIMessage

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=getattr(logging, AppConfig.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Setup Rate Limiter ---
limiter = Limiter(key_func=get_remote_address)

# --- Setup Application ---
app = FastAPI(
    title=AppConfig.APP_TITLE,
    description=AppConfig.APP_DESCRIPTION,
    version=AppConfig.APP_VERSION
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- Initialize Services ---
query_router = QueryRouter()
response_service = ResponseService()
followup_service = FollowUpService()


# Add request timing middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    # Only log non-health check requests to reduce noise
    if not request.url.path.startswith(("/health", "/status")):
        logger.info(
            f"Request: {request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Time: {process_time:.3f}s"
        )
    return response


class Message(BaseModel):
    sender: str = Field(..., description="Either 'user' or 'assistant'")
    text: str = Field(..., description="The message content")


class Query(BaseModel):
    question: str = Field(..., min_length=1, description="The user's question")
    chat_history: List[Message] = Field(default=[], description="Previous conversation history")
    preferred_model: Optional[str] = Field(default=None, description="User's preferred model (claude or gemini)")


def initialize_illustration_service():
    """Initialize the illustration service."""
    try:
        service = IllustrationService(
            illustrations_path=AppConfig.ILLUSTRATIONS_PATH,
            search_threshold=AppConfig.SEARCH_THRESHOLD,
            max_results=AppConfig.MAX_RESULTS
        )
        is_valid, message = service.validate_data()
        logger.info(message)
        return service
    except Exception as e:
        logger.error(f"Failed to initialize illustration service: {e}")
        return None


def initialize_app_state():
    """Initialize application state with error handling."""
    try:
        logger.info("Initializing application state...")
        logger.info(f"Primary LLM configured: {AppConfig.PRIMARY_LLM}")

        logger.info("Loading documents...")
        all_docs = load_all_documents()
        logger.info(f"Loaded {len(all_docs)} documents")

        logger.info("Creating retrieval chain...")
        retriever = create_full_retrieval_chain(all_docs)

        logger.info("Initializing illustration service...")
        illustration_service = initialize_illustration_service()

        logger.info("Application initialization complete")
        return retriever, illustration_service
    except Exception as e:
        logger.error(f"Failed to initialize app state: {e}")
        raise


# Initialize app state
try:
    retriever, illustration_service = initialize_app_state()
    app_initialized = True
except Exception as e:
    logger.critical(f"Application startup failed: {e}")
    retriever, illustration_service = None, None
    app_initialized = False

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=AppConfig.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


def handle_image_query(query_type: QueryType, search_term: str, start_time: float, user_question: str, conversation_history: List = None) -> QueryResponse:
    """Handle image-related queries."""
    if not illustration_service:
        logger.warning("Illustration service not available")
        followup_questions = followup_service.generate_followups(
            user_question,
            "No illustrations available",
            conversation_history
        )
        return response_service.build_no_images_response(start_time, followup_questions)

    if query_type == QueryType.ALL_IMAGES:
        found_images = illustration_service.get_all()
        ai_response = "Of course! Here are some of my illustrations:"
    else:
        found_images = illustration_service.search(search_term)
        if found_images:
            ai_response = f"Here are the illustrations I found for '{search_term}':"
        else:
            ai_response = f"Sorry, I couldn't find any illustrations matching '{search_term}'."

    # Generate follow-up questions
    followup_questions = followup_service.generate_followups(
        user_question,
        ai_response,
        conversation_history
    )

    return response_service.build_image_response(
        search_term,
        found_images,
        start_time,
        followup_questions
    )


def handle_ai_query(query: Query, start_time: float) -> QueryResponse:
    """Handle AI text queries."""
    if not retriever:
        raise HTTPException(
            status_code=503,
            detail="AI service temporarily unavailable - app not properly initialized"
        )

    # Format chat history for LLM
    formatted_chat_history = []
    conversation_history = []  # For follow-up service

    for message in query.chat_history:
        # For LLM
        if message.sender == 'user':
            formatted_chat_history.append(HumanMessage(content=message.text))
        elif message.sender in ['assistant', 'ai', 'bot']:
            formatted_chat_history.append(AIMessage(content=message.text))

        # For follow-up service (simpler format)
        conversation_history.append({
            "sender": message.sender,
            "text": message.text
        })

    # Get AI response with enhanced error handling
    try:
        answer, model_used = invoke_with_fallback(
            retriever,
            formatted_chat_history,
            query.question,
            query.preferred_model  # Pass the preferred model
        )

        if not answer:
            answer = "I'm sorry, I couldn't generate a response. Please try rephrasing your question."
            model_used = "fallback"

        # Generate follow-up questions
        followup_questions = followup_service.generate_followups(
            query.question,
            answer,
            conversation_history
        )

        return response_service.build_ai_response(answer, start_time, model_used, followup_questions, model_used)

    except Exception as llm_error:
        logger.error(f"LLM processing failed: {llm_error}")
        error_message = (
            "I'm sorry, I'm currently experiencing technical difficulties with the AI service. "
            "This might be due to high demand or temporary service issues. Please try again in a few moments."
        )

        # Even for errors, provide helpful follow-ups
        followup_questions = [
            "Tell me about Nick's experience",
            "Show me his illustrations",
            "What technologies does he work with?"
        ]

        return response_service.build_error_response(error_message, start_time, "fallback", followup_questions, "error")


# --- API Endpoints ---

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy" if app_initialized else "degraded",
        "message": AppConfig.APP_TITLE,
        "primary_llm": AppConfig.PRIMARY_LLM,
        "version": AppConfig.APP_VERSION
    }


@app.get("/health")
async def health_check():
    """Detailed health check."""
    illustration_count = illustration_service.get_count() if illustration_service else 0

    return {
        "status": "healthy" if app_initialized else "degraded",
        "app_initialized": app_initialized,
        "components": {
            "retriever": retriever is not None,
            "illustrations": illustration_count > 0,
            "illustrations_count": illustration_count
        },
        "configuration": {
            "primary_llm": AppConfig.PRIMARY_LLM,
            "search_threshold": AppConfig.SEARCH_THRESHOLD,
            "max_results": AppConfig.MAX_RESULTS
        }
    }


@app.get("/status")
async def status():
    """Simple status check."""
    return {
        "status": "online",
        "timestamp": time.time(),
        "primary_llm": AppConfig.PRIMARY_LLM,
        "app_initialized": app_initialized
    }


@app.get("/cache-stats")
async def cache_stats():
    """Get cache statistics for monitoring."""
    try:
        from .core.llm_chain import get_cache_stats
        return get_cache_stats()
    except ImportError:
        return {"error": "Cache stats not available"}
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return {"error": "Unable to retrieve cache stats"}


@app.get("/llm-status")
async def llm_status():
    """Check LLM service status."""
    try:
        from .core.llm_chain import get_llm_instances
        llms = get_llm_instances()
        return {
            "primary_llm": AppConfig.PRIMARY_LLM,
            "claude_available": llms.get('claude') is not None,
            "gemini_available": llms.get('gemini') is not None,
            "models": {
                "claude": AppConfig.CLAUDE_MODEL,
                "gemini": AppConfig.GEMINI_MODEL
            }
        }
    except Exception as e:
        logger.error(f"Error checking LLM status: {e}")
        return {"error": "Unable to check LLM status", "detail": str(e)}


@app.post("/query", response_model=QueryResponse)
@limiter.limit(AppConfig.RATE_LIMIT)
async def query_endpoint(request: Request, query: Query) -> QueryResponse:
    """
    Main query endpoint that handles both text queries and illustration searches.
    """
    start_time = time.time()

    try:
        question = query.question.lower().strip()
        logger.info(f"Processing query: {question[:50]}{'...' if len(question) > 50 else ''}")

        # Log model preference
        if query.preferred_model:
            logger.info(f"User requested model: {query.preferred_model}")

        # Route the query to determine its type
        query_type, search_term = query_router.route_query(question)

        # Convert chat history for follow-up service
        conversation_history = [
            {"sender": msg.sender, "text": msg.text}
            for msg in query.chat_history
        ]

        # Handle image queries
        if query_type != QueryType.AI_TEXT_RESPONSE:
            return handle_image_query(query_type, search_term, start_time, query.question, conversation_history)

        # Handle AI text queries
        return handle_ai_query(query, start_time)

    except HTTPException:
        raise
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Error processing query after {processing_time:.3f}s: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error - please try again later"
        )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Global exception handler with better logging."""
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}")
    return {
        "error": "An unexpected error occurred",
        "path": request.url.path,
        "method": request.method
    }


# Startup event
@app.on_event("startup")
async def startup_event():
    """Log startup information."""
    logger.info("=== Nick Berens Portfolio API Starting ===")
    logger.info(f"Primary LLM: {AppConfig.PRIMARY_LLM}")
    logger.info(f"App initialized: {app_initialized}")

    if illustration_service:
        logger.info(f"Illustration service initialized with {illustration_service.get_count()} illustrations")

    logger.info("=== Startup Complete ===")


# Development server
if __name__ == "__main__":
    import uvicorn

    logger.info("Starting development server...")
    uvicorn.run(
        app,
        host=AppConfig.HOST,
        port=AppConfig.PORT,
        log_level=AppConfig.LOG_LEVEL.lower(),
        reload=True
    )

print("Backend setup complete. Ready for queries with Claude as primary LLM.")
