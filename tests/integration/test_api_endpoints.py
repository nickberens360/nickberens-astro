"""
Integration tests for FastAPI backend endpoints - Updated for Auto-RAG implementation.

This module contains integration tests that validate the entire request/response
lifecycle of the Auto-RAG FastAPI application. These tests ensure that the API endpoints
are correctly configured, requests are properly processed, and responses conform
to the expected schemas.
"""

from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

# Import the FastAPI app instance
from backend.main import app

# Mark the entire module to be run with asyncio
pytestmark = pytest.mark.asyncio


@pytest.fixture
async def client():
    """
    Pytest fixture to create an AsyncClient for making requests to the test app.
    """
    # Use the app's lifespan context manager to ensure rag_system is initialized
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


async def test_health_check_returns_ok(client: AsyncClient):
    """
    Test that the GET /health endpoint returns 200 OK and correct status.
    """
    response = await client.get("/health")

    assert response.status_code == 200
    response_json = response.json()
    assert "status" in response_json
    assert response_json["status"] == "healthy"
    assert "auto_rag_available" in response_json
    assert "version" in response_json


async def test_root_endpoint_returns_status(client: AsyncClient):
    """
    Test that the GET / endpoint returns the correct status.
    """
    response = await client.get("/")

    assert response.status_code == 200
    response_json = response.json()
    assert "status" in response_json
    # In a test environment with mocks, rag_system might be None, so status could be degraded
    assert response_json["status"] in ["healthy", "degraded"]


async def test_query_endpoint_successful_response(client: AsyncClient):
    """
    Test that the POST /query endpoint works with a valid request.
    Mocks the Auto-RAG system to prevent external API calls.
    """
    # Test data constants
    test_question = "Tell me about your experience"
    expected_response = "This is a mocked AI response."
    empty_chat_history: List[Dict[str, str]] = []
    preferred_model = "claude"
    mock_stats = {
        "total_files": 5,
        "file_types": {"md": 3, "json": 2},
        "total_size": 1024,
        "last_updated": "2025-01-01T00:00:00Z",
    }
    mock_source_nodes: List[Dict[str, Any]] = []  # Mock empty source nodes

    # Mock the global rag_system object in the main module
    with patch("backend.main.rag_system", autospec=True) as mock_rag_system:
        # Update mock to return tuple (response_text, source_nodes, image_urls)
        mock_rag_system.query.return_value = (expected_response, mock_source_nodes, [])
        mock_rag_system.get_document_stats.return_value = mock_stats
        mock_rag_system.get_model_name.return_value = "claude-3-sonnet"

        # Make a POST request to "/query"
        response = await client.post(
            "/query",
            json={
                "question": test_question,
                "chat_history": empty_chat_history,
                "preferred_model": preferred_model,
                "max_results": 5,
                "include_sources": True,
            },
        )

        assert response.status_code == 200
        response_json = response.json()

        # Check response structure
        assert "response" in response_json
        assert "sources" in response_json
        assert "document_stats" in response_json
        assert "model_used" in response_json

        # Check response content
        assert response_json["response"] == expected_response
        assert response_json["model_used"] == "claude-3-sonnet"
        assert response_json["document_stats"] == mock_stats
        assert isinstance(response_json["sources"], list)

        # Verify the mock was called with the correct arguments
        mock_rag_system.query.assert_called_once_with(test_question, top_k=5)
        mock_rag_system.get_document_stats.assert_called_once()
        mock_rag_system.get_model_name.assert_called_once()


async def test_query_endpoint_invalid_payload_returns_422(client: AsyncClient):
    """
    Test that POST /query returns a 422 error for a malformed request body.
    """
    response = await client.post("/query", json={"wrong_key": "some value"})

    assert response.status_code == 422
    response_json = response.json()
    assert "detail" in response_json
    # Check that the validation error mentions the missing 'question' field
    assert any(
        error.get("loc") == ["body", "question"] and error.get("type") == "missing" for error in response_json["detail"]
    )


async def test_query_endpoint_rag_system_not_initialized(client: AsyncClient):
    """
    Test that POST /query returns 503 when RAG system is not initialized.
    """
    with patch("backend.main.rag_system", None):
        response = await client.post(
            "/query",
            json={"question": "Test question"},
        )
        assert response.status_code == 503
        assert "RAG system not initialized" in response.json()["detail"]


