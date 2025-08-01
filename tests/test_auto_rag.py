from unittest.mock import patch
from httpx import AsyncClient


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
        assert response_json["status"] == "processing"

        # Verify the refresh method was called
        mock_rag_system.refresh_documents.assert_called_once_with(force=False)


async def test_documents_refresh_force(client: AsyncClient):
    """
    Test the POST /documents/refresh endpoint with force=True.
    """
    with patch('backend.main.rag_system') as mock_rag_system:
        response = await client.post("/documents/refresh", json={"force": True})

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["force"] is True

        # Verify the refresh method was called with force=True
        mock_rag_system.refresh_documents.assert_called_once_with(force=True)