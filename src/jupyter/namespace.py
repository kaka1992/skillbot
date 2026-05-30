"""Shell namespace abstraction — vars, context, cell tracking, injection.

Usage::

    from jupyter.namespace import Namespace
    ns = Namespace(shell)
    ns.inject("df", dataframe)
    ns.track_cell("print(1)", "output text")
    ns.vars()           # → {"df": DataFrame, "name": str}
    ns.context()        # → "Available variables:\\n  df: DataFrame shape=(3,1)"
"""

from __future__ import annotations

import sys

import pandas as pd

_IPYTHON_INTERNAL = {"In", "Out", "_ih", "_oh", "_dh", "exit", "quit", "get_ipython"}


class Namespace:
    """Manage IPython shell user_ns: query, inject, remove, context, cells."""

    def __init__(self, shell):
        self._shell = shell
        self._seen: set[str] = set()
        self._cells: list[dict] = []
        self._cell_idx: int = 0
        self._hook_events: list[str] = []
        self._hook_idx: int = 0
        self._sql_var_counter: int = 0
        self._pending_edits: list[str] = []   # unexecuted cell sources from frontend
        self._pending_idx: int = 0

    def next_sql_var(self) -> str:
        self._sql_var_counter += 1
        return f"var_{self._sql_var_counter}"

    # -- query --

    def vars(self) -> dict[str, object]:
        """Return user-defined variables (excludes internals, callables, types)."""
        return {
            k: v for k, v in self._shell.user_ns.items()
            if not k.startswith("_") and k not in _IPYTHON_INTERNAL
            and not callable(v) and not isinstance(v, type)
        }

    def get(self, name: str, default=None) -> object:
        return self._shell.user_ns.get(name, default)

    def context(self) -> str:
        """Full snapshot: variables + recent cells."""
        self._seen = set(self.vars().keys())
        self._cell_idx = len(self._cells)
        self._hook_idx = len(self._hook_events)
        return self._build_context(self.vars(), self._cells, self._hook_events)

    def track_pending_edit(self, source: str) -> None:
        """Record an unexecuted cell edit from the frontend."""
        src = source.strip()
        if src:
            self._pending_edits.append(src[:3000])

    def remove_cell(self, source: str) -> None:
        """Remove cells matching *source* from tracked history (deleted in notebook)."""
        src = source.strip()[:1500]
        if not src:
            return
        # Remove last matching cell (newest first)
        for i in range(len(self._cells) - 1, -1, -1):
            if self._cells[i]["code"][:1500] == src:
                del self._cells[i]
                break

    def delta(self) -> str:
        """Incremental: new variables + new cells + pending edits + hook events."""
        current = self.vars()
        new_vars = {k: v for k, v in current.items() if k not in self._seen}
        self._seen.update(new_vars.keys())
        new_cells = self._cells[self._cell_idx:]
        self._cell_idx = len(self._cells)
        pending = self._pending_edits[self._pending_idx:]
        self._pending_idx = len(self._pending_edits)
        new_hooks = self._hook_events[self._hook_idx:]
        self._hook_idx = len(self._hook_events)
        if not new_vars and not new_cells and not pending and not new_hooks:
            return ""
        return self._build_context(new_vars, new_cells, new_hooks, pending_edits=pending)

    def context(self) -> str:
        """Full snapshot: variables + recent cells + pending edits."""
        self._seen = set(self.vars().keys())
        self._cell_idx = len(self._cells)
        self._pending_idx = len(self._pending_edits)
        self._hook_idx = len(self._hook_events)
        return self._build_context(self.vars(), self._cells, self._hook_events)

    def reset(self) -> None:
        self._seen.clear()
        self._cell_idx = 0
        self._hook_idx = 0
        self._pending_idx = 0
        self._pending_edits.clear()

    def track_hook(self, event: str) -> None:
        """Record a hook activity event for agent context."""
        self._hook_events.append(event)

    # -- write --

    def inject(self, name: str, value: object) -> None:
        if name in self.vars():
            print(f"[namespace] variable '{name}' already exists, overwriting", file=sys.stderr)
        self._shell.user_ns[name] = value

    # -- delete --

    def remove(self, name: str) -> bool:
        if name in self._shell.user_ns and name not in _IPYTHON_INTERNAL:
            del self._shell.user_ns[name]
            return True
        return False

    # -- cell tracking --

    def track_cell(self, code: str, output: str = "", error: str = "") -> None:
        """Record a cell execution.

        *code* truncated to 1500, *output* and *error* to 500.
        """
        self._cells.append({
            "code": code.strip()[:1500],
            "output": output.strip()[:500],
            "error": error.strip()[:500],
        })

    # -- helpers --

    @staticmethod
    def _build_context(variables: dict, cells: list[dict],
                       hook_events: list[str],
                       pending_edits: list[str] | None = None) -> str:
        parts: list[str] = []
        if variables:
            parts.append("Available variables:")
            for name, val in sorted(variables.items()):
                parts.append(f"  {_describe(name, val)}")
        if cells:
            if parts:
                parts.append("")
            parts.append("Recent cell history:")
            for c in cells[-5:]:
                parts.append(f"  › {c['code'][:200]}")
                if c.get("output"):
                    parts.append(f"    → {c['output'][:150]}")
                if c.get("error"):
                    parts.append(f"    ✗ {c['error'][:150]}")
        if pending_edits:
            if parts:
                parts.append("")
            parts.append("Unexecuted cell edits (user modified but hasn't run):")
            for src in pending_edits[-3:]:
                parts.append(f"  ```\n  {src[:1500]}\n  ```")
        if hook_events:
            if parts:
                parts.append("")
            parts.append("## Hook Activity")
            for e in hook_events[-10:]:
                parts.append(f"  {e}")
        return "\n".join(parts) if parts else ""


