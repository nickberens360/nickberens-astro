"""
Integration tests for FastAPI backend endpoints.

This module contains integration tests that validate the entire request/response
lifecycle of the FastAPI application. These tests ensure that the API endpoints
are correctly configured, requests are properly processed, and responses conform
to the expected schemas, including error handling.

This is a "black box" testing approach, focusing on the API's external behavior
rather than its internal logic (which is already covered by unit tests).
"""

import json
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

    # Mock the app state to have truthy retrievers
    mock_retrievers = {"mock": "retrievers"}

    with patch.object(app.state, "retrievers", mock_retrievers):
        with patch("backend.routes.query.stream_with_fallback") as mock_stream_with_fallback:
            mock_stream_with_fallback.return_value = (mock_stream(), "claude-3-sonnet")

            # Make a POST request to "/query" with a valid JSON payload
            response = await client.post(
                "/query",
                json={"question": "Tell me about your experience", "chat_history": [], "preferred_model": None},
            )

            assert response.status_code == 200
            # For streaming responses, check the content type
            assert response.headers.get("content-type") == "text/plain; charset=utf-8"

            # Read the streamed response
            content = ""
            async for chunk in response.aiter_text():
                content += chunk

            assert "This is a mocked AI response." in content

            # Verify the mock was called with the correct arguments
            mock_stream_with_fallback.assert_called_once_with(
                mock_retrievers,  # mocked retrievers
                [],  # formatted_chat_history
                "Tell me about your experience",  # sanitized_question
                None,  # preferred_model
            )


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


async def test_query_handles_primary_llm_failure_and_uses_fallback(client: AsyncClient):
    """
    SPEC: Verifies the /query endpoint correctly falls back to the secondary LLM
    when the primary one fails.
    """
    from unittest.mock import MagicMock

    # Create mock LLM instances
    mock_claude = MagicMock()
    mock_gemini = MagicMock()

    # Create a working mock chain for Gemini
    mock_gemini_chain = MagicMock()

    # Configure the fallback (Gemini) chain to succeed
    async def successful_stream(*args, **kwargs):
        yield "Successful response from fallback model."

    mock_gemini_chain.astream = MagicMock(side_effect=successful_stream)

    # Mock get_llm_instances to return our mock instances
    with (
        patch("backend.core.llm_chain.get_llm_instances") as mock_get_llms,
        patch("backend.core.llm_chain.create_qa_chain") as mock_create_chain,
    ):
        # Configure get_llm_instances to return both models
        mock_get_llms.return_value = {"claude": mock_claude, "gemini": mock_gemini}

        # Configure create_qa_chain to fail for Claude and succeed for Gemini
        def create_chain_side_effect(llm_instance):
            if llm_instance == mock_claude:
                raise Exception("Primary LLM service is down")
            elif llm_instance == mock_gemini:
                return mock_gemini_chain
            return MagicMock()

        mock_create_chain.side_effect = create_chain_side_effect

        # Make the API call
        response = await client.post(
            "/query", json={"question": "Does the fallback work?", "chat_history": [], "preferred_model": None}
        )

        # Assert the outcome
        # The API should handle the internal exception and still return 200 OK
        assert response.status_code == 200

        # Check that the response has the correct content type
        assert response.headers.get("content-type") == "text/plain; charset=utf-8"

        # Check that the fallback model was used (indicated in headers)
        assert response.headers.get("X-Model-Used") == "gemini"

        # Read the streamed response
        content = ""
        async for chunk in response.aiter_text():
            content += chunk

        # The response should contain the message from the fallback LLM
        assert "Successful response from fallback model." in content

        # Verify that both LLM instances were retrieved
        mock_get_llms.assert_called_once()

        # Verify that both chains were attempted (primary failed, then fallback succeeded)
        assert mock_create_chain.call_count == 2

        # Verify that the fallback chain was called and succeeded
        mock_gemini_chain.astream.assert_called_once()


@patch("backend.core.illustration_service.IllustrationService.get_all")
async def test_chat_handles_illustration_query_correctly(mock_get_all, client: AsyncClient):
    """
    SPEC: Verifies that a query for an illustration is routed to the
    illustration service and returns image data.
    """
    # 1. Configure the mock
    # This is the data we expect the illustration service to find.
    mock_image_data = [{"file": "cosmic_dragon.webp"}]
    mock_get_all.return_value = mock_image_data

    # 2. Make the API call with an image-related query
    # Note: The actual endpoint is /query, not /api/chat as in the original spec.
    # Using "show me images" which is explicitly in the all_image_phrases list
    response = await client.post(
        "/query", json={"question": "show me images", "chat_history": [], "preferred_model": None}
    )

    # 3. Assert the outcome
    assert response.status_code == 200

    # The response should contain the mocked image data in the expected format.
    # Based on the ResponseService, the response has an 'images' field with full URLs.
    response_json = response.json()
    assert "images" in response_json
    assert response_json["images"] == ["/illustrations/cosmic_dragon.webp"]
    assert "answer" in response_json
    assert "illustrations" in response_json["answer"].lower()

    # Verify that the illustration service was called
    mock_get_all.assert_called_once()


