"""Claude backend — HTTP wrapper server on port 9000."""

import json
import logging
import time
from collections.abc import Iterator
from typing import Optional

import requests

from agent.permissions import ExecutionMode
from .base import AbstractBackend, AgentStartupTimeout, StreamChunk, TraceBlock

_log = logging.getLogger(__name__)

CLAUDE_PORT = 9000
CLAUDE_BASE = f"http://127.0.0.1:{CLAUDE_PORT}"


class ClaudeBackend(AbstractBackend):
    """Chat backend via Claude Code HTTP server (port 9000).

    Requires ``src/server/app.py`` running::

        python3 -c "from server.app import main; main()"

    Multi-turn context is managed server-side via session IDs.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        auto_start: bool = True,
        timeout: int = 300,
    ) -> None:
        self._sessions: set[str] = set()
        self._server_sids: dict[str, str] = {}  # client session → server sid
        self._session_tokens: dict[str, str] = {}
        self._prepared_runs: dict[str, dict] = {}
        self._model = model
        self._timeout = timeout
        self._execution_mode = ExecutionMode.DEFAULT

        if auto_start:
            self._ensure_running()

    def set_execution_mode(self, mode: str) -> None:
        self._execution_mode = ExecutionMode(mode)

    @staticmethod
    def _is_port_ready(port: int) -> bool:
        try:
            requests.get(f"http://127.0.0.1:{port}/health", timeout=2)
            return True
        except Exception:
            return False

    @classmethod
    def _ensure_running(cls) -> None:
        if cls._is_port_ready(CLAUDE_PORT):
            return
        cls._wait_port(CLAUDE_PORT, timeout=30)

    @staticmethod
    def _wait_port(port: int, timeout: int = 30) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if ClaudeBackend._is_port_ready(port):
                return
            time.sleep(1)
        raise AgentStartupTimeout(
            f"Claude Code server port {port} not ready after {timeout}s. "
            f"Start it: python3 -c 'from server.app import main; main()'"
        )

    # ------------------------------------------------------------------
    # session management
    # ------------------------------------------------------------------

    def _get_session(self, session: str) -> str:
        """Return cached server-side session ID, creating one on first call."""
        health = requests.get(f"{CLAUDE_BASE}/health", timeout=5)
        health.raise_for_status()
        if health.json().get("permission_policy_version") != 1:
            raise RuntimeError("Claude server lacks execution permissions; restart the updated server")
        if session not in self._server_sids:
            try:
                resp = requests.post(f"{CLAUDE_BASE}/sessions", timeout=5)
                if resp.status_code == 201:
                    data = resp.json()
                    self._server_sids[session] = data["session_id"]
                    self._session_tokens[session] = data["session_token"]
                else:
                    self._server_sids[session] = f"chat-{session}"
            except Exception:
                self._server_sids[session] = f"chat-{session}"
        return self._server_sids[session]

    # ------------------------------------------------------------------
    # chat / stream
    # ------------------------------------------------------------------

    def prepare_run(self, session: str) -> dict:
        """Create a token-scoped steering target for the next streamed query."""
        sid = self._get_session(session)
        resp = requests.post(
            f"{CLAUDE_BASE}/sessions/{sid}/runs",
            json={"session_token": self._session_tokens.get(session, "")},
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
        target = {
            "url": (
                f"{CLAUDE_BASE}/sessions/{sid}/runs/"
                f"{data['run_id']}/steer"
            ),
            "run_id": data["run_id"],
            "control_token": data["control_token"],
        }
        self._prepared_runs[session] = target
        return target

    def chat(
        self, content: str, session: str, model: Optional[str] = None
    ) -> str:
        """Send a message. `model` is ignored (Claude Code uses .claude/settings.json)."""
        self._sessions.add(session)
        sid = self._get_session(session)
        resp = requests.post(
            f"{CLAUDE_BASE}/sessions/{sid}/chat",
            json={"message": content, "timeout": self._timeout,
                  "execution_mode": self._execution_mode.value},
            timeout=self._timeout + 10,
        )
        resp.raise_for_status()
        return resp.json().get("reply", "")

    def stream(
        self, content: str, session: str, model: Optional[str] = None
    ) -> Iterator[str]:
        self._sessions.add(session)
        sid = self._get_session(session)
        resp = requests.post(
            f"{CLAUDE_BASE}/sessions/{sid}/chat/stream",
            json={"message": content, "timeout": self._timeout,
                  "execution_mode": self._execution_mode.value},
            timeout=self._timeout + 10,
            stream=True,
        )
        resp.raise_for_status()
        for line in resp.iter_lines(decode_unicode=True):
            if not line.startswith("data: "):
                continue
            data = json.loads(line[6:])
            if text := data.get("text"):
                yield text
            elif data.get("type") == "error":
                raise RuntimeError(data["error"])
            elif data.get("type") == "done":
                return

    def stream_chunks(
        self, content: str, session: str, model: Optional[str] = None
    ) -> Iterator[StreamChunk]:
        """Stream with trace data (thinking, tool_use, subagent, usage)."""
        self._sessions.add(session)
        sid = self._get_session(session)
        target = self._prepared_runs.pop(session, None)
        resp = requests.post(
            f"{CLAUDE_BASE}/sessions/{sid}/chat/trace",
            json={"message": content, "timeout": self._timeout,
                  "execution_mode": self._execution_mode.value,
                  "run_id": target.get("run_id") if target else None},
            timeout=self._timeout + 10,
            stream=True,
        )
        resp.raise_for_status()
        text_parts: list[str] = []
        blocks: list[TraceBlock] = []
        try:
            for line in resp.iter_lines(decode_unicode=True):
                if not line.startswith("data: "):
                    continue
                data = json.loads(line[6:])
                event_type = data.get("type")
                if event_type == "text":
                    text_parts.append(data.get("text", ""))
                elif event_type == "error":
                    raise RuntimeError(data["error"])
                elif event_type == "done":
                    if text_parts or blocks:
                        yield StreamChunk(
                            text="".join(text_parts), blocks=blocks or None
                        )
                    return
                else:
                    # trace event: thinking, tool_use, tool_result, subagent, usage
                    # flush accumulated text first
                    if text_parts:
                        yield StreamChunk(text="".join(text_parts))
                        text_parts.clear()
                    blocks.append(TraceBlock(
                        type=event_type,
                        data=data.get("data"),
                    ))
            if text_parts or blocks:
                yield StreamChunk(text="".join(text_parts), blocks=blocks or None)
        finally:
            resp.close()

    def interrupt(self, session: str) -> None:
        """POST /sessions/{sid}/interrupt — signal subprocess to stop."""
        sid = self._server_sids.get(session)
        if not sid:
            return
        try:
            resp = requests.post(f"{CLAUDE_BASE}/sessions/{sid}/interrupt", timeout=5)
            if resp.status_code != 200:
                _log.warning("claude interrupt: session=%s sid=%s status=%d body=%s",
                             session, sid, resp.status_code, resp.text[:200])
        except Exception:
            _log.exception("claude interrupt failed: session=%s sid=%s", session, sid)

    def list_sessions(self) -> list[str]:
        return sorted(self._sessions)

    def clear_session(self, session: str) -> None:
        self._sessions.discard(session)
        self._prepared_runs.pop(session, None)
        self._session_tokens.pop(session, None)
        if session in self._server_sids:
            sid = self._server_sids.pop(session)
            try:
                requests.delete(f"{CLAUDE_BASE}/sessions/{sid}", timeout=5)
            except Exception:
                pass
