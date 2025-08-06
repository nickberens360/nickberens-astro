"""
Query logging service for tracking user queries and responses.

This module provides functionality to:
- Log user queries and AI responses
- Filter out queries from specified IP addresses
- Store logs in JSON format for easy retrieval
- Provide methods to read and search logs
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .config import AppConfig


class QueryLogger:
    """Service for logging user queries and AI responses with IP filtering."""

    def __init__(self, log_file_path: Optional[str] = None, excluded_ips: Optional[Set[str]] = None):
        """
        Initialize the QueryLogger.

        Args:
            log_file_path: Path to the log file (defaults to backend/query_logs.json)
            excluded_ips: Set of IP addresses to exclude from logging
        """
        self.logger = logging.getLogger(__name__)

        # Set default log file path if not provided
        if log_file_path is None:
            backend_dir = Path(__file__).parent.parent
            self.log_file_path = backend_dir / "query_logs.json"
        else:
            self.log_file_path = Path(log_file_path)

        # Ensure log file exists
        self.log_file_path.touch(exist_ok=True)

        # Initialize with empty list if file is empty
        if self.log_file_path.stat().st_size == 0:
            with open(self.log_file_path, "w") as f:
                json.dump([], f)

        # Set excluded IPs (can be loaded from config)
        self.excluded_ips = excluded_ips or set()

        # Load excluded IPs from environment if available
        excluded_ips_env = getattr(AppConfig, "EXCLUDED_IPS", None)
        if excluded_ips_env:
            # Support comma-separated IPs in environment variable
            env_ips = [ip.strip() for ip in excluded_ips_env.split(",")]
            self.excluded_ips.update(env_ips)

    def should_log_ip(self, client_ip: str) -> bool:
        """
        Check if queries from this IP should be logged.

        Args:
            client_ip: The client's IP address

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
    ) -> None:
        """
        Log a query and its response.

        Args:
            client_ip: The client's IP address
            question: The user's question
            response: The AI's response
            model_used: The model used for the response
            query_type: Type of query (text/image)
            response_time: Time taken to process the query
            metadata: Additional metadata to log
        """
        # Skip logging if IP is excluded
        if not self.should_log_ip(client_ip):
            return

        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "client_ip": client_ip,
            "question": question,
            "response": response,
            "model_used": model_used,
            "query_type": query_type,
            "response_time": response_time,
            "metadata": metadata or {},
        }

        try:
            # Read existing logs
            logs = self._read_logs()

            # Add new entry
            logs.append(log_entry)

            # Write back to file
            with open(self.log_file_path, "w") as f:
                json.dump(logs, f, indent=2, default=str)

        except Exception as e:
            self.logger.error(f"Failed to log query: {e}")

    def log_streaming_query(
        self,
        client_ip: str,
        question: str,
        model_used: str,
        response_time: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log a streaming query (response will be marked as [STREAMING]).

        Args:
            client_ip: The client's IP address
            question: The user's question
            model_used: The model used for the response
            response_time: Time taken to process the query
            metadata: Additional metadata to log
        """
        self.log_query(
            client_ip=client_ip,
            question=question,
            response="[STREAMING RESPONSE]",
            model_used=model_used,
            query_type="text",
            response_time=response_time,
            metadata=metadata,
        )

    def get_logs(
        self,
        limit: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        query_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve logs with optional filtering.

        Args:
            limit: Maximum number of logs to return
            start_date: Start date filter (ISO format)
            end_date: End date filter (ISO format)
            query_type: Filter by query type

        Returns:
            List of log entries matching the criteria
        """
        try:
            logs = self._read_logs()

            # Apply date filters
            if start_date or end_date:
                filtered_logs = []
                for log in logs:
                    log_date = log.get("timestamp", "")
                    if start_date and log_date < start_date:
                        continue
                    if end_date and log_date > end_date:
                        continue
                    filtered_logs.append(log)
                logs = filtered_logs

            # Apply query type filter
            if query_type:
                logs = [log for log in logs if log.get("query_type") == query_type]

            # Sort by timestamp (newest first)
            logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

            # Apply limit
            if limit:
                logs = logs[:limit]

            return logs

        except Exception as e:
            self.logger.error(f"Failed to retrieve logs: {e}")
            return []

    def get_log_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the query logs.

        Returns:
            Dictionary containing log statistics
        """
        try:
            logs = self._read_logs()

            if not logs:
                return {"total_queries": 0}

            query_types: Dict[str, int] = {}
            models_used: Dict[str, int] = {}

            # Count query types and models
            for log in logs:
                query_type = log.get("query_type", "unknown")
                model = log.get("model_used", "unknown")

                query_types[query_type] = query_types.get(query_type, 0) + 1
                models_used[model] = models_used.get(model, 0) + 1

            stats = {
                "total_queries": len(logs),
                "unique_ips": len(set(log.get("client_ip", "") for log in logs)),
                "query_types": query_types,
                "models_used": models_used,
                "date_range": {
                    "earliest": min(log.get("timestamp", "") for log in logs),
                    "latest": max(log.get("timestamp", "") for log in logs),
                },
            }

            return stats

        except Exception as e:
            self.logger.error(f"Failed to get log stats: {e}")
            return {"error": str(e)}

    def _read_logs(self) -> List[Dict[str, Any]]:
        """Read logs from file."""
        try:
            with open(self.log_file_path, "r") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def clear_logs(self) -> bool:
        """
        Clear all logs (use with caution).

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(self.log_file_path, "w") as f:
                json.dump([], f)
            return True
        except Exception as e:
            self.logger.error(f"Failed to clear logs: {e}")
            return False


# Global instance
_query_logger_instance = None


def get_query_logger() -> QueryLogger:
    """Get the global QueryLogger instance."""
    global _query_logger_instance
    if _query_logger_instance is None:
        _query_logger_instance = QueryLogger()
    return _query_logger_instance