@patch("backend.core.illustration_service.IllustrationService.search")
async def test_chat_handles_specific_illustration_search_correctly(mock_search, client: AsyncClient):
    """
    SPEC: Verifies that a specific query for an illustration is routed to the
    illustration service search method and returns image data.
    """
    # 1. Configure the mock
    # This is the data we expect the illustration service to find.
    mock_image_data = [{"file": "cosmic_dragon.webp"}]
    mock_search.return_value = mock_image_data

    # 2. Make the API call with a specific image search query
    # Using "images of dragon" which should trigger SPECIFIC_IMAGE_SEARCH
    response = await client.post(
        "/query", json={"question": "images of dragon", "chat_history": [], "preferred_model": None}
    )

    # 3. Assert the outcome
    assert response.status_code == 200

    # The response should contain the mocked image data in the expected format.
    response_json = response.json()
    assert "images" in response_json
    assert response_json["images"] == ["/illustrations/cosmic_dragon.webp"]
    assert "answer" in response_json
    assert "dragon" in response_json["answer"].lower()

    # Verify that the illustration service search was called with the correct term
    mock_search.assert_called_once_with("dragon")


async def test_chat_response_includes_follow_up_questions(client: AsyncClient):
    """
    SPEC: Verifies that the /query endpoint's response correctly includes AI-generated
    follow-up questions alongside the primary chat message. This ensures the followup_service
    is properly integrated into the main chat workflow.
    """

    # 1. Configure the mocks
    # Mock the main RAG chain to return a predictable text response
    async def mock_stream():
        yield "Here is a summary of my skills."

    # Mock the follow-up service to return predictable suggestions
    mock_followup_questions = [
        "Tell me more about your frontend skills.",
        "What backend technologies do you use?",
        "Show me a relevant project.",
    ]

    # Mock the app state to have truthy retrievers
    mock_retrievers = {"mock": "retrievers"}

    with patch.object(app.state, "retrievers", mock_retrievers):
        with patch("backend.routes.query.stream_with_fallback") as mock_stream_with_fallback:
            with patch.object(app.state.followup_service, "generate_followups") as mock_generate_followups:
                with patch.object(app.state, "limiter") as mock_limiter:
                    # Configure the limiter mock to bypass rate limiting
                    mock_limiter.limit.return_value = lambda func: func

                    mock_stream_with_fallback.return_value = (mock_stream(), "claude")
                    mock_generate_followups.return_value = mock_followup_questions

                    # 2. Make the API call
                    response = await client.post(
                        "/query",
                        json={"question": "Tell me about your skills", "chat_history": [], "preferred_model": None},
                    )

                    # 3. Assert the outcome
                    assert response.status_code == 200

                    # Verify the response has the correct content type for streaming
                    assert response.headers.get("content-type") == "text/plain; charset=utf-8"

                    # Verify the model used is included in headers
                    assert response.headers.get("X-Model-Used") == "claude"

                    # Verify the follow-up questions are included in headers
                    followup_header = response.headers.get("X-Followup-Questions")
                    assert followup_header is not None

                    # Parse the JSON-encoded follow-up questions from headers
                    parsed_followups = json.loads(followup_header)
                    assert parsed_followups == mock_followup_questions

                    # Read the streamed response content
                    content = ""
                    async for chunk in response.aiter_text():
                        content += chunk

                    # Verify the main message content
                    assert "Here is a summary of my skills." in content

                    # 4. Verify service calls
                    # Verify that the LLM chain was called
                    mock_stream_with_fallback.assert_called_once_with(
                        mock_retrievers,  # mocked retrievers
                        [],  # formatted_chat_history
                        "Tell me about your skills",  # sanitized_question
                        None,  # preferred_model
                    )

                    # Verify that the follow-up service was called with correct parameters
                    mock_generate_followups.assert_called_once()
                    call_args = mock_generate_followups.call_args
                    assert call_args[0][0] == "Tell me about your skills"  # sanitized_question
                    assert call_args[0][1] == ""  # empty ai_response for text queries
                    assert call_args[0][2] == []  # sanitized_history
