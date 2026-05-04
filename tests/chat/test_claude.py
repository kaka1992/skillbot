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


class TestClaudeSessionManagement:
    def test_list_and_clear(self, claude_client):
        c = claude_client
        c.chat("hi", session="cm-a")
        assert "cm-a" in c.list_sessions()
        c.clear_session("cm-a")
        assert "cm-a" not in c.list_sessions()
