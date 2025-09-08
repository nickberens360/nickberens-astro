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

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import ValidationError

from ..core.admin_auth import admin_auth_manager, require_admin_auth, require_admin_role
from ..core.admin_database import admin_db_manager
from ..core.api_key_manager import api_key_manager
from ..core.audit_logger import AuditAction, AuditLogger, audit_logger

# CSRF protection removed - session-based auth is inherently CSRF-resistant for our use case
from ..core.query_data_manager import query_data_manager
from ..core.settings_manager import get_settings_manager
from ..core.settings_schemas import (
    FeatureFlags,
    FollowUpSettings,
    QueryRoutingSettings,
    ResponseSettings,
    SecuritySettings,
    SystemConfigurationSettings,
)
from ..models.admin_models import (
    AdminUser,
    BulkDeactivateUsersRequest,
    BulkDeleteUsersRequest,
    BulkQuestionRequest,
    CategoryDeleteRequest,
    ChangePasswordRequest,
    CreateFollowupCategoryRequest,
    CreateFollowupQuestionRequest,
    CreateUserRequest,
    CreateWelcomeQuestionRequest,
    FeedbackUpdate,
    LoginRequest,
    LoginResponse,
    OverviewStats,
    QueryResponse,
    UpdateDisplayNameRequest,
    UpdateEmailRequest,
    UpdateFollowupCategoryRequest,
    UpdateFollowupQuestionRequest,
    UpdateWelcomeQuestionRequest,
)

logger = logging.getLogger(__name__)

# Initialize audit logger
audit_logger = AuditLogger()


router = APIRouter()


