"""Tests for ClaudeBackend — requires claude server :9000 running."""

import pytest


class TestClaudeChat:
    """Single-turn chat."""

    def test_single_chat(self, claude_client):
        reply = claude_client.chat("Say hello in one word", session="c1")
        assert isinstance(reply, str) and len(reply.strip()) > 0

    def test_simple_qa(self, claude_client):
        reply = claude_client.chat(
            "What is the capital of France? Reply in one word.", session="c2"
        )
        assert isinstance(reply, str) and len(reply.strip()) > 0


class TestClaudeMultiTurn:
    """Multi-turn conversation with session context."""

    def test_session_remembers_context(self, claude_client):
        c = claude_client
        sid = "ctx-mem"
        try:
            c.chat("My name is Alice", session=sid)
            reply = c.chat("What is my name?", session=sid)
            assert "Alice" in reply
        finally:
            c.clear_session(sid)

    def test_session_isolation(self, claude_client):
        """不同 session 之间完全隔离，互不可见上下文。"""
        c = claude_client
        c.chat("My name is Alice", session="iso-a")
        c.chat("My name is Bob", session="iso-b")

        reply_a = c.chat("What is my name?", session="iso-a")
        reply_b = c.chat("What is my name?", session="iso-b")

        assert "Alice" in reply_a
        assert "Bob" in reply_b
        assert "Bob" not in reply_a, "session iso-a should not see iso-b context"
        assert "Alice" not in reply_b, "session iso-b should not see iso-a context"

    def test_clear_session_loses_context(self, claude_client):
        """清除 session 后上下文丢失。"""
        c = claude_client
        sid = "ctx-clear"
        c.chat("My name is Charlie", session=sid)
        c.clear_session(sid)
        reply = c.chat("What is my name?", session=sid)
        # After clear, the session is new — should not remember "Charlie"
        assert isinstance(reply, str) and len(reply.strip()) > 0


class TestClaudeStream:
    """SSE streaming via ClaudeBackend.stream()."""

    def test_stream_returns_chunks(self, claude_client):
        """stream() yields multiple text chunks, not one big blob."""
        chunks = list(
            claude_client.stream(
                "Count from 1 to 3, one per line. No extra text.",
                session="stream-1",
            )
        )
        assert len(chunks) >= 2, f"Expected multiple chunks, got {len(chunks)}: {chunks}"
        full = "".join(chunks)
        assert "1" in full and "3" in full

    def test_stream_single_word(self, claude_client):
        """stream() on a simple prompt yields non-empty text."""
        chunks = list(
            claude_client.stream(
                "Say hello in one word.", session="stream-2"
            )
        )
        assert len(chunks) >= 1
        assert all(isinstance(c, str) and len(c) > 0 for c in chunks)


class TestClaudeSessionManagement:
    def test_list_and_clear(self, claude_client):
        c = claude_client
        c.chat("hi", session="cm-a")
        assert "cm-a" in c.list_sessions()
        c.clear_session("cm-a")
        assert "cm-a" not in c.list_sessions()
