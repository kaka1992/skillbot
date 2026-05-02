"""Tests for base.py — error types and abstract interface."""

import pytest

from chat import ChatClient, ChatError, AgentNotInstalledError, AgentStartupTimeout


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


class TestChatClientValidation:
    def test_unknown_agent_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown agent"):
            ChatClient("not-an-agent")

    def test_valid_agents_do_not_raise(self):
        # deer-flow is always valid (doesn't need port)
        c = ChatClient("deer-flow", model="deepseek-v4-flash")
        assert c.agent == "deer-flow"
