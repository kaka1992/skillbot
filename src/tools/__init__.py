"""Standard tool framework — ToolDef interface + dynamic registration + discovery."""

from .interface import ReturnProperty, ToolDef, ToolPreset, ToolRequirement, ToolResult
from .registry import ToolRegistry, impl, register

__all__ = [
    "ReturnProperty",
    "ToolDef",
    "ToolPreset",
    "ToolRequirement",
    "ToolRegistry",
    "ToolResult",
    "impl",
    "register",
]
