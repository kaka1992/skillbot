"""Shell namespace abstraction — query / write / delete / context.

Usage::

    from jupyter.namespace import Namespace
    ns = Namespace(shell)
    ns.inject("df", dataframe)
    ns.remove("tmp")
    ns.vars()           # → {"df": DataFrame, "name": str}
    ns.context()        # → "Available variables:\\n  df: DataFrame shape=(3,1)"
"""

from __future__ import annotations

import pandas as pd

_IPYTHON_INTERNAL = {"In", "Out", "_ih", "_oh", "_dh", "exit", "quit", "get_ipython"}


class Namespace:
    """Manage IPython shell user_ns: query, inject, remove, context, cells."""

    def __init__(self, shell):
        self._shell = shell
        self._seen: set[str] = set()
        self._cells: list[dict] = []
        self._cell_idx: int = 0

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
        return self._build_context(self.vars(), self._cells)

    def delta(self) -> str:
        """Incremental: new variables + new cells since last context/delta."""
        current = self.vars()
        new_vars = {k: v for k, v in current.items() if k not in self._seen}
        self._seen.update(new_vars.keys())
        new_cells = self._cells[self._cell_idx:]
        self._cell_idx = len(self._cells)
        if not new_vars and not new_cells:
            return ""
        return self._build_context(new_vars, new_cells)

    def reset(self) -> None:
        self._seen.clear()
        self._cell_idx = 0

    # -- write --

    def inject(self, name: str, value: object) -> None:
        if name in self.vars():
            import sys
            print(f"[namespace] variable '{name}' already exists, overwriting", file=sys.stderr)
        self._shell.user_ns[name] = value

    # -- delete --

    def remove(self, name: str) -> bool:
        if name in self._shell.user_ns and name not in _IPYTHON_INTERNAL:
            del self._shell.user_ns[name]
            return True
        return False

    # -- cell tracking --

    def track_cell(self, code: str, output: str = "") -> None:
        """Record a cell execution — call after each %%agent run."""
        self._cells.append({
            "code": code.strip()[:300],
            "output": output.strip()[:200],
        })

    def set_next_input(self, code: str) -> None:
        self._shell.set_next_input(code, replace=False)

    def flush_current_cell(self, marker: str = "%agent --trace") -> str:
        """Capture and track code before *marker* in the current cell.
        Returns the code before the marker, or "" on failure.
        """
        try:
            from IPython import get_ipython
            shell = get_ipython()
            full_cell = getattr(shell, "_current_cell_raw", "")
            if not full_cell:
                return ""
            lines = full_cell.split("\n")
            idx = next((i for i, l in enumerate(lines) if marker in l), len(lines))
            code_before = "\n".join(lines[:idx])
            if code_before.strip():
                self.track_cell(code_before, "")
            return code_before
        except Exception:
            return ""

    # -- helpers --

    @staticmethod
    def _build_context(variables: dict, cells: list[dict]) -> str:
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
        return "\n".join(parts) if parts else ""


# -- singleton (set by magic __init__) --

_ns: Namespace | None = None


def set_shell(shell) -> Namespace:
    global _ns
    _ns = Namespace(shell)
    return _ns


def get_shell() -> Namespace:
    if _ns is None:
        raise RuntimeError("Namespace not initialized. Call set_shell(shell) first.")
    return _ns


# -- helpers --

def _describe(name: str, val: object) -> str:
    t = type(val).__name__
    try:
        if isinstance(val, pd.DataFrame):
            return f"{name}: DataFrame shape={val.shape}"
        if isinstance(val, pd.Series):
            return f"{name}: Series len={len(val)}"
        if isinstance(val, (list, tuple)):
            return f"{name}: {t} len={len(val)}"
        if isinstance(val, dict):
            return f"{name}: dict keys={list(val.keys())[:5]}"
        if isinstance(val, str):
            return f"{name}: str len={len(val)}"
    except Exception:
        pass
    return f"{name}: {t}"
