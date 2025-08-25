"""
API routes for the RAG admin dashboard.
"""

import csv
import io
import logging
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response, StreamingResponse

from .auth import auth_manager, get_current_user, require_admin_role, require_auth
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
async def login(login_data: LoginRequest, request: Request, response: Response):
    """Authenticate user and create session."""
    try:
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("User-Agent")

        auth_result = auth_manager.authenticate_user(
            login_data.username, login_data.password, ip_address=client_ip, user_agent=user_agent
        )

        if not auth_result:
            return LoginResponse(success=False, message="Invalid username or password")

        user_data = auth_result["user"].copy()
        user_data.pop("password_hash", None)  # Remove password hash from response

        # Set session cookie
        response.set_cookie(
            key="admin_session",
            value=auth_result["session_id"],
            max_age=24 * 60 * 60,  # 24 hours
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax",
        )

        return LoginResponse(
            success=True, message="Login successful", user=user_data, session_id=auth_result["session_id"]
        )

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail="Login failed")


@router.post("/auth/logout")
async def logout(request: Request, response: Response, session: dict = Depends(require_auth)):
    """Logout user and expire session."""
    try:
        session_id = request.cookies.get("admin_session")
        if session_id:
            auth_manager.expire_session(session_id)

        # Clear session cookie
        response.delete_cookie(key="admin_session")

        return {"success": True, "message": "Logout successful"}

    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(status_code=500, detail="Logout failed")


@router.get("/auth/me")
async def get_current_user_info(session: dict = Depends(require_auth)):
    """Get current authenticated user information."""
    user_data = {
        "id": session["user_id"],
        "username": session["username"],
        "email": session["email"],
        "role": session["role"],
        "last_login_at": session.get("last_login_at"),
    }
    return {"user": user_data}


@router.post("/auth/change-password")
async def change_password(password_data: ChangePasswordRequest, session: dict = Depends(require_auth)):
    """Change the current user's password."""
    try:
        # Get the current user
        user = db_manager.get_admin_user(session["username"])
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Verify current password
        if not auth_manager.verify_password(password_data.current_password, user["password_hash"]):
            raise HTTPException(status_code=400, detail="Current password is incorrect")

        # Validate new password
        if len(password_data.new_password) < 8:
            raise HTTPException(status_code=400, detail="New password must be at least 8 characters long")

        if password_data.current_password == password_data.new_password:
            raise HTTPException(status_code=400, detail="New password must be different from current password")

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
        logger.error(f"Password change error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to change password")


@router.post("/auth/create-user")
async def create_user(user_data: CreateUserRequest, session: dict = Depends(require_admin_role)):
    """Create a new admin user (admin only)."""
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
        logger.error(f"Create user error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create user")


@router.get("/stats/overview", response_model=OverviewStats)
async def get_overview_stats(days: int = Query(7, ge=1, le=90), session: dict = Depends(require_auth)):
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
        raise HTTPException(status_code=500, detail=f"Error fetching overview stats: {str(e)}")


@router.get("/queries", response_model=QueryResponse)
async def get_queries(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    errors_only: bool = Query(False),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    session: dict = Depends(require_auth),
):
    """Get paginated list of queries with optional filters."""
    try:
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
        raise HTTPException(status_code=500, detail=f"Error fetching queries: {str(e)}")


@router.get("/queries/{query_id}")
async def get_query_detail(query_id: int, session: dict = Depends(require_auth)):
    """Get detailed information about a specific query."""
    try:
        result = query_data_manager.get_queries(limit=1, offset=0)
        # Filter by ID (simplified for this implementation)
        with query_data_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM query_logs WHERE id = ?", (query_id,))
            row = cursor.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="Query not found")

            query_dict = dict(row)
            # Parse JSON fields
            if query_dict["sources_used"]:
                import json

                query_dict["sources_used"] = json.loads(query_dict["sources_used"])
            if query_dict["follow_up_questions"]:
                import json

                query_dict["follow_up_questions"] = json.loads(query_dict["follow_up_questions"])

            return query_dict
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching query detail: {str(e)}")


@router.post("/queries/{query_id}/feedback")
async def update_query_feedback(query_id: int, feedback: FeedbackUpdate, session: dict = Depends(require_auth)):
    """Update user feedback for a query."""
    if feedback.feedback not in ["helpful", "not_helpful"]:
        raise HTTPException(status_code=400, detail="Feedback must be 'helpful' or 'not_helpful'")

    try:
        # Update feedback directly in the backend database
        with query_data_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE query_logs SET user_feedback = ? WHERE id = ?", (feedback.feedback, query_id))
            conn.commit()
        return {"status": "success", "message": "Feedback updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating feedback: {str(e)}")


@router.get("/performance/metrics")
async def get_performance_metrics(
    time_range: str = Query("24h", regex="^(1h|6h|24h|7d|30d)$"), session: dict = Depends(require_auth)
):
    """Get performance metrics for the specified time range with comparison to previous period."""
    try:
        current_metrics = query_data_manager.get_performance_metrics(time_range)
        # TODO: Implement previous period calculation
        previous_metrics = query_data_manager.get_performance_metrics(time_range)

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
        raise HTTPException(status_code=500, detail=f"Error fetching performance metrics: {str(e)}")


