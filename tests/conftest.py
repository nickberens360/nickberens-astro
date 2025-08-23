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
        from backend.core import app_factory

        def _noop_decorator(*args, **kwargs):
            def _wrap(func):
                return func

            return _wrap

        monkeypatch.setattr(app_factory.limiter, "limit", _noop_decorator, raising=False)
    except Exception:
        # If limiter import fails for any reason in certain environments, just continue.
        pass
