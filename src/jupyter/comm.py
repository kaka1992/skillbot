"""Comm notification to frontend extension — fire-and-forget."""

from __future__ import annotations

import logging
import warnings

TARGET_NAME = "skillbot:execute-cell"
_MAX_CODE_SIZE = 100_000  # 100KB max per cell to avoid choking the websocket

_log = logging.getLogger(__name__)


def send_cell_via_comm(ns, code: str, auto: bool = False) -> bool:
    """Notify frontend extension to create + optionally execute a cell.

    Fire-and-forget: opens a comm with *code* and *auto*, closes immediately.
    The ``%agent --trace`` marker (if any) is already part of *code*.
    """
    if len(code) > _MAX_CODE_SIZE:
        _log.warning("send_cell_via_comm: code too large (%d bytes), truncating", len(code))
        code = code[:_MAX_CODE_SIZE] + "\n# ...truncated..."
    try:
        from comm import create_comm
        shell = ns._shell
        kernel = shell.kernel

        if not hasattr(kernel, "comm_manager"):
            return False

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            comm = create_comm(TARGET_NAME,
                               data={"code": code, "auto": auto})
            comm.close()
        return True
    except Exception:
        _log.debug("send_cell_via_comm: failed", exc_info=True)
        return False
