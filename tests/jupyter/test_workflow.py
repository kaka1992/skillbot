import pytest

from jupyter.workflow import (
    InvalidTransition,
    WorkflowEvent,
    WorkflowState,
    WorkflowStateMachine,
)


def test_prompt_to_plan_to_idle():
    changes = []
    machine = WorkflowStateMachine(
        on_change=lambda snapshot, trigger: changes.append((snapshot, trigger))
    )

    machine.transition(WorkflowEvent.USER_PROMPT_ACCEPTED)
    machine.transition(WorkflowEvent.AGENT_RETURNED_PLAN)
    machine.transition(WorkflowEvent.USER_REJECTED)

    assert machine.state is WorkflowState.IDLE
    assert [item[0].revision for item in changes] == [1, 2, 3]
    assert changes[-1][0].state is WorkflowState.IDLE


def test_auto_batch_success_path():
    machine = WorkflowStateMachine()

    machine.transition(WorkflowEvent.USER_PROMPT_ACCEPTED)
    machine.transition(
        WorkflowEvent.CELL_BATCH_CREATED,
        {"active_batch_id": "batch-1", "total_cells": 2},
    )
    machine.transition(WorkflowEvent.CELL_MATERIALIZED)
    machine.transition(WorkflowEvent.CELL_STARTED)
    machine.transition(
        WorkflowEvent.CELL_SUCCEEDED,
        {"batch_complete": False, "completed_cells": 1},
    )
    machine.transition(WorkflowEvent.CELL_MATERIALIZED)
    machine.transition(WorkflowEvent.CELL_STARTED)
    machine.transition(
        WorkflowEvent.CELL_SUCCEEDED,
        {"batch_complete": True, "completed_cells": 2},
    )

    assert machine.state is WorkflowState.IDLE
    assert machine.snapshot.active_batch_id == ""


def test_failure_can_enter_auto_fix_and_return_new_batch():
    machine = WorkflowStateMachine()
    machine.transition(WorkflowEvent.USER_PROMPT_ACCEPTED)
    machine.transition(WorkflowEvent.CELL_BATCH_CREATED)
    machine.transition(WorkflowEvent.CELL_STARTED)
    machine.transition(WorkflowEvent.CELL_FAILED, {"auto_fix": True})
    assert machine.state is WorkflowState.AUTO_FIXING

    machine.transition(WorkflowEvent.AUTO_FIX_RETURNED_CODE)
    assert machine.state is WorkflowState.CELL_DISPATCHING


@pytest.mark.parametrize(
    ("event", "payload", "expected"),
    [
        (
            WorkflowEvent.CELL_SUCCEEDED,
            {"batch_complete": True},
            WorkflowState.IDLE,
        ),
        (
            WorkflowEvent.CELL_FAILED,
            {"auto_fix": True},
            WorkflowState.AUTO_FIXING,
        ),
        (
            WorkflowEvent.CELL_FAILED,
            {"auto_fix": False},
            WorkflowState.IDLE,
        ),
    ],
)
def test_dispatching_accepts_terminal_receipt_without_started(
    event,
    payload,
    expected,
):
    machine = WorkflowStateMachine()
    machine.transition(WorkflowEvent.USER_PROMPT_ACCEPTED)
    machine.transition(WorkflowEvent.CELL_BATCH_CREATED)
    machine.transition(WorkflowEvent.CELL_MATERIALIZED)

    machine.transition(event, payload)

    assert machine.state is expected


def test_stop_from_active_state():
    machine = WorkflowStateMachine()
    machine.transition(WorkflowEvent.USER_PROMPT_ACCEPTED)
    machine.transition(WorkflowEvent.STOP_REQUESTED)
    assert machine.state is WorkflowState.INTERRUPTING

    machine.transition(WorkflowEvent.INTERRUPT_COMPLETED)
    assert machine.state is WorkflowState.IDLE


def test_invalid_transition_raises_without_mutation():
    machine = WorkflowStateMachine()
    with pytest.raises(InvalidTransition):
        machine.transition(WorkflowEvent.CELL_SUCCEEDED)
    assert machine.state is WorkflowState.IDLE
    assert machine.snapshot.revision == 0


def test_capabilities_are_derived_from_state():
    machine = WorkflowStateMachine()
    assert machine.accepts_new_prompt
    assert not machine.has_active_work

    machine.transition(WorkflowEvent.USER_PROMPT_ACCEPTED)
    machine.transition(WorkflowEvent.AGENT_RETURNED_CODE)
    assert machine.awaiting_user
    assert machine.has_active_work
    assert not machine.accepts_new_prompt


def test_text_only_response_finishes_without_confirmation():
    machine = WorkflowStateMachine()

    machine.transition(WorkflowEvent.USER_PROMPT_ACCEPTED)
    result = machine.transition(WorkflowEvent.AGENT_RETURNED_TEXT)

    assert result.current is WorkflowState.IDLE
    assert not machine.awaiting_user
    assert machine.accepts_new_prompt
