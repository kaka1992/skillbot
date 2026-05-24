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


class TestClaudeTrace:
    """stream_chunks() with full process trace data."""

    def test_stream_chunks_yields_streamchunk(self, claude_client):
        """stream_chunks() returns StreamChunk objects."""
        from chat.base import StreamChunk

        chunks = list(
            claude_client._backend.stream_chunks(
                "Say hello in one word.", session="trace-1"
            )
        )
        assert len(chunks) >= 1
        assert all(isinstance(c, StreamChunk) for c in chunks)
        full_text = "".join(c.text for c in chunks)
        assert len(full_text.strip()) > 0

    def test_stream_chunks_has_usage(self, claude_client):
        """stream_chunks() includes usage block with cost/tokens."""
        from chat.base import StreamChunk

        chunks = list(
            claude_client._backend.stream_chunks(
                "Say hi in one word.", session="trace-usage"
            )
        )
        usage_blocks = [
            b for c in chunks if c.blocks
            for b in c.blocks if b.type == "usage"
        ]
        assert len(usage_blocks) >= 1, f"No usage block in: {chunks}"
        usage = usage_blocks[0].data or {}
        assert "total_cost_usd" in usage
        assert "num_turns" in usage

    def test_stream_chunks_public_api(self, claude_client):
        """ChatClient.stream_chunks() public method works."""
        from chat.base import StreamChunk

        chunks = list(
            claude_client.stream_chunks(
                "Say hi in one word.", session="trace-public"
            )
        )
        assert len(chunks) >= 1
        assert all(isinstance(c, StreamChunk) for c in chunks)

    def test_stream_chunks_tool_use_prompt(self, claude_client):
        """A prompt requiring Python execution emits tool_use + tool_result blocks."""
        chunks = list(
            claude_client.stream_chunks(
                "使用Python执行: print('hello_trace_test')",
                session="trace-tool",
            )
        )
        tool_blocks = [
            b for c in chunks if c.blocks
            for b in c.blocks if b.type in ("tool_use", "tool_result")
        ]
        assert len(tool_blocks) >= 1, f"No tool blocks in {chunks}"
        tool_names = {b.data.get("name") for b in tool_blocks if b.type == "tool_use"}
        assert tool_names, f"Expected tool blocks: {tool_blocks}"


class TestClaudeSessionManagement:
    def test_list_and_clear(self, claude_client):
        c = claude_client
        c.chat("hi", session="cm-a")
        assert "cm-a" in c.list_sessions()
        c.clear_session("cm-a")
        assert "cm-a" not in c.list_sessions()
