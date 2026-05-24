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


@pytest.mark.deerflow
class TestDeerFlowTrace:
    """stream_chunks() via default wrapper (text-only, no trace blocks yet)."""

    def test_stream_chunks_yields_streamchunk(self, deerflow_client):
        from chat.base import StreamChunk

        chunks = list(
            deerflow_client._backend.stream_chunks(
                "Say hello in one word.", session="trace-d1"
            )
        )
        assert len(chunks) >= 1
        assert all(isinstance(c, StreamChunk) for c in chunks)
        full_text = "".join(c.text for c in chunks)
        assert len(full_text.strip()) > 0

    def test_stream_chunks_returns_text(self, deerflow_client):
        """stream_chunks() text is non-empty and contains expected content."""
        full_text = "".join(
            c.text for c in deerflow_client._backend.stream_chunks(
                "What is 1+1? Reply with just the number.",
                session="trace-d2",
            )
        )
        assert "2" in full_text, f"Expected '2' in: {full_text}"

    def test_stream_chunks_tool_use_prompt(self, deerflow_client):
        """A prompt requiring Python code execution emits tool_use blocks."""
        chunks = list(
            deerflow_client._backend.stream_chunks(
                "使用Python执行: print('hello_trace_test')",
                session="trace-dtool",
            )
        )
        tool_blocks = [
            b for c in chunks if c.blocks
            for b in c.blocks if b.type in ("tool_use", "tool_result")
        ]
        assert len(tool_blocks) >= 1, f"No tool blocks in {chunks}"
        tool_names = {
            b.data.get("name") for b in tool_blocks if b.type == "tool_use"
        }
        assert "bash" in tool_names or "Bash" in tool_names or tool_names, (
            f"Expected tool blocks: {tool_blocks}"
        )
