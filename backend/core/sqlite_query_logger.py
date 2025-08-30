"""
SQLite-only query logging service for tracking user queries and responses.

This module provides functionality to:
- Log user queries and AI responses directly to SQLite database
- Handle streaming responses by logging complete responses only
- Provide methods to read and search logs from database
- Avoid duplicate logging by using single insert per query
"""

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .config import AppConfig
from .geolocation_service import get_geolocation_service


class SQLiteQueryLogger:
    """Service for logging user queries and AI responses to SQLite database only."""

    def __init__(
        self,
        sqlite_db_path: Optional[str] = None,
        excluded_ips: Optional[Set[str]] = None,
    ) -> None:
        """
        Initialize the SQLiteQueryLogger.

        Args:
            sqlite_db_path: Path to the SQLite database
            excluded_ips: Set of IP addresses to exclude from logging
        """
        self.logger = logging.getLogger(__name__)

        # Set up SQLite database path - use absolute path for consistency
        if sqlite_db_path is None:
            # Compute absolute path relative to project root
            project_root = Path(__file__).parent.parent.parent
            sqlite_db_path = str(project_root / "backend" / "logs" / "rag_monitoring.db")
        self.sqlite_db_path = sqlite_db_path
        self._init_sqlite_database()

        # Set excluded IPs (can be loaded from config)
        self.excluded_ips = excluded_ips or set()

        # Load excluded IPs from environment if available
        config = AppConfig()
        try:
            excluded_ips_list = config.EXCLUDED_IPS
            if excluded_ips_list:
                self.excluded_ips.update(excluded_ips_list)
        except Exception as e:
            self.logger.warning("Failed to load excluded IPs: %s", e)

        # IP anonymization settings
        self.anonymize_ips = AppConfig.ANONYMIZE_IPS
        # Salt for IP hashing - should be kept secret and consistent
        try:
            self.ip_salt = config.IP_HASH_SALT
        except ValueError as e:
            # In production, this will raise if not set
            self.logger.error("Failed to get IP hash salt: %s", e)
            raise

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
                    request_id TEXT,
                    user_query TEXT NOT NULL,
                    system_response TEXT,
                    query_type TEXT DEFAULT 'text',
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
            # Check if columns exist
            cursor.execute("PRAGMA table_info(query_logs)")
            columns = [row[1] for row in cursor.fetchall()]

            # Define all columns that might need to be added
            required_columns = {
                "client_ip": "TEXT",
                "location_city": "TEXT",
                "location_region": "TEXT",
                "location_country": "TEXT",
                "location_country_code": "TEXT",
                "query_type": "TEXT DEFAULT 'text'",
                "request_id": "TEXT",
            }

            for column_name, column_type in required_columns.items():
                if column_name not in columns:
                    # Use parameterized query construction for safety
                    alter_query = f"ALTER TABLE query_logs ADD COLUMN {column_name} {column_type}"
                    cursor.execute(alter_query)
                    self.logger.info("Added missing column: %s", column_name)

        except Exception as e:
            self.logger.error("Failed to migrate schema: %s", e)

    @contextmanager
    def _get_sqlite_connection(self):
        """Get a SQLite database connection with automatic cleanup and optimized settings."""
        conn = sqlite3.connect(self.sqlite_db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row

        # Configure SQLite pragmas for better performance and reliability
        conn.execute("PRAGMA foreign_keys = ON")  # Enforce foreign key constraints
        conn.execute("PRAGMA journal_mode = WAL")  # Write-Ahead Logging for better concurrency
        conn.execute("PRAGMA synchronous = NORMAL")  # Balance between safety and performance

        try:
            yield conn
        finally:
            conn.close()

    def anonymize_ip(self, ip_address: str) -> str:
        """
        Anonymize an IP address using SHA-256 hashing with salt.

        Args:
            ip_address: The raw IP address to anonymize

        Returns:
            Anonymized IP address (16-character hash) or original if anonymization is disabled
        """
        if not self.anonymize_ips:
            return ip_address

        import hashlib

        # Combine IP with salt for better security
        salted_ip = f"{ip_address}{self.ip_salt}".encode("utf-8")

        # Create SHA-256 hash
        hash_object = hashlib.sha256(salted_ip)
        hash_hex = hash_object.hexdigest()

        # Return first 16 characters of hash for readability
        return f"anon_{hash_hex[:16]}"

    def should_log_ip(self, client_ip: str) -> bool:
        """
        Check if queries from this IP should be logged.

        Args:
            client_ip: The client's IP address (raw, not anonymized)

        Returns:
            True if the IP should be logged, False otherwise
        """
        return client_ip not in self.excluded_ips

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
        Log a query to SQLite database with full response.

        Args:
            client_ip: The client's IP address
            question: The user's question
            response: The AI's response (full response, not streaming placeholder)
            model_used: The model used for the response
            query_type: Type of query (text/image)
            response_time: Time taken to process the query
            metadata: Additional metadata
            request_id: Optional request ID
        """
        try:
            # Process IP address
            processed_ip = self._process_ip_for_logging(client_ip)
            if processed_ip is None:
                return  # IP was excluded

            # Get location data using original IP before anonymization
            geolocation_service = get_geolocation_service()
            location_data = {}
            if geolocation_service:
                try:
                    location_info = geolocation_service.get_location(client_ip)
                    if location_info:
                        location_data = {
                            "location_city": location_info.get("city"),
                            "location_region": location_info.get("region"),
                            "location_country": location_info.get("country_name"),
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

            # Get current UTC timestamp
            current_utc_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

            # Insert into database
            with self._get_sqlite_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO query_logs (
                        session_id, request_id, user_query, system_response, query_type, response_time_ms,
                        llm_provider, llm_model, vector_search_score, sources_used,
                        follow_up_questions, cache_hit, error_occurred, error_message,
                        client_ip, location_city, location_region, location_country, location_country_code, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        session_id,
                        request_id,
                        question,
                        response,
                        query_type,
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
                        current_utc_timestamp,
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
            is_content_gap = False

            # Check for content gaps based on various indicators
            if similarity_score is not None and similarity_score < AppConfig.LOW_SIMILARITY_THRESHOLD:
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

    # Compatibility methods for existing code
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
        Compatibility method - in SQLite-only logger, we don't log streaming placeholders.
        This is a no-op that will be replaced by full response logging.
        """
        # No-op: We don't log streaming placeholders, only full responses
        self.logger.debug("Streaming query logging skipped - will log full response when complete")

    def update_streaming_response(
        self,
        cache_key: str,
        client_ip: str,
        question: str,
        actual_response: str,
        request_id: Optional[str] = None,
        model_used: Optional[str] = None,
        response_time: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        In SQLite-only logger, we use this to log the complete response.
        This replaces the streaming placeholder approach with single full response logging.
        """
        # For compatibility, we'll log the complete response here
        # This method will be called from llm_chain.py with the full response
        try:
            # Merge cache-specific metadata with provided metadata
            combined_metadata = {
                "cache_key": cache_key,
                "response_updated": datetime.now(timezone.utc).isoformat(),
            }
            if metadata:
                combined_metadata.update(metadata)

            self.log_query(
                client_ip=client_ip,
                question=question,
                response=actual_response,
                model_used=model_used or "streaming_completion",
                query_type="text",
                response_time=response_time or 0.0,
                metadata=combined_metadata,
                request_id=request_id,
            )
            return True
        except Exception as e:
            self.logger.error("Failed to log streaming response completion: %s", e)
            return False

    # Additional methods for compatibility with admin dashboard
    def get_logs(
        self,
        limit: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        query_type: Optional[str] = None,
        exclude_ips: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve logs from SQLite database with optional filtering.
        """
        try:
            # Prepare excluded IPs set
            excluded_set = set()
            if exclude_ips:
                raw_excluded = set(ip.strip() for ip in exclude_ips.split(","))
                excluded_set = {self.anonymize_ip(ip) for ip in raw_excluded} if self.anonymize_ips else raw_excluded

            with self._get_sqlite_connection() as conn:
                cursor = conn.cursor()

                # Build query conditions
                conditions = []
                params = []

                if start_date:
                    conditions.append("timestamp >= ?")
                    params.append(start_date)
                if end_date:
                    conditions.append("timestamp <= ?")
                    params.append(end_date)
                if query_type:
                    conditions.append("query_type = ?")
                    params.append(query_type)
                if excluded_set:
                    placeholders = ",".join("?" * len(excluded_set))
                    conditions.append(f"client_ip NOT IN ({placeholders})")
                    params.extend(excluded_set)

                # Build query safely
                base_query = "SELECT * FROM query_logs"
                where_clause = ""
                if conditions:
                    where_clause = " WHERE " + " AND ".join(conditions)

                order_clause = " ORDER BY timestamp DESC"
                limit_clause = ""
                if limit and isinstance(limit, int) and limit > 0:
                    limit_clause = f" LIMIT {limit}"

                query = base_query + where_clause + order_clause + limit_clause
                cursor.execute(query, params)
                rows = cursor.fetchall()

                # Convert to list of dicts with proper data type conversion
                result = []
                for row in rows:
                    item = dict(row)

                    # Decode JSON fields if present
                    for key in ("sources_used", "follow_up_questions"):
                        val = item.get(key)
                        if isinstance(val, str) and val:
                            try:
                                item[key] = json.loads(val)
                            except json.JSONDecodeError:
                                # Keep as string if JSON parsing fails
                                pass

                    # Normalize booleans from SQLite (0/1 -> False/True)
                    for key in ("cache_hit", "error_occurred"):
                        if key in item and item[key] is not None:
                            item[key] = bool(item[key])

                    result.append(item)

                return result

        except Exception as e:
            self.logger.error("Failed to retrieve logs: %s", e)
            return []

    def get_log_stats(self, exclude_ips: Optional[str] = None) -> Dict[str, Any]:
        """Get statistics about the query logs from SQLite database."""
        try:
            excluded_set = set()
            if exclude_ips:
                raw_excluded = set(ip.strip() for ip in exclude_ips.split(","))
                excluded_set = {self.anonymize_ip(ip) for ip in raw_excluded} if self.anonymize_ips else raw_excluded

            with self._get_sqlite_connection() as conn:
                cursor = conn.cursor()

                # Build exclusion condition safely
                exclude_condition = ""
                params = []
                if excluded_set:
                    placeholders = ",".join("?" * len(excluded_set))
                    exclude_condition = f" WHERE client_ip NOT IN ({placeholders})"
                    params = list(excluded_set)

                # Get basic stats
                total_count_query = "SELECT COUNT(*) FROM query_logs" + exclude_condition
                cursor.execute(total_count_query, params)
                total_queries = cursor.fetchone()[0]

                if total_queries == 0:
                    return {"total_queries": 0}

                unique_ip_query = "SELECT COUNT(DISTINCT client_ip) FROM query_logs" + exclude_condition
                cursor.execute(unique_ip_query, params)
                unique_ips = cursor.fetchone()[0]

                date_range_query = "SELECT MIN(timestamp), MAX(timestamp) FROM query_logs" + exclude_condition
                cursor.execute(date_range_query, params)
                date_range = cursor.fetchone()

                # Get model usage stats
                model_stats_query = (
                    "SELECT llm_model, COUNT(*) FROM query_logs" + exclude_condition + " GROUP BY llm_model"
                )
                cursor.execute(model_stats_query, params)
                models_used = dict(cursor.fetchall())

                # Get query type stats
                query_type_query = (
                    "SELECT COALESCE(query_type, 'text') AS qt, COUNT(*) FROM query_logs"
                    + exclude_condition
                    + " GROUP BY qt"
                )
                cursor.execute(query_type_query, params)
                query_types = dict(cursor.fetchall())

                return {
                    "total_queries": total_queries,
                    "unique_ips": unique_ips,
                    "query_types": query_types,
                    "models_used": models_used,
                    "date_range": {
                        "earliest": date_range[0] or "",
                        "latest": date_range[1] or "",
                    },
                }

        except Exception as e:
            self.logger.error("Failed to get log stats: %s", e)
            return {"error": str(e)}

    def clear_logs(self) -> bool:
        """Clear all logs from SQLite database."""
        try:
            with self._get_sqlite_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM query_logs")
                cursor.execute("DELETE FROM content_gaps")
                conn.commit()
                return True
        except Exception as e:
            self.logger.error("Failed to clear logs: %s", e)
            return False
