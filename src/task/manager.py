"""TaskManager — CRUD + dependency resolution."""

from __future__ import annotations

from .task import Task


class TaskManager:
    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}

    def add(self, task: Task) -> None:
        self._tasks[task.task_id] = task

    def get(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    def list(self, status: str | None = None) -> list[Task]:
        tasks = self._tasks.values()
        if status:
            tasks = [t for t in tasks if t.status == status]
        return sorted(tasks, key=lambda t: t.task_id)

    def update(self, task_id: str, **fields) -> None:
        t = self._tasks.get(task_id)
        if t is None:
            raise KeyError(f"Task not found: {task_id}")
        for k, v in fields.items():
            if hasattr(t, k):
                setattr(t, k, v)

    def remove(self, task_id: str) -> bool:
        return self._tasks.pop(task_id, None) is not None

    def set_dep(self, task_id: str, blocked_by: list[str]) -> None:
        """Set dependencies: *task_id* depends on tasks in *blocked_by*."""
        t = self._tasks.get(task_id)
        if t is None:
            raise KeyError(f"Task not found: {task_id}")
        for dep_id in blocked_by:
            dep = self._tasks.get(dep_id)
            if dep:
                t.blocked_by(dep_id)
                dep.block(task_id)

    def ready_tasks(self) -> list[Task]:
        return [t for t in self._tasks.values() if t.is_ready]
