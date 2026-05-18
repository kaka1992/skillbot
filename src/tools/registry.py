"""Tool registry with preset-based multi-implementation support."""

from __future__ import annotations

import importlib
import sys
from functools import wraps
from pathlib import Path
from typing import Callable

from .interface import ReturnProperty, ToolDef, ToolPreset, ToolRequirement, ToolResult


class ToolRegistry:
    _tools: dict[str, ToolDef] = {}           # flat: name → ToolDef (default impl)
    _presets: dict[str, ToolPreset] = {}       # name → preset
    _implementations: dict[str, dict[str, ToolDef]] = {}  # preset_name → {impl_name → ToolDef}
    _preferred: dict[str, str] = {}            # preset_name → preferred impl_name

    # ---- preset registration ----

    @classmethod
    def register_preset(cls, preset: ToolPreset) -> None:
        cls._presets[preset.name] = preset
        cls._implementations.setdefault(preset.name, {})

    # ---- implementation registration ----

    @classmethod
    def register_impl(
        cls,
        preset_name: str,
        impl_name: str,
        execute: Callable,
        requires: list[ToolRequirement] | None = None,
    ) -> ToolDef:
        preset = cls._presets.get(preset_name)
        if preset is None:
            raise KeyError(f"Preset '{preset_name}' not found. Register preset first.")
        wrapped = _wrap_with_defaults(execute, preset)
        tool = ToolDef(preset=preset, execute=wrapped, requires=requires or [])
        cls._implementations[preset_name][impl_name] = tool
        if impl_name == "default":
            cls._tools[preset_name] = tool
        return tool

    # ---- flat registration (backward compat) ----

    @classmethod
    def add(cls, tool: ToolDef) -> None:
        """Register a tool. Preset is auto-registered if not present."""
        name = tool.preset.name
        if name not in cls._presets:
            cls._presets[name] = tool.preset
            cls._implementations[name] = {}
        cls._implementations[name]["default"] = tool
        cls._tools[name] = tool

    # ---- requirement checking ----

    @classmethod
    def check_all(cls) -> dict[str, list[str]]:
        """Check requirements for all default tools. Returns ``{tool_name: errors}``."""
        results: dict[str, list[str]] = {}
        for name, tool in cls._tools.items():
            errors = tool.check_requirements()
            if errors:
                results[name] = errors
        return results

    @classmethod
    def remove(cls, name: str) -> bool:
        cls._presets.pop(name, None)
        cls._implementations.pop(name, None)
        return cls._tools.pop(name, None) is not None

    @classmethod
    def clear(cls) -> None:
        cls._tools.clear()
        cls._presets.clear()
        cls._implementations.clear()
        cls._preferred.clear()

    # ---- implementation preference ----

    @classmethod
    def set_preferred(cls, preset_name: str, impl_name: str) -> None:
        """Set the preferred implementation for a preset.

        When ``get(preset_name)`` is called without an explicit *impl*, the
        preferred implementation is returned instead of ``"default"``.
        """
        if preset_name not in cls._presets:
            raise KeyError(f"Preset '{preset_name}' not found")
        if impl_name not in cls._implementations.get(preset_name, {}):
            raise KeyError(f"Implementation '{impl_name}' not found for preset '{preset_name}'")
        cls._preferred[preset_name] = impl_name

    @classmethod
    def reset_preferred(cls, preset_name: str | None = None) -> None:
        """Reset preferred implementations.

        If *preset_name* is given, reset only that preset.
        Otherwise reset all.
        """
        if preset_name is not None:
            cls._preferred.pop(preset_name, None)
        else:
            cls._preferred.clear()

    @classmethod
    def get_preferred(cls, preset_name: str) -> str | None:
        """Return the preferred impl name for *preset_name*, or None."""
        return cls._preferred.get(preset_name)

    # ---- discovery ----

    @classmethod
    def discover(cls, path: str) -> list[ToolDef]:
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
                sys.modules.pop(mod_name, None)
                importlib.import_module(mod_name)
        finally:
            sys.path.pop(0)

        new_tools = list(cls._tools.values())[prev_count:]

        # auto-check requirements for newly discovered tools
        for tool in new_tools[:]:
            errors = tool.check_requirements()
            if errors:
                print(
                    f"\n[ToolRegistry] {tool.name} skipped due to missing dependencies:",
                    file=sys.stderr,
                )
                for err in errors:
                    print(f"  - {err}", file=sys.stderr)
                cls.remove(tool.name)
                new_tools.remove(tool)

        # detect name conflicts from third-party tool loading
        _warn_discover_conflicts(new_tools)

        return new_tools

    # ---- query ----

    @classmethod
    def get(cls, name: str, impl: str | None = None) -> ToolDef | None:
        # impl=None → respect preference, fall back to "default"
        # impl="default" → explicitly bypass preference
        if impl is None:
            preferred = cls._preferred.get(name)
            if preferred:
                return cls._implementations.get(name, {}).get(preferred)
            return cls._tools.get(name)
        if impl == "default":
            return cls._tools.get(name)
        return cls._implementations.get(name, {}).get(impl)

    @classmethod
    def list(cls, group: str | None = None) -> list[ToolDef]:
        tools = cls._tools.values()
        if group:
            tools = [t for t in tools if t.group == group]
        return sorted(tools, key=lambda t: t.name)

    @classmethod
    def list_presets(cls, group: str | None = None) -> list[ToolPreset]:
        presets = cls._presets.values()
        if group:
            presets = [p for p in presets if p.group == group]
        return sorted(presets, key=lambda p: p.name)

    @classmethod
    def list_impls(cls, preset_name: str) -> list[str]:
        return sorted(cls._implementations.get(preset_name, {}).keys())

    @classmethod
    def get_preset(cls, name: str) -> ToolPreset | None:
        return cls._presets.get(name)


