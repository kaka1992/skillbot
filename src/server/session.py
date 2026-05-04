"""Session manager for Claude Code HTTP wrapper."""

import asyncio
import logging
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _resolve_claude_home() -> Path:
    """Return isolated Claude home path (same logic as install.sh get_agent_path).

    Respects ``SKILL_BOT_AGENT_INSTALL_DIR`` if set.
    """
    install_dir = os.environ.get("SKILL_BOT_AGENT_INSTALL_DIR", "")
    if install_dir:
        return Path(install_dir) / "claude-code"
    return _PROJECT_ROOT / "agents" / "claude-code"


def _ensure_claude_home(claude_home: Path) -> None:
    """Verify isolated claude home dir with .claude/settings.json exists."""
    settings = claude_home / ".claude" / "settings.json"
    if not settings.exists():
        raise RuntimeError(
            f"Claude settings not found: {settings}\n"
            f"Copy the template first:\n"
            f"  mkdir -p {claude_home / '.claude'} && "
            f"cp conf/agent_conf/claude-code/settings.example.json {settings}"
        )


_claude_env: dict[str, str] | None = None
_claude_env_lock = threading.Lock()


def get_claude_env() -> dict[str, str]:
    """Return env dict with isolated HOME for claude subprocess (cached, thread-safe)."""
    global _claude_env
    if _claude_env is not None:
        return _claude_env
    with _claude_env_lock:
        if _claude_env is not None:      # double-check under lock
            return _claude_env
        claude_home = _resolve_claude_home()
        _ensure_claude_home(claude_home)
        env = os.environ.copy()
        env["HOME"] = str(claude_home)
        _claude_env = env
        return env

@dataclass
class Message:
    role: str
    content: str
    time: float = field(default_factory=time.time)


class Session:
    """A single Claude Code session with history tracking."""

    def __init__(self, sid: str) -> None:
        self.sid = sid
        self.claude_sid: str | None = None  # Claude's internal --resume ID
        self.history: list[Message] = []
        self.created_at = time.time()
        self.lock = asyncio.Lock()

    def add(self, role: str, content: str) -> None:
        self.history.append(Message(role=role, content=content))

    def to_dict(self) -> dict:
        return {
            "session_id": self.sid,
            "claude_sid": self.claude_sid,
            "messages": len(self.history),
            "created_at": self.created_at,
        }


class SessionManager:
    """Manage multiple Claude Code sessions."""

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

    def delete(self, sid: str) -> bool:
        if sid in self._sessions:
            del self._sessions[sid]
            logger.info("Deleted session %s", sid)
            return True
        return False


async def run_claude(
    message: str,
    *,
    timeout: float = 300,
    allowed_tools: str | None = None,
    cwd: str | None = None,
) -> str:
    """Run ``claude -p`` in one-shot mode and return the response text.

    Note: Claude Code v2.x ``-p`` mode is designed for single-turn code tasks
    and does not support ``--resume``. Multi-turn context must be managed by
    the caller (pass full conversation in the prompt).  The session HTTP layer
    appends history to each request as context.
    """
    args = [
        "claude", "-p", message,
        "--output-format", "text",
        "--dangerously-skip-permissions",   # Server mode: auto-approve all tools
    ]
    if allowed_tools:
        args += ["--allowedTools", allowed_tools]

    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
        env=get_claude_env(),       # Use isolated claude home
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
    except asyncio.TimeoutError:
        proc.kill()
        raise RuntimeError(f"claude timed out after {timeout}s")

    text = stdout.decode("utf-8", errors="replace").strip()
    err = stderr.decode("utf-8", errors="replace").strip()

    if proc.returncode != 0 and not text:
        raise RuntimeError(err or f"claude exited with code {proc.returncode}")

    return text
