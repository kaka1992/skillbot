"""Versioned Cell Comm protocol and serial execution coordinator."""

from __future__ import annotations

import logging
import threading
import time
import warnings
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Literal
from uuid import uuid4


TARGET_NAME = "skillbot:execute-cell"
PROTOCOL_VERSION = 1
MAX_CODE_SIZE = 100_000

_log = logging.getLogger(__name__)


class ReceiptPhase(str, Enum):
    RECEIVED = "received"
    MATERIALIZED = "materialized"
    STARTED = "started"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class CellRequestState(str, Enum):
    QUEUED = "queued"
    SENT = "sent"
    RECEIVED = "received"
    MATERIALIZED = "materialized"
    STARTED = "started"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


TERMINAL_STATES = {
    CellRequestState.SUCCEEDED,
    CellRequestState.FAILED,
    CellRequestState.REJECTED,
    CellRequestState.CANCELLED,
    CellRequestState.TIMED_OUT,
}


@dataclass(frozen=True)
class CellSpec:
    code: str
    cell_type: Literal["code", "markdown"] = "code"
    replace_cell_id: str = ""
    run_cell_id: str = ""


@dataclass(frozen=True)
class CellExecutionRequest:
    request_id: str
    batch_id: str
    notebook_path: str
    kernel_id: str
    operation: Literal["create", "replace", "run_existing"]
    code: str
    cell_type: Literal["code", "markdown"]
    auto_execute: bool
    replace_cell_id: str = ""
    run_cell_id: str = ""
    sequence_index: int = 0
    sequence_size: int = 1
    timeout_ms: int = 600_000
    protocol_version: int = PROTOCOL_VERSION

    def as_payload(self) -> dict[str, Any]:
        return {"action": "execute_cell", **asdict(self)}


@dataclass(frozen=True)
class CellExecutionReceipt:
    request_id: str
    batch_id: str
    notebook_path: str
    kernel_id: str
    phase: ReceiptPhase
    timestamp_ms: int
    cell_id: str = ""
    execution_count: int | None = None
    elapsed_ms: int | None = None
    error_code: str = ""
    error_message: str = ""
    protocol_version: int = PROTOCOL_VERSION

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> CellExecutionReceipt:
        return cls(
            protocol_version=int(data.get("protocol_version", 0)),
            request_id=str(data.get("request_id", "")),
            batch_id=str(data.get("batch_id", "")),
            notebook_path=str(data.get("notebook_path", "")),
            kernel_id=str(data.get("kernel_id", "")),
            phase=ReceiptPhase(str(data.get("phase", ""))),
            timestamp_ms=int(data.get("timestamp_ms", 0)),
            cell_id=str(data.get("cell_id", "")),
            execution_count=data.get("execution_count"),
            elapsed_ms=data.get("elapsed_ms"),
            error_code=str(data.get("error_code", "")),
            error_message=str(data.get("error_message", ""))[:2000],
        )


@dataclass
class CellRequest:
    request: CellExecutionRequest
    state: CellRequestState = CellRequestState.QUEUED
    cell_id: str = ""
    sent_at_ms: int = 0
    started_at_ms: int = 0
    finished_at_ms: int = 0
    seen_phases: set[ReceiptPhase] = field(default_factory=set)
    timer: threading.Timer | None = field(default=None, repr=False)
    timer_generation: int = field(default=0, repr=False)

    @property
    def terminal(self) -> bool:
        if (
            not self.request.auto_execute
            or self.request.cell_type == "markdown"
        ):
            return self.state in {
                CellRequestState.MATERIALIZED,
                CellRequestState.REJECTED,
                CellRequestState.CANCELLED,
                CellRequestState.TIMED_OUT,
            }
        return self.state in TERMINAL_STATES


@dataclass
class ExecutionBatch:
    batch_id: str
    notebook_path: str
    kernel_id: str
    requests: list[CellRequest]
    fail_fast: bool = True
    created_at_ms: int = 0
    finished_at_ms: int | None = None

    @property
    def terminal_count(self) -> int:
        return sum(item.terminal for item in self.requests)

    @property
    def completed_count(self) -> int:
        return sum(
            item.state in {
                CellRequestState.MATERIALIZED,
                CellRequestState.SUCCEEDED,
            }
            for item in self.requests
        )

    @property
    def is_terminal(self) -> bool:
        return self.terminal_count == len(self.requests)

    @property
    def is_success(self) -> bool:
        return self.is_terminal and all(
            item.state
            in {
                CellRequestState.MATERIALIZED,
                CellRequestState.SUCCEEDED,
            }
            for item in self.requests
        )

    @property
    def next_queued(self) -> CellRequest | None:
        return next(
            (item for item in self.requests if item.state is CellRequestState.QUEUED),
            None,
        )


