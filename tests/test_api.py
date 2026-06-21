from __future__ import annotations

import pytest
import httpx
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["app"] == "myScholar"


def test_chat_offline_demo():
    resp = client.post("/api/chat", json={
        "session_id": "test-session",
        "message": "What are the five pillars of Islam?",
        "madhab": "general",
        "stream": False,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert len(data["answer"]) > 10


def test_image_moderation_blocks_prophet():
    resp = client.post("/api/images", json={
        "session_id": "test",
        "prompt": "Draw a picture of Prophet Muhammad",
        "style": "geometric",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["moderation"]["allowed"] is False


def test_image_allowed_geometric():
    resp = client.post("/api/images", json={
        "session_id": "test",
        "prompt": "Islamic geometric art pattern",
        "style": "geometric",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["moderation"]["allowed"] is True
    assert data["image_url"] != ""


def test_session_clear():
    resp = client.post("/api/sessions/test-session/clear")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cleared"


def test_search_endpoint():
    resp = client.get("/api/search?q=prayer&top_k=3")
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
