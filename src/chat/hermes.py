"""Hermes backend — OpenAI-compatible REST API on port 8642."""

import os
import time
from collections.abc import Iterator
from typing import Optional

import requests

from .base import AbstractBackend, AgentStartupTimeout, ChatError

HERMES_PORT = 8642
HERMES_BASE = f"http://127.0.0.1:{HERMES_PORT}/v1"

# Resolve API key from conf/agent_conf/hermes-agent/.env
_PROJECT_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
_ENV_FILE = os.path.join(
    _PROJECT_DIR, "conf", "agent_conf", "hermes-agent", ".env"
)


def _load_api_key() -> str:
    if not os.path.exists(_ENV_FILE):
        raise ChatError(
            f"hermes-agent .env not found: {_ENV_FILE}"
        )
    for line in open(_ENV_FILE):
        line = line.strip()
        if line.startswith("API_SERVER_KEY="):
            key = line.split("=", 1)[1].strip()
            if key:
                return key
    raise ChatError(
        f"API_SERVER_KEY not found in {_ENV_FILE}"
    )


HERMES_API_KEY = _load_api_key()


class HermesBackend(AbstractBackend):
    """Chat backend via hermes-agent's OpenAI-compatible REST API (port 8642)."""

    def __init__(
        self, model: Optional[str] = None, auto_start: bool = True, timeout: int = 120
    ) -> None:
        self._sessions: set[str] = set()
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
        if cls._is_port_ready(HERMES_PORT):
            return
        cls._wait_port(HERMES_PORT, timeout=30)

    @staticmethod
    def _wait_port(port: int, timeout: int = 30) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if HermesBackend._is_port_ready(port):
                return
            time.sleep(1)
        raise AgentStartupTimeout(
            f"hermes-agent port {port} not ready after {timeout}s. "
            f"Run: run.sh start hermes-agent --no-webui"
        )

    # ------------------------------------------------------------------
    # chat / stream
    # ------------------------------------------------------------------

    @staticmethod
    def _build_body(
        model: Optional[str], content: str, stream: bool = False
    ) -> dict:
        body = {"messages": [{"role": "user", "content": content}]}
        if model:
            body["model"] = model
        if stream:
            body["stream"] = True
        return body

    @staticmethod
    def _headers(session: str) -> dict:
        return {
            "Authorization": f"Bearer {HERMES_API_KEY}",
            "X-Hermes-Session-Id": session,
        }

    def chat(
        self, content: str, session: str, model: Optional[str] = None
    ) -> str:
        """Send a message. NOTE: `model` param is ignored by hermes API server
        (always uses ~/.hermes/config.yaml). Use `run.sh start hermes-agent <model>`
        to change the active model."""
        self._sessions.add(session)
        resp = requests.post(
            f"{HERMES_BASE}/chat/completions",
            json=self._build_body(model or self._model, content),
            headers=self._headers(session),
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    def stream(
        self, content: str, session: str, model: Optional[str] = None
    ) -> Iterator[str]:
        """Stream tokens. NOTE: `model` param is ignored by hermes API server."""
        self._sessions.add(session)
        resp = requests.post(
            f"{HERMES_BASE}/chat/completions",
            json=self._build_body(model or self._model, content, stream=True),
            headers=self._headers(session),
            stream=True,
            timeout=self._timeout,
        )
        resp.raise_for_status()
        for line in resp.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue
            if line == "data: [DONE]":
                break
            try:
                import json

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
