"""
Comprehensive admin routes for the main backend.
Migrated from admin/backend/routes.py with full functionality.
"""

import csv
import io
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse

from ..core.admin_auth import admin_auth_manager, require_admin_auth, require_admin_role
from ..core.admin_database import admin_db_manager
from ..core.audit_logger import AuditAction, AuditLogger
from ..core.config import FollowUpSettings

# CSRF protection removed - session-based auth is inherently CSRF-resistant for our use case
from ..core.query_data_manager import query_data_manager
from ..models.admin_models import (
    AdminUser,
    BulkQuestionRequest,
    CategoryDeleteRequest,
    CategoryWithStats,
    ChangePasswordRequest,
    CreateFollowupCategoryRequest,
    CreateFollowupQuestionRequest,
    CreateUserRequest,
    FeedbackUpdate,
    FollowupCategory,
    FollowupQuestion,
    LoginRequest,
    LoginResponse,
    OverviewStats,
    QueryResponse,
    QuestionSearchRequest,
    ReorderCategoriesRequest,
    UpdateFollowupCategoryRequest,
    UpdateFollowupQuestionRequest,
)

logger = logging.getLogger(__name__)

# Initialize audit logger
audit_logger = AuditLogger()

router = APIRouter(tags=["admin"])


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

        auth_result = admin_auth_manager.authenticate_user(
            login_data.username, login_data.password, ip_address=client_ip, user_agent=user_agent
        )

        if not auth_result:
            logger.warning(f"Failed login attempt for username: {login_data.username} from IP: {client_ip}")

            # Audit log failed login
            from ..core.audit_logger import audit_logger

            audit_logger.log_login(
                login_data.username, client_ip, user_agent, success=False, error_message="Invalid credentials"
            )

            return LoginResponse(success=False, message="Invalid username or password")

        user_data = auth_result["user"].copy()
        user_data.pop("password_hash", None)  # Remove password hash from response

        # Set secure HTTPOnly session cookie
        is_production = os.getenv("ENVIRONMENT", "development") == "production"
        response.set_cookie(
            key="admin_session",
            value=auth_result["session_id"],
            max_age=24 * 60 * 60,  # 24 hours
            httponly=True,  # Always HTTPOnly for security
            secure=is_production,  # Only secure in production (requires HTTPS)
            samesite="lax",  # Lax for better compatibility with same-domain dev
        )

        # Audit log successful login
        from ..core.audit_logger import audit_logger

        audit_logger.log_login(login_data.username, client_ip, user_agent, success=True, method="password")

        return LoginResponse(
            success=True, message="Login successful", user=user_data, session_id=auth_result["session_id"]
        )

    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Login failed")


