"""Tool registry with decorator-based registration and dynamic discovery."""

import importlib
import sys
from functools import wraps
from pathlib import Path

from .interface import ToolDef


class ToolRegistry:
    """Global tool registry with auto-discovery support."""

    _tools: dict[str, ToolDef] = {}

    # ---- registration ----

    @classmethod
    def add(cls, tool: ToolDef) -> None:
        if tool.name in cls._tools:
            raise ValueError(f"Tool '{tool.name}' already registered")
        cls._tools[tool.name] = tool

    @classmethod
    def remove(cls, name: str) -> bool:
        return cls._tools.pop(name, None) is not None

    @classmethod
    def clear(cls) -> None:
        cls._tools.clear()

    # ---- discovery ----

    @classmethod
    def discover(cls, path: str) -> list[ToolDef]:
        """Scan `path` for .py files, import them, collect any @register tools."""
        root = Path(path).resolve()
        if not root.exists():
            return []

        prev_count = len(cls._tools)
        sys.path.insert(0, str(root))
        try:
            for f in sorted(root.glob("*.py")):
                if f.name.startswith("_"):
                    continue
                mod_name = f.stem
                importlib.import_module(mod_name)
        finally:
            sys.path.pop(0)

        new_tools = list(cls._tools.values())[prev_count:]
        return new_tools

    # ---- query ----

    @classmethod
    def list(cls, group: str | None = None) -> list[ToolDef]:
        tools = cls._tools.values()
        if group:
            tools = [t for t in tools if t.group == group]
        return sorted(tools, key=lambda t: t.name)

    @classmethod
    def get(cls, name: str) -> ToolDef | None:
        return cls._tools.get(name)


def register(
    *,
    name: str,
    description: str,
    parameters: dict,
    group: str = "custom",
):
    """Decorator: register a function as a tool.

    Usage::

        @register(name="my_tool", description="...", parameters={...})
        async def my_tool(params: dict) -> ToolResult:
            ...
    """

    def decorator(fn):
        tool = ToolDef(
            name=name,
            description=description,
            parameters=parameters,
            execute=fn,
            group=group,
        )
        ToolRegistry.add(tool)

        @wraps(fn)
        async def wrapper(params):
            return await fn(params)

        return wrapper

    return decorator
