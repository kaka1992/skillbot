"""%%sql cell magic + agent panel integration — thin scheduling layer."""

import hashlib
import logging
import os as _os
import shlex
import sys
import time
from enum import Enum, auto

from IPython.core.magic import Magics, cell_magic, line_magic, magics_class

from agent import AgentSession, SubAgentConfig
from agent.prompt import PromptBuilder
from chat import _AGENTS
from hook import HookGroup, HookRegistry, HookEvent
from jupyter.telemetry import get_recorder, SessionEventRecorder, set_recorder
from .config import pop_flag, parse_kv, configure_agent, load_yaml_config
from .namespace import Namespace
from .panel import send_to_panel, send_thinking
from .parser import parse
from .render import render_debug, render_error, render_info, render_output, render_sql_dataframe
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


def _panel_input(text: str, mode: str = "default") -> None:
    """Bridge: called by frontend requestExecute → dispatches to AgentMagic."""
    inst = _get_magic()
    if inst:
        inst._on_panel_input(text, mode)


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


def _merge_prompt(claude_md_path: str | None = None) -> str:
    return PromptBuilder.main(claude_md_path)


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


class AgentState(Enum):
    """Explicit agent lifecycle state."""
    IDLE = auto()
    STREAMING = auto()           # agent is generating a response
    PLAN_REVIEW = auto()         # plan displayed, waiting for confirm/revision
    WAITING_CONFIRM = auto()     # response ready, waiting for user yes/no before acting
    AUTO_FIXING = auto()         # deferred auto-fix in progress (auto mode)


