from unittest.mock import MagicMock, patch

import pytest

from agent.permissions import ExecutionMode
from jupyter.magic import AgentMagic
from jupyter.parser import ParsedResult
from jupyter.workflow import WorkflowEvent, WorkflowState, WorkflowStateMachine


@pytest.fixture
def magic():
    m = AgentMagic.__new__(AgentMagic)
    m._workflow = WorkflowStateMachine()
    m._permission_mode = ExecutionMode.DEFAULT
    m._execution = MagicMock()
    m.ns = MagicMock()
    m.ns.delta.return_value = ""
    m._timeout = 1
    m._session_dirty = False
    m._pending_result = None
    m._pending_auto_fix = None
    m._agent_cells = {}
    m._auto_fix_count = 0
    m._workflow_notebook_path = "a.ipynb"
    m._session_nb_path = "a.ipynb"
    m._pending_session_nb_path = None
    m._ensure_session = MagicMock()
    m._session = MagicMock()
    m._session.stream.return_value = '{"text":"ok"}'
    with patch("jupyter.magic.send_to_panel"), patch("jupyter.magic.get_recorder", return_value=None):
        yield m


@pytest.mark.parametrize("mode", [ExecutionMode.PLAN, ExecutionMode.DEFAULT])
def test_readonly_never_dispatches(magic, mode):
    magic._permission_mode = mode
    magic._workflow.transition(WorkflowEvent.USER_PROMPT_ACCEPTED)
    assert magic._submit_code_cells(["print(1)"], auto=True) is None
    magic._execution.submit_batch.assert_not_called()
    assert magic._permission_mode is ExecutionMode.DEFAULT


def test_edit_approval_cannot_execute(magic):
    magic._permission_mode = ExecutionMode.EDIT
    magic._workflow.transition(WorkflowEvent.USER_PROMPT_ACCEPTED)
    magic._submit_code_cells(["print(1)"], auto=True)
    magic._execution.submit_batch.assert_not_called()


def test_confirm_pending_code_grants_execution(magic):
    magic._workflow.transition(WorkflowEvent.USER_PROMPT_ACCEPTED)
    magic._workflow.transition(WorkflowEvent.AGENT_RETURNED_CODE)
    magic._pending_result = ParsedResult(code_list=["print(1)"])
    with patch("jupyter.magic.current_kernel_id", return_value="k"):
        magic._handle_continue("yes")
    assert magic._permission_mode is ExecutionMode.EXECUTE
    magic._execution.submit_batch.assert_called_once()


def test_text_only_default_response_finishes_without_confirmation(magic):
    with patch("jupyter.magic.send_to_panel") as send:
        magic._handle_panel_prompt("hello", mode="default")

    assert magic._state is WorkflowState.IDLE
    assert all(
        not (len(call.args) > 1 and call.args[1] == "continue_confirm")
        for call in send.call_args_list
    )


def test_stale_confirmation_does_not_grant_permission(magic):
    magic._last_plan_result = ParsedResult(code_list=["print(1)"])
    magic._handle_panel_confirm("yes")
    magic._handle_continue("yes")
    assert magic._permission_mode is ExecutionMode.DEFAULT
    magic._execution.submit_batch.assert_not_called()


@pytest.mark.parametrize("mode", ["default", "plan", "auto"])
def test_panel_mode_reaches_agent(magic, mode):
    magic._emit_plan_cell = MagicMock()
    magic._handle_panel_prompt("hello", mode=mode)
    assert magic._session.stream.call_args.kwargs["execution_mode"] == mode


@pytest.mark.parametrize("mode", ["execute", "edit", "bypass"])
def test_panel_cannot_promote_itself_with_internal_mode(magic, mode):
    magic._handle_panel_prompt("hello", mode=mode)
    magic._session.stream.assert_not_called()
    assert magic._permission_mode is ExecutionMode.DEFAULT


@pytest.mark.parametrize("event", [WorkflowEvent.RUN_FINISHED, WorkflowEvent.INTERNAL_ERROR])
def test_terminal_revokes_grant(magic, event):
    magic._permission_mode = ExecutionMode.AUTO
    magic._workflow.transition(WorkflowEvent.USER_PROMPT_ACCEPTED)
    magic._transition(event)
    assert magic._permission_mode is ExecutionMode.DEFAULT


def test_stream_failure_revokes_and_returns_idle(magic):
    magic._permission_mode = ExecutionMode.AUTO
    magic._workflow.transition(WorkflowEvent.USER_PROMPT_ACCEPTED)
    magic._session.stream.side_effect = RuntimeError("blocked")
    assert magic._stream_with_interrupt("hi") == ("", True)
    assert magic._permission_mode is ExecutionMode.DEFAULT
    assert magic._state is WorkflowState.IDLE


def test_legacy_hook_cannot_bypass_confirmation(magic):
    from jupyter.comm import send_cell_via_comm
    with patch("jupyter.magic._get_magic", return_value=magic), patch("jupyter.comm.CellCommClient") as client:
        assert send_cell_via_comm(magic.ns, "print(1)", auto=True) == ""
    client.assert_not_called()


@pytest.mark.parametrize("choice,mode,auto", [
    ("yes", ExecutionMode.EXECUTE, True),
    ("accept_edits", ExecutionMode.EDIT, False),
])
def test_plan_approval_scope(magic, choice, mode, auto):
    magic._workflow.transition(WorkflowEvent.USER_PROMPT_ACCEPTED)
    magic._workflow.transition(WorkflowEvent.AGENT_RETURNED_PLAN)
    magic._last_plan_output = ""
    magic._last_plan_result = ParsedResult(code_list=["print(1)"])
    with patch("jupyter.magic.current_kernel_id", return_value="k"):
        magic._handle_panel_confirm(choice)
    assert magic._permission_mode is mode
    assert magic._execution.submit_batch.call_args.kwargs["auto_execute"] is auto


@pytest.mark.parametrize("request_id", ["req_restore", ""])
def test_snapshot_restore_is_edit_only_and_revoked(magic, request_id):
    magic._restoring_cells = {}

    def dispatch(*_, **kwargs):
        assert magic._permission_mode is ExecutionMode.EDIT
        assert kwargs["auto"] is False
        return request_id

    with patch("jupyter.magic._notebook_path", return_value="a.ipynb"), \
            patch("jupyter.cell_snapshot.restore", return_value="print(1)") as restore, \
            patch("jupyter.comm.send_cell_via_comm", side_effect=dispatch):
        magic._handle_cell_restore("/cell-snapshot-restore cell1 v1")
    restore.assert_called_once_with("cell1", "v1", nb_path="a.ipynb")
    assert magic._permission_mode is ExecutionMode.DEFAULT
    assert ("cell1" in magic._restoring_cells) is bool(request_id)


def test_plan_cell_receipt_updates_replace_target(magic):
    def dispatch(_ns, code, **kwargs):
        assert kwargs["cell_type"] == "markdown"
        assert kwargs["replace_cell_id"] == "previous"
        kwargs["on_cell_id"]("materialized", code)

    magic._plan_cell_id = "previous"
    with patch("jupyter.comm.send_cell_via_comm", side_effect=dispatch):
        magic._emit_plan_cell("Revised plan")
    assert magic._plan_cell_id == "materialized"
