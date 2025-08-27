"""
Shared database utilities for SQLite connections.

This module provides centralized database connection management
to avoid code duplication across route handlers.
"""

import logging
import sqlite3
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def get_rag_monitoring_db_connection() -> Optional[sqlite3.Connection]:
    """
    Get database connection to the RAG monitoring SQLite database.

    Returns:
        sqlite3.Connection with row_factory set to sqlite3.Row for dict-like access,
        or None if connection fails or database doesn't exist.
    """
    db_path = "backend/logs/rag_monitoring.db"
    if not Path(db_path).exists():
        logger.warning(f"Database not found at {db_path}, returning empty results")
        return None

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to RAG monitoring database: {e}")
        return None
