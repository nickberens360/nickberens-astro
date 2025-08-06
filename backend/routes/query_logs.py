"""
Query logs endpoint for viewing logged queries and responses.

This module provides a protected endpoint to:
- View query logs with filtering options
- Get log statistics
- Clear logs (admin function)
"""

import hmac
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi import Query as FastAPIQuery
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..core.config import AppConfig
from ..core.query_logger import get_query_logger

# Initialize router and security
router = APIRouter()
security = HTTPBearer()


async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Verify the authorization token for accessing query logs.

    Args:
        credentials: HTTP Authorization credentials

    Returns:
        The verified token

    Raises:
        HTTPException: If token is invalid or missing
    """
    config = AppConfig()
    try:
        auth_token = config.QUERY_LOG_AUTH_TOKEN
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))

    if not auth_token:
        raise HTTPException(
            status_code=503, detail="Query log access is not configured. Set QUERY_LOG_AUTH_TOKEN environment variable."
        )

    token = str(credentials.credentials)
    if not hmac.compare_digest(token, auth_token):
        raise HTTPException(status_code=403, detail="Invalid authorization token")

    return token


@router.get("/query-logs")
async def get_query_logs(
    _token: str = Depends(verify_token),
    limit: Optional[int] = FastAPIQuery(default=100, ge=1, le=1000, description="Maximum number of logs to return"),
    start_date: Optional[str] = FastAPIQuery(default=None, description="Start date filter (YYYY-MM-DD format)"),
    end_date: Optional[str] = FastAPIQuery(default=None, description="End date filter (YYYY-MM-DD format)"),
    query_type: Optional[str] = FastAPIQuery(default=None, description="Filter by query type (text/image)"),
):
    """
    Retrieve query logs with optional filtering.

    Requires authentication via Bearer token.

    Query Parameters:
    - limit: Maximum number of logs to return (1-1000, default: 100)
    - start_date: Start date filter in YYYY-MM-DD format
    - end_date: End date filter in YYYY-MM-DD format
    - query_type: Filter by query type (text/image)
    """
    logger = get_query_logger()

    # Validate date formats if provided
    if start_date:
        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").isoformat()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD format.")

    if end_date:
        try:
            # Add time component to include the entire end date
            end_date = datetime.strptime(end_date + " 23:59:59", "%Y-%m-%d %H:%M:%S").isoformat()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD format.")

    # Validate query type
    if query_type and query_type not in ["text", "image"]:
        raise HTTPException(status_code=400, detail="Invalid query_type. Must be 'text' or 'image'.")

    logs = logger.get_logs(limit=limit, start_date=start_date, end_date=end_date, query_type=query_type)

    return {
        "logs": logs,
        "count": len(logs),
        "filters": {"limit": limit, "start_date": start_date, "end_date": end_date, "query_type": query_type},
    }


@router.get("/query-logs/stats")
async def get_query_log_stats(_token: str = Depends(verify_token)):
    """
    Get statistics about query logs.

    Requires authentication via Bearer token.

    Returns summary statistics including:
    - Total number of queries
    - Unique IP count
    - Query type breakdown
    - Model usage breakdown
    - Date range of logs
    """
    logger = get_query_logger()
    stats = logger.get_log_stats()

    return {"stats": stats, "generated_at": datetime.utcnow().isoformat()}


@router.delete("/query-logs")
async def clear_query_logs(_token: str = Depends(verify_token)):
    """
    Clear all query logs (use with caution).

    Requires authentication via Bearer token.

    This action is irreversible and will delete all logged queries.
    """
    logger = get_query_logger()
    success = logger.clear_logs()

    if success:
        return {"message": "Query logs cleared successfully", "cleared_at": datetime.utcnow().isoformat()}
    else:
        raise HTTPException(status_code=500, detail="Failed to clear query logs")


@router.get("/query-logs/health")
async def query_logs_health():
    """
    Health check endpoint for query logging system.

    This endpoint does not require authentication and can be used to verify
    that the query logging system is operational.
    """
    logger = get_query_logger()

    try:
        # Test basic functionality
        stats = logger.get_log_stats()

        return {
            "status": "healthy",
            "log_file_exists": logger.log_file_path.exists(),
            "total_logs": stats.get("total_queries", 0),
            "excluded_ips_count": len(logger.excluded_ips),
            "auth_configured": bool(getattr(AppConfig(), "QUERY_LOG_AUTH_TOKEN", None)),
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@router.get("/query-logs/admin", response_class=HTMLResponse)
async def query_logs_admin_page():
    """
    Serve the query logs admin web interface.

    This endpoint serves a web interface for managing query logs.
    No authentication required for serving the page (auth happens via API calls).
    """
    template_path = Path(__file__).parent.parent / "templates" / "query_logs_admin.html"

    try:
        with open(template_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Admin page template not found")
