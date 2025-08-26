"""
API routes for the RAG admin dashboard.
"""

import csv
import io
import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response, StreamingResponse

from .auth import auth_manager, require_admin_role, require_auth
from .database import db_manager, query_data_manager
from .models import (
    ChangePasswordRequest,
    CreateUserRequest,
    FeedbackUpdate,
    FileContentUpdate,
    LoginRequest,
    LoginResponse,
    OverviewStats,
    QueryResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/api", tags=["admin"])


# Authentication endpoints
@router.post("/auth/login", response_model=LoginResponse)
async def login(login_data: LoginRequest, request: Request, response: Response) -> LoginResponse:
    """Authenticate user and create session with rate limiting and security checks."""
    try:
        # Basic rate limiting check (in production, use Redis or similar)
        client_ip = request.client.host if request.client else "unknown"

        # Validate input
        if not login_data.username.strip() or not login_data.password:
            return LoginResponse(success=False, message="Username and password are required")
        user_agent = request.headers.get("User-Agent", "")

        auth_result = auth_manager.authenticate_user(
            login_data.username, login_data.password, ip_address=client_ip, user_agent=user_agent
        )

        if not auth_result:
            logger.warning(f"Failed login attempt for username: {login_data.username} from IP: {client_ip}")
            return LoginResponse(success=False, message="Invalid username or password")

        user_data = auth_result["user"].copy()
        user_data.pop("password_hash", None)  # Remove password hash from response

        # Set secure session cookie
        is_production = os.getenv("ENVIRONMENT", "development") == "production"
        response.set_cookie(
            key="admin_session",
            value=auth_result["session_id"],
            max_age=24 * 60 * 60,  # 24 hours
            httponly=True,
            secure=is_production,  # Only secure in production
            samesite="strict" if is_production else "lax",
        )

        return LoginResponse(
            success=True, message="Login successful", user=user_data, session_id=auth_result["session_id"]
        )

    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Login failed")


@router.post("/auth/logout")
async def logout(
    request: Request, response: Response, session: Dict[str, Any] = Depends(require_auth)
) -> Dict[str, Any]:
    """Logout user and expire session securely."""
    try:
        session_id = request.cookies.get("admin_session")
        if session_id:
            auth_manager.expire_session(session_id)

        # Clear session cookie
        response.delete_cookie(key="admin_session")

        return {"success": True, "message": "Logout successful"}

    except Exception as e:
        logger.error(f"Logout error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Logout failed")


@router.get("/auth/me")
async def get_current_user_info(session: Dict[str, Any] = Depends(require_auth)) -> Dict[str, Any]:
    """Get current authenticated user information (excluding sensitive data)."""
    user_data = {
        "id": session["user_id"],
        "username": session["username"],
        "email": session.get("email"),
        "role": session["role"],
        "last_login_at": session.get("last_login_at"),
    }
    return {"user": user_data}


@router.post("/auth/change-password")
async def change_password(
    password_data: ChangePasswordRequest, session: Dict[str, Any] = Depends(require_auth)
) -> Dict[str, Any]:
    """Change the current user's password with enhanced security."""
    try:
        # Get the current user
        user = db_manager.get_admin_user(session["username"])
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Verify current password
        if not auth_manager.verify_password(password_data.current_password, user["password_hash"]):
            logger.warning(f"Invalid current password attempt for user: {session['username']}")
            raise HTTPException(status_code=400, detail="Current password is incorrect")

        # Enhanced password validation
        new_password = password_data.new_password
        if len(new_password) < 8:
            raise HTTPException(status_code=400, detail="New password must be at least 8 characters long")

        # Check for basic password complexity (more efficient with single pass)
        has_upper = has_lower = has_digit = False
        for char in new_password:
            if char.isupper():
                has_upper = True
            elif char.islower():
                has_lower = True
            elif char.isdigit():
                has_digit = True
            # Early exit if all conditions are met
            if has_upper and has_lower and has_digit:
                break

        if not (has_upper and has_lower):
            raise HTTPException(status_code=400, detail="Password must contain both uppercase and lowercase letters")

        if not has_digit:
            raise HTTPException(status_code=400, detail="Password must contain at least one digit")

        # Hash and update the new password
        new_password_hash = auth_manager.hash_password(password_data.new_password)

        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE admin_users SET password_hash = ? WHERE id = ?", (new_password_hash, user["id"]))
            conn.commit()

        # Expire all sessions for this user (except current one)
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE admin_sessions SET is_active = 0 WHERE user_id = ? AND id != ?", (user["id"], session.get("id"))
            )
            conn.commit()

        return {"success": True, "message": "Password changed successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to change password")