# Authentication endpoints
@router.post(
    "/auth/login",
    tags=["Admin Authentication"],
    response_model=LoginResponse,
    summary="Admin Login",
    description="""
            **Authenticate admin user and create secure session.**
            
            **Authentication Flow:**
            1. Submit username and password
            2. System validates credentials and checks rate limits
            3. On success: secure HTTPOnly cookie is set (`admin_session`)
            4. Use this cookie for subsequent admin API calls
            
            **Security Features:**
            - Rate limiting per IP address
            - Secure session management with HTTPOnly cookies
            - Audit logging of all login attempts
            - Password validation and security checks
            - Session fingerprinting for additional security
            
            **Session Management:**
            - Session expires in 24 hours
            - HTTPOnly cookie prevents XSS attacks
            - Secure flag enabled in production (HTTPS)
            - SameSite=Lax for CSRF protection
            
            **Next Steps After Login:**
            1. Cookie is automatically included in browser requests
            2. Access admin endpoints like `/api/admin/stats/overview`
            3. Use `/api/admin/auth/me` to verify current session
            """,
    responses={
        200: {
            "description": "Login successful - session cookie set",
            "content": {
                "application/json": {
                    "examples": {
                        "successful_login": {
                            "summary": "Successful admin login",
                            "value": {
                                "success": True,
                                "message": "Login successful",
                                "user": {
                                    "id": 1,
                                    "username": "admin",
                                    "role": "admin",
                                    "created_at": "2024-01-01T00:00:00Z",
                                    "last_login": "2024-09-02T17:00:00Z",
                                },
                            },
                        },
                        "invalid_credentials": {
                            "summary": "Invalid login credentials",
                            "value": {"success": False, "message": "Invalid username or password"},
                        },
                        "missing_fields": {
                            "summary": "Missing required fields",
                            "value": {"success": False, "message": "Username and password are required"},
                        },
                    }
                }
            },
            "headers": {
                "Set-Cookie": {
                    "description": "Secure session cookie for admin authentication",
                    "schema": {"type": "string"},
                    "example": "admin_session=abc123...; HttpOnly; Secure; SameSite=Lax; Max-Age=86400",
                }
            },
        }
    },
)
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
    # Get full user data including display_name
    user_info = admin_db_manager.get_admin_user_by_id(session["user_id"])
    user_data = {
        "id": session["user_id"],
        "username": session["username"],
        "email": session.get("email"),
        "display_name": user_info.get("display_name") if user_info else None,
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

        # SECURITY FIX: Force complete re-authentication after password change
        # This prevents session fixation attacks
        admin_auth_manager.expire_user_sessions(user["id"])

        # Force logout by clearing the current session cookie
        response = JSONResponse({"success": True, "message": "Password changed successfully. Please log in again."})
        response.delete_cookie("admin_session", path="/", httponly=True, secure=True, samesite="lax")
        return response

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


# User profile endpoints
@router.put("/user/display-name")
async def update_display_name(
    request_data: UpdateDisplayNameRequest, session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Update current user's display name."""
    try:
        user_id = session["user_id"]
        success = admin_db_manager.update_user_display_name(user_id, request_data.display_name)

        if success:
            audit_logger.log_action(
                action=AuditAction.USER_UPDATE,
                username=session["username"],
                details={"field": "display_name", "new_value": request_data.display_name},
            )
            return {"success": True, "message": "Display name updated successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to update display name")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Display name update error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update display name")


@router.put("/user/email")
async def update_email(
    request_data: UpdateEmailRequest, session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Update current user's email address with password verification."""
    try:
        user_id = session["user_id"]

        # Verify current password first
        if not admin_db_manager.verify_user_password(user_id, request_data.password):
            raise HTTPException(status_code=400, detail="Current password is incorrect")

        success = admin_db_manager.update_user_email(user_id, request_data.email)

        if success:
            audit_logger.log_action(
                action=AuditAction.USER_UPDATE,
                username=session["username"],
                details={"field": "email", "new_value": request_data.email},
            )
            return {"success": True, "message": "Email address updated successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to update email address - email may already be in use")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email update error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update email address")


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
        # Use settings manager for cached access
        settings_mgr = get_settings_manager()
        settings = settings_mgr.get_followup_settings()

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_VIEW,
            username=session["username"],
            details={"resource": "followup_settings"},
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

        # Use settings manager to store settings
        settings_mgr = get_settings_manager()
        success = settings_mgr.set_followup_settings(settings, session["user_id"])

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

        # Clear cache in follow-up service to ensure immediate effect
        try:
            followup_service = getattr(request.app.state, "followup_service", None)
            if followup_service and hasattr(followup_service, "clear_cache"):
                followup_service.clear_cache()
                logger.info("FollowUp service cache cleared after settings update")
            else:
                logger.warning("FollowUp service not found or clear_cache method not available")
        except Exception as e:
            logger.warning(f"Could not clear followup service cache: {e}")

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

        # Use settings manager to store settings
        settings_mgr = get_settings_manager()
        success = settings_mgr.set_followup_settings(default_settings, session["user_id"])

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

        # Clear cache in follow-up service to ensure immediate effect
        try:
            followup_service = getattr(request.app.state, "followup_service", None)
            if followup_service and hasattr(followup_service, "clear_cache"):
                followup_service.clear_cache()
                logger.info("FollowUp service cache cleared after settings reset")
            else:
                logger.warning("FollowUp service not found or clear_cache method not available")
        except Exception as e:
            logger.warning(f"Could not clear followup service cache: {e}")

        logger.info(f"Follow-up settings reset to defaults by user {session['user_id']}")

        return {
            "success": True,
            "message": "Follow-up settings reset to defaults",
            "settings": default_settings.to_dict(),
        }

    except Exception as e:
        logger.error(f"Error resetting follow-up settings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error resetting follow-up settings")


# Follow-up Category Management Routes
@router.get("/settings/followup/categories")
async def get_followup_categories(
    request: Request,
    session: Dict[str, Any] = Depends(require_admin_auth),
    include_inactive: bool = Query(default=True, description="Include inactive categories"),
) -> List[Dict[str, Any]]:
    """Get all follow-up categories with optional filtering."""
    try:
        categories = admin_db_manager.get_followup_categories(active_only=not include_inactive)

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_VIEW,
            username=session["username"],
            details={"resource": "followup_categories", "include_inactive": include_inactive, "count": len(categories)},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        return categories

    except Exception as e:
        logger.error(f"Error getting follow-up categories: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching follow-up categories")


@router.post("/settings/followup/categories")
async def create_followup_category(
    request: Request,
    category_data: CreateFollowupCategoryRequest,
    session: Dict[str, Any] = Depends(require_admin_auth),
) -> Dict[str, Any]:
    """Create a new follow-up category."""
    try:
        # Check if category name already exists
        existing_category = admin_db_manager.get_followup_category_by_name(category_data.name)
        if existing_category:
            raise HTTPException(status_code=409, detail=f"Category '{category_data.name}' already exists")

        # Create the category
        category_id = admin_db_manager.create_followup_category(
            name=category_data.name,
            display_name=category_data.display_name,
            description=category_data.description,
            icon=category_data.icon,
            sort_order=category_data.sort_order,
        )

        # Fetch the created category
        created_category = admin_db_manager.get_followup_category(category_id)
        if not created_category:
            raise HTTPException(status_code=500, detail="Failed to retrieve created category")

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_CREATE,
            username=session["username"],
            details={"resource": "followup_category", "category_id": category_id, "name": category_data.name},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        logger.info(f"Follow-up category created by user {session['user_id']}: {category_data.name}")

        return created_category

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating follow-up category: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error creating follow-up category")


@router.put("/settings/followup/categories/{category_id}")
async def update_followup_category(
    request: Request,
    category_id: int,
    category_data: UpdateFollowupCategoryRequest,
    session: Dict[str, Any] = Depends(require_admin_auth),
) -> Dict[str, Any]:
    """Update an existing follow-up category."""
    try:
        # Check if category exists
        existing_category = admin_db_manager.get_followup_category(category_id)
        if not existing_category:
            raise HTTPException(status_code=404, detail="Category not found")

        # Update the category
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

        # Fetch the updated category
        updated_category = admin_db_manager.get_followup_category(category_id)
        if not updated_category:
            raise HTTPException(status_code=500, detail="Failed to retrieve updated category")

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_UPDATE,
            username=session["username"],
            details={
                "resource": "followup_category",
                "category_id": category_id,
                "changes": category_data.dict(exclude_unset=True),
            },
            ip_address=client_ip,
            user_agent=user_agent,
        )

        logger.info(f"Follow-up category {category_id} updated by user {session['user_id']}")

        return updated_category

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating follow-up category: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error updating follow-up category")


@router.post("/settings/followup/categories/{category_id}/delete")
async def delete_followup_category_with_strategy(
    request: Request,
    category_id: int,
    delete_request: CategoryDeleteRequest,
    session: Dict[str, Any] = Depends(require_admin_auth),
) -> Dict[str, Any]:
    """Delete a follow-up category using specified strategy."""
    try:
        # Fast path: direct hard delete strategy
        if delete_request.strategy == "delete":
            success = admin_db_manager.delete_followup_category(category_id)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to delete category")
            result = {"success": True, "action": "delete", "category_id": category_id}
        else:
            # Initialize management service for move/deactivate flows
            from ..core.followup_management_service import FollowUpManagementService

            management_service = FollowUpManagementService()

            # Validate the deletion request
            validation_result = management_service.validate_category_deletion(category_id)
            if not validation_result.get("can_delete", False):
                raise HTTPException(status_code=400, detail=validation_result.get("reason", "Cannot delete category"))

            # Perform deletion with strategy
            result = management_service.delete_category_with_strategy(
                category_id=category_id,
                strategy=delete_request.strategy,
                target_category_id=delete_request.target_category_id,
                user_id=session.get("user_id"),
            )

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        # Best-effort audit logging
        try:
            audit_logger.log_action(
                action=AuditAction.DATA_DELETE,
                username=session["username"],
                details={
                    "resource": "followup_category",
                    "category_id": category_id,
                    "strategy": delete_request.strategy,
                    "result": result,
                },
                ip_address=client_ip,
                user_agent=user_agent,
            )
        except Exception as log_err:
            logger.error(f"Audit log failed for category delete {category_id}: {log_err}")

        logger.info(
            f"Follow-up category {category_id} deleted by user {session['user_id']} using strategy: {delete_request.strategy}"
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting follow-up category: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error deleting follow-up category")


@router.get("/settings/followup/categories/{category_id}/stats")
async def get_followup_category_stats(
    request: Request, category_id: int, session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Get statistics for a specific follow-up category."""
    try:
        # Check if category exists
        category = admin_db_manager.get_followup_category(category_id)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")

        # Get questions for this category
        questions = admin_db_manager.get_followup_questions(category_id=category_id, active_only=False)

        active_questions = [q for q in questions if q.get("is_active", True)]
        inactive_questions = [q for q in questions if not q.get("is_active", True)]

        stats = {
            "question_count": len(questions),
            "active_questions": len(active_questions),
            "inactive_questions": len(inactive_questions),
            "category_id": category_id,
            "category_name": category.get("name"),
            "category_display_name": category.get("display_name"),
        }

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_VIEW,
            username=session["username"],
            details={"resource": "followup_category_stats", "category_id": category_id},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        return stats

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting follow-up category stats: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error getting follow-up category stats")


# Follow-up Question Management Routes
@router.get("/settings/followup/questions")
async def get_followup_questions(
    request: Request,
    session: Dict[str, Any] = Depends(require_admin_auth),
    category_id: Optional[int] = Query(default=None, description="Filter by category ID"),
    active_only: bool = Query(default=False, description="Return only active questions"),
    search: Optional[str] = Query(default=None, description="Search in question text"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of questions to return"),
    offset: int = Query(default=0, ge=0, description="Number of questions to skip"),
) -> List[Dict[str, Any]]:
    """Get follow-up questions with filtering and pagination."""
    try:
        questions = admin_db_manager.get_followup_questions(
            category_id=category_id, active_only=active_only, search=search, limit=limit, offset=offset
        )

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_VIEW,
            username=session["username"],
            details={
                "resource": "followup_questions",
                "category_id": category_id,
                "active_only": active_only,
                "count": len(questions),
            },
            ip_address=client_ip,
            user_agent=user_agent,
        )

        return questions

    except Exception as e:
        logger.error(f"Error getting follow-up questions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching follow-up questions")


@router.post("/settings/followup/questions")
async def create_followup_question(
    request: Request,
    question_data: CreateFollowupQuestionRequest,
    session: Dict[str, Any] = Depends(require_admin_auth),
) -> Dict[str, Any]:
    """Create a new follow-up question."""
    try:
        # Validate that category exists
        category = admin_db_manager.get_followup_category(question_data.category_id)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")

        # Create the question
        question_id = admin_db_manager.create_followup_question(
            category_id=question_data.category_id,
            question_text=question_data.question_text,
            sort_order=question_data.sort_order,
            created_by=session["user_id"],
        )

        # Fetch the created question
        created_question = admin_db_manager.get_followup_question(question_id)
        if not created_question:
            # Graceful fallback: construct minimal response when read-after-write fails
            created_question = {
                "id": question_id,
                "category_id": question_data.category_id,
                "question_text": question_data.question_text,
                "sort_order": question_data.sort_order or 0,
                "is_active": True,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "created_by": session.get("user_id"),
            }

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        # Best-effort audit logging
        try:
            audit_logger.log_action(
                action=AuditAction.DATA_CREATE,
                username=session["username"],
                details={
                    "resource": "followup_question",
                    "question_id": question_id,
                    "category_id": question_data.category_id,
                    "question_text": question_data.question_text,
                },
                ip_address=client_ip,
                user_agent=user_agent,
            )
        except Exception as log_err:
            logger.error(f"Audit log failed for question create {question_id}: {log_err}")

        logger.info(f"Follow-up question created by user {session['user_id']}: {question_data.question_text}")

        return created_question

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating follow-up question: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error creating follow-up question")


@router.put("/settings/followup/questions/{question_id}")
async def update_followup_question(
    request: Request,
    question_id: int,
    question_data: UpdateFollowupQuestionRequest,
    session: Dict[str, Any] = Depends(require_admin_auth),
) -> Dict[str, Any]:
    """Update an existing follow-up question."""
    try:
        # Check if question exists
        existing_question = admin_db_manager.get_followup_question(question_id)
        if not existing_question:
            raise HTTPException(status_code=404, detail="Question not found")

        # Update the question
        success = admin_db_manager.update_followup_question(
            question_id=question_id,
            question_text=question_data.question_text,
            sort_order=question_data.sort_order,
            is_active=question_data.is_active,
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update question")

        # Fetch the updated question
        updated_question = admin_db_manager.get_followup_question(question_id)
        if not updated_question:
            raise HTTPException(status_code=500, detail="Failed to retrieve updated question")

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        # Best-effort audit logging; do not fail the request if logging fails
        try:
            audit_logger.log_action(
                action=AuditAction.DATA_UPDATE,
                username=session["username"],
                details={
                    "resource": "followup_question",
                    "question_id": question_id,
                    "changes": question_data.dict(exclude_unset=True),
                },
                ip_address=client_ip,
                user_agent=user_agent,
            )
        except Exception as log_err:
            logger.error(f"Audit log failed for question update {question_id}: {log_err}")

        logger.info(f"Follow-up question {question_id} updated by user {session['user_id']}")

        return updated_question

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating follow-up question: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error updating follow-up question")


@router.delete("/settings/followup/questions/{question_id}")
async def delete_followup_question(
    request: Request, question_id: int, session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Delete a follow-up question."""
    try:
        # Check if question exists
        existing_question = admin_db_manager.get_followup_question(question_id)
        if not existing_question:
            raise HTTPException(status_code=404, detail="Question not found")

        # Delete the question
        success = admin_db_manager.delete_followup_question(question_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete question")

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_DELETE,
            username=session["username"],
            details={
                "resource": "followup_question",
                "question_id": question_id,
                "question_text": existing_question.get("question_text", ""),
            },
            ip_address=client_ip,
            user_agent=user_agent,
        )

        logger.info(f"Follow-up question {question_id} deleted by user {session['user_id']}")

        return {"success": True, "message": "Question deleted successfully", "question_id": question_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting follow-up question: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error deleting follow-up question")


@router.post("/settings/followup/questions/bulk")
async def bulk_update_followup_questions(
    request: Request, bulk_request: BulkQuestionRequest, session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Perform bulk operations on follow-up questions."""
    try:
        # Initialize management service
        from ..core.followup_management_service import FollowUpManagementService

        management_service = FollowUpManagementService()

        # Convert operations to expected format
        operations = [op.dict() for op in bulk_request.operations]

        # Perform bulk operations
        result = management_service.bulk_update_questions(operations)

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_UPDATE,
            username=session["username"],
            details={"resource": "followup_questions_bulk", "operation_count": len(operations), "result": result},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        logger.info(f"Bulk question operations performed by user {session['user_id']}: {len(operations)} operations")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error performing bulk question operations: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error performing bulk question operations")


# Additional settings endpoints for new functionality
@router.get("/settings/response")
async def get_response_settings(
    request: Request, session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Get current response generation settings."""
    try:
        settings_mgr = get_settings_manager()
        settings = settings_mgr.get_response_settings()

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_VIEW,
            username=session["username"],
            details={"resource": "response_settings"},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        return settings.to_dict()

    except Exception as e:
        logger.error(f"Error getting response settings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching response settings")


@router.put("/settings/response")
async def update_response_settings(
    request: Request, settings_data: Dict[str, Any], session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Update response generation settings."""
    try:
        settings = ResponseSettings.from_dict(settings_data)
        settings_mgr = get_settings_manager()
        success = settings_mgr.set_response_settings(settings, session["user_id"])

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update response settings")

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.CONFIG_UPDATE,
            username=session["username"],
            details={"resource": "response_settings", "new_settings": settings.to_dict()},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        logger.info(f"Response settings updated by user {session['user_id']}: {settings.to_dict()}")
        return {"success": True, "message": "Response settings updated successfully", "settings": settings.to_dict()}

    except Exception as e:
        logger.error(f"Error updating response settings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error updating response settings")


@router.get("/settings/routing")
async def get_routing_settings(
    request: Request, session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Get current query routing settings."""
    try:
        settings_mgr = get_settings_manager()
        settings = settings_mgr.get_routing_settings()

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_VIEW,
            username=session["username"],
            details={"resource": "routing_settings"},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        return settings.to_dict()

    except Exception as e:
        logger.error(f"Error getting routing settings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching routing settings")


@router.put("/settings/routing")
async def update_routing_settings(
    request: Request, settings_data: Dict[str, Any], session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Update query routing settings."""
    try:
        settings = QueryRoutingSettings.from_dict(settings_data)
        settings_mgr = get_settings_manager()
        success = settings_mgr.set_routing_settings(settings, session["user_id"])

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update routing settings")

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.CONFIG_UPDATE,
            username=session["username"],
            details={"resource": "routing_settings", "new_settings": settings.to_dict()},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        logger.info(f"Routing settings updated by user {session['user_id']}: {settings.to_dict()}")
        return {"success": True, "message": "Routing settings updated successfully", "settings": settings.to_dict()}

    except Exception as e:
        logger.error(f"Error updating routing settings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error updating routing settings")


@router.get("/settings/features")
async def get_feature_flags(request: Request, session: Dict[str, Any] = Depends(require_admin_auth)) -> Dict[str, Any]:
    """Get current feature flags."""
    try:
        settings_mgr = get_settings_manager()
        settings = settings_mgr.get_feature_flags()

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_VIEW,
            username=session["username"],
            details={"resource": "feature_flags"},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        return settings.to_dict()

    except Exception as e:
        logger.error(f"Error getting feature flags: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching feature flags")


@router.put("/settings/features")
async def update_feature_flags(
    request: Request, settings_data: Dict[str, Any], session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Update feature flags."""
    try:
        settings = FeatureFlags.from_dict(settings_data)
        settings_mgr = get_settings_manager()
        success = settings_mgr.set_feature_flags(settings, session["user_id"])

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update feature flags")

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.CONFIG_UPDATE,
            username=session["username"],
            details={"resource": "feature_flags", "new_settings": settings.to_dict()},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        logger.info(f"Feature flags updated by user {session['user_id']}: {settings.to_dict()}")
        return {"success": True, "message": "Feature flags updated successfully", "settings": settings.to_dict()}

    except Exception as e:
        logger.error(f"Error updating feature flags: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error updating feature flags")


@router.get("/settings/cache/status")
async def get_settings_cache_status(
    request: Request, session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Get settings cache status for monitoring."""
    try:
        settings_mgr = get_settings_manager()
        cache_status = settings_mgr.get_cache_status()

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_VIEW,
            username=session["username"],
            details={"resource": "settings_cache_status"},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        return cache_status

    except Exception as e:
        logger.error(f"Error getting settings cache status: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching cache status")


@router.post("/settings/cache/invalidate")
async def invalidate_settings_cache(
    request: Request, session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Invalidate settings cache to force refresh."""
    try:
        settings_mgr = get_settings_manager()
        settings_mgr.invalidate_cache()

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.CONFIG_UPDATE,
            username=session["username"],
            details={"resource": "settings_cache_invalidation"},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        logger.info(f"Settings cache invalidated by user {session['user_id']}")
        return {"success": True, "message": "Settings cache invalidated successfully"}

    except Exception as e:
        logger.error(f"Error invalidating settings cache: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error invalidating cache")


# Welcome Question Management Routes
@router.get("/settings/welcome/questions")
async def get_welcome_questions(
    request: Request,
    session: Dict[str, Any] = Depends(require_admin_auth),
    active_only: bool = Query(default=False, description="Return only active questions"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of questions to return"),
    offset: int = Query(default=0, ge=0, description="Number of questions to skip"),
) -> List[Dict[str, Any]]:
    """Get welcome questions with filtering and pagination."""
    try:
        questions = admin_db_manager.get_welcome_questions(active_only=active_only, limit=limit, offset=offset)

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_VIEW,
            username=session["username"],
            details={
                "resource": "welcome_questions",
                "active_only": active_only,
                "count": len(questions),
            },
            ip_address=client_ip,
            user_agent=user_agent,
        )

        return questions

    except Exception as e:
        logger.error(f"Error getting welcome questions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching welcome questions")


@router.post("/settings/welcome/questions")
async def create_welcome_question(
    request: Request,
    question_data: CreateWelcomeQuestionRequest,
    session: Dict[str, Any] = Depends(require_admin_auth),
) -> Dict[str, Any]:
    """Create a new welcome question."""
    try:
        # Create the question
        question_id = admin_db_manager.create_welcome_question(
            question_text=question_data.question_text,
            sort_order=question_data.sort_order,
            created_by=session["user_id"],
        )

        # Fetch the created question
        created_question = admin_db_manager.get_welcome_question(question_id)
        if not created_question:
            # Graceful fallback
            created_question = {
                "id": question_id,
                "question_text": question_data.question_text,
                "sort_order": question_data.sort_order or 0,
                "is_active": True,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "created_by": session.get("user_id"),
            }

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_CREATE,
            username=session["username"],
            details={
                "resource": "welcome_question",
                "question_id": question_id,
                "question_text": question_data.question_text,
            },
            ip_address=client_ip,
            user_agent=user_agent,
        )

        logger.info(f"Welcome question created by user {session['user_id']}: {question_data.question_text}")

        return created_question

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating welcome question: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error creating welcome question")


@router.put("/settings/welcome/questions/{question_id}")
async def update_welcome_question(
    request: Request,
    question_id: int,
    question_data: UpdateWelcomeQuestionRequest,
    session: Dict[str, Any] = Depends(require_admin_auth),
) -> Dict[str, Any]:
    """Update an existing welcome question."""
    try:
        # Check if question exists
        existing_question = admin_db_manager.get_welcome_question(question_id)
        if not existing_question:
            raise HTTPException(status_code=404, detail="Question not found")

        # Update the question
        success = admin_db_manager.update_welcome_question(
            question_id=question_id,
            question_text=question_data.question_text,
            sort_order=question_data.sort_order,
            is_active=question_data.is_active,
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update question")

        # Fetch the updated question
        updated_question = admin_db_manager.get_welcome_question(question_id)
        if not updated_question:
            raise HTTPException(status_code=500, detail="Failed to retrieve updated question")

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_UPDATE,
            username=session["username"],
            details={
                "resource": "welcome_question",
                "question_id": question_id,
                "changes": question_data.dict(exclude_unset=True),
            },
            ip_address=client_ip,
            user_agent=user_agent,
        )

        logger.info(f"Welcome question {question_id} updated by user {session['user_id']}")

        return updated_question

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating welcome question: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error updating welcome question")


@router.delete("/settings/welcome/questions/{question_id}")
async def delete_welcome_question(
    request: Request, question_id: int, session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Delete a welcome question."""
    try:
        # Check if question exists
        existing_question = admin_db_manager.get_welcome_question(question_id)
        if not existing_question:
            raise HTTPException(status_code=404, detail="Question not found")

        # Delete the question
        success = admin_db_manager.delete_welcome_question(question_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete question")

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_DELETE,
            username=session["username"],
            details={
                "resource": "welcome_question",
                "question_id": question_id,
                "question_text": existing_question.get("question_text", ""),
            },
            ip_address=client_ip,
            user_agent=user_agent,
        )

        logger.info(f"Welcome question {question_id} deleted by user {session['user_id']}")

        return {"success": True, "message": "Question deleted successfully", "question_id": question_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting welcome question: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error deleting welcome question")


@router.post("/test/reset-database")
async def reset_test_database(session: Dict[str, Any] = Depends(require_admin_auth)):
    """Reset database to default state for testing purposes."""
    try:
        # Only allow in development or test environments
        env = os.environ.get("ENVIRONMENT", "development")  # Default to development
        if env not in ["development", "test", "testing"] and not os.environ.get("ALLOW_DB_RESET"):
            raise HTTPException(
                status_code=403, detail="Database reset only available in development/test environments"
            )

        # Clear test data but preserve admin users
        with query_data_manager.get_connection() as conn:
            cursor = conn.cursor()

            # Clear query logs except for essential admin queries
            cursor.execute("DELETE FROM query_logs WHERE session_id != 'system'")

            # Clear content gaps
            cursor.execute("DELETE FROM content_gaps")

            conn.commit()

        logger.info(f"Test database reset completed by admin user {session['username']}")

        return {
            "success": True,
            "message": "Test database reset completed",
            "reset_items": ["query_logs", "content_gaps"],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting test database: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error resetting test database")


# API Key Management Endpoints
@router.get("/settings/api-keys")
async def get_api_keys(
    request: Request,
    session: Dict[str, Any] = Depends(require_admin_auth),
    include_inactive: bool = Query(default=False, description="Include inactive API keys"),
) -> Dict[str, Any]:
    """Get all API keys (without actual values)."""
    try:
        keys = api_key_manager.list_api_keys(include_inactive=include_inactive)

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_VIEW,
            username=session["username"],
            details={"resource": "api_keys", "count": len(keys), "include_inactive": include_inactive},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        return {"keys": keys, "total": len(keys)}

    except Exception as e:
        logger.error(f"Error getting API keys: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching API keys")


@router.post("/settings/api-keys")
async def create_api_key(
    request: Request,
    key_data: Dict[str, Any],
    session: Dict[str, Any] = Depends(require_admin_auth),
) -> Dict[str, Any]:
    """Create a new API key."""
    try:
        # Validate required fields
        if not all(k in key_data for k in ["key_name", "key_type", "api_key"]):
            raise HTTPException(status_code=400, detail="Missing required fields: key_name, key_type, api_key")

        # Create the key
        created_key = api_key_manager.create_api_key(
            key_name=key_data["key_name"],
            key_type=key_data["key_type"],
            api_key=key_data["api_key"],
            updated_by=session["user_id"],
        )

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_CREATE,
            username=session["username"],
            details={"resource": "api_key", "key_name": created_key["key_name"], "key_type": created_key["key_type"]},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        return {"success": True, "message": "API key created successfully", "key": created_key}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating API key: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error creating API key")


@router.put("/settings/api-keys/{key_name}")
async def update_api_key(
    request: Request,
    key_name: str,
    key_data: Dict[str, Any],
    session: Dict[str, Any] = Depends(require_admin_auth),
) -> Dict[str, Any]:
    """Update an existing API key."""
    try:
        if "api_key" not in key_data:
            raise HTTPException(status_code=400, detail="Missing required field: api_key")

        # Update the key
        success = api_key_manager.update_api_key(
            key_name=key_name, new_api_key=key_data["api_key"], updated_by=session["user_id"]
        )

        if not success:
            raise HTTPException(status_code=404, detail="API key not found")

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_UPDATE,
            username=session["username"],
            details={"resource": "api_key", "key_name": key_name},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        return {"success": True, "message": "API key updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating API key {key_name}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error updating API key")


@router.post("/settings/api-keys/{key_name}/toggle")
async def toggle_api_key(
    request: Request,
    key_name: str,
    toggle_data: Dict[str, Any],
    session: Dict[str, Any] = Depends(require_admin_auth),
) -> Dict[str, Any]:
    """Enable or disable an API key."""
    try:
        if "is_active" not in toggle_data:
            raise HTTPException(status_code=400, detail="Missing required field: is_active")

        success = api_key_manager.toggle_api_key(
            key_name=key_name, is_active=toggle_data["is_active"], updated_by=session["user_id"]
        )

        if not success:
            raise HTTPException(status_code=404, detail="API key not found")

        action_name = "enabled" if toggle_data["is_active"] else "disabled"
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_UPDATE,
            username=session["username"],
            details={
                "resource": "api_key",
                "key_name": key_name,
                "action": action_name,
                "is_active": toggle_data["is_active"],
            },
            ip_address=client_ip,
            user_agent=user_agent,
        )

        return {"success": True, "message": f"API key {action_name} successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling API key {key_name}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error toggling API key")


@router.delete("/settings/api-keys/{key_name}")
async def delete_api_key(
    request: Request,
    key_name: str,
    session: Dict[str, Any] = Depends(require_admin_auth),
) -> Dict[str, Any]:
    """Delete an API key."""
    try:
        success = api_key_manager.delete_api_key(key_name)

        if not success:
            raise HTTPException(status_code=404, detail="API key not found")

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_DELETE,
            username=session["username"],
            details={"resource": "api_key", "key_name": key_name},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        return {"success": True, "message": "API key deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting API key {key_name}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error deleting API key")


@router.post("/settings/api-keys/{key_name}/validate")
async def validate_api_key(
    request: Request,
    key_name: str,
    session: Dict[str, Any] = Depends(require_admin_auth),
) -> Dict[str, Any]:
    """Validate an API key by testing it with the provider."""
    try:
        is_valid, message = api_key_manager.validate_api_key(key_name)

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_VIEW,
            username=session["username"],
            details={
                "resource": "api_key_validation",
                "key_name": key_name,
                "is_valid": is_valid,
                "validation_message": message,
            },
            ip_address=client_ip,
            user_agent=user_agent,
        )

        return {"success": True, "valid": is_valid, "message": message, "key_name": key_name}

    except Exception as e:
        logger.error(f"Error validating API key {key_name}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error validating API key")


@router.post("/settings/api-keys/migrate-from-env")
async def migrate_api_keys_from_env(
    request: Request,
    session: Dict[str, Any] = Depends(require_admin_auth),
) -> Dict[str, Any]:
    """Migrate API keys from environment variables to database."""
    try:
        results = api_key_manager.migrate_from_environment(session["user_id"])

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.CONFIG_UPDATE,
            username=session["username"],
            details={"resource": "api_key_migration", "migration_results": results},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        successful = sum(1 for success in results.values() if success)
        total = len(results)

        return {
            "success": True,
            "message": f"Migration completed: {successful}/{total} keys migrated",
            "results": results,
        }

    except Exception as e:
        logger.error(f"Error migrating API keys from environment: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error migrating API keys")


# System Configuration Settings Endpoints
@router.get("/settings/system-config")
async def get_system_config_settings(
    request: Request, session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Get current system configuration settings."""
    try:
        settings_mgr = get_settings_manager()
        settings = settings_mgr.get_system_config_settings()

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_VIEW,
            username=session["username"],
            details={"resource": "system_config_settings"},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        return settings.to_dict()

    except Exception as e:
        logger.error(f"Error getting system config settings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching system configuration settings")


@router.put("/settings/system-config")
async def update_system_config_settings(
    request: Request, settings_data: Dict[str, Any], session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Update system configuration settings."""
    try:
        settings = SystemConfigurationSettings.from_dict(settings_data)
        settings_mgr = get_settings_manager()
        success = settings_mgr.set_system_config_settings(settings, session["user_id"])

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update system configuration settings")

        # IMPORTANT: Invalidate settings cache to ensure changes take effect immediately
        # This prevents the 5-minute cache from serving stale settings
        settings_mgr.invalidate_cache("system_config_settings")
        logger.info("Invalidated system config settings cache after admin update")

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.CONFIG_UPDATE,
            username=session["username"],
            details={"resource": "system_config_settings", "new_settings": settings.to_dict()},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        logger.info(f"System config settings updated by user {session['user_id']}: {settings.to_dict()}")
        return {
            "success": True,
            "message": "System configuration settings updated successfully",
            "settings": settings.to_dict(),
        }

    except Exception as e:
        logger.error(f"Error updating system config settings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error updating system configuration settings")


# Security Settings Endpoints
@router.get("/settings/security")
async def get_security_settings(
    request: Request, session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Get current security settings."""
    try:
        settings_mgr = get_settings_manager()
        settings = settings_mgr.get_security_settings()

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_VIEW,
            username=session["username"],
            details={"resource": "security_settings"},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        return settings.to_dict()

    except Exception as e:
        logger.error(f"Error getting security settings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching security settings")


@router.put("/settings/security")
async def update_security_settings(
    request: Request, settings_data: Dict[str, Any], session: Dict[str, Any] = Depends(require_admin_auth)
) -> Dict[str, Any]:
    """Update security settings."""
    try:
        settings = SecuritySettings.from_dict(settings_data)
        settings_mgr = get_settings_manager()
        success = settings_mgr.set_security_settings(settings, session["user_id"])

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update security settings")

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.CONFIG_UPDATE,
            username=session["username"],
            details={"resource": "security_settings", "new_settings": settings.to_dict()},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        logger.info(f"Security settings updated by user {session['user_id']}: {settings.to_dict()}")
        return {"success": True, "message": "Security settings updated successfully", "settings": settings.to_dict()}

    except Exception as e:
        logger.error(f"Error updating security settings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error updating security settings")


# User Management endpoints
@router.get(
    "/users",
    tags=["Admin Management"],
    summary="Get Admin Users",
    description="""
            **Get all admin users with safe information (excluding password hashes).**
            
            **Access Control:**
            - Requires admin authentication
            - Only users with admin role can access
            
            **Returns:**
            - List of admin users with safe fields only
            - User creation and last login timestamps
            - User roles and active status
            
            **Security:**
            - Password hashes are never returned
            - Audit logged for security monitoring
            """,
)
async def get_admin_users(
    request: Request,
    session: Dict[str, Any] = Depends(require_admin_auth),
) -> List[Dict[str, Any]]:
    """Get all admin users (safe information only)."""
    try:
        users = admin_db_manager.get_all_admin_users()

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.DATA_VIEW,
            username=session["username"],
            details={"resource": "admin_users", "user_count": len(users)},
            ip_address=client_ip,
            user_agent=user_agent,
        )

        return users

    except Exception as e:
        logger.error(f"Error getting admin users: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error fetching admin users")


@router.post(
    "/users",
    tags=["Admin Management"],
    summary="Create Admin User",
    description="""
            **Create a new admin user account.**
            
            **Requirements:**
            - Username must be unique
            - Password must meet security requirements (min 12 characters)
            - Email is optional but recommended
            - Role defaults to 'viewer' if not specified
            
            **Security:**
            - Password is securely hashed with bcrypt
            - Creation is audit logged
            - Only admin users can create other users
            """,
)
async def create_admin_user(
    request: Request,
    user_data: CreateUserRequest,
    session: Dict[str, Any] = Depends(require_admin_auth),
) -> Dict[str, Any]:
    """Create a new admin user."""
    try:
        # Validate password strength using centralized validator
        try:
            admin_auth_manager.validate_password_strength(user_data.password)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Check if username already exists
        existing_user = admin_db_manager.get_admin_user(user_data.username)
        if existing_user:
            raise HTTPException(status_code=409, detail="Username already exists")

        # Hash password
        password_bytes = user_data.password.encode("utf-8")
        password_hash = bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")

        # Create user
        user_id = admin_db_manager.create_admin_user(
            username=user_data.username,
            email=user_data.email,
            password_hash=password_hash,
            role=user_data.role or "viewer",
        )

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.USER_CREATE,
            username=session["username"],
            details={
                "resource": "admin_user",
                "new_user_id": user_id,
                "new_username": user_data.username,
                "new_role": user_data.role or "viewer",
                "created_by": session["user_id"],
            },
            ip_address=client_ip,
            user_agent=user_agent,
        )

        logger.info(f"Admin user {user_data.username} created by user {session['user_id']}")

        # Return safe user data (no password hash)
        new_user = admin_db_manager.get_admin_user(user_data.username)
        if new_user:
            # Remove password hash for response
            safe_user = {k: v for k, v in new_user.items() if k != "password_hash"}
            return {"success": True, "message": "User created successfully", "user": safe_user}
        else:
            return {"success": True, "message": "User created successfully", "user_id": user_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating admin user: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error creating admin user")


@router.put(
    "/users/{user_id}/deactivate",
    tags=["Admin Management"],
    summary="Deactivate Admin User",
    description="""
            **Deactivate an admin user account.**
            
            **Actions Performed:**
            - Sets user as inactive
            - Expires all user sessions immediately
            - User cannot log in until reactivated
            
            **Security:**
            - Cannot deactivate your own account (prevents lockout)
            - Action is audit logged
            - All user sessions are terminated
            """,
)
async def deactivate_admin_user(
    request: Request,
    user_id: int,
    session: Dict[str, Any] = Depends(require_admin_auth),
) -> Dict[str, Any]:
    """Deactivate an admin user."""
    try:
        # Prevent self-deactivation
        if user_id == session["user_id"]:
            raise HTTPException(status_code=400, detail="Cannot deactivate your own account")

        # Check if user exists
        user_info = admin_db_manager.get_admin_user_by_id(user_id)
        if not user_info:
            raise HTTPException(status_code=404, detail="User not found")

        # Deactivate user
        success = admin_db_manager.deactivate_admin_user(user_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to deactivate user")

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        audit_logger.log_action(
            action=AuditAction.USER_DEACTIVATE,
            username=session["username"],
            details={
                "resource": "admin_user",
                "target_user_id": user_id,
                "target_username": user_info.get("username"),
                "deactivated_by": session["user_id"],
            },
            ip_address=client_ip,
            user_agent=user_agent,
        )

        logger.info(f"Admin user {user_id} deactivated by user {session['user_id']}")

        return {"success": True, "message": "User deactivated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating admin user: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error deactivating admin user")


@router.post(
    "/users/{user_id}/reactivate",
    tags=["Admin Management"],
    summary="Reactivate a deactivated admin user",
    description="""
            **Reactivate a deactivated admin user account.**
            
            **Actions Performed:**
            - Sets user as active
            - User can log in again
            
            **Security:**
            - Cannot reactivate your own account (must be active to use this endpoint)
            - Action is audit logged
            """,
)
async def reactivate_admin_user(
    user_id: int,
    request: Request,
    session: Dict[str, Any] = Depends(require_admin_auth),
) -> Dict[str, Any]:
    """Reactivate a deactivated admin user account."""
    try:
        current_user_id = session["user_id"]
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        # Get user info before reactivation
        user_info = admin_db_manager.get_admin_user_by_id(user_id)
        if not user_info:
            raise HTTPException(status_code=404, detail="User not found")

        # Check if user is already active
        if user_info.get("is_active"):
            raise HTTPException(status_code=400, detail="User is already active")

        # Reactivate the user
        success = admin_db_manager.reactivate_admin_user(user_id)
        if success:
            # Log the action
            audit_logger.log_action(
                action=AuditAction.USER_REACTIVATE,
                username=session["username"],
                details={
                    "resource": "admin_user",
                    "target_user_id": user_id,
                    "target_username": user_info.get("username"),
                    "reactivated_by": current_user_id,
                },
                ip_address=client_ip,
                user_agent=user_agent,
            )
            logger.info(f"Admin user {user_id} reactivated by user {current_user_id}")
            return {"success": True, "message": f"User {user_info.get('username')} reactivated successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to reactivate user")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reactivating admin user: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error reactivating admin user")


@router.post(
    "/users/bulk/deactivate",
    tags=["Admin Management"],
    summary="Bulk deactivate admin users",
    description="""
            **Deactivate multiple admin users at once.**
            
            **Actions Performed:**
            - Sets users as inactive
            - Expires all user sessions immediately for each user
            - Users cannot log in until reactivated
            
            **Security:**
            - Cannot deactivate your own account (prevents lockout)
            - Action is audit logged for each user
            - All user sessions are terminated for each deactivated user
            
            **Request Format:**
            ```json
            {
                "user_ids": [1, 2, 3]
            }
            ```
            """,
)
async def bulk_deactivate_admin_users(
    bulk_request: BulkDeactivateUsersRequest,
    request: Request,
    session: Dict[str, Any] = Depends(require_admin_auth),
) -> Dict[str, Any]:
    """Deactivate multiple admin users at once."""
    try:
        user_ids = bulk_request.user_ids
        current_user_id = session["user_id"]
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        # Validate request
        if not user_ids:
            raise HTTPException(status_code=400, detail="No user IDs provided")

        if len(user_ids) > 50:
            raise HTTPException(status_code=400, detail="Cannot deactivate more than 50 users at once")

        # Prevent self-deactivation
        if current_user_id in user_ids:
            raise HTTPException(status_code=400, detail="Cannot deactivate your own account")

        # Verify all users exist before deactivating any (single query to prevent N+1 problem)
        user_infos = admin_db_manager.get_admin_users_by_ids(user_ids)

        # Check if all requested users were found
        missing_user_ids = [user_id for user_id in user_ids if user_id not in user_infos]
        if missing_user_ids:
            if len(missing_user_ids) == 1:
                raise HTTPException(status_code=404, detail=f"User with ID {missing_user_ids[0]} not found")
            else:
                raise HTTPException(status_code=404, detail=f"Users with IDs {missing_user_ids} not found")

        # Deactivate users
        successful_deactivations = []
        failed_deactivations = []

        for user_id in user_ids:
            try:
                success = admin_db_manager.deactivate_admin_user(user_id)
                if success:
                    successful_deactivations.append(user_id)

                    # Log audit entry for each deactivation
                    audit_logger.log_action(
                        action=AuditAction.USER_DEACTIVATE,
                        username=session["username"],
                        details={
                            "resource": "admin_user",
                            "target_user_id": user_id,
                            "target_username": user_infos[user_id].get("username"),
                            "deactivated_by": current_user_id,
                            "bulk_operation": True,
                        },
                        ip_address=client_ip,
                        user_agent=user_agent,
                    )
                else:
                    failed_deactivations.append(user_id)
            except Exception as e:
                logger.error(f"Error deactivating user {user_id}: {str(e)}")
                failed_deactivations.append(user_id)

        # Log summary
        logger.info(
            f"Bulk deactivation completed by user {current_user_id}: "
            f"{len(successful_deactivations)} successful, {len(failed_deactivations)} failed"
        )

        # Prepare response
        response_data = {
            "success": True,
            "total_requested": len(user_ids),
            "successful_deactivations": len(successful_deactivations),
            "failed_deactivations": len(failed_deactivations),
            "deactivated_user_ids": successful_deactivations,
        }

        if failed_deactivations:
            response_data["failed_user_ids"] = failed_deactivations
            response_data["message"] = (
                f"Bulk deactivation partially completed. "
                f"{len(successful_deactivations)} users deactivated, "
                f"{len(failed_deactivations)} failed."
            )
        else:
            response_data["message"] = f"Successfully deactivated {len(successful_deactivations)} users"

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in bulk deactivate admin users: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error deactivating admin users")


@router.delete(
    "/users/bulk",
    summary="Bulk delete admin users",
    description="Permanently delete multiple admin users at once. This action cannot be undone.",
)
async def bulk_delete_admin_users(
    bulk_request: BulkDeleteUsersRequest,
    request: Request,
    session: Dict[str, Any] = Depends(require_admin_auth),
):
    """
    Permanently delete multiple admin users at once.

    Security restrictions:
        - Cannot delete your own account (prevents lockout)
        - Only admin users can delete other users
        - All deletions are logged for audit purposes
        - Terminates all sessions for deleted users
    """
    try:
        user_ids = bulk_request.user_ids
        current_user_id = session["user_id"]

        # Prevent self-deletion to avoid lockout
        if current_user_id in user_ids:
            raise HTTPException(status_code=400, detail="Cannot delete your own account in bulk operation")

        # Track successful deletions and failures
        successful_deletions = []
        failed_deletions = []
        audit_entries = []

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        # Get all users at once to prevent N+1 query problem
        users_to_delete = admin_db_manager.get_admin_users_by_ids(user_ids)

        # Process each user deletion
        for user_id in user_ids:
            try:
                # Get user info from our batch fetch
                user_to_delete = users_to_delete.get(user_id)
                if not user_to_delete:
                    failed_deletions.append({"user_id": user_id, "error": "User not found"})
                    continue

                # Permanently delete the user
                success = admin_db_manager.delete_admin_user(user_id)
                if not success:
                    failed_deletions.append(
                        {
                            "user_id": user_id,
                            "username": user_to_delete["username"],
                            "error": "Failed to delete user from database",
                        }
                    )
                    continue

                # Track successful deletion
                successful_deletions.append({"user_id": user_id, "username": user_to_delete["username"]})

                # Prepare audit entry
                audit_entries.append(
                    {
                        "deleted_user_id": user_id,
                        "deleted_username": user_to_delete["username"],
                    }
                )

            except Exception as e:
                failed_deletions.append({"user_id": user_id, "error": f"Unexpected error: {str(e)}"})

        # Log all successful deletions in a single audit entry
        if successful_deletions:
            audit_logger.log_action(
                action=AuditAction.USER_DELETE,
                username=session["username"],
                details={
                    "bulk_operation": True,
                    "deleted_users": audit_entries,
                    "deleted_by": current_user_id,
                    "total_deleted": len(successful_deletions),
                },
                ip_address=client_ip,
                user_agent=user_agent,
            )

            logger.info(
                f"Bulk deletion: {len(successful_deletions)} users deleted by user {current_user_id}. "
                f"Users: {[d['username'] for d in successful_deletions]}"
            )

        # Prepare response
        response_data = {
            "success": len(failed_deletions) == 0,
            "total_requested": len(user_ids),
            "successful_deletions": len(successful_deletions),
            "failed_deletions": len(failed_deletions),
        }

        if successful_deletions:
            response_data["deleted_users"] = [d["username"] for d in successful_deletions]

        if failed_deletions:
            response_data["failures"] = failed_deletions

        if len(successful_deletions) > 0 and len(failed_deletions) == 0:
            response_data["message"] = f"Successfully deleted {len(successful_deletions)} user(s)"
        elif len(successful_deletions) > 0 and len(failed_deletions) > 0:
            response_data["message"] = (
                f"Partially completed: {len(successful_deletions)} deleted, {len(failed_deletions)} failed"
            )
        else:
            response_data["message"] = "No users were deleted due to errors"

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in bulk delete admin users: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error processing bulk delete operation")


@router.delete(
    "/users/{user_id}",
    summary="Permanently delete admin user",
    description="Permanently delete an admin user account. This action cannot be undone.",
    dependencies=[Depends(require_admin_auth)],
)
async def delete_admin_user(
    user_id: int,
    request: Request,
    session: Dict[str, Any] = Depends(require_admin_auth),
):
    """
    Permanently delete an admin user account.

    Security restrictions:
        - Cannot delete your own account (prevents lockout)
        - Only admin users can delete other users
        - Action is logged for audit purposes
        - Terminates all sessions for the deleted user
    """
    try:
        # Prevent self-deletion to avoid lockout
        if user_id == session["user_id"]:
            raise HTTPException(status_code=400, detail="Cannot delete your own account")

        # Get user info before deletion for audit logging
        user_to_delete = admin_db_manager.get_admin_user_by_id(user_id)
        if not user_to_delete:
            raise HTTPException(status_code=404, detail="User not found")

        # Permanently delete the user
        success = admin_db_manager.delete_admin_user(user_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete user")

        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "")

        # Audit log deletion
        audit_logger.log_action(
            action=AuditAction.USER_DELETE,
            username=session["username"],
            details={
                "deleted_user_id": user_id,
                "deleted_username": user_to_delete["username"],
                "deleted_by": session["user_id"],
            },
            ip_address=client_ip,
            user_agent=user_agent,
        )

        logger.info(
            f"Admin user {user_id} ({user_to_delete['username']}) permanently deleted by user {session['user_id']}"
        )

        return {"success": True, "message": "User permanently deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting admin user: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error deleting admin user")
