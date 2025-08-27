"""
Enhanced query logging service that writes to both JSON and SQLite.

This module extends the original query logger to write to both:
1. JSON files (for backward compatibility and data export)
2. SQLite database (for real-time admin dashboard access)
"""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Optional, Set

from .geolocation_service import get_geolocation_service
from .query_logger import QueryLogger


class DualQueryLogger(QueryLogger):
    """Enhanced QueryLogger that writes to both JSON and SQLite."""

    def __init__(
        self,
        log_file_path: Optional[str] = None,
        excluded_ips: Optional[Set[str]] = None,
        sqlite_db_path: Optional[str] = None,
    ) -> None:
        """
        Initialize the DualQueryLogger.

        Args:
            log_file_path: Path to the JSON log file
            excluded_ips: Set of IP addresses to exclude from logging
            sqlite_db_path: Path to the SQLite database for admin dashboard
        """
        # Initialize parent JSON logger
        super().__init__(log_file_path, excluded_ips)

        # Set up SQLite database path - use absolute path for consistency with admin
        if sqlite_db_path is None:
            # Compute absolute path relative to project root using Path for better reliability
            project_root = Path(__file__).parent.parent.parent
            sqlite_db_path = str(project_root / "backend" / "logs" / "rag_monitoring.db")
        self.sqlite_db_path = sqlite_db_path
        self._init_sqlite_database()

    def _init_sqlite_database(self):
        """Initialize the SQLite database with required tables."""
        # Ensure directory exists
        Path(self.sqlite_db_path).parent.mkdir(parents=True, exist_ok=True)

        with self._get_sqlite_connection() as conn:
            cursor = conn.cursor()

            # Create query_logs table if it doesn't exist
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

            # Migrate existing tables - add location columns if missing
            self._migrate_schema(cursor)

            # Create content_gaps table for automatic content gap detection
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS content_gaps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query_pattern TEXT NOT NULL,
                    occurrence_count INTEGER DEFAULT 1,
                    avg_similarity_score REAL,
                    first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    resolved BOOLEAN DEFAULT 0,
                    notes TEXT,
                    sample_query_id INTEGER,
                    FOREIGN KEY (sample_query_id) REFERENCES query_logs (id)
                )
            """
            )

            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_query_logs_timestamp ON query_logs(timestamp DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_query_logs_errors ON query_logs(error_occurred)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_gaps_resolved ON content_gaps(resolved)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_gaps_score ON content_gaps(avg_similarity_score)")

            conn.commit()
            self.logger.info("SQLite database initialized at %s", self.sqlite_db_path)

    def _migrate_schema(self, cursor):
        """Migrate database schema to add missing columns."""
        try:
            # Check if location columns exist
            cursor.execute("PRAGMA table_info(query_logs)")
            columns = [row[1] for row in cursor.fetchall()]

            location_columns = [
                "client_ip",
                "location_city",
                "location_region",
                "location_country",
                "location_country_code",
            ]

            for column in location_columns:
                if column not in columns:
                    cursor.execute(f"ALTER TABLE query_logs ADD COLUMN {column} TEXT")
                    self.logger.info(f"Added missing column: {column}")

        except Exception as e:
            self.logger.error(f"Failed to migrate schema: {e}")

    @contextmanager
    def _get_sqlite_connection(self):
        """Get a SQLite database connection with automatic cleanup."""
        conn = sqlite3.connect(self.sqlite_db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def log_query(
        self,
        client_ip: str,
        question: str,
        response: str,
        model_used: str,
        query_type: str,
        response_time: float,
        metadata: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> None:
        """
        Log a query to both JSON file and SQLite database.

        Args:
            client_ip: The client's IP address
            question: The user's question
            response: The AI's response
            model_used: The model used for the response
            query_type: Type of query (text/image)
            response_time: Time taken to process the query
            metadata: Additional metadata
            request_id: Optional request ID
        """
        # Call parent method to log to JSON
        super().log_query(client_ip, question, response, model_used, query_type, response_time, metadata, request_id)

        # Also log to SQLite database
        self._log_to_sqlite(client_ip, question, response, model_used, query_type, response_time, metadata, request_id)

    def _log_to_sqlite(
        self,
        client_ip: str,
        question: str,
        response: str,
        model_used: str,
        query_type: str,
        response_time: float,
        metadata: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> None:
        """Log query to SQLite database."""
        try:
            # Process IP address
            processed_ip = self._process_ip_for_logging(client_ip)
            if processed_ip is None:
                return  # IP was excluded

            # Get location data
            geolocation_service = get_geolocation_service()
            location_data = {}
            if geolocation_service and not self.anonymize_ips:
                try:
                    location_info = geolocation_service.get_location(client_ip)
                    if location_info:
                        location_data = {
                            "location_city": location_info.get("city"),
                            "location_region": location_info.get("region"),
                            "location_country": location_info.get("country"),
                            "location_country_code": location_info.get("country_code"),
                        }
                except Exception as e:
                    self.logger.warning("Failed to get location data: %s", e)

            # Extract metadata
            metadata = metadata or {}
            vector_search_score = metadata.get("vector_search_score")
            sources_used = metadata.get("sources_used", [])
            follow_up_questions = metadata.get("follow_up_questions", [])
            cache_hit = metadata.get("cache_hit", False)
            error_occurred = metadata.get("error_occurred", False)
            error_message = metadata.get("error_message")
            session_id = metadata.get("session_id")

            # Convert response_time to milliseconds
            response_time_ms = response_time * 1000 if response_time else None

            # Insert into database
            with self._get_sqlite_connection() as conn:
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
                        question,
                        response,
                        response_time_ms,
                        self._infer_llm_provider(model_used),
                        model_used,
                        vector_search_score,
                        json.dumps(sources_used) if sources_used else None,
                        json.dumps(follow_up_questions) if follow_up_questions else None,
                        cache_hit,
                        error_occurred,
                        error_message,
                        processed_ip,
                        location_data.get("location_city"),
                        location_data.get("location_region"),
                        location_data.get("location_country"),
                        location_data.get("location_country_code"),
                    ),
                )
                conn.commit()
                query_id = cursor.lastrowid

                # Check for potential content gaps and log them automatically
                self._detect_content_gap(cursor, query_id, question, vector_search_score, error_occurred)

                conn.commit()  # Commit content gap detection too
                self.logger.debug("Query logged to SQLite database")

        except Exception as e:
            self.logger.error("Failed to log query to SQLite: %s", e)
            # Don't raise - we don't want to break the main application

    def log_streaming_query(
        self,
        client_ip: str,
        question: str,
        model_used: str,
        response_time: float,
        metadata: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> None:
        """
        Log a streaming query to both JSON file and SQLite database.

        Args:
            client_ip: The client's IP address
            question: The user's question
            model_used: The model used for the response
            response_time: Time taken to process the query
            metadata: Additional metadata
            request_id: Optional request ID
        """
        # Call parent method to log to JSON
        super().log_streaming_query(client_ip, question, model_used, response_time, metadata, request_id)

        # Also log to SQLite database with streaming response placeholder
        self._log_to_sqlite(
            client_ip, question, "[STREAMING RESPONSE]", model_used, "text", response_time, metadata, request_id
        )

    def update_streaming_response(
        self,
        cache_key: str,
        client_ip: str,
        question: str,
        actual_response: str,
        request_id: Optional[str] = None,
    ) -> bool:
        """
        Update a streaming response in both JSON and SQLite databases.

        Args:
            cache_key: The cache key used for the response
            client_ip: The client's IP address
            question: The user's question
            actual_response: The actual response content
            request_id: Optional request ID

        Returns:
            bool: True if update was successful
        """
        # Call parent method to update JSON
        json_success = super().update_streaming_response(cache_key, client_ip, question, actual_response, request_id)

        # Also update SQLite database
        sqlite_success = self._update_sqlite_streaming_response(client_ip, question, actual_response, request_id)

        return json_success and sqlite_success

    def _update_sqlite_streaming_response(
        self,
        client_ip: str,
        question: str,
        actual_response: str,
        request_id: Optional[str] = None,
    ) -> bool:
        """Update streaming response in SQLite database."""
        try:
            processed_ip = self._process_ip_for_logging(client_ip)
            if processed_ip is None:
                return True  # IP was excluded, but return success

            with self._get_sqlite_connection() as conn:
                cursor = conn.cursor()

                # Update the most recent matching entry with [STREAMING RESPONSE]
                # SQLite doesn't support ORDER BY in UPDATE, so we find the ID first
                cursor.execute(
                    """
                    SELECT id FROM query_logs 
                    WHERE user_query = ? AND system_response = '[STREAMING RESPONSE]'
                    ORDER BY id DESC LIMIT 1
                """,
                    (question,),
                )

                row = cursor.fetchone()
                if row:
                    entry_id = row[0]
                    cursor.execute(
                        """
                        UPDATE query_logs 
                        SET system_response = ?
                        WHERE id = ?
                    """,
                        (actual_response, entry_id),
                    )

                    conn.commit()

                    if cursor.rowcount > 0:
                        self.logger.debug("Updated streaming response in SQLite database for ID %s", entry_id)
                        return True
                    else:
                        self.logger.warning("Failed to update streaming entry with ID %s", entry_id)
                        return False
                else:
                    self.logger.warning(
                        "No matching streaming entry found to update in SQLite for question: %s", question[:50]
                    )
                    return False

        except Exception as e:
            self.logger.error("Failed to update streaming response in SQLite: %s", e)
            return False

    def _infer_llm_provider(self, model_name: Optional[str]) -> str:
        """Infer LLM provider from model name."""
        if not model_name:
            return "unknown"

        model_lower = model_name.lower()
        if "claude" in model_lower or "anthropic" in model_lower:
            return "anthropic"
        elif "gpt" in model_lower or "openai" in model_lower:
            return "openai"
        elif "gemini" in model_lower or "google" in model_lower:
            return "google"
        elif "llama" in model_lower:
            return "meta"
        else:
            return "unknown"

    def _detect_content_gap(
        self, cursor, query_id: int, question: str, similarity_score: Optional[float], error_occurred: bool
    ):
        """Detect and record potential content gaps based on query quality indicators."""
        try:
            # Define thresholds for content gap detection
            LOW_SIMILARITY_THRESHOLD = 0.7  # Configurable threshold
            is_content_gap = False

            # Check for content gaps based on various indicators
            if similarity_score is not None and similarity_score < LOW_SIMILARITY_THRESHOLD:
                is_content_gap = True
            elif error_occurred:
                is_content_gap = True
            elif not question.strip():  # Empty or whitespace-only queries
                return  # Skip empty queries

            if is_content_gap:
                # Normalize the query pattern (remove common variations)
                query_pattern = self._normalize_query_pattern(question)

                # Check if this pattern already exists
                cursor.execute(
                    "SELECT id, occurrence_count, avg_similarity_score FROM content_gaps WHERE query_pattern = ?",
                    (query_pattern,),
                )
                existing_gap = cursor.fetchone()

                if existing_gap:
                    # Update existing content gap
                    gap_id, count, avg_score = existing_gap
                    new_count = count + 1
                    new_avg_score = avg_score

                    if similarity_score is not None:
                        # Update running average
                        new_avg_score = ((avg_score * count) + similarity_score) / new_count

                    cursor.execute(
                        """
                        UPDATE content_gaps 
                        SET occurrence_count = ?, avg_similarity_score = ?, last_seen = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (new_count, new_avg_score, gap_id),
                    )
                else:
                    # Create new content gap entry
                    cursor.execute(
                        """
                        INSERT INTO content_gaps (
                            query_pattern, occurrence_count, avg_similarity_score, sample_query_id
                        ) VALUES (?, 1, ?, ?)
                        """,
                        (query_pattern, similarity_score or 0.0, query_id),
                    )

                self.logger.debug(f"Content gap detected: {query_pattern[:50]}...")

        except Exception as e:
            self.logger.error(f"Failed to detect content gap: {e}")
            # Don't raise - this is secondary functionality

    def _normalize_query_pattern(self, question: str) -> str:
        """Normalize a query to identify similar patterns."""
        import re

        # Basic normalization - can be enhanced
        pattern = question.lower().strip()

        # Remove common question words and patterns
        pattern = re.sub(r"^(what|how|when|where|why|who|can|could|would|should|is|are|do|does)\s+", "", pattern)

        # Remove specific names and numbers (basic approach)
        pattern = re.sub(r"\b\d+\b", "[NUMBER]", pattern)

        # Limit length for storage
        if len(pattern) > 200:
            pattern = pattern[:200] + "..."

        return pattern

    def _process_ip_for_logging(self, ip_address: str) -> Optional[str]:
        """Process IP address for logging, handling exclusion and anonymization."""
        if ip_address in self.excluded_ips:
            return None

        if self.anonymize_ips:
            return self.anonymize_ip(ip_address)
        else:
            return ip_address