def current_kernel_id() -> str:
    """Return the current ipykernel id from its connection filename."""
    from ipykernel.connect import get_connection_file

    stem = Path(get_connection_file()).stem
    if not stem.startswith("kernel-"):
        raise RuntimeError("cannot resolve current kernel id")
    return stem.removeprefix("kernel-")


class CellCommClient:
    """Send v1 Cell requests and retain Comms until a terminal receipt."""

    def __init__(self, ns: Any):
        self._ns = ns
        self._active: dict[str, Any] = {}

    def send(
        self,
        request: CellExecutionRequest,
        on_receipt: Callable[[CellExecutionReceipt], None],
    ) -> None:
        from comm import create_comm

        shell = self._ns._shell
        kernel = shell.kernel
        if not hasattr(kernel, "comm_manager"):
            raise RuntimeError("kernel has no comm_manager")

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            comm = create_comm(TARGET_NAME, data=request.as_payload())
        self._active[request.request_id] = comm

        @comm.on_msg
        def _on_msg(msg):
            data = msg.get("content", {}).get("data", {})
            try:
                receipt = CellExecutionReceipt.from_payload(data)
                if receipt.protocol_version != PROTOCOL_VERSION:
                    raise ValueError("unsupported receipt protocol")
                if receipt.request_id != request.request_id:
                    raise ValueError("receipt request_id mismatch")
                on_receipt(receipt)
                if receipt.phase in {
                    ReceiptPhase.SUCCEEDED,
                    ReceiptPhase.FAILED,
                    ReceiptPhase.REJECTED,
                    ReceiptPhase.CANCELLED,
                } or (
                    receipt.phase is ReceiptPhase.MATERIALIZED
                    and (
                        not request.auto_execute
                        or request.cell_type == "markdown"
                    )
                ):
                    self._close(request.request_id)
            except Exception:
                _log.warning("invalid Cell Comm receipt", exc_info=True)

    def close_all(self, reason: str = "") -> None:
        if reason:
            _log.info("closing %d Cell Comms: %s", len(self._active), reason)
        for request_id in list(self._active):
            self._close(request_id)

    def close_request(self, request_id: str) -> None:
        self._close(request_id)

    def _close(self, request_id: str) -> None:
        comm = self._active.pop(request_id, None)
        if comm is not None:
            try:
                comm.close()
            except Exception:
                pass


CoordinatorEventHandler = Callable[
    [str, CellRequest, ExecutionBatch, CellExecutionReceipt | None],
    None,
]
CallbackScheduler = Callable[[Callable[[], None]], None]


