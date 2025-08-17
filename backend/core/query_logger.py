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
from .geolocation_service import get_geolocation_service


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
        config = AppConfig()
        try:
            excluded_ips_list = config.EXCLUDED_IPS
            if excluded_ips_list:
                self.excluded_ips.update(excluded_ips_list)
        except Exception as e:
            self.logger.warning(f"Failed to load excluded IPs: {e}")

        # IP anonymization settings
        self.anonymize_ips = AppConfig.ANONYMIZE_IPS
        # Salt for IP hashing - should be kept secret and consistent
        try:
            self.ip_salt = config.IP_HASH_SALT
        except ValueError as e:
            # In production, this will raise if not set
            self.logger.error(f"Failed to get IP hash salt: {e}")
            raise

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
        request_id: Optional[str] = None,
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

        # Get geolocation data before anonymizing
        geo_service = get_geolocation_service()
        location_data = geo_service.get_location(client_ip)

        # Anonymize IP address before logging
        anonymized_ip = self.anonymize_ip(client_ip)

        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "client_ip": anonymized_ip,
            "location": location_data,  # Add location data
            "question": question,
            "response": response,
            "model_used": model_used,
            "query_type": query_type,
            "response_time": response_time,
            "request_id": request_id,
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
        request_id: Optional[str] = None,
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
            request_id=request_id,
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
        Update a streaming response log entry with the actual response content.

        This method finds the most recent streaming log entry for the given client_ip
        and question, then updates it with the actual response content.

        Args:
            cache_key: The cache key used for the response
            client_ip: The client's IP address
            question: The user's question
            actual_response: The actual response content to log

        Returns:
            bool: True if the update was successful, False otherwise
        """
        if not self.should_log_ip(client_ip):
            return True  # Skip logging but return success

        try:
            # Read all log entries
            log_entries = []
            try:
                with open(self.log_file_path, "r") as f:
                    for line in f:
                        if line.strip():
                            try:
                                log_entries.append(json.loads(line))
                            except json.JSONDecodeError:
                                # Keep malformed entries as-is
                                log_entries.append(line.rstrip())
            except FileNotFoundError:
                self.logger.warning(f"Log file not found: {self.log_file_path}")
                return False

            # If request_id is provided, append a completion entry instead of rewriting the file
            if request_id:
                completion_entry = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "client_ip": self.anonymize_ip(client_ip),
                    "location": get_geolocation_service().get_location(client_ip),
                    "question": question,
                    "response": actual_response,
                    "model_used": "streaming_completion",
                    "query_type": "text",
                    "response_time": None,
                    "request_id": request_id,
                    "metadata": {"cache_key": cache_key, "response_updated": datetime.utcnow().isoformat()},
                }
                try:
                    with open(self.log_file_path, "a") as f:
                        f.write(json.dumps(completion_entry, default=str) + "\n")
                    self.logger.debug(f"Appended streaming completion for request_id: {request_id}")
                    return True
                except (IOError, TypeError) as e:
                    self.logger.error(f"Failed to append streaming completion: {e}")
                    # Fall through to legacy rewrite method

            # Legacy rewrite path disabled to avoid race conditions
            self.logger.warning(
                "No request_id provided; skipping legacy rewrite of query logs to avoid race conditions"
            )
            return False

        except (IOError, TypeError) as e:
            self.logger.error(f"Failed to update streaming response: {e}")
            return False

    def get_logs(
        self,
        limit: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        query_type: Optional[str] = None,
        exclude_ips: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve logs with optional filtering.

        Args:
            limit: Maximum number of logs to return
            start_date: Start date filter (ISO format)
            end_date: End date filter (ISO format)
            query_type: Filter by query type
            exclude_ips: Comma-separated list of IPs to exclude

        Returns:
            List of log entries matching the criteria
        """
        try:
            # Prepare excluded IPs set once, outside the loop for performance
            excluded_set = set()
            if exclude_ips:
                excluded_set = set(ip.strip() for ip in exclude_ips.split(","))

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
                and (not excluded_set or log.get("client_ip") not in excluded_set)
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

    def get_log_stats(self, exclude_ips: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics about the query logs.

        Args:
            exclude_ips: Optional comma-separated list of IPs to exclude from statistics

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

            # Prepare excluded IPs set once, outside the loop for performance
            excluded_set = set()
            if exclude_ips:
                excluded_set = set(ip.strip() for ip in exclude_ips.split(","))

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

                        # Skip this log entry if it's from the excluded IPs
                        client_ip = log.get("client_ip")
                        if excluded_set and client_ip in excluded_set:
                            continue

                        total_queries += 1

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
