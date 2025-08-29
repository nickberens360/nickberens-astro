"""
Query logs endpoint for viewing logged queries and responses.

This module provides a protected endpoint to:
- View query logs with filtering options
- Get log statistics
- Clear logs (admin function)
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi import Query as FastAPIQuery
from fastapi import Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..core.admin_auth import require_admin_auth
from ..core.query_logger import get_query_logger

# Initialize router and security
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

# Initialize logger
logger = logging.getLogger(__name__)

# Initialize templates
template_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(template_dir))


@router.get("/query-logs")
@limiter.limit("60/minute")  # Reasonable rate limit for log viewing
async def get_query_logs(
    request: Request,
    session: dict = Depends(require_admin_auth),
    limit: Optional[int] = FastAPIQuery(default=100, ge=1, le=1000, description="Maximum number of logs to return"),
    start_date: Optional[str] = FastAPIQuery(default=None, description="Start date filter (YYYY-MM-DD format)"),
    end_date: Optional[str] = FastAPIQuery(default=None, description="End date filter (YYYY-MM-DD format)"),
    query_type: Optional[str] = FastAPIQuery(default=None, description="Filter by query type (text/image)"),
    exclude_ips: Optional[str] = FastAPIQuery(
        default=None, description="Comma-separated list of IP addresses to exclude (anonymized hashes)"
    ),
) -> Dict[str, Any]:
    """
    Retrieve query logs with optional filtering.

    Requires admin session authentication.

    Query Parameters:
    - limit: Maximum number of logs to return (1-1000, default: 100)
    - start_date: Start date filter in YYYY-MM-DD format
    - end_date: End date filter in YYYY-MM-DD format
    - query_type: Filter by query type (text/image)
    - exclude_ips: Comma-separated list of IP addresses to exclude (anonymized hashes)
    """
    logger = get_query_logger()

    # Validate date formats if provided
    if start_date:
        try:
            _sd = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            start_date = _sd.isoformat()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD format.")

    if end_date:
        try:
            # Add time component to include the entire end date
            _ed = datetime.strptime(end_date + " 23:59:59", "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            end_date = _ed.isoformat()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD format.")

    # Validate query type
    if query_type and query_type not in ["text", "image"]:
        raise HTTPException(status_code=400, detail="Invalid query_type. Must be 'text' or 'image'.")

    logs = logger.get_logs(
        limit=limit, start_date=start_date, end_date=end_date, query_type=query_type, exclude_ips=exclude_ips
    )

    return {
        "logs": logs,
        "count": len(logs),
        "filters": {
            "limit": limit,
            "start_date": start_date,
            "end_date": end_date,
            "query_type": query_type,
            "exclude_ips": exclude_ips,
        },
    }


@router.get("/query-logs/stats")
@limiter.limit("30/minute")  # Stats endpoint rate limit
async def get_query_log_stats(
    request: Request,
    session: dict = Depends(require_admin_auth),
    exclude_ips: Optional[str] = FastAPIQuery(
        default=None, description="Comma-separated list of IPs to exclude from stats"
    ),
) -> Dict[str, Any]:
    """
    Get statistics about query logs.

    Requires admin session authentication.

    Returns summary statistics including:
    - Total number of queries
    - Unique IP count
    - Query type breakdown
    - Model usage breakdown
    - Date range of logs

    Query Parameters:
    - exclude_ips: Comma-separated list of IPs to exclude from statistics
    """
    logger = get_query_logger()
    stats = logger.get_log_stats(exclude_ips=exclude_ips)

    return {"stats": stats, "generated_at": datetime.now(timezone.utc).isoformat(), "excluded_ips": exclude_ips}


@router.delete("/query-logs")
@limiter.limit("5/minute")  # Restrictive rate limit for destructive operations
async def clear_query_logs(request: Request, session: dict = Depends(require_admin_auth)) -> Dict[str, Any]:
    """
    Clear all query logs (use with caution).

    Requires admin session authentication.

    This action is irreversible and will delete all logged queries.
    """
    logger = get_query_logger()
    success = logger.clear_logs()

    if success:
        return {"message": "Query logs cleared successfully", "cleared_at": datetime.now(timezone.utc).isoformat()}
    else:
        raise HTTPException(status_code=500, detail="Failed to clear query logs")


@router.get("/query-logs/download")
async def download_query_logs(session: dict = Depends(require_admin_auth)) -> Dict[str, Any]:
    """
    Export query logs from SQLite database as JSON.

    Requires admin session authentication.

    Returns all logs from SQLite database in JSON format.
    For large datasets, consider adding pagination or streaming.
    """
    logger = get_query_logger()

    # Get all logs from SQLite database
    logs = logger.get_logs(limit=None)  # Get all logs

    if not logs:
        raise HTTPException(status_code=404, detail="No logs found in database")

    # Return as JSON response
    return {"logs": logs, "count": len(logs), "exported_at": datetime.now(timezone.utc).isoformat(), "format": "json"}


@router.get("/query-logs/health")
async def query_logs_health() -> Dict[str, Any]:
    """
    Health check endpoint for query logging system.

    This endpoint does not require authentication and can be used to verify
    that the query logging system is operational.
    """
    logger = get_query_logger()

    try:
        # Test basic functionality
        stats = logger.get_log_stats()

        # Check if SQLite database exists
        from pathlib import Path

        db_path = Path(logger.sqlite_db_path) if hasattr(logger, "sqlite_db_path") else None
        db_exists = db_path.exists() if db_path else False

        return {
            "status": "healthy",
            "database_exists": db_exists,
            "database_path": str(db_path) if db_path else "unknown",
            "total_logs": stats.get("total_queries", 0),
            "excluded_ips_count": len(logger.excluded_ips),
            "auth_method": "session-based",
            "storage_type": "sqlite",
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@router.get("/query-logs/admin", response_class=HTMLResponse)
async def query_logs_admin_page(request: Request) -> HTMLResponse:
    """
    Serve the query logs admin web interface.

    This endpoint serves a web interface for managing query logs.
    No authentication required for serving the page (auth happens via API calls).
    """
    # Get the client IP address
    client_ip = request.client.host if request.client else "127.0.0.1"

    # Get query logger to access anonymization method
    logger = get_query_logger()

    # Calculate anonymized IP hashes for the current user
    my_ip_hash = logger.anonymize_ip(client_ip)
    my_local_ip_hash = logger.anonymize_ip("127.0.0.1")  # Always include localhost

    # Render template with dynamic values
    return templates.TemplateResponse(
        "query_logs_admin.html", {"request": request, "my_ip_hash": my_ip_hash, "my_local_ip_hash": my_local_ip_hash}
    )
