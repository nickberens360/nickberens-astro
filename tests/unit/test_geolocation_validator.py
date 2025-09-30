"""Unit tests for the GeolocationValidator class."""

from unittest.mock import MagicMock, patch

import pytest

from backend.core.geolocation_validator import GeolocationValidator


class TestGeolocationValidator:
    """Test cases for GeolocationValidator."""

    @pytest.fixture
    def validator(self):
        """Create a GeolocationValidator instance for testing."""
        return GeolocationValidator()

    @pytest.fixture
    def mock_admin_db(self):
        """Mock admin database manager."""
        with patch("backend.core.geolocation_validator.admin_db_manager") as mock:
            mock.get_connection.return_value.__enter__.return_value.cursor.return_value.fetchall.return_value = []
            mock.record_security_event = MagicMock()
            yield mock

    def test_public_ip_classification_is_low_risk(self, validator):
        """Test that public IPs are classified as low risk after the fix."""
        result = validator._classify_ip("8.8.8.8")  # Google DNS - definitely public

        assert result["type"] == "public"
        assert result["risk_level"] == "low"  # Fixed from "medium"
        assert result["description"] == "Public internet address"

    def test_new_ip_should_not_be_blocked(self, validator, mock_admin_db):
        """Test that a new public IP should not be blocked."""
        result = validator.validate_login_location("testuser", "8.8.8.8")

        assert result["action"] == "allow"  # Should not be "block"
        assert result["risk_level"] in ["low", "medium"]  # But not "high"

    def test_frequent_ip_changes_threshold_increased(self, validator):
        """Test that the frequent IP changes threshold has been increased."""
        # Test with 6 different IPs (should NOT trigger frequent changes)
        login_history_6_ips = [
            {"ip": f"192.0.2.{i}", "last_seen": f"2024-01-{i:02d}T00:00:00", "count": 1}
            for i in range(1, 7)  # 6 different IPs
        ]

        ip_info = {"type": "public", "risk_level": "low", "description": "Public internet address"}
        is_unusual, risk_factors = validator._analyze_location_risk("192.0.2.7", ip_info, login_history_6_ips)

        # Should not flag 6 IPs as frequent changes (threshold is >6)
        assert "frequent_ip_changes" not in risk_factors

    def test_frequent_ip_changes_boundary_condition(self, validator):
        """Test the boundary condition for frequent IP changes (7+ IPs should trigger)."""
        # Test with 7 different IPs (should trigger frequent changes)
        login_history_7_ips = [
            {"ip": f"192.0.2.{i}", "last_seen": f"2024-01-{i:02d}T00:00:00", "count": 1}
            for i in range(1, 8)  # 7 different IPs
        ]

        ip_info = {"type": "public", "risk_level": "low", "description": "Public internet address"}
        is_unusual, risk_factors = validator._analyze_location_risk("192.0.2.8", ip_info, login_history_7_ips)

        # Should flag 7+ IPs as frequent changes (threshold is >6)
        assert "frequent_ip_changes" in risk_factors

    def test_risk_score_calculation_is_more_lenient(self, validator):
        """Test that risk score calculation is more lenient."""
        ip_info = {"type": "public", "risk_level": "low", "description": "Public internet address"}

        # New IP alone should not result in high risk
        risk_level = validator._calculate_risk_level(ip_info, ["new_ip_address"], is_unusual=True)
        assert risk_level != "high"  # Should be "low" or "medium"

        # Need more factors to reach high risk
        risk_level = validator._calculate_risk_level(
            ip_info, ["new_ip_address", "frequent_ip_changes", "long_time_since_last_use"], is_unusual=True
        )
        # Even with multiple factors, should be more forgiving
        assert risk_level in ["medium", "low"]  # Not immediately "high"

    def test_action_determination_less_aggressive(self, validator):
        """Test that action determination is less aggressive."""
        # Medium risk should warn, not block
        action = validator._determine_action("medium", is_unusual=True)
        assert action == "warn"  # Changed from conditional logic

        action = validator._determine_action("medium", is_unusual=False)
        assert action == "warn"  # Should still warn for medium risk

        # Only high risk should block
        action = validator._determine_action("high", is_unusual=True)
        assert action == "block"

    def test_cloud_penalty_only_when_unusual(self, validator):
        """Test that cloud usage only adds penalty when it's unusual for the user."""
        ip_info = {"type": "cloud", "risk_level": "medium", "description": "AWS cloud infrastructure"}

        # Test without unusual cloud usage - should not get extra penalty
        risk_factors_without_unusual_cloud = ["new_ip_address"]
        risk_level = validator._calculate_risk_level(ip_info, risk_factors_without_unusual_cloud, is_unusual=True)

        # Test with unusual cloud usage - should get extra penalty
        risk_factors_with_unusual_cloud = ["new_ip_address", "unusual_cloud_usage"]
        risk_level_with_penalty = validator._calculate_risk_level(
            ip_info, risk_factors_with_unusual_cloud, is_unusual=True
        )

        # The second case should have higher risk due to unusual cloud usage
        # Base case: 1 risk factor + 1 is_unusual penalty = 2 points = low (< 3)
        # With unusual cloud: 2 risk factors + 1 is_unusual + 1 cloud penalty = 4 points, but actually just 3 = medium
        assert risk_level == "low"  # Base case: 1 factor + 1 is_unusual = 2 points = low (< 3)
        assert risk_level_with_penalty == "medium"  # With cloud: 2 factors + 1 is_unusual = 3 points = medium

        # If they're different, the penalty version should be higher
        if risk_level != risk_level_with_penalty:
            severity_order = {"low": 0, "medium": 1, "high": 2}
            assert severity_order[risk_level_with_penalty] > severity_order[risk_level]
