import pytest
from app import app
from fastapi.testclient import TestClient

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_telegram_webhook_payload_enqueued():
    payload = {
        "update_id": 99999,
        "message": {
            "chat": {"id": 12345678},
            "text": "Stripe webhook 500 error when handling zero-amount invoices"
        }
    }
    response = client.post("/webhook/telegram", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "queued"
    assert "task_id" in response.json()
