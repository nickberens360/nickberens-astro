"""
Test configuration and fixtures.

This module sets up global test configuration including:
- Environment variables for testing
- Common fixtures
- Test setup and teardown
- Performance optimizations
"""

import asyncio
import os
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

# Set environment variables at module level before any imports
# This ensures they are available when the FastAPI app is created
os.environ["RATE_LIMIT"] = "1000/minute"
os.environ["ANTHROPIC_API_KEY"] = "test-key-for-testing"  # Prevent API calls in tests


# Session-scoped fixtures for expensive setup
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def mock_external_services():
    """Mock all external services to prevent network calls."""
    with (
        patch("backend.core.auto_rag.HuggingFaceEmbedding") as mock_hf,
        patch("backend.core.auto_rag.Anthropic") as mock_anthropic,
        patch("backend.core.auto_rag.VectorStoreIndex") as mock_index,
    ):

        # Configure mocks to return sensible defaults
        mock_hf.return_value = MagicMock()
        mock_anthropic.return_value = MagicMock()
        mock_index.return_value = MagicMock()

        yield {"hf_embedding": mock_hf, "anthropic": mock_anthropic, "vector_index": mock_index}


@pytest.fixture(scope="session")
def mock_rag_system():
    """Create a mock RAG system for tests that don't need real indexing."""
    mock_system = MagicMock()
    mock_system.query.return_value = ("Test response", [], [])
    mock_system.get_document_stats.return_value = {
        "total_files": 0,
        "file_types": {},
        "total_size": 0,
        "last_updated": "2025-01-01T00:00:00Z",
    }
    mock_system.get_model_name.return_value = "test-model"
    return mock_system


@pytest.fixture
async def fast_client(mock_rag_system):
    """
    Fast AsyncClient fixture that uses mocked RAG system.
    Use this for API tests that don't need real RAG functionality.
    """
    with patch("backend.main.rag_system", mock_rag_system):
        # Import here to avoid circular imports
        from backend.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest.fixture
async def client():
    """
    Full AsyncClient fixture for integration tests.
    Use fast_client for unit tests instead.
    """
    # Import here to avoid circular imports and ensure mocks are in place
    from backend.main import app

    # Use the app's lifespan context manager to ensure rag_system is initialized
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest.fixture(scope="function")
def mock_file_system():
    """Mock file system operations for consistent test environment."""
    with (
        patch("os.path.exists") as mock_exists,
        patch("os.listdir") as mock_listdir,
        patch("os.path.isfile") as mock_isfile,
        patch("pathlib.Path.exists") as mock_path_exists,
    ):

        # Configure reasonable defaults
        mock_exists.return_value = True
        mock_listdir.return_value = ["test_file.json", "test_doc.md"]
        mock_isfile.return_value = True
        mock_path_exists.return_value = True

        yield {"exists": mock_exists, "listdir": mock_listdir, "isfile": mock_isfile, "path_exists": mock_path_exists}


# Performance optimization: Skip heavy imports during test collection
def pytest_collection_modifyitems(config, items):
    """Modify test items during collection for performance."""
    # Add markers automatically based on test location/name
    for item in items:
        # Mark integration tests
        if "integration" in str(item.fspath) or "integration" in item.name:
            item.add_marker(pytest.mark.integration)

        # Mark API tests
        if "api" in item.name or "endpoint" in item.name:
            item.add_marker(pytest.mark.api)

        # Mark slow tests (auto-detect based on certain patterns)
        if any(keyword in item.name.lower() for keyword in ["slow", "heavy", "large", "full"]):
            item.add_marker(pytest.mark.slow)

        # Mark security tests
        if "security" in str(item.fspath) or "security" in item.name:
            item.add_marker(pytest.mark.security)


# Configure pytest to run faster
def pytest_configure(config):
    """Configure pytest for optimal performance."""
    # Disable verbose mode for faster runs unless explicitly requested
    if config.getoption("verbose") == 0:
        config.option.verbose = -1  # Quiet mode


# Cleanup fixtures
@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Cleanup after each test to prevent state leakage."""
    yield
    # Reset any global state here if needed
    # For example, clear caches, reset singletons, etc.
