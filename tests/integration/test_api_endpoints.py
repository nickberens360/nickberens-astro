"""
E2E tests for FastAPI backend endpoints.

This module contains end-to-end tests that validate the entire request/response
lifecycle of the FastAPI application. These tests ensure that the API endpoints
are correctly configured, requests are properly processed, and responses conform
to the expected schemas, including error handling.

This is a "black box" testing approach, focusing on the API's external behavior
rather than its internal logic (which is already covered by unit and integration tests).
"""

from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Import the FastAPI app instance
from backend.main import app

# Mark the entire module to be run with asyncio
pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def client():
    """
    Pytest fixture to create an AsyncClient for making requests to the test app.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_health_check_returns_ok(client: AsyncClient):
    """
    SPEC: Verifies the GET /status endpoint returns 200 OK and correct status.
    Note: The actual endpoint is /status, not /api/health as in the original spec.
    """
    response = await client.get("/status")

    assert response.status_code == 200
    response_json = response.json()
    assert "status" in response_json
    assert response_json["status"] == "online"
    assert "app_initialized" in response_json
    assert "timestamp" in response_json


async def test_query_endpoint_successful_response(client: AsyncClient):
    """
    SPEC: Verifies the POST /query endpoint works with a valid request.
    Mocks the LLM chain to prevent external API calls.
    Note: The actual endpoint is /query, not /api/chat as in the original spec.
    The request field is 'question', not 'message'.
    """

    # Configure the mock to return a sample successful response
    async def mock_stream():
        yield "This is a mocked AI response."

    with patch("backend.routes.query.stream_with_fallback") as mock_stream_with_fallback:
        mock_stream_with_fallback.return_value = (mock_stream(), "claude-3-sonnet")

        # Make a POST request to "/query" with a valid JSON payload
        response = await client.post(
            "/query", json={"question": "Tell me about your experience", "chat_history": [], "preferred_model": None}
        )

        assert response.status_code == 200
        # For streaming responses, check the content type
        assert response.headers.get("content-type") == "text/plain; charset=utf-8"

        # Read the streamed response
        content = ""
        async for chunk in response.aiter_text():
            content += chunk

        assert "This is a mocked AI response." in content

        # Verify the mock was called
        mock_stream_with_fallback.assert_called_once()


async def test_query_endpoint_invalid_payload_returns_422(client: AsyncClient):
    """
    SPEC: Verifies the POST /query endpoint returns a 422 error for a malformed request body.
    Note: The actual endpoint is /query, not /api/chat as in the original spec.
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


async def test_query_endpoint_service_unavailable(client: AsyncClient):
    """
    Additional test: Verifies the POST /query endpoint returns 503 when retrievers are not available.
    This tests the error handling when the AI service is temporarily unavailable.
    """
    # Mock the app state to have no retrievers
    with patch.object(app.state, "retrievers", None):
        response = await client.post(
            "/query", json={"question": "Test question", "chat_history": [], "preferred_model": None}
        )

        assert response.status_code == 503
        response_json = response.json()
        assert "detail" in response_json
        assert response_json["detail"] == "AI service temporarily unavailable"


async def test_root_endpoint_returns_status(client: AsyncClient):
    """
    Additional test: Verifies the GET / endpoint returns the correct status based on app initialization.
    """
    response = await client.get("/")

    assert response.status_code == 200
    response_json = response.json()
    assert "status" in response_json
    assert response_json["status"] in ["healthy", "degraded"]


async def test_health_endpoint_returns_detailed_status(client: AsyncClient):
    """
    Additional test: Verifies the GET /health endpoint returns detailed health information.
    """
    response = await client.get("/health")

    assert response.status_code == 200
    response_json = response.json()
    assert "status" in response_json
    assert response_json["status"] in ["healthy", "degraded"]
    assert "illustration_count" in response_json
    assert isinstance(response_json["illustration_count"], int)
