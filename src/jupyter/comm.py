"""Comm notification to frontend extension — fire-and-forget."""

from __future__ import annotations

import logging
import warnings

TARGET_NAME = "skillbot:execute-cell"
_MAX_CODE_SIZE = 100_000  # 100KB max per cell to avoid choking the websocket

_log = logging.getLogger(__name__)


def send_cell_via_comm(ns, code: str, auto: bool = False, cell_type: str = "code",
                       replace_cell_id: str = "", on_cell_id: callable | None = None) -> str:
    """Notify frontend extension to create + optionally execute a cell.

    Fire-and-forget: creates a comm, registers on_msg for async reply,
    does NOT block or poll. The comm stays alive to receive the reply.
    """
    if len(code) > _MAX_CODE_SIZE:
        _log.warning("send_cell_via_comm: code too large (%d bytes), truncating", len(code))
        code = code[:_MAX_CODE_SIZE] + "\n# ...truncated..."
    try:
        from comm import create_comm
        shell = ns._shell
        kernel = shell.kernel

        if not hasattr(kernel, "comm_manager"):
            return ""

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            comm = create_comm(TARGET_NAME,
                               data={"code": code, "auto": auto, "cell_type": cell_type,
                                      "replace_cell_id": replace_cell_id})

            @comm.on_msg
            def _on_msg(msg):
                cell_id = msg.get("content", {}).get("data", {}).get("cell_id", "")
                if cell_id and on_cell_id:
                    on_cell_id(cell_id, code)

            # Don't close — comm stays alive for async reply, GC cleans up later
        return ""
    except Exception:
        _log.debug("send_cell_via_comm: failed", exc_info=True)
        return ""
