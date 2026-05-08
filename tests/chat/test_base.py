"""Tests for base.py — error types, trace dataclasses, abstract interface."""

import pytest

from chat import ChatClient, ChatError, AgentNotInstalledError, AgentStartupTimeout
from chat.base import StreamChunk, TraceBlock


class TestErrors:
    def test_chat_error_is_exception(self):
        assert issubclass(ChatError, Exception)

    def test_agent_not_installed_is_chat_error(self):
        assert issubclass(AgentNotInstalledError, ChatError)

    def test_agent_startup_timeout_is_chat_error(self):
        assert issubclass(AgentStartupTimeout, ChatError)

    def test_raise_agent_startup_timeout(self):
        with pytest.raises(AgentStartupTimeout):
            raise AgentStartupTimeout("test timeout")


class TestTraceDataclasses:
    """TraceBlock + StreamChunk data model tests."""

    def test_trace_block_defaults(self):
        b = TraceBlock(type="thinking")
        assert b.type == "thinking"
        assert b.data is None
        assert b.text == ""

    def test_trace_block_with_data(self):
        b = TraceBlock(type="tool_use", data={"name": "Bash", "id": "1"})
        assert b.data["name"] == "Bash"

    def test_stream_chunk_defaults(self):
        c = StreamChunk()
        assert c.text == ""
        assert c.blocks == []
        assert c.final is False

    def test_stream_chunk_with_fields(self):
        c = StreamChunk(text="hello", blocks=[
            TraceBlock(type="usage", data={"tokens": 100}),
        ], final=True)
        assert c.text == "hello"
        assert c.blocks[0].type == "usage"
        assert c.final is True

    def test_stream_chunk_blocks_default_factory(self):
        """blocks defaults to empty list, not shared across instances."""
        a = StreamChunk()
        b = StreamChunk()
        a.blocks.append(TraceBlock(type="thinking"))
        assert len(b.blocks) == 0


class TestChatClientValidation:
    def test_unknown_agent_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown agent"):
            ChatClient("not-an-agent")

    def test_valid_agents_do_not_raise(self):
        c = ChatClient("deer-flow", model="deepseek-v4-flash")
        assert c.agent == "deer-flow"

    def test_chat_client_has_stream_chunks(self):
        """ChatClient exposes stream_chunks() via public API."""
        # deer-flow backend implements stream_chunks; just check method exists
        c = ChatClient("deer-flow", model="deepseek-v4-flash")
        assert callable(c.stream_chunks)
        assert callable(c.async_stream_chunks)
