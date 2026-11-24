"""Shared application-level execution policy (not an OS sandbox)."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class ExecutionMode(str, Enum):
    DEFAULT = "default"
    PLAN = "plan"
    EDIT = "edit"
    EXECUTE = "execute"
    AUTO = "auto"

    @property
    def can_execute(self) -> bool:
        return self in {self.EXECUTE, self.AUTO}

    @property
    def can_materialize(self) -> bool:
        return self.can_execute or self is self.EDIT


SDK_TOOLS = ("Read", "Glob", "Grep", "Write", "Edit")
BLOCKED_TOOLS = (
    "Bash", "NotebookEdit", "Agent", "Task", "WebFetch",
    "WebSearch", "EnterPlanMode", "ExitPlanMode",
)


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str


def check_cell_permission(mode: ExecutionMode | str, auto: bool) -> Decision:
    mode = ExecutionMode(mode)
    if not mode.can_materialize:
        return Decision(False, "CELL_APPROVAL_REQUIRED")
    if auto and not mode.can_execute:
        return Decision(False, "CELL_EXECUTION_NOT_APPROVED")
    return Decision(True, "CELL_APPROVED")


@dataclass(frozen=True)
class ToolPolicy:
    mode: ExecutionMode
    cwd: Path
    read_roots: tuple[Path, ...]
    write_root: Path
    allowed_tools: frozenset[str] = frozenset(SDK_TOOLS)
    denied_tools: frozenset[str] = frozenset()
    allowed_skills: frozenset[str] = frozenset()

    def decide(self, name: str, data: dict[str, Any]) -> Decision:
        if name == "Skill":
            if name in self.denied_tools:
                return Decision(False, "TOOL_NOT_ALLOWED")
            skill = data.get("skill")
            if not isinstance(skill, str) or not skill:
                return Decision(False, "INVALID_SKILL")
            if skill not in self.allowed_skills:
                return Decision(False, "SKILL_NOT_ALLOWED")
            return Decision(True, "SKILL_ALLOWED")
        if name not in SDK_TOOLS or name not in self.allowed_tools or name in self.denied_tools:
            return Decision(False, "TOOL_NOT_ALLOWED")
        write = name in {"Write", "Edit"}
        if write and not self.mode.can_execute:
            return Decision(False, "READ_ONLY_MODE")
        raw = data.get("file_path") if name in {"Read", "Write", "Edit"} else data.get("path", ".")
        if not isinstance(raw, str) or not raw or "\x00" in raw:
            return Decision(False, "INVALID_PATH")
        if name == "Glob":
            pattern = data.get("pattern")
            if (
                not isinstance(pattern, str) or not pattern
                or Path(pattern).is_absolute() or ".." in Path(pattern).parts
            ):
                return Decision(False, "INVALID_GLOB")
        try:
            if write:
                # The grant is for the configured directory, not a later symlink target.
                ancestor = self.write_root
                while ancestor != self.cwd and ancestor != ancestor.parent:
                    if ancestor.is_symlink():
                        return Decision(False, "WRITE_ROOT_ALIAS_DENIED")
                    ancestor = ancestor.parent
            requested = Path(raw).expanduser()
            path = (requested if requested.is_absolute() else self.cwd / requested).resolve()
            roots = (self.write_root,) if write else self.read_roots
            root = next((r.resolve() for r in roots if path.is_relative_to(r.resolve())), None)
            if root is None:
                return Decision(False, "PATH_OUTSIDE_SCOPE")
            parts = path.relative_to(root).parts
            if any(p.startswith(".") for p in parts):
                return Decision(False, "HIDDEN_PATH_DENIED")
            if path.exists() and path.is_file() and path.stat().st_nlink > 1:
                return Decision(False, "HARDLINK_DENIED")
            if name in {"Read", "Write", "Edit"} and path.is_dir():
                return Decision(False, "EXPECTED_FILE")
            if path.exists() and not path.is_file() and not path.is_dir():
                return Decision(False, "SPECIAL_FILE_DENIED")
            # Recursive search must not traverse aliases into another scope.
            if name in {"Glob", "Grep"} and path.is_dir():
                for entry in path.rglob("*"):
                    if any(p.startswith(".") for p in entry.relative_to(path).parts):
                        return Decision(False, "SEARCH_HIDDEN_PATH_DENIED")
                    if entry.is_symlink() or (entry.is_file() and entry.stat().st_nlink > 1):
                        return Decision(False, "SEARCH_ALIAS_DENIED")
        except (OSError, RuntimeError, ValueError):
            return Decision(False, "INVALID_PATH")
        return Decision(True, "SCOPED_WRITE" if write else "SCOPED_READ")
