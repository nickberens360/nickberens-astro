"""
Health check endpoints for monitoring application status.

This module contains health-related endpoints:
- Root endpoint for basic status
- Status endpoint with detailed information
- Health check endpoint with service validation
- Rate limits endpoint for LLM status monitoring
"""

import time

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from ..core.config import AppConfig
from ..dependencies import get_app_state

router = APIRouter()


def _get_current_primary_llm() -> str:
    """Get the current primary LLM from database settings with fallback."""
    try:
        from ..core.settings_manager import get_settings_manager

        settings_manager = get_settings_manager()
        system_config = settings_manager.get_system_config_settings()
        return system_config.primary_llm
    except Exception:
        # Fallback to environment config
        return AppConfig.PRIMARY_LLM


@router.get(
    "/",
    tags=["Health"],
    summary="Root Status Check",
    description="Quick health check endpoint. Returns basic application status.",
    responses={
        200: {
            "description": "Application status",
            "content": {
                "application/json": {
                    "examples": {
                        "healthy": {"summary": "Application running", "value": {"status": "healthy"}},
                        "degraded": {"summary": "Application starting", "value": {"status": "degraded"}},
                    }
                }
            },
        }
    },
)
async def root(state: dict = Depends(get_app_state)):
    return {"status": "healthy" if state["app_initialized"] else "degraded"}


@router.get(
    "/status",
    tags=["Health"],
    summary="Detailed System Status",
    description="""
           **Comprehensive system status with AI service information.**
           
           Returns detailed information about:
           - Application initialization status
           - AI model availability and rate limits
           - Primary LLM configuration
           - Timestamp for monitoring
           
           **Rate Limits:** This endpoint helps you monitor which AI models are currently available vs rate-limited.
           """,
    responses={
        200: {
            "description": "Detailed system status",
            "content": {
                "application/json": {
                    "example": {
                        "status": "online",
                        "timestamp": 1694123456.789,
                        "primary_llm": "claude",
                        "app_initialized": True,
                        "rate_limits": {"claude": False, "gemini": False},
                    }
                }
            },
        }
    },
)
async def status(state: dict = Depends(get_app_state)):
    """Status check with rate limit information."""
    try:
        # Import here to avoid circular imports
        from ..core.llm_chain import get_rate_limit_status

        rate_limits = get_rate_limit_status()
    except Exception as e:
        # Fallback if rate limit checking fails
        rate_limits = {"claude": False, "gemini": False}
        print(f"Error getting rate limits: {e}")

    return {
        "status": "online",
        "timestamp": time.time(),
        "primary_llm": _get_current_primary_llm(),
        "app_initialized": state["app_initialized"],
        "rate_limits": rate_limits,
    }


@router.get(
    "/health",
    tags=["Health"],
    summary="Health Check with Service Validation",
    description="""
           **Health check endpoint for monitoring and load balancers.**
           
           Validates:
           - Application initialization status
           - Illustration service availability 
           - Knowledge base readiness
           
           Use this endpoint for:
           - Load balancer health checks
           - Monitoring system alerts
           - Container orchestration readiness probes
           """,
    responses={
        200: {
            "description": "Application health status",
            "content": {
                "application/json": {
                    "examples": {
                        "healthy": {
                            "summary": "Fully operational",
                            "value": {"status": "healthy", "illustration_count": 15},
                        },
                        "initializing": {
                            "summary": "Still starting up",
                            "value": {"status": "initializing", "illustration_count": 0},
                        },
                    }
                }
            },
        }
    },
)
async def health_check(state: dict = Depends(get_app_state)):
    illustration_count = 0
    try:
        if state["illustration_service"]:
            count = state["illustration_service"].get_all()
            illustration_count = len(count)
    except Exception:
        # During startup, illustration service may not be ready
        illustration_count = 0

    return {
        "status": "healthy" if state["app_initialized"] else "initializing",
        "illustration_count": illustration_count,
    }


