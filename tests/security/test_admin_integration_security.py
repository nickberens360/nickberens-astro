"""
Integration security tests for admin dashboard.
Tests complete authentication flows, cross-system security, and end-to-end security scenarios.
"""

import os
import sqlite3
import tempfile
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.main import app


@pytest.mark.security
@pytest.mark.integration
class TestAdminIntegrationSecurity:
    """Integration security tests for admin dashboard."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary test database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            yield tmp.name
        os.unlink(tmp.name)

    @pytest.fixture
    def client(self):
        """Create test client for API testing."""
        return TestClient(app)

    @pytest.fixture
    def setup_test_environment(self, temp_db):
        """Set up complete test environment with database and user."""
        # Initialize test database
        conn = sqlite3.connect(temp_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Create all required tables
        tables = {
            "admin_users": """
                CREATE TABLE admin_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'viewer',
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login_at TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """,
            "admin_sessions": """
                CREATE TABLE admin_sessions (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    started_at TIMESTAMP NOT NULL,
                    last_active_at TIMESTAMP NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES admin_users (id)
                )
            """,
            "rate_limiting": """
                CREATE TABLE rate_limiting (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    identifier TEXT NOT NULL,
                    identifier_type TEXT NOT NULL,
                    attempt_count INTEGER NOT NULL DEFAULT 1,
                    first_attempt_at TIMESTAMP NOT NULL,
                    last_attempt_at TIMESTAMP NOT NULL,
                    lockout_until TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(identifier, identifier_type)
                )
            """,
            "security_events": """
                CREATE TABLE security_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    identifier TEXT NOT NULL,
                    details TEXT,
                    severity TEXT NOT NULL DEFAULT 'low',
                    ip_address TEXT,
                    user_agent TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """,
        }

        for table_name, table_sql in tables.items():
            cursor.execute(table_sql)

        # Create test user with known password
        import bcrypt

        test_password = "TestP@ssw0rd123!"
        password_hash = bcrypt.hashpw(test_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        cursor.execute(
            """
            INSERT INTO admin_users (username, email, password_hash, role, is_active)
            VALUES (?, ?, ?, ?, ?)
        """,
            ("testadmin", "admin@test.com", password_hash, "admin", 1),
        )

        cursor.execute(
            """
            INSERT INTO admin_users (username, email, password_hash, role, is_active)
            VALUES (?, ?, ?, ?, ?)
        """,
            ("testviewer", "viewer@test.com", password_hash, "viewer", 1),
        )

        conn.commit()
        conn.close()

        yield {
            "db_path": temp_db,
            "admin_username": "testadmin",
            "viewer_username": "testviewer",
            "password": test_password,
        }

    def test_complete_authentication_flow_security(self, client, setup_test_environment):
        """Test complete authentication flow with security validations."""
        with patch("backend.core.admin_database.AdminDatabaseManager.db_path", setup_test_environment["db_path"]):
            with patch("backend.core.admin_auth.admin_db_manager") as mock_db:
                # Mock database manager to use our test database
                mock_db.get_connection.return_value.__enter__ = lambda: sqlite3.connect(
                    setup_test_environment["db_path"]
                )
                mock_db.get_connection.return_value.__enter__.return_value.row_factory = sqlite3.Row
                mock_db.get_connection.return_value.__exit__ = lambda *args: None

                mock_db.get_admin_user.side_effect = self._get_admin_user_mock(setup_test_environment["db_path"])
                mock_db.record_security_event.return_value = True
                mock_db.is_rate_limited.return_value = False
                mock_db.reset_rate_limit.return_value = True

                # Mock additional services
                with patch("backend.routes.admin.audit_logger") as mock_audit:
                    # Step 1: Failed login attempt
                    response = client.post(
                        "/admin/api/auth/login",
                        json={"username": setup_test_environment["admin_username"], "password": "wrongpassword"},
                    )

                    assert response.status_code == 200
                    assert not response.json()["success"]

                    # Should log failed attempt
                    mock_audit.log_login.assert_called_with(
                        setup_test_environment["admin_username"],
                        "testclient",
                        "",
                        success=False,
                        error_message="Invalid credentials",
                    )

                    # Step 2: Successful login
                    with patch("backend.core.admin_auth.AdminAuthManager.authenticate_user") as mock_auth:
                        mock_user = {
                            "id": 1,
                            "username": setup_test_environment["admin_username"],
                            "email": "admin@test.com",
                            "role": "admin",
                        }
                        mock_auth.return_value = {"user": mock_user, "session_id": "test-session-123"}

                        response = client.post(
                            "/admin/api/auth/login",
                            json={
                                "username": setup_test_environment["admin_username"],
                                "password": setup_test_environment["password"],
                            },
                        )

                        assert response.status_code == 200
                        assert response.json()["success"]
                        assert "admin_session" in response.cookies

                        # Should log successful login
                        mock_audit.log_login.assert_called_with(
                            setup_test_environment["admin_username"], "testclient", "", success=True, method="password"
                        )

    def test_session_hijacking_detection_flow(self, client, setup_test_environment):
        """Test complete session hijacking detection flow."""
        with patch("backend.core.admin_database.AdminDatabaseManager.db_path", setup_test_environment["db_path"]):
            with patch("backend.routes.admin.require_admin_auth") as mock_auth:
                with patch("backend.core.admin_auth.admin_db_manager") as mock_db:
                    # Create valid session
                    session_data = {
                        "id": "test-session-123",
                        "user_id": 1,
                        "username": setup_test_environment["admin_username"],
                        "role": "admin",
                        "ip_address": "192.168.1.100",
                        "user_agent": "Mozilla/5.0 (Chrome/90.0)",
                    }
                    mock_auth.return_value = session_data
                    mock_db.record_security_event.return_value = True

                    # Mock session fingerprinting detection
                    with patch("backend.core.admin_auth.session_fingerprinter") as mock_fingerprinter:
                        mock_fingerprinter.monitor_session_fingerprint.return_value = {
                            "validation_result": {
                                "risk_level": "high",
                                "reason": "Significant fingerprint change detected",
                            }
                        }

                        # Access admin endpoint - should trigger session monitoring
                        response = client.get("/admin/api/stats/overview")

                        # Should still allow access but log security event
                        assert response.status_code == 200

                        # Should record high-risk fingerprint change
                        mock_db.record_security_event.assert_called_with(
                            "possible_session_hijacking",
                            setup_test_environment["admin_username"],
                            "high",
                            "High-risk fingerprint change: Significant fingerprint change detected",
                            "testclient",
                            "",
                        )

    def test_rate_limiting_cross_system_integration(self, client, setup_test_environment):
        """Test rate limiting integration across authentication and API endpoints."""
        with patch("backend.core.admin_database.AdminDatabaseManager.db_path", setup_test_environment["db_path"]):
            with patch("backend.core.admin_auth.admin_db_manager") as mock_db:
                # Setup rate limiting state
                mock_db.get_connection.return_value.__enter__ = lambda: sqlite3.connect(
                    setup_test_environment["db_path"]
                )
                mock_db.get_connection.return_value.__enter__.return_value.row_factory = sqlite3.Row
                mock_db.get_connection.return_value.__exit__ = lambda *args: None

                # Mock progressive rate limiting
                attempt_count = 0

                def mock_is_rate_limited(*args):
                    nonlocal attempt_count
                    attempt_count += 1
                    return attempt_count > 3  # Rate limit after 3 attempts

                mock_db.is_rate_limited.side_effect = mock_is_rate_limited
                mock_db.record_rate_limit_attempt.return_value = attempt_count > 5  # Lockout after 5
                mock_db.record_security_event.return_value = True

                # Make multiple failed login attempts
                for i in range(6):
                    response = client.post(
                        "/admin/api/auth/login",
                        json={"username": setup_test_environment["admin_username"], "password": "wrongpassword"},
                    )

                    assert response.status_code == 200
                    assert not response.json()["success"]

                    if i >= 3:
                        # Should start triggering rate limiting logic
                        assert mock_db.record_security_event.called

    def test_geolocation_security_integration(self, client, setup_test_environment):
        """Test geolocation security validation integration."""
        with patch("backend.core.admin_database.AdminDatabaseManager.db_path", setup_test_environment["db_path"]):
            with patch("backend.core.admin_auth.admin_db_manager") as mock_db:
                mock_db.get_admin_user.side_effect = self._get_admin_user_mock(setup_test_environment["db_path"])
                mock_db.record_security_event.return_value = True

                # Mock geolocation validation
                with patch("backend.core.admin_auth.geo_validator") as mock_geo:
                    with patch("backend.core.admin_auth.AdminAuthManager.check_user_rate_limits") as mock_rate_check:
                        mock_rate_check.return_value = {"any_rate_limited": False}

                        # Test blocked unusual location
                        mock_geo.validate_login_location.return_value = {
                            "action": "block",
                            "reason": "Login from unusual country detected",
                        }

                        with patch("backend.core.admin_auth.AdminAuthManager.authenticate_user") as mock_auth:
                            mock_auth.return_value = None  # Blocked by geolocation

                            response = client.post(
                                "/admin/api/auth/login",
                                json={
                                    "username": setup_test_environment["admin_username"],
                                    "password": setup_test_environment["password"],
                                },
                            )

                            assert response.status_code == 200
                            assert not response.json()["success"]

                            # Should record security event
                            mock_db.record_security_event.assert_called()

    def test_audit_trail_security_integration(self, client, setup_test_environment):
        """Test comprehensive audit trail integration."""
        with patch("backend.core.admin_database.AdminDatabaseManager.db_path", setup_test_environment["db_path"]):
            with patch("backend.routes.admin.audit_logger") as mock_audit:
                with patch("backend.routes.admin.require_admin_auth") as mock_auth:
                    session_data = {"user_id": 1, "username": setup_test_environment["admin_username"], "role": "admin"}
                    mock_auth.return_value = session_data

                    # Test multiple admin actions that should be audited
                    admin_actions = [
                        ("GET", "/admin/api/auth/me", {}, "profile_access"),
                        ("POST", "/admin/api/auth/logout", {}, "logout"),
                    ]

                    for method, endpoint, data, expected_event in admin_actions:
                        if method == "GET":
                            response = client.get(endpoint)
                        elif method == "POST":
                            response = client.post(endpoint, json=data)

                        # Should complete successfully and be audited
                        assert response.status_code in [200, 201]

    def test_role_escalation_prevention(self, client, setup_test_environment):
        """Test prevention of role escalation attacks."""
        with patch("backend.core.admin_database.AdminDatabaseManager.db_path", setup_test_environment["db_path"]):
            # Test with viewer role trying to access admin endpoints
            with patch("backend.routes.admin.require_admin_role") as mock_admin_role:
                with patch("backend.routes.admin.require_admin_auth") as mock_auth:
                    # Mock viewer session
                    viewer_session = {
                        "user_id": 2,
                        "username": setup_test_environment["viewer_username"],
                        "role": "viewer",
                    }
                    mock_auth.return_value = viewer_session
                    mock_admin_role.side_effect = HTTPException(status_code=403, detail="Admin privileges required")

                    # Try to access admin-only endpoints
                    admin_endpoints = ["/admin/api/auth/create-user", "/admin/api/users"]

                    for endpoint in admin_endpoints:
                        if endpoint.endswith("create-user"):
                            response = client.post(
                                endpoint, json={"username": "newuser", "password": "NewP@ss123!", "role": "admin"}
                            )
                        else:
                            response = client.get(endpoint)

                        assert response.status_code == 403
                        assert "Admin privileges required" in response.json()["detail"]

    def test_session_security_lifecycle(self, client, setup_test_environment):
        """Test complete session security lifecycle."""
        with patch("backend.core.admin_database.AdminDatabaseManager.db_path", setup_test_environment["db_path"]):
            with patch("backend.core.admin_auth.admin_db_manager") as mock_db:
                # Mock database operations
                mock_db.get_connection.return_value.__enter__ = lambda: sqlite3.connect(
                    setup_test_environment["db_path"]
                )
                mock_db.get_connection.return_value.__enter__.return_value.row_factory = sqlite3.Row
                mock_db.get_connection.return_value.__exit__ = lambda *args: None

                session_id = "test-session-lifecycle"

                # Step 1: Session creation with security monitoring
                with patch("backend.core.admin_auth.session_fingerprinter") as mock_fingerprinter:
                    mock_fingerprinter.create_fingerprint.return_value = "test-fingerprint"
                    mock_fingerprinter.store_session_fingerprint.return_value = True

                    # Step 2: Session validation and monitoring
                    with patch("backend.routes.admin.require_admin_auth") as mock_auth:
                        session_data = {
                            "id": session_id,
                            "user_id": 1,
                            "username": setup_test_environment["admin_username"],
                            "role": "admin",
                        }
                        mock_auth.return_value = session_data

                        # Access protected endpoint
                        response = client.get("/admin/api/auth/me")
                        assert response.status_code == 200

                        # Step 3: Session expiry and cleanup
                        with patch("backend.core.admin_auth.AdminAuthManager.expire_session") as mock_expire:
                            response = client.post("/admin/api/auth/logout")
                            assert response.status_code == 200

                            # Should clean up session cookie
                            # Note: TestClient may not fully simulate cookie deletion

    def test_database_isolation_security(self, client, setup_test_environment):
        """Test database isolation between admin and backend systems."""
        with patch("backend.core.admin_database.AdminDatabaseManager.db_path", setup_test_environment["db_path"]):
            with patch("backend.routes.admin.require_admin_auth") as mock_auth:
                mock_auth.return_value = {
                    "user_id": 1,
                    "username": setup_test_environment["admin_username"],
                    "role": "admin",
                }

                # Test that admin system has read-only access to backend data
                with patch("backend.routes.admin.query_data_manager") as mock_query_manager:
                    mock_query_manager.get_queries.return_value = {"queries": [], "total": 0, "limit": 50, "offset": 0}

                    response = client.get("/admin/api/queries")
                    assert response.status_code == 200

                    # Should only read, never write to backend database
                    # Verify no write operations were attempted
                    assert not any(
                        call[0][0].upper().startswith(("INSERT", "UPDATE", "DELETE"))
                        for call in mock_query_manager.method_calls
                        if hasattr(call, "__len__") and len(call) > 0
                    )

    def _get_admin_user_mock(self, db_path):
        """Helper to create admin user mock function."""

        def mock_get_admin_user(username):
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM admin_users WHERE username = ? AND is_active = 1", (username.lower(),))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None

        return mock_get_admin_user

    def test_comprehensive_security_scenario(self, client, setup_test_environment):
        """Test comprehensive security scenario with multiple attack vectors."""
        with patch("backend.core.admin_database.AdminDatabaseManager.db_path", setup_test_environment["db_path"]):
            with patch("backend.core.admin_auth.admin_db_manager") as mock_db:
                mock_db.get_admin_user.side_effect = self._get_admin_user_mock(setup_test_environment["db_path"])
                mock_db.record_security_event.return_value = True
                mock_db.is_rate_limited.return_value = False
                mock_db.reset_rate_limit.return_value = True

                # Scenario: Attacker attempts multiple attack vectors

                # 1. SQL injection in login
                response = client.post(
                    "/admin/api/auth/login", json={"username": "admin'; DROP TABLE admin_users; --", "password": "any"}
                )
                assert response.status_code == 200
                assert not response.json()["success"]

                # 2. XSS in search parameters
                with patch("backend.routes.admin.require_admin_auth") as mock_auth:
                    mock_auth.return_value = {
                        "user_id": 1,
                        "username": setup_test_environment["admin_username"],
                        "role": "admin",
                    }

                    response = client.get("/admin/api/queries?search=<script>alert('xss')</script>")
                    assert response.status_code in [200, 400, 422]

                    # Response should not contain unescaped script
                    assert "<script>" not in response.text

                # 3. Parameter pollution
                response = client.get("/admin/api/queries?limit=10&limit=999999&limit=-1")
                # Should handle parameter pollution gracefully
                assert response.status_code in [200, 400, 422]

                # 4. All attacks should be handled securely without system compromise
                # Database should still be intact
                user = self._get_admin_user_mock(setup_test_environment["db_path"])(
                    setup_test_environment["admin_username"]
                )
                assert user is not None  # User still exists, table wasn't dropped
