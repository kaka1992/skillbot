"""Agent session — main + sub-agent with streaming."""

from __future__ import annotations

import logging
import sys
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

_log = logging.getLogger(__name__)


@dataclass
class SubAgentConfig:
    name: str
    description: str = ""
    tools: list[str] = field(default_factory=list)
    persistent: bool = False


class AgentSession:
    def __init__(self, agent: str, timeout: int):
        self._agent = agent
        self._timeout = timeout
        self._client: Any = None
        self._session_id: str = ""
        self._sub_configs: dict[str, SubAgentConfig] = {}
        self._sub_sessions: dict[str, SubAgentSession] = {}

    def init_session(self, system_prompt: str, session_key: str,
                     on_init: callable | None = None) -> None:
        if self._client is not None:
            return
        from chat import ChatClient

        self._client = ChatClient(self._agent, timeout=self._timeout)
        self._session_id = session_key
        self._client.chat(system_prompt, session=session_key)
        if on_init:
            on_init(self)
        _log.info("session init: agent=%s timeout=%ds session=%s",
                  self._agent, self._timeout, self._session_id)

    def cleanup(self) -> None:
        for sub in self._sub_sessions.values():
            sub._cleanup_all()
        if self._client and self._session_id:
            try:
                self._client.clear_session(self._session_id)
            except Exception:
                pass
        self._client = None
        self._session_id = ""

    @property
    def client(self):
        return self._client

    @property
    def session_id(self) -> str:
        return self._session_id

    # -- streaming --

    def stream(self, prompt: str, timeout: int | None = None,
               show_text: bool = True) -> str:
        return self._stream(self._client, prompt, self._session_id, timeout, show_text)

    @staticmethod
    def _stream(client, prompt: str, session: str,
                timeout: int | None = None, show_text: bool = True) -> str:
        if timeout is not None and client is not None:
            client._backend._timeout = timeout

        raw = ""
        thinking_lines: list[str] = []
        tool_names: set[str] = set()
        t0 = time.time()

        for chunk in client._backend.stream_chunks(prompt, session=session):
            if chunk.text:
                raw += chunk.text
                if show_text:
                    sys.stdout.write(chunk.text)
                    sys.stdout.flush()

            if chunk.blocks:
                for b in chunk.blocks:
                    if b.type == "thinking" and b.data:
                        t = b.data.get("thinking", "").strip()
                        if t:
                            thinking_lines.append(t)
                    elif b.type == "tool_use" and b.data:
                        name = b.data.get("name", "?")
                        if name not in tool_names:
                            tool_names.add(name)
                            _log.debug("tool_use: %s", name)
                            print(f"\n\033[90m[{name}]\033[0m")
                    elif b.type == "tool_result" and b.data:
                        pass

        elapsed = round(time.time() - t0, 1)
        print()
        if tool_names:
            print(f"\033[90m# tools: {', '.join(sorted(tool_names))}\033[0m")
        if thinking_lines:
            summary = " ".join(thinking_lines)[:200]
            print(f"\033[90m# thinking: {summary}\033[0m")
        print()

        _log.info("agent stream: session=%s elapsed=%.1fs output=%d chars tools=%d",
                  session, elapsed, len(raw), len(tool_names))
        _log.debug("agent output:\n%s", raw[:5000])
        return raw

    # -- sub-agents --

    def configure_subs(self, configs: dict[str, SubAgentConfig]) -> None:
        self._sub_configs.update(configs)

    def get_sub(self, name: str) -> SubAgentSession:
        if name not in self._sub_sessions:
            config = self._sub_configs.get(name, SubAgentConfig(name=name))
            self._sub_sessions[name] = SubAgentSession(config, self._agent, self._session_id)
        return self._sub_sessions[name]


class SubAgentSession:
    def __init__(self, config: SubAgentConfig, main_agent: str, base_id: str):
        self._config = config
        self._main_agent = main_agent
        self._base_id = base_id
        self._persistent_chat: Any = None
        self._persistent_id: str | None = None
        if config.persistent:
            from chat import ChatClient
            self._persistent_chat = ChatClient(main_agent)
            self._persistent_id = f"{base_id}_{config.name}"

    def execute(self, task: Any) -> Any:
        task.status = "in_progress"
        sid = self._resolve_session()
        client = self._get_client()
        self._ensure_seed(client, sid)
        try:
            prompt = task.metadata.get("prompt", "")
            context = task.metadata.get("context", "")
            full = f"{context}\n\n{prompt}" if context else prompt
            raw = AgentSession._stream(client, full, sid, show_text=False)
            task.metadata["results"].append(raw)
            task.status = "done"
        except Exception as e:
            _log.warning("SubAgentSession.execute failed: %s", e)
            task.status = "failed"
        finally:
            if not self._config.persistent:
                self._cleanup(client, sid)
        return task

    def _get_client(self) -> Any:
        if self._config.persistent and self._persistent_chat:
            return self._persistent_chat
        from chat import ChatClient
        return ChatClient(self._main_agent)

    def _ensure_seed(self, client, sid: str) -> None:
        """Seed sub-agent session with full capabilities prompt."""
        from agent.prompt import PromptBuilder

        try:
            client.chat(PromptBuilder.sub(), session=sid)
        except Exception:
            pass

    def _resolve_session(self) -> str:
        if self._config.persistent and self._persistent_id:
            return self._persistent_id
        return f"{self._base_id}_{self._config.name}_{uuid4().hex[:6]}"

    def _cleanup(self, client, sid: str) -> None:
        try:
            client.clear_session(sid)
        except Exception:
            pass

    def _cleanup_all(self) -> None:
        if self._config.persistent and self._persistent_chat and self._persistent_id:
            try:
                self._persistent_chat.clear_session(self._persistent_id)
            except Exception:
                pass
        self._persistent_chat = None
        self._persistent_id = None
