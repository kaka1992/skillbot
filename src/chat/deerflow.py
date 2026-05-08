"""DeerFlow backend — LangGraph REST API via Gateway :8001."""

import json
import time
from collections.abc import Iterator
from typing import Optional

import requests

from .base import AbstractBackend, AgentStartupTimeout, StreamChunk, TraceBlock

DEER_PORT = 8001  # Gateway port


def _try_parse_json(v):
    """Try to parse a JSON string, returning the original value on failure."""
    if not isinstance(v, str):
        return v
    try:
        return json.loads(v)
    except (json.JSONDecodeError, TypeError):
        return v


DEER_BASE = f"http://127.0.0.1:{DEER_PORT}/api"
_AUTH_EMAIL = "admin@skillbot.com"
_AUTH_PASSWORD = "skillbot123"


class DeerFlowBackend(AbstractBackend):
    """Chat backend via deer-flow LangGraph REST API (port 8001).

    Authentication is handled automatically (initialize + login).
    Each ``session`` maps to a LangGraph ``thread_id`` for multi-turn
    context.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        auto_start: bool = True,
        timeout: int = 120,
    ) -> None:
        self._sessions: set[str] = set()
        self._model = model
        self._timeout = timeout
        self._threads: dict[str, str] = {}  # session -> thread_id
        self._session = requests.Session()
        self._csrf = ""
        self._auth_done = False

        if auto_start:
            self._ensure_running()
        self._auth_init()

    # ------------------------------------------------------------------
    # auth
    # ------------------------------------------------------------------

    def _auth_init(self) -> None:
        """Initialize admin account (first boot) + login, extract CSRF."""
        if self._auth_done:
            return

        r = self._session.get(f"{DEER_BASE}/v1/auth/setup-status")
        if r.status_code == 200 and r.json().get("needs_setup"):
            self._session.post(
                f"{DEER_BASE}/v1/auth/initialize",
                json={"email": _AUTH_EMAIL, "password": _AUTH_PASSWORD},
            )

        self._session.post(
            f"{DEER_BASE}/v1/auth/login/local",
            data={"username": _AUTH_EMAIL, "password": _AUTH_PASSWORD},
        )

        self._csrf = self._session.cookies.get("csrf_token", "")
        self._auth_done = True

    def _auth_retry(self) -> bool:
        """Re-authenticate after 401; return True if retry should proceed."""
        self._auth_done = False
        self._session.cookies.clear()
        self._auth_init()
        return bool(self._csrf)

    # ------------------------------------------------------------------
    # thread management
    # ------------------------------------------------------------------

    def _get_thread(self, session: str) -> str:
        """Get or create a LangGraph thread for the given session."""
        if session not in self._threads:
            r = self._session.post(
                f"{DEER_BASE}/threads",
                json={},
                headers={"X-CSRF-Token": self._csrf},
            )
            if r.status_code == 401 and self._auth_retry():
                r = self._session.post(
                    f"{DEER_BASE}/threads",
                    json={},
                    headers={"X-CSRF-Token": self._csrf},
                )
            r.raise_for_status()
            self._threads[session] = r.json()["thread_id"]
        return self._threads[session]

    # ------------------------------------------------------------------
    # port / health checks
    # ------------------------------------------------------------------

    @staticmethod
    def _is_port_ready(port: int) -> bool:
        try:
            requests.get(f"http://127.0.0.1:{port}/health", timeout=2)
            return True
        except Exception:
            return False

    @classmethod
    def _ensure_running(cls) -> None:
        if cls._is_port_ready(DEER_PORT):
            return
        cls._wait_port(DEER_PORT, timeout=30)

    @staticmethod
    def _wait_port(port: int, timeout: int = 30) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if DeerFlowBackend._is_port_ready(port):
                return
            time.sleep(1)
        raise AgentStartupTimeout(
            f"deer-flow port {port} not ready after {timeout}s. "
            f"Run: run.sh start deer-flow"
        )

    # ------------------------------------------------------------------
    # chat / stream
    # ------------------------------------------------------------------

    @staticmethod
    def _build_config(model: Optional[str]) -> dict:
        cfg = {}
        if model:
            cfg["model_name"] = model
        return cfg

    def chat(
        self, content: str, session: str, model: Optional[str] = None
    ) -> str:
        """Send a message. `model` overrides config.yaml's default (dynamic switching)."""
        self._sessions.add(session)
        tid = self._get_thread(session)
        r = self._session.post(
            f"{DEER_BASE}/threads/{tid}/runs/wait",
            json={
                "input": {
                    "messages": [{"role": "user", "content": content}]
                },
                "config": {
                    "configurable": self._build_config(model or self._model)
                },
            },
            headers={"X-CSRF-Token": self._csrf},
            timeout=self._timeout,
        )
        if r.status_code == 401 and self._auth_retry():
            return self.chat(content, session, model)
        r.raise_for_status()
        data = r.json()
        messages = data.get("messages") or data.get("values", {}).get(
            "messages", []
        )
        if messages:
            last = messages[-1]
            return (
                last.get("content", "")
                if isinstance(last, dict)
                else str(last)
            )
        return ""

    def stream(
        self, content: str, session: str, model: Optional[str] = None
    ) -> Iterator[str]:
        """Stream tokens. `model` overrides config.yaml's default (dynamic switching)."""
        self._sessions.add(session)
        tid = self._get_thread(session)
        r = self._session.post(
            f"{DEER_BASE}/threads/{tid}/runs/stream",
            json={
                "input": {
                    "messages": [{"role": "user", "content": content}]
                },
                "config": {
                    "configurable": self._build_config(model or self._model)
                },
                "stream_mode": ["messages-tuple"],
            },
            headers={"X-CSRF-Token": self._csrf},
            stream=True,
            timeout=self._timeout,
        )
        if r.status_code == 401 and self._auth_retry():
            yield from self.stream(content, session, model)
            return
        r.raise_for_status()
        for line in r.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue
            if line == "data: [DONE]":
                break
            try:
                chunk = json.loads(line[6:])
                if isinstance(chunk, list):
                    for item in chunk:
                        if (
                            isinstance(item, dict)
                            and item.get("type") == "AIMessageChunk"
                        ):
                            text = item.get("content", "")
                            if text:
                                yield text
            except json.JSONDecodeError:
                continue

    def stream_chunks(
        self, content: str, session: str, model: Optional[str] = None
    ) -> Iterator[StreamChunk]:
        """Stream with trace data: text + tool_use + tool_result."""
        self._sessions.add(session)
        tid = self._get_thread(session)
        r = self._session.post(
            f"{DEER_BASE}/threads/{tid}/runs/stream",
            json={
                "input": {
                    "messages": [{"role": "user", "content": content}]
                },
                "config": {
                    "configurable": self._build_config(model or self._model)
                },
                "stream_mode": ["messages-tuple"],
            },
            headers={"X-CSRF-Token": self._csrf},
            stream=True,
            timeout=self._timeout,
        )
        if r.status_code == 401 and self._auth_retry():
            yield from self.stream_chunks(content, session, model)
            return
        r.raise_for_status()
        for line in r.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue
            if line == "data: [DONE]":
                break
            try:
                chunk = json.loads(line[6:])
                if not isinstance(chunk, list):
                    continue

                text_parts: list[str] = []
                blocks: list[TraceBlock] = []
                for item in chunk:
                    if not isinstance(item, dict):
                        continue
                    msg_type = item.get("type", "")

                    # text
                    if msg_type == "AIMessageChunk":
                        if t := item.get("content", ""):
                            text_parts.append(t)
                        # tool_use chunks
                        for tc in item.get("tool_call_chunks") or []:
                            blocks.append(TraceBlock(
                                type="tool_use",
                                data={
                                    "id": tc.get("id"),
                                    "name": tc.get("name"),
                                    "input": _try_parse_json(tc.get("args")),
                                    "index": tc.get("index"),
                                },
                            ))

                    # tool results
                    elif msg_type == "ToolMessage" or msg_type == "tool":
                        blocks.append(TraceBlock(
                            type="tool_result",
                            data={
                                "tool_call_id": item.get("tool_call_id"),
                                "content": item.get("content"),
                            },
                        ))

                if text_parts or blocks:
                    yield StreamChunk(
                        text="".join(text_parts),
                        blocks=blocks or None,
                    )
            except json.JSONDecodeError:
                continue

    def list_sessions(self) -> list[str]:
        return sorted(self._sessions)

    def clear_session(self, session: str) -> None:
        self._sessions.discard(session)
        self._threads.pop(session, None)
