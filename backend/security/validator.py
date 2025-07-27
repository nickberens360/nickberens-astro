"""
Security validation module for input sanitization and rate limiting.

This module contains the SecurityValidator class that handles:
- Query validation and sanitization
- Rate limiting per client IP
- Detection of suspicious patterns and injection attempts
- Input length validation
"""

import logging
import re
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class SecurityValidator:
    MAX_QUERY_LENGTH: int = 1000
    MAX_CHAT_HISTORY_LENGTH: int = 10
    MAX_MESSAGE_LENGTH: int = 1000
    SUSPICIOUS_PATTERNS: List[str] = [
        r"ignore\s+(previous|above|all)\s+instructions?",
        r"system\s*:?\s*you\s+are\s+now",
        r"forget\s+everything\s+(above|before)",
        r"new\s+instructions?\s*:",
        r"</?\s*(script|iframe|object|embed|form)",
        r"javascript\s*:",
        r"data\s*:\s*text/html",
        r"(prompt|system)\s+(injection|hack|override)",
        r"act\s+as\s+if\s+you\s+are",
        r"pretend\s+(you\s+are|to\s+be)",
    ]
    ALLOWED_MODELS: List[Optional[str]] = ["claude", "gemini", None]
    _user_requests: Dict[str, List[datetime]] = defaultdict(list)

    @classmethod
    def validate_query(cls, query, client_ip: str) -> tuple[bool, str]:
        try:
            if not query.question or not isinstance(query.question, str):
                return False, "Question is required and must be text"
            if len(query.question) > cls.MAX_QUERY_LENGTH:
                return (
                    False,
                    f"Question too long (max {cls.MAX_QUERY_LENGTH} characters)",
                )
            if query.chat_history:
                if len(query.chat_history) > cls.MAX_CHAT_HISTORY_LENGTH:
                    return (
                        False,
                        f"Chat history too long (max {cls.MAX_CHAT_HISTORY_LENGTH} messages)",
                    )
                for i, msg in enumerate(query.chat_history):
                    if not isinstance(msg.text, str) or len(msg.text) > cls.MAX_MESSAGE_LENGTH:
                        return (
                            False,
                            f"Message {i + 1} invalid or too long (max {cls.MAX_MESSAGE_LENGTH} characters)",
                        )
            if query.preferred_model and query.preferred_model not in cls.ALLOWED_MODELS:
                return False, "Invalid model preference"

            combined_text = query.question.lower()
            if query.chat_history:
                combined_text += " " + " ".join([msg.text.lower() for msg in query.chat_history])
            for pattern in cls.SUSPICIOUS_PATTERNS:
                if re.search(pattern, combined_text, re.IGNORECASE):
                    logger.warning(f"Suspicious pattern detected from {client_ip}: {pattern}")
                    return False, "Content not allowed"

            # This internal rate limiting can be a secondary check to the main SlowAPI one.
            if not cls._check_rate_limit(client_ip):
                return False, "Rate limit exceeded"

            return True, ""
        except Exception as e:
            logger.error(f"Error validating query: {e}")
            return False, "Validation error"

    @classmethod
    def _check_rate_limit(cls, client_ip: str) -> bool:
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)
        # Prune old requests
        cls._user_requests[client_ip] = [
            req_time for req_time in cls._user_requests[client_ip] if req_time > minute_ago
        ]

        # Check limit (e.g., 20 requests per minute)
        if len(cls._user_requests[client_ip]) >= 20:
            return False
        cls._user_requests[client_ip].append(now)
        return True

    @classmethod
    def sanitize_input(cls, text: Optional[str]) -> str:
        if not isinstance(text, str):
            return ""
        # Remove control characters except for common whitespace
        sanitized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
        # Normalize whitespace and limit length
        return re.sub(r"\s+", " ", sanitized).strip()[: cls.MAX_QUERY_LENGTH]
