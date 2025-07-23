# backend/main.py
import logging
import time
import re
from typing import List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
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


# --- Security Validator ---
class SecurityValidator:
    """Centralized input validation and security checks."""

    # Configuration
    MAX_QUERY_LENGTH = 1000
    MAX_CHAT_HISTORY_LENGTH = 10  # Maximum number of messages
    MAX_MESSAGE_LENGTH = 1000
    MAX_PROCESSING_TIME = 30  # seconds

    # Progressive length thresholds
    QUERY_WARNING_THRESHOLD = int(0.9 * MAX_QUERY_LENGTH)  # 90% of max query length
    MESSAGE_WARNING_THRESHOLD = 900  # 90% of max message length
    CHUNK_SIZE = 1500  # For text chunking when needed

    # Suspicious patterns (basic prompt injection detection)
    SUSPICIOUS_PATTERNS = [
        r'ignore\s+(previous|above|all)\s+instructions?',
        r'system\s*:?\s*you\s+are\s+now',
        r'forget\s+everything\s+(above|before)',
        r'new\s+instructions?\s*:',
        r'</?\s*(script|iframe|object|embed|form)',  # Basic HTML injection
        r'javascript\s*:',
        r'data\s*:\s*text/html',
        r'(prompt|system)\s+(injection|hack|override)',
        r'act\s+as\s+if\s+you\s+are',
        r'pretend\s+(you\s+are|to\s+be)',
    ]

    ALLOWED_MODELS = ['claude', 'gemini', None]

    # Simple rate limiting storage (in production, use Redis)
    _user_requests = defaultdict(list)

    @classmethod
    def validate_query(cls, query, client_ip: str) -> tuple[bool, str]:
        """
        Comprehensive query validation.
        Returns: (is_valid, error_message)
        """
        try:
            # 1. Basic input validation
            if not query.question or not isinstance(query.question, str):
                return False, "Question is required and must be text"

            # 2. Length limits
            if len(query.question) > cls.MAX_QUERY_LENGTH:
                return False, f"Question too long (max {cls.MAX_QUERY_LENGTH} characters)"

            # 3. Chat history validation
            if query.chat_history:
                if len(query.chat_history) > cls.MAX_CHAT_HISTORY_LENGTH:
                    return False, f"Chat history too long (max {cls.MAX_CHAT_HISTORY_LENGTH} messages)"

                for i, msg in enumerate(query.chat_history):
                    if not isinstance(msg.text, str):
                        return False, f"Message {i+1} text must be string"

                    if len(msg.text) > cls.MAX_MESSAGE_LENGTH:
                        return False, f"Message {i+1} too long (max {cls.MAX_MESSAGE_LENGTH} characters)"

                    if msg.sender not in ['user', 'assistant', 'ai', 'bot']:
                        return False, f"Invalid sender in message {i+1}"

            # 4. Model preference validation
            if query.preferred_model and query.preferred_model not in cls.ALLOWED_MODELS:
                return False, "Invalid model preference"

            # 5. Content filtering (basic prompt injection detection)
            combined_text = query.question.lower()
            if query.chat_history:
                combined_text += " " + " ".join([msg.text.lower() for msg in query.chat_history])

            for pattern in cls.SUSPICIOUS_PATTERNS:
                if re.search(pattern, combined_text, re.IGNORECASE):
                    logger.warning(f"Suspicious pattern detected from {client_ip}: {pattern}")
                    return False, "Content not allowed"

            # 6. Rate limiting (per IP)
            if not cls._check_rate_limit(client_ip):
                return False, "Rate limit exceeded"

            return True, ""

        except Exception as e:
            logger.error(f"Error validating query: {e}")
            return False, "Validation error"

    @classmethod
    def _check_rate_limit(cls, client_ip: str) -> bool:
        """
        Simple rate limiting: 10 requests per minute per IP.
        In production, use Redis with sliding window.
        """
        try:
            now = datetime.now()
            minute_ago = now - timedelta(minutes=1)

            # Clean old requests
            cls._user_requests[client_ip] = [
                req_time for req_time in cls._user_requests[client_ip]
                if req_time > minute_ago
            ]

            # Check limit
            if len(cls._user_requests[client_ip]) >= 10:
                return False

            # Record this request
            cls._user_requests[client_ip].append(now)
            return True

        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            return True  # Allow request if rate limiting fails

    @classmethod
    def check_length_status(cls, text: str, text_type: str = "query") -> dict:
        """
        Check text length and return status information.
        Returns: {
            'length': int,
            'max_length': int,
            'status': 'ok'|'warning'|'error',
            'message': str,
            'needs_chunking': bool
        }
        """
        length = len(text)

        if text_type == "query":
            max_length = cls.MAX_QUERY_LENGTH
            warning_threshold = cls.QUERY_WARNING_THRESHOLD
        else:  # message
            max_length = cls.MAX_MESSAGE_LENGTH
            warning_threshold = cls.MESSAGE_WARNING_THRESHOLD

        if length <= warning_threshold:
            status = "ok"
            message = f"Text length is within normal limits ({length}/{max_length})"
        elif length <= max_length:
            status = "warning"
            message = f"Text is approaching length limit ({length}/{max_length})"
        else:
            status = "error"
            message = f"Text exceeds maximum length ({length}/{max_length})"

        needs_chunking = length > cls.CHUNK_SIZE

        return {
            'length': length,
            'max_length': max_length,
            'status': status,
            'message': message,
            'needs_chunking': needs_chunking
        }

    @classmethod
    def chunk_text(cls, text: str, chunk_size: int = None) -> list[str]:
        """
        Split large text into smaller chunks while preserving sentence boundaries.
        """
        if chunk_size is None:
            chunk_size = cls.CHUNK_SIZE

        if len(text) <= chunk_size:
            return [text]

        chunks = []
        current_chunk = ""

        # Split by sentences first
        sentences = re.split(r'(?<=[.!?])\s+', text)

        for sentence in sentences:
            # If adding this sentence would exceed chunk size
            if len(current_chunk) + len(sentence) > chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = sentence
                else:
                    # Single sentence is too long, split by words
                    words = sentence.split()
                    temp_chunk = ""
                    for word in words:
                        if len(temp_chunk) + len(word) + 1 > chunk_size:
                            if temp_chunk:
                                chunks.append(temp_chunk.strip())
                                temp_chunk = word
                            else:
                                # Single word is too long, force split
                                chunks.append(word[:chunk_size])
                                temp_chunk = word[chunk_size:]
                        else:
                            temp_chunk += (" " + word) if temp_chunk else word
                    current_chunk = temp_chunk
            else:
                current_chunk += (" " + sentence) if current_chunk else sentence

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    @classmethod
    def sanitize_input(cls, text: str) -> str:
        """Sanitize input text while preserving meaning."""
        if not isinstance(text, str):
            return ""

        # Remove null bytes and control characters
        sanitized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

        # Normalize whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()

        # Limit length as final safety
        return sanitized[:cls.MAX_QUERY_LENGTH]

    @classmethod
    def log_request_metrics(cls, client_ip: str, text_length: int, processing_time: float = None):
        """Enhanced request monitoring and logging."""
        try:
            # Log basic metrics
            logger.info(f"Request metrics - IP: {client_ip}, Text length: {text_length}")

            # Log warnings for large requests
            if text_length > cls.QUERY_WARNING_THRESHOLD:
                logger.warning(f"Large text input from {client_ip}: {text_length} characters")

            if processing_time and processing_time > 10:  # Log slow requests
                logger.warning(f"Slow request from {client_ip}: {processing_time:.2f}s")

        except Exception as e:
            logger.error(f"Error logging request metrics: {e}")


