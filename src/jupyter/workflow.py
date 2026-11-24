"""Single source of truth for the Jupyter agent workflow lifecycle."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable, Mapping


class WorkflowState(Enum):
    IDLE = auto()
    AGENT_STREAMING = auto()
    STREAMING = AGENT_STREAMING  # compatibility alias during migration
    PLAN_REVIEW = auto()
    WAITING_CONFIRM = auto()
    CELL_DISPATCHING = auto()
    CELL_EXECUTING = auto()
    AUTO_FIXING = auto()
    INTERRUPTING = auto()


class WorkflowEvent(Enum):
    USER_PROMPT_ACCEPTED = auto()
    AGENT_RETURNED_PLAN = auto()
    AGENT_RETURNED_CODE = auto()
    AGENT_RETURNED_TEXT = auto()
    AGENT_RETURNED_EMPTY = auto()
    USER_CONFIRMED = auto()
    USER_REJECTED = auto()
    PLAN_REVISION_REQUESTED = auto()
    CELL_BATCH_CREATED = auto()
    CELL_MATERIALIZED = auto()
    CELL_STARTED = auto()
    CELL_SUCCEEDED = auto()
    CELL_FAILED = auto()
    CELL_REJECTED = auto()
    CELL_CANCELLED = auto()
    CELL_TIMED_OUT = auto()
    BATCH_SUCCEEDED = auto()
    AUTO_FIX_RETURNED_CODE = auto()
    AUTO_FIX_EXHAUSTED = auto()
    RUN_FINISHED = auto()
    STOP_REQUESTED = auto()
    INTERRUPT_COMPLETED = auto()
    INTERNAL_ERROR = auto()


class WorkflowEffect(Enum):
    START_AGENT_STREAM = auto()
    SHOW_PLAN_CONFIRM = auto()
    SHOW_CODE_CONFIRM = auto()
    CREATE_EXECUTION_BATCH = auto()
    DISPATCH_NEXT_CELL = auto()
    START_AUTO_FIX = auto()
    CANCEL_ACTIVE_BATCH = auto()
    SEND_PANEL_READY = auto()
    APPLY_PENDING_NOTEBOOK_SWITCH = auto()


class InvalidTransition(RuntimeError):
    pass


@dataclass(frozen=True)
class WorkflowStateSnapshot:
    state: WorkflowState
    revision: int
    active_batch_id: str = ""
    completed_cells: int = 0
    total_cells: int = 0
    message: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.name,
            "revision": self.revision,
            "active_batch_id": self.active_batch_id,
            "completed_cells": self.completed_cells,
            "total_cells": self.total_cells,
            "message": self.message,
        }


@dataclass(frozen=True)
class TransitionResult:
    previous: WorkflowState
    current: WorkflowState
    effects: tuple[WorkflowEffect, ...] = ()


class WorkflowStateMachine:
    """Validate lifecycle transitions and publish monotonic state snapshots."""

    def __init__(
        self,
        on_change: Callable[[WorkflowStateSnapshot, str], None] | None = None,
        strict: bool = True,
    ) -> None:
        self._state = WorkflowState.IDLE
        self._revision = 0
        self._active_batch_id = ""
        self._completed_cells = 0
        self._total_cells = 0
        self._message = ""
        self._on_change = on_change
        self._strict = strict

    @property
    def state(self) -> WorkflowState:
        return self._state

    @property
    def accepts_new_prompt(self) -> bool:
        return self._state is WorkflowState.IDLE

    @property
    def awaiting_user(self) -> bool:
        return self._state in {
            WorkflowState.PLAN_REVIEW,
            WorkflowState.WAITING_CONFIRM,
        }

    @property
    def has_active_work(self) -> bool:
        return self._state is not WorkflowState.IDLE

    @property
    def should_defer_notebook_switch(self) -> bool:
        return self.has_active_work

    @property
    def snapshot(self) -> WorkflowStateSnapshot:
        return WorkflowStateSnapshot(
            state=self._state,
            revision=self._revision,
            active_batch_id=self._active_batch_id,
            completed_cells=self._completed_cells,
            total_cells=self._total_cells,
            message=self._message,
        )

    def transition(
        self,
        event: WorkflowEvent,
        payload: Mapping[str, Any] | None = None,
    ) -> TransitionResult:
        payload = payload or {}
        previous = self._state
        resolved = self._resolve(previous, event, payload)
        if resolved is None:
            message = f"invalid workflow transition: {previous.name} + {event.name}"
            if self._strict:
                raise InvalidTransition(message)
            return TransitionResult(previous, previous)

        current, effects = resolved
        self._state = current
        self._apply_payload(current, payload)
        self._revision += 1
        trigger = str(payload.get("trigger") or event.name.lower())
        if self._on_change:
            self._on_change(self.snapshot, trigger)
        return TransitionResult(previous, current, effects)

    def update_context(self, **fields: Any) -> WorkflowStateSnapshot:
        """Publish progress without changing the lifecycle state."""
        self._apply_payload(self._state, fields)
        self._revision += 1
        if self._on_change:
            self._on_change(self.snapshot, str(fields.get("trigger") or "progress"))
        return self.snapshot

    def _resolve(
        self,
        state: WorkflowState,
        event: WorkflowEvent,
        payload: Mapping[str, Any],
    ) -> tuple[WorkflowState, tuple[WorkflowEffect, ...]] | None:
        if event is WorkflowEvent.INTERNAL_ERROR:
            return self._idle()
        if event is WorkflowEvent.RUN_FINISHED and state is not WorkflowState.IDLE:
            return self._idle()
        if event is WorkflowEvent.STOP_REQUESTED and state is not WorkflowState.IDLE:
            return (
                WorkflowState.INTERRUPTING,
                (WorkflowEffect.CANCEL_ACTIVE_BATCH,),
            )
        if state is WorkflowState.INTERRUPTING:
            if event is WorkflowEvent.INTERRUPT_COMPLETED:
                return self._idle()
            return None

        if state is WorkflowState.IDLE:
            if event is WorkflowEvent.USER_PROMPT_ACCEPTED:
                return (
                    WorkflowState.AGENT_STREAMING,
                    (WorkflowEffect.START_AGENT_STREAM,),
                )
            return None

        if state is WorkflowState.AGENT_STREAMING:
            if event is WorkflowEvent.AGENT_RETURNED_PLAN:
                return (
                    WorkflowState.PLAN_REVIEW,
                    (WorkflowEffect.SHOW_PLAN_CONFIRM,),
                )
            if event is WorkflowEvent.AGENT_RETURNED_CODE:
                return (
                    WorkflowState.WAITING_CONFIRM,
                    (WorkflowEffect.SHOW_CODE_CONFIRM,),
                )
            if event in {
                WorkflowEvent.AGENT_RETURNED_TEXT,
                WorkflowEvent.AGENT_RETURNED_EMPTY,
            }:
                return self._idle()
            if event is WorkflowEvent.CELL_BATCH_CREATED:
                return (
                    WorkflowState.CELL_DISPATCHING,
                    (WorkflowEffect.DISPATCH_NEXT_CELL,),
                )
            return None

        if state is WorkflowState.PLAN_REVIEW:
            if event is WorkflowEvent.PLAN_REVISION_REQUESTED:
                return (
                    WorkflowState.AGENT_STREAMING,
                    (WorkflowEffect.START_AGENT_STREAM,),
                )
            if event is WorkflowEvent.USER_CONFIRMED:
                if payload.get("has_code"):
                    return (
                        WorkflowState.CELL_DISPATCHING,
                        (WorkflowEffect.CREATE_EXECUTION_BATCH,),
                    )
                return (
                    WorkflowState.AGENT_STREAMING,
                    (WorkflowEffect.START_AGENT_STREAM,),
                )
            if event is WorkflowEvent.USER_REJECTED:
                return self._idle()
            return None

        if state is WorkflowState.WAITING_CONFIRM:
            if event is WorkflowEvent.USER_CONFIRMED:
                if payload.get("has_code", True):
                    return (
                        WorkflowState.CELL_DISPATCHING,
                        (WorkflowEffect.CREATE_EXECUTION_BATCH,),
                    )
                return (
                    WorkflowState.AGENT_STREAMING,
                    (WorkflowEffect.START_AGENT_STREAM,),
                )
            if event is WorkflowEvent.USER_REJECTED:
                return self._idle()
            return None

        if state is WorkflowState.CELL_DISPATCHING:
            if event is WorkflowEvent.CELL_MATERIALIZED:
                if payload.get("batch_complete"):
                    return self._idle()
                return (WorkflowState.CELL_DISPATCHING, ())
            if event is WorkflowEvent.CELL_STARTED:
                return (WorkflowState.CELL_EXECUTING, ())
            if event is WorkflowEvent.CELL_SUCCEEDED:
                if payload.get("batch_complete"):
                    return self._idle()
                return (
                    WorkflowState.CELL_DISPATCHING,
                    (WorkflowEffect.DISPATCH_NEXT_CELL,),
                )
            if event is WorkflowEvent.CELL_FAILED:
                if payload.get("auto_fix"):
                    return (
                        WorkflowState.AUTO_FIXING,
                        (WorkflowEffect.START_AUTO_FIX,),
                    )
                return self._idle()
            if event in {
                WorkflowEvent.CELL_REJECTED,
                WorkflowEvent.CELL_CANCELLED,
                WorkflowEvent.CELL_TIMED_OUT,
            }:
                return self._idle()
            return None

        if state is WorkflowState.CELL_EXECUTING:
            if event is WorkflowEvent.CELL_SUCCEEDED:
                if payload.get("batch_complete"):
                    return self._idle()
                return (
                    WorkflowState.CELL_DISPATCHING,
                    (WorkflowEffect.DISPATCH_NEXT_CELL,),
                )
            if event is WorkflowEvent.BATCH_SUCCEEDED:
                return self._idle()
            if event is WorkflowEvent.CELL_FAILED:
                if payload.get("auto_fix"):
                    return (
                        WorkflowState.AUTO_FIXING,
                        (WorkflowEffect.START_AUTO_FIX,),
                    )
                return self._idle()
            if event in {
                WorkflowEvent.CELL_CANCELLED,
                WorkflowEvent.CELL_TIMED_OUT,
            }:
                return self._idle()
            return None

        if state is WorkflowState.AUTO_FIXING:
            if event is WorkflowEvent.AUTO_FIX_RETURNED_CODE:
                return (
                    WorkflowState.CELL_DISPATCHING,
                    (WorkflowEffect.CREATE_EXECUTION_BATCH,),
                )
            if event is WorkflowEvent.AUTO_FIX_EXHAUSTED:
                return self._idle()
            return None

    @staticmethod
    def _idle() -> tuple[WorkflowState, tuple[WorkflowEffect, ...]]:
        return (
            WorkflowState.IDLE,
            (
                WorkflowEffect.SEND_PANEL_READY,
                WorkflowEffect.APPLY_PENDING_NOTEBOOK_SWITCH,
            ),
        )

    def _apply_payload(
        self,
        state: WorkflowState,
        payload: Mapping[str, Any],
    ) -> None:
        if "active_batch_id" in payload:
            self._active_batch_id = str(payload["active_batch_id"] or "")
        if "completed_cells" in payload:
            self._completed_cells = int(payload["completed_cells"] or 0)
        if "total_cells" in payload:
            self._total_cells = int(payload["total_cells"] or 0)
        if "message" in payload:
            self._message = str(payload["message"] or "")
        if state is WorkflowState.IDLE:
            self._active_batch_id = ""
            self._completed_cells = 0
            self._total_cells = 0
            self._message = str(payload.get("message") or "")
