"""
Shared database utilities for SQLite connections and path resolution.

This module provides centralized database connection management
and path resolution to avoid code duplication across route handlers.
"""

import logging
import os
import sqlite3
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def get_database_path(filename: str) -> Path:
    """
    Get the appropriate database path based on environment.

    Args:
        filename: The database filename (e.g., "admin_monitoring.db")

    Returns:
        Path: Full path to the database file

    In production (Railway), uses persistent volume at /data/
    In development, uses local backend/logs/ directory
    """
    if os.getenv("RAILWAY_ENVIRONMENT_NAME"):
        # Production: try persistent volume paths for Railway
        potential_paths = [
            Path("/data"),  # Standard Railway persistent volume mount
            Path("/app/data"),  # Alternative mount point
            # NOTE: /tmp is temporary storage - data will be lost on restart
            # NOTE: /app/backend/logs is ephemeral - gets overwritten on deployment
        ]

        base_path = None
        for path in potential_paths:
            try:
                # Test if we can create the directory and write to it
                path.mkdir(parents=True, exist_ok=True)
                test_file = path / ".write_test"
                test_file.write_text("test")
                test_file.unlink()  # Clean up test file
                base_path = path
                logger.info(f"Using database path: {path}")
                break
            except (PermissionError, OSError) as e:
                logger.warning(f"Cannot use path {path}: {e}")
                continue

        if base_path is None:
            raise RuntimeError(
                "No persistent volume found for database storage in Railway production environment. "
                "Please ensure Railway persistent volume is mounted at /data. "
                "Ephemeral storage (/tmp, /app/*) avoided to prevent data loss."
            )
    else:
        # Development: use local logs directory
        # Assumes this file is in backend/core/
        base_path = Path(__file__).parent.parent / "logs"

    # Ensure the directory exists
    try:
        base_path.mkdir(parents=True, exist_ok=True)
    except (PermissionError, OSError) as e:
        logger.error(f"Failed to create database directory {base_path}: {e}")
        raise

    return base_path / filename


def get_rag_monitoring_db_connection() -> Optional[sqlite3.Connection]:
    """
    Get database connection to the RAG monitoring SQLite database.

    Returns:
        sqlite3.Connection with row_factory set to sqlite3.Row for dict-like access,
        or None if connection fails or database doesn't exist.
    """
    db_path = get_database_path("rag_monitoring.db")
    if not db_path.exists():
        logger.warning(f"Database not found at {db_path}, returning empty results")
        return None

    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to RAG monitoring database: {e}")
        return None