@router.post("/auth/create-user")
async def create_user(
    user_data: CreateUserRequest, session: Dict[str, Any] = Depends(require_admin_role)
) -> Dict[str, Any]:
    """Create a new admin user (admin only) with validation."""
    try:
        # Check if username already exists
        existing_user = db_manager.get_admin_user(user_data.username)
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already exists")

        user_id = auth_manager.create_admin_user(
            username=user_data.username, password=user_data.password, email=user_data.email, role=user_data.role
        )

        return {"success": True, "message": f"User '{user_data.username}' created successfully", "user_id": user_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create user error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create user")


@router.get("/stats/overview", response_model=OverviewStats)
async def get_overview_stats(
    days: int = Query(7, ge=1, le=90), session: Dict[str, Any] = Depends(require_auth)
) -> OverviewStats:
    """Get overview statistics for the specified number of days."""
    try:
        stats = query_data_manager.get_overview_stats(days)
        return OverviewStats(
            total_queries=stats.get("total_queries", 0),
            unique_sessions=stats.get("unique_sessions", 0),
            avg_response_time_ms=stats.get("avg_response_time", 0) or 0,  # Database returns 'avg_response_time'
            error_rate=stats.get("error_rate", 0) or 0,
            cache_hit_rate=stats.get("cache_hit_rate", 0) or 0,
            helpful_rate=stats.get("helpful_rate", 0) or 0,
            queries_today=stats.get("queries_today", 0),
            queries_this_week=stats.get("queries_this_week", 0),
        )
    except Exception as e:
        logger.error(f"Error fetching overview stats: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching overview statistics")


@router.get("/queries", response_model=QueryResponse)
async def get_queries(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None, max_length=500),
    errors_only: bool = Query(False),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    session: Dict[str, Any] = Depends(require_auth),
) -> QueryResponse:
    """Get paginated list of queries with optional filters and input sanitization."""
    try:
        # Sanitize search input
        if search:
            search = search.strip()[:500]  # Limit search length
        result = query_data_manager.get_queries(
            limit=limit,
            offset=offset,
            search_query=search,
            error_filter=errors_only,
            date_from=start_date,
            date_to=end_date,
        )
        return QueryResponse(**result)
    except Exception as e:
        logger.error(f"Error fetching queries: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching queries")


@router.get("/queries/{query_id}")
async def get_query_detail(query_id: int, session: Dict[str, Any] = Depends(require_auth)) -> Dict[str, Any]:
    """Get detailed information about a specific query with proper error handling."""
    if query_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid query ID")

    try:
        # Filter by ID (simplified for this implementation)
        with query_data_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM query_logs WHERE id = ?", (query_id,))
            row = cursor.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="Query not found")

            query_dict = dict(row)
            # Safely parse JSON fields
            try:
                if query_dict["sources_used"]:
                    query_dict["sources_used"] = json.loads(query_dict["sources_used"])
            except (json.JSONDecodeError, TypeError):
                query_dict["sources_used"] = []

            try:
                if query_dict["follow_up_questions"]:
                    query_dict["follow_up_questions"] = json.loads(query_dict["follow_up_questions"])
            except (json.JSONDecodeError, TypeError):
                query_dict["follow_up_questions"] = []

            return query_dict
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching query detail: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching query details")


