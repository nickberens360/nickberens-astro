"""
Content management API routes.

Provides endpoints for:
- Content gap detection and management
- Popular topic analytics
- Source usage analytics
"""

import logging
import sqlite3
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from starlette.requests import Request

# Import shared models from knowledge module
from .knowledge import IndexedDocument, IndexedDocumentsResponse

logger = logging.getLogger(__name__)
router = APIRouter()


# Request/Response Models
class ContentGapUpdate(BaseModel):
    """Model for updating content gap properties."""

    resolved: Optional[bool] = None
    notes: Optional[str] = None


class ContentGap(BaseModel):
    """Model for content gap data."""

    id: int
    pattern: str
    count: int
    avg_score: float
    first_seen: str
    last_seen: str
    resolved: bool
    notes: Optional[str] = None
    sample_query: Optional[str] = None


class ContentGapsResponse(BaseModel):
    """Response model for content gaps listing."""

    gaps: List[ContentGap]
    total_count: int


# Database connection utility imported from shared module
from ..core.database_utils import get_rag_monitoring_db_connection


def get_db_connection():
    """Get database connection to the SQLite database."""
    conn = get_rag_monitoring_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Database not available")
    return conn


@router.get("/content/gaps", response_model=ContentGapsResponse)
async def get_content_gaps(
    request: Request,
    resolved: bool = Query(False, description="Include resolved gaps"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of gaps to return"),
):
    """
    Get content gaps from the database.

    Args:
        resolved: Whether to include resolved gaps (default: only unresolved)
        limit: Maximum number of gaps to return
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Build query based on resolved filter
        if resolved:
            # Show all gaps
            query = """
                SELECT cg.id, cg.query_pattern as pattern, cg.occurrence_count as count,
                       cg.avg_similarity_score as avg_score, cg.first_seen, cg.last_seen,
                       cg.resolved, cg.notes, ql.user_query as sample_query
                FROM content_gaps cg
                LEFT JOIN query_logs ql ON cg.sample_query_id = ql.id
                ORDER BY cg.last_seen DESC
                LIMIT ?
            """
            params = (limit,)
        else:
            # Show only unresolved gaps
            query = """
                SELECT cg.id, cg.query_pattern as pattern, cg.occurrence_count as count,
                       cg.avg_similarity_score as avg_score, cg.first_seen, cg.last_seen,
                       cg.resolved, cg.notes, ql.user_query as sample_query
                FROM content_gaps cg
                LEFT JOIN query_logs ql ON cg.sample_query_id = ql.id
                WHERE cg.resolved = 0
                ORDER BY cg.last_seen DESC
                LIMIT ?
            """
            params = (limit,)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        gaps = []
        for row in rows:
            gaps.append(
                ContentGap(
                    id=row["id"],
                    pattern=row["pattern"],
                    count=row["count"],
                    avg_score=row["avg_score"],
                    first_seen=row["first_seen"],
                    last_seen=row["last_seen"],
                    resolved=bool(row["resolved"]),
                    notes=row["notes"],
                    sample_query=row["sample_query"],
                )
            )

        # Get total count
        count_query = (
            "SELECT COUNT(*) FROM content_gaps WHERE resolved = 0"
            if not resolved
            else "SELECT COUNT(*) FROM content_gaps"
        )
        cursor.execute(count_query)
        total_count = cursor.fetchone()[0]

        conn.close()

        return ContentGapsResponse(gaps=gaps, total_count=total_count)

    except sqlite3.Error as e:
        logger.error(f"Database error in get_content_gaps: {e}")
        raise HTTPException(status_code=500, detail="Database error") from e
    except Exception as e:
        logger.error(f"Error in get_content_gaps: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.patch("/content/gaps/{gap_id}")
async def update_content_gap(
    gap_id: int,
    resolved: Optional[bool] = Query(None, description="Mark gap as resolved/unresolved"),
    notes: Optional[str] = Query(None, description="Add or update notes"),
):
    """
    Update a content gap's resolved status or notes.

    Args:
        gap_id: ID of the content gap to update
        resolved: Whether to mark the gap as resolved
        notes: Notes to add or update for the gap
    """
    if resolved is None and notes is None:
        raise HTTPException(status_code=400, detail="At least one field (resolved or notes) must be provided")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if gap exists
        cursor.execute("SELECT id FROM content_gaps WHERE id = ?", (gap_id,))
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=404, detail="Content gap not found")

        # Build update query
        update_parts = []
        params = []

        if resolved is not None:
            update_parts.append("resolved = ?")
            params.append(resolved)

        if notes is not None:
            update_parts.append("notes = ?")
            params.append(notes)

        params.append(gap_id)

        query = f"UPDATE content_gaps SET {', '.join(update_parts)} WHERE id = ?"
        cursor.execute(query, params)
        conn.commit()

        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail="Content gap not found")

        conn.close()

        return {"success": True, "message": "Content gap updated successfully"}

    except sqlite3.Error as e:
        logger.error(f"Database error in update_content_gap: {e}")
        raise HTTPException(status_code=500, detail="Database error") from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in update_content_gap: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/content/popular-topics")
async def get_popular_topics(time_range: str = Query("7d", description="Time range (7d, 30d, 90d)")):
    """
    Get popular query topics based on frequency analysis.

    Args:
        time_range: Time range for analysis (7d, 30d, 90d)
    """
    # This would be implemented with proper topic analysis
    # For now, return a placeholder response
    return {
        "topics": [
            {"topic": "Development", "count": 45},
            {"topic": "Experience", "count": 32},
            {"topic": "Skills", "count": 28},
        ]
    }


@router.get("/content/sources")
async def get_source_usage():
    """Get usage statistics for different content sources."""
    # This would be implemented with proper source analysis
    # For now, return a placeholder response
    return {
        "sources": [
            {"source": "Resume", "usage_count": 120},
            {"source": "About", "usage_count": 85},
            {"source": "Projects", "usage_count": 67},
        ]
    }
