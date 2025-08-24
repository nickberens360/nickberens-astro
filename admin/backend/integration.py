"""
Integration module to connect existing RAG system with admin dashboard logging.
"""

import json
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from .database import db_manager


class AdminQueryLogger:
    """Enhanced query logger that integrates with the admin dashboard database."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def log_query(
        self,
        client_ip: Optional[str] = None,
        question: str = "",
        response: str = "",
        model_used: Optional[str] = None,
        query_type: str = "text",
        response_time: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
        error_occurred: bool = False,
        error_message: Optional[str] = None,
        session_id: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> int:
        """
        Log a completed query to the admin database.

        Returns the query ID for potential future reference.
        """
        try:
            # Extract metadata
            metadata = metadata or {}
            vector_search_score = metadata.get("similarity_score", metadata.get("vector_search_score"))
            sources_used = metadata.get("sources_used", metadata.get("context_sources", []))
            follow_up_questions = metadata.get("followup_questions", [])
            cache_hit = metadata.get("cache_hit", False)

            # Generate session ID if not provided
            if not session_id and client_ip:
                session_id = f"session_{hash(client_ip)}_{int(time.time() / 3600)}"  # Hourly sessions

            # Log the query
            query_id = db_manager.log_query(
                session_id=session_id,
                user_query=question,
                system_response=response,
                response_time_ms=response_time * 1000,  # Convert to milliseconds
                llm_provider=self._extract_llm_provider(model_used),
                llm_model=model_used,
                vector_search_score=vector_search_score,
                sources_used=sources_used if isinstance(sources_used, list) else [],
                follow_up_questions=follow_up_questions if isinstance(follow_up_questions, list) else [],
                cache_hit=cache_hit,
                error_occurred=error_occurred,
                error_message=error_message,
            )

            # Update session info
            if session_id:
                db_manager.update_session(session_id=session_id, user_agent=user_agent, ip_address=client_ip)

            self.logger.debug(f"Logged query {query_id} to admin database")
            return query_id

        except Exception as e:
            self.logger.error(f"Failed to log query to admin database: {e}")
            return -1

    def log_streaming_query(
        self,
        client_ip: Optional[str] = None,
        question: str = "",
        model_used: Optional[str] = None,
        response_time: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        session_id: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> int:
        """
        Log a streaming query (response will be marked as [STREAMING]).
        """
        return self.log_query(
            client_ip=client_ip,
            question=question,
            response="[STREAMING RESPONSE]",
            model_used=model_used,
            query_type="text_streaming",
            response_time=response_time,
            metadata=metadata,
            session_id=session_id,
            user_agent=user_agent,
        )

    def update_streaming_response(self, query_id: int, full_response: str):
        """Update a streaming query with the complete response."""
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE query_logs 
                    SET system_response = ? 
                    WHERE id = ?
                """,
                    (full_response, query_id),
                )
                conn.commit()
                self.logger.debug(f"Updated streaming response for query {query_id}")
        except Exception as e:
            self.logger.error(f"Failed to update streaming response: {e}")

    def log_error(
        self,
        client_ip: Optional[str] = None,
        question: str = "",
        error_message: str = "",
        model_used: Optional[str] = None,
        response_time: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> int:
        """Log a query that resulted in an error."""
        return self.log_query(
            client_ip=client_ip,
            question=question,
            response="",
            model_used=model_used,
            response_time=response_time,
            metadata=metadata,
            error_occurred=True,
            error_message=error_message,
            session_id=session_id,
        )

    def _extract_llm_provider(self, model_name: Optional[str]) -> Optional[str]:
        """Extract LLM provider from model name."""
        if not model_name:
            return None

        model_name_lower = model_name.lower()

        if "claude" in model_name_lower or "anthropic" in model_name_lower:
            return "anthropic"
        elif "gpt" in model_name_lower or "openai" in model_name_lower:
            return "openai"
        elif "gemini" in model_name_lower or "google" in model_name_lower:
            return "google"
        elif "llama" in model_name_lower:
            return "meta"
        else:
            return "unknown"


# Global admin query logger instance
admin_query_logger = AdminQueryLogger()


def get_admin_query_logger() -> AdminQueryLogger:
    """Get the global admin query logger instance."""
    return admin_query_logger


# Monkey patch the existing query logger to also log to admin database
def patch_existing_query_logger():
    """
    Monkey patch the existing query logger to also send logs to admin database.
    This should be called during application startup.
    """
    try:
        from backend.core.query_logger import QueryLogger

        # Store original methods
        original_log_query = QueryLogger.log_query
        original_log_streaming_query = QueryLogger.log_streaming_query

        def enhanced_log_query(self, **kwargs):
            """Enhanced log_query that also logs to admin database."""
            # Call original logging
            result = original_log_query(self, **kwargs)

            # Also log to admin database
            try:
                admin_query_logger.log_query(**kwargs)
            except Exception as e:
                logging.getLogger(__name__).error(f"Failed to log to admin database: {e}")

            return result

        def enhanced_log_streaming_query(self, **kwargs):
            """Enhanced log_streaming_query that also logs to admin database."""
            # Call original logging
            result = original_log_streaming_query(self, **kwargs)

            # Also log to admin database
            try:
                admin_query_logger.log_streaming_query(**kwargs)
            except Exception as e:
                logging.getLogger(__name__).error(f"Failed to log streaming query to admin database: {e}")

            return result

        # Apply patches
        QueryLogger.log_query = enhanced_log_query
        QueryLogger.log_streaming_query = enhanced_log_streaming_query

        logging.getLogger(__name__).info("Successfully patched existing query logger with admin database integration")

    except ImportError as e:
        logging.getLogger(__name__).warning(f"Could not patch existing query logger: {e}")
    except Exception as e:
        logging.getLogger(__name__).error(f"Error patching query logger: {e}")


# Session middleware for tracking user sessions
class SessionTrackingMiddleware:
    """Middleware to track user sessions for the admin dashboard."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Extract session info from request
            headers = dict(scope.get("headers", []))
            user_agent = headers.get(b"user-agent", b"").decode()

            # For now, we'll let the query logger handle session creation
            # In a more sophisticated setup, we could create sessions here

        await self.app(scope, receive, send)