@magics_class
class AgentMagic(Magics):
    _agent = "claude-code"
    _timeout = 600
    _claude_md_path: str | None = None
    _tools_cfg: dict = {}

    def __init__(self, shell):
        super().__init__(shell)
        import sys as _sys
        _sys.modules[__name__]._agent_magic_instance = self
        self.ns = Namespace(shell)
        self._state = AgentState.IDLE
        self._busy = False                         # legacy — will be removed after refactor
        self._last_plan_prompt = ""
        self._last_plan_output = ""
        self._last_plan_result = None                  # cached ParsedResult for _implement_plan
        self._pending_result = None                    # ParsedResult waiting for user confirmation
        self._agent_cells: dict[str, str] = {}     # cell_id → code, for auto-fix lookup
        self._round_results: list[dict] = []        # [{cell_id, code, output}] for auto-fix lookup
        self._auto_pending = 0                      # count of auto-exec cells still running
        self._auto_fix_count = 0                    # limit retries per batch
        self._session_ready = False                 # lazy-init session on first query
        self._session_dirty = False                 # set on interrupt, prepend note on next query
        self._jupyter_config_path = ""              # path from JUPYTER_CONFIG_PATH env var
        self._config_pending = None                 # pending (resolved, new_path, old_path)
        self._cell_restored = False                 # track if any cell was individually restored
        self._restoring_cells: set = set()          # cell_ids being restored, skip snapshot for these

        self._load_dotenv()

        # Load default config for hooks baseline, then auto-load from env var
        cfg = load_yaml_config("conf/jupyter_agent.yaml")
        self._hook_cfg = cfg.get("hooks", {})
        self._startup_config_msg = self._load_jupyter_config()
        self.ns.delta()
        shell.events.register("post_run_cell", self._on_cell_run)
        from .panel import init_panel_comm
        init_panel_comm(shell)

    # ---- state machine helpers -----------------------------------------------

    def _interrupt_cleanup(self, msg: str = "\n⏏ interrupted\n") -> None:
        """Unified KeyboardInterrupt handler — replaces 5 duplicated copies."""
        self._session_dirty = True
        self._state = AgentState.IDLE
        self._record_state("interrupt")
        self._busy = False
        self._auto_pending = 0
        self._auto_fix_count = 0
        self._pending_result = None
        self._round_results.clear()
        send_to_panel(self.ns, "text", content=msg)
        send_to_panel(self.ns, "result", summary="")
        send_to_panel(self.ns, "ready")

    def _stream_with_interrupt(self, prompt: str) -> tuple[str, bool]:
        """Stream agent response. Returns (raw_text, was_interrupted)."""
        if self._session_dirty:
            self._session_dirty = False
            prompt = _INTERRUPT_NOTE + "\n\n" + prompt
        rec = get_recorder()
        t0 = time.time()
        thinking_chars = 0
        tool_names: set[str] = set()

        def _on_chunk(t):
            send_to_panel(self.ns, "text", content=t)

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
                on_thinking=_on_thinking)
            if _think_buf:
                send_thinking(_think_buf)
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

    def _finish_agent_run(self, msg: str = "") -> None:
        """Clean up after agent run completes. Sends result + ready to frontend."""
        if self._state == AgentState.IDLE:
            return  # already finished, prevent duplicate ready/result
        self._state = AgentState.IDLE
        self._record_state("agent_done")
        self._busy = False
        self._auto_pending = 0
        self._pending_result = None
        self._round_results.clear()
        self._agent_cells.clear()
        if msg:
            send_to_panel(self.ns, "text", content=f"{msg}\n")
        send_to_panel(self.ns, "result", summary="")
        send_to_panel(self.ns, "ready")

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
        """Show Yes/No confirmation — text + buttons via comm."""
        self._state = AgentState.WAITING_CONFIRM
        self._record_state("confirm_shown")
        self._busy = False
        self._pending_result = pending_result
        send_to_panel(self.ns, "result", summary="")
        send_to_panel(self.ns, "ready")
        send_to_panel(self.ns, "text",
            content=f"\n{'─'*40}\n{msg}\nType /continue yes or /continue no\n{'─'*40}\n")
        send_to_panel(self.ns, "continue_confirm", summary=msg)

    def _handle_continue(self, arg: str) -> None:
        """Handle /continue yes|no from panel."""
        arg = arg.strip()
        rec = get_recorder()
        if rec:
            rec.record("agent_continue", choice="yes" if arg.strip() == "yes" else "no")
        if arg != "yes":
            self._finish_agent_run("Task stopped")
            self._record_state("user_stop")
            return

        pending = self._pending_result
        self._pending_result = None
        if pending is not None and pending.code_list:
            # Has code cells: inject + auto-execute
            self._state = AgentState.STREAMING
            self._record_state("user_continue")
            self._busy = True
            self._agent_cells.clear()
            self._auto_fix_count = 0
            self._auto_pending = len(pending.code_list)
            render_output(self.ns, pending, auto=True, on_cell_id=self._track_agent_cell)
            if self._auto_pending == 0:
                self._finish_agent_run()
            # else: _on_cell_run handles completion → finish
            return

        # No code cells: continue the conversation
        prompt = "[System: Continue with the task. Generate the next steps.]"
        self._state = AgentState.STREAMING
        self._record_state("user_continue")
        self._busy = True
        if rec:
            rec.record("agent_prompt", mode="continue", prompt="", context_preview="")
        raw, interrupted = self._stream_with_interrupt(prompt)
        if interrupted:
            return
        if not raw.strip():
            self._finish_agent_run()
            return
        result = parse(raw)
        if result.code_list:
            self._ask_confirm(f"Generate and execute {len(result.code_list)} cells?", pending_result=result)
        else:
            self._ask_confirm("Continue?", pending_result=result)

    def _handle_panel_stop(self) -> None:
        """Handle /stop — exit current task immediately."""
        if self._state == AgentState.IDLE:
            send_to_panel(self.ns, "text", content="No active task.\n")
            return
        try:
            self._session.interrupt()
        except Exception:
            pass
        self._finish_agent_run("Task stopped")

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
        self._session = AgentSession(agent, timeout)
        self._session.configure_subs(SUB_AGENT_DEFAULTS)
        self._session.init_session(
            system_prompt=_merge_prompt(claude_md),
            session_key=_session_key(),
            on_init=lambda s: _register_hooks(timeout, self._hook_cfg),
        )

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
            # Track cell for auto-fix lookup
            self._agent_cells[cell_id] = code.strip()
            self._round_results.append({
                "cell_id": cell_id, "code": code.strip(), "output": output.strip()
            })

            # Auto mode: decrement pending count
            if self._auto_pending > 0:
                self._auto_pending -= 1
                _log.debug("auto pending: %d remaining", self._auto_pending)

            # Auto-fix: agent-generated cell failed → ask AI to fix
            if not result.success and self._state in (AgentState.STREAMING, AgentState.AUTO_FIXING):
                if error_str:
                    self._auto_fix_cell(code.strip(), error_str)

        # ---- snapshot logic ----
        restoring = cell_id in getattr(self, '_restoring_cells', set())
        if cell_id and code.strip() and not restoring:
            from .cell_snapshot import save as save_cell_snapshot
            save_cell_snapshot(cell_id, code.strip(), output.strip(), error_str, nb_path=_notebook_path())
        if code.strip():
            if restoring:
                self._restoring_cells.discard(cell_id)
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
            rec.record("cell_executed",
                cell_id=cell_id,
                type=cell_type,
                code=code.strip(),
                output=output.strip(),
                error=str(error) if error else None,
                elapsed_ms=0.0,
                is_agent_cell=is_agent_cell,
                exec_order=rec.next_exec_order(),
            )

        # ---- state transitions ----
        # Auto mode / confirmed execution: all cells complete → finish or continue
        if is_agent_cell and self._auto_pending == 0 and self._state in (AgentState.STREAMING, AgentState.AUTO_FIXING):
            self._finish_agent_run()

    # ---- panel handler ----

    def _on_panel_input(self, text: str, mode: str = "default") -> None:
        """Handle input from right-side panel."""
        # Flush startup config message on first interaction
        msg = getattr(self, '_startup_config_msg', '')
        if msg and send_to_panel(self.ns, "text", content=msg):
            self._startup_config_msg = ""
        text = text.strip()
        if text.startswith("/confirm "):
            self._handle_panel_confirm(text[9:])
        elif text == "/clear":
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
            self._handle_panel_prompt(text, mode)

    def _handle_panel_prompt(self, prompt: str, mode: str = "default") -> None:
        """Execute agent prompt from panel: stream to panel + inject cells to left."""
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
            return

        if self._state != AgentState.IDLE:
            send_to_panel(self.ns, "text", content="⏳ agent is working, please wait...\n")
            send_to_panel(self.ns, "result", summary="")
            return

        # Build prompt with context
        ctx = self.ns.delta()
        full = f"{ctx}\n\n{prompt}" if ctx else prompt

        if mode == "plan":
            self._last_plan_prompt = prompt
            plan_prefix = (
                "[System: You are in plan mode. Explore the request, research the codebase, "
                "and design an implementation approach. Present your plan as structured markdown. "
                "Do NOT write or execute any code until the user confirms the plan.]\n\n"
            )
            full = plan_prefix + full

        # Stream
        self._state = AgentState.STREAMING
        self._busy = True
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
            send_to_panel(self.ns, "plan_confirm", summary=plan_text)
            self._state = AgentState.PLAN_REVIEW
            self._busy = False
            send_to_panel(self.ns, "ready")
        elif mode == "auto":
            _log.info("auto mode: %d code blocks", len(result.code_list))
            self._agent_cells.clear()
            self._auto_fix_count = 0
            self._auto_pending = len(result.code_list)
            if self._auto_pending == 0:
                self._finish_agent_run()
            else:
                render_output(self.ns, result, auto=True, on_cell_id=self._track_agent_cell)
                # _on_cell_run handles completion: sends ready when _auto_pending == 0
        else:
            if result.code_list:
                self._ask_confirm(f"Generate and execute {len(result.code_list)} cells?", pending_result=result)
            else:
                self._ask_confirm("Continue?", pending_result=result)

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
            # Session not yet initialized — use SkillManager directly
            try:
                from chat.skill import SkillManager
                from chat import _resolve_skill_dir
                mgr = SkillManager(_resolve_skill_dir("claude-code"))
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
        from .cell_snapshot import restore
        parts = text.split()
        if len(parts) < 3:
            send_to_panel(self.ns, "text", content="Usage: /cell-snapshot-restore <cell_id> <version>\n")
            return
        cell_id = parts[1]
        version = parts[2]
        code = restore(cell_id, version)
        if code is None:
            send_to_panel(self.ns, "text", content=f"Version {version} not found.\n")
            return
        self._restoring_cells.add(cell_id)
        from .comm import send_cell_via_comm
        send_cell_via_comm(self.ns, code, auto=False, cell_type="code", replace_cell_id=cell_id)
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
        self._state = AgentState.STREAMING
        self._busy = True
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
            from .render import render_code
            render_code(self.ns, optimized, auto=auto_exec, replace_cell_id=cell_id)
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
        arg = arg.strip()
        if not arg:
            return

        if arg == "yes":
            if self._last_plan_result is not None:
                self._implement_plan(self._last_plan_output or "", auto=True,
                                     preparsed_result=self._last_plan_result)
                self._record_state("plan_confirm")
            self._last_plan_output = ""
            self._last_plan_result = None
            send_to_panel(self.ns, "result", summary="")
        elif arg == "accept_edits":
            if self._last_plan_result is not None:
                self._implement_plan(self._last_plan_output or "", auto=False,
                                     preparsed_result=self._last_plan_result)
                self._record_state("plan_confirm")
            self._last_plan_output = ""
            self._last_plan_result = None
            send_to_panel(self.ns, "result", summary="")
        elif arg == "no":
            self._last_plan_output = ""
            self._finish_agent_run("Plan cancelled")
        else:
            # Revision feedback
            send_to_panel(self.ns, "text", content=f"↻ revising plan: {arg}\n")
            plan = self._last_plan_output or ""
            prompt = self._last_plan_prompt or ""
            if plan and prompt:
                full = f"User feedback on the plan: {arg}\n\nOriginal request:\n{prompt}\n\nPrevious plan:\n{plan}\n\nRevise the plan based on the feedback."
                self._state = AgentState.STREAMING
                self._busy = True
                raw, interrupted = self._stream_with_interrupt(full)
                if interrupted:
                    return
                if raw.strip():
                    self._last_plan_output = raw.strip()
                    result = parse(raw)
                    plan_text = result.plan or result.text or ""
                    self._state = AgentState.PLAN_REVIEW
                    self._busy = False
                    send_to_panel(self.ns, "plan_confirm", summary=plan_text)
                    send_to_panel(self.ns, "ready")
                else:
                    self._last_plan_output = ""
                    send_to_panel(self.ns, "text", content="✗ plan revision failed (no output)\n")
                    send_to_panel(self.ns, "result", summary="")
            else:
                send_to_panel(self.ns, "text", content="✗ no plan to revise\n")
                send_to_panel(self.ns, "result", summary="")

    def _auto_fix_cell(self, code: str, error_msg: str) -> None:
        """Auto mode: cell execution failed → ask AI to fix and replace in-place."""
        if self._state == AgentState.AUTO_FIXING:
            _log.warning("auto-fix: already fixing, skipping recursive call")
            return
        self._state = AgentState.AUTO_FIXING
        self._record_state("auto_fix")
        try:
            self._auto_fix_cell_impl(code, error_msg)
        finally:
            if self._state == AgentState.AUTO_FIXING:
                self._state = AgentState.STREAMING

    def _auto_fix_cell_impl(self, code: str, error_msg: str) -> None:
        self._busy = True
        self._auto_fix_count += 1
        if self._auto_fix_count >= 3:
            _log.warning("auto-fix: retry limit reached (%d)", self._auto_fix_count)
            self._auto_pending = 0
            self._finish_agent_run("Auto-fix retry limit reached")
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
                from .render import render_code
                self._auto_pending += 1
                render_code(self.ns, fixed_code, auto=True, replace_cell_id=cell_id)
                send_to_panel(self.ns, "text",
                    content="✓ auto-fixed (replaced)\n" if cell_id else "✓ auto-fixed (new cell)\n")
                if self._auto_fix_count >= 2:
                    self._finish_agent_run()
                    return
            else:
                self._finish_agent_run("Auto-fix: no code in response")
                return
        else:
            self._finish_agent_run("Auto-fix: no output")
            return

    def _implement_plan(self, plan: str, auto: bool = False,
                        preparsed_result=None) -> None:
        """Execute a confirmed plan: inject code blocks if present, or send as implementation prompt."""
        result = preparsed_result if preparsed_result is not None else parse(plan)
        _log.info("plan implement: %d code blocks, auto=%s", len(result.code_list), auto)

        self._agent_cells.clear()
        self._auto_fix_count = 0

        if result.code_list:
            if auto:
                self._state = AgentState.STREAMING
                self._busy = True
                self._auto_pending = len(result.code_list)
                render_output(self.ns, result, auto=True, on_cell_id=self._track_agent_cell)
                if self._auto_pending == 0:
                    self._finish_agent_run()
                    return
            else:
                self._ask_confirm(f"Generate and execute {len(result.code_list)} cells?", pending_result=result)
            label = "✓ plan implemented\n" if auto else "✓ plan accepted (code cells generated)\n"
            send_to_panel(self.ns, "text", content=label)
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

        self._state = AgentState.STREAMING
        self._busy = True
        raw, interrupted = self._stream_with_interrupt(full)
        if interrupted:
            return
        if not raw.strip():
            self._finish_agent_run("Plan implementation failed (no output)")
            return

        result = parse(raw)
        if auto:
            self._state = AgentState.STREAMING
            self._auto_pending = len(result.code_list)
            render_output(self.ns, result, auto=True, on_cell_id=self._track_agent_cell)
            if self._auto_pending == 0:
                self._finish_agent_run()
        elif result.code_list:
            self._ask_confirm(f"Generate and execute {len(result.code_list)} cells?", pending_result=result)
        else:
            self._ask_confirm("Continue?", pending_result=result)
        send_to_panel(self.ns, "text", content="✓ plan implemented\n" if auto else "✓ plan accepted (code cells generated)\n")

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