async def test_query_endpoint_with_chat_history(client: AsyncClient):
    """
    Test that the POST /query endpoint properly builds context from chat history.
    """
    test_question = "Follow up question"
    expected_response = "Response with context"
    mock_source_nodes: List[Dict[str, Any]] = []
    chat_history = [
        {"sender": "user", "text": "Previous question"},
        {"sender": "assistant", "text": "Previous response"},
    ]

    with patch("backend.main.rag_system", autospec=True) as mock_rag_system:
        mock_rag_system.query.return_value = (expected_response, mock_source_nodes, [])
        mock_rag_system.get_document_stats.return_value = {}
        mock_rag_system.get_model_name.return_value = "claude-3-sonnet"

        await client.post(
            "/query",
            json={"question": test_question, "chat_history": chat_history},
        )

        mock_rag_system.query.assert_called_once()
        # Check that the full question passed to the RAG system includes context
        full_question_arg = mock_rag_system.query.call_args[0][0]
        assert "Previous conversation context:" in full_question_arg
        assert "User: Previous question" in full_question_arg
        assert "Assistant: Previous response" in full_question_arg
        assert "Current question:\nFollow up question" in full_question_arg


async def test_query_endpoint_query_processing_failure(client: AsyncClient):
    """
    Test that POST /query handles exceptions from the RAG system gracefully.
    """
    with patch("backend.main.rag_system", autospec=True) as mock_rag_system:
        mock_rag_system.query.side_effect = Exception("Processing failed")

        response = await client.post(
            "/query",
            json={"question": "Test question"},
        )
        assert response.status_code == 500
        assert "Query processing failed: Processing failed" in response.json()["detail"]


async def test_query_endpoint_unpacking_error_handling(client: AsyncClient):
    """
    Test that POST /query handles ValueError and TypeError (unpacking errors) with specific hint message.
    """
    # Test ValueError (common unpacking error)
    with patch("backend.main.rag_system", autospec=True) as mock_rag_system:
        mock_rag_system.query.side_effect = ValueError("too many values to unpack (expected 2)")

        response = await client.post(
            "/query",
            json={"question": "Test question"},
        )
        assert response.status_code == 500
        assert "Query processing failed: too many values to unpack (expected 2)" in response.json()["detail"]

    # Test TypeError (another common unpacking error)
    with patch("backend.main.rag_system", autospec=True) as mock_rag_system:
        mock_rag_system.query.side_effect = TypeError("cannot unpack non-sequence NoneType")

        response = await client.post(
            "/query",
            json={"question": "Test question"},
        )
        assert response.status_code == 500
        assert "Query processing failed: cannot unpack non-sequence NoneType" in response.json()["detail"]


async def test_documents_stats_endpoint(client: AsyncClient):
    """
    Test the GET /documents/stats endpoint.
    """
    mock_stats = {
        "total_files": 10,
        "file_types": {"md": 5, "json": 3, "csv": 2},
        "total_size": 2048,
        "last_updated": "2025-01-01T00:00:00Z",
    }
    with patch("backend.main.rag_system", autospec=True) as mock_rag_system:
        mock_rag_system.get_document_stats.return_value = mock_stats
        response = await client.get("/documents/stats")
        assert response.status_code == 200
        assert response.json() == mock_stats
        mock_rag_system.get_document_stats.assert_called_once()


async def test_documents_stats_rag_unavailable(client: AsyncClient):
    """
    Test GET /documents/stats when RAG system is unavailable.
    """
    with patch("backend.main.rag_system", None):
        response = await client.get("/documents/stats")
        assert response.status_code == 503
        assert "RAG system not available" in response.json()["detail"]


async def test_documents_refresh_endpoint(client: AsyncClient):
    """
    Test the POST /documents/refresh endpoint (force=False).
    """
    with patch("backend.main.rag_system", MagicMock()):
        response = await client.post("/documents/refresh", json={"force": False})

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["message"] == "Document refresh started"
        assert response_json["force"] is False


async def test_documents_refresh_force(client: AsyncClient):
    """
    Test the POST /documents/refresh endpoint with force=True.
    """
    with patch("backend.main.rag_system", MagicMock()):
        response = await client.post("/documents/refresh", json={"force": True})

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["force"] is True


async def test_documents_types_endpoint(client: AsyncClient):
    """
    Test the GET /documents/types endpoint.
    """
    response = await client.get("/documents/types")
    assert response.status_code == 200
    response_json = response.json()
    assert "supported_types" in response_json
    assert ".json" in response_json["supported_types"]
    assert ".md" in response_json["supported_types"]


async def test_setup_endpoint(client: AsyncClient):
    """
    Test the GET /setup endpoint.
    """
    with (
        patch("os.path.exists", return_value=True),
        patch("os.listdir", return_value=["file1.json", "file2.md"]),
        patch("os.path.isfile", return_value=True),
    ):
        response = await client.get("/setup")

        assert response.status_code == 200
        response_json = response.json()
        assert "anthropic_api_key_set" in response_json
        assert response_json["public_dir_exists"] is True
        assert response_json["public_files"] == 2
