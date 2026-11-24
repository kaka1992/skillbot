"""Session manager for Claude Code HTTP wrapper using claude-agent-sdk."""

import asyncio
import logging
import os
import secrets
import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    HookMatcher,
    PermissionResultDeny,
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
from agent.permissions import BLOCKED_TOOLS, SDK_TOOLS, ExecutionMode, ToolPolicy

logger = logging.getLogger(__name__)


def _format_result_error(msg: ResultMessage) -> str:
    """Build a detailed error message from a failed ResultMessage."""
    parts: list[str] = []
    if msg.errors:
        parts.append("errors=" + "; ".join(str(e) for e in msg.errors))
    for field, label in [
        ("subtype", "subtype"), ("stop_reason", "stop_reason"),
        ("api_error_status", "api_status"), ("uuid", "msg_uuid"),
        ("duration_ms", "duration_ms"), ("num_turns", "turns"),
        ("total_cost_usd", "cost"), ("result", "result"),
        ("permission_denials", "denials"),
        ("deferred_tool_use", "deferred_tool"),
        ("model_usage", "model_usage"),
        ("structured_output", "structured_output"),
    ]:
        val = getattr(msg, field, None)
        if val is not None and val != [] and val != {} and val != "":
            parts.append(f"{label}={val}")
    detail = ", ".join(parts) if parts else "no diagnostic info available"
    logger.error("Claude ResultMessage error: %s", detail)
    return f"Claude SDK error: {detail}"

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
    policy_hook=None,
) -> ClaudeAgentOptions:
    claude_home = _resolve_claude_home()
    _ensure_claude_home(claude_home)

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
        tools=[t for t in SDK_TOOLS if not allowed_tools or t in {
            n.strip() for n in allowed_tools.split(",")
        }],
        allowed_tools=[],
        disallowed_tools=sorted(set(BLOCKED_TOOLS) | set(disallow)),
        skills=skills if skills is not None else "all",
        permission_mode="default",
        can_use_tool=_deny_unhandled_tool,
        hooks={"PreToolUse": [HookMatcher(hooks=[policy_hook or _deny_tool_hook])]},
        cwd=cwd or os.getcwd(),
        env={"HOME": str(claude_home)},
        setting_sources=["user"],
        max_turns=50,
        include_partial_messages=True,
        agents={},
    )


async def _deny_unhandled_tool(_name, _data, _context):
    return PermissionResultDeny(message="Tool not authorized by execution policy")


async def _deny_tool_hook(_data, _tool_id, _context):
    return {"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": "NO_ACTIVE_REQUEST",
    }}


@dataclass
class Message:
    role: str
    content: str
    time: float = field(default_factory=time.time)


@dataclass
class SteerReceipt:
    message_id: str
    seq: int
    status: str = "accepted"
    message: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "message_id": self.message_id,
            "seq": self.seq,
            "status": self.status,
        }


@dataclass
class RunContext:
    run_id: str
    control_token: str
    status: str = "prepared"
    execution_mode: ExecutionMode | None = None
    steers: dict[str, SteerReceipt] = field(default_factory=dict)


class SteerRejected(RuntimeError):
    def __init__(self, code: str, status_code: int = 409) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code


