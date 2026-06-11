"""Claude backend — HTTP wrapper server on port 9000."""

import json
import logging
import signal
import time

# Signal-aware interrupt: SIGINT sets a flag checked on SSE read timeouts.
# macOS doesn't reliably deliver SIGINT during blocking C-level socket reads,
# so we use a short read timeout + flag check as a workaround.
_sigint_flag = False


def _sigint_handler(signum, frame):
    global _sigint_flag
    _sigint_flag = True
    signal.signal(signal.SIGINT, _sigint_handler)  # re-register


signal.signal(signal.SIGINT, _sigint_handler)
from collections.abc import Iterator
from typing import Optional

import requests

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
        self._model = model
        self._timeout = timeout

        if auto_start:
            self._ensure_running()

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
        if session not in self._server_sids:
            try:
                resp = requests.post(f"{CLAUDE_BASE}/sessions", timeout=5)
                if resp.status_code == 201:
                    self._server_sids[session] = resp.json()["session_id"]
                else:
                    self._server_sids[session] = f"chat-{session}"
            except Exception:
                self._server_sids[session] = f"chat-{session}"
        return self._server_sids[session]

    # ------------------------------------------------------------------
    # chat / stream
    # ------------------------------------------------------------------

    def chat(
        self, content: str, session: str, model: Optional[str] = None
    ) -> str:
        """Send a message. `model` is ignored (Claude Code uses .claude/settings.json)."""
        self._sessions.add(session)
        sid = self._get_session(session)
        resp = requests.post(
            f"{CLAUDE_BASE}/sessions/{sid}/chat",
            json={"message": content, "timeout": self._timeout},
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
            json={"message": content, "timeout": self._timeout},
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
        resp = requests.post(
            f"{CLAUDE_BASE}/sessions/{sid}/chat/trace",
            json={"message": content, "timeout": self._timeout},
            timeout=(5, 2),  # 5s connect, 2s read — check signals every 2s
            stream=True,
        )
        resp.raise_for_status()
        text_parts: list[str] = []
        blocks: list[TraceBlock] = []
        try:
            from requests.exceptions import ReadTimeout, ConnectionError as ReqConnError
            lines = resp.iter_lines(decode_unicode=True)
            retries = 0
            while True:
                try:
                    line = next(lines)
                    retries = 0  # reset on success
                except (ReadTimeout, ReqConnError):
                    retries += 1
                    global _sigint_flag
                    if _sigint_flag:
                        _sigint_flag = False
                        raise KeyboardInterrupt()
                    if retries > 300:  # 10 minutes at 2s timeout
                        raise
                    continue
                except StopIteration:
                    break
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
        if session in self._server_sids:
            sid = self._server_sids.pop(session)
            try:
                requests.delete(f"{CLAUDE_BASE}/sessions/{sid}", timeout=5)
            except Exception:
                pass
