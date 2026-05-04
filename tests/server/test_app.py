"""Tests for FastAPI app endpoints (using TestClient)."""

import json
import os
import sys

import pytest

sys.path.insert(0, "src")


def _has_real_api_key() -> bool:
    home = os.environ.get("CLAUDE_HOME_PATH", "")
    if not home:
        return False
    try:
        with open(os.path.join(home, ".claude", "settings.json")) as f:
            cfg = json.load(f)
        token = cfg.get("env", {}).get("ANTHROPIC_AUTH_TOKEN", "")
        return bool(token) and "sk-your-" not in token
    except Exception:
        return False


def test_health():
    from fastapi.testclient import TestClient
    from server.app import app

    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "claude-code-server"


def test_create_session():
    from fastapi.testclient import TestClient
    from server.app import app

    client = TestClient(app)
    resp = client.post("/sessions")
    assert resp.status_code == 201
    data = resp.json()
    assert "session_id" in data
    assert len(data["session_id"]) == 12


def test_list_sessions():
    from fastapi.testclient import TestClient
    from server.app import app

    client = TestClient(app)
    client.post("/sessions")
    client.post("/sessions")
    resp = client.get("/sessions")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2  # may include sessions from other tests
    assert "session_id" in data[0]


def test_get_session():
    from fastapi.testclient import TestClient
    from server.app import app

    client = TestClient(app)
    sid = client.post("/sessions").json()["session_id"]
    resp = client.get(f"/sessions/{sid}")
    assert resp.status_code == 200
    assert resp.json()["session_id"] == sid


def test_get_nonexistent_session():
    from fastapi.testclient import TestClient
    from server.app import app

    client = TestClient(app)
    resp = client.get("/sessions/nonexistent")
    assert resp.status_code == 404


def test_delete_session():
    from fastapi.testclient import TestClient
    from server.app import app

    client = TestClient(app)
    sid = client.post("/sessions").json()["session_id"]
    resp = client.delete(f"/sessions/{sid}")
    assert resp.status_code == 204

    # Verify gone
    resp = client.get(f"/sessions/{sid}")
    assert resp.status_code == 404


def test_delete_nonexistent_session():
    from fastapi.testclient import TestClient
    from server.app import app

    client = TestClient(app)
    resp = client.delete("/sessions/nonexistent")
    assert resp.status_code == 404


def test_chat_requires_valid_session():
    from fastapi.testclient import TestClient
    from server.app import app

    client = TestClient(app)
    resp = client.post(
        "/sessions/nonexistent/chat",
        json={"message": "hello"},
    )
    assert resp.status_code == 404


def _has_real_api_key():
    import json, os
    home = os.environ.get("CLAUDE_HOME_PATH", "")
    if not home: return False
    p = os.path.join(home, ".claude", "settings.json")
    try:
        with open(p) as f:
            cfg = json.load(f)
        token = cfg.get("env", {}).get("ANTHROPIC_AUTH_TOKEN", "")
        return token and "sk-your-" not in token
    except Exception:
        return False


def test_chat_response_format():
    """Chat endpoint returns correct response schema even on real claude call."""
    if not _has_real_api_key():
        pytest.skip("real API key not configured in claude settings.json")

    from fastapi.testclient import TestClient
    from server.app import app

    client = TestClient(app)
    sid = client.post("/sessions").json()["session_id"]

    resp = client.post(
        f"/sessions/{sid}/chat",
        json={"message": "Say hello in one word", "timeout": 60},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == sid
    assert isinstance(data["reply"], str)
    assert len(data["reply"]) > 0
    assert data["elapsed"] >= 0


def test_history():
    if not _has_real_api_key():
        pytest.skip("real API key not configured in claude settings.json")

    from fastapi.testclient import TestClient
    from server.app import app

    client = TestClient(app)
    sid = client.post("/sessions").json()["session_id"]
    client.post(
        f"/sessions/{sid}/chat",
        json={"message": "Say hello in one word", "timeout": 60},
    )
    resp = client.get(f"/sessions/{sid}/history")
    assert resp.status_code == 200
    history = resp.json()
    assert len(history) >= 2  # user + assistant
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"