@router.post("/queries/{query_id}/feedback")
async def update_query_feedback(
    query_id: int, feedback: FeedbackUpdate, session: Dict[str, Any] = Depends(require_auth)
) -> Dict[str, str]:
    """Update user feedback for a query with validation."""
    if query_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid query ID")

    try:
        # Update feedback directly in the backend database
        with query_data_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE query_logs SET user_feedback = ? WHERE id = ?", (feedback.feedback, query_id))
            conn.commit()
        return {"status": "success", "message": "Feedback updated"}
    except Exception as e:
        logger.error(f"Error updating feedback: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error updating feedback")


@router.get("/performance/metrics")
async def get_performance_metrics(
    time_range: str = Query("24h", regex="^(1h|6h|24h|7d|30d)$"), session: Dict[str, Any] = Depends(require_auth)
) -> Dict[str, Any]:
    """Get performance metrics for the specified time range with comparison to previous period."""
    try:

        def get_previous_time_range(time_range: str) -> str:
            """Calculate the equivalent previous time range for comparison."""
            # For now, return the same time range to get a baseline comparison
            # In a full implementation, this would calculate dates for the previous period
            # e.g., if current is last 24h, previous would be 24h before that
            time_mappings = {
                "1h": "2h",  # Compare current 1h to previous 1h (using 2h and offset)
                "6h": "12h",  # Compare current 6h to previous 6h (using 12h and offset)
                "24h": "48h",  # Compare current 24h to previous 24h (using 48h and offset)
                "7d": "14d",  # Compare current 7d to previous 7d (using 14d and offset)
                "30d": "60d",  # Compare current 30d to previous 30d (using 60d and offset)
            }
            return time_mappings.get(time_range, time_range)

        current_metrics = query_data_manager.get_performance_metrics(time_range)
        # Get broader time range and calculate previous period metrics
        previous_time_range = get_previous_time_range(time_range)
        broader_metrics = query_data_manager.get_performance_metrics(previous_time_range)

        # For now, use half the values from broader range as approximation of previous period
        # This is a simplified approach - a full implementation would use date filtering
        previous_metrics = {
            key: (value * 0.5 if isinstance(value, (int, float)) and value is not None else value)
            for key, value in broader_metrics.items()
        }

        def safe_divide(a, b):
            return (a or 0) / max(b or 1, 1)

        def calculate_change(current, previous):
            if not previous or previous == 0:
                return 0
            return ((current or 0) - previous) / previous * 100

        # Calculate current values
        current_response_time = current_metrics.get("avg_response_time", 0) or 0
        current_throughput = current_metrics.get("total_queries", 0) or 0
        current_error_rate = (
            safe_divide(current_metrics.get("error_count", 0), current_metrics.get("total_queries", 1)) * 100
        )
        current_cache_hit_rate = (current_metrics.get("cache_hit_rate", 0) or 0) * 100

        # Calculate previous values
        previous_response_time = previous_metrics.get("avg_response_time", 0) or 0
        previous_throughput = previous_metrics.get("total_queries", 0) or 0
        previous_error_rate = (
            safe_divide(previous_metrics.get("error_count", 0), previous_metrics.get("total_queries", 1)) * 100
        )
        previous_cache_hit_rate = (previous_metrics.get("cache_hit_rate", 0) or 0) * 100

        return {
            "response_time": {
                "current": round(current_response_time, 1),
                "previous": round(previous_response_time, 1),
                "change": round(calculate_change(current_response_time, previous_response_time), 1),
            },
            "throughput": {
                "current": current_throughput,
                "previous": previous_throughput,
                "change": round(calculate_change(current_throughput, previous_throughput), 1),
            },
            "error_rate": {
                "current": round(current_error_rate, 2),
                "previous": round(previous_error_rate, 2),
                "change": round(calculate_change(current_error_rate, previous_error_rate), 1),
            },
            "cache_hit_rate": {
                "current": round(current_cache_hit_rate, 1),
                "previous": round(previous_cache_hit_rate, 1),
                "change": round(calculate_change(current_cache_hit_rate, previous_cache_hit_rate), 1),
            },
        }
    except Exception as e:
        logger.error(f"Error fetching performance metrics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching performance metrics")


