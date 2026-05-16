"""Standard tool interface."""

from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    """Result returned by a tool execution."""

    content: str
    error: str | None = None
    files: list[str] = field(default_factory=list)


@dataclass
class ToolDef:
    """Standard tool definition."""

    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema
    execute: Callable[[dict[str, Any]], Coroutine[Any, Any, ToolResult]]
    group: str = "custom"
