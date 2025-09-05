"""
Pytest configuration to streamline local and CI tests without extra env vars.

This file applies lightweight test-time patches only during pytest runs:
- Disable SlowAPI rate limiting decorator to avoid ASGITransport issues
  with streaming responses and to speed up tests.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def disable_rate_limiting(monkeypatch: pytest.MonkeyPatch):
    """Turn the SlowAPI limiter decorator into a no-op for tests.

    Avoids middleware TaskGroup errors with ASGI test transport and
    ensures tests focus on endpoint behavior rather than throttling.
    """
    try:
        # Set unlimited rate limit in config for tests
        from backend.core.config import AppConfig

        monkeypatch.setattr(AppConfig, "RATE_LIMIT", "100000/minute", raising=False)

        # Import and patch slowapi components
        from slowapi import Limiter

        def _noop_decorator(*args, **kwargs):
            def _wrap(func):
                return func

            return _wrap

        # Patch the Limiter class methods
        monkeypatch.setattr(Limiter, "limit", _noop_decorator, raising=False)

        # Try to patch the app_factory limiter instance too
        try:
            from backend.core import app_factory

            monkeypatch.setattr(app_factory.limiter, "limit", _noop_decorator, raising=False)
        except Exception:
            pass

    except Exception as e:
        # If any patching fails, continue with tests
        print(f"Warning: Could not fully disable rate limiting for tests: {e}")
