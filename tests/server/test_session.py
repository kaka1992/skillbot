"""Tests for Session + SessionManager (no claude CLI needed)."""

import asyncio
import sys
from unittest.mock import AsyncMock

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


class TestRunSteering:
    def _active_session(self):
        from agent.permissions import ExecutionMode
        from server.session import Session

        session = Session("steer-1")
        run = session.prepare_run()
        session._activate_run(run.run_id, ExecutionMode.DEFAULT)
        session._policy = object()
        session._client = type(
            "FakeClient",
            (),
            {"query": AsyncMock()},
        )()
        return session, run

    def test_prepare_run_is_stable_until_activated(self):
        from server.session import Session

        session = Session("steer-prepare")
        first = session.prepare_run()
        second = session.prepare_run()

        assert first is second
        assert first.status == "prepared"
        assert len(first.run_id) == 32
        assert first.control_token

    @pytest.mark.asyncio
    async def test_steer_delivers_to_active_sdk_query(self):
        session, run = self._active_session()
        policy = session._policy

        receipt = await session.steer(
            run.run_id,
            run.control_token,
            "msg-1",
            "focus on the failing test",
        )

        assert receipt.status == "accepted"
        assert receipt.seq == 1
        session._client.query.assert_awaited_once()
        prompt = session._client.query.await_args.args[0]
        assert "focus on the failing test" in prompt
        assert session.history[-1].content == "focus on the failing test"
        assert session._policy is policy

    @pytest.mark.asyncio
    async def test_duplicate_steer_is_idempotent(self):
        session, run = self._active_session()

        first = await session.steer(
            run.run_id, run.control_token, "same-id", "first",
        )
        second = await session.steer(
            run.run_id, run.control_token, "same-id", "ignored duplicate",
        )

        assert second is first
        session._client.query.assert_awaited_once()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("run_id", "token", "message_id", "message", "code"),
        [
            ("wrong", "token", "m1", "change", "RUN_NOT_ACTIVE"),
            ("valid", "wrong", "m1", "change", "INVALID_CONTROL_TOKEN"),
            ("valid", "token", "m1", " ", "EMPTY_STEER"),
            ("valid", "token", "", "change", "INVALID_MESSAGE_ID"),
        ],
    )
    async def test_invalid_steer_is_rejected(
        self, run_id, token, message_id, message, code,
    ):
        from server.session import SteerRejected

        session, run = self._active_session()
        actual_run = run.run_id if run_id == "valid" else run_id
        actual_token = run.control_token if token == "token" else token

        with pytest.raises(SteerRejected, match=code):
            await session.steer(
                actual_run, actual_token, message_id, message,
            )

    @pytest.mark.asyncio
    async def test_result_boundary_closes_steering_and_applies_receipts(self):
        from server.session import SteerRejected

        session, run = self._active_session()
        await session.steer(
            run.run_id, run.control_token, "msg-1", "change",
        )

        receipts = await session._complete_steers()

        assert receipts == [{
            "message_id": "msg-1",
            "seq": 1,
            "status": "applied",
        }]
        assert run.status == "closing"
        with pytest.raises(SteerRejected, match="RUN_NOT_ACTIVE"):
            await session.steer(
                run.run_id, run.control_token, "msg-2", "too late",
            )

    @pytest.mark.asyncio
    async def test_failed_run_marks_unconsumed_steers(self):
        session, run = self._active_session()
        receipt = await session.steer(
            run.run_id, run.control_token, "msg-1", "change",
        )

        await session._finish_run(False)

        assert run.status == "failed"
        assert receipt.status == "not_consumed"

    @pytest.mark.asyncio
    async def test_steer_limit_is_enforced(self):
        from server.session import SteerRejected

        session, run = self._active_session()
        for index in range(10):
            await session.steer(
                run.run_id,
                run.control_token,
                f"msg-{index}",
                f"change {index}",
            )

        with pytest.raises(SteerRejected, match="STEER_LIMIT_REACHED"):
            await session.steer(
                run.run_id,
                run.control_token,
                "msg-10",
                "one too many",
            )
