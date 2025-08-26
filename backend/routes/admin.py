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
from ..core.query_data_manager import query_data_manager
from ..models.admin_models import (
    AdminUser,
    ChangePasswordRequest,
    CreateUserRequest,
    FeedbackUpdate,
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

        auth_result = admin_auth_manager.authenticate_user(
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
            httponly=is_production,  # Allow JS access in development
            secure=is_production,  # Only secure in production
            samesite="lax",  # Lax is better for same-domain dev
        )

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

        # Clear session cookie
        response.delete_cookie(key="admin_session")

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
        if admin_auth_manager._is_rate_limited(client_ip):
            logger.warning(f"Rate limited password change attempt from {client_ip} for user {session['username']}")
            raise HTTPException(status_code=429, detail="Too many password change attempts. Please try again later.")

        # Get the current user
        user = admin_db_manager.get_admin_user(session["username"])
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Verify current password
        if not admin_auth_manager.verify_password(password_data.current_password, user["password_hash"]):
            # Record failed password verification attempt
            admin_auth_manager._record_failed_attempt(client_ip)
            logger.warning(f"Invalid current password attempt for user: {session['username']} from IP: {client_ip}")
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
        new_password_hash = admin_auth_manager.hash_password(password_data.new_password)
        success = admin_db_manager.update_user_password(user["id"], new_password_hash)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update password")

        # Reset failed attempts on successful password change
        admin_auth_manager._reset_failed_attempts(client_ip)

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
    days: int = Query(7, ge=1, le=90), session: Dict[str, Any] = Depends(require_admin_auth)
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
        current_metrics = query_data_manager.get_performance_metrics(time_range)
        return {
            "response_time": {"current": round(current_metrics.get("avg_response_time", 0) or 0, 1)},
            "throughput": {"current": current_metrics.get("total_queries", 0) or 0},
            "error_rate": {"current": round(current_metrics.get("error_rate", 0) or 0, 2)},
            "cache_hit_rate": {"current": round((current_metrics.get("cache_hit_rate", 0) or 0) * 100, 1)},
        }
    except Exception as e:
        logger.error(f"Error fetching performance metrics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching performance metrics")


@router.get("/performance/timeline")
async def get_performance_timeline(
    days: int = Query(7, ge=1, le=30),
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
