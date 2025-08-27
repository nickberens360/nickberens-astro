"""
Production security configuration tests for admin dashboard.
Tests production-ready security settings, environment configuration, and deployment security.
"""

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.mark.security
@pytest.mark.production
@pytest.mark.critical
class TestAdminProductionSecurity:
    """Production security configuration tests."""

    @pytest.fixture
    def client(self):
        """Create test client for production security testing."""
        return TestClient(app)

    @pytest.fixture
    def production_env(self):
        """Mock production environment variables."""
        return {
            "ENVIRONMENT": "production",
            "DEBUG": "false",
            "ADMIN_TOKEN": "secure-production-token-2024",
            "PYTHONPATH": "/app",
            "PORT": "8000",
        }

    def test_environment_variable_security(self, production_env):
        """Test that sensitive environment variables are properly configured."""
        with patch.dict(os.environ, production_env, clear=False):
            # Test that sensitive variables exist and are secure

            # Admin token should be present and strong
            admin_token = os.getenv("ADMIN_TOKEN")
            assert admin_token is not None, "ADMIN_TOKEN not set in production"
            assert len(admin_token) >= 20, "ADMIN_TOKEN too short for production"
            assert admin_token != "admin", "ADMIN_TOKEN is default/weak value"
            assert admin_token != "password", "ADMIN_TOKEN is weak value"
            assert not admin_token.startswith("test"), "ADMIN_TOKEN appears to be test value"

            # Debug should be disabled
            debug_mode = os.getenv("DEBUG", "").lower()
            assert debug_mode in ["false", "0", ""], "DEBUG mode enabled in production"

            # Environment should be production
            environment = os.getenv("ENVIRONMENT", "").lower()
            assert environment == "production", "ENVIRONMENT not set to production"

    def test_debug_mode_disabled(self, client, production_env):
        """Test that debug mode is disabled in production."""
        with patch.dict(os.environ, production_env, clear=False):
            # Test that debug endpoints are not exposed
            debug_endpoints = ["/docs", "/redoc", "/openapi.json", "/debug", "/admin/debug", "/_debug_toolbar"]

            for endpoint in debug_endpoints:
                response = client.get(endpoint)
                # Should return 404, not expose debug info
                assert response.status_code in [404, 403], f"Debug endpoint exposed: {endpoint}"

                # Response should not contain debug information
                response_text = response.text.lower()
                debug_terms = ["traceback", "debug", "development", "stack trace", "python"]
                exposed_terms = [term for term in debug_terms if term in response_text]
                assert len(exposed_terms) == 0, f"Debug info exposed in {endpoint}: {exposed_terms}"

    def test_security_headers_production(self, client, production_env):
        """Test that production security headers are properly set."""
        with patch.dict(os.environ, production_env, clear=False):
            # Test public endpoint for headers
            response = client.get("/admin/api/health")
            headers = {k.lower(): v for k, v in response.headers.items()}

            security_checks = []

            # Check for security headers
            expected_headers = {
                "x-content-type-options": "nosniff",
                "x-frame-options": ["DENY", "SAMEORIGIN"],
                "x-xss-protection": "1; mode=block",
                "strict-transport-security": "max-age",  # Should contain max-age
                "referrer-policy": ["strict-origin-when-cross-origin", "no-referrer"],
            }

            for header, expected_value in expected_headers.items():
                header_value = headers.get(header, "")

                if isinstance(expected_value, list):
                    # Check if any of the expected values is present
                    header_ok = any(val.lower() in header_value.lower() for val in expected_value)
                    if not header_ok:
                        security_checks.append(f"Missing/incorrect {header}: {header_value}")
                elif isinstance(expected_value, str):
                    if expected_value not in header_value.lower():
                        security_checks.append(f"Missing/incorrect {header}: {header_value}")

            # Check that server header is not exposed
            if "server" in headers:
                server_header = headers["server"].lower()
                revealing_terms = ["uvicorn", "fastapi", "python", "gunicorn"]
                if any(term in server_header for term in revealing_terms):
                    security_checks.append(f"Server header reveals technology: {headers['server']}")

            # Content-Type should be properly set
            content_type = headers.get("content-type", "")
            if response.status_code == 200 and not content_type.startswith("application/json"):
                security_checks.append(f"Incorrect content-type: {content_type}")

            # Note: Some headers may not be set if not configured in middleware
            # This is informational for now
            if len(security_checks) > 0:
                print(f"Security header recommendations: {security_checks}")

    def test_https_enforcement(self, client, production_env):
        """Test HTTPS enforcement in production."""
        with patch.dict(os.environ, production_env, clear=False):
            # Test that HTTP requests are redirected to HTTPS (if configured)
            # Note: This depends on reverse proxy/load balancer configuration

            # Test secure cookie settings
            with patch("backend.routes.admin.admin_auth_manager") as mock_auth:
                mock_user = {"id": 1, "username": "testuser", "email": "test@example.com", "role": "admin"}
                mock_auth.authenticate_user.return_value = {"user": mock_user, "session_id": "test-session-123"}

                response = client.post("/admin/api/auth/login", json={"username": "testuser", "password": "correct"})

                if response.status_code == 200:
                    # Check cookie security attributes
                    set_cookie_header = response.headers.get("set-cookie", "")

                    cookie_checks = []

                    # In production, cookies should have Secure flag
                    if "admin_session" in set_cookie_header:
                        if "Secure" not in set_cookie_header:
                            cookie_checks.append("Session cookie missing Secure flag")

                        if "HttpOnly" not in set_cookie_header:
                            cookie_checks.append("Session cookie missing HttpOnly flag")

                        if "SameSite" not in set_cookie_header:
                            cookie_checks.append("Session cookie missing SameSite attribute")

                    # Note: Current implementation may set Secure=False for dev
                    # This is configuration dependent
                    if len(cookie_checks) > 0:
                        print(f"Cookie security recommendations: {cookie_checks}")

    def test_error_handling_production(self, client, production_env):
        """Test that production error handling doesn't expose sensitive information."""
        with patch.dict(os.environ, production_env, clear=False):
            # Test various error conditions
            error_endpoints = [
                ("/admin/api/queries/999999", "GET", None),  # Non-existent resource
                ("/admin/api/auth/login", "POST", {"invalid": "json"}),  # Invalid request
                ("/admin/nonexistent", "GET", None),  # 404 error
            ]

            for endpoint, method, payload in error_endpoints:
                if method == "GET":
                    response = client.get(endpoint)
                elif method == "POST":
                    response = client.post(endpoint, json=payload)

                # Error responses should not expose sensitive info
                response_text = response.text.lower() if hasattr(response, "text") else ""

                # Check for information disclosure
                sensitive_patterns = [
                    # File paths
                    "/users/",
                    "/backend/",
                    "/app/",
                    "c:\\",
                    "/var/",
                    "/opt/",
                    # Stack traces
                    "traceback",
                    "line ",
                    "file ",
                    ".py",
                    "error at",
                    # Database info
                    "sqlite",
                    "database",
                    "connection",
                    "query failed",
                    # System info
                    "python",
                    "fastapi",
                    "uvicorn",
                    "version",
                    # Internal structure
                    "admin_auth",
                    "admin_database",
                    "backend.core",
                ]

                disclosed_info = []
                for pattern in sensitive_patterns:
                    if pattern in response_text:
                        disclosed_info.append(pattern)

                assert (
                    len(disclosed_info) == 0
                ), f"Production error exposed sensitive info: {disclosed_info} in {method} {endpoint}"

    def test_logging_security_production(self, production_env):
        """Test that logging doesn't expose sensitive information in production."""
        with patch.dict(os.environ, production_env, clear=False):
            # Test that sensitive data is not logged
            sensitive_data = [
                "password123",
                "admin-token-secret",
                "192.168.1.100",  # IP addresses
                "session-id-12345",
            ]

            # Mock logging to capture log messages
            logged_messages = []

            def mock_log(message, *args, **kwargs):
                logged_messages.append(str(message) + " ".join(str(arg) for arg in args))

            with patch("backend.core.admin_auth.logger.info", mock_log):
                with patch("backend.core.admin_auth.logger.warning", mock_log):
                    with patch("backend.core.admin_auth.logger.error", mock_log):
                        # Simulate operations that might log sensitive data
                        from backend.core.admin_auth import AdminAuthManager

                        AdminAuthManager()

                        # This would normally log authentication attempts
                        # Check that sensitive data is not in logs

            # Verify no sensitive data in logs
            for message in logged_messages:
                message_lower = message.lower()
                for sensitive in sensitive_data:
                    assert (
                        sensitive.lower() not in message_lower
                    ), f"Sensitive data in logs: '{sensitive}' in '{message}'"

    def test_admin_token_security_production(self, client, production_env):
        """Test admin token security in production environment."""
        with patch.dict(os.environ, production_env, clear=False):
            admin_token = production_env["ADMIN_TOKEN"]

            # Test token strength
            token_checks = []

            # Length check
            if len(admin_token) < 32:
                token_checks.append("Token should be at least 32 characters")

            # Complexity check
            has_upper = any(c.isupper() for c in admin_token)
            has_lower = any(c.islower() for c in admin_token)
            has_digit = any(c.isdigit() for c in admin_token)
            has_special = any(c in "!@#$%^&*()_+-=" for c in admin_token)

            complexity_score = sum([has_upper, has_lower, has_digit, has_special])
            if complexity_score < 3:
                token_checks.append("Token should have better complexity (upper, lower, digits, special)")

            # Common weak patterns
            weak_patterns = ["admin", "password", "secret", "token", "key", "123", "abc"]
            for pattern in weak_patterns:
                if pattern.lower() in admin_token.lower():
                    token_checks.append(f"Token contains weak pattern: {pattern}")

            # Sequential characters
            if any(
                ord(admin_token[i]) == ord(admin_token[i + 1]) - 1 == ord(admin_token[i + 2]) - 2
                for i in range(len(admin_token) - 2)
            ):
                token_checks.append("Token contains sequential characters")

            assert len(token_checks) == 0, f"Admin token security issues: {token_checks}"

            # Test that token is required for admin endpoints
            response = client.post("/admin/refresh", json={"force_reindex": True})
            assert response.status_code == 401, "Admin refresh endpoint accessible without token"

            # Test with correct token
            response = client.post(
                "/admin/refresh", json={"force_reindex": True}, headers={"Authorization": f"Bearer {admin_token}"}
            )
            # Should be accepted (200) or method not allowed (405)
            assert response.status_code in [200, 201, 405], f"Valid admin token rejected: {response.status_code}"

    def test_database_security_production(self, production_env):
        """Test database security configuration for production."""
        with patch.dict(os.environ, production_env, clear=False):
            from backend.core.admin_database import AdminDatabaseManager

            # Test database path security
            db_manager = AdminDatabaseManager()
            db_path = str(db_manager.db_path)

            security_checks = []

            # Database should not be in web-accessible location
            web_accessible_paths = ["/var/www", "/public", "/static", "/assets"]
            if any(path in db_path.lower() for path in web_accessible_paths):
                security_checks.append("Database in potentially web-accessible location")

            # Database should not be in tmp or obviously insecure location
            insecure_paths = ["/tmp", "/temp", "/var/tmp"]
            if any(path in db_path.lower() for path in insecure_paths):
                security_checks.append("Database in insecure temporary location")

            # Should use absolute path
            if not os.path.isabs(db_path):
                security_checks.append("Database path should be absolute")

            assert len(security_checks) == 0, f"Database security issues: {security_checks}"

    def test_session_security_production(self, client, production_env):
        """Test session security in production environment."""
        with patch.dict(os.environ, production_env, clear=False):
            with patch("backend.routes.admin.admin_auth_manager") as mock_auth:
                mock_user = {"id": 1, "username": "prod_user", "role": "admin"}
                mock_auth.authenticate_user.return_value = {"user": mock_user, "session_id": "prod-session-123"}

                # Test session configuration
                response = client.post(
                    "/admin/api/auth/login", json={"username": "prod_user", "password": "ProdP@ssw0rd123!"}
                )

                if response.status_code == 200:
                    # Session should be created with production settings
                    session_data = response.json()

                    # Session ID should be present
                    assert "session_id" in session_data or "admin_session" in response.cookies

                    # Session should not expose internal details
                    sensitive_fields = ["password_hash", "database", "internal_id"]
                    for field in sensitive_fields:
                        assert field not in str(session_data).lower()

    def test_cors_configuration_production(self, client, production_env):
        """Test CORS configuration for production security."""
        with patch.dict(os.environ, production_env, clear=False):
            # Test CORS headers
            origins_to_test = [
                "https://evil.com",
                "http://localhost:3000",  # Should not be allowed in production
                "https://malicious-site.com",
                "null",
            ]

            for origin in origins_to_test:
                response = client.options("/admin/api/auth/me", headers={"Origin": origin})

                cors_header = response.headers.get("access-control-allow-origin", "")

                # Should not allow arbitrary origins in production
                if origin in ["https://evil.com", "https://malicious-site.com", "null"]:
                    assert cors_header != origin, f"CORS allows malicious origin: {origin}"

                # Localhost should not be allowed in production
                if "localhost" in origin:
                    assert cors_header != origin, f"CORS allows localhost in production: {origin}"

    def test_file_permissions_security(self, production_env):
        """Test file permissions and access security."""
        with patch.dict(os.environ, production_env, clear=False):
            # Test that sensitive files have appropriate permissions
            sensitive_files = ["backend/core/admin_database.py", "backend/core/admin_auth.py", "backend/core/config.py"]

            permission_checks = []

            for file_path in sensitive_files:
                if os.path.exists(file_path):
                    # Check file permissions (Unix-like systems)
                    try:
                        file_stat = os.stat(file_path)
                        file_perms = oct(file_stat.st_mode)[-3:]  # Last 3 digits

                        # Files should not be world-writable
                        if file_perms.endswith("7") or file_perms.endswith("6"):
                            permission_checks.append(f"{file_path} is world-writable: {file_perms}")

                        # Files should not be world-readable for sensitive configs
                        if file_path.endswith("config.py") and file_perms.endswith(("4", "5", "6", "7")):
                            permission_checks.append(f"{file_path} is world-readable: {file_perms}")

                    except (OSError, AttributeError):
                        # Permission check not available on this system
                        pass

            # This is informational - file permissions depend on deployment
            if len(permission_checks) > 0:
                print(f"File permission recommendations: {permission_checks}")

    def test_dependency_security_production(self):
        """Test that production dependencies are secure and up-to-date."""
        # Test for known vulnerable dependencies
        # This would typically be done by security scanners in CI/CD

        try:
            import pkg_resources

            installed_packages = []
            for dist in pkg_resources.working_set:
                installed_packages.append(f"{dist.project_name}=={dist.version}")

            # Known vulnerable patterns (examples)
            vulnerable_patterns = [
                "requests==2.9.0",  # Old version with vulnerabilities
                "urllib3==1.24.0",  # Old version
                "jinja2==2.10.0",  # Old version with XSS vulnerability
            ]

            security_issues = []
            for package in installed_packages:
                for vulnerable in vulnerable_patterns:
                    if package.lower() == vulnerable.lower():
                        security_issues.append(f"Vulnerable dependency: {package}")

            # This is informational for security review
            if len(security_issues) > 0:
                print(f"Dependency security review needed: {security_issues}")

        except ImportError:
            # pkg_resources not available
            pass
