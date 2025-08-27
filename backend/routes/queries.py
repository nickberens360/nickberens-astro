"""
Admin dashboard queries API routes.

Provides endpoints for:
- Query listing and management
- Individual query details
- Query insights and analytics
"""

import logging
import sqlite3
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


class QueryItem(BaseModel):
    """Model for individual query data."""

    id: str
    user_query: str
    response: str
    timestamp: str
    response_time_ms: Optional[float] = None
    model_used: Optional[str] = None
    error_occurred: Optional[bool] = None
    error_message: Optional[str] = None
    session_id: Optional[str] = None
    user_feedback: Optional[str] = None
    vector_search_score: Optional[float] = None
    sources_used: Optional[str] = None
    client_ip: Optional[str] = None
    location_city: Optional[str] = None
    location_region: Optional[str] = None
    location_country: Optional[str] = None
    location_country_code: Optional[str] = None


class QueryResponse(BaseModel):
    """Model for query listing response."""

    queries: List[QueryItem]
    total: int
    has_more: bool


class QueryInsights(BaseModel):
    """Model for query insights and analytics."""

    total_queries: int = 0
    avg_response_time: float = 0.0
    error_rate: float = 0.0
    popular_topics: List[str] = []
    feedback_summary: dict = {}


# Database connection utility imported from shared module
from ..core.database_utils import get_rag_monitoring_db_connection as get_db_connection


