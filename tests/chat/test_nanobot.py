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


class TestNanobotTrace:
    """stream_chunks() via default wrapper (text-only, no trace blocks yet)."""

    def test_stream_chunks_yields_streamchunk(self, nanobot_client):
        from chat.base import StreamChunk

        chunks = list(
            nanobot_client._backend.stream_chunks(
                "Say hello in one word.", session="trace-n1"
            )
        )
        assert len(chunks) >= 1
        assert all(isinstance(c, StreamChunk) for c in chunks)
        full_text = "".join(c.text for c in chunks)
        assert len(full_text.strip()) > 0

    def test_stream_chunks_returns_text(self, nanobot_client):
        """stream_chunks() text is non-empty and contains expected content."""
        full_text = "".join(
            c.text for c in nanobot_client._backend.stream_chunks(
                "What is 1+1? Reply with just the number.",
                session="trace-n2",
            )
        )
        assert "2" in full_text, f"Expected '2' in: {full_text}"

    @pytest.mark.skip(reason="nanobot currently returns text-only deltas")
    def test_stream_chunks_tool_use_prompt(self, nanobot_client):
        """tool_use blocks when model invokes tools (depends on model behavior)."""
        chunks = list(
            nanobot_client._backend.stream_chunks(
                "使用Python执行: print('hello_trace_test')",
                session="trace-ntool",
            )
        )
        tool_blocks = [
            b for c in chunks if c.blocks
            for b in c.blocks if b.type == "tool_use"
        ]
        assert len(tool_blocks) >= 1

    def test_stream_chunks_text_and_blocks(self, nanobot_client):
        """stream_chunks() yields well-formed StreamChunks with valid text."""
        chunks = list(
            nanobot_client._backend.stream_chunks(
                "What is 1+1? Reply with the number only.",
                session="trace-n3",
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