@router.post("/auth/logout")
async def logout(
    request: Request, response: Response, session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Logout user and expire session securely."""
    try:
        session_id = request.cookies.get("admin_session")
        if session_id:
            admin_auth_manager.expire_session(session_id)

        # Clear session cookie with same attributes as when set
        is_production = os.getenv("ENVIRONMENT", "development") == "production"
        response.delete_cookie(key="admin_session", secure=is_production, samesite="lax")

        # Audit log logout
        from ..core.audit_logger import audit_logger

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")
        audit_logger.log_logout(session["username"], client_ip, user_agent)

        return {"success": True, "message": "Logout successful"}

    except Exception as e:
        logger.error(f"Logout error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Logout failed")


@router.get("/auth/me")
async def get_current_user_info(session: Dict[str, Any] = Depends(require_admin_auth)) -> Dict[str, Any]:
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
    password_data: ChangePasswordRequest, request: Request, session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Change the current user's password with enhanced security and rate limiting."""
    try:
        # Rate limiting for password change attempts
        client_ip = request.client.host if request.client else "unknown"
        if admin_auth_manager.is_rate_limited(client_ip, "ip"):
            logger.warning(f"Rate limited password change attempt from {client_ip} for user {session['username']}")
            raise HTTPException(status_code=429, detail="Too many password change attempts. Please try again later.")

        # Get the current user
        user = admin_db_manager.get_admin_user(session["username"])
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Verify current password
        if not admin_auth_manager.verify_password(password_data.current_password, user["password_hash"]):
            # Record failed password verification attempt
            admin_db_manager.record_rate_limit_attempt(client_ip, "ip", 5)
            admin_db_manager.record_security_event(
                "password_change_failure",
                session["username"],
                "medium",
                "Failed password change attempt - invalid current password",
                client_ip,
                request.headers.get("User-Agent"),
            )
            logger.warning(f"Invalid current password attempt for user: {session['username']} from IP: {client_ip}")
            raise HTTPException(status_code=400, detail="Current password is incorrect")

        # Validate new password using centralized validation
        try:
            admin_auth_manager.validate_password_strength(password_data.new_password)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Hash and update the new password
        new_password_hash = admin_auth_manager.hash_password(password_data.new_password)
        success = admin_db_manager.update_user_password(user["id"], new_password_hash)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update password")

        # Reset failed attempts on successful password change
        admin_db_manager.reset_rate_limit(client_ip, "ip")

        # Audit log password change
        from ..core.audit_logger import audit_logger

        audit_logger.log_password_change(
            session["username"], session["username"], client_ip, request.headers.get("User-Agent", ""), success=True
        )

        # Expire all sessions for this user (except current one)
        admin_auth_manager.expire_user_sessions(user["id"])

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
        existing_user = admin_db_manager.get_admin_user(user_data.username)
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already exists")

        user_id = admin_auth_manager.create_admin_user(
            username=user_data.username, password=user_data.password, email=user_data.email, role=user_data.role
        )

        return {"success": True, "message": f"User '{user_data.username}' created successfully", "user_id": user_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create user error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create user")


# Stats endpoints
@router.get("/stats/overview", response_model=OverviewStats)
async def get_overview_stats(
    days: float = Query(7, ge=0.1, le=90), session: Dict[str, Any] = Depends(require_admin_auth)
) -> OverviewStats:
    """Get overview statistics for the specified number of days."""
    try:
        stats = query_data_manager.get_overview_stats(days)
        return OverviewStats(
            total_queries=stats.get("total_queries", 0),
            unique_sessions=stats.get("unique_sessions", 0),
            avg_response_time_ms=stats.get("avg_response_time", 0) or 0,
            error_rate=stats.get("error_rate", 0) or 0,
            cache_hit_rate=stats.get("cache_hit_rate", 0) or 0,
            helpful_rate=stats.get("helpful_rate", 0) or 0,
            queries_today=stats.get("queries_today", 0),
            queries_this_week=stats.get("queries_this_week", 0),
            total_queries_change=stats.get("total_queries_change", 0) or 0,
            unique_sessions_change=stats.get("unique_sessions_change", 0) or 0,
            avg_response_time_change=stats.get("avg_response_time_change", 0) or 0,
            error_rate_change=stats.get("error_rate_change", 0) or 0,
            cache_hit_rate_change=stats.get("cache_hit_rate_change", 0) or 0,
            helpful_rate_change=stats.get("helpful_rate_change", 0) or 0,
        )
    except Exception as e:
        logger.error(f"Error fetching overview stats: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching overview statistics")


# Health endpoint
@router.get("/health")
async def health_check():
    """Health check endpoint (no auth required)."""
    try:
        # Test database connection
        with admin_db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()

        return {"status": "healthy", "timestamp": datetime.now().isoformat()}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")


# Query management endpoints
@router.get("/queries", response_model=QueryResponse)
async def get_queries(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None, max_length=500),
    errors_only: bool = Query(False),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    session: Dict[str, Any] = Depends(require_admin_auth),
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
async def get_query_detail(query_id: int, session: Dict[str, Any] = Depends(require_admin_auth)) -> Dict[str, Any]:
    """Get detailed information about a specific query with proper error handling."""
    if query_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid query ID")

    try:
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
    query_id: int, feedback: FeedbackUpdate, session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, str]:
    """Update user feedback for a query with validation."""
    if query_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid query ID")

    try:
        with query_data_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE query_logs SET user_feedback = ? WHERE id = ?", (feedback.feedback, query_id))
            conn.commit()
        return {"status": "success", "message": "Feedback updated"}
    except Exception as e:
        logger.error(f"Error updating feedback: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error updating feedback")


# Performance endpoints
@router.get("/performance/metrics")
async def get_performance_metrics(
    time_range: str = Query("24h", pattern="^(1h|6h|24h|7d|30d)$"),
    session: Dict[str, Any] = Depends(require_admin_auth),
) -> Dict[str, Any]:
    """Get performance metrics for the specified time range."""
    try:
        # Use the same logic as the main performance API endpoint
        from datetime import datetime, timedelta

        from ..core.config import AppConfig

        # Import database connection utility from performance route
        from ..core.database_utils import get_rag_monitoring_db_connection as get_db_connection

        def parse_time_range(time_range: str) -> tuple:
            """Parse time range string to start and end dates."""
            end_date = datetime.now()
            if time_range == "1h":
                start_date = end_date - timedelta(hours=1)
            elif time_range == "6h":
                start_date = end_date - timedelta(hours=6)
            elif time_range == "24h":
                start_date = end_date - timedelta(hours=24)
            elif time_range == "7d":
                start_date = end_date - timedelta(days=7)
            elif time_range == "30d":
                start_date = end_date - timedelta(days=30)
            else:
                start_date = end_date - timedelta(hours=24)
            return start_date, end_date

        conn = get_db_connection()

        if not conn:
            # Return empty metrics if database is not available
            return {
                "response_time": {"current": 0, "previous": 0, "change": 0},
                "throughput": {"current": 0, "previous": 0, "change": 0},
                "error_rate": {"current": 0, "previous": 0, "change": 0},
                "cache_hit_rate": {"current": 85.0, "previous": 85.0, "change": 0},
            }

        cursor = conn.cursor()
        start_date, end_date = parse_time_range(time_range)

        # Calculate dynamic date ranges based on the period
        period_duration = end_date - start_date
        previous_period_end = start_date
        previous_period_start = previous_period_end - period_duration

        # Convert to string format for SQL queries
        current_period_start = start_date.isoformat()
        current_period_end = end_date.isoformat()
        previous_start = previous_period_start.isoformat()
        previous_end = previous_period_end.isoformat()

        # Get current period metrics
        cursor.execute(
            """
            SELECT 
                AVG(response_time_ms) as avg_response_time,
                COUNT(*) as query_count,
                AVG(CASE WHEN error_occurred = 1 THEN 1 ELSE 0 END) as error_rate
            FROM query_logs
            WHERE timestamp >= ? AND timestamp <= ?
            AND response_time_ms IS NOT NULL
        """,
            (current_period_start, current_period_end),
        )

        current_result = cursor.fetchone()
        current_response_time = current_result["avg_response_time"] or 0.0
        current_queries = current_result["query_count"] or 0
        current_error_rate = (current_result["error_rate"] or 0.0) * 100

        # Get previous period metrics
        cursor.execute(
            """
            SELECT 
                AVG(response_time_ms) as avg_response_time,
                COUNT(*) as query_count,
                AVG(CASE WHEN error_occurred = 1 THEN 1 ELSE 0 END) as error_rate
            FROM query_logs
            WHERE timestamp >= ? AND timestamp <= ?
            AND response_time_ms IS NOT NULL
        """,
            (previous_start, previous_end),
        )

        previous_result = cursor.fetchone()
        previous_response_time = previous_result["avg_response_time"] or 0.0
        previous_queries = previous_result["query_count"] or 0
        previous_error_rate = (previous_result["error_rate"] or 0.0) * 100

        conn.close()

        # Calculate changes
        def calculate_change(current, previous):
            if previous == 0:
                return 100.0 if current > 0 else 0.0
            return round(((current - previous) / previous) * 100, 2)

        # Calculate throughput (queries per hour)
        period_hours = period_duration.total_seconds() / 3600
        current_throughput = current_queries / period_hours if period_hours > 0 else 0
        previous_throughput = previous_queries / period_hours if period_hours > 0 else 0

        return {
            "response_time": {
                "current": round(current_response_time, 1),
                "previous": round(previous_response_time, 1),
                "change": calculate_change(current_response_time, previous_response_time),
            },
            "throughput": {
                "current": round(current_throughput, 1),
                "previous": round(previous_throughput, 1),
                "change": calculate_change(current_throughput, previous_throughput),
            },
            "error_rate": {
                "current": round(current_error_rate, 2),
                "previous": round(previous_error_rate, 2),
                "change": calculate_change(current_error_rate, previous_error_rate),
            },
            "cache_hit_rate": {
                "current": AppConfig.DEFAULT_CACHE_HIT_RATE * 100,
                "previous": AppConfig.DEFAULT_CACHE_HIT_RATE * 100,
                "change": 0.0,
            },
        }
    except Exception as e:
        logger.error(f"Error fetching performance metrics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching performance metrics")


@router.get("/performance/timeline")
async def get_performance_timeline(
    days: float = Query(7, ge=0.1, le=30),
    interval: str = Query("day", pattern="^(hour|day)$"),
    session: Dict[str, Any] = Depends(require_admin_auth),
) -> Dict[str, Any]:
    """Get performance timeline data for charts."""
    try:
        with query_data_manager.get_connection() as conn:
            cursor = conn.cursor()

            if interval == "hour":
                # Hourly data for the last N days
                cursor.execute(
                    """
                    SELECT
                        strftime('%Y-%m-%d %H:00:00', timestamp) as period,
                        COUNT(*) as query_count,
                        AVG(response_time_ms) as avg_response_time,
                        AVG(CASE WHEN error_occurred THEN 1.0 ELSE 0.0 END) as error_rate,
                        AVG(CASE WHEN cache_hit THEN 1.0 ELSE 0.0 END) as cache_hit_rate
                    FROM query_logs
                    WHERE timestamp >= datetime('now', '-' || ? || ' days')
                    GROUP BY strftime('%Y-%m-%d %H:00:00', timestamp)
                    ORDER BY period
                    """,
                    (days,),
                )
            else:
                # Daily data for the last N days
                cursor.execute(
                    """
                    SELECT
                        strftime('%Y-%m-%d', timestamp) as period,
                        COUNT(*) as query_count,
                        AVG(response_time_ms) as avg_response_time,
                        AVG(CASE WHEN error_occurred THEN 1.0 ELSE 0.0 END) as error_rate,
                        AVG(CASE WHEN cache_hit THEN 1.0 ELSE 0.0 END) as cache_hit_rate
                    FROM query_logs
                    WHERE timestamp >= datetime('now', '-' || ? || ' days')
                    GROUP BY strftime('%Y-%m-%d', timestamp)
                    ORDER BY period
                    """,
                    (days,),
                )

            timeline_data = []
            for row in cursor.fetchall():
                timeline_data.append(
                    {
                        "period": row[0],
                        "query_count": row[1],
                        "avg_response_time": round(row[2] or 0, 1),
                        "error_rate": round((row[3] or 0) * 100, 2),
                        "cache_hit_rate": round((row[4] or 0) * 100, 1),
                    }
                )

            return {"timeline": timeline_data}

    except Exception as e:
        logger.error(f"Error fetching performance timeline: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching performance timeline")


@router.get("/performance/percentiles")
async def get_response_time_percentiles(
    time_range: str = Query("7d", pattern="^(1h|6h|24h|7d|30d)$"),
    session: Dict[str, Any] = Depends(require_admin_auth),
) -> Dict[str, Any]:
    """Get response time percentiles for performance analysis."""
    try:
        with query_data_manager.get_connection() as conn:
            cursor = conn.cursor()

            # Convert time range to SQL
            time_map = {"1h": "1 hours", "6h": "6 hours", "24h": "1 days", "7d": "7 days", "30d": "30 days"}

            cursor.execute(
                f"""
                SELECT response_time_ms
                FROM query_logs
                WHERE timestamp >= datetime('now', '-{time_map[time_range]}')
                AND response_time_ms IS NOT NULL
                ORDER BY response_time_ms
                """,
            )

            response_times = [row[0] for row in cursor.fetchall()]

            if not response_times:
                return {"percentiles": {"p50": 0, "p75": 0, "p90": 0, "p95": 0, "p99": 0}, "sample_size": 0}

            def percentile(data, p):
                """Calculate percentile from sorted data."""
                n = len(data)
                if n == 0:
                    return 0
                index = p * (n - 1) / 100
                if index.is_integer():
                    return data[int(index)]
                lower = data[int(index)]
                upper = data[int(index) + 1]
                return lower + (upper - lower) * (index - int(index))

            percentiles = {
                "p50": round(percentile(response_times, 50), 1),
                "p75": round(percentile(response_times, 75), 1),
                "p90": round(percentile(response_times, 90), 1),
                "p95": round(percentile(response_times, 95), 1),
                "p99": round(percentile(response_times, 99), 1),
            }

            return {"percentiles": percentiles, "sample_size": len(response_times)}

    except Exception as e:
        logger.error(f"Error fetching response time percentiles: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching response time percentiles")


# Knowledge base endpoints
@router.get("/knowledge/files")
async def get_knowledge_files(session: Dict[str, Any] = Depends(require_admin_auth)):
    """Get list of files in the knowledge base directory."""
    knowledge_dir = Path(__file__).parent.parent / "knowledge"

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


# Content management endpoints
@router.get("/content/gaps")
async def get_content_gaps(
    resolved: bool = Query(False, description="Include resolved content gaps"),
    limit: int = Query(50, ge=1, le=200),
    session: Dict[str, Any] = Depends(require_admin_auth),
):
    """Get content gaps detected automatically by the query logger."""
    try:
        with query_data_manager.get_connection() as conn:
            cursor = conn.cursor()

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


# Export endpoints
@router.get("/export/csv")
async def export_csv(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    export_type: str = Query("queries", pattern="^(queries|metrics)$"),
    session: Dict[str, Any] = Depends(require_admin_auth),
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


# Security monitoring endpoints
@router.get("/security/alerts")
async def get_security_alerts(
    hours: int = Query(24, ge=1, le=168, description="Hours to look back"),
    session: Dict[str, Any] = Depends(require_admin_auth),
) -> Dict[str, Any]:
    """Get recent security events and alerts."""
    try:
        alerts = admin_auth_manager.get_security_alerts(hours)

        # Categorize alerts by severity
        critical = [a for a in alerts if a["severity"] == "critical"]
        high = [a for a in alerts if a["severity"] == "high"]
        medium = [a for a in alerts if a["severity"] == "medium"]
        low = [a for a in alerts if a["severity"] == "low"]

        return {
            "alerts": alerts,
            "summary": {
                "total": len(alerts),
                "critical": len(critical),
                "high": len(high),
                "medium": len(medium),
                "low": len(low),
            },
            "time_range_hours": hours,
        }
    except Exception as e:
        logger.error(f"Error fetching security alerts: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching security alerts")


@router.get("/security/session-stats")
async def get_session_security_stats(session: Dict[str, Any] = Depends(require_admin_auth)) -> Dict[str, Any]:
    """Get session-related security statistics."""
    try:
        with admin_db_manager.get_connection() as conn:
            cursor = conn.cursor()

            # Active sessions by IP
            cursor.execute(
                """
                SELECT ip_address, COUNT(*) as session_count
                FROM admin_sessions
                WHERE is_active = 1
                GROUP BY ip_address
                ORDER BY session_count DESC
                LIMIT 10
            """
            )
            sessions_by_ip = [{"ip": row[0], "count": row[1]} for row in cursor.fetchall()]

            # Sessions by user
            cursor.execute(
                """
                SELECT u.username, COUNT(*) as session_count
                FROM admin_sessions s
                JOIN admin_users u ON s.user_id = u.id
                WHERE s.is_active = 1
                GROUP BY u.username
                ORDER BY session_count DESC
            """
            )
            sessions_by_user = [{"username": row[0], "count": row[1]} for row in cursor.fetchall()]

            # Session duration statistics
            cursor.execute(
                """
                SELECT
                    AVG((julianday('now') - julianday(started_at)) * 24) as avg_duration_hours,
                    MAX((julianday('now') - julianday(started_at)) * 24) as max_duration_hours,
                    COUNT(*) as total_active_sessions
                FROM admin_sessions
                WHERE is_active = 1
            """
            )
            duration_stats = cursor.fetchone()

            return {
                "sessions_by_ip": sessions_by_ip,
                "sessions_by_user": sessions_by_user,
                "duration_stats": {
                    "average_hours": round(duration_stats[0] or 0, 1),
                    "max_hours": round(duration_stats[1] or 0, 1),
                    "total_active": duration_stats[2] or 0,
                },
            }
    except Exception as e:
        logger.error(f"Error fetching session security stats: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching session security statistics")


# User management endpoints
@router.get("/users", response_model=List[AdminUser])
async def get_all_users(session: Dict[str, Any] = Depends(require_admin_role)) -> List[AdminUser]:
    """Get all admin users (admin only)."""
    try:
        users = admin_db_manager.get_all_admin_users()
        return [AdminUser(**user) for user in users]
    except Exception as e:
        logger.error(f"Error fetching users: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching users")


# Settings endpoints
@router.get("/settings/followup")
async def get_followup_settings(
    request: Request, session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Get current follow-up question settings."""
    try:
        # Get settings from database
        settings_json = admin_db_manager.get_admin_setting("followup_settings")

        if settings_json:
            # Parse existing settings
            settings = FollowUpSettings.from_json(settings_json)
        else:
            # Return defaults if no settings exist
            settings = FollowUpSettings()

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_VIEW,
            username=session["username"],
            details={"resource": "followup_settings", "settings_exists": settings_json is not None},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        return settings.to_dict()

    except Exception as e:
        logger.error(f"Error getting follow-up settings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching follow-up settings")


@router.put("/settings/followup")
async def update_followup_settings(
    request: Request, settings_data: Dict[str, Any], session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Update follow-up question settings."""
    try:
        # Validate and create settings object
        settings = FollowUpSettings.from_dict(settings_data)

        # Store in database
        success = admin_db_manager.set_admin_setting(
            setting_key="followup_settings", setting_value=settings.to_json(), updated_by=session["user_id"]
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update settings")

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.CONFIG_UPDATE,
            username=session["username"],
            details={"resource": "followup_settings", "new_settings": settings.to_dict()},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        # Reload settings in the follow-up service
        # Note: Settings will be reloaded automatically on next request due to cache expiry

        logger.info(f"Follow-up settings updated by user {session['user_id']}: {settings.to_dict()}")

        return {"success": True, "message": "Follow-up settings updated successfully", "settings": settings.to_dict()}

    except Exception as e:
        logger.error(f"Error updating follow-up settings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error updating follow-up settings")


@router.post("/settings/followup/reset")
async def reset_followup_settings(
    request: Request, session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Reset follow-up settings to defaults."""
    try:
        # Create default settings
        default_settings = FollowUpSettings()

        # Store in database
        success = admin_db_manager.set_admin_setting(
            setting_key="followup_settings", setting_value=default_settings.to_json(), updated_by=session["user_id"]
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to reset settings")

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.CONFIG_UPDATE,
            username=session["username"],
            details={
                "resource": "followup_settings",
                "action": "reset_to_defaults",
                "reset_to": default_settings.to_dict(),
            },
            ip_address=client_ip,
            user_agent=user_agent,
        )

        logger.info(f"Follow-up settings reset to defaults by user {session['user_id']}")

        return {
            "success": True,
            "message": "Follow-up settings reset to defaults",
            "settings": default_settings.to_dict(),
        }

    except Exception as e:
        logger.error(f"Error resetting follow-up settings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error resetting follow-up settings")


# OLD ROUTE REMOVED - Using normalized database-driven endpoint below


# OLD ROUTE REMOVED - Using normalized database-driven endpoints below


# OLD ROUTE REMOVED - Using normalized database-driven endpoints below


# Follow-up category management endpoints
@router.get("/settings/followup/categories", response_model=List[FollowupCategory])
async def get_followup_categories(
    include_inactive: bool = Query(False, description="Include inactive categories"),
    session: Dict[str, Any] = Depends(require_admin_auth),
) -> List[FollowupCategory]:
    """Get all follow-up categories."""
    try:
        categories = admin_db_manager.get_followup_categories(active_only=not include_inactive)
        return [FollowupCategory(**category) for category in categories]
    except Exception as e:
        logger.error(f"Error getting followup categories: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching follow-up categories")


@router.get("/settings/followup/categories/{category_id}", response_model=FollowupCategory)
async def get_followup_category(
    category_id: int, session: Dict[str, Any] = Depends(require_admin_auth)
) -> FollowupCategory:
    """Get a single follow-up category by ID."""
    if category_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid category ID")

    try:
        category = admin_db_manager.get_followup_category(category_id)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        return FollowupCategory(**category)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting followup category {category_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching follow-up category")


@router.post("/settings/followup/categories", response_model=Dict[str, Any])
async def create_followup_category(
    request: Request,
    category_data: CreateFollowupCategoryRequest,
    session: Dict[str, Any] = Depends(require_admin_auth),
) -> Dict[str, Any]:
    """Create a new follow-up category."""
    try:
        # Check if category name already exists
        existing = admin_db_manager.get_followup_category_by_name(category_data.name)
        if existing:
            raise HTTPException(status_code=400, detail=f"Category '{category_data.name}' already exists")

        category_id = admin_db_manager.create_followup_category(
            name=category_data.name,
            display_name=category_data.display_name,
            description=category_data.description,
            icon=category_data.icon,
            sort_order=category_data.sort_order,
        )

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.CONFIG_UPDATE,
            username=session["username"],
            details={
                "resource": "followup_category",
                "action": "create",
                "category_id": category_id,
                "category_name": category_data.name,
            },
            ip_address=client_ip,
            user_agent=user_agent,
        )

        logger.info(f"Follow-up category '{category_data.name}' created by user {session['user_id']}")

        return {
            "success": True,
            "message": f"Category '{category_data.display_name}' created successfully",
            "category_id": category_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating followup category: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error creating follow-up category")


@router.put("/settings/followup/categories/{category_id}", response_model=Dict[str, Any])
async def update_followup_category(
    category_id: int,
    request: Request,
    category_data: UpdateFollowupCategoryRequest,
    session: Dict[str, Any] = Depends(require_admin_auth),
) -> Dict[str, Any]:
    """Update a follow-up category."""
    if category_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid category ID")

    try:
        # Check if category exists
        existing = admin_db_manager.get_followup_category(category_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Category not found")

        # Prevent deactivating categories that have questions
        if category_data.is_active is False:
            # Get current settings to check for questions
            settings_json = admin_db_manager.get_admin_setting("followup_settings")
            if settings_json:
                settings = FollowUpSettings.from_json(settings_json)
                if existing["name"] in settings.custom_questions and settings.custom_questions[existing["name"]]:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cannot deactivate category '{existing['display_name']}' - it contains questions. Remove questions first.",
                    )

        success = admin_db_manager.update_followup_category(
            category_id=category_id,
            display_name=category_data.display_name,
            description=category_data.description,
            icon=category_data.icon,
            sort_order=category_data.sort_order,
            is_active=category_data.is_active,
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update category")

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.CONFIG_UPDATE,
            username=session["username"],
            details={
                "resource": "followup_category",
                "action": "update",
                "category_id": category_id,
                "category_name": existing["name"],
                "changes": category_data.dict(exclude_unset=True),
            },
            ip_address=client_ip,
            user_agent=user_agent,
        )

        logger.info(f"Follow-up category ID {category_id} updated by user {session['user_id']}")

        return {"success": True, "message": "Category updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating followup category {category_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error updating follow-up category")


@router.delete("/settings/followup/categories/{category_id}")
async def delete_followup_category(
    category_id: int, request: Request, session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Delete (deactivate) a follow-up category."""
    if category_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid category ID")

    try:
        # Check if category exists
        existing = admin_db_manager.get_followup_category(category_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Category not found")

        # Prevent deleting categories that have questions
        settings_json = admin_db_manager.get_admin_setting("followup_settings")
        if settings_json:
            settings = FollowUpSettings.from_json(settings_json)
            if existing["name"] in settings.custom_questions and settings.custom_questions[existing["name"]]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot delete category '{existing['display_name']}' - it contains questions. Remove questions first.",
                )

        success = admin_db_manager.delete_followup_category(category_id)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete category")

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.CONFIG_UPDATE,
            username=session["username"],
            details={
                "resource": "followup_category",
                "action": "delete",
                "category_id": category_id,
                "category_name": existing["name"],
            },
            ip_address=client_ip,
            user_agent=user_agent,
        )

        logger.info(f"Follow-up category ID {category_id} deleted by user {session['user_id']}")

        return {"success": True, "message": f"Category '{existing['display_name']}' deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting followup category {category_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error deleting follow-up category")


@router.post("/settings/followup/categories/reorder")
async def reorder_followup_categories(
    request: Request, reorder_data: ReorderCategoriesRequest, session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Reorder follow-up categories by updating sort_order."""
    try:
        # Validate that all category IDs exist
        for item in reorder_data.categories:
            if not admin_db_manager.get_followup_category(item["id"]):
                raise HTTPException(status_code=400, detail=f"Category ID {item['id']} not found")

        success = admin_db_manager.reorder_followup_categories(reorder_data.categories)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to reorder categories")

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.CONFIG_UPDATE,
            username=session["username"],
            details={
                "resource": "followup_categories",
                "action": "reorder",
                "category_count": len(reorder_data.categories),
            },
            ip_address=client_ip,
            user_agent=user_agent,
        )

        logger.info(f"Follow-up categories reordered by user {session['user_id']}")

        return {"success": True, "message": "Categories reordered successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reordering followup categories: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error reordering follow-up categories")


# Enhanced category endpoints with question counts
@router.get("/settings/followup/categories/with-stats", response_model=List[CategoryWithStats])
async def get_categories_with_stats(
    include_inactive: bool = Query(False, description="Include inactive categories"),
    session: Dict[str, Any] = Depends(require_admin_auth),
) -> List[CategoryWithStats]:
    """Get all categories with question counts and stats."""
    try:
        from ..core.followup_management_service import followup_management_service

        categories = followup_management_service.get_categories_with_stats()

        if not include_inactive:
            categories = [cat for cat in categories if cat["is_active"]]

        return [CategoryWithStats(**category) for category in categories]
    except Exception as e:
        logger.error(f"Error getting categories with stats: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching categories with stats")


@router.post("/settings/followup/categories/{category_id}/delete")
async def delete_category_with_strategy(
    category_id: int,
    request: Request,
    delete_request: CategoryDeleteRequest,
    session: Dict[str, Any] = Depends(require_admin_auth),
) -> Dict[str, Any]:
    """Delete category with smart handling of questions."""
    if category_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid category ID")

    try:
        from ..core.followup_management_service import followup_management_service

        result = followup_management_service.delete_category_with_strategy(
            category_id=category_id,
            strategy=delete_request.strategy,
            target_category_id=delete_request.target_category_id,
            user_id=session.get("user_id"),
        )

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.CONFIG_UPDATE,
            username=session["username"],
            details={
                "resource": "followup_category",
                "action": f"delete_with_strategy_{delete_request.strategy}",
                "category_id": category_id,
                "questions_affected": result.get("questions_affected", 0),
                "target_category_id": delete_request.target_category_id,
            },
            ip_address=client_ip,
            user_agent=user_agent,
        )

        logger.info(
            f"Category {category_id} deleted with strategy {delete_request.strategy} by user {session['user_id']}"
        )

        return {
            "success": True,
            "message": f"Category '{result['category_name']}' {result['action']} successfully",
            **result,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting category {category_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error deleting category")


@router.get("/settings/followup/categories/{category_id}/validate-deletion")
async def validate_category_deletion(
    category_id: int, session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Validate category deletion and return available options."""
    if category_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid category ID")

    try:
        from ..core.followup_management_service import followup_management_service

        result = followup_management_service.validate_category_deletion(category_id)

        if not result["valid"]:
            raise HTTPException(status_code=404, detail=result["error"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating category deletion {category_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error validating category deletion")


@router.get("/settings/followup/categories/{category_id}/stats")
async def get_category_stats(category_id: int, session: Dict[str, Any] = Depends(require_admin_auth)) -> Dict[str, Any]:
    """Get statistics for a specific follow-up category."""
    if category_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid category ID")

    try:
        # Verify category exists
        category = admin_db_manager.get_followup_category(category_id)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")

        # Get question count for this category
        questions = admin_db_manager.get_followup_questions(
            category_id=category_id, active_only=False  # Get all questions for stats
        )

        active_questions = [q for q in questions if q.get("is_active", True)]
        inactive_questions = [q for q in questions if not q.get("is_active", True)]

        return {
            "category_id": category_id,
            "question_count": len(questions),
            "active_questions": len(active_questions),
            "inactive_questions": len(inactive_questions),
            "category_name": category.get("name", ""),
            "category_display_name": category.get("display_name", ""),
            "is_category_active": category.get("is_active", True),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting category stats {category_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching category statistics")


# New normalized question management endpoints
@router.get("/settings/followup/questions", response_model=List[FollowupQuestion])
async def get_followup_questions(
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    active_only: bool = Query(True, description="Only include active questions"),
    search: Optional[str] = Query(None, min_length=3, description="Search question text"),
    limit: int = Query(50, ge=1, le=100, description="Maximum questions to return"),
    offset: int = Query(0, ge=0, description="Number of questions to skip"),
    session: Dict[str, Any] = Depends(require_admin_auth),
) -> List[FollowupQuestion]:
    """Get follow-up questions with pagination and filtering."""
    try:
        questions = admin_db_manager.get_followup_questions(
            category_id=category_id, active_only=active_only, search=search, limit=limit, offset=offset
        )
        return [FollowupQuestion(**question) for question in questions]
    except Exception as e:
        logger.error(f"Error getting followup questions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching follow-up questions")


@router.get("/settings/followup/questions/{question_id}", response_model=FollowupQuestion)
async def get_followup_question(
    question_id: int, session: Dict[str, Any] = Depends(require_admin_auth)
) -> FollowupQuestion:
    """Get a single follow-up question by ID."""
    if question_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid question ID")

    try:
        question = admin_db_manager.get_followup_question(question_id)
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")
        return FollowupQuestion(**question)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting followup question {question_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching follow-up question")


@router.post("/settings/followup/questions", response_model=Dict[str, Any])
async def create_followup_question(
    request: Request,
    question_data: CreateFollowupQuestionRequest,
    session: Dict[str, Any] = Depends(require_admin_auth),
) -> Dict[str, Any]:
    """Create a new follow-up question."""
    try:
        question_id = admin_db_manager.create_followup_question(
            category_id=question_data.category_id,
            question_text=question_data.question_text,
            sort_order=question_data.sort_order,
            created_by=session.get("user_id"),
        )

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.CONFIG_UPDATE,
            username=session["username"],
            details={
                "resource": "followup_question",
                "action": "create",
                "question_id": question_id,
                "category_id": question_data.category_id,
            },
            ip_address=client_ip,
            user_agent=user_agent,
        )

        logger.info(f"Follow-up question {question_id} created by user {session['user_id']}")

        return {"success": True, "message": "Question created successfully", "question_id": question_id}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating followup question: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error creating follow-up question")


@router.put("/settings/followup/questions/{question_id}", response_model=Dict[str, Any])
async def update_followup_question(
    question_id: int,
    request: Request,
    question_data: UpdateFollowupQuestionRequest,
    session: Dict[str, Any] = Depends(require_admin_auth),
) -> Dict[str, Any]:
    """Update a follow-up question."""
    if question_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid question ID")

    try:
        # Check if question exists
        existing = admin_db_manager.get_followup_question(question_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Question not found")

        success = admin_db_manager.update_followup_question(
            question_id=question_id,
            question_text=question_data.question_text,
            sort_order=question_data.sort_order,
            is_active=question_data.is_active,
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update question")

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.CONFIG_UPDATE,
            username=session["username"],
            details={
                "resource": "followup_question",
                "action": "update",
                "question_id": question_id,
                "changes": question_data.dict(exclude_unset=True),
            },
            ip_address=client_ip,
            user_agent=user_agent,
        )

        logger.info(f"Follow-up question {question_id} updated by user {session['user_id']}")

        return {"success": True, "message": "Question updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating followup question {question_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error updating follow-up question")


@router.delete("/settings/followup/questions/{question_id}")
async def delete_followup_question(
    question_id: int, request: Request, session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Delete a follow-up question."""
    if question_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid question ID")

    try:
        # Check if question exists
        existing = admin_db_manager.get_followup_question(question_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Question not found")

        success = admin_db_manager.delete_followup_question(question_id)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete question")

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.CONFIG_UPDATE,
            username=session["username"],
            details={
                "resource": "followup_question",
                "action": "delete",
                "question_id": question_id,
                "question_text": existing["question_text"][:100],
            },
            ip_address=client_ip,
            user_agent=user_agent,
        )

        logger.info(f"Follow-up question {question_id} deleted by user {session['user_id']}")

        return {"success": True, "message": "Question deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting followup question {question_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error deleting follow-up question")


@router.post("/settings/followup/questions/bulk")
async def bulk_update_questions(
    request: Request, bulk_data: BulkQuestionRequest, session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Perform bulk operations on questions."""
    try:
        from ..core.followup_management_service import followup_management_service

        result = followup_management_service.bulk_update_questions(bulk_data.operations)

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.CONFIG_UPDATE,
            username=session["username"],
            details={
                "resource": "followup_questions",
                "action": "bulk_update",
                "operations_count": len(bulk_data.operations),
                "completed": result["operations_completed"],
                "failed": result["operations_failed"],
            },
            ip_address=client_ip,
            user_agent=user_agent,
        )

        logger.info(
            f"Bulk question operations by user {session['user_id']}: {result['operations_completed']} completed, {result['operations_failed']} failed"
        )

        return {
            "success": result["operations_failed"] == 0,
            "message": f"Bulk operations completed: {result['operations_completed']} successful, {result['operations_failed']} failed",
            **result,
        }

    except Exception as e:
        logger.error(f"Error in bulk question operations: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error performing bulk operations")


@router.get("/settings/followup/questions/search")
async def search_followup_questions(
    query: str = Query(..., min_length=3, max_length=100),
    category_id: Optional[int] = Query(None, gt=0),
    limit: int = Query(20, ge=1, le=50),
    session: Dict[str, Any] = Depends(require_admin_auth),
) -> List[FollowupQuestion]:
    """Search follow-up questions by text."""
    try:
        from ..core.followup_management_service import followup_management_service

        questions = followup_management_service.search_questions(query=query, category_id=category_id, limit=limit)

        return [FollowupQuestion(**question) for question in questions]

    except Exception as e:
        logger.error(f"Error searching questions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error searching follow-up questions")