class Session:
    """A single Claude session backed by a ClaudeSDKClient."""

    def __init__(self, sid: str) -> None:
        self.sid = sid
        self.session_token = secrets.token_urlsafe(32)
        self.history: list[Message] = []
        self.created_at = time.time()
        self.lock = asyncio.Lock()
        self._client: ClaudeSDKClient | None = None
        self._pending_tool_ids: list[str] = []
        self._needs_tool_fix: bool = False
        self._policy: ToolPolicy | None = None
        self._run: RunContext | None = None
        self._steer_lock = asyncio.Lock()

    def prepare_run(self) -> RunContext:
        if self._run is not None and self._run.status in {"prepared", "active"}:
            return self._run
        self._run = RunContext(
            run_id=uuid.uuid4().hex,
            control_token=secrets.token_urlsafe(32),
        )
        return self._run

    def _activate_run(
        self,
        run_id: str | None,
        execution_mode: ExecutionMode,
    ) -> RunContext:
        if run_id:
            run = self._run
            if run is None or run.run_id != run_id or run.status != "prepared":
                raise RuntimeError("INVALID_PREPARED_RUN")
        else:
            run = self.prepare_run()
        run.status = "active"
        run.execution_mode = ExecutionMode(execution_mode)
        return run

    async def steer(
        self,
        run_id: str,
        control_token: str,
        message_id: str,
        message: str,
    ) -> SteerReceipt:
        text = message.strip()
        if not text:
            raise SteerRejected("EMPTY_STEER", 422)
        if len(text) > 8000:
            raise SteerRejected("STEER_TOO_LARGE", 422)
        if not message_id or len(message_id) > 128:
            raise SteerRejected("INVALID_MESSAGE_ID", 422)

        async with self._steer_lock:
            run = self._run
            if run is None or run.run_id != run_id or run.status != "active":
                raise SteerRejected("RUN_NOT_ACTIVE")
            if not secrets.compare_digest(run.control_token, control_token):
                raise SteerRejected("INVALID_CONTROL_TOKEN", 403)
            if message_id in run.steers:
                return run.steers[message_id]
            if len(run.steers) >= 10:
                raise SteerRejected("STEER_LIMIT_REACHED", 429)
            if self._client is None or self._policy is None:
                raise SteerRejected("RUN_NOT_READY")

            receipt = SteerReceipt(
                message_id=message_id,
                seq=len(run.steers) + 1,
                message=text,
            )
            run.steers[message_id] = receipt
            try:
                await self._client.query(
                    "[Steering update for the current task. Preserve valid work "
                    "already completed, apply this new direction, and state how "
                    f"you handled it in the final answer.]\n\n{text}"
                )
            except Exception:
                run.steers.pop(message_id, None)
                raise SteerRejected("STEER_DELIVERY_FAILED", 503)
            self.add("user", text)
            logger.info(
                "steer session=%s run=%s seq=%d message_id=%s accepted",
                self.sid, run_id, receipt.seq, message_id,
            )
            return receipt

    async def _complete_steers(self) -> list[dict[str, object]]:
        async with self._steer_lock:
            run = self._run
            if run is None:
                return []
            run.status = "closing"
            completed = []
            for receipt in run.steers.values():
                if receipt.status == "accepted":
                    receipt.status = "applied"
                    completed.append(receipt.as_dict())
            return completed

    async def _finish_run(self, succeeded: bool) -> None:
        async with self._steer_lock:
            run = self._run
            if run is None:
                return
            for receipt in run.steers.values():
                if receipt.status == "accepted":
                    receipt.status = "not_consumed"
            run.status = "completed" if succeeded else "failed"

    async def _pre_tool_use(self, data, _tool_id, _context):
        policy = self._policy
        try:
            decision = policy.decide(data["tool_name"], data["tool_input"]) if policy else None
            allowed = decision is not None and decision.allowed
            reason = decision.reason if decision else "NO_ACTIVE_REQUEST"
        except Exception:
            allowed, reason = False, "POLICY_CHECK_FAILED"
        logger.info(
            "permission session=%s mode=%s tool=%s call=%s allowed=%s reason=%s",
            self.sid, policy.mode.value if policy else "inactive",
            data.get("tool_name", ""), data.get("tool_use_id", ""),
            allowed, reason,
        )
        return {"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow" if allowed else "deny",
            "permissionDecisionReason": reason,
        }}

    def _request_options(self, mode, cwd, allowed_tools, disallowed_tools):
        from chat.skill import SkillManager

        work = Path(cwd or os.getcwd()).resolve()
        artifacts = work / "artifacts" / self.sid
        skill_root = _resolve_claude_home() / ".claude" / "skills"
        active_skills = frozenset(SkillManager(str(skill_root)).active_skills)
        configured_roots = tuple(
            Path(p).expanduser().resolve()
            for p in os.environ.get("CLAUDE_SERVER_READ_ROOTS", "").split(os.pathsep) if p
        )
        roots = (work, skill_root, *configured_roots)
        allowed = frozenset(allowed_tools.split(",")) if allowed_tools else frozenset(SDK_TOOLS)
        denied = frozenset(disallowed_tools.split(",")) if disallowed_tools else frozenset()
        allowed = frozenset(t.strip() for t in allowed)
        server_allowed = os.environ.get("CLAUDE_SERVER_ALLOWED_TOOLS", "")
        if server_allowed:
            allowed &= frozenset(t.strip() for t in server_allowed.split(","))
        denied |= frozenset(
            t.strip() for t in os.environ.get("CLAUDE_SERVER_DISALLOWED_TOOLS", "").split(",") if t
        )
        policy = ToolPolicy(
            ExecutionMode(mode), work, roots, artifacts,
            allowed, frozenset(t.strip() for t in denied), active_skills,
        )
        options = _build_options(
            cwd=str(work),
            skills=sorted(active_skills),
            policy_hook=self._pre_tool_use,
        )
        self._policy = policy
        return options

    def _permission_note(self, message: str) -> str:
        policy = self._policy
        return (
            f"[Execution policy: {policy.mode.value}. "
            f"Read roots: {', '.join(str(p) for p in policy.read_roots)}. "
            f"Write/Edit only in {policy.write_root} when execute/auto. "
            "Bash, native delegation, and external tools are disabled. "
            "Answer ordinary questions directly; do not turn simple text replies into code. "
            "Only when a task requires running code, return notebook code for approval.]\n\n"
            + message
        )

    def add(self, role: str, content: str) -> None:
        self.history.append(Message(role=role, content=content))

    async def send(
        self,
        message: str,
        *,
        timeout: float = 300,
        allowed_tools: str | None = None,
        cwd: str | None = None,
        disallowed_tools: str | None = None,
        execution_mode: ExecutionMode = ExecutionMode.DEFAULT,
        run_id: str | None = None,
    ) -> str:
        self.add("user", message)
        await self._apply_tool_fix()
        options = self._request_options(execution_mode, cwd, allowed_tools, disallowed_tools)
        self._activate_run(run_id, execution_mode)

        completed = False
        try:
            text = await asyncio.wait_for(
                self._send_inner(self._permission_note(message), options),
                timeout=timeout,
            )
            completed = True
        except asyncio.TimeoutError:
            raise RuntimeError(f"claude timed out after {timeout}s")
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Session %s error", self.sid)
            self.add("error", message)
            raise
        finally:
            self._policy = None
            await self._finish_run(completed)
            if not completed:
                await self.close()

        self.add("assistant", text)
        return text

    async def _send_inner(
        self, message: str, options: ClaudeAgentOptions
    ) -> str:
        if self._client is None:
            self._client = ClaudeSDKClient(options=options)
            await self._client.connect()
        await self._client.query(message)

        text_parts: list[str] = []
        async for msg in self._client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        text_parts.append(block.text)
            elif isinstance(msg, ResultMessage):
                if msg.is_error:
                    raise RuntimeError(_format_result_error(msg))

        return "".join(text_parts)

    async def send_stream(
        self,
        message: str,
        *,
        timeout: float = 300,
        allowed_tools: str | None = None,
        cwd: str | None = None,
        disallowed_tools: str | None = None,
        execution_mode: ExecutionMode = ExecutionMode.DEFAULT,
        run_id: str | None = None,
    ) -> AsyncIterator[str]:
        """Send a message and yield text chunks progressively.

        The caller MUST hold ``self.lock`` for the entire iteration.
        """
        self.add("user", message)
        await self._apply_tool_fix()
        options = self._request_options(execution_mode, cwd, allowed_tools, disallowed_tools)
        self._activate_run(run_id, execution_mode)

        full_text_parts: list[str] = []
        gen = self._send_inner_stream(self._permission_note(message), options)
        completed = False
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
            completed = True
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
        finally:
            self._policy = None
            await self._finish_run(completed)
            try:
                await gen.aclose()
            finally:
                if not completed:
                    await self.close()

        self.add("assistant", "".join(full_text_parts))

    async def _send_inner_stream(
        self, message: str, options: ClaudeAgentOptions
    ) -> AsyncIterator[str]:
        if self._client is None:
            self._client = ClaudeSDKClient(options=options)
            await self._client.connect()
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
                    raise RuntimeError(_format_result_error(msg))

    async def send_stream_chunks(
        self,
        message: str,
        *,
        timeout: float = 300,
        allowed_tools: str | None = None,
        cwd: str | None = None,
        disallowed_tools: str | None = None,
        execution_mode: ExecutionMode = ExecutionMode.DEFAULT,
        run_id: str | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """Send a message and yield StreamChunks with full trace data.

        The caller MUST hold ``self.lock`` for the entire iteration.
        """
        self.add("user", message)
        # Fix interrupted tool_use state before next query
        if self._needs_tool_fix:
            logger.info("Session %s: applying tool fix, pending_ids=%s", self.sid, self._pending_tool_ids)
        await self._apply_tool_fix()
        options = self._request_options(execution_mode, cwd, allowed_tools, disallowed_tools)
        self._activate_run(run_id, execution_mode)

        text_parts: list[str] = []
        gen = self._send_inner_chunks(self._permission_note(message), options)
        completed = False
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
            completed = True
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
        finally:
            self._policy = None
            await self._finish_run(completed)
            try:
                await gen.aclose()
            finally:
                if not completed:
                    await self.close()

        self.add("assistant", "".join(text_parts))

    async def _send_inner_chunks(
        self, message: str, options: ClaudeAgentOptions
    ) -> AsyncIterator[StreamChunk]:
        if self._client is None:
            self._client = ClaudeSDKClient(options=options)
            await self._client.connect()
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
                    # thinking_delta skipped — incremental deltas lose whitespace;
                    # the complete ThinkingBlock (see below) provides correct formatting

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
                    raise RuntimeError(_format_result_error(msg))
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
                for receipt in await self._complete_steers():
                    blocks.append(TraceBlock(
                        type="steer_receipt",
                        data=receipt,
                    ))

            yield StreamChunk(
                text="".join(text_parts),
                blocks=blocks if blocks else None,
            )

    async def interrupt(self) -> None:
        """Interrupt current query — sends signal to subprocess, preserves context."""
        self._policy = None
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
        self._policy = None
        if self._client is not None:
            client = self._client
            self._client = None
            await client.disconnect()

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
