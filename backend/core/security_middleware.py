"""
Security middleware for FastAPI application.
Adds security headers and other security features.
"""

import logging
import os
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.

    Security headers implemented:
    - HSTS (HTTP Strict Transport Security)
    - CSP (Content Security Policy)
    - X-Frame-Options
    - X-Content-Type-Options
    - X-XSS-Protection
    - Referrer-Policy
    - Permissions-Policy
    """

    def __init__(self, app, enable_hsts: bool = None):
        super().__init__(app)

        # Auto-detect production environment for HSTS
        if enable_hsts is None:
            environment = os.getenv("ENVIRONMENT", "development").lower()
            self.enable_hsts = environment in ["production", "prod"]
        else:
            self.enable_hsts = enable_hsts

        # CSP policy - strict but allows necessary resources
        self.csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "  # Allow inline scripts for Vue.js dev
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )

        # Development CSP is more permissive
        environment = os.getenv("ENVIRONMENT", "development").lower()
        if environment in ["development", "dev", "local"]:
            self.csp_policy = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' http://localhost:* ws://localhost:*; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com data:; "
                "img-src 'self' data: https: http://localhost:*; "
                "connect-src 'self' https: http://localhost:* ws://localhost:*; "
                "frame-ancestors 'self'; "
                "base-uri 'self'; "
                "form-action 'self'"
            )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to all responses."""
        response = await call_next(request)

        # HSTS - Only in production and over HTTPS
        if self.enable_hsts and request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        # Content Security Policy
        response.headers["Content-Security-Policy"] = self.csp_policy

        # X-Frame-Options - Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # X-Content-Type-Options - Prevent MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-XSS-Protection - Enable XSS filtering (legacy but harmless)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer-Policy - Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions-Policy - Disable unnecessary browser features
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "accelerometer=(), "
            "gyroscope=()"
        )

        # Server header removal/modification
        response.headers["Server"] = "Admin-Backend/1.0"

        # Cache control for sensitive endpoints
        if request.url.path.startswith("/admin/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

        return response


class SecurityMonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware to monitor for suspicious activity and security events.
    """

    def __init__(self, app):
        super().__init__(app)
        self.suspicious_paths = {
            "/admin.php",
            "/wp-admin/",
            "/.env",
            "/config.php",
            "/phpinfo.php",
            "/xmlrpc.php",
            "/wp-login.php",
            "/.git/",
            "/phpmyadmin/",
            "/mysql/",
            "/sql/",
        }
        self.suspicious_user_agents = {
            "sqlmap",
            "nikto",
            "nessus",
            "burp",
            "zaproxy",
            "masscan",
            "nmap",
            "dirbuster",
            "gobuster",
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Monitor requests for suspicious activity."""
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "").lower()
        path = request.url.path.lower()

        # Check for suspicious paths
        if any(suspicious in path for suspicious in self.suspicious_paths):
            logger.warning(f"Suspicious path access: {path} from {client_ip}")
            # You could record this in the database here
            from .admin_database import admin_db_manager

            admin_db_manager.record_security_event(
                "suspicious_path_access",
                client_ip,
                "medium",
                f"Access to suspicious path: {path}",
                client_ip,
                user_agent,
            )

        # Check for suspicious user agents
        if any(suspicious in user_agent for suspicious in self.suspicious_user_agents):
            logger.warning(f"Suspicious user agent: {user_agent} from {client_ip}")
            from .admin_database import admin_db_manager

            admin_db_manager.record_security_event(
                "suspicious_user_agent",
                client_ip,
                "high",
                f"Suspicious user agent: {user_agent}",
                client_ip,
                user_agent,
            )

        # Check for unusually long URLs (potential buffer overflow attempts)
        if len(str(request.url)) > 2000:
            logger.warning(f"Unusually long URL from {client_ip}: {len(str(request.url))} characters")
            from .admin_database import admin_db_manager

            admin_db_manager.record_security_event(
                "long_url_attack",
                client_ip,
                "medium",
                f"URL length: {len(str(request.url))} characters",
                client_ip,
                user_agent,
            )

        # Check for SQL injection patterns in query params
        query_string = str(request.url.query).lower()
        sql_patterns = ["union select", "drop table", "'; --", "' or 1=1", "script>"]
        if any(pattern in query_string for pattern in sql_patterns):
            logger.warning(f"Potential SQL injection attempt from {client_ip}: {query_string[:100]}")
            from .admin_database import admin_db_manager

            admin_db_manager.record_security_event(
                "sql_injection_attempt",
                client_ip,
                "high",
                f"SQL injection pattern in query: {query_string[:200]}",
                client_ip,
                user_agent,
            )

        response = await call_next(request)
        return response


def add_security_middleware(app):
    """
    Add all security middleware to the FastAPI app.

    Args:
        app: FastAPI application instance
    """
    # Add security monitoring first (inner middleware)
    app.add_middleware(SecurityMonitoringMiddleware)

    # Add security headers (outer middleware)
    app.add_middleware(SecurityHeadersMiddleware)

    logger.info("Security middleware added to application")
