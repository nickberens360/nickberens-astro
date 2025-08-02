# backend/main.py - Updated FastAPI integration with fixed type annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Type, Union

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# --- Start of Refactored Section ---

# Use a standard try-except block that mypy can understand
try:
    # This is the standard path when running from the project root
    from backend.core.config import AppConfig
except (ImportError, AttributeError):
    # This is a fallback for different execution contexts (like some tests)
    from core.config import AppConfig


# Handle optional dependency for AutoRAGSystem
try:
    from backend.core.auto_rag import AutoRAGSystem

    AutoRAGSystemClass: Optional[Type[AutoRAGSystem]] = AutoRAGSystem
    AUTO_RAG_AVAILABLE = True
except (ImportError, AttributeError):
    AutoRAGSystemClass = None
    AUTO_RAG_AVAILABLE = False

# --- End of Refactored Section ---


if not AUTO_RAG_AVAILABLE:
    print("⚠️ Auto RAG system not available")
    print("Install dependencies: pip install llama-index llama-index-llms-anthropic llama-index-embeddings-huggingface")

# Set up logging
logging.basicConfig(level=getattr(logging, AppConfig.LOG_LEVEL))
logger = logging.getLogger(__name__)

# Global RAG system instance
rag_system: Optional[Any] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup the RAG system."""
    global rag_system

    if not AUTO_RAG_AVAILABLE or AutoRAGSystemClass is None:
        logger.warning("🚫 Auto RAG system not available - install dependencies")
        yield
        return

    logger.info("🚀 Initializing Auto-Discovery RAG System...")
    try:
        # Check for required environment variables
        if not os.getenv("ANTHROPIC_API_KEY"):
            logger.warning("⚠️ ANTHROPIC_API_KEY not set - some features may not work")

        rag_system = AutoRAGSystemClass(data_dir="public")
        logger.info("✅ RAG system initialized successfully")

        # Log document discovery stats
        stats = rag_system.get_document_stats()
        logger.info(f"📊 Discovered {stats['total_files']} files across {len(stats['file_types'])} types")

    except Exception as e:
        logger.error(f"❌ Failed to initialize RAG system: {e}")
        rag_system = None

    yield

    # Cleanup (if needed)
    logger.info("🛑 Shutting down RAG system...")


# Create FastAPI app with lifespan management
app = FastAPI(
    title=AppConfig.APP_TITLE, description=AppConfig.APP_DESCRIPTION, version=AppConfig.APP_VERSION, lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=AppConfig.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class QueryRequest(BaseModel):
    question: str
    chat_history: List[Dict[str, str]] = []
    preferred_model: str = "claude"
    max_results: int = 5
    include_sources: bool = True


class QueryResponse(BaseModel):
    response: str
    sources: List[Dict[str, Any]] = []
    document_stats: Dict[str, Any] = {}
    model_used: str = "auto-rag"


class RefreshRequest(BaseModel):
    force: bool = False


class DocumentStats(BaseModel):
    total_files: int
    file_types: Dict[str, int]
    total_size: int
    last_updated: str


# API Endpoints


@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint - returns application status."""
    if rag_system:
        return {"status": "healthy"}
    else:
        return {"status": "degraded"}


@app.get("/status")
async def status() -> Dict[str, Union[str, Dict]]:
    """Status endpoint with rate limits (for test compatibility)."""
    return {"status": "healthy" if rag_system else "degraded", "rate_limits": {}}


@app.get("/rate-limits")
async def rate_limits() -> Dict[str, Dict]:
    """Rate limits endpoint (for test compatibility)."""
    return {"rate_limits": {}}


@app.get("/health")
async def health_check() -> Dict[str, Union[str, bool]]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "auto_rag_available": AUTO_RAG_AVAILABLE,
        "rag_system": "initialized" if rag_system else "not_initialized",
        "version": AppConfig.APP_VERSION,
    }


@app.post("/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest) -> QueryResponse:
    """
    Query the auto-discovered document collection.

    This endpoint automatically searches across ALL documents
    in the public directory - no configuration needed!
    """
    if not AUTO_RAG_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Auto RAG system not available. Install: pip install llama-index llama-index-llms-anthropic llama-index-embeddings-huggingface",
        )

    if not rag_system:
        raise HTTPException(
            status_code=503, detail="RAG system not initialized. Check server logs and ANTHROPIC_API_KEY."
        )

    try:
        logger.info(f"🔍 Processing query: {request.question[:100]}...")
        logger.info(f"📝 Chat history length: {len(request.chat_history)} messages")
        logger.info(f"🤖 Preferred model: {request.preferred_model}")

        # Format chat history into context
        context_parts: List[str] = []
        if request.chat_history:
            context_parts.append("Previous conversation context:")
            for msg in request.chat_history[-10:]:  # Use last 10 messages to avoid token limits
                sender = msg.get("sender", "unknown")
                text = msg.get("text", "")
                if text.strip():
                    context_parts.append(f"{sender.capitalize()}: {text}")
            context_parts.append("\nCurrent question:")

        # Combine context with current question
        if context_parts:
            full_question = "\n".join(context_parts) + f"\n{request.question}"
        else:
            full_question = request.question

        # Query the system - now expecting a tuple (response, source_nodes)
        response_text, source_nodes = rag_system.query(full_question, top_k=request.max_results)

        # Get document stats for transparency
        stats = rag_system.get_document_stats()

        # Extract source information from the LlamaIndex response
        sources: List[Dict[str, Any]] = []
        if request.include_sources and source_nodes:
            for node in source_nodes:
                sources.append(
                    {
                        "file_name": node.metadata.get("file_name"),
                        "file_path": node.metadata.get("file_path"),
                        "score": node.score,
                        # Optional: include a snippet of the node's text
                        # "snippet": node.get_content(metadata_mode="all")[:200] + "..."
                    }
                )

        # --- This is the section that was missing ---
        return QueryResponse(
            response=response_text,
            sources=sources,
            document_stats=stats if request.include_sources else {},
            model_used=rag_system.get_model_name(),
        )

    except (ValueError, TypeError) as e:
        logger.error(f"❌ Query failed with a possible signature mismatch: {e}")
        logger.error("💡 Hint: Ensure 'AutoRAGSystem.query' returns a tuple of (response_text, source_nodes).")
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}") from e
    except Exception as e:
        logger.error(f"❌ Query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}") from e


