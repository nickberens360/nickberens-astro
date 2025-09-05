"""
Pytest configuration to streamline local and CI tests without extra env vars.

This file applies lightweight test-time patches only during pytest runs:
- Disable SlowAPI rate limiting decorator to avoid ASGITransport issues
  with streaming responses and to speed up tests.
"""

from __future__ import annotations

import os

import pytest


def pytest_configure(config):
    """Configure pytest environment to disable rate limiting for all tests."""
    # Set environment variable for high rate limits during testing
    os.environ["RATE_LIMIT"] = "100000/minute"


@pytest.fixture(autouse=True, scope="session")
def setup_test_environment():
    """Setup test environment with disabled rate limiting."""
    # Ensure environment variable is set for entire test session
    original_rate_limit = os.environ.get("RATE_LIMIT")
    os.environ["RATE_LIMIT"] = "100000/minute"

    yield

    # Restore original value after tests
    if original_rate_limit is not None:
        os.environ["RATE_LIMIT"] = original_rate_limit
    else:
        os.environ.pop("RATE_LIMIT", None)
