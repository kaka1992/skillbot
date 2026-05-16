"""Standard tool framework — ToolDef interface + dynamic registration + discovery."""

from .interface import ToolDef, ToolResult
from .registry import ToolRegistry, register

__all__ = [
    "ToolDef",
    "ToolRegistry",
    "ToolResult",
    "register",
]
