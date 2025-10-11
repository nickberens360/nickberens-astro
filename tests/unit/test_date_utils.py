"""
Comprehensive unit tests for backend.core.date_utils module.

Tests all date utility functions including edge cases, error handling,
and timezone consistency.
"""

from datetime import datetime, timedelta, timezone

import pytest

from backend.core.date_utils import (
    ensure_utc_naive,
    get_utc_now,
    parse_time_range,
    parse_time_range_start_only,
    parse_timestamp_string,
)


class TestParseTimeRange:
    """Tests for parse_time_range function."""

    def test_parse_time_range_valid_ranges(self):
        """Test parsing of all valid time range formats."""
        end_date = datetime(2024, 1, 15, 12, 0, 0)

        # Test 1 hour range
        start, end = parse_time_range("1h", end_date)
        assert end == end_date
        assert start == end_date - timedelta(hours=1)

        # Test 6 hour range
        start, end = parse_time_range("6h", end_date)
        assert end == end_date
        assert start == end_date - timedelta(hours=6)

        # Test 24 hour range
        start, end = parse_time_range("24h", end_date)
        assert end == end_date
        assert start == end_date - timedelta(days=1)

        # Test 7 day range
        start, end = parse_time_range("7d", end_date)
        assert end == end_date
        assert start == end_date - timedelta(days=7)

        # Test 30 day range
        start, end = parse_time_range("30d", end_date)
        assert end == end_date
        assert start == end_date - timedelta(days=30)

    def test_parse_time_range_with_custom_end_date(self):
        """Test that custom end date is respected."""
        custom_end = datetime(2024, 6, 15, 10, 30, 45)
        start, end = parse_time_range("24h", custom_end)

        assert end == custom_end
        assert start == datetime(2024, 6, 14, 10, 30, 45)

    def test_parse_time_range_without_end_date_uses_utc_now(self):
        """Test that omitting end_date uses current UTC time."""
        before_call = datetime.now(timezone.utc).replace(tzinfo=None)
        start, end = parse_time_range("1h")
        after_call = datetime.now(timezone.utc).replace(tzinfo=None)

        # End date should be between before and after
        assert before_call <= end <= after_call

        # Start should be 1 hour before end
        assert end - start == timedelta(hours=1)

    def test_parse_time_range_invalid_format(self):
        """Test that invalid time range raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported time range"):
            parse_time_range("invalid")

        with pytest.raises(ValueError, match="Unsupported time range"):
            parse_time_range("2h")  # Not a supported format

        with pytest.raises(ValueError, match="Unsupported time range"):
            parse_time_range("1d")  # Should be "24h" or "7d"

    def test_parse_time_range_returns_naive_datetime(self):
        """Test that returned datetimes are timezone-naive."""
        start, end = parse_time_range("24h")

        assert start.tzinfo is None
        assert end.tzinfo is None


class TestParseTimeRangeStartOnly:
    """Tests for parse_time_range_start_only function."""

    def test_parse_time_range_start_only_returns_correct_start(self):
        """Test that function returns only the start date."""
        end_date = datetime(2024, 1, 15, 12, 0, 0)
        start = parse_time_range_start_only("7d", end_date)

        expected_start = end_date - timedelta(days=7)
        assert start == expected_start

    def test_parse_time_range_start_only_all_ranges(self):
        """Test all time ranges return correct start dates."""
        end_date = datetime(2024, 1, 15, 12, 0, 0)

        assert parse_time_range_start_only("1h", end_date) == end_date - timedelta(hours=1)
        assert parse_time_range_start_only("6h", end_date) == end_date - timedelta(hours=6)
        assert parse_time_range_start_only("24h", end_date) == end_date - timedelta(days=1)
        assert parse_time_range_start_only("7d", end_date) == end_date - timedelta(days=7)
        assert parse_time_range_start_only("30d", end_date) == end_date - timedelta(days=30)


class TestParseTimestampString:
    """Tests for parse_timestamp_string function."""

    def test_parse_timestamp_string_iso_format(self):
        """Test parsing ISO format timestamps."""
        # ISO with 'Z' suffix
        result = parse_timestamp_string("2024-01-15T10:30:00Z")
        assert result == datetime(2024, 1, 15, 10, 30, 0)
        assert result.tzinfo is None

        # ISO with timezone offset
        result = parse_timestamp_string("2024-01-15T10:30:00+00:00")
        assert result == datetime(2024, 1, 15, 10, 30, 0)
        assert result.tzinfo is None

        # ISO with different timezone (should convert to UTC)
        result = parse_timestamp_string("2024-01-15T10:30:00-05:00")
        assert result == datetime(2024, 1, 15, 15, 30, 0)  # Converted to UTC
        assert result.tzinfo is None

        # ISO without timezone (assume UTC)
        result = parse_timestamp_string("2024-01-15T10:30:00")
        assert result == datetime(2024, 1, 15, 10, 30, 0)
        assert result.tzinfo is None

    def test_parse_timestamp_string_space_separated(self):
        """Test parsing space-separated format."""
        # Without microseconds
        result = parse_timestamp_string("2024-01-15 10:30:00")
        assert result == datetime(2024, 1, 15, 10, 30, 0)
        assert result.tzinfo is None

        # With microseconds (admin database format)
        result = parse_timestamp_string("2024-01-15 10:30:00.123456")
        assert result == datetime(2024, 1, 15, 10, 30, 0, 123456)
        assert result.tzinfo is None

    def test_parse_timestamp_string_date_only(self):
        """Test parsing date-only format."""
        result = parse_timestamp_string("2024-01-15")
        assert result == datetime(2024, 1, 15, 0, 0, 0)
        assert result.tzinfo is None

    def test_parse_timestamp_string_edge_cases(self):
        """Test edge cases and error handling."""
        # Empty string
        with pytest.raises(ValueError, match="Empty timestamp string"):
            parse_timestamp_string("")

        # Invalid format
        with pytest.raises(ValueError, match="Unable to parse timestamp"):
            parse_timestamp_string("invalid-date")

        # Malformed ISO format
        with pytest.raises(ValueError, match="Unable to parse timestamp"):
            parse_timestamp_string("2024-13-45T99:99:99Z")

    def test_parse_timestamp_string_microseconds(self):
        """Test parsing timestamps with microseconds."""
        result = parse_timestamp_string("2024-01-15T10:30:00.123456Z")
        assert result == datetime(2024, 1, 15, 10, 30, 0, 123456)
        assert result.tzinfo is None

    def test_parse_timestamp_string_consistency(self):
        """Test that various formats produce consistent results."""
        # All these should parse to the same UTC time
        formats = [
            "2024-01-15T10:30:00Z",
            "2024-01-15T10:30:00+00:00",
            "2024-01-15 10:30:00",
        ]

        results = [parse_timestamp_string(fmt) for fmt in formats]
        expected = datetime(2024, 1, 15, 10, 30, 0)

        for result in results:
            assert result == expected
            assert result.tzinfo is None


class TestGetUtcNow:
    """Tests for get_utc_now function."""

    def test_get_utc_now_returns_naive_datetime(self):
        """Test that function returns timezone-naive datetime."""
        result = get_utc_now()
        assert result.tzinfo is None

    def test_get_utc_now_returns_current_time(self):
        """Test that returned time is approximately current UTC time."""
        before = datetime.now(timezone.utc).replace(tzinfo=None)
        result = get_utc_now()
        after = datetime.now(timezone.utc).replace(tzinfo=None)

        # Result should be between before and after
        assert before <= result <= after

    def test_get_utc_now_consistency(self):
        """Test multiple calls return similar times."""
        time1 = get_utc_now()
        time2 = get_utc_now()

        # Times should be within 1 second of each other
        diff = abs((time2 - time1).total_seconds())
        assert diff < 1.0


class TestEnsureUtcNaive:
    """Tests for ensure_utc_naive function."""

    def test_ensure_utc_naive_with_timezone_aware(self):
        """Test converting timezone-aware datetime to naive UTC."""
        # Create timezone-aware datetime (UTC)
        aware_utc = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = ensure_utc_naive(aware_utc)

        assert result == datetime(2024, 1, 15, 10, 30, 0)
        assert result.tzinfo is None

    def test_ensure_utc_naive_with_different_timezone(self):
        """Test converting non-UTC timezone to naive UTC."""
        # Create timezone-aware datetime (EST: UTC-5)
        from datetime import timezone as tz

        est = tz(timedelta(hours=-5))
        aware_est = datetime(2024, 1, 15, 10, 30, 0, tzinfo=est)
        result = ensure_utc_naive(aware_est)

        # Should convert to UTC (10:30 EST = 15:30 UTC)
        assert result == datetime(2024, 1, 15, 15, 30, 0)
        assert result.tzinfo is None

    def test_ensure_utc_naive_with_already_naive(self):
        """Test that naive datetime is returned as-is."""
        naive = datetime(2024, 1, 15, 10, 30, 0)
        result = ensure_utc_naive(naive)

        assert result == naive
        assert result.tzinfo is None

    def test_ensure_utc_naive_preserves_microseconds(self):
        """Test that microseconds are preserved."""
        aware = datetime(2024, 1, 15, 10, 30, 0, 123456, tzinfo=timezone.utc)
        result = ensure_utc_naive(aware)

        assert result.microsecond == 123456
        assert result.tzinfo is None


class TestIntegrationScenarios:
    """Integration tests simulating real-world usage patterns."""

    def test_database_timestamp_workflow(self):
        """Test typical database timestamp handling workflow."""
        # Simulate storing current time
        stored_time = get_utc_now()

        # Simulate retrieving from database as ISO string
        db_string = stored_time.isoformat()

        # Parse back from database
        retrieved_time = parse_timestamp_string(db_string)

        # Should match original (within microseconds)
        assert retrieved_time == stored_time
        assert retrieved_time.tzinfo is None

    def test_performance_metrics_calculation(self):
        """Test time range calculation for performance metrics."""
        # Simulate getting latest timestamp from database
        latest_timestamp_str = "2024-01-15 23:59:59"
        end_date = parse_timestamp_string(latest_timestamp_str)

        # Calculate start date for 24h metrics
        start_date = parse_time_range_start_only("24h", end_date)

        # Verify range
        assert end_date == datetime(2024, 1, 15, 23, 59, 59)
        assert start_date == datetime(2024, 1, 14, 23, 59, 59)
        assert (end_date - start_date).total_seconds() == 86400  # 24 hours

    def test_cross_timezone_consistency(self):
        """Test that different timezone inputs produce consistent UTC results."""
        # Create same moment in different timezones
        utc_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        est_offset = timezone(timedelta(hours=-5))
        est_time = datetime(2024, 1, 15, 7, 0, 0, tzinfo=est_offset)  # Same moment

        # Both should convert to same naive UTC
        utc_result = ensure_utc_naive(utc_time)
        est_result = ensure_utc_naive(est_time)

        assert utc_result == est_result
        assert utc_result == datetime(2024, 1, 15, 12, 0, 0)
