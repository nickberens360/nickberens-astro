"""
Integration tests for FastAPI backend endpoints - Updated for Auto-RAG implementation.

This module contains integration tests that validate the entire request/response
lifecycle of the Auto-RAG FastAPI application. These tests ensure that the API endpoints
are correctly configured, requests are properly processed, and responses conform
to the expected schemas.
"""

from typing import List
from unittest.mock import patch

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
    assert response_json["status"] in ["healthy", "degraded"]


async def test_query_endpoint_successful_response(client: AsyncClient):
    """
    Test that the POST /query endpoint works with a valid request.
    Mocks the Auto-RAG system to prevent external API calls.
    """
    # Test data constants
    test_question = "Tell me about your experience"
    expected_response = "This is a mocked AI response."
    empty_chat_history: List[dict] = []
    preferred_model = "claude"

    # Mock the rag_system to return a sample response
    with patch('backend.main.rag_system') as mock_rag_system:
        mock_rag_system.query.return_value = expected_response
        mock_rag_system.get_document_stats.return_value = {
            "total_files": 5,
            "file_types": {"md": 3, "json": 2},
            "total_size": 1024,
            "last_updated": "2025-01-01T00:00:00Z"
        }
        mock_rag_system.get_model_name.return_value = "claude-3-sonnet"

        # Make a POST request to "/query" with a valid JSON payload
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

        # Check response structure matches QueryResponse model
        assert "response" in response_json
        assert "sources" in response_json
        assert "document_stats" in response_json
        assert "model_used" in response_json

        # Check response content
        assert response_json["response"] == expected_response
        assert response_json["model_used"] == "claude-3-sonnet"
        assert isinstance(response_json["sources"], list)
        assert isinstance(response_json["document_stats"], dict)

        # Verify the mock was called with the correct arguments
        mock_rag_system.query.assert_called_once()
        mock_rag_system.get_document_stats.assert_called_once()


async def test_query_endpoint_invalid_payload_returns_422(client: AsyncClient):
    """
    Test that the POST /query endpoint returns a 422 error for a malformed request body.
    """
    # Make a POST request to "/query" with an INVALID JSON payload
    response = await client.post("/query", json={"wrong_key": "some value"})  # Missing required 'question' field

    assert response.status_code == 422
    response_json = response.json()
    assert "detail" in response_json

    # Check that the validation error mentions the missing field
    detail = response_json["detail"]
    assert isinstance(detail, list)
    assert len(detail) > 0

    # Find the error for the missing 'question' field
    question_error = next((error for error in detail if error.get("loc") == ["body", "question"]), None)
    assert question_error is not None
    assert question_error["type"] == "missing"


async def test_query_endpoint_auto_rag_unavailable(client: AsyncClient):
    """
    Test that the POST /query endpoint returns 503 when Auto-RAG system is not available.
    """
    # Test data constants
    test_question = "Test question"
    empty_chat_history: List[dict] = []
    preferred_model = "claude"

    # Mock AUTO_RAG_AVAILABLE to be False
    with patch('backend.main.AUTO_RAG_AVAILABLE', False):
        response = await client.post(
            "/query",
            json={
                "question": test_question,
                "chat_history": empty_chat_history,
                "preferred_model": preferred_model
            },
        )

        assert response.status_code == 503
        response_json = response.json()
        assert "detail" in response_json
        assert "Auto RAG system not available" in response_json["detail"]


async def test_query_endpoint_rag_system_not_initialized(client: AsyncClient):
    """
    Test that the POST /query endpoint returns 503 when RAG system is not initialized.
    """
    # Test data constants
    test_question = "Test question"
    empty_chat_history: List[dict] = []
    preferred_model = "claude"

    # Mock rag_system to be None (not initialized)
    with patch('backend.main.rag_system', None):
        response = await client.post(
            "/query",
            json={
                "question": test_question,
                "chat_history": empty_chat_history,
                "preferred_model": preferred_model
            },
        )

        assert response.status_code == 503
        response_json = response.json()
        assert "detail" in response_json
        assert "RAG system not initialized" in response_json["detail"]


