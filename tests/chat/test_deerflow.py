"""Tests for DeerFlowBackend — requires deer-flow venv + DEEPSEEK_API_KEY."""

import pytest


@pytest.mark.deerflow
class TestDeerFlowChat:
    def test_single_chat(self, deerflow_client):
        reply = deerflow_client.chat("Say hello in one word", session="d1")
        assert isinstance(reply, str) and len(reply.strip()) > 0


@pytest.mark.deerflow
class TestDeerFlowSessionIsolation:
    def test_session_remembers(self, deerflow_client):
        sid = "d-mem"
        try:
            deerflow_client.chat("My name is Alice", session=sid)
            reply = deerflow_client.chat("What is my name?", session=sid)
            assert "Alice" in reply or "alice" in reply.lower()
        finally:
            deerflow_client.clear_session(sid)

    def test_sessions_isolated(self, deerflow_client):
        a, b = "d-iso-a", "d-iso-b"
        try:
            deerflow_client.chat("My name is Alice", session=a)
            deerflow_client.chat("My name is Bob", session=b)
            ra = deerflow_client.chat("What is my name?", session=a)
            rb = deerflow_client.chat("What is my name?", session=b)
            assert "Alice" in ra or "alice" in ra.lower()
            assert "Bob" in rb or "bob" in rb.lower()
        finally:
            deerflow_client.clear_session(a)
            deerflow_client.clear_session(b)


@pytest.mark.deerflow
class TestDeerFlowSessionManagement:
    def test_list_and_clear(self, deerflow_client):
        c = deerflow_client
        c.chat("hi", session="dm-a")
        assert "dm-a" in c.list_sessions()
        c.clear_session("dm-a")
        assert "dm-a" not in c.list_sessions()