# --- Data Models ---
class Message(BaseModel):
    sender: str = Field(..., description="Either 'user' or 'assistant'")
    text: str = Field(..., min_length=1, max_length=SecurityValidator.MAX_MESSAGE_LENGTH, description="The message content")


class Query(BaseModel):
    question: str = Field(..., min_length=1, max_length=SecurityValidator.MAX_QUERY_LENGTH, description="The user's question")
    chat_history: List[Message] = Field(default=[], description="Previous conversation history")
    preferred_model: Optional[str] = Field(default=None, description="User's preferred model (claude or gemini)")


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


# --- Security Middleware ---
@app.middleware("http")
async def security_middleware(request: Request, call_next):
    """Add security headers and basic protection."""
    start_time = time.time()

    # Basic security checks
    user_agent = request.headers.get("user-agent", "")
    if len(user_agent) > 500:  # Unusually long user agent
        logger.warning(f"Suspicious user agent from {request.client.host}")

    # Content length check for non-GET requests
    if request.method != "GET":
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 100000:  # 100KB limit
            logger.warning(f"Large request from {request.client.host}: {content_length} bytes")

    response = await call_next(request)
    process_time = time.time() - start_time

    # Add security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"

    # Only log non-health check requests
    if not request.url.path.startswith(("/health", "/status")):
        logger.info(
            f"Request: {request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Time: {process_time:.3f}s - "
            f"IP: {request.client.host}"
        )

    return response


