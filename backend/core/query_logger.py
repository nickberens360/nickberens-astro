"""
Query logging service for tracking user queries and responses.

This module provides functionality to:
- Log user queries and AI responses
- Filter out queries from specified IP addresses
- Store logs in JSON format for easy retrieval
- Provide methods to read and search logs
"""

import hashlib
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

        # Set excluded IPs (can be loaded from config)
        self.excluded_ips = excluded_ips or set()

        # Load excluded IPs from environment if available
        excluded_ips_env = getattr(AppConfig, "EXCLUDED_IPS", None)
        if excluded_ips_env:
            # Support comma-separated IPs in environment variable
            env_ips = [ip.strip() for ip in excluded_ips_env.split(",")]
            self.excluded_ips.update(env_ips)

        # IP anonymization settings
        self.anonymize_ips = getattr(AppConfig, "ANONYMIZE_IPS", True)
        # Salt for IP hashing - should be kept secret and consistent
        self.ip_salt = getattr(AppConfig, "IP_HASH_SALT", "default-salt-change-in-production")

    def anonymize_ip(self, ip_address: str) -> str:
        """
        Anonymize an IP address using SHA-256 hashing with salt.

        The hash is truncated to 16 characters for readability while maintaining
        sufficient entropy to prevent collisions in typical use cases.

        Args:
            ip_address: The raw IP address to anonymize

        Returns:
            Anonymized IP address (16-character hash) or original if anonymization is disabled
        """
        if not self.anonymize_ips:
            return ip_address

        # Combine IP with salt for better security
        salted_ip = f"{ip_address}{self.ip_salt}".encode("utf-8")

        # Create SHA-256 hash
        hash_object = hashlib.sha256(salted_ip)
        hash_hex = hash_object.hexdigest()

        # Return first 16 characters of hash for readability
        # This provides ~64 bits of entropy, sufficient for most use cases
        return f"anon_{hash_hex[:16]}"

    def should_log_ip(self, client_ip: str) -> bool:
        """
        Check if queries from this IP should be logged.

        Note: This check is performed on the raw IP address before anonymization,
        allowing excluded IPs to be specified in their original form.

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

        # Anonymize IP address before logging
        anonymized_ip = self.anonymize_ip(client_ip)

        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "client_ip": anonymized_ip,
            "question": question,
            "response": response,
            "model_used": model_used,
            "query_type": query_type,
            "response_time": response_time,
            "metadata": metadata or {},
        }

        try:
            # Append to file in JSONL format for efficiency and safety
            with open(self.log_file_path, "a") as f:
                f.write(json.dumps(log_entry, default=str) + "\n")
        except (IOError, TypeError) as e:
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

            def _log_stream():
                """Stream logs from file without loading all into memory."""
                try:
                    with open(self.log_file_path, "r") as f:
                        for line in f:
                            if line.strip():
                                try:
                                    yield json.loads(line)
                                except json.JSONDecodeError:
                                    continue
                except FileNotFoundError:
                    pass

            # Apply filters using generator expression for memory efficiency
            filtered_logs = (
                log
                for log in _log_stream()
                if (not start_date or log.get("timestamp", "") >= start_date)
                and (not end_date or log.get("timestamp", "") <= end_date)
                and (not query_type or log.get("query_type") == query_type)
            )

            # Sort logs (requires materializing the generator)
            sorted_logs = sorted(filtered_logs, key=lambda x: x.get("timestamp", ""), reverse=True)

            # Apply limit
            if limit:
                return sorted_logs[:limit]
            return sorted_logs

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
            total_queries = 0
            unique_ips: Set[str] = set()
            query_types: Dict[str, int] = {}
            models_used: Dict[str, int] = {}
            earliest_ts: Optional[str] = None
            latest_ts: Optional[str] = None

            try:
                with open(self.log_file_path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            log = json.loads(line)
                        except json.JSONDecodeError:
                            continue

                        total_queries += 1

                        client_ip = log.get("client_ip")
                        if client_ip:
                            unique_ips.add(client_ip)

                        query_type = log.get("query_type", "unknown")
                        query_types[query_type] = query_types.get(query_type, 0) + 1

                        model = log.get("model_used", "unknown")
                        models_used[model] = models_used.get(model, 0) + 1

                        timestamp = log.get("timestamp", "")
                        if timestamp:
                            if earliest_ts is None or timestamp < earliest_ts:
                                earliest_ts = timestamp
                            if latest_ts is None or timestamp > latest_ts:
                                latest_ts = timestamp
            except FileNotFoundError:
                return {"total_queries": 0}

            if total_queries == 0:
                return {"total_queries": 0}

            return {
                "total_queries": total_queries,
                "unique_ips": len(unique_ips),
                "query_types": query_types,
                "models_used": models_used,
                "date_range": {
                    "earliest": earliest_ts or "",
                    "latest": latest_ts or "",
                },
            }

        except Exception as e:
            self.logger.error(f"Failed to get log stats: {e}")
            return {"error": str(e)}

    def _read_logs(self) -> List[Dict[str, Any]]:
        """Read logs from JSONL file."""
        logs = []
        try:
            with open(self.log_file_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:  # Skip empty lines
                        try:
                            log_entry = json.loads(line)
                            logs.append(log_entry)
                        except json.JSONDecodeError:
                            # Skip malformed lines but continue processing
                            continue
        except FileNotFoundError:
            # File doesn't exist yet, return empty list
            pass
        return logs

    def clear_logs(self) -> bool:
        """
        Clear all logs (use with caution).

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create empty file for JSONL format
            with open(self.log_file_path, "w"):
                pass  # Just create/truncate the file
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
