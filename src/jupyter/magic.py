"""%%sql cell magic + agent panel integration — thin scheduling layer."""

import hashlib
import logging
import os as _os
import shlex

from IPython.core.magic import Magics, cell_magic, line_magic, magics_class

from agent import AgentSession, SubAgentConfig
from agent.prompt import PromptBuilder
from chat import _AGENTS
from hook import HookGroup, HookRegistry, HookEvent
from jupyter.telemetry import get_recorder, TelemetryRecorder, set_recorder
from .config import pop_flag, parse_kv, configure_agent, load_yaml_config
from .namespace import Namespace
from .panel import send_to_panel, send_thinking
from .parser import parse, traceback_line
from .render import render_debug, render_error, render_info, render_output, render_sql_dataframe
from .dsl.sql import SqlRunner, sql_progress
from hook.impl.code_review import AgentCodeReviewHook
from hook.impl.cell_review import AgentCellReviewHook

_log = logging.getLogger(__name__)

_TRACE_MARKER = "%agent --trace"

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


def _notebook_path() -> str:
    try:
        ip = get_ipython()  # noqa: F821
        nb = getattr(ip, "_notebook_path", None)
        if nb:
            return nb
        kernel = getattr(ip, "kernel", None)
        parent = getattr(kernel, "_parent_header", None) or {}
        nb = (parent.get("metadata") or {}).get("notebook_path")
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
        self._plan = False
        self._plan_mode_active = False
        self._last_plan_prompt = ""
        self._last_plan_output = ""
        self._agent_cells: dict[str, str] = {}  # cell_id → code, for auto-fix on error
        self._auto_fixing = False  # guard against recursive auto-fix
        self._auto_fix_count = 0   # limit retries per batch
        self._auto_pending = 0     # count of auto-exec cells still running
        self._busy = False          # block input while agent is working
        self._session_ready = False  # lazy-init session on first query
        cfg = load_yaml_config("conf/jupyter_agent.yaml")
        self._hook_cfg = cfg.get("hooks", {})
        self.ns.delta()
        shell.events.register("post_run_cell", self._on_cell_run)
        from .panel import init_panel_comm
        init_panel_comm(shell)

    def _ensure_session(self) -> None:
        """Lazy-init agent session on first query (keeps kernel startup fast)."""
        if self._session_ready:
            return
        self._init_session(self._agent, self._timeout, self._claude_md_path)
        if self._session.client is None:
            raise RuntimeError("session init failed — is Claude server (port 9000) running?")
        rec = TelemetryRecorder(
            session_id=self._session.session_id,
            path=_os.path.join(".run", "sessions", f"{self._session.session_id}.jsonl"),
        )
        set_recorder(rec)
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
        code = getattr(info, "raw_cell", "")
        if not code:
            return

        # Track auto-exec cell completion (decrement only, signal after auto-fix check)
        is_agent_cell = "# %%agent generate code" in code
        if is_agent_cell and self._auto_pending > 0:
            self._auto_pending -= 1
            _log.debug("auto pending: %d remaining", self._auto_pending)

        # Auto-fix: agent-generated cell failed → send error to AI
        if not result.success and is_agent_cell:
            error = result.error_in_exec or result.error_before_exec
            _log.info("auto-fix triggered: error=%s", type(error).__name__ if error else "None")
            if error is not None:
                import traceback as _tb
                error_msg = "".join(_tb.format_exception_only(type(error), error))
                self._auto_fix_cell(code.strip(), error_msg)
            return

        # Detect: code before %agent --trace errored → auto-trigger trace
        if _TRACE_MARKER in code and not result.success:
            error = result.error_in_exec or result.error_before_exec
            if error is not None:
                tb = getattr(error, "__traceback__", None)
                err_line = traceback_line(tb) if tb else 10**9
                _, tr_idx = self._split_at_trace(code)
                if err_line <= code[:tr_idx].count("\n") + 1:
                    import traceback
                    error_msg = "".join(traceback.format_exception_only(type(error), error))
                    self._trace_on_error(code, error_msg)
            return

        output = str(info.result) if getattr(info, "result", None) else ""
        self.ns.track_cell(code.strip(), output.strip())

        rec = get_recorder()
        if rec:
            cell_type = "plain"
            if code.startswith("%%sql"): cell_type = "%%sql"
            error = getattr(result, "error_in_exec", None) or getattr(result, "error_before_exec", None)
            rec.record("cell_executed",
                cell_id="",
                type=cell_type,
                code=code[:2000],
                output=output[:2000],
                error=str(error)[:2000] if error else None,
                elapsed=0.0,
            )

        # Signal ready when all auto-exec cells complete (success path)
        if is_agent_cell and self._auto_pending == 0 and self._busy:
            self._busy = False
            send_to_panel(self.ns, "ready")

    # ---- panel handler ----

    def _on_panel_input(self, text: str, mode: str = "default") -> None:
        """Handle input from right-side panel."""
        text = text.strip()
        if text.startswith("/confirm "):
            self._handle_panel_confirm(text[9:])
        elif text == "/clear":
            send_to_panel(self.ns, "clear")
        elif text.startswith("/mode "):
            self._handle_panel_mode(text[6:].strip())
        else:
            self._handle_panel_prompt(text, mode)

    def _handle_panel_prompt(self, prompt: str, mode: str = "default") -> None:
        """Execute agent prompt from panel: stream to panel + inject cells to left."""
        try:
            self._ensure_session()
        except Exception:
            _log.exception("_handle_panel_prompt: session init failed")
            send_to_panel(self.ns, "text", content="✗ session initialization failed, check server logs\n")
            send_to_panel(self.ns, "result", summary="")
            return
        if self._busy:
            send_to_panel(self.ns, "text", content="⏳ agent is working, please wait...\n")
            send_to_panel(self.ns, "result", summary="")
            return

        ctx = self.ns.delta()
        full = f"{ctx}\n\n{prompt}" if ctx else prompt
        self._busy = True

        # plan mode: inject plan-mode instruction prefix + set state
        if mode == "plan":
            self._plan = True
            self._last_plan_prompt = full
            self._plan_mode_active = True
            plan_prefix = (
                "[System: You are in plan mode. Explore the request, research the codebase, "
                "and design an implementation approach. Present your plan as structured markdown. "
                "Do NOT write or execute any code until the user confirms the plan.]\n\n"
            )
            full = plan_prefix + full
        else:
            self._plan = False

        raw = self._session.stream(full, show_text=False,
                                    on_chunk=lambda t: send_to_panel(self.ns, "text", content=t),
                                    on_thinking=lambda t: send_thinking(t))
        send_to_panel(self.ns, "text", content="\n")

        if raw.strip():
            result = parse(raw)
            if mode == "plan":
                # plan mode: show plan in panel only, NO cell injection yet
                self._last_plan_output = raw.strip()
                plan_text = result.plan or result.text or ""
                send_to_panel(self.ns, "plan_confirm", summary=plan_text)
                self._busy = False
                send_to_panel(self.ns, "ready")
            elif mode == "auto":
                _log.info("auto mode: %d code blocks, tracking cells for auto-fix", len(result.code_list))
                self._agent_cells.clear()
                self._auto_fix_count = 0
                self._auto_pending += len(result.code_list)
                if self._auto_pending == 0:
                    self._busy = False
                    send_to_panel(self.ns, "ready")
                def _on_cid(cid, code_str):
                    if cid:
                        self._agent_cells[cid] = code_str
                        _log.debug("auto mode: tracked cell %s (%d chars)", cid, len(code_str))
                render_output(self.ns, result, auto=True, trace=False, on_cell_id=_on_cid)
                _log.info("auto mode: tracked %d cells", len(self._agent_cells))
                send_to_panel(self.ns, "result", summary="")
            else:
                self._agent_cells.clear()
                def _on_cid_default(cid, code_str):
                    if cid:
                        self._agent_cells[cid] = code_str
                render_output(self.ns, result, auto=False, trace=False, on_cell_id=_on_cid_default)
                send_to_panel(self.ns, "result", summary="")
                self._busy = False
                send_to_panel(self.ns, "ready")
        else:
            # no output — still signal completion
            send_to_panel(self.ns, "result", summary="")
            self._busy = False
            send_to_panel(self.ns, "ready")

    def _handle_panel_mode(self, mode: str) -> None:
        """Handle /mode from panel: cycle between default, plan, auto."""
        self._plan = (mode == "plan")

    def _handle_panel_confirm(self, arg: str) -> None:
        """Handle /confirm from panel."""
        arg = arg.strip()
        if not arg:
            return  # empty /confirm — do nothing

        if arg == "yes":
            self._plan = False
            self._plan_mode_active = False
            plan = getattr(self, '_last_plan_output', '') or ""
            if plan:
                self._implement_plan(plan, auto=True)
            send_to_panel(self.ns, "result", summary="")
        elif arg == "accept_edits":
            self._plan = False
            self._plan_mode_active = False
            plan = getattr(self, '_last_plan_output', '') or ""
            if plan:
                self._implement_plan(plan, auto=False)
            send_to_panel(self.ns, "result", summary="")
        elif arg == "no":
            self._plan = False
            self._plan_mode_active = False
            self._last_plan_output = ""
            send_to_panel(self.ns, "text", content="✗ plan cancelled\n")
            send_to_panel(self.ns, "result", summary="")
        else:
            # Revision feedback
            send_to_panel(self.ns, "text", content=f"↻ revising plan: {arg}\n")
            plan = getattr(self, '_last_plan_output', '') or ""
            prompt = getattr(self, '_last_plan_prompt', '') or ""
            if plan and prompt:
                full = f"User feedback on the plan: {arg}\n\nOriginal request:\n{prompt}\n\nPrevious plan:\n{plan}\n\nRevise the plan based on the feedback."
                raw = self._session.stream(full, show_text=False,
                    on_chunk=lambda t: send_to_panel(self.ns, "text", content=t),
                    on_thinking=lambda t: send_thinking(t))
                send_to_panel(self.ns, "text", content="\n")
                if raw.strip():
                    self._last_plan_output = raw.strip()
                    result = parse(raw)
                    plan_text = result.plan or result.text or ""
                    send_to_panel(self.ns, "plan_confirm", summary=plan_text)
                else:
                    # Revision produced empty output — clear stale state
                    self._last_plan_output = ""
                    send_to_panel(self.ns, "text", content="✗ plan revision failed (no output)\n")
                    send_to_panel(self.ns, "result", summary="")
            else:
                send_to_panel(self.ns, "text", content="✗ no plan to revise\n")
                send_to_panel(self.ns, "result", summary="")

    def _auto_fix_cell(self, code: str, error_msg: str) -> None:
        """Auto mode: cell execution failed → ask AI to fix and replace in-place."""
        if self._auto_fixing:
            _log.warning("auto-fix: already fixing, skipping recursive call")
            return
        self._auto_fixing = True
        try:
            self._auto_fix_cell_impl(code, error_msg)
        finally:
            self._auto_fixing = False

    def _auto_fix_cell_impl(self, code: str, error_msg: str) -> None:
        self._busy = True  # re-set — failed cell's completion may have cleared it
        # Retry limit: 2 attempts, then force-stop to unblock the queue
        self._auto_fix_count += 1
        if self._auto_fix_count >= 3:
            _log.warning("auto-fix: retry limit reached (%d)", self._auto_fix_count)
            send_to_panel(self.ns, "text", content="✗ auto-fix retry limit reached, stopping\n")
            send_to_panel(self.ns, "result", summary="")
            self._auto_pending = 0
            self._busy = False
            send_to_panel(self.ns, "ready")
            return

        # Find the cell_id for this code to replace in-place
        cell_id = ""
        for cid, ccode in self._agent_cells.items():
            if ccode.strip() == code.strip():
                cell_id = cid
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
        raw = self._session.stream(prompt, show_text=False,
            on_chunk=lambda t: send_to_panel(self.ns, "text", content=t),
            on_thinking=lambda t: send_thinking(t))
        send_to_panel(self.ns, "text", content="\n")

        if raw.strip():
            result = parse(raw)
            if result.code_list:
                fixed_code = result.code_list[0]
                from .render import render_code
                self._auto_pending += 1
                render_code(self.ns, fixed_code, auto=True, trace=False,
                           replace_cell_id=cell_id)
                send_to_panel(self.ns, "text",
                    content="✓ auto-fixed (replaced)\n" if cell_id else "✓ auto-fixed (new cell)\n")
                # Last retry: unblock queue even if fix cell never executes
                if self._auto_fix_count >= 2:
                    self._busy = False
                    send_to_panel(self.ns, "ready")
            else:
                send_to_panel(self.ns, "text", content="✗ auto-fix: no code in response\n")
                self._auto_pending = 0
                self._busy = False
                send_to_panel(self.ns, "ready")
        else:
            send_to_panel(self.ns, "text", content="✗ auto-fix failed (no output)\n")
            self._auto_pending = 0
            self._busy = False
            send_to_panel(self.ns, "ready")
        send_to_panel(self.ns, "result", summary="")

    def _implement_plan(self, plan: str, auto: bool = False) -> None:
        """Execute a confirmed plan: inject code blocks if present, or send as implementation prompt."""
        result = parse(plan)
        _log.info("plan implement: %d code blocks, auto=%s", len(result.code_list), auto)

        _log.info("implement_plan: auto=%s tracking cells", auto)
        self._agent_cells.clear()
        self._auto_fix_count = 0
        if auto:
            self._busy = True
            self._auto_pending = len(result.code_list)
            if self._auto_pending == 0:
                self._busy = False
                send_to_panel(self.ns, "ready")
        def _on_cid(cid, code_str):
            if cid:
                self._agent_cells[cid] = code_str
                _log.debug("implement_plan: tracked cell %s", cid)

        if result.code_list:
            # Plan contains executable code blocks → inject directly
            render_output(self.ns, result, auto=auto, trace=False, on_cell_id=_on_cid)
            label = "✓ plan implemented\n" if auto else "✓ plan accepted (code cells generated)\n"
            send_to_panel(self.ns, "text", content=label)
            return

        # Plan has no code blocks → send as implementation prompt
        prompt = getattr(self, '_last_plan_prompt', '') or ""
        send_to_panel(self.ns, "text", content="↻ implementing plan...\n")

        # Build implementation prompt with clear instructions
        impl_instruction = (
            "[System: Plan mode has ended. The plan has been approved. "
            "You are now in implementation mode. "
            "Generate executable code cells to implement the approved plan below. "
            "Write complete, working code that the user can run directly — "
            "do NOT output plan descriptions or markdown explanations.]"
        )
        full = f"{impl_instruction}\n\n## Approved Plan\n\n{plan}\n\nImplement this plan by writing executable code cells."
        if prompt:
            full = f"Original request:\n{prompt}\n\n{full}"

        raw = self._session.stream(full, show_text=False,
            on_chunk=lambda t: send_to_panel(self.ns, "text", content=t),
            on_thinking=lambda t: send_thinking(t))
        send_to_panel(self.ns, "text", content="\n")

        if raw.strip():
            result = parse(raw)
            if auto:
                self._auto_pending += len(result.code_list)
            render_output(self.ns, result, auto=auto, trace=False, on_cell_id=_on_cid)
            if auto and self._auto_pending == 0:
                self._busy = False
                send_to_panel(self.ns, "ready")
            label = "✓ plan implemented\n" if auto else "✓ plan accepted (code cells generated)\n"
            send_to_panel(self.ns, "text", content=label)
        else:
            send_to_panel(self.ns, "text", content="✗ plan implementation failed (no output)\n")
            if auto:
                self._busy = False
                send_to_panel(self.ns, "ready")

    def _split_at_trace(self, code: str) -> tuple[str, int]:
        """Return (code_before, idx) of _TRACE_MARKER in *code*."""
        idx = code.find(_TRACE_MARKER)
        if idx < 0:
            return code, -1
        return code[:idx].strip(), idx

    def _trace_on_error(self, code: str, error_msg: str) -> None:
        auto = "--auto" in code
        code_before, _ = self._split_at_trace(code)
        self.ns.track_cell(code_before, error=error_msg)
        if self._session_ready:
            HookRegistry.dispatch(HookEvent.AGENT_CELL_REVIEW, {
                "ns": self.ns, "auto": auto,
            }, session=self._session)

    # ---- agent_config ----

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
            self._plan = True; args.remove("--plan")
        if "--no-plan" in args:
            self._plan = False; args.remove("--no-plan")
        env_vars = parse_kv(args)

        # hook enable/disable (repeatable flags)
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

        cfg = load_yaml_config(config_path)
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

        agent = resolved["agent"]
        timeout = resolved["timeout"]
        claude_md_path = resolved["claude_md"]
        self._hook_cfg = resolved["hook_cfg"]
        self._tools_cfg = resolved["tools_cfg"]

        if agent not in _AGENTS:
            render_error(f"[agent_config] unknown agent '{agent}', valid: {', '.join(sorted(_AGENTS))}")
            agent = self._agent

        if resolved["session_rebuild"]:
            if self._session_ready:
                self._session.cleanup()
            self._init_session(agent, timeout, claude_md_path)
            self._session_ready = True
        elif timeout != self._timeout:
            if self._session_ready and self._session.client is not None:
                self._session.client._backend._timeout = timeout

        self._agent = agent
        self._timeout = timeout
        self._claude_md_path = claude_md_path
        render_info(f"agent: {self._agent}, timeout: {self._timeout}s")

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
