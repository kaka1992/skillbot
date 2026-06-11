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
        try:
            # Drain the full system-prompt response so the session is clean for queries
            for _ in self._client.stream(system_prompt, session=session_key):
                pass
        except KeyboardInterrupt:
            _log.warning("session init: interrupted, clearing client for retry")
            self._client = None
            self._session_id = ""
            raise
        except Exception:
            _log.warning("session init: stream failed, clearing client for retry", exc_info=True)
            self._client = None
            self._session_id = ""
            return
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

    def interrupt(self) -> None:
        """Interrupt the current streaming query, preserving context."""
        if self._client and self._session_id:
            self._client.interrupt(self._session_id)

    # -- streaming --

    def stream(self, prompt: str, timeout: int | None = None,
               show_text: bool = True, on_chunk=None, on_thinking=None) -> str:
        if self._client:
            prompt = self._client._maybe_inject_skills(prompt)
        return self._stream(self._client, prompt, self._session_id, timeout, show_text, on_chunk, on_thinking)

    @staticmethod
    def _stream(
        client, prompt: str, session: str,
        timeout: int | None = None, show_text: bool = True,
        on_chunk=None, on_thinking=None,
    ) -> str:
        if timeout is not None and client is not None:
            client._backend._timeout = timeout

        raw = ""
        thinking_lines: list[str] = []
        tool_names: set[str] = set()
        t0 = time.time()

        gen = client._backend.stream_chunks(prompt, session=session)
        try:
            for chunk in gen:
                if chunk.text:
                    raw += chunk.text
                    if show_text:
                        sys.stdout.write(chunk.text)
                        sys.stdout.flush()
                    if on_chunk:
                        on_chunk(chunk.text)

                if chunk.blocks:
                    # Tools first (before thinking), with result tracking
                    for b in chunk.blocks:
                        if b.type == "tool_use" and b.data:
                            name = b.data.get("name", "?")
                            tool_input = b.data.get("input", {}) or {}
                            detail = _format_tool_detail(name, tool_input, b.data)
                            if name not in tool_names:
                                tool_names.add(name)
                            _log.debug("tool_use: %s %s", name, tool_input)
                            if on_chunk:
                                on_chunk(f"\n\033[32m⏺ {name}\033[0m\033[90m({detail})\033[0m\n")
                        elif b.type == "tool_result" and b.data:
                            raw = b.data.get("content", "")
                            # content may be a list of TextBlock-like objects or a string
                            if isinstance(raw, list):
                                content = "\n".join(
                                    getattr(c, "text", "") or str(c) for c in raw
                                )
                            elif isinstance(raw, str):
                                content = raw
                            else:
                                content = str(raw) if raw else ""
                            is_error = b.data.get("is_error", False)
                            color = "\033[31m" if is_error else "\033[90m"
                            lines = content.split("\n")
                            if len(lines) <= 3:
                                if on_chunk:
                                    on_chunk(f"  \033[90m⎿\033[0m {color}{content}\033[0m\n")
                            else:
                                top = "\n".join(lines[:3])
                                rest = "\n".join(lines[3:])
                                n = len(lines) - 3
                                label = f"▼ {n} more line{'s' if n > 1 else ''}"
                                if on_chunk:
                                    on_chunk(
                                        f"  \033[90m⎿\033[0m {color}{top}\033[0m\n"
                                        f"  <details><summary style='color:#888;cursor:pointer;font-size:12px'>{label}</summary>\n"
                                        f"  {color}{rest}\033[0m\n"
                                        f"  </details>\n"
                                    )
                    for b in chunk.blocks:
                        if b.type == "thinking" and b.data:
                            t = b.data.get("thinking", "").strip()
                            if t:
                                thinking_lines.append(t)
                                if on_thinking:
                                    on_thinking(t)
        except KeyboardInterrupt:
            # Tell the server to interrupt the subprocess, then close the stream.
            if client:
                client.interrupt(session)
            gen.close()
            raise

        elapsed = round(time.time() - t0, 1)
        print()
        if thinking_lines and show_text:
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


def _format_tool_detail(name: str, inp: dict, data: dict | None = None) -> str:
    """Format tool input as a compact display string."""
    # Per-tool formatting
    if inp:
        if name == "Bash":
            cmd = inp.get("command", "")
            return f"\033[90m{cmd[:120]}\033[0m"
        if name == "Read":
            return f"\033[90m{inp.get('file_path', '?')}\033[0m"
        if name == "Write":
            return f"\033[90m{inp.get('file_path', '?')}\033[0m"
        if name == "Grep":
            return f"\033[90m{inp.get('pattern', '?')}\033[0m"
        if name == "Glob":
            return f"\033[90m{inp.get('pattern', '?')}\033[0m"
        first_val = next(iter(inp.values()), "")
        return f"\033[90m{str(first_val)[:120]}\033[0m"
    # Fallback: extract detail from other data fields (label, id, tool, etc.)
    if data:
        for key in ("label", "tool_call_id", "tool", "id"):
            val = data.get(key)
            if val and isinstance(val, str) and val.strip():
                return f"\033[90m{val[:120]}\033[0m"
    return ""
