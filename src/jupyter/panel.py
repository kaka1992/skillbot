"""Comm bridge to right-side Agent TUI panel."""

from __future__ import annotations

import logging

_log = logging.getLogger(__name__)
TARGET = "skillbot:tui"


def send_to_panel(ns, action: str, **data) -> bool:
    """Send a display message to the right-hand Agent TUI panel via comm."""
    try:
        from comm import create_comm
        shell = ns._shell
        kernel = shell.kernel
        if not hasattr(kernel, "comm_manager"):
            return False
        comm = create_comm(TARGET, data={"action": action, **data})
        comm.close()
        return True
    except Exception:
        _log.debug("send_to_panel: failed", exc_info=True)
        return False