async def test_query_endpoint_with_chat_history(client: AsyncClient):
    """
    Test that the POST /query endpoint properly handles chat history.
    """
    # Test data constants
    test_question = "Follow up question"
    expected_response = "Response with context"
    chat_history = [
        {"sender": "user", "text": "Previous question"},
        {"sender": "assistant", "text": "Previous response"}
    ]
    preferred_model = "claude"

    # Mock the rag_system
    with patch('backend.main.rag_system') as mock_rag_system:
        mock_rag_system.query.return_value = expected_response
        mock_rag_system.get_document_stats.return_value = {"total_files": 1}
        mock_rag_system.get_model_name.return_value = "claude-3-sonnet"

        response = await client.post(
            "/query",
            json={
                "question": test_question,
                "chat_history": chat_history,
                "preferred_model": preferred_model,
            },
        )

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["response"] == expected_response

        # Verify that query was called (chat history should be included in the full_question)
        mock_rag_system.query.assert_called_once()
        # The actual call should include context from chat history
        call_args = mock_rag_system.query.call_args[0][0]
        assert test_question in call_args
        assert "Previous question" in call_args or "previous conversation" in call_args.lower()


async def test_query_endpoint_query_processing_failure(client: AsyncClient):
    """
    Test that the POST /query endpoint handles query processing failures gracefully.
    """
    test_question = "Test question"

    # Mock the rag_system to raise an exception
    with patch('backend.main.rag_system') as mock_rag_system:
        mock_rag_system.query.side_effect = Exception("Processing failed")

        response = await client.post(
            "/query",
            json={
                "question": test_question,
                "chat_history": [],
                "preferred_model": "claude",
            },
        )

        assert response.status_code == 500
        response_json = response.json()
        assert "detail" in response_json
        assert "Query processing failed" in response_json["detail"]


async def test_documents_stats_endpoint(client: AsyncClient):
    """
    Test the GET /documents/stats endpoint.
    """
    mock_stats = {
        "total_files": 10,
        "file_types": {"md": 5, "json": 3, "csv": 2},
        "total_size": 2048,
        "last_updated": "2025-01-01T00:00:00Z"
    }

    with patch('backend.main.rag_system') as mock_rag_system:
        mock_rag_system.get_document_stats.return_value = mock_stats

        response = await client.get("/documents/stats")

        assert response.status_code == 200
        response_json = response.json()

        # Check that all expected fields are present
        assert "total_files" in response_json
        assert "file_types" in response_json
        assert "total_size" in response_json
        assert "last_updated" in response_json

        # Check values match
        assert response_json["total_files"] == 10
        assert response_json["file_types"] == {"md": 5, "json": 3, "csv": 2}


async def test_documents_stats_rag_unavailable(client: AsyncClient):
    """
    Test the GET /documents/stats endpoint when RAG system is unavailable.
    """
    with patch('backend.main.rag_system', None):
        response = await client.get("/documents/stats")

        assert response.status_code == 503
        response_json = response.json()
        assert "detail" in response_json
        assert "RAG system not available" in response_json["detail"]


async def test_documents_refresh_endpoint(client: AsyncClient):
    """
    Test the POST /documents/refresh endpoint.
    """
    with patch('backend.main.rag_system') as mock_rag_system:
        response = await client.post("/documents/refresh", json={"force": False})

        assert response.status_code == 200
        response_json = response.json()

        assert "message" in response_json
        assert "force" in response_json
        assert "status" in response_json
        assert response_json["message"] == "Document refresh started"
        assert response_json["force"] is False
        mock_rag_system.refresh_documents.assert_called_once_with(force=False)
        assert response_json["status"] == "processing"


async def test_documents_refresh_force(client: AsyncClient):
    """
    Test the POST /documents/refresh endpoint with force=True.
    """
    with patch('backend.main.rag_system') as mock_rag_system:
        response = await client.post("/documents/refresh", json={"force": True})

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["force"] is True
        mock_rag_system.refresh_documents.assert_called_once_with(force=False)


