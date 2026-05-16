"""Standard tool interface."""

from __future__ import annotations

import importlib
import os
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any, Literal, NotRequired, TypedDict


# ---------------------------------------------------------------------------
# parameter schema types
# ---------------------------------------------------------------------------


class ParamProperty(TypedDict, total=False):
    """JSON Schema property descriptor for tool input parameters."""

    type: str  # "string" | "integer" | "number" | "boolean" | "array" | "object"
    description: str
    default: Any
    items: dict[str, Any]  # array item schema
    enum: list[Any]


class ParamsSchema(TypedDict):
    """JSON Schema object wrapper for tool input parameters."""

    type: Literal["object"]
    properties: dict[str, ParamProperty]
    required: NotRequired[list[str]]


# ---------------------------------------------------------------------------
# return value types
# ---------------------------------------------------------------------------


@dataclass
class ReturnProperty:
    """Describes a single key in the tool's return value.

    Nesting support::

        # array of strings
        ReturnProperty(type="array", items=ReturnProperty(type="str"))

        # array of objects
        ReturnProperty(type="array", items=ReturnProperty(
            type="object",
            properties={"name": ReturnProperty(type="str")},
        ))

        # nested object
        ReturnProperty(type="object", properties={
            "user": ReturnProperty(type="str"),
        })
    """

    type: str  # "str" | "int" | "float" | "bool" | "array" | "object"
    description: str = ""
    items: ReturnProperty | None = None  # element schema when type="array"
    properties: dict[str, ReturnProperty] | None = None  # nested fields when type="object"


# ---------------------------------------------------------------------------
# runtime dependency
# ---------------------------------------------------------------------------


@dataclass
class ToolRequirement:
    """A runtime dependency that must be satisfied for the tool to work.

    Two types are supported:

    * ``"env"`` — an environment variable (checked via ``os.environ``)
    * ``"import"`` — a Python package (checked via ``importlib.import_module``)
    """

    type: str  # "env" | "import"
    key: str  # env var name, or package/module name
    description: str = ""  # human-readable, shown in error messages


# ---------------------------------------------------------------------------
# core types
# ---------------------------------------------------------------------------


@dataclass
class ToolResult:
    """Result returned by a tool execution."""

    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass
class ToolPreset:
    """Tool contract — what the tool does, without implementation."""

    name: str
    description: str
    parameters: ParamsSchema  # JSON Schema (input)
    returns: dict[str, ReturnProperty] = field(default_factory=dict)
    group: str = "custom"


@dataclass
class ToolDef:
    """A tool preset bound to an implementation."""

    preset: ToolPreset
    execute: Callable[[dict[str, Any]], Coroutine[Any, Any, ToolResult]]
    requires: list[ToolRequirement] = field(default_factory=list)

    def check_requirements(self) -> list[str]:
        """Check all requirements. Returns a list of error messages (empty = all OK)."""
        errors: list[str] = []
        for req in self.requires:
            if req.type == "env":
                if os.environ.get(req.key) is None:
                    msg = f"env var '{req.key}' is not set"
                    if req.description:
                        msg += f" ({req.description})"
                    errors.append(msg)
            elif req.type == "import":
                try:
                    importlib.import_module(req.key)
                except ImportError:
                    msg = f"package '{req.key}' is not installed"
                    if req.description:
                        msg += f" ({req.description})"
                    errors.append(msg)
        return errors

    # backward-compat properties
    @property
    def name(self) -> str:
        return self.preset.name

    @property
    def description(self) -> str:
        return self.preset.description

    @property
    def parameters(self) -> dict[str, Any]:
        return self.preset.parameters

    @property
    def group(self) -> str:
        return self.preset.group
