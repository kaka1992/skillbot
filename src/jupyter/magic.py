"""%%agent cell magic — call agent from Jupyter with streaming progress."""

import atexit
import hashlib
import os
import shlex
import sys
import time
from datetime import datetime
from pathlib import Path

from IPython.core.magic import Magics, cell_magic, magics_class

from .namespace import Namespace
from .parser import parse
from .render import render_output

# ---- prompt templates ----

SYSTEM_PROMPT = """\
Return results in this format:
- Explanatory text outside fenced blocks (plain text, no code fences).
- Images as ```image blocks (base64-encoded PNG).
- CSV data as ```file:filename.csv blocks.
- Other files as ```file:filename blocks.
"""

CODE_PROMPT = "Return ONLY a single ```python block with executable code. No explanations, no markdown outside the fence."

# ---- session state ----

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


def _init_session(agent: str, timeout: int) -> None:
    """Create client + stable session, seed system prompt. Idempotent."""
    global _client, _session_id
    if _client is not None:
        return
    from chat import ChatClient
    _client = ChatClient(agent, timeout=timeout)
    _session_id = _session_key()
    # seed system prompt as first turn (model-caches the instructions)
    _client.chat(SYSTEM_PROMPT, session=_session_id)


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


atexit.register(_cleanup_session)

_LOG_DIR = Path(__file__).resolve().parents[2] / ".run"
_LOG_DIR.mkdir(parents=True, exist_ok=True)


def _log_agent(session: str, vars_: list[str], cells: list[dict],
               prompt: str, result: str, elapsed: float, error: str = "") -> None:
    """Write a human-readable log entry."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_file = _LOG_DIR / f"agent-{datetime.now().strftime('%Y%m%d')}.log"

    lines = [
        f"{'='*60}",
        f"  [{ts}]  session={session}  elapsed={elapsed:.1f}s",
        f"{'='*60}",
    ]
    if vars_:
        lines.append(f"  variables: {', '.join(vars_)}")
    if cells:
        lines.append(f"  cell history ({len(cells)} total):")
        for c in cells[-3:]:
            code = c["code"][:120].replace("\n", "\\n")
            lines.append(f"    › {code}")
            if c.get("output"):
                out = c["output"][:100].replace("\n", "\\n")
                lines.append(f"      → {out}")
    lines.append(f"  {'─'*50}")
    lines.append(f"  prompt: {prompt[:300]}")
    if error:
        lines.append(f"  ERROR: {error}")
    if result:
        lines.append(f"  result ({len(result)} chars):")
        for rline in result[:2000].split("\n")[:30]:
            lines.append(f"    {rline}")
    lines.append("")

    with open(log_file, "a", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _stream_output(prompt: str, timeout: int | None = None) -> str:
    """Stream agent response via ``stream_chunks()``, display progress."""
    if timeout is not None:
        _client._backend._timeout = timeout

    raw = ""
    thinking_lines: list[str] = []
    tool_names: set[str] = set()

    for chunk in _client._backend.stream_chunks(prompt, session=_session_id):
        if chunk.text:
            raw += chunk.text
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
                        print(f"\n\033[90m[{name}]\033[0m")
                elif b.type == "tool_result" and b.data:
                    pass

    print()
    if tool_names:
        print(f"\033[90m# tools: {', '.join(sorted(tool_names))}\033[0m")
    if thinking_lines:
        summary = " ".join(thinking_lines)[:200]
        print(f"\033[90m# thinking: {summary}\033[0m")
    print()

    return raw


# ---- magic ----

@magics_class
class AgentMagic(Magics):
    _agent = "claude-code"
    _timeout = 600

    def __init__(self, shell):
        super().__init__(shell)
        self.ns = Namespace(shell)
        _init_session(self._agent, self._timeout)
        # track ALL cell executions (not just %%agent)
        shell.events.register("post_run_cell", self._on_cell_run)

    def _on_cell_run(self, result):
        """Hook: capture cell code + output for namespace context."""
        info = getattr(result, "info", None)
        if info is None:
            return
        code = getattr(info, "raw_cell", "")
        if not code or code.startswith("%%agent") or code.startswith("%agent"):
            return
        output = str(info.result) if getattr(info, "result", None) else ""
        self.ns.track_cell(code.strip(), output.strip())

    @cell_magic
    def agent(self, line: str, cell: str) -> None:
        timeout = self._timeout
        code_only = False
        args = shlex.split(line)
        i = 0
        while i < len(args):
            if args[i] == "--timeout" and i + 1 < len(args):
                timeout = int(args[i + 1]); i += 2
            elif args[i] == "--code":
                code_only = True; i += 1
            else:
                i += 1

        src = str(Path(__file__).resolve().parents[1])
        if src not in sys.path:
            sys.path.insert(0, src)

        ctx = self.ns.context() if not self.ns._seen else self.ns.delta()
        if code_only:
            prompt = f"{CODE_PROMPT}\n\n{cell}"
        else:
            prompt = f"{ctx}\n\n{cell}" if ctx else cell

        t0 = time.time()
        raw = ""
        try:
            raw = _stream_output(prompt, timeout)
        except Exception as e:
            _log_agent(_session_id, sorted(self.ns.vars().keys()),
                       self.ns._cells, cell, "", round(time.time() - t0, 1),
                       error=str(e))
            print(f"\033[91mError: {e}\033[0m")
            return

        elapsed = round(time.time() - t0, 1)
        _log_agent(_session_id, sorted(self.ns.vars().keys()),
                   self.ns._cells, cell, raw, elapsed)

        if raw.strip():
            result = parse(raw)
            render_output(self.ns, result, skip_text=True, inject_code=code_only)

        self.ns.track_cell(cell, raw.strip()[:200])
