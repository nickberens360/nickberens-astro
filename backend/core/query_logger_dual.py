"""
Enhanced query logging service that writes to both JSON and SQLite.

This module extends the original query logger to write to both:
1. JSON files (for backward compatibility and data export)
2. SQLite database (for real-time admin dashboard access)
"""

import hashlib
import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .config import AppConfig
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

        # Set up SQLite database path - use backend/logs for container compatibility
        self.sqlite_db_path = sqlite_db_path or "backend/logs/rag_monitoring.db"
        self._init_sqlite_database()

    def _init_sqlite_database(self):
        """Initialize the SQLite database with required tables."""
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.sqlite_db_path), exist_ok=True)

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

            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_query_logs_timestamp ON query_logs(timestamp DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_query_logs_errors ON query_logs(error_occurred)")

            conn.commit()
            self.logger.info("SQLite database initialized at %s", self.sqlite_db_path)

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
                    location_info = geolocation_service.get_location_info(client_ip)
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
                        "anthropic" if "claude" in model_used.lower() else "google",  # Infer provider
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

                if request_id:
                    # Update by request_id if available (most reliable)
                    cursor.execute(
                        """
                        UPDATE query_logs 
                        SET system_response = ?
                        WHERE user_query = ? AND system_response = '[STREAMING RESPONSE]'
                        ORDER BY id DESC LIMIT 1
                    """,
                        (actual_response, question),
                    )
                else:
                    # Fallback: update most recent matching entry
                    cursor.execute(
                        """
                        UPDATE query_logs 
                        SET system_response = ?
                        WHERE client_ip = ? AND user_query = ? AND system_response = '[STREAMING RESPONSE]'
                        ORDER BY id DESC LIMIT 1  
                    """,
                        (actual_response, processed_ip, question),
                    )

                conn.commit()

                if cursor.rowcount > 0:
                    self.logger.debug("Updated streaming response in SQLite database")
                    return True
                else:
                    self.logger.warning("No matching streaming entry found to update in SQLite")
                    return False

        except Exception as e:
            self.logger.error("Failed to update streaming response in SQLite: %s", e)
            return False

    def _process_ip_for_logging(self, ip_address: str) -> Optional[str]:
        """Process IP address for logging, handling exclusion and anonymization."""
        if ip_address in self.excluded_ips:
            return None

        if self.anonymize_ips:
            return self.anonymize_ip(ip_address)
        else:
            return ip_address