@router.get("/performance/timeline")
async def get_performance_timeline(
    days: int = Query(7, ge=1, le=90),
    interval: str = Query("hour", regex="^(hour|day)$"),
    session: Dict[str, Any] = Depends(require_auth),
):
    """Get time series data for performance charts."""
    try:
        with query_data_manager.get_connection() as conn:
            cursor = conn.cursor()

            if interval == "hour":
                time_group = "strftime('%Y-%m-%d %H:00:00', timestamp)"
            else:
                time_group = "date(timestamp)"

            cursor.execute(
                f"""
                SELECT 
                    {time_group} as time_bucket,
                    COUNT(*) as query_count,
                    AVG(response_time_ms) as avg_response_time,
                    SUM(CASE WHEN error_occurred THEN 1 ELSE 0 END) as error_count,
                    AVG(CASE WHEN cache_hit THEN 1.0 ELSE 0.0 END) as cache_hit_rate
                FROM query_logs 
                WHERE timestamp >= datetime('now', '-{days} days')
                GROUP BY {time_group}
                ORDER BY time_bucket
            """
            )

            timeline_data = []
            for row in cursor.fetchall():
                query_count = row[1]
                error_count = row[3]
                error_rate = (error_count / max(query_count, 1)) if query_count > 0 else 0

                timeline_data.append(
                    {
                        "timestamp": row[0],
                        "query_count": row[1],
                        "avg_response_time": row[2] or 0,
                        "error_count": row[3],
                        "error_rate": error_rate,
                        "cache_hit_rate": row[4] or 0,
                    }
                )

            return {"timeline": timeline_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching timeline data: {str(e)}")


@router.get("/performance/percentiles")
async def get_response_time_percentiles(
    time_range: str = Query("24h", regex="^(1h|6h|24h|7d|30d)$"), session: Dict[str, Any] = Depends(require_auth)
):
    """Get response time percentiles for the specified time range."""
    try:
        metrics = query_data_manager.get_performance_metrics(time_range)
        return {
            "p50": round(metrics.get("p50_response_time", 0) or 0, 1),
            "p95": round(metrics.get("p95_response_time", 0) or 0, 1),
            "p99": round(metrics.get("p99_response_time", 0) or 0, 1),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching percentiles: {str(e)}")


@router.get("/content/gaps")
async def get_content_gaps(
    resolved: bool = Query(False, description="Include resolved content gaps"),
    limit: int = Query(50, ge=1, le=200),
    session: Dict[str, Any] = Depends(require_auth),
):
    """Get content gaps detected automatically by the query logger."""
    try:
        with query_data_manager.get_connection() as conn:
            cursor = conn.cursor()

            # Get content gaps from the dedicated table
            where_clause = "WHERE resolved = 0" if not resolved else ""

            cursor.execute(
                f"""
                SELECT 
                    cg.id,
                    cg.query_pattern,
                    cg.occurrence_count,
                    cg.avg_similarity_score,
                    cg.first_seen,
                    cg.last_seen,
                    cg.resolved,
                    cg.notes,
                    ql.user_query as sample_query
                FROM content_gaps cg
                LEFT JOIN query_logs ql ON cg.sample_query_id = ql.id
                {where_clause}
                ORDER BY cg.occurrence_count DESC, cg.avg_similarity_score ASC
                LIMIT ?
                """,
                (limit,),
            )

            gaps = []
            for row in cursor.fetchall():
                gaps.append(
                    {
                        "id": row[0],
                        "pattern": row[1],
                        "count": row[2],
                        "avg_score": round(row[3] or 0, 2),
                        "first_seen": row[4],
                        "last_seen": row[5],
                        "resolved": bool(row[6]),
                        "notes": row[7],
                        "sample_query": row[8],
                    }
                )

            return {"gaps": gaps, "total": len(gaps)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching content gaps: {str(e)}")


@router.patch("/content/gaps/{gap_id}")
async def update_content_gap(
    gap_id: int,
    resolved: bool = Query(None, description="Mark as resolved/unresolved"),
    notes: str = Query(None, description="Add notes about the content gap"),
    session: Dict[str, Any] = Depends(require_auth),
):
    """Update a content gap (mark as resolved, add notes)."""
    try:
        with query_data_manager.get_connection() as conn:
            cursor = conn.cursor()

            # Build update query
            updates = []
            params = []

            if resolved is not None:
                updates.append("resolved = ?")
                params.append(resolved)

            if notes is not None:
                updates.append("notes = ?")
                params.append(notes)

            if not updates:
                raise HTTPException(status_code=400, detail="No updates provided")

            params.append(gap_id)

            cursor.execute(f"UPDATE content_gaps SET {', '.join(updates)} WHERE id = ?", params)

            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Content gap not found")

            conn.commit()
            return {"message": "Content gap updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating content gap: {str(e)}")


@router.get("/content/popular-topics")
async def get_popular_topics(session: Dict[str, Any] = Depends(require_auth)):
    """Get most queried topics/themes."""
    try:
        with query_data_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT 
                    user_query,
                    COUNT(*) as query_count,
                    AVG(response_time_ms) as avg_response_time,
                    AVG(vector_search_score) as avg_score
                FROM query_logs 
                WHERE timestamp >= datetime('now', '-30 days')
                GROUP BY user_query
                HAVING query_count > 1
                ORDER BY query_count DESC
                LIMIT 20
            """
            )

            topics = []
            for row in cursor.fetchall():
                topics.append(
                    {"query": row[0], "count": row[1], "avg_response_time": row[2] or 0, "avg_score": row[3] or 0}
                )

            return topics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching popular topics: {str(e)}")


@router.get("/sessions")
async def get_sessions(
    active_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=1000),
    session: Dict[str, Any] = Depends(require_auth),
):
    """Get user session information."""
    try:
        with query_data_manager.get_connection() as conn:
            cursor = conn.cursor()

            where_clause = ""
            if active_only:
                where_clause = "WHERE last_active_at >= datetime('now', '-1 hour')"

            cursor.execute(
                f"""
                SELECT * FROM user_sessions 
                {where_clause}
                ORDER BY last_active_at DESC 
                LIMIT ?
            """,
                (limit,),
            )

            sessions = [dict(row) for row in cursor.fetchall()]
            return sessions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching sessions: {str(e)}")


@router.get("/export/csv")
async def export_csv(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    export_type: str = Query("queries", regex="^(queries|metrics)$"),
    session: Dict[str, Any] = Depends(require_auth),
):
    """Export data as CSV file."""
    try:
        output = io.StringIO()
        writer = csv.writer(output)

        with query_data_manager.get_connection() as conn:
            cursor = conn.cursor()

            if export_type == "queries":
                # Build WHERE clause for date filtering
                where_conditions = []
                params = []

                if start_date:
                    where_conditions.append("timestamp >= ?")
                    params.append(start_date)

                if end_date:
                    where_conditions.append("timestamp <= ?")
                    params.append(end_date)

                where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""

                cursor.execute(
                    f"""
                    SELECT 
                        id, session_id, user_query, response_time_ms, 
                        llm_provider, llm_model, vector_search_score,
                        cache_hit, error_occurred, error_message, 
                        user_feedback, timestamp
                    FROM query_logs{where_clause}
                    ORDER BY timestamp DESC
                """,
                    params,
                )

                # Write header
                writer.writerow(
                    [
                        "ID",
                        "Session ID",
                        "User Query",
                        "Response Time (ms)",
                        "LLM Provider",
                        "LLM Model",
                        "Search Score",
                        "Cache Hit",
                        "Error Occurred",
                        "Error Message",
                        "User Feedback",
                        "Timestamp",
                    ]
                )

                # Write data
                for row in cursor.fetchall():
                    writer.writerow(row)

            elif export_type == "metrics":
                cursor.execute(
                    """
                    SELECT * FROM hourly_metrics 
                    ORDER BY hour DESC
                """
                )

                # Write header
                writer.writerow(
                    [
                        "ID",
                        "Hour",
                        "Total Queries",
                        "Unique Sessions",
                        "Avg Response Time (ms)",
                        "P95 Response Time (ms)",
                        "Cache Hit Rate",
                        "Error Rate",
                        "Helpful Rate",
                    ]
                )

                # Write data
                for row in cursor.fetchall():
                    writer.writerow(row)

        # Prepare response
        output.seek(0)
        filename = f"rag_admin_{export_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting CSV: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check endpoint (no auth required)."""
    try:
        # Test database connection
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()

        return {"status": "healthy", "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")


# Knowledge base management endpoints
@router.post("/knowledge/upload")
async def upload_knowledge_files(
    files: List[UploadFile] = File(...), session: Dict[str, Any] = Depends(require_auth)
) -> Dict[str, Any]:
    """Upload files to the knowledge base directory with security validation."""
    # Security: Only allow authenticated users
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    if len(files) > 10:  # Limit number of files
        raise HTTPException(status_code=400, detail="Too many files (max 10 per upload)")

    # Get the knowledge base directory path
    knowledge_dir = Path(__file__).parent.parent.parent / "backend" / "knowledge"

    # Security check: ensure directory is within expected bounds
    try:
        knowledge_dir = knowledge_dir.resolve()
        expected_base = Path(__file__).parent.parent.parent.resolve()
        knowledge_dir.relative_to(expected_base)
    except ValueError:
        raise HTTPException(status_code=500, detail="Invalid knowledge directory path")

    knowledge_dir.mkdir(parents=True, exist_ok=True)

    # Allowed file extensions and MIME types for security
    allowed_extensions = {".md", ".pdf", ".json", ".txt", ".html", ".docx"}
    allowed_mime_types = {
        "text/markdown",
        "text/plain",
        "application/json",
        "text/html",
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/octet-stream",  # Some browsers send this for text files
    }

    uploaded_files = []
    errors = []

    try:
        for file in files:
            # Security: Validate filename
            if not file.filename or ".." in file.filename or "/" in file.filename or "\\" in file.filename:
                errors.append(f"Invalid filename: {file.filename}")
                continue

            # Validate file extension
            file_ext = Path(file.filename).suffix.lower()
            if file_ext not in allowed_extensions:
                errors.append(
                    f"File '{file.filename}' has unsupported extension. Allowed: {', '.join(allowed_extensions)}"
                )
                continue

            # Validate MIME type for additional security
            if file.content_type and file.content_type not in allowed_mime_types:
                logger.warning(f"Suspicious file upload attempt: {file.filename} with MIME type {file.content_type}")
                errors.append(f"File '{file.filename}' has unsupported content type")
                continue

            # Check file size (5MB limit for security)
            if file.size and file.size > 5 * 1024 * 1024:
                errors.append(f"File '{file.filename}' is too large (max 5MB)")
                continue

            # Security: Sanitize filename
            safe_filename = "".join(c for c in file.filename if c.isalnum() or c in ".-_").rstrip()
            if not safe_filename:
                errors.append(f"Invalid filename after sanitization: {file.filename}")
                continue

            # Save file to knowledge directory
            file_path = knowledge_dir / safe_filename

            # Check if file already exists
            if file_path.exists():
                errors.append(f"File '{safe_filename}' already exists")
                continue

            # Security: Ensure file path is within knowledge directory
            try:
                file_path.resolve().relative_to(knowledge_dir.resolve())
            except ValueError:
                errors.append(f"Invalid file path: {safe_filename}")
                continue

            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            uploaded_files.append({"filename": safe_filename, "size": file.size or 0, "path": str(file_path)})

    except Exception as e:
        logger.error(f"Error uploading files: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error uploading files")

    # Return results
    response = {"uploaded_files": uploaded_files, "upload_count": len(uploaded_files), "total_files": len(files)}

    if errors:
        response["errors"] = errors

    if not uploaded_files and errors:
        raise HTTPException(status_code=400, detail={"message": "No files were uploaded", "errors": errors})

    return response


@router.get("/knowledge/files")
async def get_knowledge_files(session: Dict[str, Any] = Depends(require_auth)):
    """Get list of files in the knowledge base directory."""
    knowledge_dir = Path(__file__).parent.parent.parent / "backend" / "knowledge"

    if not knowledge_dir.exists():
        return {"files": [], "total_files": 0}

    try:
        files = []
        for file_path in knowledge_dir.iterdir():
            if file_path.is_file() and not file_path.name.startswith("."):
                stat = file_path.stat()
                files.append(
                    {
                        "name": file_path.name,
                        "type": file_path.suffix.lower(),
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    }
                )

        # Sort by modification time (newest first)
        files.sort(key=lambda x: x["modified"], reverse=True)

        return {"files": files, "total_files": len(files)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing files: {str(e)}")


@router.delete("/knowledge/files/{filename}")
async def delete_knowledge_file(filename: str, session: Dict[str, Any] = Depends(require_auth)) -> Dict[str, str]:
    """Delete a file from the knowledge base directory with enhanced security."""
    # Enhanced security validation
    if not filename or ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Only allow specific file extensions for deletion
    allowed_extensions = {".md", ".pdf", ".json", ".txt", ".html", ".docx"}
    file_ext = Path(filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="File type not allowed")

    knowledge_dir = Path(__file__).parent.parent.parent / "backend" / "knowledge"
    file_path = knowledge_dir / filename

    # Security check - ensure file is in knowledge directory
    try:
        resolved_path = file_path.resolve()
        resolved_knowledge_dir = knowledge_dir.resolve()
        resolved_path.relative_to(resolved_knowledge_dir)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid file path")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")

    try:
        file_path.unlink()
        return {"message": f"File '{filename}' deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting file {filename}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error deleting file")


@router.get("/knowledge/stats")
async def get_knowledge_stats(session: Dict[str, Any] = Depends(require_auth)):
    """Get statistics about the knowledge base."""
    knowledge_dir = Path(__file__).parent.parent.parent / "backend" / "knowledge"

    if not knowledge_dir.exists():
        return {"total_files": 0, "indexed_documents": 0, "last_indexed": None}

    try:
        # Count files
        files = [f for f in knowledge_dir.iterdir() if f.is_file() and not f.name.startswith(".")]
        total_files = len(files)

        # For indexed_documents, we'll use the same count as total_files for now
        # In a real implementation, you might query the vector database
        indexed_documents = total_files

        # Get last modification time as proxy for last indexed
        last_indexed = None
        if files:
            latest_file = max(files, key=lambda f: f.stat().st_mtime)
            last_indexed = datetime.fromtimestamp(latest_file.stat().st_mtime).isoformat()

        return {"total_files": total_files, "indexed_documents": indexed_documents, "last_indexed": last_indexed}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting stats: {str(e)}")


@router.post("/knowledge/refresh")
async def refresh_knowledge_base(
    force_reindex: bool = Query(True, description="Force re-indexing of all files"),
    session: Dict[str, Any] = Depends(require_auth),
) -> Dict[str, Any]:
    """Trigger a production-ready refresh of the knowledge base index."""
    try:
        from .knowledge_refresh_service_v2 import knowledge_refresh_service

        result = await knowledge_refresh_service.refresh_knowledge_base(force_reindex=force_reindex)
        return result
    except ImportError:
        logger.warning("Knowledge refresh service not available")
        raise HTTPException(status_code=503, detail="Knowledge refresh service not available")
    except Exception as e:
        logger.error(f"Knowledge base refresh failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error refreshing knowledge base")


@router.get("/knowledge/refresh/status")
async def get_refresh_status(session: Dict[str, Any] = Depends(require_auth)) -> Dict[str, Any]:
    """Get the current status of knowledge base refresh operation."""
    try:
        from .knowledge_refresh_service_v2 import knowledge_refresh_service

        return knowledge_refresh_service.get_refresh_status()
    except ImportError:
        logger.warning("Knowledge refresh service not available")
        raise HTTPException(status_code=503, detail="Knowledge refresh service not available")
    except Exception as e:
        logger.error(f"Failed to get refresh status: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error getting refresh status")


@router.post("/knowledge/refresh/wait")
async def wait_for_refresh_completion(
    timeout: int = Query(300, ge=10, le=600, description="Timeout in seconds"),
    session: Dict[str, Any] = Depends(require_auth),
) -> Dict[str, Any]:
    """Wait for the current refresh operation to complete."""
    try:
        from .knowledge_refresh_service_v2 import knowledge_refresh_service

        result = await knowledge_refresh_service.wait_for_completion(timeout=timeout)
        return result
    except ImportError:
        logger.warning("Knowledge refresh service not available")
        raise HTTPException(status_code=503, detail="Knowledge refresh service not available")
    except Exception as e:
        logger.error(f"Error waiting for refresh completion: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error waiting for refresh completion")


@router.get("/knowledge/files/{filename}/content")
async def get_knowledge_file_content(filename: str, session: Dict[str, Any] = Depends(require_auth)) -> Dict[str, Any]:
    """Get the content of a specific file from the knowledge base directory with security validation."""
    # Enhanced security validation
    if not filename or ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    knowledge_dir = Path(__file__).parent.parent.parent / "backend" / "knowledge"
    file_path = knowledge_dir / filename

    # Security check - ensure file is in knowledge directory
    try:
        resolved_path = file_path.resolve()
        resolved_knowledge_dir = knowledge_dir.resolve()
        resolved_path.relative_to(resolved_knowledge_dir)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid file path")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")

    # Check if file type is editable
    editable_extensions = {".md", ".json", ".txt", ".html"}
    if file_path.suffix.lower() not in editable_extensions:
        raise HTTPException(status_code=400, detail="File type not editable")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        return {
            "filename": filename,
            "content": content,
            "size": file_path.stat().st_size,
            "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
            "type": file_path.suffix.lower(),
        }
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File is not a text file or has invalid encoding")
    except Exception as e:
        logger.error(f"Error reading file {filename}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error reading file")


@router.put("/knowledge/files/{filename}/content")
async def update_knowledge_file_content(
    filename: str, file_content: FileContentUpdate, session: Dict[str, Any] = Depends(require_auth)
) -> Dict[str, Any]:
    """Update the content of a specific file in the knowledge base directory with backup and validation."""
    # Enhanced security validation
    if not filename or ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    knowledge_dir = Path(__file__).parent.parent.parent / "backend" / "knowledge"
    file_path = knowledge_dir / filename

    # Security check - ensure file is in knowledge directory
    try:
        resolved_path = file_path.resolve()
        resolved_knowledge_dir = knowledge_dir.resolve()
        resolved_path.relative_to(resolved_knowledge_dir)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid file path")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")

    # Check if file type is editable
    editable_extensions = {".md", ".json", ".txt", ".html"}
    if file_path.suffix.lower() not in editable_extensions:
        raise HTTPException(status_code=400, detail="File type not editable")

    # Validate JSON content if it's a JSON file
    if file_path.suffix.lower() == ".json":
        try:
            import json

            json.loads(file_content.content)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")

    try:
        # Create backup of original file
        backup_path = file_path.with_suffix(file_path.suffix + ".backup")
        shutil.copy2(file_path, backup_path)

        # Write new content
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(file_content.content)

        # Remove backup after successful write
        backup_path.unlink()

        return {
            "message": f"File '{filename}' updated successfully",
            "filename": filename,
            "size": file_path.stat().st_size,
            "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
        }
    except Exception as e:
        # Restore from backup if write failed
        try:
            if backup_path.exists():
                shutil.copy2(backup_path, file_path)
                backup_path.unlink()
        except Exception as restore_error:
            logger.error(f"Failed to restore backup for {filename}: {str(restore_error)}")

        logger.error(f"Error updating file {filename}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error updating file")
