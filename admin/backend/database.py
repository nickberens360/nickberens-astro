"""
SQLite database setup and connection management for the RAG admin dashboard.

This module provides two database managers:
1. DatabaseManager - Admin-specific database for user management, settings, etc.
2. QueryDataManager - Read-only access to query data from the backend database.
"""

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional


class DatabaseManager:
    """Manages admin-specific SQLite database for user management and settings."""

    def __init__(self, db_path: str = None):
        if db_path is None:
            # Use admin-specific database for admin features
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            db_path = os.path.join(project_root, "admin", "admin_monitoring.db")
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize the admin database with admin-specific tables only.

        Note: Query data is now read from the backend database.
        This database handles admin-specific features like user management.
        """
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Admin users table (for future admin user management)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS admin_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT DEFAULT 'viewer',
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_login_at DATETIME
                )
            """
            )

            # User sessions (for admin session management)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS admin_sessions (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER,
                    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_active_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    ip_address TEXT,
                    user_agent TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES admin_users (id)
                )
            """
            )

            # Note: content_gaps table moved to backend database for real-time detection

            # Admin settings/configuration
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS admin_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    description TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_by INTEGER,
                    FOREIGN KEY (updated_by) REFERENCES admin_users (id)
                )
            """
            )

            # Create indexes for admin tables
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_admin_sessions_active ON admin_sessions(last_active_at DESC)"
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_admin_sessions_user ON admin_sessions(user_id)")

            conn.commit()

    @contextmanager
    def get_connection(self):
        """Get a database connection with automatic cleanup."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    # Admin-specific methods for user management, settings, etc.

    def create_admin_user(self, username: str, email: str, password_hash: str, role: str = "viewer") -> int:
        """Create a new admin user."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO admin_users (username, email, password_hash, role)
                VALUES (?, ?, ?, ?)
                """,
                (username, email, password_hash, role),
            )
            conn.commit()
            return cursor.lastrowid

    def get_admin_user(self, username: str) -> Optional[Dict[str, Any]]:
        """Get admin user by username."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM admin_users WHERE username = ? AND is_active = 1", (username,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_setting(self, key: str, value: str, description: str = None, updated_by: int = None):
        """Update or create an admin setting."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO admin_settings (key, value, description, updated_by)
                VALUES (?, ?, ?, ?)
                """,
                (key, value, description, updated_by),
            )
            conn.commit()

    def get_setting(self, key: str) -> Optional[str]:
        """Get an admin setting value."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM admin_settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row[0] if row else None

    def log_query(
        self,
        session_id: Optional[str] = None,
        user_query: str = "",
        system_response: str = "",
        response_time_ms: float = 0.0,
        llm_provider: Optional[str] = None,
        llm_model: Optional[str] = None,
        vector_search_score: Optional[float] = None,
        sources_used: Optional[List[str]] = None,
        follow_up_questions: Optional[List[str]] = None,
        cache_hit: bool = False,
        error_occurred: bool = False,
        error_message: Optional[str] = None,
    ) -> int:
        """Log a query to the admin database. This method delegates to the backend database."""
        # This should actually write to the backend database, not the admin database
        # For now, we'll return a dummy ID since the real logging happens in the backend
        import logging

        logging.getLogger(__name__).warning(
            "log_query called on DatabaseManager - this should use QueryDataManager instead"
        )
        return -1

    def update_session(self, session_id: str, user_agent: Optional[str] = None, ip_address: Optional[str] = None):
        """Update session information."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO admin_sessions 
                (id, user_agent, ip_address, last_active_at, is_active)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, 1)
                """,
                (session_id, user_agent, ip_address),
            )
            conn.commit()


class QueryDataManager:
    """Manages read-only access to query data from the backend database."""

    def __init__(self, backend_db_path: str = None):
        if backend_db_path is None:
            # Point to the backend database where actual query data is stored
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            backend_db_path = os.path.join(project_root, "backend", "logs", "rag_monitoring.db")
        self.backend_db_path = backend_db_path

    @contextmanager
    def get_connection(self):
        """Get a connection to the backend database."""
        conn = sqlite3.connect(self.backend_db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def get_queries(
        self,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "timestamp",
        sort_order: str = "desc",
        session_id: Optional[str] = None,
        error_filter: Optional[bool] = None,
        search_query: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get queries with filtering and pagination from backend database."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Build WHERE clause
                where_conditions = []
                params = []

                if session_id:
                    where_conditions.append("session_id = ?")
                    params.append(session_id)

                if error_filter is not None:
                    where_conditions.append("error_occurred = ?")
                    params.append(error_filter)

                if search_query:
                    where_conditions.append("(user_query LIKE ? OR system_response LIKE ?)")
                    params.extend([f"%{search_query}%", f"%{search_query}%"])

                if date_from:
                    where_conditions.append("timestamp >= ?")
                    params.append(date_from)

                if date_to:
                    where_conditions.append("timestamp <= ?")
                    params.append(date_to)

                where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

                # Get total count
                count_query = f"SELECT COUNT(*) FROM query_logs WHERE {where_clause}"
                cursor.execute(count_query, params)
                total_count = cursor.fetchone()[0]

                # Build main query
                valid_sort_columns = ["timestamp", "response_time_ms", "llm_model", "error_occurred"]
                sort_column = sort_by if sort_by in valid_sort_columns else "timestamp"
                sort_direction = "DESC" if sort_order.upper() == "DESC" else "ASC"

                main_query = f"""
                    SELECT * FROM query_logs 
                    WHERE {where_clause}
                    ORDER BY {sort_column} {sort_direction}
                    LIMIT ? OFFSET ?
                """
                params.extend([limit, offset])

                cursor.execute(main_query, params)
                queries = [dict(row) for row in cursor.fetchall()]

                # Process the results
                for query in queries:
                    # Parse JSON fields
                    if query.get("sources_used"):
                        try:
                            query["sources_used"] = json.loads(query["sources_used"])
                        except json.JSONDecodeError:
                            query["sources_used"] = []

                    if query.get("follow_up_questions"):
                        try:
                            query["follow_up_questions"] = json.loads(query["follow_up_questions"])
                        except json.JSONDecodeError:
                            query["follow_up_questions"] = []

                return {
                    "queries": queries,
                    "total": total_count,
                    "page": (offset // limit) + 1,
                    "per_page": limit,
                    "has_more": offset + limit < total_count,
                }

        except Exception as e:
            print(f"Database error in get_queries: {e}")
            return {"queries": [], "total": 0, "page": 1, "per_page": limit, "has_more": False}

    def get_overview_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get overview statistics for the dashboard from backend database."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Main stats
                cursor.execute(
                    """
                SELECT 
                    COUNT(*) as total_queries,
                    AVG(response_time_ms) as avg_response_time,
                    AVG(CASE WHEN error_occurred THEN 1.0 ELSE 0.0 END) as error_rate,
                    AVG(CASE WHEN cache_hit THEN 1.0 ELSE 0.0 END) as cache_hit_rate,
                    AVG(CASE WHEN user_feedback = 'helpful' THEN 1.0 
                             WHEN user_feedback = 'not_helpful' THEN 0.0 
                             ELSE NULL END) as helpful_rate
                FROM query_logs 
                WHERE timestamp >= datetime('now', '-' || ? || ' days')
            """,
                    (days,),
                )

                stats = dict(cursor.fetchone())

                # Unique sessions
                cursor.execute(
                    """
                SELECT COUNT(DISTINCT session_id) as unique_sessions
                FROM query_logs 
                WHERE timestamp >= datetime('now', '-' || ? || ' days') AND session_id IS NOT NULL
            """,
                    (days,),
                )

                stats["unique_sessions"] = cursor.fetchone()[0]

                # Queries today
                cursor.execute(
                    """
                SELECT COUNT(*) FROM query_logs 
                WHERE date(timestamp) = date('now')
            """
                )

                stats["queries_today"] = cursor.fetchone()[0]

                # Popular models
                cursor.execute(
                    """
                SELECT llm_model, COUNT(*) as count 
                FROM query_logs 
                WHERE timestamp >= datetime('now', '-' || ? || ' days')
                  AND llm_model IS NOT NULL
                GROUP BY llm_model 
                ORDER BY count DESC 
                LIMIT 5
            """,
                    (days,),
                )

                stats["popular_models"] = [{"model": row[0], "count": row[1]} for row in cursor.fetchall()]

                return stats

        except Exception as e:
            print(f"Database error in get_overview_stats: {e}")
            return {}

    def get_performance_metrics(self, time_range: str = "7d") -> Dict[str, Any]:
        """Get performance metrics for a given time range from backend database."""
        try:
            # Convert time range to SQL clause
            if time_range == "24h":
                time_clause = "1 day"
            elif time_range == "7d":
                time_clause = "7 days"
            elif time_range == "30d":
                time_clause = "30 days"
            else:
                time_clause = "7 days"

            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Get basic metrics
                cursor.execute(
                    """
                SELECT 
                    AVG(response_time_ms) as avg_response_time,
                    COUNT(*) as total_queries,
                    SUM(CASE WHEN error_occurred THEN 1 ELSE 0 END) as error_count,
                    SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) as cache_hits
                FROM query_logs 
                WHERE timestamp >= datetime('now', '-' || ?)
            """,
                    (time_clause,),
                )

                result = dict(cursor.fetchone())

                # Calculate percentiles more efficiently using SQL
                cursor.execute(
                    """
                    SELECT COUNT(*) 
                    FROM query_logs 
                    WHERE timestamp >= datetime('now', '-' || ?) AND response_time_ms IS NOT NULL
                """,
                    (time_clause,),
                )

                total_count = cursor.fetchone()[0]

                if total_count > 0:
                    # Calculate percentile positions using proper percentile formula
                    p50_pos = max(0, int(0.5 * (total_count - 1)))
                    p95_pos = max(0, int(0.95 * (total_count - 1)))
                    p99_pos = max(0, int(0.99 * (total_count - 1)))

                    # Use LIMIT and OFFSET to get specific percentile values
                    for percentile, pos in [("p50", p50_pos), ("p95", p95_pos), ("p99", p99_pos)]:
                        cursor.execute(
                            """
                            SELECT response_time_ms 
                            FROM query_logs 
                            WHERE timestamp >= datetime('now', '-' || ?) AND response_time_ms IS NOT NULL
                            ORDER BY response_time_ms
                            LIMIT 1 OFFSET ?
                        """,
                            (time_clause, pos),
                        )
                        result_row = cursor.fetchone()
                        result[f"{percentile}_response_time"] = result_row[0] if result_row else 0
                else:
                    result["p50_response_time"] = 0
                    result["p95_response_time"] = 0
                    result["p99_response_time"] = 0

                # Calculate rates
                result["error_rate"] = (
                    result["error_count"] / max(result["total_queries"], 1) if result["total_queries"] > 0 else 0
                )
                result["cache_hit_rate"] = (
                    result["cache_hits"] / max(result["total_queries"], 1) if result["total_queries"] > 0 else 0
                )

                return result

        except Exception as e:
            print(f"Database error in get_performance_metrics: {e}")
            return {}

    def get_timeline_data(self, days: int = 7, interval: str = "day") -> List[Dict[str, Any]]:
        """Get timeline data for charts from backend database."""
        try:
            # Determine the date format based on interval
            if interval == "hour":
                sql_format = "strftime('%Y-%m-%d %H', timestamp)"
                time_range = f"{days * 24} hours"
            else:  # day
                sql_format = "date(timestamp)"
                time_range = f"{days} days"

            with self.get_connection() as conn:
                cursor = conn.cursor()

                query = f"""
                SELECT 
                    {sql_format} as period,
                    COUNT(*) as queries,
                    AVG(response_time_ms) as avg_response_time,
                    SUM(CASE WHEN error_occurred THEN 1 ELSE 0 END) as errors,
                    SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) as cache_hits
                FROM query_logs 
                WHERE timestamp >= datetime('now', '-{time_range}')
                GROUP BY {sql_format}
                ORDER BY period ASC
                """

                cursor.execute(query)
                return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            print(f"Database error in get_timeline_data: {e}")
            return []

    def log_query(
        self,
        session_id: Optional[str] = None,
        user_query: str = "",
        system_response: str = "",
        response_time_ms: float = 0.0,
        llm_provider: Optional[str] = None,
        llm_model: Optional[str] = None,
        vector_search_score: Optional[float] = None,
        sources_used: Optional[List[str]] = None,
        follow_up_questions: Optional[List[str]] = None,
        cache_hit: bool = False,
        error_occurred: bool = False,
        error_message: Optional[str] = None,
    ) -> int:
        """Log a query to the backend database."""
        try:
            # Ensure the backend database directory exists
            os.makedirs(os.path.dirname(self.backend_db_path), exist_ok=True)

            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Create the query_logs table if it doesn't exist
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS query_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT,
                        user_query TEXT NOT NULL,
                        system_response TEXT,
                        response_time_ms REAL,
                        llm_provider TEXT,
                        llm_model TEXT,
                        vector_search_score REAL,
                        sources_used TEXT,  -- JSON array
                        follow_up_questions TEXT,  -- JSON array  
                        cache_hit BOOLEAN DEFAULT 0,
                        error_occurred BOOLEAN DEFAULT 0,
                        error_message TEXT,
                        user_feedback TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # Create indexes
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_query_logs_timestamp ON query_logs(timestamp DESC)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_query_logs_session ON query_logs(session_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_query_logs_error ON query_logs(error_occurred)")

                # Insert the query log
                cursor.execute(
                    """
                    INSERT INTO query_logs 
                    (session_id, user_query, system_response, response_time_ms, llm_provider, 
                     llm_model, vector_search_score, sources_used, follow_up_questions, 
                     cache_hit, error_occurred, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        user_query,
                        system_response,
                        response_time_ms,
                        llm_provider,
                        llm_model,
                        vector_search_score,
                        json.dumps(sources_used) if sources_used else None,
                        json.dumps(follow_up_questions) if follow_up_questions else None,
                        cache_hit,
                        error_occurred,
                        error_message,
                    ),
                )

                conn.commit()
                return cursor.lastrowid

        except Exception as e:
            print(f"Database error in log_query: {e}")
            return -1


# Global instances
db_manager = DatabaseManager()
query_data_manager = QueryDataManager()
