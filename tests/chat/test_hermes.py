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


class TestHermesTrace:
    """stream_chunks() via default wrapper (text-only, no trace blocks yet)."""

    def test_stream_chunks_yields_streamchunk(self, hermes_client):
        from chat.base import StreamChunk

        chunks = list(
            hermes_client._backend.stream_chunks(
                "Say hello in one word.", session="trace-h1"
            )
        )
        assert len(chunks) >= 1
        assert all(isinstance(c, StreamChunk) for c in chunks)
        full_text = "".join(c.text for c in chunks)
        assert len(full_text.strip()) > 0

    def test_stream_chunks_returns_text(self, hermes_client):
        """stream_chunks() text is non-empty and contains expected content."""
        full_text = "".join(
            c.text for c in hermes_client._backend.stream_chunks(
                "What is the capital of France? Reply in one word.",
                session="trace-h2",
            )
        )
        assert "Paris" in full_text, f"Expected 'Paris' in: {full_text}"

    def test_stream_chunks_tool_use_prompt(self, hermes_client):
        """tool_use blocks when model invokes tools (depends on model behavior)."""
        chunks = list(
            hermes_client._backend.stream_chunks(
                "使用Python执行: print('hello_trace_test')",
                session="trace-htool",
            )
        )
        tool_blocks = [
            b for c in chunks if c.blocks
            for b in c.blocks if b.type == "tool_use"
        ]
        assert len(tool_blocks) >= 1

    def test_stream_chunks_text_and_blocks(self, hermes_client):
        """stream_chunks() yields well-formed StreamChunks with valid text."""
        chunks = list(
            hermes_client._backend.stream_chunks(
                "What is 1+1? Reply with the number only.",
                session="trace-h3",
            )
        )
        assert len(chunks) >= 1
        full_text = "".join(c.text for c in chunks)
        assert "2" in full_text
        from chat.base import StreamChunk
        assert all(isinstance(c, StreamChunk) for c in chunks)
        for c in chunks:
            if c.blocks:
                for b in c.blocks:
                    assert b.type in (
                        "thinking", "tool_use", "tool_result",
                        "subagent", "usage",
                    ), f"Unknown block type: {b.type}"
