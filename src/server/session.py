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
    AgentDefinition,
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    StreamEvent,
    TaskNotificationMessage,
    TaskProgressMessage,
    TaskStartedMessage,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
)

from chat.base import StreamChunk, TraceBlock  # noqa: E402

logger = logging.getLogger(__name__)

def _resolve_claude_home() -> Path:
    install_dir = os.environ.get("SKILL_BOT_AGENT_INSTALL_DIR", "")
    if install_dir:
        return Path(install_dir) / "claude-code"

    # running from agents/claude-code/server/ → home is ../  (install.sh copy)
    here = Path(__file__).resolve()
    agent_home = here.parents[1]
    if (agent_home / ".claude").is_dir():
        return agent_home

    # running from src/server/ → home is ../../agents/claude-code/
    return here.parents[2] / "agents" / "claude-code"


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
    skills: list[str] | None = None,
    disallowed_tools: str | None = None,
) -> ClaudeAgentOptions:
    claude_home = _resolve_claude_home()
    _ensure_claude_home(claude_home)

    tools = None
    if allowed_tools:
        tools = [t.strip() for t in allowed_tools.split(",") if t.strip()]

    disallow: list[str] = []
    if disallowed_tools:
        disallow = [t.strip() for t in disallowed_tools.split(",") if t.strip()]

    # Resolve active skills from persisted enable/disable state
    if skills is None:
        from chat.skill import SkillManager
        skill_dir = str(claude_home / ".claude" / "skills")
        mgr = SkillManager(skill_dir)
        installed = mgr.list_skills()
        if installed:
            skills = mgr.active_skills

    return ClaudeAgentOptions(
        allowed_tools=tools or [],
        disallowed_tools=disallow,
        skills=skills if skills is not None else "all",
        permission_mode="bypassPermissions",
        cwd=cwd or os.getcwd(),
        env={"HOME": str(claude_home)},
        setting_sources=["user"],
        max_turns=50,
        include_partial_messages=True,
        agents={
            "general-purpose": AgentDefinition(
                description="General-purpose agent for complex multi-step tasks",
                prompt="You are a capable agent. Complete the assigned task thoroughly and report results.",
                tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob"],
            ),
            "coding": AgentDefinition(
                description="Coding specialist for writing and refactoring code",
                prompt="You are a coding specialist. Write clean, working code. Explain your approach briefly then produce the implementation.",
                tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob"],
            ),
            "code-reviewer": AgentDefinition(
                description="Reviews code for bugs, style, and security issues",
                prompt="You are a code reviewer. Analyze the code carefully. Report bugs, style violations, and security concerns.",
                tools=["Read", "Grep", "Glob"],
            ),
        },
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
        self._pending_tool_ids: list[str] = []
        self._needs_tool_fix: bool = False

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

        await self._apply_tool_fix()

        try:
            text = await asyncio.wait_for(
                self._send_inner(message, options),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            raise RuntimeError(f"claude timed out after {timeout}s")
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Session %s error", self.sid)
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
        options = _build_options(allowed_tools=allowed_tools, cwd=cwd)

        await self._apply_tool_fix()

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
        except asyncio.CancelledError:
            if gen is not None:
                try:
                    await gen.aclose()
                except Exception:
                    pass
            raise
        except Exception:
            logger.exception("Session %s error", self.sid)
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

    async def send_stream_chunks(
        self,
        message: str,
        *,
        timeout: float = 300,
        allowed_tools: str | None = None,
        cwd: str | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """Send a message and yield StreamChunks with full trace data.

        The caller MUST hold ``self.lock`` for the entire iteration.
        """
        self.add("user", message)
        options = _build_options(allowed_tools=allowed_tools, cwd=cwd)

        # Fix interrupted tool_use state before next query
        if self._needs_tool_fix:
            logger.info("Session %s: applying tool fix, pending_ids=%s", self.sid, self._pending_tool_ids)
        await self._apply_tool_fix()

        text_parts: list[str] = []
        gen = self._send_inner_chunks(message, options)
        try:
            while True:
                try:
                    chunk = await asyncio.wait_for(
                        gen.__anext__(), timeout=timeout
                    )
                except StopAsyncIteration:
                    break
                if chunk.text:
                    text_parts.append(chunk.text)
                # Track tool_use IDs for interrupt recovery
                if chunk.blocks:
                    for b in chunk.blocks:
                        if b.type == "tool_use" and b.data:
                            tid = b.data.get("id", "")
                            if tid:
                                self._pending_tool_ids.append(tid)
                yield chunk
        except asyncio.TimeoutError:
            raise RuntimeError(f"claude timed out after {timeout}s")
        except asyncio.CancelledError:
            # Interrupt leaves unresolved tool_use — _apply_tool_fix handles it.
            # Must properly close the inner generator so the SDK client is usable.
            if gen is not None:
                try:
                    await gen.aclose()
                except Exception:
                    pass
            raise
        except Exception:
            logger.exception("Session %s error", self.sid)
            self.add("error", message)
            raise

        self.add("assistant", "".join(text_parts))

    async def _send_inner_chunks(
        self, message: str, options: ClaudeAgentOptions
    ) -> AsyncIterator[StreamChunk]:
        if self._client is None:
            self._client = ClaudeSDKClient(options=options)
            await self._client.connect(prompt=message)
        else:
            await self._client.query(message)

        async for msg in self._client.receive_response():
            blocks: list[TraceBlock] = []
            text_parts: list[str] = []

            if isinstance(msg, StreamEvent):
                event = msg.event
                event_type = event.get("type", "")
                if event_type == "content_block_delta":
                    delta = event.get("delta", {})
                    delta_type = delta.get("type", "")
                    if delta_type == "text_delta":
                        if t := delta.get("text", ""):
                            text_parts.append(t)
                    elif delta_type == "thinking_delta":
                        blocks.append(TraceBlock(
                            type="thinking",
                            data={"thinking": delta.get("thinking", "")},
                        ))

            elif isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        pass  # text from StreamEvent deltas
                    elif isinstance(block, ThinkingBlock):
                        blocks.append(TraceBlock(
                            type="thinking",
                            data={"thinking": block.thinking,
                                  "signature": block.signature},
                        ))
                    elif isinstance(block, ToolUseBlock):
                        blocks.append(TraceBlock(
                            type="tool_use",
                            data={"id": block.id, "name": block.name,
                                  "input": block.input},
                        ))
                    elif isinstance(block, ToolResultBlock):
                        blocks.append(TraceBlock(
                            type="tool_result",
                            data={"tool_use_id": block.tool_use_id,
                                  "content": block.content,
                                  "is_error": block.is_error},
                        ))

            elif isinstance(msg, TaskStartedMessage):
                blocks.append(TraceBlock(
                    type="subagent",
                    data={"event": "started", "task_id": msg.task_id,
                          "description": msg.description,
                          "agent_type": msg.task_type},
                ))
            elif isinstance(msg, TaskProgressMessage):
                blocks.append(TraceBlock(
                    type="subagent",
                    data={"event": "progress", "task_id": msg.task_id,
                          "last_tool_name": msg.last_tool_name,
                          "usage": dict(msg.usage) if msg.usage else None},
                ))
            elif isinstance(msg, TaskNotificationMessage):
                blocks.append(TraceBlock(
                    type="subagent",
                    data={"event": msg.status, "task_id": msg.task_id,
                          "summary": msg.summary,
                          "usage": dict(msg.usage) if msg.usage else None},
                ))

            elif isinstance(msg, ResultMessage):
                if msg.is_error:
                    errors = msg.errors or ["Unknown error"]
                    raise RuntimeError("; ".join(errors))
                blocks.append(TraceBlock(
                    type="usage",
                    data={
                        "total_cost_usd": msg.total_cost_usd,
                        "num_turns": msg.num_turns,
                        "duration_ms": msg.duration_ms,
                        "duration_api_ms": msg.duration_api_ms,
                        "stop_reason": msg.stop_reason,
                        "usage": msg.usage,
                    },
                ))

            yield StreamChunk(
                text="".join(text_parts),
                blocks=blocks if blocks else None,
            )

    async def interrupt(self) -> None:
        """Interrupt current query — sends signal to subprocess, preserves context."""
        if self._client is not None:
            logger.info("Session %s: interrupt — tool_ids=%s", self.sid, self._pending_tool_ids)
            self._needs_tool_fix = True
            await self._client.interrupt()
            logger.info("Session %s: interrupt done", self.sid)

    async def _apply_tool_fix(self) -> None:
        """Send synthetic tool_results to complete interrupted tool_use blocks."""
        if not self._needs_tool_fix or not self._client:
            return
        self._needs_tool_fix = False
        ids = list(self._pending_tool_ids)  # copy before clearing
        self._pending_tool_ids.clear()
        if not ids:
            # No tool_use ID tracked — must recreate client
            logger.warning("Session %s: interrupt without tool_use ID, disconnecting + recreating client", self.sid)
            if self._client is not None:
                try:
                    await self._client.disconnect()
                except Exception:
                    pass
                self._client = None
            return
        async def _fix_stream():
            for tid in ids:
                yield {
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": tid,
                        "content": "[interrupted by user]",
                        "is_error": True,
                    }],
                }
        try:
            await self._client.query(_fix_stream())
            async for _ in self._client.receive_response():
                pass
        except Exception:
            logger.exception("Session %s tool fix failed", self.sid)
            if self._client is not None:
                await self._client.disconnect()
                self._client = None

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
