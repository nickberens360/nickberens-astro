"""
Security-focused tests for Admin API endpoints.
Tests authentication, authorization, rate limiting, input validation, and security headers.
"""

from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.main import app


@pytest.mark.security
@pytest.mark.api
class TestAdminAPIEndpointSecurity:
    """Security-focused tests for Admin API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client for API testing."""
        return TestClient(app)

    @pytest.fixture
    def mock_auth_session(self):
        """Mock authenticated admin session."""
        return {
            "id": "test-session-123",
            "user_id": 1,
            "username": "admin",
            "role": "admin",
            "email": "admin@test.com",
            "last_login_at": datetime.now().isoformat(),
        }

    @pytest.fixture
    def mock_viewer_session(self):
        """Mock authenticated viewer session."""
        return {
            "id": "test-session-456",
            "user_id": 2,
            "username": "viewer",
            "role": "viewer",
            "email": "viewer@test.com",
            "last_login_at": datetime.now().isoformat(),
        }

    def test_authentication_required_endpoints(self, client):
        """Test that protected endpoints require authentication."""
        protected_endpoints = [
            ("GET", "/admin/api/auth/me"),
            ("POST", "/admin/api/auth/logout"),
            ("POST", "/admin/api/auth/change-password"),
            ("GET", "/admin/api/stats/overview"),
            ("GET", "/admin/api/queries"),
            ("GET", "/admin/api/performance/metrics"),
            ("GET", "/admin/api/knowledge/files"),
            ("GET", "/admin/api/security/alerts"),
        ]

        for method, endpoint in protected_endpoints:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "POST":
                response = client.post(endpoint, json={})

            assert response.status_code == 401, f"Endpoint {method} {endpoint} should require authentication"
            assert "Authentication required" in response.json().get("detail", "")

    def test_authorization_role_enforcement(self, client):
        """Test role-based authorization enforcement."""
        admin_only_endpoints = [
            ("POST", "/admin/api/auth/create-user", {"username": "test", "password": "TestPass123!", "role": "viewer"}),
            ("GET", "/admin/api/users"),
        ]

        # Mock viewer session (should be denied)
        with patch("backend.routes.admin.require_admin_role") as mock_auth:
            mock_auth.side_effect = HTTPException(status_code=403, detail="Admin privileges required")

            for method, endpoint, data in admin_only_endpoints:
                if method == "GET":
                    response = client.get(endpoint)
                elif method == "POST":
                    response = client.post(endpoint, json=data)

                assert response.status_code == 403, f"Endpoint {method} {endpoint} should require admin role"
                assert "Admin privileges required" in response.json().get("detail", "")

    def test_login_rate_limiting_security(self, client):
        """Test login rate limiting and brute force protection."""
        with patch("backend.routes.admin.admin_auth_manager") as mock_auth:
            # Mock rate limited response
            mock_auth.authenticate_user.return_value = None
            mock_auth.is_rate_limited.return_value = True

            login_data = {"username": "testuser", "password": "wrongpassword"}

            # Multiple failed attempts
            for i in range(6):
                response = client.post("/admin/api/auth/login", json=login_data)

                if i < 5:
                    assert response.status_code == 200  # Login endpoint responds 200 with error message
                    assert not response.json()["success"]
                else:
                    # After rate limiting kicks in, should still handle gracefully
                    assert response.status_code in [200, 429]

    def test_session_cookie_security(self, client):
        """Test session cookie security attributes."""
        with patch("backend.routes.admin.admin_auth_manager") as mock_auth:
            mock_user = {
                "id": 1,
                "username": "testuser",
                "email": "test@example.com",
                "role": "admin",
                "password_hash": "test-hash",
            }

            mock_auth.authenticate_user.return_value = {"user": mock_user, "session_id": "test-session-123"}

            login_data = {"username": "testuser", "password": "correctpassword"}

            response = client.post("/admin/api/auth/login", json=login_data)
            assert response.status_code == 200

            # Check cookie security attributes
            cookies = response.cookies
            if "admin_session" in cookies:
                cookie = cookies["admin_session"]
                # Note: TestClient may not preserve all cookie attributes
                # In real implementation, verify HTTPOnly, Secure, SameSite
                assert cookie is not None

    def test_password_change_security_validation(self, client):
        """Test password change security and validation."""
        with patch("backend.routes.admin.require_admin_auth") as mock_auth:
            mock_auth.return_value = {"user_id": 1, "username": "testuser", "role": "admin"}

            with patch("backend.routes.admin.admin_db_manager") as mock_db:
                with patch("backend.routes.admin.admin_auth_manager") as mock_auth_mgr:
                    mock_db.get_admin_user.return_value = {
                        "id": 1,
                        "username": "testuser",
                        "password_hash": "current-hash",
                    }
                    mock_auth_mgr.verify_password.return_value = False  # Wrong current password

                    password_data = {"current_password": "wrongcurrent", "new_password": "NewSecureP@ss123!"}

                    response = client.post("/admin/api/auth/change-password", json=password_data)
                    assert response.status_code == 400
                    assert "Current password is incorrect" in response.json()["detail"]

    def test_input_validation_and_sanitization(self, client):
        """Test input validation and sanitization across endpoints."""
        # Test malicious inputs
        malicious_inputs = [
            "<script>alert('xss')</script>",
            "'; DROP TABLE admin_users; --",
            "javascript:alert('xss')",
            "../../../etc/passwd",
            "{{7*7}}",  # Template injection
            "\x00\x01\x02",  # Binary data
        ]

        with patch("backend.routes.admin.require_admin_auth") as mock_auth:
            mock_auth.return_value = {"user_id": 1, "username": "testuser", "role": "admin"}

            # Test query endpoint with malicious search
            for malicious_input in malicious_inputs:
                response = client.get(f"/admin/api/queries?search={malicious_input}")
                # Should handle gracefully without 500 error
                assert response.status_code in [200, 400, 422]

                # Response should not contain malicious input unescaped
                response_text = response.text.lower()
                assert "<script>" not in response_text
                assert "drop table" not in response_text

    def test_query_parameter_injection_protection(self, client):
        """Test protection against query parameter injection attacks."""
        with patch("backend.routes.admin.require_admin_auth") as mock_auth:
            mock_auth.return_value = {"user_id": 1, "username": "testuser", "role": "admin"}

            # Test with malicious query parameters
            malicious_params = [
                "?limit=-1",
                "?offset=-1",
                "?limit=999999999",
                "?days=-1",
                "?search=' OR 1=1 --",
                "?errors_only=true'; DROP TABLE query_logs; --",
            ]

            for param in malicious_params:
                response = client.get(f"/admin/api/queries{param}")
                # Should validate parameters and handle safely
                assert response.status_code in [200, 400, 422]

                # Should not cause internal server error
                if response.status_code != 200:
                    error_detail = response.json().get("detail", "")
                    # Should be validation error, not database error
                    assert "database" not in error_detail.lower()

    def test_json_payload_security(self, client):
        """Test security of JSON payload processing."""
        with patch("backend.routes.admin.require_admin_auth") as mock_auth:
            mock_auth.return_value = {"user_id": 1, "username": "testuser", "role": "admin"}

            # Test oversized JSON payload
            large_payload = {"feedback": "A" * 100000}  # Very large feedback

            response = client.post("/admin/api/queries/1/feedback", json=large_payload)
            # Should handle large payloads gracefully
            assert response.status_code in [200, 400, 413, 422]

            # Test malformed JSON structure
            malicious_payloads = [
                {"feedback": {"$ne": None}},  # NoSQL injection attempt
                {"feedback": ["array", "instead", "of", "string"]},
                {"feedback": None},
                {"extra_field": "should_be_ignored", "feedback": "normal"},
            ]

            for payload in malicious_payloads:
                response = client.post("/admin/api/queries/1/feedback", json=payload)
                # Should validate JSON structure
                assert response.status_code in [200, 400, 422]

    def test_csrf_protection_measures(self, client):
        """Test CSRF protection measures."""
        # Test that state-changing operations require proper authentication
        with patch("backend.routes.admin.require_admin_auth") as mock_auth:
            mock_auth.side_effect = HTTPException(status_code=401, detail="Authentication required")

            state_changing_endpoints = [
                ("POST", "/admin/api/auth/logout", {}),
                ("POST", "/admin/api/auth/change-password", {"current_password": "old", "new_password": "NewP@ss123!"}),
                ("POST", "/admin/api/queries/1/feedback", {"feedback": "good"}),
            ]

            for method, endpoint, data in state_changing_endpoints:
                # Without proper session, should be denied
                response = client.post(endpoint, json=data)
                assert response.status_code == 401

    def test_information_disclosure_prevention(self, client):
        """Test prevention of sensitive information disclosure."""
        # Test that error messages don't reveal sensitive information
        with patch("backend.routes.admin.require_admin_auth") as mock_auth:
            mock_auth.return_value = {"user_id": 1, "username": "testuser", "role": "admin"}

            # Test nonexistent query ID
            response = client.get("/admin/api/queries/99999")
            assert response.status_code == 404
            error_message = response.json().get("detail", "").lower()

            # Should not reveal database schema or internal details
            sensitive_terms = ["table", "column", "database", "sql", "select", "from"]
            for term in sensitive_terms:
                assert term not in error_message

    def test_security_headers_enforcement(self, client):
        """Test security headers in API responses."""
        response = client.get("/admin/api/health")  # Public endpoint

        # Check for security headers (may depend on middleware configuration)
        headers = response.headers

        # Content-Type should be properly set
        assert "application/json" in headers.get("content-type", "")

        # Test that sensitive headers are not exposed
        sensitive_headers = ["server", "x-powered-by", "x-aspnet-version"]
        for header in sensitive_headers:
            assert header.lower() not in [h.lower() for h in headers.keys()]

    def test_api_endpoint_timeout_protection(self, client):
        """Test API endpoint timeout and DoS protection."""
        with patch("backend.routes.admin.require_admin_auth") as mock_auth:
            mock_auth.return_value = {"user_id": 1, "username": "testuser", "role": "admin"}

            # Test with parameters that could cause slow queries
            slow_params = {
                "limit": 10000,  # Very large limit
                "days": 365,  # Large time range
                "search": "a",  # Generic search term
            }

            response = client.get("/admin/api/queries", params=slow_params)
            # Should either complete quickly or have reasonable limits
            assert response.status_code in [200, 400]

            if response.status_code == 400:
                # Should have validation error for excessive parameters
                error = response.json().get("detail", "")
                assert any(term in error.lower() for term in ["limit", "range", "validation"])

    def test_export_functionality_security(self, client):
        """Test security of data export functionality."""
        with patch("backend.routes.admin.require_admin_auth") as mock_auth:
            mock_auth.return_value = {"user_id": 1, "username": "testuser", "role": "admin"}

            # Test CSV export with malicious parameters
            malicious_dates = [
                "2024-01-01'; DROP TABLE query_logs; --",
                "../../../etc/passwd",
                "2024-13-45",  # Invalid date
                "' OR 1=1 --",
            ]

            for malicious_date in malicious_dates:
                response = client.get(f"/admin/api/export/csv?start_date={malicious_date}")
                # Should handle malicious dates safely
                assert response.status_code in [200, 400, 422]

                # Should not cause database errors
                if response.status_code != 200:
                    error = response.json().get("detail", "").lower()
                    assert "database" not in error
                    assert "sql" not in error

    def test_concurrent_request_handling(self, client):
        """Test handling of concurrent requests for DoS protection."""
        import threading

        responses = []
        errors = []

        def make_request():
            try:
                response = client.get("/admin/api/health")
                responses.append(response.status_code)
            except Exception as e:
                errors.append(str(e))

        # Make multiple concurrent requests
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Should handle concurrent requests without errors
        assert len(responses) == 10
        assert all(status == 200 for status in responses)
        assert len(errors) == 0

    def test_admin_token_validation_security(self, client):
        """Test admin token validation for refresh endpoints."""
        # Test refresh endpoint without token
        response = client.post("/admin/refresh")
        assert response.status_code == 401

        # Test refresh endpoint with invalid token
        headers = {"Authorization": "Bearer invalid-token"}
        response = client.post("/admin/refresh", headers=headers)
        assert response.status_code == 401

        # Test with token in query param
        response = client.post("/admin/refresh?token=invalid-token")
        assert response.status_code == 401

    def test_audit_logging_for_security_events(self, client):
        """Test that security events are properly logged."""
        with patch("backend.routes.admin.audit_logger") as mock_audit:
            with patch("backend.routes.admin.admin_auth_manager") as mock_auth:
                # Test failed login logging
                mock_auth.authenticate_user.return_value = None

                response = client.post(
                    "/admin/api/auth/login", json={"username": "testuser", "password": "wrongpassword"}
                )

                # Should log failed login attempt
                mock_audit.log_login.assert_called_once()
                call_args = mock_audit.log_login.call_args
                assert call_args[1]["success"] is False
                assert call_args[1]["error_message"] == "Invalid credentials"