# -- helpers --

_PREVIEW_ROWS = 3
_PREVIEW_WIDTH = 80


def _describe(name: str, val: object) -> str:
    t = type(val).__name__
    try:
        if isinstance(val, pd.DataFrame):
            return _describe_dataframe(name, val)
        if isinstance(val, pd.Series):
            return _describe_series(name, val)
        if isinstance(val, (list, tuple)):
            return _describe_list(name, val, t)
        if isinstance(val, dict):
            return _describe_dict(name, val)
        if isinstance(val, str):
            return _describe_str(name, val)
    except Exception:
        pass
    return f"{name}: {t}"


def _describe_dataframe(name: str, df) -> str:
    shape = f"shape={df.shape}"
    if len(df) == 0:
        return f"{name}: DataFrame {shape}"
    preview = df.head(_PREVIEW_ROWS).to_string(max_rows=_PREVIEW_ROWS, max_cols=10, max_colwidth=20)
    return f"{name}: DataFrame {shape}\n{_indent(preview)}"


def _describe_series(name: str, s) -> str:
    if len(s) == 0:
        return f"{name}: Series len=0"
    preview = s.head(_PREVIEW_ROWS).to_string(max_rows=_PREVIEW_ROWS)
    return f"{name}: Series len={len(s)}\n{_indent(preview)}"


def _describe_list(name: str, lst, t: str) -> str:
    body = ", ".join(repr(x) for x in lst[:5])
    if len(lst) > 5:
        body += ", ..."
    return f"{name}: {t} len={len(lst)}  [{body}]"


def _describe_dict(name: str, dct) -> str:
    body = ", ".join(f"{k}: {type(v).__name__}" for k, v in list(dct.items())[:5])
    if len(dct) > 5:
        body += ", ..."
    return f"{name}: dict len={len(dct)}  {{{body}}}"


def _describe_str(name: str, s: str) -> str:
    if len(s) <= _PREVIEW_WIDTH:
        return f"{name}: str len={len(s)}  '{s}'"
    return f"{name}: str len={len(s)}  '{s[:_PREVIEW_WIDTH]}...'"


def _indent(text: str, spaces: int = 2) -> str:
    prefix = " " * spaces
    return prefix + text.replace("\n", "\n" + prefix)