@router.get(
    "/rate-limits",
    tags=["Health"],
    summary="AI Model Rate Limit Status",
    description="""
           **Monitor AI model availability and rate limiting status.**
           
           Returns the current rate limit status for all configured LLM providers:
           - `false`: Model is available and not rate limited
           - `true`: Model is currently rate limited
           
           **Use Cases:**
           - Monitor AI service health
           - Implement client-side fallback logic
           - Track service availability metrics
           
           **Rate Limit Details:**
           - Claude: Anthropic API rate limits
           - Gemini: Google AI rate limits
           """,
    responses={
        200: {
            "description": "Rate limit status for all LLM providers",
            "content": {
                "application/json": {
                    "examples": {
                        "all_available": {
                            "summary": "All models available",
                            "value": {"rate_limits": {"claude": False, "gemini": False}},
                        },
                        "claude_limited": {
                            "summary": "Claude rate limited",
                            "value": {"rate_limits": {"claude": True, "gemini": False}},
                        },
                    }
                }
            },
        },
        500: {
            "description": "Error retrieving rate limit status",
            "content": {
                "application/json": {
                    "example": {
                        "error": "Failed to get rate limit status",
                        "rate_limits": {"claude": False, "gemini": False},
                    }
                }
            },
        },
    },
)
async def get_rate_limits():
    """Get current rate limit status for all LLM providers."""
    try:
        # Import here to avoid circular imports
        from ..core.llm_chain import get_rate_limit_status

        rate_limits = get_rate_limit_status()

        return JSONResponse(content={"rate_limits": rate_limits})
    except Exception as e:
        print(f"Error getting rate limits: {e}")
        return JSONResponse(
            content={"error": "Failed to get rate limit status", "rate_limits": {"claude": False, "gemini": False}},
            status_code=500,
        )


@router.get(
    "/db-paths",
    tags=["Health"],
    summary="Database Path Status (Debug)",
    description="Debug endpoint to check which database paths are being used",
)
async def get_db_paths():
    """Debug endpoint to check database path resolution."""
    import os
    from pathlib import Path

    try:
        from ..core.database_utils import get_database_path

        # Test both admin and RAG monitoring databases
        admin_db_path = get_database_path("admin_monitoring.db")
        rag_db_path = get_database_path("rag_monitoring.db")

        # Check environment and volume info
        env_info = {
            "RAILWAY_ENVIRONMENT_NAME": os.getenv("RAILWAY_ENVIRONMENT_NAME"),
            "RAILWAY_VOLUME_NAME": os.getenv("RAILWAY_VOLUME_NAME"),
            "RAILWAY_VOLUME_MOUNT_PATH": os.getenv("RAILWAY_VOLUME_MOUNT_PATH"),
            "RAILWAY_RUN_UID": os.getenv("RAILWAY_RUN_UID"),
        }

        # Check path accessibility
        paths_status = {}
        for path_name, path in [("/data", Path("/data")), ("/tmp", Path("/tmp")), ("/app", Path("/app"))]:
            paths_status[path_name] = {
                "exists": path.exists(),
                "readable": path.exists() and os.access(path, os.R_OK),
                "writable": path.exists() and os.access(path, os.W_OK),
            }

        return {
            "admin_db_path": str(admin_db_path),
            "rag_db_path": str(rag_db_path),
            "admin_db_exists": admin_db_path.exists(),
            "rag_db_exists": rag_db_path.exists(),
            "environment": env_info,
            "paths": paths_status,
        }

    except Exception as e:
        return {"error": str(e)}


@router.get(
    "/welcome-questions",
    tags=["Public API"],
    summary="Get Welcome Questions",
    description="""
           **Public endpoint for homepage welcome questions.**
           
           Returns active welcome questions configured in the admin panel.
           These are the suggested questions displayed to users on the homepage.
           
           **Public Access:** This endpoint does not require authentication.
           """,
    responses={
        200: {
            "description": "List of active welcome questions",
            "content": {
                "application/json": {
                    "example": {
                        "questions": [
                            {"id": 1, "question_text": "Tell me about yourself", "sort_order": 1},
                            {"id": 2, "question_text": "Show me your resume", "sort_order": 2},
                        ]
                    }
                }
            },
        }
    },
)
async def get_welcome_questions():
    """Get active welcome questions for homepage display."""
    try:
        # Import here to avoid circular imports
        from ..core.admin_database import admin_db_manager

        questions = admin_db_manager.get_welcome_questions(active_only=True)

        # Return only the fields needed by the frontend
        public_questions = [
            {"id": q["id"], "question_text": q["question_text"], "sort_order": q["sort_order"] or 0} for q in questions
        ]

        return {"questions": public_questions}

    except Exception as e:
        # Fallback to default questions if database is unavailable
        print(f"Error getting welcome questions: {e}")
        return {
            "questions": [
                {"id": 1, "question_text": "Tell me about yourself", "sort_order": 1},
                {"id": 2, "question_text": "Show me your resume", "sort_order": 2},
                {"id": 3, "question_text": "Show me your illustrations", "sort_order": 3},
            ]
        }
