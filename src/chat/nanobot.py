from typing import Optional
"""Nanobot backend — OpenAI-compatible REST API on port 8900."""

import json
import time
import urllib.request
import urllib.error
from collections.abc import Iterator

from .base import AbstractBackend, AgentStartupTimeout

NANOBOT_PORT = 8900
NANOBOT_BASE = f"http://127.0.0.1:{NANOBOT_PORT}/v1"


class NanobotBackend(AbstractBackend):
    """Chat backend via nanobot's OpenAI-compatible REST API (port 8900)."""

    def __init__(self, model: Optional[str] = None, auto_start: bool = True, timeout: int = 120) -> None:


        self._sessions: set[str] = set()
        self._model = model
        self._timeout = timeout

        if auto_start:
            self._ensure_running()

    # ------------------------------------------------------------------
    # port / health checks
    # ------------------------------------------------------------------

    @staticmethod
    def _is_port_ready(port: int) -> bool:
        try:
            req = urllib.request.Request(
                f"http://localhost:{port}/health",
                method="GET",
            )
            urllib.request.urlopen(req, timeout=2)
            return True
        except Exception:
            return False

    @classmethod
    def _ensure_running(cls) -> None:
        if cls._is_port_ready(NANOBOT_PORT):
            return
        cls._wait_port(NANOBOT_PORT, timeout=30)

    @staticmethod
    def _wait_port(port: int, timeout: int = 30) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if NanobotBackend._is_port_ready(port):
                return
            time.sleep(1)
        raise AgentStartupTimeout(
            f"nanobot port {port} not ready after {timeout}s. "
            f"Run: run.sh start nanobot --no-webui"
        )

    # ------------------------------------------------------------------
    # chat / stream
    # ------------------------------------------------------------------


    @staticmethod
    def _build_body(model, content, stream=False):
        body = {"messages": [{"role": "user", "content": content}]}
        if model:
            body["model"] = model
        if stream:
            body["stream"] = True
        return body

    def chat(self, content: str, session: str, model: Optional[str] = None) -> str:
        """Send a message. `model` must match gateway's configured model or omit it."""
        self._sessions.add(session)
        body = json.dumps({
            **({} if (model or self._model) is None else {"model": model or self._model}),
            "messages": [{"role": "user", "content": content}],
        }).encode()
        req = urllib.request.Request(
            f"{NANOBOT_BASE}/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "skillbot/1.0",
                "X-Nanobot-Session-ID": session,
            },
        )
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"]

    def stream(self, content: str, session: str, model: Optional[str] = None) -> Iterator[str]:
        """Stream tokens. `model` must match gateway's configured model or omit it."""
        self._sessions.add(session)
        body = json.dumps({
            **({} if (model or self._model) is None else {"model": model or self._model}),
            "messages": [{"role": "user", "content": content}],
            "stream": True,
        }).encode()
        req = urllib.request.Request(
            f"{NANOBOT_BASE}/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "skillbot/1.0",
                "X-Nanobot-Session-ID": session,
            },
        )
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            for line in resp:
                line = line.decode("utf-8").strip()
                if not line.startswith("data: "):
                    continue
                if line == "data: [DONE]":
                    break
                try:
                    chunk = json.loads(line[6:])
                    delta = chunk["choices"][0]["delta"]
                    if "content" in delta:
                        yield delta["content"]
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue

    def list_sessions(self) -> list[str]:
        return sorted(self._sessions)

    def clear_session(self, session: str) -> None:
        self._sessions.discard(session)