@router.get("/queries", response_model=QueryResponse)
async def get_queries(
    limit: int = Query(50, ge=1, le=100, description="Number of queries to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    search: Optional[str] = Query(None, description="Search term for filtering queries"),
    start_date: Optional[str] = Query(None, description="Start date for filtering (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date for filtering (ISO format)"),
    errors_only: Optional[bool] = Query(False, description="Show only queries with errors"),
    min_relevance: Optional[float] = Query(None, description="Minimum relevance score"),
    sort_by: Optional[str] = Query("created_at", description="Field to sort by"),
    sort_order: Optional[str] = Query("desc", description="Sort order (asc/desc)"),
):
    """
    Get list of queries with filtering and pagination.
    """
    try:
        conn = get_db_connection()

        if not conn:
            return QueryResponse(queries=[], total=0, has_more=False)

        cursor = conn.cursor()

        # Build WHERE clause
        where_conditions = []
        params = []

        if search:
            where_conditions.append("(user_query LIKE ? OR system_response LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])

        if start_date:
            where_conditions.append("timestamp >= ?")
            params.append(start_date)

        if end_date:
            where_conditions.append("timestamp <= ?")
            params.append(end_date)

        if errors_only:
            where_conditions.append("error_occurred = 1")

        where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""

        # Get total count
        count_query = f"SELECT COUNT(*) as total FROM query_logs{where_clause}"
        cursor.execute(count_query, params)
        total = cursor.fetchone()["total"]

        # Build main query with pagination
        order_direction = "DESC" if sort_order.lower() == "desc" else "ASC"
        valid_sort_fields = ["timestamp", "response_time_ms", "user_query", "llm_model"]
        sort_field = sort_by if sort_by in valid_sort_fields else "timestamp"

        query = f"""
            SELECT id, user_query, system_response, timestamp, response_time_ms, 
                   llm_model, error_occurred, error_message, session_id, user_feedback,
                   vector_search_score, sources_used, client_ip, location_city, 
                   location_region, location_country, location_country_code
            FROM query_logs
            {where_clause}
            ORDER BY {sort_field} {order_direction}
            LIMIT ? OFFSET ?
        """

        cursor.execute(query, params + [limit, offset])
        rows = cursor.fetchall()

        queries = []
        for row in rows:
            queries.append(
                QueryItem(
                    id=str(row["id"]),
                    user_query=row["user_query"] or "",
                    response=row["system_response"] or "",
                    timestamp=row["timestamp"] or "",
                    response_time_ms=row["response_time_ms"],
                    model_used=row["llm_model"],
                    error_occurred=bool(row["error_occurred"]) if row["error_occurred"] is not None else None,
                    error_message=row["error_message"],
                    session_id=row["session_id"],
                    user_feedback=row["user_feedback"],
                    vector_search_score=row["vector_search_score"],
                    sources_used=row["sources_used"],
                    client_ip=row["client_ip"],
                    location_city=row["location_city"],
                    location_region=row["location_region"],
                    location_country=row["location_country"],
                    location_country_code=row["location_country_code"],
                )
            )

        conn.close()

        has_more = offset + limit < total

        return QueryResponse(queries=queries, total=total, has_more=has_more)

    except sqlite3.Error as e:
        logger.error(f"Database error in get_queries: {e}")
        return QueryResponse(queries=[], total=0, has_more=False)
    except Exception as e:
        logger.error(f"Error in get_queries: {e}")
        return QueryResponse(queries=[], total=0, has_more=False)


@router.get("/queries/insights", response_model=QueryInsights)
async def get_query_insights():
    """
    Get insights and analytics about queries.
    """
    try:
        conn = get_db_connection()

        if not conn:
            return QueryInsights()

        cursor = conn.cursor()

        # Get basic stats
        cursor.execute(
            """
            SELECT 
                COUNT(*) as total_queries,
                AVG(response_time_ms) as avg_response_time,
                COUNT(CASE WHEN error_occurred = 1 THEN 1 END) as error_count
            FROM query_logs
        """
        )

        stats = cursor.fetchone()

        total_queries = stats["total_queries"] if stats else 0
        avg_response_time = stats["avg_response_time"] if stats and stats["avg_response_time"] else 0.0
        error_rate = (stats["error_count"] / total_queries) if stats and total_queries > 0 else 0.0

        # Get feedback summary
        cursor.execute(
            """
            SELECT user_feedback, COUNT(*) as count
            FROM query_logs
            WHERE user_feedback IS NOT NULL
            GROUP BY user_feedback
        """
        )

        feedback_rows = cursor.fetchall()
        feedback_summary = {row["user_feedback"]: row["count"] for row in feedback_rows}

        # Popular topics (simplified - could be enhanced with real topic analysis)
        popular_topics = ["Development", "Experience", "Skills", "Projects"]

        conn.close()

        return QueryInsights(
            total_queries=total_queries,
            avg_response_time=round(avg_response_time, 2),
            error_rate=round(error_rate, 3),
            popular_topics=popular_topics,
            feedback_summary=feedback_summary,
        )

    except sqlite3.Error as e:
        logger.error(f"Database error in get_query_insights: {e}")
        return QueryInsights()
    except Exception as e:
        logger.error(f"Error in get_query_insights: {e}")
        return QueryInsights()


@router.get("/queries/{query_id}", response_model=QueryItem)
async def get_query(query_id: str):
    """
    Get details of a specific query by ID.
    """
    try:
        conn = get_db_connection()

        if not conn:
            raise HTTPException(status_code=503, detail="Database not available")

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, user_query, system_response, timestamp, response_time_ms,
                   llm_model, error_occurred, error_message, session_id, user_feedback,
                   vector_search_score, sources_used, client_ip, location_city, 
                   location_region, location_country, location_country_code
            FROM query_logs
            WHERE id = ?
        """,
            (query_id,),
        )

        row = cursor.fetchone()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail="Query not found")

        return QueryItem(
            id=str(row["id"]),
            user_query=row["user_query"] or "",
            response=row["system_response"] or "",
            timestamp=row["timestamp"] or "",
            response_time_ms=row["response_time_ms"],
            model_used=row["llm_model"],
            error_occurred=bool(row["error_occurred"]) if row["error_occurred"] is not None else None,
            error_message=row["error_message"],
            session_id=row["session_id"],
            user_feedback=row["user_feedback"],
            vector_search_score=row["vector_search_score"],
            sources_used=row["sources_used"],
            client_ip=row["client_ip"],
            location_city=row["location_city"],
            location_region=row["location_region"],
            location_country=row["location_country"],
            location_country_code=row["location_country_code"],
        )

    except HTTPException:
        raise
    except sqlite3.Error as e:
        logger.error(f"Database error in get_query: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        logger.error(f"Error in get_query: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/queries/{query_id}/feedback")
async def update_query_feedback(query_id: str, feedback_data: dict):
    """
    Update feedback for a specific query.
    """
    try:
        feedback = feedback_data.get("feedback")
        if not feedback:
            raise HTTPException(status_code=400, detail="Feedback is required")

        conn = get_db_connection()

        if not conn:
            raise HTTPException(status_code=503, detail="Database not available")

        cursor = conn.cursor()

        # Check if query exists
        cursor.execute("SELECT id FROM query_logs WHERE id = ?", (query_id,))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=404, detail="Query not found")

        # Update feedback
        cursor.execute(
            """
            UPDATE query_logs
            SET user_feedback = ?
            WHERE id = ?
        """,
            (feedback, query_id),
        )

        conn.commit()
        conn.close()

        return {"success": True, "message": "Feedback updated successfully"}

    except HTTPException:
        raise
    except sqlite3.Error as e:
        logger.error(f"Database error in update_query_feedback: {e}")
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        logger.error(f"Error in update_query_feedback: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
