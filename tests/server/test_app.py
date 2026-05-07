"""Tests for FastAPI app endpoints (using TestClient)."""

import json
import os
import sys

import pytest

sys.path.insert(0, "src")


def _has_real_api_key() -> bool:
    install_dir = os.environ.get("SKILL_BOT_AGENT_INSTALL_DIR", "")
    project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if install_dir:
        home = os.path.join(install_dir, "claude-code")
    else:
        home = os.path.join(project_dir, "agents", "claude-code")
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


def test_chat_stream_requires_valid_session():
    from fastapi.testclient import TestClient
    from server.app import app

    client = TestClient(app)
    resp = client.post(
        "/sessions/nonexistent/chat/stream",
        json={"message": "hello"},
    )
    assert resp.status_code == 404


def test_chat_stream_response_headers():
    """SSE endpoint returns correct Content-Type and headers."""
    from fastapi.testclient import TestClient
    from server.app import app

    client = TestClient(app)
    sid = client.post("/sessions").json()["session_id"]

    resp = client.post(
        f"/sessions/{sid}/chat/stream",
        json={"message": "Say hi in one word", "timeout": 30},
    )
    assert resp.status_code == 200
    assert resp.headers["Content-Type"] == "text/event-stream; charset=utf-8"
    assert "no-cache" in resp.headers["Cache-Control"]


def test_chat_stream_response_format():
    """SSE streaming returns properly formatted events and a done marker."""
    if not _has_real_api_key():
        pytest.skip("real API key not configured in claude settings.json")

    from fastapi.testclient import TestClient
    from server.app import app

    client = TestClient(app)
    sid = client.post("/sessions").json()["session_id"]

    resp = client.post(
        f"/sessions/{sid}/chat/stream",
        json={"message": "Say hello in one word", "timeout": 60},
    )
    assert resp.status_code == 200

    lines = resp.text.strip().split("\n")
    # Every non-empty line should start with "data: "
    data_lines = [l for l in lines if l]
    assert all(l.startswith("data: ") for l in data_lines), (
        f"Expected SSE data: prefix, got: {data_lines}"
    )

    # Parse JSON from each data line
    events = []
    for line in data_lines:
        import json
        events.append(json.loads(line[6:]))

    # At least one text event
    text_events = [e for e in events if "text" in e]
    assert len(text_events) >= 1, f"Expected text events, got: {events}"

    # Last event should be done or error
    assert events[-1].get("type") in ("done", "error"), (
        f"Last event should be done/error, got: {events[-1]}"
    )


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
