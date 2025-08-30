"""Tests for admin settings API endpoints."""

from unittest.mock import patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from backend.core.config import FollowUpSettings


class TestAdminSettingsAPI:
    """Test cases for admin settings API endpoints."""

    @pytest.fixture
    def mock_session(self):
        """Mock admin session for authentication."""
        return {"user_id": 1, "username": "testadmin", "role": "admin"}

    @pytest.fixture
    def client(self):
        """Create test client."""
        from backend.main import app

        return TestClient(app)

    @pytest.mark.unit
    @patch("backend.routes.admin.admin_db_manager")
    @patch("backend.routes.admin.require_admin_auth")
    @patch("backend.routes.admin.audit_logger")
    def test_get_followup_settings_no_existing_settings(
        self, mock_audit, mock_auth, mock_db_manager, client, mock_session
    ):
        """Test GET /settings/followup when no settings exist."""
        mock_auth.return_value = mock_session
        mock_db_manager.get_admin_setting.return_value = None

        response = client.get("/api/admin/settings/followup")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should return default settings
        default_settings = FollowUpSettings()
        assert data["enabled"] == default_settings.enabled
        assert data["service_type"] == default_settings.service_type
        assert data["max_questions"] == default_settings.max_questions

    @pytest.mark.unit
    @patch("backend.routes.admin.admin_db_manager")
    @patch("backend.routes.admin.require_admin_auth")
    def test_get_followup_settings_existing_settings(self, mock_auth, mock_db_manager, client, mock_session):
        """Test GET /settings/followup when settings exist."""
        mock_auth.return_value = mock_session

        existing_settings = FollowUpSettings(enabled=False, service_type="dynamic", max_questions=3)
        mock_db_manager.get_admin_setting.return_value = existing_settings.to_json()

        response = client.get("/api/admin/settings/followup")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["enabled"] is False
        assert data["service_type"] == "dynamic"
        assert data["max_questions"] == 3

    @pytest.mark.unit
    @patch("backend.routes.admin.admin_db_manager")
    @patch("backend.routes.admin.require_admin_auth")
    def test_update_followup_settings_success(self, mock_auth, mock_db_manager, client, mock_session):
        """Test PUT /settings/followup with valid data."""
        mock_auth.return_value = mock_session
        mock_db_manager.set_admin_setting.return_value = True

        settings_data = {
            "enabled": True,
            "service_type": "contextual",
            "max_questions": 2,
            "relevance_threshold": 0.8,
            "include_technical": True,
            "include_personal": False,
            "include_creative": True,
            "question_style": "formal",
        }

        response = client.put("/api/admin/settings/followup", json=settings_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["success"] is True
        assert "message" in data
        assert data["settings"]["enabled"] is True
        assert data["settings"]["service_type"] == "contextual"
        assert data["settings"]["max_questions"] == 2

    @pytest.mark.unit
    @patch("backend.routes.admin.admin_db_manager")
    @patch("backend.routes.admin.require_admin_auth")
    def test_update_followup_settings_validation(self, mock_auth, mock_db_manager, client, mock_session):
        """Test that settings validation works during update."""
        mock_auth.return_value = mock_session
        mock_db_manager.set_admin_setting.return_value = True

        # Send invalid values that should be corrected
        settings_data = {
            "enabled": "true",  # String instead of bool
            "service_type": "invalid_type",  # Invalid service type
            "max_questions": 10,  # Too high, should be capped at 5
            "relevance_threshold": 2.0,  # Too high, should be capped at 1.0
            "question_style": "invalid_style",  # Invalid style
        }

        response = client.put("/api/admin/settings/followup", json=settings_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Check that validation corrected the values
        assert data["settings"]["enabled"] is True  # String "true" converted to bool
        assert data["settings"]["service_type"] == "static"  # Invalid type defaulted
        assert data["settings"]["max_questions"] == 5  # Capped at maximum
        assert data["settings"]["relevance_threshold"] == 1.0  # Capped at maximum
        assert data["settings"]["question_style"] == "conversational"  # Invalid style defaulted

    @pytest.mark.unit
    @patch("backend.routes.admin.admin_db_manager")
    @patch("backend.routes.admin.require_admin_auth")
    def test_update_followup_settings_database_error(self, mock_auth, mock_db_manager, client, mock_session):
        """Test PUT /settings/followup when database save fails."""
        mock_auth.return_value = mock_session
        mock_db_manager.set_admin_setting.return_value = False

        settings_data = {"enabled": False, "service_type": "static"}

        response = client.put("/api/admin/settings/followup", json=settings_data)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "Failed to update settings" in data["detail"]

    @pytest.mark.unit
    @patch("backend.routes.admin.admin_db_manager")
    @patch("backend.routes.admin.require_admin_auth")
    def test_reset_followup_settings_success(self, mock_auth, mock_db_manager, client, mock_session):
        """Test POST /settings/followup/reset."""
        mock_auth.return_value = mock_session
        mock_db_manager.set_admin_setting.return_value = True

        response = client.post("/api/admin/settings/followup/reset")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["success"] is True
        assert "reset to defaults" in data["message"]

        # Should return default settings
        default_settings = FollowUpSettings()
        assert data["settings"]["enabled"] == default_settings.enabled
        assert data["settings"]["service_type"] == default_settings.service_type
        assert data["settings"]["max_questions"] == default_settings.max_questions

    @pytest.mark.unit
    @patch("backend.routes.admin.admin_db_manager")
    @patch("backend.routes.admin.require_admin_auth")
    def test_reset_followup_settings_database_error(self, mock_auth, mock_db_manager, client, mock_session):
        """Test POST /settings/followup/reset when database save fails."""
        mock_auth.return_value = mock_session
        mock_db_manager.set_admin_setting.return_value = False

        response = client.post("/api/admin/settings/followup/reset")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "Failed to reset settings" in data["detail"]

    @pytest.mark.unit
    @patch("backend.routes.admin.require_admin_auth")
    def test_settings_authentication_required(self, mock_auth, client):
        """Test that all settings endpoints require authentication."""
        mock_auth.side_effect = Exception("Authentication required")

        # Test GET endpoint
        response = client.get("/api/admin/settings/followup")
        assert response.status_code != status.HTTP_200_OK

        # Test PUT endpoint
        response = client.put("/api/admin/settings/followup", json={})
        assert response.status_code != status.HTTP_200_OK

        # Test POST endpoint
        response = client.post("/api/admin/settings/followup/reset")
        assert response.status_code != status.HTTP_200_OK

    @pytest.mark.unit
    @patch("backend.routes.admin.admin_db_manager")
    @patch("backend.routes.admin.require_admin_auth")
    @patch("backend.routes.admin.audit_logger")
    def test_settings_audit_logging(self, mock_audit, mock_auth, mock_db_manager, client, mock_session):
        """Test that settings changes are properly audited."""
        mock_auth.return_value = mock_session
        mock_db_manager.get_admin_setting.return_value = None
        mock_db_manager.set_admin_setting.return_value = True

        # Test GET request audit
        response = client.get("/api/admin/settings/followup")
        assert response.status_code == status.HTTP_200_OK
        mock_audit.log_action.assert_called_with(
            user_id=mock_session["user_id"], action="get_followup_settings", details={"settings_exists": False}
        )

        # Test PUT request audit
        settings_data = {"enabled": False}
        response = client.put("/api/admin/settings/followup", json=settings_data)
        assert response.status_code == status.HTTP_200_OK

        # Should log the update action with new settings
        update_call = [
            call for call in mock_audit.log_action.call_args_list if call[1]["action"] == "update_followup_settings"
        ][0]
        assert update_call[1]["user_id"] == mock_session["user_id"]
        assert "new_settings" in update_call[1]["details"]

    @pytest.mark.unit
    @patch("backend.routes.admin.admin_db_manager")
    @patch("backend.routes.admin.require_admin_auth")
    def test_malformed_json_handling(self, mock_auth, mock_db_manager, client, mock_session):
        """Test handling of malformed JSON in request."""
        mock_auth.return_value = mock_session

        # Send malformed JSON
        response = client.put(
            "/api/admin/settings/followup", data="invalid json {", headers={"content-type": "application/json"}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.unit
    @patch("backend.routes.admin.admin_db_manager")
    @patch("backend.routes.admin.require_admin_auth")
    def test_empty_request_body(self, mock_auth, mock_db_manager, client, mock_session):
        """Test handling of empty request body."""
        mock_auth.return_value = mock_session
        mock_db_manager.set_admin_setting.return_value = True

        # Send empty JSON object
        response = client.put("/api/admin/settings/followup", json={})

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should use default settings
        assert data["success"] is True
        default_settings = FollowUpSettings()
        assert data["settings"]["enabled"] == default_settings.enabled