async def test_documents_types_endpoint(client: AsyncClient):
    """
    Test the GET /documents/types endpoint.
    """
    response = await client.get("/documents/types")

    assert response.status_code == 200
    response_json = response.json()

    assert "supported_types" in response_json
    assert "note" in response_json
    assert "auto_rag_available" in response_json

    # Check that some expected file types are listed
    supported_types = response_json["supported_types"]
    assert ".json" in supported_types
    assert ".csv" in supported_types
    assert ".md" in supported_types


async def test_setup_endpoint(client: AsyncClient):
    """
    Test the GET /setup endpoint.
    """
    with patch('os.path.exists', return_value=True), \
         patch('os.listdir', return_value=['file1.json', 'file2.md']):

        response = await client.get("/setup")

        assert response.status_code == 200
        response_json = response.json()

        assert "auto_rag_available" in response_json
        assert "anthropic_api_key_set" in response_json
        assert "installation_command" in response_json
        assert "env_vars_needed" in response_json
        assert "public_dir_exists" in response_json
        assert "public_files" in response_json


async def test_illustrations_legacy_endpoint(client: AsyncClient):
    """
    Test the legacy GET /illustrations endpoint.
    """
    with patch('backend.main.rag_system') as mock_rag_system:
        mock_rag_system.query.return_value = "Here are some illustrations from Nick's collection..."

        response = await client.get("/illustrations")

        assert response.status_code == 200
        response_json = response.json()

        assert "message" in response_json
        assert "query_example" in response_json
        assert "response_preview" in response_json
        assert "auto-discovered" in response_json["message"]


async def test_illustrations_legacy_endpoint_rag_unavailable(client: AsyncClient):
    """
    Test the legacy GET /illustrations endpoint when RAG is unavailable.
    """
    with patch('backend.main.rag_system', None):
        response = await client.get("/illustrations")

        assert response.status_code == 200
        response_json = response.json()

        assert "message" in response_json
        assert "install_command" in response_json
        assert "not available" in response_json["message"]


async def test_query_request_validation(client: AsyncClient):
    """
    Test various query request validation scenarios.
    """
    # Test with minimal valid request
    response = await client.post(
        "/query",
        json={"question": "Simple question"}
    )
    # Should succeed (other fields have defaults)
    assert response.status_code in [200, 503]  # 503 if RAG system not available

    # Test with all fields
    with patch('backend.main.rag_system') as mock_rag_system:
        mock_rag_system.query.return_value = "Response"
        mock_rag_system.get_document_stats.return_value = {}
        mock_rag_system.get_model_name.return_value = "claude"

        response = await client.post(
            "/query",
            json={
                "question": "Test question",
                "chat_history": [{"sender": "user", "text": "Hello"}],
                "preferred_model": "gemini",
                "max_results": 10,
                "include_sources": False
            }
        )
        assert response.status_code == 200


async def test_query_with_context_building(client: AsyncClient):
    """
    Test that queries with chat history properly build context.
    """
    chat_history = [
        {"sender": "user", "text": "What is Nick's background?"},
        {"sender": "assistant", "text": "Nick is a software engineer..."},
        {"sender": "user", "text": "What about his projects?"}
    ]

    with patch('backend.main.rag_system') as mock_rag_system:
        mock_rag_system.query.return_value = "Based on the context..."
        mock_rag_system.get_document_stats.return_value = {}
        mock_rag_system.get_model_name.return_value = "claude"

        response = await client.post(
            "/query",
            json={
                "question": "Tell me more about that",
                "chat_history": chat_history,
            }
        )

        assert response.status_code == 200

        # Verify that the query was called with context
        mock_rag_system.query.assert_called_once()
        full_question = mock_rag_system.query.call_args[0][0]

        # Should include context and current question
        assert "Tell me more about that" in full_question
        assert "Previous conversation context:" in full_question or any(msg["text"] in full_question for msg in chat_history)