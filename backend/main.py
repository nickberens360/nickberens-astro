import os
import glob
import json
import re
import logging
import time
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Import the fuzzy matching library
from thefuzz import process

# Import rate limiting components
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Import your custom modules
from .core.data_loader import load_all_documents
from .core.llm_chain import create_full_retrieval_chain, invoke_with_fallback
from langchain_core.messages import HumanMessage, AIMessage

# Load environment variables
load_dotenv()

# Setup logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Configuration ---
SEARCH_THRESHOLD = int(os.getenv("SEARCH_THRESHOLD", "55"))
MAX_RESULTS = int(os.getenv("MAX_RESULTS", "15"))
ILLUSTRATIONS_PATH = os.getenv("ILLUSTRATIONS_PATH", "public/illustrations.json")
PRIMARY_LLM = os.getenv("PRIMARY_LLM", "claude")

# --- Setup Rate Limiter ---
limiter = Limiter(key_func=get_remote_address)

# --- Setup Application ---
app = FastAPI(
    title="Nick Berens Portfolio API",
    description="API for AI-powered responses and illustration search with Claude as primary LLM",
    version="2.0.0"
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


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


class QueryResponse(BaseModel):
    answer: str
    images: Optional[List[str]] = None
    processing_time: Optional[float] = None
    llm_used: Optional[str] = None


def load_illustrations() -> List[Dict[str, Any]]:
    """Load illustrations data from JSON file with error handling."""
    try:
        with open(ILLUSTRATIONS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            logger.info(f"Loaded {len(data)} illustrations")
            return data
    except FileNotFoundError:
        logger.warning(f"Illustrations file not found at {ILLUSTRATIONS_PATH}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in illustrations file: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error loading illustrations: {e}")
        return []


def initialize_app_state():
    """Initialize application state with error handling."""
    try:
        logger.info("Initializing application state...")
        logger.info(f"Primary LLM configured: {PRIMARY_LLM}")

        logger.info("Loading documents...")
        all_docs = load_all_documents()
        logger.info(f"Loaded {len(all_docs)} documents")

        logger.info("Creating retrieval chain...")
        retriever = create_full_retrieval_chain(all_docs)

        logger.info("Loading illustrations...")
        illustrations_data = load_illustrations()

        logger.info("Application initialization complete")
        return retriever, illustrations_data
    except Exception as e:
        logger.error(f"Failed to initialize app state: {e}")
        raise


# Initialize app state
try:
    retriever, illustrations_data = initialize_app_state()
    app_initialized = True
except Exception as e:
    logger.critical(f"Application startup failed: {e}")
    retriever, illustrations_data = None, []
    app_initialized = False

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Consider restricting this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def search_illustrations(search_term: str) -> List[Dict[str, str]]:
    """
    Search illustrations using fuzzy matching with improved error handling.

    Args:
        search_term: The search term to match against illustrations

    Returns:
        List of dictionaries containing file paths of matching illustrations
    """
    try:
        if not illustrations_data:
            logger.warning("No illustrations data available")
            return []

        if not search_term or search_term.lower() == "all":
            return [{"file": img["file"]} for img in illustrations_data]

        search_term = search_term.strip()

        # Handle multiple search terms joined by "and"
        if " and " in search_term.lower():
            terms = [term.strip() for term in search_term.lower().split(" and ") if term.strip()]
            all_matches = []

            for term in terms:
                choices = {
                    img["file"]: f"{img.get('title', '')} {' '.join(img.get('tags', []))}"
                    for img in illustrations_data
                    if isinstance(img, dict) and 'file' in img
                }

                if choices:
                    found_matches = process.extract(term, choices, limit=10)
                    term_matches = [key for match, score, key in found_matches if score >= SEARCH_THRESHOLD]
                    all_matches.extend(term_matches)

            # Deduplicate results while preserving order
            unique_files = list(dict.fromkeys(all_matches))
            return [{"file": file} for file in unique_files[:MAX_RESULTS]]
        else:
            # Single-term search logic
            choices = {
                img["file"]: f"{img.get('title', '')} {' '.join(img.get('tags', []))}"
                for img in illustrations_data
                if isinstance(img, dict) and 'file' in img
            }

            if not choices:
                return []

            found_matches = process.extract(search_term, choices, limit=10)
            high_quality_matches = [
                {"file": key} for match, score, key in found_matches
                if score >= SEARCH_THRESHOLD
            ]
            return high_quality_matches[:MAX_RESULTS]

    except Exception as e:
        logger.error(f"Error searching illustrations: {e}")
        return []


# --- API Endpoints ---

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy" if app_initialized else "degraded",
        "message": "Nick Berens Portfolio API",
        "primary_llm": PRIMARY_LLM,
        "version": "2.0.0"
    }


@app.get("/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy" if app_initialized else "degraded",
        "app_initialized": app_initialized,
        "components": {
            "retriever": retriever is not None,
            "illustrations": len(illustrations_data) > 0,
            "illustrations_count": len(illustrations_data)
        },
        "configuration": {
            "primary_llm": PRIMARY_LLM,
            "search_threshold": SEARCH_THRESHOLD,
            "max_results": MAX_RESULTS
        }
    }


@app.get("/status")
async def status():
    """Simple status check."""
    return {
        "status": "online",
        "timestamp": time.time(),
        "primary_llm": PRIMARY_LLM,
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
            "primary_llm": PRIMARY_LLM,
            "claude_available": llms.get('claude') is not None,
            "gemini_available": llms.get('gemini') is not None,
            "models": {
                "claude": os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022"),
                "gemini": os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
            }
        }
    except Exception as e:
        logger.error(f"Error checking LLM status: {e}")
        return {"error": "Unable to check LLM status", "detail": str(e)}


@app.post("/query", response_model=QueryResponse)
@limiter.limit("5/minute")
async def query_endpoint(request: Request, query: Query) -> QueryResponse:
    """
    Main query endpoint that handles both text queries and illustration searches.
    Now with Claude as primary LLM and enhanced monitoring.
    """
    start_time = time.time()
    llm_used = None

    try:
        question = query.question.lower().strip()

        # Log the query (truncated for privacy)
        logger.info(f"Processing query: {question[:50]}{'...' if len(question) > 50 else ''}")

        # Define image-related keywords that indicate user wants illustrations
        image_keywords = [
            "image", "images", "illustration", "illustrations", "drawing", "drawings",
            "art", "design", "designs", "pic", "pics", "picture", "pictures"
        ]

        # Define search patterns
        specific_image_keywords = [
            "images of", "image of", "drawings of", "drawing of",
            "illustrations of", "illustration of", "art about", "art of"
        ]

        # Enhanced image search patterns
        show_me_patterns = [
            "show me", "show", "find", "get", "display"
        ]

        image_indicators = [
            "images", "image", "illustrations", "illustration", "drawings", "drawing", "art", "pics", "pictures"
        ]

        # Words to ignore when building search terms
        ignore_words = {
            "show", "me", "get", "find", "display", "see", "view", "look", "at",
            "the", "a", "an", "some", "any", "all", "your", "of", "for"
        }

        # Special phrases for showing all images
        all_image_phrases = [
            "show me all illustrations", "show all illustrations", "show me your illustrations",
            "show me all your art", "show me all images", "show me images", "show your art",
            "all images", "all illustrations", "all art", "show me everything"
        ]

        # Route to specific image search
        for trigger in specific_image_keywords:
            if trigger in question:
                search_term = question.split(trigger, 1)[1].strip()
                if search_term:
                    found_images = search_illustrations(search_term)
                    if found_images:
                        image_urls = [f"/illustrations/{img['file']}" for img in found_images]
                        processing_time = time.time() - start_time
                        logger.info(f"Image search completed in {processing_time:.3f}s")
                        return QueryResponse(
                            answer=f"Here are the illustrations I found for '{search_term}':",
                            images=image_urls,
                            processing_time=processing_time,
                            llm_used="image_search"
                        )
                    else:
                        processing_time = time.time() - start_time
                        return QueryResponse(
                            answer=f"Sorry, I couldn't find any illustrations matching '{search_term}'. You can ask to see all of my art.",
                            processing_time=processing_time,
                            llm_used="image_search"
                        )

        # Enhanced "show me X images/illustrations" pattern matching
        for show_pattern in show_me_patterns:
            if question.startswith(show_pattern):
                remaining_text = question[len(show_pattern):].strip()

                # Check if it contains image indicators
                for img_indicator in image_indicators:
                    if img_indicator in remaining_text:
                        # Extract the search term (everything before the image indicator)
                        parts = remaining_text.split(img_indicator)
                        if len(parts) > 1:
                            search_term = parts[0].strip()
                        else:
                            # Handle cases like "show me doug images" where the term comes before
                            words = remaining_text.split()
                            if img_indicator in words:
                                idx = words.index(img_indicator)
                                search_term = " ".join(words[:idx]).strip()
                            else:
                                search_term = remaining_text.replace(img_indicator, "").strip()

                        if search_term:
                            found_images = search_illustrations(search_term)
                            if found_images:
                                image_urls = [f"/illustrations/{img['file']}" for img in found_images]
                                processing_time = time.time() - start_time
                                logger.info(
                                    f"Enhanced image search completed in {processing_time:.3f}s for '{search_term}'")
                                return QueryResponse(
                                    answer=f"Here are the {search_term} illustrations I found:",
                                    images=image_urls,
                                    processing_time=processing_time,
                                    llm_used="image_search"
                                )
                            else:
                                processing_time = time.time() - start_time
                                return QueryResponse(
                                    answer=f"Sorry, I couldn't find any illustrations matching '{search_term}'. You can ask to see all of my art.",
                                    processing_time=processing_time,
                                    llm_used="image_search"
                                )
                        break
        # Route to show all images
        if question in all_image_phrases:
            all_images = search_illustrations("all")
            if all_images:
                image_urls = [f"/illustrations/{img['file']}" for img in all_images]
                processing_time = time.time() - start_time
                logger.info(f"All images search completed in {processing_time:.3f}s")
                return QueryResponse(
                    answer="Of course! Here are some of my illustrations:",
                    images=image_urls,
                    processing_time=processing_time,
                    llm_used="image_search"
                )
            else:
                processing_time = time.time() - start_time
                return QueryResponse(
                    answer="I couldn't find any illustrations at the moment.",
                    processing_time=processing_time,
                    llm_used="image_search"
                )

        # General pattern matching for "<subject> images" or similar patterns
        words = question.split()
        for img_indicator in image_indicators:
            if img_indicator in words:
                # Get the index of the image indicator
                idx = words.index(img_indicator)

                # Extract words before and after the image indicator
                words_before = words[:idx]
                words_after = words[idx+1:]

                # Filter out ignore words
                search_terms_before = [w for w in words_before if w not in ignore_words]
                search_terms_after = [w for w in words_after if w not in ignore_words]

                # Combine the search terms
                search_term = " ".join(search_terms_before + search_terms_after).strip()

                if search_term:
                    found_images = search_illustrations(search_term)
                    if found_images:
                        image_urls = [f"/illustrations/{img['file']}" for img in found_images]
                        processing_time = time.time() - start_time
                        logger.info(f"General image search completed in {processing_time:.3f}s for '{search_term}'")
                        return QueryResponse(
                            answer=f"Here are the illustrations I found for '{search_term}':",
                            images=image_urls,
                            processing_time=processing_time,
                            llm_used="image_search"
                        )
                    else:
                        processing_time = time.time() - start_time
                        return QueryResponse(
                            answer=f"Sorry, I couldn't find any illustrations matching '{search_term}'. You can ask to see all of my art.",
                            processing_time=processing_time,
                            llm_used="image_search"
                        )

        # Default to AI-powered text response
        if not retriever:
            raise HTTPException(
                status_code=503,
                detail=f"AI service temporarily unavailable - app not properly initialized"
            )

        # Format chat history
        formatted_chat_history = []
        for message in query.chat_history:
            if message.sender == 'user':
                formatted_chat_history.append(HumanMessage(content=message.text))
            elif message.sender in ['assistant', 'ai', 'bot']:
                formatted_chat_history.append(AIMessage(content=message.text))

        # Get AI response with enhanced error handling
        try:
            answer = invoke_with_fallback(retriever, formatted_chat_history, query.question)
            llm_used = PRIMARY_LLM  # Assume primary was used unless we add tracking to the chain
        except Exception as llm_error:
            logger.error(f"LLM processing failed: {llm_error}")
            answer = (
                "I'm sorry, I'm currently experiencing technical difficulties with the AI service. "
                "This might be due to high demand or temporary service issues. Please try again in a few moments."
            )
            llm_used = "fallback"

        if not answer:
            answer = "I'm sorry, I couldn't generate a response. Please try rephrasing your question."
            llm_used = "fallback"

        processing_time = time.time() - start_time
        logger.info(f"Query processed successfully in {processing_time:.3f}s using {llm_used}")

        return QueryResponse(
            answer=answer,
            processing_time=processing_time,
            llm_used=llm_used
        )

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
    logger.info(f"Primary LLM: {PRIMARY_LLM}")
    logger.info(f"App initialized: {app_initialized}")
    logger.info(f"Illustrations loaded: {len(illustrations_data)}")
    logger.info("=== Startup Complete ===")


# Development server
if __name__ == "__main__":
    import uvicorn

    logger.info("Starting development server...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level=LOG_LEVEL.lower(),
        reload=True
    )

print("Backend setup complete. Ready for queries with Claude as primary LLM.")