# --- Helper Functions ---
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

# Setup CORS with security improvements
app.add_middleware(
    CORSMiddleware,
    allow_origins=AppConfig.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # Removed ["*"]
    allow_headers=["Content-Type", "Authorization"],  # Removed ["*"]
)


# --- Query Handlers ---
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
    Main query endpoint with enhanced security validation.
    """
    start_time = time.time()
    client_ip = request.client.host

    try:
        # 1. Security validation
        is_valid, error_msg = SecurityValidator.validate_query(query, client_ip)
        if not is_valid:
            logger.warning(f"Query validation failed from {client_ip}: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)

        # 2. Input sanitization
        sanitized_question = SecurityValidator.sanitize_input(query.question)
        if not sanitized_question:
            raise HTTPException(status_code=400, detail="Invalid question format")

        # 3. Processing timeout protection
        processing_timeout = time.time() + SecurityValidator.MAX_PROCESSING_TIME

        logger.info(f"Processing query from {client_ip}: {sanitized_question[:50]}{'...' if len(sanitized_question) > 50 else ''}")

        # Log model preference securely
        if query.preferred_model:
            logger.info(f"User requested model: {query.preferred_model}")

        # 4. Route the query
        query_type, search_term = query_router.route_query(sanitized_question.lower().strip())

        # Convert chat history for follow-up service (with validation)
        conversation_history = []
        for msg in query.chat_history:
            sanitized_text = SecurityValidator.sanitize_input(msg.text)
            if sanitized_text:  # Only include non-empty messages
                conversation_history.append({
                    "sender": msg.sender,
                    "text": sanitized_text
                })

        # 5. Handle image queries
        if query_type != QueryType.AI_TEXT_RESPONSE:
            # Check timeout
            if time.time() > processing_timeout:
                raise HTTPException(status_code=408, detail="Request timeout")

            return handle_image_query(
                query_type, search_term, start_time,
                sanitized_question, conversation_history
            )

        # 6. Handle AI text queries with timeout protection
        if time.time() > processing_timeout:
            raise HTTPException(status_code=408, detail="Request timeout")

        # Create sanitized query object
        sanitized_query = Query(
            question=sanitized_question,
            chat_history=[
                Message(sender=msg["sender"], text=msg["text"])
                for msg in conversation_history
            ],
            preferred_model=query.preferred_model
        )

        return handle_ai_query(sanitized_query, start_time)

    except HTTPException:
        raise
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Error processing query from {client_ip} after {processing_time:.3f}s: {str(e)[:200]}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error - please try again later"
        )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Global exception handler with better logging."""
    client_ip = getattr(request.client, 'host', 'unknown')
    logger.error(f"Unhandled exception from {client_ip} on {request.method} {request.url.path}: {str(exc)[:200]}")
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

print("Backend setup complete with enhanced security. Ready for queries with Claude as primary LLM.")