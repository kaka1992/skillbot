"""Tests for Session + SessionManager (no claude CLI needed)."""

import asyncio
import sys

sys.path.insert(0, "src")


class TestSession:
    def test_create(self):
        from server.session import Session

        s = Session("test-1")
        assert s.sid == "test-1"
        assert s.claude_sid is None
        assert s.history == []
        assert s.created_at > 0

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
        s.claude_sid = "claude-123"
        d = s.to_dict()
        assert d["session_id"] == "test-3"
        assert d["claude_sid"] == "claude-123"
        assert d["messages"] == 0

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

    def test_delete(self):
        from server.session import SessionManager

        mgr = SessionManager()
        s = mgr.create()
        sid = s.sid

        assert mgr.delete(sid) is True
        assert mgr.get(sid) is None
        assert mgr.delete(sid) is False  # already gone

    def test_create_unique_ids(self):
        from server.session import SessionManager

        mgr = SessionManager()
        ids = {mgr.create().sid for _ in range(10)}
        assert len(ids) == 10  # all unique
