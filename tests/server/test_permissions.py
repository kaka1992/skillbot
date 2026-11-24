import asyncio
from unittest.mock import AsyncMock

import pytest

from agent.permissions import SDK_TOOLS, ExecutionMode
from server.session import Session, _build_options


@pytest.fixture
def session(monkeypatch, tmp_path):
    monkeypatch.setattr("server.session._resolve_claude_home", lambda: tmp_path)
    monkeypatch.setattr("server.session._ensure_claude_home", lambda _: None)
    monkeypatch.delenv("CLAUDE_SERVER_ALLOWED_TOOLS", raising=False)
    monkeypatch.delenv("CLAUDE_SERVER_DISALLOWED_TOOLS", raising=False)
    s = Session("test")
    s.work = tmp_path
    return s


async def gate(s, tool="Write", **data):
    result = await s._pre_tool_use(
        {"tool_name": tool, "tool_input": data, "tool_use_id": "call"}, None, {},
    )
    return result["hookSpecificOutput"]["permissionDecision"]


def test_options_no_bypass_and_no_native_delegation(session):
    options = _build_options()
    assert options.permission_mode == "default"
    assert set(options.tools) == set(SDK_TOOLS)
    assert options.allowed_tools == []
    assert not options.agents
    assert "Bash" in options.disallowed_tools
    assert options.hooks["PreToolUse"]


@pytest.mark.asyncio
async def test_request_allows_only_active_sdk_skills(session):
    skill_dir = session.work / ".claude" / "skills" / "risk-kb"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: risk-kb\ndescription: Risk knowledge.\n---\n"
    )

    options = session._request_options("default", session.work, None, None)

    assert options.skills == ["risk-kb"]
    assert await gate(session, "Skill", skill="risk-kb") == "allow"
    assert await gate(session, "Skill", skill="unknown") == "deny"


@pytest.mark.asyncio
async def test_same_hook_obeys_new_mode(session):
    options = session._request_options("execute", session.work, None, None)
    hook = options.hooks["PreToolUse"][0].hooks[0]
    data = {"tool_name": "Write", "tool_input": {"file_path": str(session.work / "artifacts/test/out.txt")}}
    assert (await hook(data, None, {}))["hookSpecificOutput"]["permissionDecision"] == "allow"
    session._request_options("plan", session.work, None, None)
    assert (await hook(data, None, {}))["hookSpecificOutput"]["permissionDecision"] == "deny"


@pytest.mark.asyncio
async def test_missing_policy_and_hook_failure_deny(session):
    assert await gate(session) == "deny"
    session._request_options("auto", session.work, None, None)
    assert await gate(session, file_path=None) == "deny"


@pytest.mark.asyncio
async def test_environment_ceiling_cannot_be_widened(session, monkeypatch):
    monkeypatch.setenv("CLAUDE_SERVER_ALLOWED_TOOLS", "Read")
    session._request_options("auto", session.work, "Read,Write,Bash", None)
    assert await gate(session, file_path=str(session.work / "artifacts/test/out.txt")) == "deny"
    assert await gate(session, "Read", file_path=str(session.work / "test.txt")) == "allow"


@pytest.mark.asyncio
async def test_permission_revoked_on_interrupt(session):
    session._request_options("auto", session.work, None, None)
    session._client = AsyncMock()
    await session.interrupt()
    assert session._policy is None
    assert await gate(session, file_path=str(session.work / "artifacts/test/out.txt")) == "deny"


@pytest.mark.asyncio
@pytest.mark.parametrize("outcome", ["success", "error", "timeout"])
async def test_chat_revokes_permission(session, outcome):
    async def send(*_):
        assert session._policy.mode is ExecutionMode.AUTO
        if outcome == "error":
            raise RuntimeError("failed")
        if outcome == "timeout":
            await asyncio.sleep(1)
        return "ok"
    session._send_inner = send
    if outcome == "success":
        assert await session.send("hello", cwd=str(session.work), execution_mode="auto") == "ok"
    else:
        with pytest.raises(RuntimeError):
            await session.send("hello", cwd=str(session.work), execution_mode="auto", timeout=0.01)
    assert session._policy is None


@pytest.mark.asyncio
@pytest.mark.parametrize("method,inner", [
    ("send_stream", "_send_inner_stream"), ("send_stream_chunks", "_send_inner_chunks"),
])
async def test_stream_disconnect_revokes_permission(session, method, inner):
    async def chunks(*_):
        from chat.base import StreamChunk
        yield "ok" if method == "send_stream" else StreamChunk(text="ok")
        await asyncio.sleep(10)
    setattr(session, inner, chunks)
    gen = getattr(session, method)("hello", cwd=str(session.work), execution_mode="auto")
    await anext(gen)
    assert session._policy is not None
    await gen.aclose()
    assert session._policy is None


@pytest.mark.parametrize("route", ["chat", "chat/stream", "chat/trace"])
def test_http_mode_validation_and_propagation(session, monkeypatch, route):
    from fastapi.testclient import TestClient
    from server.app import app, manager
    from chat.base import StreamChunk
    seen = []

    async def send(message, **kwargs):
        seen.append(kwargs["execution_mode"])
        return "ok"

    async def stream(message, **kwargs):
        seen.append(kwargs["execution_mode"])
        yield StreamChunk(text="ok") if route.endswith("trace") else "ok"

    session.send = send
    session.send_stream = stream
    session.send_stream_chunks = stream
    monkeypatch.setitem(manager._sessions, session.sid, session)
    client = TestClient(app)
    url = f"/sessions/{session.sid}/{route}"
    assert client.post(url, json={"message": "x", "execution_mode": "bypass"}).status_code == 422
    assert not seen
    assert client.post(url, json={"message": "x"}).status_code == 200
    assert client.post(url, json={"message": "x", "execution_mode": "plan"}).status_code == 200
    assert seen == [ExecutionMode.DEFAULT, ExecutionMode.PLAN]


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ["chat_stream", "chat_trace"])
async def test_http_stream_closes_session_before_unlock(session, monkeypatch, route):
    from chat.base import StreamChunk
    from server import app as server_app

    closed_under_lock = []

    async def stream(*_, **kwargs):
        try:
            yield StreamChunk(text="ok") if route == "chat_trace" else "ok"
            await asyncio.sleep(10)
        finally:
            closed_under_lock.append(session.lock.locked())

    session.send_stream = stream
    session.send_stream_chunks = stream
    monkeypatch.setitem(server_app.manager._sessions, session.sid, session)
    response = await getattr(server_app, route)(
        session.sid, server_app.ChatRequest(message="hello", execution_mode="auto"),
    )
    await anext(response.body_iterator)
    assert session.lock.locked()
    await response.body_iterator.aclose()
    assert closed_under_lock == [True]
    assert not session.lock.locked()


@pytest.mark.asyncio
@pytest.mark.parametrize("method,inner", [
    ("send_stream", "_send_inner_stream"), ("send_stream_chunks", "_send_inner_chunks"),
])
async def test_stream_cleanup_failure_still_disconnects(session, method, inner):
    from chat.base import StreamChunk

    async def chunks(*_):
        try:
            yield "ok" if method == "send_stream" else StreamChunk(text="ok")
        finally:
            raise RuntimeError("cleanup failed")

    client = AsyncMock()
    session._client = client
    setattr(session, inner, chunks)
    gen = getattr(session, method)("hello", cwd=str(session.work), execution_mode="auto")
    await anext(gen)
    with pytest.raises(RuntimeError, match="cleanup failed"):
        await gen.aclose()
    assert session._policy is None
    assert session._client is None
    client.disconnect.assert_awaited_once()
