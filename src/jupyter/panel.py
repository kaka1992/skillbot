"""Comm bridge to right-side Agent TUI panel — persistent singleton comm."""

from __future__ import annotations

import logging

_log = logging.getLogger(__name__)
TARGET = "skillbot:tui"
_panel_comm = None


def init_panel_comm(shell) -> None:
    """Register target for frontend-initiated comm. Called once on init."""
    global _panel_comm
    try:
        kernel = shell.kernel
        if not kernel or not hasattr(kernel, "comm_manager"):
            return

        def _on_comm(comm, _open_msg):
            global _panel_comm
            _panel_comm = comm

        kernel.comm_manager.register_target(TARGET, _on_comm)
    except Exception:
        _log.debug("init_panel_comm: failed", exc_info=True)


def send_to_panel(ns, action: str, **data) -> bool:
    """Send a display message to the right-hand Agent TUI panel."""
    global _panel_comm
    if _panel_comm is None:
        return False
    try:
        _panel_comm.send(data={"action": action, **data})
        return True
    except Exception:
        _log.debug("send_to_panel: failed", exc_info=True)
        return False


def send_text(content: str) -> bool:
    """Stream text to the panel output."""
    return send_to_panel(None, "text", content=content)


def send_tool(name: str) -> bool:
    """Render a tool-call marker, e.g. [Bash], [Write]."""
    return send_to_panel(None, "tool", name=name)


def send_thinking(content: str) -> bool:
    """Render a thinking/tool-thought line."""
    return send_to_panel(None, "thinking", content=content)


def send_skill_list(skills: list[dict]) -> bool:
    """Render an interactive skill list."""
    return send_to_panel(None, "skill_list", skills=skills)


def send_skill_info(skill: dict) -> bool:
    """Render a skill detail view."""
    return send_to_panel(None, "skill_info", skill=skill)


def send_code_block(language: str, code: str) -> bool:
    """Render a fenced code block."""
    return send_to_panel(None, "code_block", language=language, code=code)


def send_result(summary: str) -> bool:
    """Render an execution-result summary."""
    return send_to_panel(None, "result", summary=summary)
