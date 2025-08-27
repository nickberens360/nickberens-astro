"""
Query data manager for admin dashboard access to query logs.
Migrated from admin/backend/database.py with improvements.
"""

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class QueryDataManager:
    """Manages read-only access to query logs database for admin dashboard."""

    def __init__(self):
        """Initialize the query data manager."""
        # Use backend/logs directory for query database
        self.db_path = Path(__file__).parent.parent / "logs" / "rag_monitoring.db"
        self.db_path.parent.mkdir(exist_ok=True)
        self._initialize_database()

    @contextmanager
    def get_connection(self):
        """Get a database connection with proper cleanup."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _initialize_database(self):
        """Initialize database tables if they don't exist."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Query logs table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS query_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT,
                        user_query TEXT NOT NULL,
                        response_text TEXT,
                        response_time_ms REAL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        llm_provider TEXT,
                        llm_model TEXT,
                        vector_search_score REAL,
                        sources_used TEXT,
                        error_occurred INTEGER DEFAULT 0,
                        error_message TEXT,
                        cache_hit INTEGER DEFAULT 0,
                        user_feedback TEXT,
                        follow_up_questions TEXT,
                        user_location_city TEXT,
                        user_location_region TEXT,
                        user_location_country TEXT
                    )
                """
                )

                # Content gaps table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS content_gaps (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        query_pattern TEXT NOT NULL,
                        occurrence_count INTEGER DEFAULT 1,
                        avg_similarity_score REAL,
                        first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        sample_query_id INTEGER,
                        resolved INTEGER DEFAULT 0,
                        notes TEXT,
                        FOREIGN KEY (sample_query_id) REFERENCES query_logs (id)
                    )
                """
                )

                # User sessions table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS user_sessions (
                        session_id TEXT PRIMARY KEY,
                        first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        query_count INTEGER DEFAULT 0,
                        user_location_city TEXT,
                        user_location_region TEXT,
                        user_location_country TEXT
                    )
                """
                )

                # Create indices for performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_query_logs_timestamp ON query_logs(timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_query_logs_session_id ON query_logs(session_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_query_logs_error ON query_logs(error_occurred)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_gaps_resolved ON content_gaps(resolved)")

                logger.info("Query data manager database initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing query data manager database: {str(e)}", exc_info=True)
            raise

    def get_overview_stats(self, days: int = 7) -> Dict[str, Any]:
        """Get overview statistics for the specified number of days, including comparison with previous period."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Get date ranges - current and previous period
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                prev_end_date = start_date
                prev_start_date = prev_end_date - timedelta(days=days)

                # Helper function to calculate percentage change
                def calculate_change(current, previous):
                    if previous == 0:
                        return 0.0 if current == 0 else 100.0
                    return round(((current - previous) / previous) * 100, 1)

                # Total queries - current and previous
                cursor.execute(
                    "SELECT COUNT(*) FROM query_logs WHERE timestamp >= ? AND timestamp < ?", (start_date, end_date)
                )
                total_queries = cursor.fetchone()[0]
                cursor.execute(
                    "SELECT COUNT(*) FROM query_logs WHERE timestamp >= ? AND timestamp < ?",
                    (prev_start_date, prev_end_date),
                )
                prev_total_queries = cursor.fetchone()[0]

                # Unique sessions - current and previous
                cursor.execute(
                    "SELECT COUNT(DISTINCT session_id) FROM query_logs WHERE timestamp >= ? AND timestamp < ?",
                    (start_date, end_date),
                )
                unique_sessions = cursor.fetchone()[0]
                cursor.execute(
                    "SELECT COUNT(DISTINCT session_id) FROM query_logs WHERE timestamp >= ? AND timestamp < ?",
                    (prev_start_date, prev_end_date),
                )
                prev_unique_sessions = cursor.fetchone()[0]

                # Average response time - current and previous
                cursor.execute(
                    "SELECT AVG(response_time_ms) FROM query_logs WHERE timestamp >= ? AND timestamp < ? AND response_time_ms IS NOT NULL",
                    (start_date, end_date),
                )
                avg_response_time = cursor.fetchone()[0] or 0
                cursor.execute(
                    "SELECT AVG(response_time_ms) FROM query_logs WHERE timestamp >= ? AND timestamp < ? AND response_time_ms IS NOT NULL",
                    (prev_start_date, prev_end_date),
                )
                prev_avg_response_time = cursor.fetchone()[0] or 0

                # Error rate - current and previous
                cursor.execute(
                    """
                    SELECT
                        CAST(SUM(error_occurred) AS REAL) / CAST(COUNT(*) AS REAL) * 100 as error_rate
                    FROM query_logs
                    WHERE timestamp >= ? AND timestamp < ?
                    """,
                    (start_date, end_date),
                )
                error_rate = cursor.fetchone()[0] or 0
                cursor.execute(
                    """
                    SELECT
                        CAST(SUM(error_occurred) AS REAL) / CAST(COUNT(*) AS REAL) * 100 as error_rate
                    FROM query_logs
                    WHERE timestamp >= ? AND timestamp < ?
                    """,
                    (prev_start_date, prev_end_date),
                )
                prev_error_rate = cursor.fetchone()[0] or 0

                # Cache hit rate - current and previous
                cursor.execute(
                    """
                    SELECT
                        CAST(SUM(cache_hit) AS REAL) / CAST(COUNT(*) AS REAL) * 100 as cache_hit_rate
                    FROM query_logs
                    WHERE timestamp >= ? AND timestamp < ?
                    """,
                    (start_date, end_date),
                )
                cache_hit_rate = cursor.fetchone()[0] or 0
                cursor.execute(
                    """
                    SELECT
                        CAST(SUM(cache_hit) AS REAL) / CAST(COUNT(*) AS REAL) * 100 as cache_hit_rate
                    FROM query_logs
                    WHERE timestamp >= ? AND timestamp < ?
                    """,
                    (prev_start_date, prev_end_date),
                )
                prev_cache_hit_rate = cursor.fetchone()[0] or 0

                # Helpful rate (queries with positive feedback) - current and previous
                cursor.execute(
                    """
                    SELECT
                        CAST(SUM(CASE WHEN user_feedback = 'helpful' THEN 1 ELSE 0 END) AS REAL) /
                        CAST(COUNT(*) AS REAL) * 100 as helpful_rate
                    FROM query_logs
                    WHERE timestamp >= ? AND timestamp < ? AND user_feedback IS NOT NULL
                    """,
                    (start_date, end_date),
                )
                helpful_rate = cursor.fetchone()[0] or 0
                cursor.execute(
                    """
                    SELECT
                        CAST(SUM(CASE WHEN user_feedback = 'helpful' THEN 1 ELSE 0 END) AS REAL) /
                        CAST(COUNT(*) AS REAL) * 100 as helpful_rate
                    FROM query_logs
                    WHERE timestamp >= ? AND timestamp < ? AND user_feedback IS NOT NULL
                    """,
                    (prev_start_date, prev_end_date),
                )
                prev_helpful_rate = cursor.fetchone()[0] or 0

                # Queries today
                today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                cursor.execute("SELECT COUNT(*) FROM query_logs WHERE timestamp >= ?", (today_start,))
                queries_today = cursor.fetchone()[0]

                # Queries this week
                week_start = datetime.now() - timedelta(days=7)
                cursor.execute("SELECT COUNT(*) FROM query_logs WHERE timestamp >= ?", (week_start,))
                queries_this_week = cursor.fetchone()[0]

                return {
                    "total_queries": total_queries,
                    "unique_sessions": unique_sessions,
                    "avg_response_time": avg_response_time,
                    "error_rate": error_rate,
                    "cache_hit_rate": cache_hit_rate,
                    "helpful_rate": helpful_rate,
                    "queries_today": queries_today,
                    "queries_this_week": queries_this_week,
                    # Comparison data for percentage calculations
                    "total_queries_change": calculate_change(total_queries, prev_total_queries),
                    "unique_sessions_change": calculate_change(unique_sessions, prev_unique_sessions),
                    "avg_response_time_change": calculate_change(avg_response_time, prev_avg_response_time),
                    "error_rate_change": calculate_change(error_rate, prev_error_rate),
                    "cache_hit_rate_change": calculate_change(cache_hit_rate, prev_cache_hit_rate),
                    "helpful_rate_change": calculate_change(helpful_rate, prev_helpful_rate),
                }

        except Exception as e:
            logger.error(f"Error getting overview stats: {str(e)}", exc_info=True)
            return {}

    def get_queries(
        self,
        limit: int = 50,
        offset: int = 0,
        search_query: Optional[str] = None,
        error_filter: bool = False,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get paginated list of queries with optional filters."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Build WHERE clause
                where_conditions = []
                params = []

                if search_query:
                    where_conditions.append("user_query LIKE ?")
                    params.append(f"%{search_query}%")

                if error_filter:
                    where_conditions.append("error_occurred = 1")

                if date_from:
                    where_conditions.append("timestamp >= ?")
                    params.append(date_from)

                if date_to:
                    where_conditions.append("timestamp <= ?")
                    params.append(date_to)

                where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""

                # Get total count
                cursor.execute(f"SELECT COUNT(*) FROM query_logs{where_clause}", params)
                total = cursor.fetchone()[0]

                # Get paginated results
                params.extend([str(limit), str(offset)])
                cursor.execute(
                    f"""
                    SELECT * FROM query_logs{where_clause}
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?
                """,
                    params,
                )

                queries = []
                for row in cursor.fetchall():
                    query_dict = dict(row)

                    # Map response for frontend compatibility
                    for key in ("response", "system_response", "response_text"):
                        if key in query_dict and query_dict.get(key) is not None:
                            query_dict["response"] = query_dict[key]
                            break

                    # Parse JSON fields safely
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

                    queries.append(query_dict)

                return {
                    "queries": queries,
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                    "has_more": (offset + limit) < total,
                }

        except Exception as e:
            logger.error(f"Error getting queries: {str(e)}", exc_info=True)
            return {"queries": [], "total": 0, "limit": limit, "offset": offset, "has_more": False}

    def get_performance_metrics(self, time_range: str = "24h") -> Dict[str, Any]:
        """Get performance metrics for the specified time range."""
        try:
            # Convert time range to hours
            time_mapping = {
                "1h": 1,
                "6h": 6,
                "24h": 24,
                "7d": 24 * 7,
                "30d": 24 * 30,
            }
            hours = time_mapping.get(time_range, 24)

            with self.get_connection() as conn:
                cursor = conn.cursor()

                start_time = datetime.now() - timedelta(hours=hours)

                # Get metrics
                cursor.execute(
                    """
                    SELECT
                        COUNT(*) as total_queries,
                        AVG(response_time_ms) as avg_response_time,
                        SUM(error_occurred) as error_count,
                        SUM(cache_hit) as cache_hits,
                        COUNT(DISTINCT session_id) as unique_sessions
                    FROM query_logs
                    WHERE timestamp >= ?
                    """,
                    (start_time,),
                )

                result = cursor.fetchone()
                if not result:
                    return {}

                total_queries = result[0] or 0
                avg_response_time = result[1] or 0
                error_count = result[2] or 0
                cache_hits = result[3] or 0
                unique_sessions = result[4] or 0

                cache_hit_rate = (cache_hits / max(total_queries, 1)) if total_queries > 0 else 0
                error_rate = (error_count / max(total_queries, 1)) if total_queries > 0 else 0

                return {
                    "total_queries": total_queries,
                    "avg_response_time": avg_response_time,
                    "error_count": error_count,
                    "error_rate": error_rate,
                    "cache_hit_rate": cache_hit_rate,
                    "unique_sessions": unique_sessions,
                    "p50_response_time": avg_response_time,  # Simplified for now
                    "p95_response_time": avg_response_time * 1.5,  # Simplified for now
                    "p99_response_time": avg_response_time * 2,  # Simplified for now
                }

        except Exception as e:
            logger.error(f"Error getting performance metrics: {str(e)}", exc_info=True)
            return {}


# Global query data manager instance
query_data_manager = QueryDataManager()
