"""
Test configuration and fixtures.

This module sets up global test configuration including:
- Environment variables for testing
- Common fixtures
- Test setup and teardown
"""

import os

# Set environment variables at module level before any imports
# This ensures they are available when the FastAPI app is created
os.environ["RATE_LIMIT"] = "1000/minute"
