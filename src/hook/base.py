"""Hook base classes — Hook, HookGroup, HookRegistry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent.session import AgentSession

from .events import HookResult, HookStatus


class Hook(ABC):
    priority: int = 0

    @abstractmethod
    def on_event(self, event: str, context: dict, session: AgentSession = None) -> HookResult:
        ...

    def __lt__(self, other: "Hook") -> bool:
        return self.priority < other.priority


class HookGroup:
    def __init__(self, name: str, enabled: bool = True, config: dict | None = None) -> None:
        self.name = name
        self.enabled = enabled
        self.config = config or {}
        self._hooks: list[Hook] = []

    def add(self, hook: Hook) -> None:
        self._hooks.append(hook)
        self._hooks.sort()

    @property
    def hooks(self) -> list[Hook]:
        return list(self._hooks) if self.enabled else []


class HookRegistry:
    _events: dict[str, list[Hook]] = {}

    @classmethod
    def clear(cls) -> None:
        cls._events.clear()

    @classmethod
    def register_group(cls, group: HookGroup, *events: str) -> None:
        for event in events:
            cls._events.setdefault(event, []).extend(group.hooks)
            cls._events[event].sort()

    @classmethod
    def dispatch(cls, event: str, context: dict, session: object = None) -> HookResult:
        hook_results: list[dict] = []
        final = HookResult(HookStatus.SUCCESS)
        for hook in cls._events.get(event, []):
            result = hook.on_event(event, context, session=session)
            hook_results.append({
                "hook": type(hook).__name__,
                "status": result.status,
                "message": result.message,
            })
            if result.status == HookStatus.FAILED_STOP:
                final = result
                break
            final = result

        from jupyter.telemetry import get_recorder
        rec = get_recorder()
        if rec:
            rec.record("hook_event",
                hook_type=event,
                hooks=hook_results,
                context_summary={
                    k: str(v)[:200] for k, v in context.items()
                    if k != "ns"
                },
            )
        return final
