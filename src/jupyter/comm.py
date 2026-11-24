"""Compatibility wrapper for one-off Cell Comm requests."""

from __future__ import annotations

import logging
from uuid import uuid4

from .cell_execution import (
    CellCommClient,
    CellExecutionRequest,
    ReceiptPhase,
    current_kernel_id,
)

_log = logging.getLogger(__name__)
_clients: dict[int, CellCommClient] = {}


def send_cell_via_comm(ns, code: str, auto: bool = False, cell_type: str = "code",
                       replace_cell_id: str = "", on_cell_id: callable | None = None) -> str:
    """Send a versioned request outside an Agent execution batch.

    Agent-generated code uses ``ExecutionCoordinator`` directly. This wrapper
    remains for plan markdown, snapshot restore, and hook compatibility.
    """
    try:
        from .magic import _get_magic, _notebook_path
        from agent.permissions import ExecutionMode, check_cell_permission

        if cell_type != "markdown":
            inst = _get_magic()
            decision = check_cell_permission(
                getattr(inst, "_permission_mode", ExecutionMode.DEFAULT), auto,
            )
            if not decision.allowed:
                _log.warning("Compatibility Cell dispatch denied: %s", decision.reason)
                return ""

        request_id = f"req_{uuid4().hex}"
        batch_id = f"batch_{uuid4().hex}"
        request = CellExecutionRequest(
            request_id=request_id,
            batch_id=batch_id,
            notebook_path=_notebook_path(),
            kernel_id=current_kernel_id(),
            operation="replace" if replace_cell_id else "create",
            code=code,
            cell_type=cell_type,
            auto_execute=auto,
            replace_cell_id=replace_cell_id,
        )
        client = _clients.setdefault(id(ns._shell), CellCommClient(ns))

        def _on_receipt(receipt):
            if receipt.phase is ReceiptPhase.MATERIALIZED and on_cell_id:
                on_cell_id(receipt.cell_id, code)

        client.send(request, _on_receipt)
        return request_id
    except Exception:
        _log.debug("send_cell_via_comm: failed", exc_info=True)
        return ""