def _warn_discover_conflicts(new_tools: list[ToolDef]) -> None:
    """Warn about preset name conflicts and group/preset name collisions."""
    # preset name conflicts: same preset name registered by multiple modules
    seen: dict[str, str] = {}  # preset_name -> first impl's group
    for tool in new_tools:
        name = tool.name
        if name in seen:
            print(
                f"[ToolRegistry] preset name conflict: '{name}' "
                f"overwritten by '{tool.group}' impl (was '{seen[name]}')",
                file=sys.stderr,
            )
        seen[name] = tool.group

    # group/preset name collision: a tool's group matches another tool's preset name
    all_presets = {p.name for p in ToolRegistry.list_presets()}
    for tool in new_tools:
        if tool.group in all_presets and tool.name != tool.group:
            print(
                f"[ToolRegistry] group/preset name collision: "
                f"group '{tool.group}' matches preset '{tool.group}', "
                f"use explicit presets:/groups: in preferences to disambiguate",
                file=sys.stderr,
            )


def _wrap_with_defaults(execute: Callable, preset: ToolPreset) -> Callable:
    """Return an async wrapper that fills in ``default`` values from JSON Schema."""
    properties = preset.parameters.get("properties", {})
    defaults = {k: prop["default"] for k, prop in properties.items() if "default" in prop}

    if not defaults:
        return execute

    @wraps(execute)
    async def wrapped(params: dict) -> ToolResult:
        merged = dict(defaults)
        merged.update(params)
        return await execute(merged)

    return wrapped


def impl(
    preset: ToolPreset,
    impl_name: str = "default",
    requires: list[ToolRequirement] | None = None,
):
    """Decorator: bind a ``ToolPreset`` to a function implementation.

    Usage::

        PRESET = ToolPreset(name="my_tool", description="...", parameters={...})

        @impl(PRESET)
        async def my_tool(params: dict) -> ToolResult:
            ...

        @impl(PRESET, impl_name="v2", requires=[...])
        async def my_tool_v2(params: dict) -> ToolResult:
            ...
    """

    def decorator(fn):
        ToolRegistry.register_preset(preset)
        ToolRegistry.register_impl(preset.name, impl_name, fn, requires=requires)
        return fn

    return decorator


def register(
    *,
    name: str,
    description: str,
    parameters: dict,
    returns: dict[str, str | ReturnProperty] | None = None,
    group: str = "custom",
    requires: list[ToolRequirement] | None = None,
):
    """Decorator: register a function as a tool.

    Usage::

        @register(name="my_tool", description="...", parameters={...})
        async def my_tool(params: dict) -> ToolResult:
            ...
    """

    def decorator(fn):
        preset = ToolPreset(
            name=name,
            description=description,
            parameters=parameters,
            returns=returns or {},
            group=group,
        )
        tool = ToolDef(preset=preset, execute=fn, requires=requires or [])
        ToolRegistry.add(tool)

        @wraps(fn)
        async def wrapper(params):
            return await fn(params)

        return wrapper

    return decorator
