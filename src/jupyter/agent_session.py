"""Agent session lifecycle — init, cleanup, streaming, prompts."""

import atexit
import hashlib
import logging
import os
import sys
import time
from datetime import datetime

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# prompts
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
Return results as a JSON object wrapped in a ```json fenced block:
```json
{
  "text": "explanatory markdown text",
  "files": ["/tmp/chart.png", "/tmp/data.csv"],
  "code": "print('hello')"
}
```
- "text": explanatory text (optional)
- "files": list of file paths created by tools (optional)
- "code": executable Python code (optional)
Include only non-empty fields.
"""

REVIEW_PROMPT = """Review task completion:

## Task
{task}

## Session History (non-agent cells)
{history}

## Current Variables
{variables}

## Agent Output
{output}

Is the problem solved? Reply ONLY:
SOLVED: <brief explanation>
or
NOT_SOLVED: <what's missing and suggested fix>
"""

# ---------------------------------------------------------------------------
# session state
# ---------------------------------------------------------------------------

_client: object | None = None
_session_id: str | None = None


def _notebook_path() -> str:
    """Best-effort notebook path for stable session-key binding."""
    try:
        ip = get_ipython()  # noqa: F821
        nb = getattr(ip, "_notebook_path", None)
        if nb:
            return nb
        kernel = getattr(ip, "kernel", None)
        parent = getattr(kernel, "_parent_header", None) or {}
        nb = (parent.get("metadata") or {}).get("notebook_path")
        if nb:
            return nb
    except Exception:
        pass
    return os.path.realpath(os.getcwd())


def _session_key() -> str:
    return hashlib.md5(_notebook_path().encode()).hexdigest()[:12]


# ---------------------------------------------------------------------------
# session lifecycle
# ---------------------------------------------------------------------------


def init_session(agent: str, timeout: int) -> None:
    """Create client + stable session, seed system prompt."""
    global _client, _session_id
    _cleanup_session()
    from chat import ChatClient

    _client = ChatClient(agent, timeout=timeout)
    _session_id = _session_key()
    _client.chat(SYSTEM_PROMPT, session=_session_id)
    _log.info("session init: agent=%s timeout=%ds session=%s", agent, timeout, _session_id)


def _cleanup_session() -> None:
    """Clear server-side session on kernel shutdown."""
    global _client, _session_id
    if _client is not None and _session_id is not None:
        try:
            _client.clear_session(_session_id)
        except Exception:
            pass
    _client = None
    _session_id = None


def get_client():
    """Return current ChatClient instance."""
    return _client


def get_session_id():
    """Return current session ID."""
    return _session_id


# ---------------------------------------------------------------------------
# streaming
# ---------------------------------------------------------------------------


def stream_output(prompt: str, timeout: int | None = None, show_text: bool = True) -> str:
    """Stream agent response via ``stream_chunks()``, display progress."""
    if timeout is not None and _client is not None:
        _client._backend._timeout = timeout

    raw = ""
    thinking_lines: list[str] = []
    tool_names: set[str] = set()
    t0 = time.time()

    for chunk in _client._backend.stream_chunks(prompt, session=_session_id):
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
              _session_id, elapsed, len(raw), len(tool_names))
    _log.debug("agent output:\n%s", raw[:5000])

    return raw


# ---------------------------------------------------------------------------
# cleanup
# ---------------------------------------------------------------------------

atexit.register(_cleanup_session)
