import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_telegram_webhook_ingest():
    payload = {
        "update_id": 1001,
        "message": {
            "chat": {"id": 123456},
            "text": "CRITICAL: Stripe checkout fails on null email callback"
        }
    }
    response = client.post("/webhook/telegram", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "queued"
