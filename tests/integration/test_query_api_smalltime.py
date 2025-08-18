import pytest
from typing import Any, Dict
from fastapi.testclient import TestClient


@pytest.mark.integration
def test_query_api_smalltime():
    # Importing here ensures app state is initialized as in production
    from backend.main import app

    client = TestClient(app)
    payload: Dict[str, Any] = {
        "question": "Tell me about the 'Smalltime' illustration",
        "chat_history": [],
        "preferred_model": None,
    }
    resp = client.post("/query", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    # Ensure images list is present and contains the Smalltime illustration
    assert "images" in data and isinstance(data["images"], list)
    assert any("smalltime" in img.lower() for img in data["images"]), data
