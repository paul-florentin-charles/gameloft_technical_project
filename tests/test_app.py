import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def cleanup_db():
    db_path = os.path.join(os.path.dirname(__file__), "..", "profile_matcher.db")
    try:
        os.remove(db_path)
    except FileNotFoundError:
        pass
    except PermissionError:
        # On Windows, file locks may prevent deletion; try to remove after closing all connections
        import time

        for _ in range(5):
            try:
                os.remove(db_path)
                break
            except PermissionError:
                time.sleep(0.5)


def test_create_mock_data():
    response = client.post("/create_mock_data")
    assert response.status_code == 200
    assert "Created mock player" in response.json()["message"]


def test_get_client_config():
    # Ensure mock data exists
    client.post("/create_mock_data")
    player_id = "97983be2-98b7-11e7-90cf-082e5f28d836"
    response = client.get(f"/get_client_config/{player_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["player_id"] == player_id
    assert "active_campaigns" in data
    assert data["active_campaigns"] == ["mycampaign"]