class ExecutionCoordinator:
    """Serially materialize/execute Cell requests and aggregate receipts."""

    def __init__(
        self,
        sender: Callable[
            [CellExecutionRequest, Callable[[CellExecutionReceipt], None]],
            None,
        ],
        on_event: CoordinatorEventHandler,
        materialize_timeout_ms: int = 5_000,
        close_request: Callable[[str], None] | None = None,
        schedule: CallbackScheduler | None = None,
    ) -> None:
        self._sender = sender
        self._on_event = on_event
        self._materialize_timeout_ms = materialize_timeout_ms
        self._close_request = close_request
        self._schedule = schedule or (lambda callback: callback())
        self._batches: dict[str, ExecutionBatch] = {}
        self._requests: dict[str, tuple[ExecutionBatch, CellRequest]] = {}
        self._active_batch_id = ""
        self._lock = threading.RLock()

    @property
    def active_batch(self) -> ExecutionBatch | None:
        return self._batches.get(self._active_batch_id)

    def submit_batch(
        self,
        specs: list[CellSpec],
        notebook_path: str,
        kernel_id: str,
        auto_execute: bool,
        timeout_ms: int = 600_000,
        fail_fast: bool = True,
    ) -> ExecutionBatch:
        if not specs:
            raise ValueError("execution batch requires at least one Cell")
        if self.active_batch and not self.active_batch.is_terminal:
            raise RuntimeError("another Cell batch is active")

        batch_id = f"batch_{uuid4().hex}"
        requests: list[CellRequest] = []
        for index, spec in enumerate(specs):
            code = spec.code
            if len(code) > MAX_CODE_SIZE:
                code = code[:MAX_CODE_SIZE] + "\n# ...truncated..."
            operation: Literal["create", "replace", "run_existing"] = "create"
            if spec.run_cell_id:
                operation = "run_existing"
            elif spec.replace_cell_id:
                operation = "replace"
            request = CellExecutionRequest(
                request_id=f"req_{uuid4().hex}",
                batch_id=batch_id,
                notebook_path=notebook_path,
                kernel_id=kernel_id,
                operation=operation,
                code=code,
                cell_type=spec.cell_type,
                auto_execute=auto_execute,
                replace_cell_id=spec.replace_cell_id,
                run_cell_id=spec.run_cell_id,
                sequence_index=index,
                sequence_size=len(specs),
                timeout_ms=timeout_ms,
            )
            item = CellRequest(request=request)
            requests.append(item)

        batch = ExecutionBatch(
            batch_id=batch_id,
            notebook_path=notebook_path,
            kernel_id=kernel_id,
            requests=requests,
            fail_fast=fail_fast,
            created_at_ms=_now_ms(),
        )
        with self._lock:
            self._batches[batch_id] = batch
            self._active_batch_id = batch_id
            for item in requests:
                self._requests[item.request.request_id] = (batch, item)
        self._on_event("batch_created", requests[0], batch, None)
        self._dispatch_next(batch)
        return batch

    def handle_receipt(self, receipt: CellExecutionReceipt) -> None:
        with self._lock:
            pair = self._requests.get(receipt.request_id)
            if pair is None:
                _log.warning("orphan Cell receipt: %s", receipt.request_id)
                return
            batch, item = pair
            if (
                receipt.batch_id != batch.batch_id
                or receipt.notebook_path != batch.notebook_path
                or receipt.kernel_id != batch.kernel_id
            ):
                _log.warning("Cell receipt identity mismatch: %s", receipt.request_id)
                return
            if receipt.phase in item.seen_phases:
                _log.debug(
                    "duplicate Cell receipt: %s %s",
                    receipt.request_id,
                    receipt.phase.value,
                )
                return
            if item.terminal:
                _log.warning(
                    "late Cell receipt ignored: %s %s",
                    receipt.request_id,
                    receipt.phase.value,
                )
                return
            if not self._phase_allowed(item.state, receipt.phase):
                _log.warning(
                    "out-of-order Cell receipt ignored: %s %s -> %s",
                    receipt.request_id,
                    item.state.value,
                    receipt.phase.value,
                )
                return
            item.seen_phases.add(receipt.phase)
            self._apply_receipt(item, receipt)
            self._on_event(receipt.phase.value, item, batch, receipt)
            if item.terminal:
                self._cancel_timer(item)
                if item.state in {
                    CellRequestState.FAILED,
                    CellRequestState.REJECTED,
                    CellRequestState.CANCELLED,
                    CellRequestState.TIMED_OUT,
                } and batch.fail_fast:
                    self._cancel_queued(batch)
                if batch.is_terminal:
                    self._finish_batch(batch)
                elif item.state in {
                    CellRequestState.MATERIALIZED,
                    CellRequestState.SUCCEEDED,
                }:
                    self._dispatch_next(batch)

    def cancel_active(self, reason: str = "cancelled") -> None:
        with self._lock:
            batch = self.active_batch
            if not batch or batch.is_terminal:
                return
            for item in batch.requests:
                if not item.terminal:
                    item.state = CellRequestState.CANCELLED
                    item.finished_at_ms = _now_ms()
                    self._cancel_timer(item)
                    if self._close_request:
                        self._close_request(item.request.request_id)
                    self._on_event("cancelled", item, batch, None)
            self._finish_batch(batch, event="batch_cancelled")
            _log.info("cancelled Cell batch %s: %s", batch.batch_id, reason)

    def _dispatch_next(self, batch: ExecutionBatch) -> None:
        item = batch.next_queued
        if item is None:
            return
        item.state = CellRequestState.SENT
        item.sent_at_ms = _now_ms()
        self._on_event("request_sent", item, batch, None)
        self._cancel_timer(item)
        generation = item.timer_generation
        timer = threading.Timer(
            self._materialize_timeout_ms / 1000,
            self._schedule_timeout,
            args=(
                item.request.request_id,
                "MATERIALIZE_TIMEOUT",
                generation,
            ),
        )
        timer.daemon = True
        item.timer = timer
        timer.start()
        try:
            self._sender(item.request, self.handle_receipt)
        except Exception as exc:
            self._cancel_timer(item)
            receipt = CellExecutionReceipt(
                request_id=item.request.request_id,
                batch_id=batch.batch_id,
                notebook_path=batch.notebook_path,
                kernel_id=batch.kernel_id,
                phase=ReceiptPhase.REJECTED,
                timestamp_ms=_now_ms(),
                error_code="COMM_SEND_ERROR",
                error_message=str(exc),
            )
            self.handle_receipt(receipt)

    def _apply_receipt(
        self,
        item: CellRequest,
        receipt: CellExecutionReceipt,
    ) -> None:
        states = {
            ReceiptPhase.RECEIVED: CellRequestState.RECEIVED,
            ReceiptPhase.MATERIALIZED: CellRequestState.MATERIALIZED,
            ReceiptPhase.STARTED: CellRequestState.STARTED,
            ReceiptPhase.SUCCEEDED: CellRequestState.SUCCEEDED,
            ReceiptPhase.FAILED: CellRequestState.FAILED,
            ReceiptPhase.REJECTED: CellRequestState.REJECTED,
            ReceiptPhase.CANCELLED: CellRequestState.CANCELLED,
        }
        item.state = states[receipt.phase]
        if receipt.cell_id:
            item.cell_id = receipt.cell_id
        if (
            receipt.phase is ReceiptPhase.MATERIALIZED
            and item.request.auto_execute
            and item.request.cell_type != "markdown"
        ):
            self._reset_execution_timer(item)
        elif receipt.phase is ReceiptPhase.STARTED:
            item.started_at_ms = receipt.timestamp_ms or _now_ms()
            self._reset_execution_timer(item)
        if item.terminal:
            item.finished_at_ms = receipt.timestamp_ms or _now_ms()

    def _reset_execution_timer(self, item: CellRequest) -> None:
        self._cancel_timer(item)
        generation = item.timer_generation
        timer = threading.Timer(
            item.request.timeout_ms / 1000,
            self._schedule_timeout,
            args=(
                item.request.request_id,
                "EXECUTION_TIMEOUT",
                generation,
            ),
        )
        timer.daemon = True
        item.timer = timer
        timer.start()

    def _schedule_timeout(
        self,
        request_id: str,
        error_code: str,
        generation: int,
    ) -> None:
        self._schedule(
            lambda: self._timeout_request(request_id, error_code, generation)
        )

    def _timeout_request(
        self,
        request_id: str,
        error_code: str,
        generation: int | None = None,
    ) -> None:
        with self._lock:
            pair = self._requests.get(request_id)
            if pair is None:
                return
            batch, item = pair
            if item.terminal:
                return
            if (
                generation is not None
                and generation != item.timer_generation
            ):
                return
            if (
                error_code == "MATERIALIZE_TIMEOUT"
                and item.state not in {
                    CellRequestState.SENT,
                    CellRequestState.RECEIVED,
                }
            ):
                return
            if (
                error_code == "EXECUTION_TIMEOUT"
                and item.state not in {
                    CellRequestState.MATERIALIZED,
                    CellRequestState.STARTED,
                }
            ):
                return
            item.state = CellRequestState.TIMED_OUT
            item.finished_at_ms = _now_ms()
            if self._close_request:
                self._close_request(item.request.request_id)
            self._on_event("timed_out", item, batch, None)
            if batch.fail_fast:
                self._cancel_queued(batch)
            if batch.is_terminal:
                self._finish_batch(batch)
            _log.warning("Cell request timed out: %s (%s)", request_id, error_code)

    def _cancel_queued(self, batch: ExecutionBatch) -> None:
        for item in batch.requests:
            if item.state is CellRequestState.QUEUED:
                item.state = CellRequestState.CANCELLED
                item.finished_at_ms = _now_ms()
                self._on_event("cancelled", item, batch, None)

    def _finish_batch(
        self,
        batch: ExecutionBatch,
        event: str | None = None,
    ) -> None:
        batch.finished_at_ms = _now_ms()
        if self._active_batch_id == batch.batch_id:
            self._active_batch_id = ""
        if event is None:
            event = "batch_succeeded" if batch.is_success else "batch_failed"
        self._on_event(event, batch.requests[-1], batch, None)
        for item in batch.requests:
            self._requests.pop(item.request.request_id, None)
        self._batches.pop(batch.batch_id, None)

    @staticmethod
    def _cancel_timer(item: CellRequest) -> None:
        item.timer_generation += 1
        if item.timer is not None:
            item.timer.cancel()
            item.timer = None

    @staticmethod
    def _phase_allowed(
        state: CellRequestState,
        phase: ReceiptPhase,
    ) -> bool:
        allowed = {
            CellRequestState.SENT: {
                ReceiptPhase.RECEIVED,
                ReceiptPhase.MATERIALIZED,
                ReceiptPhase.REJECTED,
                ReceiptPhase.CANCELLED,
            },
            CellRequestState.RECEIVED: {
                ReceiptPhase.MATERIALIZED,
                ReceiptPhase.REJECTED,
                ReceiptPhase.CANCELLED,
            },
            CellRequestState.MATERIALIZED: {
                ReceiptPhase.STARTED,
                ReceiptPhase.SUCCEEDED,
                ReceiptPhase.FAILED,
                ReceiptPhase.CANCELLED,
            },
            CellRequestState.STARTED: {
                ReceiptPhase.SUCCEEDED,
                ReceiptPhase.FAILED,
                ReceiptPhase.CANCELLED,
            },
        }
        return phase in allowed.get(state, set())


def _now_ms() -> int:
    return int(time.time() * 1000)
