"""Tests for HermesBackend — requires hermes :8642 running with API_SERVER_KEY=1234."""

import pytest


class TestHermesChat:
    """Single-turn chat."""

    def test_single_chat(self, hermes_client):
        reply = hermes_client.chat("Say hello in one word", session="h1")
        assert isinstance(reply, str) and len(reply.strip()) > 0

    def test_default_model(self, hermes_client):
        reply = hermes_client.chat("hi", session="h2")
        assert isinstance(reply, str) and len(reply.strip()) > 0


class TestHermesSessionIsolation:
    """Multi-turn session isolation via X-Hermes-Session-Id."""

    def test_session_remembers_context(self, hermes_client):
        sid = "h-mem"
        try:
            hermes_client.chat("My name is Alice", session=sid)
            reply = hermes_client.chat("What is my name?", session=sid)
            assert "Alice" in reply or "alice" in reply.lower()
        finally:
            hermes_client.clear_session(sid)

    def test_different_sessions_are_isolated(self, hermes_client):
        a, b = "h-iso-a", "h-iso-b"
        try:
            hermes_client.chat("My name is Alice", session=a)
            hermes_client.chat("My name is Bob", session=b)
            ra = hermes_client.chat("What is my name?", session=a)
            rb = hermes_client.chat("What is my name?", session=b)
            assert "Alice" in ra or "alice" in ra.lower()
            assert "Bob" in rb or "bob" in rb.lower()
        finally:
            hermes_client.clear_session(a)
            hermes_client.clear_session(b)

    def test_clear_session_loses_context(self, hermes_client):
        sid = "h-clear"
        hermes_client.chat("My name is Charlie", session=sid)
        hermes_client.clear_session(sid)
        reply = hermes_client.chat("What is my name?", session=sid)
        assert isinstance(reply, str) and len(reply.strip()) > 0


class TestHermesSessionManagement:
    def test_list_and_clear(self, hermes_client):
        c = hermes_client
        c.chat("hi", session="hm-a")
        assert "hm-a" in c.list_sessions()
        c.clear_session("hm-a")
        assert "hm-a" not in c.list_sessions()
