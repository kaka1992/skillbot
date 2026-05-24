"""Generic task with dependencies."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Task:
    """A task with dependencies (like Claude Code's task system).

    ``status``: pending → in_progress → done | failed
    ``_blocks`` / ``_blocked_by``: task_id sets for dependency management.
    """

    task_id: str
    subject: str
    description: str = ""
    status: str = "pending"
    owner: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    _blocks: set[str] = field(default_factory=set)
    _blocked_by: set[str] = field(default_factory=set)

    @property
    def is_ready(self) -> bool:
        return self.status == "pending" and len(self._blocked_by) == 0

    def block(self, task_id: str) -> None:
        self._blocks.add(task_id)

    def blocked_by(self, task_id: str) -> None:
        self._blocked_by.add(task_id)
