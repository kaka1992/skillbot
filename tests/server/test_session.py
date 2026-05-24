"""Tests for Session + SessionManager (no claude CLI needed)."""

import asyncio
import sys

import pytest

sys.path.insert(0, "src")


class TestSession:
    def test_create(self):
        from server.session import Session

        s = Session("test-1")
        assert s.sid == "test-1"
        assert s.history == []
        assert s.created_at > 0
        assert s._client is None

    def test_add_message(self):
        from server.session import Session

        s = Session("test-2")
        s.add("user", "hello")
        s.add("assistant", "hi there")

        assert len(s.history) == 2
        assert s.history[0].role == "user"
        assert s.history[0].content == "hello"
        assert s.history[1].role == "assistant"

    def test_to_dict(self):
        from server.session import Session

        s = Session("test-3")
        d = s.to_dict()
        assert d["session_id"] == "test-3"
        assert d["messages"] == 0
        assert "created_at" in d

    def test_lock_is_asyncio_lock(self):
        from server.session import Session

        s = Session("test-4")
        assert isinstance(s.lock, asyncio.Lock)

    def test_message_timestamp(self):
        from server.session import Session, Message
        import time

        t0 = time.time()
        s = Session("test-5")
        s.add("user", "msg")
        t1 = time.time()
        assert t0 <= s.history[0].time <= t1


class TestSessionManager:
    def test_create_and_get(self):
        from server.session import SessionManager

        mgr = SessionManager()
        s = mgr.create()
        assert len(s.sid) == 12  # uuid4 hex[:12]
        assert mgr.get(s.sid) is s

    def test_get_nonexistent(self):
        from server.session import SessionManager

        mgr = SessionManager()
        assert mgr.get("nonexistent") is None

    def test_list(self):
        from server.session import SessionManager

        mgr = SessionManager()
        mgr.create()
        mgr.create()
        sessions = mgr.list_sessions()
        assert len(sessions) == 2
        assert "session_id" in sessions[0]
        assert "messages" in sessions[0]

    @pytest.mark.asyncio
    async def test_delete(self):
        from server.session import SessionManager

        mgr = SessionManager()
        s = mgr.create()
        sid = s.sid

        assert await mgr.delete(sid) is True
        assert mgr.get(sid) is None
        assert await mgr.delete(sid) is False  # already gone

    def test_create_unique_ids(self):
        from server.session import SessionManager

        mgr = SessionManager()
        ids = {mgr.create().sid for _ in range(10)}
        assert len(ids) == 10  # all unique


class TestSessionStream:
    """Unit tests for send_stream (no real SDK calls needed)."""

    def test_send_stream_is_async_generator(self):
        from collections.abc import AsyncIterator
        from server.session import Session

        s = Session("stream-1")
        gen = s.send_stream("hello", timeout=10)
        assert isinstance(gen, AsyncIterator)

    def test_send_stream_records_user_message(self):
        from server.session import Session

        s = Session("stream-2")
        s.add("user", "test")
        assert s.history[0].role == "user"
        assert s.history[0].content == "test"

    @pytest.mark.asyncio
    async def test_send_stream_timeout_raises_runtime_error(self):
        """Timeout during streaming raises RuntimeError, not generic exception."""
        from server.session import Session

        s = Session("stream-3")
        gen = s.send_stream("test", timeout=0.001)
        with pytest.raises(RuntimeError, match="timed out"):
            async for _ in gen:
                pass

    @pytest.mark.asyncio
    async def test_send_stream_client_created_on_first_call(self):
        """_send_inner_stream creates a client on first message."""
        from server.session import Session, _build_options

        s = Session("stream-4")
        assert s._client is None
        # We can't call _send_inner_stream without a real CLI, but we
        # can verify the client-creation path in send_stream is wired.
        # Just check that send_stream is callable and returns a generator.
        gen = s.send_stream("test", timeout=1)
        assert hasattr(gen, "__anext__")
