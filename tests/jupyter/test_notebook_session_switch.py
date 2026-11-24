from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from agent.permissions import ExecutionMode
from jupyter.magic import AgentMagic
from jupyter.workflow import WorkflowEvent, WorkflowState, WorkflowStateMachine


class _Session:
    def __init__(self):
        self.cleanup_calls = 0

    def cleanup(self):
        self.cleanup_calls += 1


def _magic():
    magic = AgentMagic.__new__(AgentMagic)
    magic._workflow = WorkflowStateMachine()
    magic._session_nb_path = "a.ipynb"
    magic._pending_session_nb_path = None
    magic._session_ready = True
    magic._session_dirty = True
    magic._session = _Session()
    magic._pending_result = None
    magic._pending_auto_fix = None
    magic._agent_cells = {}
    magic._auto_fix_count = 0
    magic._workflow_notebook_path = ""
    magic.ns = None
    return magic


def test_busy_notebook_switch_is_applied_after_task_finishes():
    magic = _magic()
    magic._workflow.transition(WorkflowEvent.USER_PROMPT_ACCEPTED)

    magic._handle_notebook_switch("b.ipynb")

    assert magic._session_nb_path == "a.ipynb"
    assert magic._pending_session_nb_path == "b.ipynb"
    assert magic._session.cleanup_calls == 0

    magic._workflow.transition(WorkflowEvent.RUN_FINISHED)
    with patch("jupyter.magic.send_to_panel"):
        magic._apply_pending_notebook_switch()

    assert magic._pending_session_nb_path is None
    assert magic._session_nb_path == "b.ipynb"
    assert magic._session.cleanup_calls == 1
    assert magic._session_ready is False
    assert magic._session_dirty is False


def test_auto_fix_dispatches_implementation_in_auto_fix_state():
    magic = _magic()
    calls = []
    magic._auto_fix_cell_impl = lambda cell_id, code, error: calls.append((cell_id, code, error))
    magic._workflow.transition(WorkflowEvent.USER_PROMPT_ACCEPTED)
    magic._workflow.transition(WorkflowEvent.CELL_BATCH_CREATED)
    magic._workflow.transition(WorkflowEvent.CELL_STARTED)
    magic._workflow.transition(
        WorkflowEvent.CELL_FAILED,
        {"auto_fix": True},
    )

    magic._auto_fix_cell("failed-cell", "broken()", "boom")

    assert calls == [("failed-cell", "broken()", "boom")]


@pytest.mark.parametrize("failed_id", ["second-cell", ""])
def test_batch_auto_fix_only_replaces_the_failed_receipt_cell(failed_id):
    magic = _magic()
    magic._workflow.transition(WorkflowEvent.USER_PROMPT_ACCEPTED)
    magic._workflow.transition(WorkflowEvent.CELL_BATCH_CREATED)
    magic._workflow.transition(WorkflowEvent.CELL_STARTED)
    code = "same_source()"
    earlier = SimpleNamespace(cell_id="first-cell", request=SimpleNamespace(code=code))
    failed = SimpleNamespace(cell_id=failed_id, request=SimpleNamespace(code=code))
    batch = SimpleNamespace(batch_id="batch", completed_count=1, requests=[earlier, failed])
    magic._stream_with_interrupt = Mock(return_value=("```python\nfixed()\n```", False))
    magic._submit_code_cells = Mock()

    with patch("jupyter.magic.send_to_panel"):
        magic._on_execution_event("failed", failed, batch, SimpleNamespace(error_message="boom"))
        magic._on_execution_event("batch_failed", failed, batch, None)

    if failed_id:
        magic._submit_code_cells.assert_called_once_with(
            ["fixed()"], auto=True, replace_cell_id=failed_id,
        )
    else:
        magic._stream_with_interrupt.assert_not_called()
        magic._submit_code_cells.assert_not_called()


def test_terminal_transition_clears_workflow_scoped_data():
    magic = _magic()
    magic._pending_result = object()
    magic._pending_auto_fix = ("old", "broken()", "boom")
    magic._agent_cells = {"old": "code"}
    magic._auto_fix_count = 2
    magic._workflow_notebook_path = "a.ipynb"
    magic._workflow.transition(WorkflowEvent.USER_PROMPT_ACCEPTED)

    with patch("jupyter.magic.send_to_panel"):
        magic._transition(WorkflowEvent.RUN_FINISHED)

    assert magic._pending_result is None
    assert magic._pending_auto_fix is None
    assert magic._agent_cells == {}
    assert magic._auto_fix_count == 0
    assert magic._workflow_notebook_path == ""


def test_session_init_failure_returns_workflow_to_idle():
    magic = _magic()
    magic._ensure_session = lambda: (_ for _ in ()).throw(RuntimeError("boom"))

    with (
        patch("jupyter.magic._notebook_path", return_value="a.ipynb"),
        patch("jupyter.magic.send_to_panel"),
    ):
        magic._handle_panel_prompt("hello")

    assert magic._state is WorkflowState.IDLE
    assert magic._workflow_notebook_path == ""


def test_cell_batch_uses_workflow_origin_not_live_notebook():
    magic = _magic()
    magic._permission_mode = ExecutionMode.AUTO
    magic._timeout = 1
    magic._workflow_notebook_path = "origin.ipynb"
    calls = []

    class _Execution:
        def submit_batch(self, specs, **kwargs):
            calls.append((specs, kwargs))
            return object()

    magic._execution = _Execution()
    magic._workflow.transition(WorkflowEvent.USER_PROMPT_ACCEPTED)

    with (
        patch("jupyter.magic._notebook_path", return_value="other.ipynb"),
        patch("jupyter.magic.current_kernel_id", return_value="kernel-1"),
    ):
        magic._submit_code_cells(["print(1)"], auto=True)

    assert calls[0][1]["notebook_path"] == "origin.ipynb"


def test_referenced_edit_target_replaces_only_first_dispatched_cell():
    magic = _magic()
    magic._permission_mode = ExecutionMode.EDIT
    magic._timeout = 1
    magic._workflow_notebook_path = "origin.ipynb"
    magic._referenced_replace_cell_id = "cell-target"
    calls = []

    class _Execution:
        def submit_batch(self, specs, **kwargs):
            calls.append((specs, kwargs))
            return object()

    magic._execution = _Execution()
    magic._workflow.transition(WorkflowEvent.USER_PROMPT_ACCEPTED)

    with patch("jupyter.magic.current_kernel_id", return_value="kernel-1"):
        magic._submit_code_cells(["print(1)", "print(2)"], auto=False)

    specs = calls[0][0]
    assert specs[0].replace_cell_id == "cell-target"
    assert specs[1].replace_cell_id == ""
    assert magic._referenced_replace_cell_id == ""


def test_latest_busy_notebook_switch_wins():
    magic = _magic()
    magic._workflow.transition(WorkflowEvent.USER_PROMPT_ACCEPTED)

    magic._handle_notebook_switch("b.ipynb")
    magic._handle_notebook_switch("c.ipynb")

    magic._workflow.transition(WorkflowEvent.RUN_FINISHED)
    with patch("jupyter.magic.send_to_panel"):
        magic._apply_pending_notebook_switch()

    assert magic._session_nb_path == "c.ipynb"
    assert magic._session.cleanup_calls == 1
