"""Session manager for Claude Code HTTP wrapper using claude-agent-sdk."""

import asyncio
import logging
import os
import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    StreamEvent,
    TextBlock,
)

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _resolve_claude_home() -> Path:
    install_dir = os.environ.get("SKILL_BOT_AGENT_INSTALL_DIR", "")
    if install_dir:
        return Path(install_dir) / "claude-code"
    return _PROJECT_ROOT / "agents" / "claude-code"


def _ensure_claude_home(claude_home: Path) -> None:
    settings = claude_home / ".claude" / "settings.json"
    if not settings.exists():
        raise RuntimeError(
            f"Claude settings not found: {settings}\n"
            f"Copy the template first:\n"
            f"  mkdir -p {claude_home / '.claude'} && "
            f"cp conf/agent_conf/claude-code/settings.json {settings}"
        )


def _build_options(
    allowed_tools: str | None = None,
    cwd: str | None = None,
    include_partial_messages: bool = False,
) -> ClaudeAgentOptions:
    claude_home = _resolve_claude_home()
    _ensure_claude_home(claude_home)

    tools = None
    if allowed_tools:
        tools = [t.strip() for t in allowed_tools.split(",") if t.strip()]

    return ClaudeAgentOptions(
        allowed_tools=tools or [],
        permission_mode="bypassPermissions",
        cwd=cwd or os.getcwd(),
        env={"HOME": str(claude_home)},
        setting_sources=["user"],
        max_turns=50,
        include_partial_messages=include_partial_messages,
    )


@dataclass
class Message:
    role: str
    content: str
    time: float = field(default_factory=time.time)


class Session:
    """A single Claude session backed by a ClaudeSDKClient."""

    def __init__(self, sid: str) -> None:
        self.sid = sid
        self.history: list[Message] = []
        self.created_at = time.time()
        self.lock = asyncio.Lock()
        self._client: ClaudeSDKClient | None = None

    def add(self, role: str, content: str) -> None:
        self.history.append(Message(role=role, content=content))

    async def send(
        self,
        message: str,
        *,
        timeout: float = 300,
        allowed_tools: str | None = None,
        cwd: str | None = None,
    ) -> str:
        self.add("user", message)
        options = _build_options(allowed_tools=allowed_tools, cwd=cwd)

        try:
            text = await asyncio.wait_for(
                self._send_inner(message, options),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            raise RuntimeError(f"claude timed out after {timeout}s")
        except Exception:
            self.add("error", message)
            raise

        self.add("assistant", text)
        return text

    async def _send_inner(
        self, message: str, options: ClaudeAgentOptions
    ) -> str:
        if self._client is None:
            self._client = ClaudeSDKClient(options=options)
            await self._client.connect(prompt=message)
        else:
            await self._client.query(message)

        text_parts: list[str] = []
        async for msg in self._client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        text_parts.append(block.text)
            elif isinstance(msg, ResultMessage):
                if msg.is_error:
                    errors = msg.errors or ["Unknown error"]
                    raise RuntimeError("; ".join(errors))

        return "".join(text_parts)

    async def send_stream(
        self,
        message: str,
        *,
        timeout: float = 300,
        allowed_tools: str | None = None,
        cwd: str | None = None,
    ) -> AsyncIterator[str]:
        """Send a message and yield text chunks progressively.

        The caller MUST hold ``self.lock`` for the entire iteration.
        """
        self.add("user", message)
        options = _build_options(
            allowed_tools=allowed_tools,
            cwd=cwd,
            include_partial_messages=True,
        )

        full_text_parts: list[str] = []
        gen = self._send_inner_stream(message, options)
        try:
            while True:
                try:
                    chunk = await asyncio.wait_for(
                        gen.__anext__(), timeout=timeout
                    )
                except StopAsyncIteration:
                    break
                full_text_parts.append(chunk)
                yield chunk
        except asyncio.TimeoutError:
            raise RuntimeError(f"claude timed out after {timeout}s")
        except Exception:
            self.add("error", message)
            raise

        self.add("assistant", "".join(full_text_parts))

    async def _send_inner_stream(
        self, message: str, options: ClaudeAgentOptions
    ) -> AsyncIterator[str]:
        if self._client is None:
            self._client = ClaudeSDKClient(options=options)
            await self._client.connect(prompt=message)
        else:
            await self._client.query(message)

        async for msg in self._client.receive_response():
            if isinstance(msg, StreamEvent):
                event = msg.event
                if event.get("type") == "content_block_delta":
                    delta = event.get("delta", {})
                    if delta.get("type") == "text_delta":
                        text = delta.get("text", "")
                        if text:
                            yield text
            elif isinstance(msg, ResultMessage):
                if msg.is_error:
                    errors = msg.errors or ["Unknown error"]
                    raise RuntimeError("; ".join(errors))

    async def close(self) -> None:
        if self._client is not None:
            await self._client.disconnect()
            self._client = None

    def to_dict(self) -> dict:
        return {
            "session_id": self.sid,
            "messages": len(self.history),
            "created_at": self.created_at,
        }


class SessionManager:
    """Manage Claude Code sessions."""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def create(self) -> Session:
        sid = uuid.uuid4().hex[:12]
        s = Session(sid)
        self._sessions[sid] = s
        logger.info("Created session %s", sid)
        return s

    def get(self, sid: str) -> Session | None:
        return self._sessions.get(sid)

    def list_sessions(self) -> list[dict]:
        return [s.to_dict() for s in self._sessions.values()]

    async def delete(self, sid: str) -> bool:
        if sid in self._sessions:
            s = self._sessions.pop(sid)
            await s.close()
            logger.info("Deleted session %s", sid)
            return True
        return False
