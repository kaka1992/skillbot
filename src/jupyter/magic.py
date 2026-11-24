"""%%sql cell magic + agent panel integration — thin scheduling layer."""

import hashlib
import html
import logging
import os as _os
import shlex
import sys
import time

from IPython.core.magic import Magics, cell_magic, line_magic, magics_class

from agent import AgentSession, SubAgentConfig
from agent.permissions import ExecutionMode, check_cell_permission
from agent.prompt import PromptBuilder, SECTIONS
from chat import _AGENTS
from hook import HookGroup, HookRegistry, HookEvent
from jupyter.telemetry import get_recorder, SessionEventRecorder, set_recorder
from .config import pop_flag, parse_kv, configure_agent, load_yaml_config
from .namespace import Namespace
from .panel import send_to_panel, send_thinking
from .parser import parse, parse_json_envelope
from .render import (
    prepare_cell_code,
    render_debug,
    render_error,
    render_info,
    render_output,
    render_sql_dataframe,
)
from .cell_execution import (
    CellCommClient,
    CellRequest,
    CellSpec,
    ExecutionBatch,
    ExecutionCoordinator,
    current_kernel_id,
)
from .cell_reference import (
    format_cell_references,
    parse_cell_references,
    referenced_edit_target,
)
from .workflow import WorkflowEvent, WorkflowState, WorkflowStateMachine
from .dsl.sql import SqlRunner, sql_progress
from hook.impl.code_review import AgentCodeReviewHook
from hook.impl.cell_review import AgentCellReviewHook

_log = logging.getLogger(__name__)

_INTERRUPT_NOTE = (
    "[System note: The user cancelled the previous request with Ctrl+C. "
    "Completely disregard the prior exchange — do NOT continue, reference, or respond to it. "
    "Respond ONLY to the current prompt below as if starting fresh.]"
)

SUB_AGENT_DEFAULTS = {
    "code_review": SubAgentConfig(
        name="code_review",
        description="Review code cells for logic consistency",
        tools=["Read", "Grep", "Glob"],
    ),
    "cell_review": SubAgentConfig(
        name="cell_review",
        description="Review agent output and task progress",
        tools=["Read"],
    ),
}


class _PanelTextStream:
    """Hold a possible JSON envelope until it can be rendered cleanly."""

    _PREFIXES = ("{", "```json")

    def __init__(self, emit) -> None:
        self._emit = emit
        self._buffer = ""
        self._passthrough = False

    def feed(self, chunk: str) -> None:
        if self._passthrough:
            self._emit(chunk)
            return

        self._buffer += chunk
        stripped = self._buffer.lstrip()
        if not stripped:
            return
        if stripped.startswith(self._PREFIXES):
            return
        if any(prefix.startswith(stripped) for prefix in self._PREFIXES):
            return

        self._passthrough = True
        self._emit(self._buffer)
        self._buffer = ""

    def finish(self) -> None:
        if self._passthrough or not self._buffer:
            return
        result = parse_json_envelope(self._buffer)
        if result is None:
            self._emit(self._buffer)
        elif result.text:
            self._emit(result.text)
        self._buffer = ""


# ---------------------------------------------------------------------------
# jupyter-specific session helpers
# ---------------------------------------------------------------------------


# Set by frontend when notebook is activated — authoritative path for snapshot isolation
_active_notebook_path = ""


def _set_active_notebook_path(path: str) -> None:
    """Called by frontend to set the active notebook path for snapshot isolation."""
    global _active_notebook_path
    _active_notebook_path = path


def _notebook_path() -> str:
    """Return the notebook file path.

    Uses the frontend-provided path (most reliable), falls back to
    parent_header metadata, ip._notebook_path, then CWD.
    """
    global _active_notebook_path
    if _active_notebook_path:
        return _active_notebook_path
    try:
        ip = get_ipython()  # noqa: F821
        kernel = getattr(ip, "kernel", None)
        parent = getattr(kernel, "_parent_header", None) or {}
        nb = (parent.get("metadata") or {}).get("notebook_path")
        if nb:
            return nb
        nb = getattr(ip, "_notebook_path", None)
        if nb:
            return nb
    except Exception:
        pass
    return _os.path.realpath(_os.getcwd())


def _session_key() -> str:
    return hashlib.md5(_notebook_path().encode()).hexdigest()[:12]


def _get_magic():
    """Return the singleton AgentMagic instance, or None."""
    import sys as _sys
    mod = _sys.modules.get(__name__)
    return getattr(mod, "_agent_magic_instance", None)


def _panel_input(
    text: str,
    mode: str = "default",
    cell_references: str = "",
) -> None:
    """Bridge: called by frontend requestExecute → dispatches to AgentMagic."""
    inst = _get_magic()
    if inst:
        inst._on_panel_input(text, mode, cell_references)


def _panel_set_mode(mode: str) -> None:
    """Set mode without triggering agent execution."""
    inst = _get_magic()
    if inst:
        inst._handle_panel_mode(mode)


def _panel_track_cell_edit(source: str) -> None:
    """Record unexecuted cell edit in namespace."""
    inst = _get_magic()
    if inst:
        inst.ns.track_pending_edit(source)


def _panel_track_cell_delete(source: str) -> None:
    """Remove deleted cell from namespace context."""
    inst = _get_magic()
    if inst:
        inst.ns.remove_cell(source)


def _panel_save_conversation(nb_path: str, payload: str) -> None:
    """Bridge: persist a notebook's conversation buffer to disk."""
    from jupyter.conversation_store import save_conversation
    save_conversation(nb_path, payload)


def _panel_load_conversation(nb_path: str) -> None:
    """Bridge: load a persisted conversation buffer and push it to the panel.

    Emits a ``restore_conversation`` comm action the frontend listens for.
    """
    from jupyter.conversation_store import load_conversation
    from jupyter.panel import send_to_panel
    payload = load_conversation(nb_path)
    if payload:
        send_to_panel(None, "restore_conversation", path=nb_path, buffer=payload)


def _panel_list_conversations() -> None:
    """Bridge: push the list of persisted conversations to the panel switcher."""
    from jupyter.conversation_store import list_conversations
    from jupyter.panel import send_to_panel
    send_to_panel(None, "conversation_list", sessions=list_conversations())


def _panel_delete_conversation(nb_path: str) -> None:
    """Bridge: delete a notebook's persisted conversation from disk.

    Called when the user removes a session from the switcher, or when the
    underlying .ipynb file is deleted in the file browser.
    """
    from jupyter.conversation_store import delete_conversation
    delete_conversation(nb_path)


def _panel_switch_notebook(nb_path: str) -> None:
    """Bridge: the active notebook changed — give it its own agent conversation.

    The backend AgentMagic is a kernel-wide singleton with a single LLM session,
    so switching/opening a notebook must reset the agent's conversation memory,
    otherwise the new notebook inherits the previous one's history. Note this
    resets *LLM memory* only; the kernel's Python namespace is shared across all
    notebooks on the same kernel and cannot be per-notebook isolated.
    """
    inst = _get_magic()
    if inst:
        inst._handle_notebook_switch(nb_path)


def _merge_prompt(claude_md_path: str | None = None) -> str:
    return PromptBuilder.main(claude_md_path)


