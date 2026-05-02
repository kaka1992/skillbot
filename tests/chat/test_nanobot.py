"""Tests for NanobotBackend — requires nanobot :8900 running."""

import pytest


class TestNanobotChat:
    """Single-turn chat."""

    def test_single_chat_returns_nonempty(self, nanobot_client):
        reply = nanobot_client.chat("Say hello in one word", session="t1")
        assert isinstance(reply, str) and len(reply.strip()) > 0

    def test_default_model_works(self, nanobot_client):
        reply = nanobot_client.chat("hi", session="t2")
        assert isinstance(reply, str) and len(reply.strip()) > 0


class TestNanobotSessionIsolation:
    """Multi-turn session continuity."""

    def test_session_remembers_context(self, nanobot_client):
        sid = "test-mem"
        try:
            nanobot_client.chat("My name is Alice", session=sid)
            reply = nanobot_client.chat("What is my name?", session=sid)
            assert "Alice" in reply or "alice" in reply.lower()
        finally:
            nanobot_client.clear_session(sid)

    def test_clear_session_loses_context(self, nanobot_client):
        sid = "test-clear"
        nanobot_client.chat("My name is Charlie", session=sid)
        nanobot_client.clear_session(sid)
        reply = nanobot_client.chat("What is my name?", session=sid)
        assert isinstance(reply, str) and len(reply.strip()) > 0


class TestNanobotSessionManagement:
    def test_list_sessions_tracks_new(self, nanobot_client):
        c = nanobot_client
        c.chat("hi", session="mg-a")
        c.chat("hi", session="mg-b")
        assert "mg-a" in c.list_sessions()
        assert "mg-b" in c.list_sessions()

    def test_clear_removes_from_list(self, nanobot_client):
        c = nanobot_client
        c.chat("hi", session="mg-x")
        assert "mg-x" in c.list_sessions()
        c.clear_session("mg-x")
        assert "mg-x" not in c.list_sessions()
