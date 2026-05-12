"""%%agent cell magic — call agent from Jupyter."""

import atexit
import hashlib
import os
import shlex
import sys
from pathlib import Path

from IPython.core.magic import Magics, cell_magic, magics_class

from .parser import parse
from .render import render_output

PROMPT_TEMPLATE = """\
{content}

Return results in this format:
- Explanatory text outside fenced blocks (plain text, no code fences).
- CSV data as ```csv:variable_name blocks (use a meaningful variable name).
- Images as ```image blocks (base64-encoded PNG).
- Other files as ```file:filename blocks.
"""


def _get_notebook_path() -> str:
    """Return a stable identifier for the current notebook.

    Uses Jupyter's ``notebook_path`` from parent metadata when available,
    falls back to the current working directory (which Jupyter sets to
    the notebook directory on kernel start).
    """
    try:
        ip = get_ipython()  # noqa: F821 — available in IPython kernel
        path = ip.kernel.session.username  # not notebook-specific
        # Try to extract from startup info
        meta = getattr(ip, "_notebook_path", None)
        if meta:
            return meta
    except Exception:
        pass
    return os.path.realpath(os.getcwd())


def _session_key() -> str:
    """Stable session ID derived from notebook path."""
    raw = _get_notebook_path()
    return hashlib.md5(raw.encode()).hexdigest()[:12]


# per-kernel session tracking
_session_id: str | None = None
_client: object | None = None  # ChatClient instance


def _cleanup_session():
    """Clear server-side session on kernel shutdown."""
    global _session_id, _client
    if _client is not None and _session_id is not None:
        try:
            _client.clear_session(_session_id)
        except Exception:
            pass
    _session_id = None
    _client = None


atexit.register(_cleanup_session)


@magics_class
class AgentMagic(Magics):
    _agent: str = "claude-code"
    _timeout: int = 300

    @cell_magic
    def agent(self, line: str, cell: str) -> None:
        """%%agent [<agent>] [--timeout N]

        Call agent with cell content. Results auto-injected into namespace.
        Same notebook file shares the same session for context preservation.

        Examples:
            %%agent
            1+1=?

            %%agent deer-flow --timeout 120
            Write a sort function
        """
        global _session_id, _client

        args = shlex.split(line)
        agent = self._agent
        timeout = self._timeout

        i = 0
        while i < len(args):
            if args[i] == "--timeout" and i + 1 < len(args):
                timeout = int(args[i + 1])
                i += 2
            elif not args[i].startswith("--"):
                agent = args[i]
                i += 1
            else:
                i += 1

        src = str(Path(__file__).resolve().parents[1])
        if src not in sys.path:
            sys.path.insert(0, src)

        from chat import ChatClient

        # stable session per notebook file
        if _session_id is None:
            _session_id = _session_key()

        if _client is None:
            _client = ChatClient(agent, timeout=timeout)

        prompt = PROMPT_TEMPLATE.format(content=cell)
        raw = _client.chat(prompt, session=_session_id)

        result = parse(raw)
        render_output(self.shell, result)
