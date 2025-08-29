"""
Query logging service factory.

This module provides a factory function to get the query logger instance,
which uses SQLite database for persistent storage of query logs.
"""

from typing import Any, Optional

# Global instance
_query_logger_instance: Optional[Any] = None


def get_query_logger() -> Any:
    """
    Get the global SQLiteQueryLogger instance.

    Returns:
        SQLiteQueryLogger: The singleton query logger instance that logs to SQLite database
    """
    global _query_logger_instance
    if _query_logger_instance is None:
        # Import here to avoid circular imports
        from .sqlite_query_logger import SQLiteQueryLogger

        _query_logger_instance = SQLiteQueryLogger()
    return _query_logger_instance