@router.get("/performance/timeline")
async def get_performance_timeline(
    days: int = Query(7, ge=1, le=90),
    interval: str = Query("hour", regex="^(hour|day)$"),
    session: dict = Depends(require_auth),
):
    """Get time series data for performance charts."""
    try:
        with query_data_manager.get_connection() as conn:
            cursor = conn.cursor()

            if interval == "hour":
                time_format = "%Y-%m-%d %H:00:00"
                time_group = "strftime('%Y-%m-%d %H:00:00', timestamp)"
            else:
                time_format = "%Y-%m-%d"
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
    time_range: str = Query("24h", regex="^(1h|6h|24h|7d|30d)$"), session: dict = Depends(require_auth)
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
    session: dict = Depends(require_auth),
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
    session: dict = Depends(require_auth),
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
async def get_popular_topics(session: dict = Depends(require_auth)):
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
    active_only: bool = Query(False), limit: int = Query(50, ge=1, le=1000), session: dict = Depends(require_auth)
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
    session: dict = Depends(require_auth),
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
async def upload_knowledge_files(files: List[UploadFile] = File(...), session: dict = Depends(require_auth)):
    """Upload files to the knowledge base directory."""
    # Get the knowledge base directory path
    # Assuming the admin backend is in /admin/backend and knowledge is in /backend/knowledge
    knowledge_dir = Path(__file__).parent.parent.parent / "backend" / "knowledge"
    knowledge_dir.mkdir(parents=True, exist_ok=True)

    # Allowed file extensions
    allowed_extensions = {".md", ".pdf", ".json", ".txt", ".html", ".docx"}

    uploaded_files = []
    errors = []

    try:
        for file in files:
            # Validate file extension
            file_ext = Path(file.filename).suffix.lower()
            if file_ext not in allowed_extensions:
                errors.append(
                    f"File '{file.filename}' has unsupported extension. Allowed: {', '.join(allowed_extensions)}"
                )
                continue

            # Check file size (10MB limit)
            if file.size and file.size > 10 * 1024 * 1024:
                errors.append(f"File '{file.filename}' is too large (max 10MB)")
                continue

            # Save file to knowledge directory
            file_path = knowledge_dir / file.filename

            # Check if file already exists
            if file_path.exists():
                errors.append(f"File '{file.filename}' already exists")
                continue

            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            uploaded_files.append({"filename": file.filename, "size": file.size or 0, "path": str(file_path)})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading files: {str(e)}")

    # Return results
    response = {"uploaded_files": uploaded_files, "upload_count": len(uploaded_files), "total_files": len(files)}

    if errors:
        response["errors"] = errors

    if not uploaded_files and errors:
        raise HTTPException(status_code=400, detail={"message": "No files were uploaded", "errors": errors})

    return response


@router.get("/knowledge/files")
async def get_knowledge_files(session: dict = Depends(require_auth)):
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
async def delete_knowledge_file(filename: str, session: dict = Depends(require_auth)):
    """Delete a file from the knowledge base directory."""
    knowledge_dir = Path(__file__).parent.parent.parent / "backend" / "knowledge"
    file_path = knowledge_dir / filename

    # Security check - ensure file is in knowledge directory
    try:
        file_path.resolve().relative_to(knowledge_dir.resolve())
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
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")


@router.get("/knowledge/stats")
async def get_knowledge_stats(session: dict = Depends(require_auth)):
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
    session: dict = Depends(require_auth),
):
    """Trigger a production-ready refresh of the knowledge base index."""
    from .knowledge_refresh_service_v2 import knowledge_refresh_service

    try:
        result = await knowledge_refresh_service.refresh_knowledge_base(force_reindex=force_reindex)
        return result

    except Exception as e:
        logger.error(f"Knowledge base refresh failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error refreshing knowledge base: {str(e)}")


@router.get("/knowledge/refresh/status")
async def get_refresh_status(session: dict = Depends(require_auth)):
    """Get the current status of knowledge base refresh operation."""
    from .knowledge_refresh_service_v2 import knowledge_refresh_service

    try:
        return knowledge_refresh_service.get_refresh_status()

    except Exception as e:
        logger.error(f"Failed to get refresh status: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting refresh status: {str(e)}")


@router.post("/knowledge/refresh/wait")
async def wait_for_refresh_completion(
    timeout: int = Query(300, ge=10, le=600, description="Timeout in seconds"), session: dict = Depends(require_auth)
):
    """Wait for the current refresh operation to complete."""
    from .knowledge_refresh_service_v2 import knowledge_refresh_service

    try:
        result = await knowledge_refresh_service.wait_for_completion(timeout=timeout)
        return result

    except Exception as e:
        logger.error(f"Error waiting for refresh completion: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error waiting for refresh: {str(e)}")


@router.get("/knowledge/files/{filename}/content")
async def get_knowledge_file_content(filename: str, session: dict = Depends(require_auth)):
    """Get the content of a specific file from the knowledge base directory."""
    knowledge_dir = Path(__file__).parent.parent.parent / "backend" / "knowledge"
    file_path = knowledge_dir / filename

    # Security check - ensure file is in knowledge directory
    try:
        file_path.resolve().relative_to(knowledge_dir.resolve())
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
        raise HTTPException(status_code=400, detail="File is not a text file")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")


@router.put("/knowledge/files/{filename}/content")
async def update_knowledge_file_content(
    filename: str, file_content: FileContentUpdate, session: dict = Depends(require_auth)
):
    """Update the content of a specific file in the knowledge base directory."""
    knowledge_dir = Path(__file__).parent.parent.parent / "backend" / "knowledge"
    file_path = knowledge_dir / filename

    # Security check - ensure file is in knowledge directory
    try:
        file_path.resolve().relative_to(knowledge_dir.resolve())
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
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Error updating file: {str(e)}")
