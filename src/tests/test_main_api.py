"""Tests for main app endpoints: root and health (packaging readiness)."""
import pytest
from fastapi.testclient import TestClient

from src.app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert "message" in data
    assert "docs" in data


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