def _build_kb_view_html() -> str:
    """Load ``scripts/kb_view.py`` (not a package) and build the KB HTML view.

    Imported lazily by the %kb_view magic so kernel startup stays cheap and the
    heavy pygments/mistune render only runs on demand.
    """
    import importlib.util
    from pathlib import Path

    kb_path = Path(__file__).resolve().parents[2] / "scripts" / "kb_view.py"
    if not kb_path.is_file():
        raise FileNotFoundError(str(kb_path))
    spec = importlib.util.spec_from_file_location("kb_view", kb_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.build_html()


# ---------------------------------------------------------------------------
# Gallery bridges — called from the left-hand SkillsGalleryWidget via
# `get_ipython().user_ns['_gallery_*']()`, mirroring the `_panel_*` pattern.
# ---------------------------------------------------------------------------

def _gallery_skill_manager():
    """Resolve a SkillManager for the configured agent (best effort)."""
    inst = _get_magic()
    session = getattr(inst, "_session", None) if inst else None
    if session and getattr(session, "client", None):
        return session.client.skills
    try:
        from chat.skill import SkillManager
        from chat import _resolve_skill_dir
        agent = getattr(inst, "_agent", None) or AgentMagic._agent
        return SkillManager(_resolve_skill_dir(agent))
    except Exception:
        _log.debug("_gallery_skill_manager: failed", exc_info=True)
        return None


def _gallery_kb_manifest() -> list[dict]:
    """Return lightweight KB doc metadata (no rendered bodies) for the list."""
    import json as _json
    from pathlib import Path

    manifest = (
        Path(__file__).resolve().parents[2]
        / "skills" / "risk-knowledge-base" / "manifest.json"
    )
    if not manifest.is_file():
        return []
    items = _json.loads(manifest.read_text(encoding="utf-8"))
    return [
        {
            # `docN` matches kb_view's per-doc id (same manifest ordering), so
            # the gallery can deep-link straight to this card in the HTML view.
            "id": f"doc{i}",
            "title": it.get("title", ""),
            "summary": it.get("summary", ""),
            "category": it.get("category", ""),
            "path": it.get("path", ""),
            "source_url": it.get("source_url", ""),
            "tags": it.get("tags", []),
        }
        for i, it in enumerate(items)
    ]


def _gallery_refresh() -> None:
    """Push the skill list + KB manifest to the gallery widget."""
    from .panel import send_to_gallery

    mgr = _gallery_skill_manager()
    if mgr:
        try:
            skills = [
                {"name": s.name, "description": s.description, "enabled": s.enabled}
                for s in mgr.list_skills()
            ]
        except Exception:
            _log.debug("_gallery_refresh: list_skills failed", exc_info=True)
            skills = []
    else:
        skills = []
    send_to_gallery("gallery_skills", skills=skills)

    try:
        docs = _gallery_kb_manifest()
    except Exception:
        _log.debug("_gallery_refresh: kb manifest failed", exc_info=True)
        docs = []
    send_to_gallery("gallery_kb", docs=docs)


def _gallery_kb_html(_path: str = "") -> None:
    """Render the full KB HTML view and push it to the gallery for a new tab.

    The view is one self-contained page; the frontend deep-links to the clicked
    card via a postMessage handshake (``doc<N>`` ids), so ``_path`` is retained
    only for logging/traceability.
    """
    from .panel import send_to_gallery

    try:
        doc = _build_kb_view_html()
    except Exception:
        _log.exception("_gallery_kb_html: build failed")
        return
    send_to_gallery("gallery_kb_html", html=doc, path=_path)


def _register_hooks(timeout: int, hook_cfg: dict) -> None:
    cfg = hook_cfg or {}
    groups = cfg.get("groups", {})
    cr_cfg = groups.get("code_review", {})
    cr_group = HookGroup("code_review", enabled=cr_cfg.get("enabled", True))
    cr_group.add(AgentCodeReviewHook())
    HookRegistry.register_group(cr_group, HookEvent.CODE_REVIEW)

    cell_review_cfg = groups.get("agent_cell_review", {})
    cell_review_group = HookGroup("agent_cell_review", enabled=cell_review_cfg.get("enabled", True))
    cell_review_group.add(AgentCellReviewHook(timeout=timeout))
    HookRegistry.register_group(cell_review_group, HookEvent.AGENT_CELL_REVIEW)


AgentState = WorkflowState


@magics_class
class AgentMagic(Magics):
    _agent = "claude-code"
    _permission_mode = ExecutionMode.DEFAULT
    _timeout = 600
    _claude_md_path: str | None = None
    _tools_cfg: dict = {}

    def __init__(self, shell):
        super().__init__(shell)
        import sys as _sys
        _sys.modules[__name__]._agent_magic_instance = self
        self.ns = Namespace(shell)
        self._workflow = WorkflowStateMachine(
            on_change=self._on_workflow_change,
            strict=False,
        )
        self._cell_client = CellCommClient(self.ns)
        self._execution = ExecutionCoordinator(
            self._cell_client.send,
            self._on_execution_event,
            close_request=self._cell_client.close_request,
            schedule=self._schedule_on_kernel_loop,
        )
        self._last_plan_prompt = ""
        self._last_plan_output = ""
        self._last_plan_result = None                  # cached ParsedResult for _implement_plan
        self._plan_cell_id = ""                        # notebook markdown cell holding the current plan
        self._pending_result = None                    # ParsedResult waiting for user confirmation
        self._agent_cells: dict[str, str] = {}     # cell_id → code, for auto-fix lookup
        self._round_results: list[dict] = []        # [{cell_id, code, output}] for auto-fix lookup
        self._auto_fix_count = 0                    # limit retries per batch
        self._pending_auto_fix = None               # (code, error) after failed batch closes
        self._session_ready = False                 # lazy-init session on first query
        self._session_dirty = False                 # set on interrupt, prepend note on next query
        self._jupyter_config_path = ""              # path from JUPYTER_CONFIG_PATH env var
        self._config_pending = None                 # pending (resolved, new_path, old_path)
        self._cell_restored = False                 # track if any cell was individually restored
        self._restoring_cells: dict[str, float] = {}  # cell_id → restore timestamp (300s TTL)
        self._cell_start_ts: float = 0.0
        self._session_nb_path = None                # notebook path the current agent session is bound to
        self._pending_session_nb_path = None        # deferred switch requested while the agent is busy
        self._workflow_notebook_path = ""           # notebook pinned for the active workflow
        self._referenced_replace_cell_id = ""       # explicit @Cell edit target for this workflow

        self._load_dotenv()

        # Load default config for hooks baseline, then auto-load from env var
        cfg = load_yaml_config("conf/jupyter_agent.yaml")
        self._hook_cfg = cfg.get("hooks", {})
        self._startup_config_msg = self._load_jupyter_config()
        self.ns.delta()
        shell.events.register("pre_run_cell", self._on_cell_start)
        shell.events.register("post_run_cell", self._on_cell_run)
        from .panel import init_panel_comm, init_gallery_comm
        init_panel_comm(shell)
        init_gallery_comm(shell)

    # ---- state machine helpers -----------------------------------------------

    @property
    def _state(self) -> WorkflowState:
        return self._workflow.state

    def _schedule_on_kernel_loop(self, callback) -> None:
        loop = getattr(getattr(self.shell, "kernel", None), "io_loop", None)
        if loop is None:
            callback()
            return
        loop.add_callback(callback)

    def _transition(self, event: WorkflowEvent, **payload):
        result = self._workflow.transition(event, payload)
        if (
            result.current is WorkflowState.IDLE
            and result.previous is not WorkflowState.IDLE
        ):
            self._permission_mode = ExecutionMode.DEFAULT
            self._pending_result = None
            self._pending_auto_fix = None
            self._round_results.clear()
            self._agent_cells.clear()
            self._auto_fix_count = 0
            self._workflow_notebook_path = ""
            self._referenced_replace_cell_id = ""
            self._apply_pending_notebook_switch()
            send_to_panel(self.ns, "ready")
        return result

    def _on_workflow_change(self, snapshot, trigger: str) -> None:
        rec = get_recorder()
        if rec:
            rec.record(
                "workflow_state",
                state=snapshot.state.name,
                trigger=trigger,
                revision=snapshot.revision,
                active_batch_id=snapshot.active_batch_id,
                completed_cells=snapshot.completed_cells,
                total_cells=snapshot.total_cells,
            )
        send_to_panel(
            self.ns,
            "workflow_state",
            **snapshot.as_dict(),
        )

    def _submit_code_cells(
        self,
        codes: list[str],
        auto: bool,
        replace_cell_id: str = "",
    ) -> ExecutionBatch | None:
        if not codes:
            return None
        decision = check_cell_permission(self._permission_mode, auto)
        if not decision.allowed or self._state in {
            WorkflowState.IDLE, WorkflowState.INTERRUPTING,
        }:
            send_to_panel(
                self.ns, "text",
                content=f"Execution blocked: {decision.reason if not decision.allowed else 'NO_ACTIVE_WORKFLOW'}\n",
            )
            self._transition(WorkflowEvent.INTERNAL_ERROR, trigger="permission_denied")
            return None
        if self._state is WorkflowState.AGENT_STREAMING:
            self._transition(WorkflowEvent.CELL_BATCH_CREATED)
        elif self._state is WorkflowState.WAITING_CONFIRM:
            self._transition(WorkflowEvent.USER_CONFIRMED, has_code=True)
        elif self._state is WorkflowState.PLAN_REVIEW:
            self._transition(WorkflowEvent.USER_CONFIRMED, has_code=True)
        elif self._state is WorkflowState.AUTO_FIXING:
            self._transition(WorkflowEvent.AUTO_FIX_RETURNED_CODE)

        effective_replace_id = (
            replace_cell_id
            or getattr(self, "_referenced_replace_cell_id", "")
        )
        self._referenced_replace_cell_id = ""
        specs = [
            CellSpec(
                code=prepare_cell_code(code, "code"),
                replace_cell_id=effective_replace_id if index == 0 else "",
            )
            for index, code in enumerate(codes)
        ]
        try:
            notebook_path = (
                self._workflow_notebook_path
                or self._session_nb_path
                or _notebook_path()
            )
            return self._execution.submit_batch(
                specs,
                notebook_path=notebook_path,
                kernel_id=current_kernel_id(),
                auto_execute=auto,
                timeout_ms=self._timeout * 1000,
            )
        except Exception as exc:
            _log.exception("submit Cell batch failed")
            self._transition(
                WorkflowEvent.INTERNAL_ERROR,
                message=f"Cell dispatch failed: {exc}",
            )
            send_to_panel(
                self.ns,
                "text",
                content=f"✗ Cell dispatch failed: {exc}\n",
            )
            return None

    def _on_execution_event(
        self,
        event: str,
        item: CellRequest,
        batch: ExecutionBatch,
        receipt,
    ) -> None:
        progress = {
            "active_batch_id": batch.batch_id,
            "completed_cells": batch.completed_count,
            "total_cells": len(batch.requests),
            "trigger": f"cell_{event}",
        }
        if event == "batch_created":
            self._workflow.update_context(**progress)
            return
        if event == "materialized":
            if item.cell_id:
                self._track_agent_cell(item.cell_id, item.request.code)
            self._transition(
                WorkflowEvent.CELL_MATERIALIZED,
                batch_complete=batch.is_terminal,
                **progress,
            )
            return
        if event == "started":
            self._transition(WorkflowEvent.CELL_STARTED, **progress)
            return
        if event == "succeeded":
            self._transition(
                WorkflowEvent.CELL_SUCCEEDED,
                batch_complete=batch.is_terminal,
                **progress,
            )
            return
        if event == "failed":
            error = getattr(receipt, "error_message", "") or "Cell execution failed"
            can_fix = self._auto_fix_count < 2
            self._transition(
                WorkflowEvent.CELL_FAILED,
                auto_fix=can_fix,
                message=error,
                **progress,
            )
            if can_fix:
                self._pending_auto_fix = (item.request.code, error)
            return
        if event == "rejected":
            error = getattr(receipt, "error_message", "") or "Cell request rejected"
            self._transition(
                WorkflowEvent.CELL_REJECTED,
                message=error,
                **progress,
            )
            send_to_panel(self.ns, "text", content=f"✗ {error}\n")
            return
        if event == "timed_out":
            self._transition(
                WorkflowEvent.CELL_TIMED_OUT,
                message="Cell execution timed out",
                **progress,
            )
            send_to_panel(self.ns, "text", content="✗ Cell execution timed out\n")
            return
        if event == "cancelled" and self._state in {
            WorkflowState.CELL_DISPATCHING,
            WorkflowState.CELL_EXECUTING,
        }:
            self._transition(WorkflowEvent.CELL_CANCELLED, **progress)
            return
        if event == "batch_failed" and self._pending_auto_fix:
            code, error = self._pending_auto_fix
            self._pending_auto_fix = None
            self._auto_fix_cell(code, error)

    def _interrupt_cleanup(self, msg: str = "\n⏏ interrupted\n") -> None:
        """Unified KeyboardInterrupt handler — replaces 5 duplicated copies."""
        self._session_dirty = True
        self._auto_fix_count = 0
        self._pending_result = None
        self._round_results.clear()
        if self._state is not WorkflowState.INTERRUPTING:
            self._transition(WorkflowEvent.STOP_REQUESTED)
        self._execution.cancel_active("interrupt")
        self._transition(WorkflowEvent.INTERRUPT_COMPLETED, trigger="interrupt")
        send_to_panel(self.ns, "text", content=msg)
        send_to_panel(self.ns, "result", summary="")

    def _stream_with_interrupt(self, prompt: str) -> tuple[str, bool]:
        """Stream agent response. Returns (raw_text, was_interrupted)."""
        if self._session_dirty:
            self._session_dirty = False
            prompt = _INTERRUPT_NOTE + "\n\n" + prompt
        rec = get_recorder()
        t0 = time.time()
        thinking_chars = 0
        tool_names: set[str] = set()

        def _emit_text(t):
            send_to_panel(self.ns, "text", content=t)

        text_stream = _PanelTextStream(_emit_text)
        steer_target = None
        prepare_run = getattr(self._session, "prepare_run", None)
        if callable(prepare_run):
            try:
                steer_target = prepare_run()
                if steer_target:
                    send_to_panel(self.ns, "steer_target", **steer_target)
            except Exception:
                _log.warning("failed to prepare steering channel", exc_info=True)

        def _on_chunk(t):
            text_stream.feed(t)

        def _on_steer(receipt):
            send_to_panel(self.ns, "steer_receipt", **receipt)

        def _close_steering():
            if steer_target:
                send_to_panel(
                    self.ns,
                    "steer_closed",
                    run_id=steer_target.get("run_id", ""),
                )

        _think_buf = ""
        _think_last = 0.0

        def _on_thinking(t):
            nonlocal thinking_chars, _think_buf, _think_last
            thinking_chars += len(t)
            _think_buf += t
            now = time.time()
            if now - _think_last >= 0.2:
                send_thinking(_think_buf)
                _think_buf = ""
                _think_last = now

        try:
            raw = self._session.stream(prompt, show_text=False,
                on_chunk=_on_chunk,
                on_thinking=_on_thinking,
                execution_mode=self._permission_mode.value,
                on_steer=_on_steer)
            _close_steering()
            if _think_buf:
                send_thinking(_think_buf)
            text_stream.finish()
            send_to_panel(self.ns, "text", content="\n")
            elapsed_ms = int((time.time() - t0) * 1000)
            if rec:
                code_blocks = raw.count("```") // 2 if raw.strip() else 0
                rec.record("agent_response",
                    mode=getattr(self, '_last_mode', 'default'),
                    raw_text=raw.strip(),
                    code_blocks=code_blocks,
                    tool_names=sorted(tool_names),
                    thinking_chars=thinking_chars,
                    elapsed_ms=elapsed_ms,
                    interrupted=False,
                )
            return raw, False
        except KeyboardInterrupt:
            _close_steering()
            if _think_buf:
                send_thinking(_think_buf)
            elapsed_ms = int((time.time() - t0) * 1000)
            if rec:
                rec.record("agent_response",
                    elapsed_ms=elapsed_ms,
                    thinking_chars=thinking_chars,
                    tool_names=sorted(tool_names),
                    interrupted=True,
                )
            self._interrupt_cleanup()
            return "", True
        except Exception as exc:
            _close_steering()
            _log.exception("Agent request failed")
            if rec:
                rec.record(
                    "agent_response",
                    elapsed_ms=int((time.time() - t0) * 1000),
                    thinking_chars=thinking_chars,
                    tool_names=sorted(tool_names),
                    interrupted=True,
                    error=str(exc)[:200],
                )
            send_to_panel(self.ns, "text", content=f"Agent request failed: {exc}\n")
            send_to_panel(self.ns, "result", summary="")
            self._transition(WorkflowEvent.INTERNAL_ERROR, trigger="agent_request_failed")
            return "", True

    def _finish_agent_run(self, msg: str = "") -> None:
        """Clean up after agent run completes. Sends result + ready to frontend."""
        if self._state == AgentState.IDLE:
            return  # already finished, prevent duplicate ready/result
        self._pending_result = None
        self._round_results.clear()
        self._agent_cells.clear()
        if msg:
            send_to_panel(self.ns, "text", content=f"{msg}\n")
        send_to_panel(self.ns, "result", summary="")
        self._transition(WorkflowEvent.RUN_FINISHED, trigger="agent_done")

    def _record_state(self, trigger: str) -> None:
        """Record workflow state transition for telemetry."""
        rec = get_recorder()
        if rec:
            rec.record("workflow_state",
                state=self._state.name,
                trigger=trigger,
            )

    def _track_agent_cell(self, cid: str, code_str: str) -> None:
        """Callback: track agent-generated cell IDs for batch completion detection."""
        if cid:
            self._agent_cells[cid] = "pending"

    def _ask_confirm(self, msg: str, pending_result=None) -> None:
        """Ask permission to materialize and execute pending code cells."""
        if pending_result is None or not pending_result.code_list:
            raise ValueError("code confirmation requires pending code")
        self._transition(WorkflowEvent.AGENT_RETURNED_CODE, trigger="confirm_shown")
        self._pending_result = pending_result
        send_to_panel(self.ns, "result", summary="")
        send_to_panel(self.ns, "text",
            content=f"\n{'─'*40}\n{msg}\nType /continue yes or /continue no\n{'─'*40}\n")
        # continue_confirm implies ready (frontend stops spinner + dequeues) — sending
        # both would dequeue TWO queued prompts for a single confirmation slot
        send_to_panel(self.ns, "continue_confirm", summary=msg)

    def _handle_continue(self, arg: str) -> None:
        """Handle /continue yes|no from panel."""
        arg = arg.strip()
        if arg not in {"yes", "no"}:
            send_to_panel(self.ns, "text", content="Usage: /continue yes|no\n")
            return
        if self._state is not WorkflowState.WAITING_CONFIRM:
            send_to_panel(self.ns, "text", content="No pending continuation.\n")
            return
        rec = get_recorder()
        if rec:
            rec.record("agent_continue", choice="yes" if arg == "yes" else "no")
        if arg != "yes":
            self._transition(
                WorkflowEvent.USER_REJECTED,
                trigger="user_stop",
                message="Task stopped",
            )
            send_to_panel(self.ns, "text", content="Task stopped\n")
            send_to_panel(self.ns, "result", summary="")
            return

        pending = self._pending_result
        self._pending_result = None
        if pending is not None and pending.code_list:
            # Has code cells: inject + auto-execute
            self._permission_mode = ExecutionMode.EXECUTE
            self._agent_cells.clear()
            self._auto_fix_count = 0
            self._submit_code_cells(pending.code_list, auto=True)
            return

        # WAITING_CONFIRM is code-only. Fail closed if stale state leaks through.
        self._permission_mode = ExecutionMode.DEFAULT
        self._finish_agent_run()

    def _handle_panel_stop(self) -> None:
        """Handle /stop — exit current task immediately."""
        if self._state == AgentState.IDLE:
            send_to_panel(self.ns, "text", content="No active task.\n")
            return
        self._transition(WorkflowEvent.STOP_REQUESTED, trigger="user_stop")
        self._execution.cancel_active("user stop")
        try:
            self._session.interrupt()
        except Exception:
            pass
        send_to_panel(self.ns, "text", content="Task stopped\n")
        send_to_panel(self.ns, "result", summary="")
        self._transition(WorkflowEvent.INTERRUPT_COMPLETED, trigger="user_stop")

    @staticmethod
    def _load_dotenv() -> None:
        """Load conf/.env into os.environ (only vars not already set)."""
        from pathlib import Path
        # Use absolute path — kernel cwd may not be project root
        env_file = Path(__file__).resolve().parents[2] / "conf" / ".env"
        if not env_file.is_file():
            return
        try:
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, val = line.partition("=")
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if key and key not in _os.environ:
                        _os.environ[key] = val
        except Exception:
            print(f"[agent_config] failed to read {env_file}", file=sys.stderr)

    def _load_jupyter_config(self) -> str:
        """Load config from JUPYTER_CONFIG_PATH env var and apply it.
        Returns status message (includes tool discovery output)."""
        from io import StringIO
        from pathlib import Path
        config_path = _os.environ.get("JUPYTER_CONFIG_PATH", "")
        if not config_path:
            return "[agent_config] JUPYTER_CONFIG_PATH not set, no config loaded\n"
        if not Path(config_path).is_file():
            return f"[agent_config] config file not found: {config_path}\n"
        self._jupyter_config_path = config_path

        # Capture stdout during configure_agent (tool discovery prints here)
        capture = StringIO()
        old_stdout = sys.stdout
        sys.stdout = capture
        try:
            resolved = configure_agent(
                config_path=config_path,
                cli_agent=None, cli_timeout=None,
                cli_claude_md=None, cli_debug=None,
                cli_env={},
                enable_hooks=[], disable_hooks=[],
                defaults={},
                current_agent=self._agent,
                current_timeout=self._timeout,
                current_claude_md=self._claude_md_path,
                current_hook_cfg=self._hook_cfg,
            )
        finally:
            sys.stdout = old_stdout

        tool_output = capture.getvalue().strip()
        if resolved:
            self._apply_config(resolved)
            lines = [f"[agent_config] loaded: {config_path}  agent={self._agent} timeout={self._timeout}s"]
            if tool_output:
                lines.append(tool_output)
            return "\n".join(lines) + "\n"
        else:
            return f"[agent_config] failed to load: {config_path}\n"

    def _ensure_session(self) -> None:
        """Lazy-init agent session on first query (keeps kernel startup fast)."""
        if self._session_ready:
            return
        # Drop stale client from interrupted session (avoid lingering TCP connections)
        old = getattr(self, '_session', None)
        if old is not None:
            old.cleanup()
        self._init_session(self._agent, self._timeout, self._claude_md_path)
        if self._session.client is None:
            raise RuntimeError(f"session init failed — is agent {self._agent} running?")
        from pathlib import Path as _Path
        _project_root = _Path(__file__).resolve().parents[2]
        rec = SessionEventRecorder(
            session_id=self._session.session_id,
            path=str(_project_root / ".run" / "sessions" / f"{self._session.session_id}.jsonl"),
        )
        set_recorder(rec)
        # Register atexit flush so session data is written on kernel shutdown
        rec_ref = rec
        import atexit as _atexit
        @_atexit.register
        def _flush_telemetry():
            rec_ref.flush()
        self._session_ready = True

    def _init_session(self, agent: str, timeout: int, claude_md: str | None = None) -> None:
        if agent != "claude-code":
            raise RuntimeError("Notebook execution permissions currently require claude-code")
        self._session = AgentSession(agent, timeout)
        self._session.configure_subs(SUB_AGENT_DEFAULTS)
        self._session.init_session(
            system_prompt=_merge_prompt(claude_md),
            session_key=_session_key(),
            on_init=lambda s: _register_hooks(timeout, self._hook_cfg),
        )

    def _handle_notebook_switch(self, nb_path: str) -> None:
        """Active notebook changed — start a fresh agent conversation for it.

        Resets the LLM session so the new notebook doesn't inherit the previous
        one's conversation history. Kernel variables are shared and stay put.

        Guards against spurious ``currentChanged`` events (tab focus, layout
        restore) by only resetting when the notebook path actually differs from
        the one the current session is bound to, and never mid-task.
        """
        if self._state != AgentState.IDLE:
            _log.info("notebook switch deferred — agent busy (state=%s)", self._state)
            self._pending_session_nb_path = nb_path
            return
        self._switch_notebook_session(nb_path)

    def _apply_pending_notebook_switch(self) -> None:
        """Apply the latest notebook switch queued while an agent task was active."""
        pending = getattr(self, "_pending_session_nb_path", None)
        if not pending:
            return
        self._pending_session_nb_path = None
        self._switch_notebook_session(pending)

    def _switch_notebook_session(self, nb_path: str) -> None:
        """Bind the backend session to *nb_path* while the agent is idle."""
        prev = getattr(self, "_session_nb_path", None)
        if prev == nb_path:
            return
        self._session_nb_path = nb_path
        # First bind, or session never started → nothing to reset yet.
        if prev is None or not self._session_ready:
            return
        _log.info("notebook switch → resetting agent conversation (path=%s)", nb_path)
        old = getattr(self, "_session", None)
        if old is not None:
            old.cleanup()
        self._session_ready = False  # lazy re-init on next query
        self._session_dirty = False
        send_to_panel(
            self.ns, "text",
            content="⟳ new notebook — fresh agent conversation "
                    "(kernel variables are shared across notebooks)\n",
        )

    def _on_cell_start(self, info) -> None:
        """Record the start time for cell execution telemetry."""
        self._cell_start_ts = time.time()

    def _on_cell_run(self, result):
        info = getattr(result, "info", None)
        if info is None:
            return
        # Skip executions that aren't real notebook cells (frontend queries, etc.)
        if not getattr(info, "store_history", True):
            return
        code = getattr(info, "raw_cell", "")
        if not code:
            return

        is_agent_cell = "# %%agent generate code" in code
        cell_id = getattr(info, "cell_id", "")
        output = str(info.result) if getattr(info, "result", None) else ""

        # Track cell in namespace (do this before any early return — bug 10 fix)
        error_str = ""
        if not result.success:
            e = result.error_in_exec or result.error_before_exec
            if e:
                error_str = str(e)[:2000]
        self.ns.track_cell(code.strip(), output.strip(), cell_id=cell_id)

        # ---- agent cell tracking ----
        if is_agent_cell:
            self._round_results.append({
                "cell_id": cell_id, "code": code.strip(), "output": output.strip()
            })

        # ---- snapshot logic ----
        now = time.time()
        self._restoring_cells = {c: t for c, t in self._restoring_cells.items() if now - t < 300}
        restoring = cell_id in self._restoring_cells
        if cell_id and code.strip() and not restoring:
            from .cell_snapshot import save as save_cell_snapshot
            save_cell_snapshot(cell_id, code.strip(), output.strip(), error_str, nb_path=_notebook_path())
        if code.strip():
            if restoring:
                self._restoring_cells.pop(cell_id, None)
            else:
                from .notebook_snapshot import take as take_snapshot
                take_snapshot(self.ns._cells, nb_path=_notebook_path())

        # ---- telemetry ----
        rec = get_recorder()
        if rec:
            cell_type = "plain"
            if code.startswith("%%sql"):
                cell_type = "%%sql"
            error = getattr(result, "error_in_exec", None) or getattr(result, "error_before_exec", None)
            elapsed_ms = int((time.time() - self._cell_start_ts) * 1000) if self._cell_start_ts else 0
            self._cell_start_ts = 0.0
            rec.record("cell_executed",
                cell_id=cell_id,
                type=cell_type,
                code=code.strip(),
                output=output.strip(),
                error=str(error) if error else None,
                elapsed_ms=elapsed_ms,
                is_agent_cell=is_agent_cell,
                exec_order=rec.next_exec_order(),
            )

    # ---- panel handler ----

    def _on_panel_input(
        self,
        text: str,
        mode: str = "default",
        cell_references: str = "",
    ) -> None:
        """Handle input from right-side panel."""
        # Flush startup config message on first interaction
        msg = getattr(self, '_startup_config_msg', '')
        if msg and send_to_panel(self.ns, "text", content=msg):
            self._startup_config_msg = ""
        text = text.strip()
        if text == "/confirm" or text.startswith("/confirm "):
            self._handle_panel_confirm(text[8:].strip())
        elif text == "/clear":
            if self._state is not WorkflowState.IDLE:
                self._handle_panel_stop()
            send_to_panel(self.ns, "clear")
        elif text.startswith("/mode "):
            self._handle_panel_mode(text[6:].strip())
        elif text.startswith("/skills"):
            self._handle_panel_skills(text)
        elif text.startswith("/config"):
            self._handle_panel_config(text)
        elif text == "/snapshot":
            from .notebook_snapshot import take as take_snapshot
            path = take_snapshot(self.ns._cells, nb_path=_notebook_path())
            if path:
                send_to_panel(self.ns, "text", content=f"✓ Snapshot saved: {path.stem}\n")
            else:
                send_to_panel(self.ns, "text", content="✗ No cells to snapshot.\n")
        elif text.startswith("/continue"):
            self._handle_continue(text[10:].strip())
        elif text == "/stop":
            self._handle_panel_stop()
        elif text.startswith("/cell-optimize"):
            self._handle_cell_optimize(text)
        elif text.startswith("/cell-snapshot-restore"):
            self._handle_cell_restore(text)
        else:
            self._handle_panel_prompt(
                text,
                mode,
                parse_cell_references(cell_references),
            )

    def _handle_panel_prompt(
        self,
        prompt: str,
        mode: str = "default",
        cell_references: list[dict[str, str]] | None = None,
    ) -> None:
        """Execute agent prompt from panel: stream to panel + inject cells to left."""
        if self._state != AgentState.IDLE:
            send_to_panel(self.ns, "text", content="⏳ agent is working, please wait...\n")
            send_to_panel(self.ns, "result", summary="")
            return

        if mode not in {"default", "plan", "auto"}:
            send_to_panel(self.ns, "text", content="Execution blocked: invalid mode\n")
            return
        self._permission_mode = ExecutionMode(mode)
        self._workflow_notebook_path = _notebook_path()
        self._transition(
            WorkflowEvent.USER_PROMPT_ACCEPTED,
            trigger="user_prompt",
        )

        # Session init
        try:
            self._ensure_session()
        except KeyboardInterrupt:
            self._interrupt_cleanup()
            return
        except Exception:
            _log.exception("_handle_panel_prompt: session init failed")
            send_to_panel(self.ns, "text", content="✗ session initialization failed, check server logs\n")
            send_to_panel(self.ns, "result", summary="")
            self._transition(
                WorkflowEvent.INTERNAL_ERROR,
                trigger="session_init_failed",
            )
            return

        # Build prompt with incremental context and explicit @Cell snapshots.
        ctx = self.ns.delta()
        references = cell_references or []
        ref_ctx = format_cell_references(references)
        self._referenced_replace_cell_id = referenced_edit_target(
            prompt,
            references,
        )
        sections = [section for section in (ctx, ref_ctx, prompt) if section]
        full = "\n\n".join(sections)
        if self._referenced_replace_cell_id:
            full += (
                "\n\n[System: The user explicitly asked to modify the sole "
                "referenced Cell. Return the complete replacement Cell code "
                "as the first fenced code block. Do not edit unrelated Cells.]"
            )

        if mode == "plan":
            self._last_plan_prompt = prompt
            # Hard plan constraint (SECTIONS["plan"]): forces the model to emit a
            # non-empty "plan" field and an empty "code" array this turn, and to
            # NOT run any tools — so the user reliably gets a plan first instead of
            # the model jumping straight to exploration/code.
            plan_prefix = "[System: " + SECTIONS["plan"] + "]\n\n"
            full = plan_prefix + full

        # Stream
        rec = get_recorder()
        if rec:
            rec.record("agent_prompt",
                mode=mode,
                prompt=prompt,
                context_preview=ctx[:500] if ctx else "",
            )
        raw, interrupted = self._stream_with_interrupt(full)
        if interrupted:
            return
        if not raw.strip():
            self._finish_agent_run()
            return

        # Process result
        result = parse(raw)
        if mode == "plan":
            self._last_plan_output = raw.strip()
            self._last_plan_result = result  # cache parsed result to avoid re-parse in _implement_plan
            plan_text = result.plan or result.text or ""
            self._emit_plan_cell(plan_text)
            send_to_panel(self.ns, "plan_confirm", summary=plan_text)
            self._transition(
                WorkflowEvent.AGENT_RETURNED_PLAN,
                trigger="plan_ready",
            )
        elif mode == "auto":
            _log.info("auto mode: %d code blocks", len(result.code_list))
            self._agent_cells.clear()
            self._auto_fix_count = 0
            sent = render_output(
                self.ns,
                result,
                auto=True,
                cell_submitter=self._submit_code_cells,
                session=self._session,
            )
            if not sent:
                self._finish_agent_run()
        else:
            if result.code_list:
                self._ask_confirm(f"Generate and execute {len(result.code_list)} cells?", pending_result=result)
            else:
                self._finish_agent_run()

    def _handle_panel_mode(self, mode: str) -> None:
        """Handle /mode from panel — mode is tracked by frontend, nothing to persist."""

    def _handle_panel_skills(self, text: str) -> None:
        """Handle /skills commands from panel."""
        parts = text.split()
        if len(parts) < 2:
            cmd = "list"  # /skills alone defaults to list
        else:
            cmd = parts[1]
        session = getattr(self, '_session', None)
        mgr = None
        if session and session.client:
            mgr = session.client.skills
        else:
            # Session not yet initialized — use SkillManager directly.
            # Resolve the dir for the CONFIGURED agent (not a hardcoded one),
            # otherwise the panel shows another agent's (often empty) skills.
            try:
                from chat.skill import SkillManager
                from chat import _resolve_skill_dir
                mgr = SkillManager(_resolve_skill_dir(self._agent))
            except Exception as e:
                _log.warning("_handle_panel_skills: fallback SkillManager failed: %s", e)

        if cmd == "list":
            if not mgr:
                send_to_panel(self.ns, "text", content="✗ session not initialized\n")
                return
            skills = mgr.list_skills()
            from .panel import send_skill_list
            if not skills:
                send_skill_list([])  # show empty state in panel
                return
            send_skill_list([
                {"name": s.name, "description": s.description, "enabled": s.enabled, "body": s.body[:1000]}
                for s in skills
            ])

        elif cmd == "info":
            name = parts[2] if len(parts) > 2 else ""
            if not name:
                send_to_panel(self.ns, "text", content="Usage: /skills info <name>\n")
                return
            if not mgr:
                send_to_panel(self.ns, "text", content="✗ session not initialized\n")
                return
            s = mgr.get_skill(name)
            if not s:
                send_to_panel(self.ns, "text", content=f"✗ skill not found: {name}\n")
                return
            from .panel import send_skill_info
            send_skill_info({
                "name": s.name,
                "description": s.description,
                "enabled": s.enabled,
                "body": s.body[:2000],
                "path": s.path,
            })

        elif cmd == "enable":
            name = parts[2] if len(parts) > 2 else ""
            if not name:
                send_to_panel(self.ns, "text", content="Usage: /skills enable <name>\n")
                return
            if not mgr:
                send_to_panel(self.ns, "text", content="✗ session not initialized\n")
                return
            try:
                mgr.enable(name)
                send_to_panel(self.ns, "text",
                              content=f"✓ {name} enabled — restart agent server to apply\n")
            except FileNotFoundError:
                send_to_panel(self.ns, "text", content=f"✗ skill not found: {name}\n")

        elif cmd == "disable":
            name = parts[2] if len(parts) > 2 else ""
            if not name:
                send_to_panel(self.ns, "text", content="Usage: /skills disable <name>\n")
                return
            if not mgr:
                send_to_panel(self.ns, "text", content="✗ session not initialized\n")
                return
            try:
                mgr.disable(name)
                send_to_panel(self.ns, "text",
                              content=f"✓ {name} disabled — restart agent server to apply\n")
            except FileNotFoundError:
                send_to_panel(self.ns, "text", content=f"✗ skill not found: {name}\n")

        elif cmd == "toggle":
            name = parts[2] if len(parts) > 2 else ""
            if not name:
                send_to_panel(self.ns, "text", content="Usage: /skills toggle <name>\n")
                return
            if not mgr:
                send_to_panel(self.ns, "text", content="✗ session not initialized\n")
                return
            try:
                s = mgr.get_skill(name)
                if not s:
                    send_to_panel(self.ns, "text", content=f"✗ skill not found: {name}\n")
                    return
                if s.enabled:
                    mgr.disable(name)
                else:
                    mgr.enable(name)
                # Send updated skill list (text toggle confirmation is redundant with list UI)
                from .panel import send_skill_list
                updated = mgr.list_skills()
                send_skill_list([
                    {"name": si.name, "description": si.description, "enabled": si.enabled, "body": si.body[:1000]}
                    for si in updated
                ])
            except FileNotFoundError:
                send_to_panel(self.ns, "text", content=f"✗ skill not found: {name}\n")

        elif cmd == "install":
            path = parts[2] if len(parts) > 2 else ""
            if not path:
                send_to_panel(self.ns, "text", content="Usage: /skills install <path/to/skill.zip>\n")
                return
            if not mgr:
                send_to_panel(self.ns, "text", content="✗ session not initialized\n")
                return
            from pathlib import Path
            zpath = Path(path)
            if not zpath.is_absolute():
                import os
                zpath = Path(os.getcwd()) / zpath
            try:
                info = mgr.install(str(zpath))
                send_to_panel(self.ns, "text",
                              content=f"✓ {info.name} installed (enabled)\n")
                # Refresh skill list
                from .panel import send_skill_list
                updated = mgr.list_skills()
                send_skill_list([
                    {"name": s.name, "description": s.description, "enabled": s.enabled, "body": s.body[:1000]}
                    for s in updated
                ])
            except FileNotFoundError:
                send_to_panel(self.ns, "text", content=f"✗ file not found: {path}\n")
            except ValueError as e:
                send_to_panel(self.ns, "text", content=f"✗ {e}\n")

        elif cmd == "uninstall":
            name = parts[2] if len(parts) > 2 else ""
            if not name:
                send_to_panel(self.ns, "text", content="Usage: /skills uninstall <name>\n")
                return
            if not mgr:
                send_to_panel(self.ns, "text", content="✗ session not initialized\n")
                return
            try:
                mgr.uninstall(name)
                send_to_panel(self.ns, "text", content=f"✓ {name} uninstalled\n")
                # Refresh skill list
                from .panel import send_skill_list
                updated = mgr.list_skills()
                send_skill_list([
                    {"name": s.name, "description": s.description, "enabled": s.enabled, "body": s.body[:1000]}
                    for s in updated
                ])
            except FileNotFoundError:
                send_to_panel(self.ns, "text", content=f"✗ skill not found: {name}\n")

        else:
            send_to_panel(self.ns, "text",
                          content=f"Unknown command: /skills {cmd}\n"
                                  "Usage: /skills list|info|enable|disable|install|uninstall\n")

    def _handle_panel_config(self, text: str) -> None:
        """Handle /config commands from panel."""
        parts = text.split(maxsplit=1)
        path = parts[1].strip() if len(parts) > 1 else ""

        # Confirmation: /config --yes or /config --no
        if path == "--yes":
            pending = getattr(self, '_config_pending', None)
            if pending:
                resolved, new_path, _old_path = pending
                _os.environ["JUPYTER_CONFIG_PATH"] = new_path
                self._jupyter_config_path = new_path
                summary = self._apply_config(resolved)
                send_to_panel(self.ns, "text", content=(
                    f"\n{'─'*50}\n✓ Config applied\n"
                    f"  path    : {new_path}\n"
                    f"  agent   : {self._agent}\n"
                    f"  timeout : {self._timeout}s\n"
                    f"  changes : {summary}\n"
                    f"{'─'*50}\n"))
                self._config_pending = None
            else:
                send_to_panel(self.ns, "text", content="No pending config change.\n")
            return
        if path == "--no":
            pending = getattr(self, '_config_pending', None)
            if pending:
                _resolved, _new_path, old_path = pending
                self._jupyter_config_path = old_path
                send_to_panel(self.ns, "text", content="✗ Config change cancelled.\n")
                self._config_pending = None
            else:
                send_to_panel(self.ns, "text", content="No pending config change.\n")
            return

        if path:
            from pathlib import Path
            if not Path(path).is_file():
                send_to_panel(self.ns, "text", content=f"✗ File not found: {path}\n")
                return

            resolved = configure_agent(
                config_path=path,
                cli_agent=None, cli_timeout=None,
                cli_claude_md=None, cli_debug=None,
                cli_env={},
                enable_hooks=[], disable_hooks=[],
                defaults={},
                current_agent=self._agent,
                current_timeout=self._timeout,
                current_claude_md=self._claude_md_path,
                current_hook_cfg=self._hook_cfg,
            )

            # First load: apply directly. Subsequent: confirm.
            old_path = self._jupyter_config_path
            if not old_path:
                _os.environ["JUPYTER_CONFIG_PATH"] = path
                self._jupyter_config_path = path
                summary = self._apply_config(resolved)
                send_to_panel(self.ns, "text", content=(
                    f"\n{'─'*50}\n✓ Config loaded\n"
                    f"  path    : {path}\n"
                    f"  agent   : {self._agent}\n"
                    f"  timeout : {self._timeout}s\n"
                    f"  changes : {summary}\n"
                    f"{'─'*50}\n"))
            else:
                self._config_pending = (resolved, path, old_path)
                new_agent = resolved.get('agent', self._agent)
                new_timeout = resolved.get('timeout', self._timeout)
                send_to_panel(self.ns, "text", content=(
                    f"\n{'─'*50}\n"
                    f"  Current\n"
                    f"    path    : {old_path}\n"
                    f"    agent   : {self._agent}\n"
                    f"    timeout : {self._timeout}s\n"
                    f"  ──────────────────────────────\n"
                    f"  New\n"
                    f"    path    : {path}\n"
                    f"    agent   : {new_agent}\n"
                    f"    timeout : {new_timeout}s\n"
                    f"{'─'*50}\n"
                    f"Press y to apply  n to cancel  Esc to dismiss\n"))
        else:
            pending = getattr(self, '_config_pending', None)
            if pending:
                _res, new_p, old_p = pending
                send_to_panel(self.ns, "text", content=(
                    f"\n{'─'*40}\n"
                    f"  Config Status\n"
                    f"  {'─'*40}\n"
                    f"  path    : {old_p}\n"
                    f"  agent   : {self._agent}\n"
                    f"  timeout : {self._timeout}s\n"
                    f"  claude-md: {self._claude_md_path or '(none)'}\n"
                    f"  {'─'*40}\n"
                    f"  Pending : {new_p}\n"
                    f"  Press y to apply  n to cancel\n"
                    f"{'─'*40}\n"))
            elif self._jupyter_config_path:
                send_to_panel(self.ns, "text", content=(
                    f"\n{'─'*40}\n"
                    f"  Config Status\n"
                    f"  {'─'*40}\n"
                    f"  path    : {self._jupyter_config_path}\n"
                    f"  agent   : {self._agent}\n"
                    f"  timeout : {self._timeout}s\n"
                    f"  claude-md: {self._claude_md_path or '(none)'}\n"
                    f"  {'─'*40}\n"))
            else:
                send_to_panel(self.ns, "text",
                              content="No config loaded. Usage: /config <path/to/config.yaml>\n")

    def _handle_cell_restore(self, text: str) -> None:
        """Handle /cell-snapshot-restore <cell_id> <version> — restore a cell snapshot."""
        if self._state is not WorkflowState.IDLE:
            send_to_panel(self.ns, "text", content="Wait for the active task before restoring a Cell.\n")
            return
        from .cell_snapshot import restore
        parts = text.split()
        if len(parts) < 3:
            send_to_panel(self.ns, "text", content="Usage: /cell-snapshot-restore <cell_id> <version>\n")
            return
        cell_id = parts[1]
        version = parts[2]
        code = restore(cell_id, version, nb_path=_notebook_path())
        if code is None:
            send_to_panel(self.ns, "text", content=f"Version {version} not found.\n")
            return
        self._restoring_cells[cell_id] = time.time()
        from .comm import send_cell_via_comm
        self._permission_mode = ExecutionMode.EDIT
        try:
            request_id = send_cell_via_comm(
                self.ns, code, auto=False, cell_type="code", replace_cell_id=cell_id,
            )
        finally:
            self._permission_mode = ExecutionMode.DEFAULT
        if not request_id:
            self._restoring_cells.pop(cell_id, None)
            send_to_panel(self.ns, "text", content="Cell restore was not dispatched.\n")
            return
        self._cell_restored = True
        print("Cell restored to " + version, flush=True)

    def _handle_cell_optimize(self, text: str) -> None:
        """Handle /cell-optimize <json_payload> — agent improves a specific cell."""
        if self._state != AgentState.IDLE:
            send_to_panel(self.ns, "text", content="⏳ agent is working, please wait...\n")
            return

        import json
        try:
            payload = json.loads(text[15:].strip())
        except json.JSONDecodeError:
            send_to_panel(self.ns, "text", content="✗ invalid payload\n")
            return

        cell_id = payload.get("cellId", "")
        code = (payload.get("code") or "").strip()
        output = (payload.get("output") or "").strip()
        error_msg = (payload.get("error") or "").strip()
        request = (payload.get("request") or "improve this code").strip()
        auto_exec = payload.get("auto", False)
        if not code:
            send_to_panel(self.ns, "text", content="✗ cell is empty\n")
            return

        # Truncate large cells to avoid blowing up the context window
        code_for_prompt = code[:5000]
        output_for_prompt = output[:2000]
        if len(code) > 5000:
            code_for_prompt += f"\n# ... ({len(code) - 5000} more chars)"

        is_sql = code.startswith("%%sql")
        lang = "SQL" if is_sql else "Python"
        prompt = (
            f"## Current {lang} Cell\n```{lang.lower()}\n{code_for_prompt}\n```\n\n"
            f"## Output\n```\n{output_for_prompt or '(none)'}\n```"
        )
        if error_msg:
            prompt += f"\n## Error\n```\n{error_msg[:2000]}\n```\n"
        prompt += (
            f"\n## Request\n{request}\n\n"
            f"Return ONLY the improved {lang} code in a fenced code block. "
            f"Do NOT add explanations."
        )

        try:
            self._ensure_session()
        except KeyboardInterrupt:
            self._interrupt_cleanup()
            return
        except Exception:
            _log.exception("_handle_cell_optimize: session init failed")
            send_to_panel(self.ns, "text", content="✗ session init failed\n")
            return

        send_to_panel(self.ns, "text", content=f"↻ optimizing {lang} cell...\n")
        self._permission_mode = ExecutionMode.EXECUTE if auto_exec else ExecutionMode.EDIT
        self._workflow_notebook_path = _notebook_path()
        self._transition(
            WorkflowEvent.USER_PROMPT_ACCEPTED,
            trigger="cell_optimize",
        )
        raw, interrupted = self._stream_with_interrupt(prompt)
        if interrupted:
            return
        if not raw.strip():
            self._finish_agent_run("Optimization failed (no output)")
            return

        result = parse(raw)
        if result.code_list:
            # Take the last code block (agent might preface with explanation)
            optimized = result.code_list[-1]
            self._submit_code_cells(
                [optimized],
                auto=auto_exec,
                replace_cell_id=cell_id,
            )
            self.ns.remove_cell_by_id(cell_id)
            self.ns.track_context(
                f"[cell {cell_id[:8]}] optimized ({lang}): {request}\n"
                f"  old: {code[:100]}{'...' if len(code) > 100 else ''}\n"
                f"  new: {optimized[:100]}{'...' if len(optimized) > 100 else ''}")
            action = "optimized & run" if auto_exec else "optimized"
            send_to_panel(self.ns, "text", content=f"✓ {lang} cell {action}\n")
        else:
            send_to_panel(self.ns, "text", content="✗ no code in agent response\n")
            self._finish_agent_run()

    def _handle_panel_confirm(self, arg: str) -> None:
        """Handle /confirm from panel."""
        if self._state is not WorkflowState.PLAN_REVIEW:
            send_to_panel(self.ns, "text", content="No pending plan confirmation.\n")
            return
        arg = arg.strip()
        if not arg:
            return
        if arg == "yes":
            if self._last_plan_result is not None:
                self._permission_mode = ExecutionMode.EXECUTE
                self._implement_plan(self._last_plan_output or "", auto=True,
                                     preparsed_result=self._last_plan_result)
                self._record_state("plan_confirm")
            self._last_plan_output = ""
            self._last_plan_result = None
            self._plan_cell_id = ""  # keep confirmed plan cell in notebook; next plan starts fresh
        elif arg == "accept_edits":
            if self._last_plan_result is not None:
                self._permission_mode = ExecutionMode.EDIT
                self._implement_plan(self._last_plan_output or "", auto=False,
                                     preparsed_result=self._last_plan_result)
                self._record_state("plan_confirm")
            self._last_plan_output = ""
            self._last_plan_result = None
            self._plan_cell_id = ""  # keep confirmed plan cell in notebook; next plan starts fresh
        elif arg == "no":
            self._last_plan_output = ""
            self._last_plan_result = None
            self._plan_cell_id = ""
            send_to_panel(self.ns, "text", content="Plan cancelled\n")
            send_to_panel(self.ns, "result", summary="")
            self._transition(
                WorkflowEvent.USER_REJECTED,
                trigger="plan_cancelled",
            )
        else:
            # Revision feedback
            self._permission_mode = ExecutionMode.PLAN
            send_to_panel(self.ns, "text", content=f"↻ revising plan: {arg}\n")
            plan = self._last_plan_output or ""
            prompt = self._last_plan_prompt or ""
            if plan and prompt:
                full = (
                    "[System: " + SECTIONS["plan"] + "]\n\n"
                    f"User feedback on the plan: {arg}\n\nOriginal request:\n{prompt}\n\n"
                    f"Previous plan:\n{plan}\n\nRevise the plan based on the feedback."
                )
                self._transition(
                    WorkflowEvent.PLAN_REVISION_REQUESTED,
                    trigger="plan_revision",
                )
                raw, interrupted = self._stream_with_interrupt(full)
                if interrupted:
                    return
                if raw.strip():
                    self._last_plan_output = raw.strip()
                    result = parse(raw)
                    self._last_plan_result = result  # refresh cache so confirm implements the revised plan
                    plan_text = result.plan or result.text or ""
                    self._emit_plan_cell(plan_text)
                    self._transition(
                        WorkflowEvent.AGENT_RETURNED_PLAN,
                        trigger="plan_revised",
                    )
                    send_to_panel(self.ns, "plan_confirm", summary=plan_text)
                else:
                    send_to_panel(self.ns, "text", content="✗ plan revision failed (no output) — previous plan kept\n")
                    send_to_panel(self.ns, "result", summary="")
                    self._transition(
                        WorkflowEvent.AGENT_RETURNED_PLAN,
                        trigger="plan_revision_empty",
                    )
                    send_to_panel(self.ns, "plan_confirm", summary=plan)
            else:
                send_to_panel(self.ns, "text", content="✗ no plan to revise\n")
                send_to_panel(self.ns, "result", summary="")

    def _auto_fix_cell(self, code: str, error_msg: str) -> None:
        """Auto mode: cell execution failed → ask AI to fix and replace in-place."""
        if self._state is not AgentState.AUTO_FIXING:
            _log.warning("auto-fix ignored outside AUTO_FIXING")
            return
        self._auto_fix_cell_impl(code, error_msg)

    def _auto_fix_cell_impl(self, code: str, error_msg: str) -> None:
        self._auto_fix_count += 1
        if self._auto_fix_count >= 3:
            _log.warning("auto-fix: retry limit reached (%d)", self._auto_fix_count)
            send_to_panel(
                self.ns,
                "text",
                content="Auto-fix retry limit reached\n",
            )
            self._transition(
                WorkflowEvent.AUTO_FIX_EXHAUSTED,
                trigger="auto_fix_exhausted",
            )
            return

        # Find the cell_id for this code to replace in-place
        cell_id = ""
        for r in self._round_results:
            if (r.get("code", "") or "").strip() == code.strip():
                cell_id = r.get("cell_id", "")
                break

        _log.info("auto-fix #%d: cell=%s error=%s", self._auto_fix_count, cell_id or "(new)", error_msg[:100])
        action = "replacing failed cell" if cell_id else "inserting fix below"
        send_to_panel(self.ns, "text",
            content=f"\n⚠ execution error (attempt {self._auto_fix_count}/3) — {action}:\n{error_msg}\n")

        # Strip magic markers that could confuse the AI
        clean_code = code
        for marker in ["\n%confirm", "\n%agent", "\n# %%agent generate code"]:
            clean_code = clean_code.replace(marker, "")

        prompt = (
            f"The following code cell failed with an error. "
            f"Analyze the error and provide a corrected version of the code.\n\n"
            f"## Error\n```\n{error_msg}\n```\n\n"
            f"## Failed Code\n```python\n{clean_code}\n```\n\n"
            f"IMPORTANT: Output ONLY the corrected Python code in a fenced code block. "
            f"Do NOT include any Jupyter magic commands (like %confirm or %agent). "
            f"Do not add explanations."
        )
        raw, interrupted = self._stream_with_interrupt(prompt)
        if interrupted:
            return
        if raw.strip():
            result = parse(raw)
            if result.code_list:
                fixed_code = result.code_list[0]
                self._submit_code_cells(
                    [fixed_code],
                    auto=True,
                    replace_cell_id=cell_id,
                )
                send_to_panel(self.ns, "text",
                    content="✓ auto-fixed (replaced)\n" if cell_id else "✓ auto-fixed (new cell)\n")
            else:
                self._transition(
                    WorkflowEvent.AUTO_FIX_EXHAUSTED,
                    trigger="auto_fix_no_code",
                    message="Auto-fix: no code in response",
                )
                return
        else:
            self._transition(
                WorkflowEvent.AUTO_FIX_EXHAUSTED,
                trigger="auto_fix_no_output",
                message="Auto-fix: no output",
            )
            return

    def _emit_plan_cell(self, plan_text: str) -> None:
        """Render the plan as a notebook markdown cell so it is visible + confirmable
        inside the notebook (not just the chat panel). Reuses the existing cell id
        on revision so the plan cell is updated in place rather than duplicated."""
        if not plan_text.strip():
            return
        content = "# %%plan\n\n" + plan_text

        def _on_plan_cell(cid, _code):
            self._plan_cell_id = cid
            self.ns._shell.user_ns["__plan_cell_id__"] = cid

        from .render import render_code
        render_code(self.ns, content, cell_type="markdown",
                    replace_cell_id=self._plan_cell_id, on_cell_id=_on_plan_cell)

    def _implement_plan(self, plan: str, auto: bool = False,
                        preparsed_result=None) -> None:
        """Execute a confirmed plan: inject code blocks if present, or send as implementation prompt."""
        result = preparsed_result if preparsed_result is not None else parse(plan)
        _log.info("plan implement: %d code blocks, auto=%s", len(result.code_list), auto)

        # Plan text is already shown as a markdown cell via _emit_plan_cell; drop it
        # here so render_output only emits code cells (avoids a duplicate plan cell).
        result.plan = ""

        self._agent_cells.clear()
        self._auto_fix_count = 0

        if result.code_list:
            self._submit_code_cells(result.code_list, auto=auto)
            return

        # Plan has no code blocks → stream implementation prompt
        prompt = self._last_plan_prompt or ""
        send_to_panel(self.ns, "text", content="↻ implementing plan...\n")
        full = (
            "[System: Plan mode has ended. The plan has been approved. "
            "You are now in implementation mode. "
            "Generate executable code cells to implement the approved plan below. "
            "Write complete, working code that the user can run directly — "
            "do NOT output plan descriptions or markdown explanations.]\n\n"
            f"## Approved Plan\n\n{plan}\n\n"
            "Implement this plan by writing executable code cells."
        )
        if prompt:
            full = f"Original request:\n{prompt}\n\n{full}"

        self._transition(
            WorkflowEvent.USER_CONFIRMED,
            has_code=False,
            trigger="plan_implementation",
        )
        raw, interrupted = self._stream_with_interrupt(full)
        if interrupted:
            return
        if not raw.strip():
            self._finish_agent_run("Plan implementation failed (no output)")
            return

        result = parse(raw)
        if result.code_list:
            self._submit_code_cells(result.code_list, auto=auto)
        else:
            self._finish_agent_run("Plan implementation returned no code")

    # ---- agent_config ----

    def _apply_config(self, resolved: dict) -> str:
        """Apply resolved config and rebuild session if needed. Shared by
        %agent_config and /config. Returns a summary string."""
        self._config_pending = None
        changes: list[str] = []
        agent = resolved["agent"]
        timeout = resolved["timeout"]
        claude_md_path = resolved["claude_md"]
        self._hook_cfg = resolved["hook_cfg"]
        self._tools_cfg = resolved["tools_cfg"]

        if agent not in _AGENTS:
            render_error(f"[agent_config] unknown agent '{agent}', valid: {', '.join(sorted(_AGENTS))}")
            agent = self._agent

        if agent != self._agent:
            changes.append(f"agent: {self._agent} → {agent}")
        if timeout != self._timeout:
            changes.append(f"timeout: {self._timeout}s → {timeout}s")
        if claude_md_path != self._claude_md_path:
            changes.append(f"claude_md: {claude_md_path}")

        if resolved["session_rebuild"]:
            if self._session_ready:
                self._session.cleanup()
                self._session_ready = False  # lazy re-init on next query
            changes.append("session will rebuild on next query")
        elif timeout != self._timeout:
            if self._session_ready and self._session.client is not None:
                self._session.client._backend._timeout = timeout
            changes.append("timeout updated (hot)")

        self._agent = agent
        self._timeout = timeout
        self._claude_md_path = claude_md_path
        return ", ".join(changes) if changes else "no changes"

    @line_magic("agent_config")
    def agent_config_func(self, line: str) -> None:
        """%agent_config [--config PATH] [--agent NAME] [--timeout N] [--claude-md PATH] [--debug] [--KEY=VALUE ...]"""
        args = shlex.split(line)

        config_path = pop_flag(args, "--config")
        cli_agent = pop_flag(args, "--agent")
        cli_timeout = pop_flag(args, "--timeout", convert=int)
        cli_claude_md = pop_flag(args, "--claude-md")
        cli_debug = "--debug" in args
        if cli_debug:
            args.remove("--debug")
        if "--no-debug" in args:
            args.remove("--no-debug")
            cli_debug = False
        if "--plan" in args:
            args.remove("--plan")  # mode driven by frontend
        if "--no-plan" in args:
            args.remove("--no-plan")
        env_vars = parse_kv(args)

        enable_hooks: list[str] = []
        disable_hooks: list[str] = []
        while "--enable-hook" in args:
            idx = args.index("--enable-hook")
            if idx + 1 < len(args):
                enable_hooks.append(args.pop(idx + 1))
            args.pop(idx)
        while "--disable-hook" in args:
            idx = args.index("--disable-hook")
            if idx + 1 < len(args):
                disable_hooks.append(args.pop(idx + 1))
            args.pop(idx)

        resolved = configure_agent(
            config_path=config_path,
            cli_agent=cli_agent, cli_timeout=cli_timeout,
            cli_claude_md=cli_claude_md, cli_debug=cli_debug,
            cli_env=env_vars,
            enable_hooks=enable_hooks, disable_hooks=disable_hooks,
            defaults={},
            current_agent=self._agent,
            current_timeout=self._timeout,
            current_claude_md=self._claude_md_path,
            current_hook_cfg=self._hook_cfg,
        )
        if config_path:
            self._jupyter_config_path = config_path
        summary = self._apply_config(resolved)
        render_info(f"agent: {self._agent}, timeout: {self._timeout}s [{summary}]")

    # ---- %kb_view (line magic) ----

    @line_magic("kb_view")
    def kb_view_func(self, line: str) -> None:
        """%kb_view [--height N] [--save PATH]

        Render the risk-knowledge-base as a human-readable gallery inline.

        The view is built from ``skills/risk-knowledge-base`` (manifest + docs)
        and embedded in an isolated iframe via ``srcdoc`` so its global CSS does
        not leak into the notebook DOM. Pass ``--save PATH`` to also write the
        standalone HTML to disk.
        """
        from IPython.display import HTML, display

        args = shlex.split(line)
        height = pop_flag(args, "--height", convert=int) or 820
        save_path = pop_flag(args, "--save")

        try:
            doc = _build_kb_view_html()
        except FileNotFoundError as e:
            render_error(f"[kb_view] not found: {e}")
            return
        except Exception as e:
            render_error(f"[kb_view] failed to build view: {e}")
            _log.exception("kb_view build failed")
            return

        if save_path:
            from pathlib import Path
            out = Path(save_path)
            if not out.is_absolute():
                out = Path(_os.getcwd()) / out
            try:
                out.write_text(doc, encoding="utf-8")
                render_info(f"[kb_view] saved: {out}")
            except OSError as e:
                render_error(f"[kb_view] save failed: {e}")

        srcdoc = html.escape(doc, quote=True)
        # sandbox allows scripts (search/nav) + popups so the "原文 ↗" links can
        # open the source Lark docs in a new tab; -to-escape-sandbox lets that
        # new tab load normally instead of inheriting the sandbox restrictions.
        # Wrapped in a <div> so the payload is not a bare <iframe>…</iframe> —
        # IPython.display.HTML warns on that exact shape ("use IFrame instead"),
        # but IFrame only supports src=URL, not the srcdoc we need for isolation.
        display(HTML(
            f'<div class="kb-view-wrap">'
            f'<iframe srcdoc="{srcdoc}" '
            f'style="width:100%;height:{height}px;border:1px solid #e8e8ef;'
            f'border-radius:12px;" '
            f'sandbox="allow-scripts allow-popups allow-popups-to-escape-sandbox">'
            f'</iframe>'
            f'</div>'
        ))

    # ---- %sql / %%sql (line + cell magic) ----

    @line_magic("sql")
    @cell_magic("sql")
    def sql_func(self, line: str, cell: str = None) -> None:
        """%sql status|result|cancel [options]  |  %%sql [--var NAME] [--timeout N] [--poll N] | submit | result --job_id ID [--limit N]"""
        args = shlex.split(line)

        # ---- line magic: %sql status|result|cancel ----
        if cell is None:
            sub = args[0] if args else ""
            job_id = pop_flag(args, "--job_id")
            limit = pop_flag(args, "--limit", convert=int) or 100

            if not job_id:
                render_error("--job_id is required")
                return

            runner = SqlRunner()
            try:
                if sub == "status":
                    result = runner.status(job_id)
                    data = result.get("data", {})
                    render_info(f"job_id: {data.get('job_id', job_id)}")
                    render_info(f"status: {data.get('status', '?')}")
                    render_info(f"engine:  {data.get('engine_type', '?')}")
                elif sub == "cancel":
                    result = runner.cancel(job_id)
                    data = result.get("data", {})
                    requested = data.get("cancel_requested", "false")
                    render_info(f"job_id: {data.get('job_id', job_id)}  cancel_requested: {requested}")
                elif sub == "result":
                    var_name = pop_flag(args, "--var") or self.ns.next_sql_var()
                    result = runner.result(job_id, limit=limit)
                    render_sql_dataframe(self.ns,result.get("data", {}), var_name)
                else:
                    render_error(f"unknown subcommand: {sub}. Use: status | cancel | result")
            except RuntimeError as e:
                render_error(f"{e}")
            return

        # ---- cell magic: %%sql [query|submit] ----
        mode = args[0] if args and not args[0].startswith("--") else "query"

        if mode == "submit":
            try:
                result = SqlRunner().submit(cell)
                job_id = result.get("data", {}).get("job_id", "")
                render_info(f"job submitted: {job_id}")
            except RuntimeError as e:
                render_error(f"{e}")
        else:
            var_name = pop_flag(args, "--var")
            timeout = pop_flag(args, "--timeout", convert=int) or 600
            poll = pop_flag(args, "--poll", convert=int) or 30
            runner = SqlRunner(poll_interval=poll, timeout=timeout)
            try:
                result = runner.query(cell, on_progress=sql_progress)
                data = result.get("data", {})
                if not var_name:
                    var_name = self.ns.next_sql_var()
                df = render_sql_dataframe(self.ns, data, var_name)
                if df is not None:
                    render_info(f"sql query: var={var_name} rows={len(df)} sql={cell[:500]}")
                else:
                    render_error("sql query returned no data")
                    _log.error(f"sql={cell[:500]}")
            except (RuntimeError, TimeoutError) as e:
                render_error(str(e))
                _log.error(f"sql query error: {e}")

    # Agent interaction now handled via right-side panel only
