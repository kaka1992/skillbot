from unittest.mock import MagicMock, patch

import pytest

from agent.session import AgentSession
from chat.claude import ClaudeBackend


@pytest.mark.parametrize("method", ["chat", "stream", "stream_chunks"])
def test_mode_reaches_http_body(method):
    backend = ClaudeBackend(auto_start=False)
    backend._server_sids["s"] = "server-s"
    backend.set_execution_mode("plan")
    response = MagicMock()
    response.json.return_value = {"reply": "ok"}
    response.iter_lines.return_value = iter(['data: {"type":"done"}'])
    health = MagicMock()
    health.json.return_value = {"permission_policy_version": 1}
    with patch("chat.claude.requests.get", return_value=health), patch(
        "chat.claude.requests.post", return_value=response,
    ) as post:
        result = getattr(backend, method)("hello", "s")
        if method != "chat":
            list(result)
        assert post.call_args.kwargs["json"]["execution_mode"] == "plan"


def test_old_server_is_rejected_before_prompt():
    backend = ClaudeBackend(auto_start=False)
    health = MagicMock()
    health.json.return_value = {"status": "ok"}
    with patch("chat.claude.requests.get", return_value=health), patch(
        "chat.claude.requests.post",
    ) as post:
        with pytest.raises(RuntimeError, match="lacks execution permissions"):
            backend.chat("hello", "s")
        post.assert_not_called()


def test_prepared_run_reaches_trace_request():
    backend = ClaudeBackend(auto_start=False)
    backend._server_sids["s"] = "server-s"
    backend._session_tokens["s"] = "session-secret"
    prepared = MagicMock()
    prepared.json.return_value = {
        "run_id": "run-1",
        "control_token": "secret",
    }
    stream = MagicMock()
    stream.iter_lines.return_value = iter(['data: {"type":"done"}'])

    with patch(
        "chat.claude.requests.post",
        side_effect=[prepared, stream],
    ) as post:
        target = backend.prepare_run("s")
        list(backend.stream_chunks("hello", "s"))

    assert target == {
        "url": (
            "http://127.0.0.1:9000/sessions/server-s/"
            "runs/run-1/steer"
        ),
        "run_id": "run-1",
        "control_token": "secret",
    }
    assert post.call_args_list[0].kwargs["json"] == {
        "session_token": "session-secret",
    }
    assert post.call_args.kwargs["json"]["run_id"] == "run-1"
    assert "s" not in backend._prepared_runs


@pytest.mark.parametrize("failure", [None, RuntimeError("error"), KeyboardInterrupt()])
def test_session_permission_scope_resets(failure):
    session = AgentSession("claude-code", 1)
    client = MagicMock()
    session._client = client
    with patch.object(session, "_stream", side_effect=failure, return_value="ok"):
        if failure:
            with pytest.raises(type(failure)):
                session.stream("hello", execution_mode="auto")
        else:
            session.stream("hello", execution_mode="auto")
    assert [c.args[0] for c in client._backend.set_execution_mode.call_args_list] == ["auto", "default"]
