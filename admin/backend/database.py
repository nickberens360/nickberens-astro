"""
SQLite database setup and connection management for the RAG admin dashboard.
"""

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional


class DatabaseManager:
    """Manages SQLite database connections and operations."""

    def __init__(self, db_path: str = None):
        if db_path is None:
            # Use absolute path to the backend database
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            db_path = os.path.join(project_root, "backend", "logs", "rag_monitoring.db")
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize the database with required tables."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Main query logging table
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
                    sources_used TEXT,
                    follow_up_questions TEXT,
                    cache_hit BOOLEAN DEFAULT 0,
                    error_occurred BOOLEAN DEFAULT 0,
                    error_message TEXT,
                    user_feedback TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    client_ip TEXT,
                    location_city TEXT,
                    location_region TEXT,
                    location_country TEXT,
                    location_country_code TEXT
                )
            """
            )

            # User sessions
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id TEXT PRIMARY KEY,
                    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_active_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    total_queries INTEGER DEFAULT 0,
                    user_agent TEXT,
                    ip_address TEXT
                )
            """
            )

            # Aggregated metrics (calculated every hour)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS hourly_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hour DATETIME,
                    total_queries INTEGER,
                    unique_sessions INTEGER,
                    avg_response_time_ms REAL,
                    p95_response_time_ms REAL,
                    cache_hit_rate REAL,
                    error_rate REAL,
                    helpful_rate REAL
                )
            """
            )

            # Content gaps tracking
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS content_gaps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query_pattern TEXT,
                    occurrence_count INTEGER DEFAULT 1,
                    avg_similarity_score REAL,
                    first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    resolved BOOLEAN DEFAULT 0
                )
            """
            )

            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_query_logs_timestamp ON query_logs(timestamp DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_query_logs_session ON query_logs(session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_query_logs_errors ON query_logs(error_occurred)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_active ON user_sessions(last_active_at DESC)")

            conn.commit()

    @contextmanager
    def get_connection(self):
        """Get a database connection with automatic cleanup."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
        try:
            yield conn
        finally:
            conn.close()

    def log_query(
        self,
        session_id: Optional[str],
        user_query: str,
        system_response: Optional[str] = None,
        response_time_ms: Optional[float] = None,
        llm_provider: Optional[str] = None,
        llm_model: Optional[str] = None,
        vector_search_score: Optional[float] = None,
        sources_used: Optional[List[str]] = None,
        follow_up_questions: Optional[List[str]] = None,
        cache_hit: bool = False,
        error_occurred: bool = False,
        error_message: Optional[str] = None,
        client_ip: Optional[str] = None,
        location_city: Optional[str] = None,
        location_region: Optional[str] = None,
        location_country: Optional[str] = None,
        location_country_code: Optional[str] = None,
    ) -> int:
        """Log a query to the database and return the query ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO query_logs (
                    session_id, user_query, system_response, response_time_ms,
                    llm_provider, llm_model, vector_search_score, sources_used,
                    follow_up_questions, cache_hit, error_occurred, error_message,
                    client_ip, location_city, location_region, location_country, location_country_code
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    client_ip,
                    location_city,
                    location_region,
                    location_country,
                    location_country_code,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def update_session(self, session_id: str, user_agent: Optional[str] = None, ip_address: Optional[str] = None):
        """Update or create a user session."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Try to update existing session
            cursor.execute(
                """
                UPDATE user_sessions 
                SET last_active_at = CURRENT_TIMESTAMP, total_queries = total_queries + 1
                WHERE id = ?
            """,
                (session_id,),
            )

            # If no rows affected, create new session
            if cursor.rowcount == 0:
                cursor.execute(
                    """
                    INSERT INTO user_sessions (id, user_agent, ip_address, total_queries)
                    VALUES (?, ?, ?, 1)
                """,
                    (session_id, user_agent, ip_address),
                )

            conn.commit()

    def get_queries(
        self,
        limit: int = 50,
        offset: int = 0,
        search: Optional[str] = None,
        errors_only: bool = False,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get paginated query logs with optional filters."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Build WHERE clause
            where_conditions = []
            params = []

            if search:
                where_conditions.append("(user_query LIKE ? OR system_response LIKE ?)")
                params.extend([f"%{search}%", f"%{search}%"])

            if errors_only:
                where_conditions.append("error_occurred = 1")

            if start_date:
                where_conditions.append("timestamp >= ?")
                params.append(start_date)

            if end_date:
                where_conditions.append("timestamp <= ?")
                params.append(end_date)

            where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""

            # Get total count
            cursor.execute(f"SELECT COUNT(*) FROM query_logs{where_clause}", params)
            total = cursor.fetchone()[0]

            # Get paginated results
            cursor.execute(
                f"""
                SELECT * FROM query_logs{where_clause}
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """,
                params + [limit, offset],
            )

            queries = []
            for row in cursor.fetchall():
                query_dict = dict(row)

                # Parse JSON fields
                if query_dict.get("sources_used"):
                    query_dict["sources_used"] = json.loads(query_dict["sources_used"])
                if query_dict.get("follow_up_questions"):
                    query_dict["follow_up_questions"] = json.loads(query_dict["follow_up_questions"])

                # Ensure location fields are included (in case they're missing from older records)
                location_fields = [
                    "client_ip",
                    "location_city",
                    "location_region",
                    "location_country",
                    "location_country_code",
                ]
                for field in location_fields:
                    if field not in query_dict:
                        query_dict[field] = None

                queries.append(query_dict)

            return {"queries": queries, "total": total, "page": offset // limit + 1, "per_page": limit}

    def get_overview_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get overview statistics for the dashboard."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Total queries and basic stats
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
                WHERE timestamp >= datetime('now', '-{} days')
            """.format(
                    days
                )
            )

            stats = dict(cursor.fetchone())

            # Unique sessions
            cursor.execute(
                """
                SELECT COUNT(DISTINCT session_id) as unique_sessions
                FROM query_logs 
                WHERE timestamp >= datetime('now', '-{} days') AND session_id IS NOT NULL
            """.format(
                    days
                )
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

            # Queries this week
            cursor.execute(
                """
                SELECT COUNT(*) FROM query_logs 
                WHERE timestamp >= datetime('now', '-7 days')
            """
            )
            stats["queries_this_week"] = cursor.fetchone()[0]

            return stats

    def update_query_feedback(self, query_id: int, feedback: str):
        """Update user feedback for a query."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE query_logs SET user_feedback = ? WHERE id = ?
            """,
                (feedback, query_id),
            )
            conn.commit()

    def get_performance_metrics(self, time_range: str = "24h") -> Dict[str, Any]:
        """Get performance metrics for the specified time range."""
        time_mapping = {"1h": "1 hours", "6h": "6 hours", "24h": "24 hours", "7d": "7 days", "30d": "30 days"}

        time_clause = time_mapping.get(time_range, "24 hours")

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT 
                    AVG(response_time_ms) as avg_response_time,
                    COUNT(*) as total_queries,
                    SUM(CASE WHEN error_occurred THEN 1 ELSE 0 END) as error_count,
                    SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) as cache_hits
                FROM query_logs 
                WHERE timestamp >= datetime('now', '-{}')
            """.format(
                    time_clause
                )
            )

            result = dict(cursor.fetchone())

            # Calculate percentiles more efficiently using SQL
            # Get count first to avoid loading all data
            cursor.execute(
                """
                SELECT COUNT(*) 
                FROM query_logs 
                WHERE timestamp >= datetime('now', '-{}') AND response_time_ms IS NOT NULL
            """.format(
                    time_clause
                )
            )

            total_count = cursor.fetchone()[0]

            if total_count > 0:
                # Calculate percentile positions
                p50_pos = max(1, int(total_count * 0.5))
                p95_pos = max(1, int(total_count * 0.95))
                p99_pos = max(1, int(total_count * 0.99))

                # Use LIMIT and OFFSET to get specific percentile values
                cursor.execute(
                    """
                    SELECT response_time_ms 
                    FROM query_logs 
                    WHERE timestamp >= datetime('now', '-{}') AND response_time_ms IS NOT NULL
                    ORDER BY response_time_ms
                    LIMIT 1 OFFSET {}
                """.format(
                        time_clause, p50_pos - 1
                    )
                )
                p50_result = cursor.fetchone()
                result["p50_response_time"] = p50_result[0] if p50_result else 0

                cursor.execute(
                    """
                    SELECT response_time_ms 
                    FROM query_logs 
                    WHERE timestamp >= datetime('now', '-{}') AND response_time_ms IS NOT NULL
                    ORDER BY response_time_ms
                    LIMIT 1 OFFSET {}
                """.format(
                        time_clause, p95_pos - 1
                    )
                )
                p95_result = cursor.fetchone()
                result["p95_response_time"] = p95_result[0] if p95_result else 0

                cursor.execute(
                    """
                    SELECT response_time_ms 
                    FROM query_logs 
                    WHERE timestamp >= datetime('now', '-{}') AND response_time_ms IS NOT NULL
                    ORDER BY response_time_ms
                    LIMIT 1 OFFSET {}
                """.format(
                        time_clause, p99_pos - 1
                    )
                )
                p99_result = cursor.fetchone()
                result["p99_response_time"] = p99_result[0] if p99_result else 0
            else:
                result["p50_response_time"] = 0
                result["p95_response_time"] = 0
                result["p99_response_time"] = 0

            result["cache_hit_rate"] = result["cache_hits"] / max(result["total_queries"], 1)

            return result

    def get_performance_metrics_previous(self, time_range: str = "24h") -> Dict[str, Any]:
        """Get performance metrics for the previous period (used for comparison)."""
        time_mapping = {
            "1h": ("2 hours", "1 hours"),
            "6h": ("12 hours", "6 hours"),
            "24h": ("2 days", "1 days"),
            "7d": ("14 days", "7 days"),
            "30d": ("60 days", "30 days"),
        }

        time_info = time_mapping.get(time_range, ("2 days", "1 days"))
        start_offset = time_info[0]
        end_offset = time_info[1]

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT 
                    AVG(response_time_ms) as avg_response_time,
                    COUNT(*) as total_queries,
                    SUM(CASE WHEN error_occurred THEN 1 ELSE 0 END) as error_count,
                    SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) as cache_hits
                FROM query_logs 
                WHERE timestamp >= datetime('now', '-{}') 
                  AND timestamp < datetime('now', '-{}')
            """.format(
                    start_offset, end_offset
                )
            )

            result = dict(cursor.fetchone())

            # Calculate percentiles more efficiently using SQL
            cursor.execute(
                """
                SELECT COUNT(*) 
                FROM query_logs 
                WHERE timestamp >= datetime('now', '-{}') 
                  AND timestamp < datetime('now', '-{}')
                  AND response_time_ms IS NOT NULL
            """.format(
                    start_offset, end_offset
                )
            )

            total_count = cursor.fetchone()[0]

            if total_count > 0:
                # Calculate percentile positions
                p50_pos = max(1, int(total_count * 0.5))
                p95_pos = max(1, int(total_count * 0.95))
                p99_pos = max(1, int(total_count * 0.99))

                # Use LIMIT and OFFSET to get specific percentile values
                cursor.execute(
                    """
                    SELECT response_time_ms 
                    FROM query_logs 
                    WHERE timestamp >= datetime('now', '-{}') 
                      AND timestamp < datetime('now', '-{}')
                      AND response_time_ms IS NOT NULL
                    ORDER BY response_time_ms
                    LIMIT 1 OFFSET {}
                """.format(
                        start_offset, end_offset, p50_pos - 1
                    )
                )
                p50_result = cursor.fetchone()
                result["p50_response_time"] = p50_result[0] if p50_result else 0

                cursor.execute(
                    """
                    SELECT response_time_ms 
                    FROM query_logs 
                    WHERE timestamp >= datetime('now', '-{}') 
                      AND timestamp < datetime('now', '-{}')
                      AND response_time_ms IS NOT NULL
                    ORDER BY response_time_ms
                    LIMIT 1 OFFSET {}
                """.format(
                        start_offset, end_offset, p95_pos - 1
                    )
                )
                p95_result = cursor.fetchone()
                result["p95_response_time"] = p95_result[0] if p95_result else 0

                cursor.execute(
                    """
                    SELECT response_time_ms 
                    FROM query_logs 
                    WHERE timestamp >= datetime('now', '-{}') 
                      AND timestamp < datetime('now', '-{}')
                      AND response_time_ms IS NOT NULL
                    ORDER BY response_time_ms
                    LIMIT 1 OFFSET {}
                """.format(
                        start_offset, end_offset, p99_pos - 1
                    )
                )
                p99_result = cursor.fetchone()
                result["p99_response_time"] = p99_result[0] if p99_result else 0
            else:
                result["p50_response_time"] = 0
                result["p95_response_time"] = 0
                result["p99_response_time"] = 0

            result["cache_hit_rate"] = (
                result["cache_hits"] / max(result["total_queries"], 1) if result["total_queries"] > 0 else 0
            )

            return result


# Global database manager instance
db_manager = DatabaseManager()