@app.get("/documents/stats", response_model=DocumentStats)
async def get_document_stats() -> DocumentStats:
    """Get statistics about all discovered documents."""
    if not AUTO_RAG_AVAILABLE or not rag_system:
        raise HTTPException(status_code=503, detail="RAG system not available")

    try:
        stats = rag_system.get_document_stats()
        return DocumentStats(**stats)
    except Exception as e:
        logger.error(f"❌ Failed to get document stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve document statistics: {str(e)}") from e


@app.post("/documents/refresh")
async def refresh_documents(request: RefreshRequest, background_tasks: BackgroundTasks) -> Dict[str, Union[str, bool]]:
    """
    Refresh the document index.

    This will scan for new files and rebuild the index if changes are detected.
    Use force=true to rebuild regardless of changes.
    """
    if not AUTO_RAG_AVAILABLE or not rag_system:
        raise HTTPException(status_code=503, detail="RAG system not available")

    def refresh_task() -> None:
        try:
            logger.info("🔄 Starting document refresh...")
            if request.force:
                rag_system.refresh()
            else:
                rag_system._load_or_build_index()
            logger.info("✅ Document refresh completed")
        except Exception as e:
            logger.error(f"❌ Document refresh failed: {e}")

    # Run refresh in background to avoid blocking the API
    background_tasks.add_task(refresh_task)

    return {"message": "Document refresh started", "force": request.force, "status": "processing"}


@app.get("/documents/types")
async def get_supported_file_types() -> Dict[str, Union[Dict[str, str], str, bool]]:
    """Get list of supported file types for document processing."""
    return {
        "supported_types": {
            ".json": "JSON documents and structured data",
            ".csv": "CSV spreadsheets and data files",
            ".md": "Markdown documents and documentation",
            ".txt": "Plain text files",
            ".pdf": "PDF documents (requires additional setup)",
            ".docx": "Microsoft Word documents (requires additional setup)",
        },
        "note": "Just drop any of these file types into the public/ directory!",
        "auto_rag_available": AUTO_RAG_AVAILABLE,
    }


@app.get("/setup")
async def get_setup_info() -> Dict[str, Union[bool, str, List[str], int]]:
    """Get setup information and requirements."""
    return {
        "auto_rag_available": AUTO_RAG_AVAILABLE,
        "anthropic_api_key_set": bool(os.getenv("ANTHROPIC_API_KEY")),
        "installation_command": "pip install llama-index llama-index-llms-anthropic llama-index-embeddings-huggingface",
        "env_vars_needed": ["ANTHROPIC_API_KEY"],
        "public_dir_exists": os.path.exists("public"),
        "public_files": (
            len([f for f in os.listdir("public") if os.path.isfile(os.path.join("public", f))])
            if os.path.exists("public")
            else 0
        ),
    }


# Legacy endpoints (for backward compatibility)
@app.get("/illustrations")
async def get_illustrations() -> Dict[str, str]:
    """
    Legacy endpoint for illustrations.
    Now automatically discovers illustration files!
    """
    if not AUTO_RAG_AVAILABLE or not rag_system:
        return {
            "message": "Auto RAG system not available. Install dependencies to enable auto-discovery.",
            "install_command": "pip install llama-index llama-index-llms-anthropic llama-index-embeddings-huggingface",
        }

    try:
        # Query for illustration-related content
        response_text, _ = rag_system.query("Show me all illustrations and artwork")
        return {
            "message": "Illustrations are now auto-discovered! Use the /query endpoint.",
            "query_example": "Ask: 'Show me Nick's illustrations' or 'What artwork does Nick have?'",
            "response_preview": response_text[:200] + "..." if len(response_text) > 200 else response_text,
        }

    except Exception as e:
        logger.error(f"❌ Illustrations query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,  # Pass the app object directly instead of string
        host=AppConfig.HOST,
        port=AppConfig.PORT,
        reload=False,  # Disable reload to avoid import issues
        log_level=AppConfig.LOG_LEVEL.lower(),
    )
