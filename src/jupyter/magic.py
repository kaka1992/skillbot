"""%%agent / %%sql cell magics — thin scheduling layer."""

import hashlib
import logging
import os as _os
import shlex
import sys
import time
from pathlib import Path

from IPython.core.magic import Magics, cell_magic, line_magic, magics_class

from agent import AgentSession, SubAgentConfig
from agent.prompt import PromptBuilder
from chat import _AGENTS
from hook import HookGroup, HookRegistry, HookEvent
from jupyter.telemetry import get_recorder, TelemetryRecorder, set_recorder
from .config import pop_flag, parse_kv, configure_agent, load_yaml_config
from .feedback import parse_feedback_line
from .namespace import Namespace
from .parser import parse, traceback_line
from .render import render_debug, render_error, render_info, render_output, render_sql_dataframe, render_code, render_variables
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


def _extract_trailing_agent(cell: str) -> tuple[str, str]:
    """Split *cell* into (code_before, agent_line) if last line is ``%agent``."""
    lines = cell.split("\n")
    for i in reversed(range(len(lines))):
        stripped = lines[i].strip()
        if stripped:
            if stripped.startswith("%agent"):
                return "\n".join(lines[:i]).strip(), stripped
            break
    return cell, ""


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
        self.ns = Namespace(shell)
        cfg = load_yaml_config("conf/jupyter_agent.yaml")
        self._hook_cfg = cfg.get("hooks", {})
        self._init_session(self._agent, self._timeout, self._claude_md_path)
        rec = TelemetryRecorder(
            session_id=self._session.session_id,
            path=_os.path.join(".run", "sessions", f"{self._session.session_id}.jsonl"),
        )
        set_recorder(rec)
        self.ns.delta()
        shell.events.register("pre_run_cell", self._on_pre_run_cell)
        shell.events.register("post_run_cell", self._on_cell_run)

    def _init_session(self, agent: str, timeout: int, claude_md: str | None = None) -> None:
        self._session = AgentSession(agent, timeout)
        self._session.configure_subs(SUB_AGENT_DEFAULTS)
        self._session.init_session(
            system_prompt=_merge_prompt(claude_md),
            session_key=_session_key(),
            on_init=lambda s: _register_hooks(timeout, self._hook_cfg),
        )

    def _on_pre_run_cell(self, info):
        self._raw_cell = getattr(info, "raw_cell", "")

    def _on_cell_run(self, result):
        info = getattr(result, "info", None)
        if info is None:
            return
        code = getattr(info, "raw_cell", "")
        if not code:
            return

        # %%sql + trailing %agent → dispatch (sql() already tracked result)
        if code.startswith("%%sql") and "%agent" in code:
            HookRegistry.dispatch(HookEvent.AGENT_CELL_REVIEW, {
                "ns": self.ns, "auto": "--auto" in code,
            }, session=self._session)
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

        if code.startswith("%%agent") or code.startswith("%agent"):
            return

        output = str(info.result) if getattr(info, "result", None) else ""
        self.ns.track_cell(code.strip(), output.strip())

        rec = get_recorder()
        if rec:
            cell_type = "plain"
            if code.startswith("%%agent"): cell_type = "%%agent"
            elif code.startswith("%agent"): cell_type = "%agent"
            elif code.startswith("%%sql"): cell_type = "%%sql"
            error = getattr(result, "error_in_exec", None) or getattr(result, "error_before_exec", None)
            rec.record("cell_executed",
                cell_id="",
                type=cell_type,
                code=code[:2000],
                output=output[:2000],
                error=str(error)[:2000] if error else None,
                elapsed=0.0,
            )

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
        HookRegistry.dispatch(HookEvent.AGENT_CELL_REVIEW, {
            "ns": self.ns, "auto": auto,
        }, session=self._session)

    def _flush_current_cell(self) -> str:
        code = getattr(self, "_raw_cell", "")
        if not code:
            return ""
        code_before, idx = self._split_at_trace(code)
        if idx < 0:
            return ""
        if code_before:
            self.ns.track_cell(code_before, "")
        return code_before


    # ---- %feedback / %fb ----

    @line_magic("fb")
    def fb_fuc(self, line: str) -> None:
        """%fb yes|no [--comment '...'] — confirm whether agent output meets expectation."""
        self.feedback_func(line)

    @line_magic("feedback")
    def feedback_func(self, line: str) -> None:
        """%feedback yes|no [--comment '...'] — short: %fb."""
        result, comment = parse_feedback_line(line)
        if result is None:
            render_error("Usage: %feedback yes|no [--comment '...']")
            return

        rec = get_recorder()
        if rec:
            rec.record("feedback", result=result, comment=comment)

        label = "meets expectation" if result == "yes" else "does not meet expectation"
        render_info(f"[feedback] {label}" + (f" — {comment}" if comment else ""))

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
            self._session.cleanup()
            self._init_session(agent, timeout, claude_md_path)
        elif timeout != self._timeout:
            if self._session.client is not None:
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
        # Detect %agent on last non-empty line → SQL first, then agent trace
        cell, _trailing_agent = _extract_trailing_agent(cell)
        _has_trailing_agent = bool(_trailing_agent)

        mode = args[0] if args and not args[0].startswith("--") else "query"

        sql_output = ""
        sql_error = ""

        if mode == "submit":
            try:
                result = SqlRunner().submit(cell)
                job_id = result.get("data", {}).get("job_id", "")
                render_info(f"job submitted: {job_id}")
                sql_output = f"[SQL] submitted: {job_id}"
            except RuntimeError as e:
                render_error(f"{e}")
                sql_error = str(e)
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
                    preview = df.head(3).to_string(max_rows=3, max_cols=5)
                    sql_output = f"[SQL] {var_name}: {len(df)} rows\n{preview}"
                else:
                    render_error("sql query returned no data")
                    _log.error(f"sql={cell[:500]}")
                    sql_error = "sql query returned no data"
            except (RuntimeError, TimeoutError) as e:
                render_error(str(e))
                _log.error(f"sql query error: {e}")
                sql_error = str(e)

        if _has_trailing_agent:
            self.ns.track_cell(cell, output=sql_output, error=sql_error)

    # ---- %%agent (cell magic) ----

    @line_magic("agent")
    @cell_magic("agent")
    def agent_func(self, line: str, cell: str = None) -> None:
        """%%agent [--timeout N] [--trace] [--auto]  |  %agent --trace [--auto]"""
        if cell is None:
            self._agent_line_func(line)
            return

        timeout = self._timeout
        trace = False
        auto = False
        args = shlex.split(line)
        i = 0
        while i < len(args):
            if args[i] == "--timeout" and i + 1 < len(args):
                timeout = int(args[i + 1]); i += 2
            elif args[i] == "--trace":
                trace = True; i += 1
            elif args[i] == "--auto":
                auto = True; i += 1
            else:
                i += 1

        src = str(Path(__file__).resolve().parents[1])
        if src not in sys.path:
            sys.path.insert(0, src)

        ctx = self.ns.delta()
        prompt = f"{ctx}\n\n{cell}" if ctx else cell
        t0 = time.time()
        raw = ""
        try:
            raw = self._session.stream(prompt, timeout, show_text=True)
        except Exception as e:
            render_error(f"Error: {e}")
            _log.error(f"agent error session={self._session.session_id} elapsed={round(time.time()-t0,1)}s")
            if trace:
                render_code(self.ns, f"# Fix: {str(e)[:500]}\n{cell}", auto=auto, trace=True)
                render_info("[trace] auto retry after error" if auto else "[trace] retry cell generated")
            return

        elapsed = round(time.time() - t0, 1)

        rec = get_recorder()
        if rec:
            rec.record("agent_call",
                call_id="",
                cell_id="",
                prompt=prompt[:3000],
                raw_output=raw[:5000],
                tool_calls=[],
                thinking_summary="",
                elapsed=elapsed,
                parse_error=None,
            )

        render_info(f"agent done: elapsed={elapsed:.1f}s output={len(raw)} chars")

        render_debug(f"agent output: {len(raw)} chars")
        _log.debug(raw[:5000])

        has_new_cell = False
        if raw.strip():
            result = parse(raw)
            render_debug(
                f"agent parse: text={len(result.text or '')} chars files={len(result.files)} code={len(result.code_list)}")
            _log.debug(
                f"agent parse detail: text={len(result.text or '')} files={len(result.files)} code={len(result.code_list)}")
            render_output(self.ns, result, auto=auto, trace=trace)
            has_new_cell = bool(result.code_list)

        self.ns.track_cell(cell, raw.strip())

        # ---- trace post-execution ----
        if not trace:
            return

        agent_output = raw.strip()[:2000] if raw.strip() else "(no output)"

        if has_new_cell:
            render_info(f"[trace] new cell with %agent --trace")
        else:
            HookRegistry.dispatch(HookEvent.AGENT_CELL_REVIEW, {
                "ns": self.ns, "auto": auto, "output": agent_output,
            }, session=self._session)

    def _agent_line_func(self, line: str) -> None:
        """%agent --trace [--auto] — trigger trace review from current cell."""
        args = shlex.split(line)
        trace = "--trace" in args
        auto = "--auto" in args

        if not trace:
            render_error("use %agent --trace to trigger trace review")
            return

        code_before = self._flush_current_cell()
        if not code_before:
            render_error("[trace] no cell content found before %agent --trace")
            return

        from hook import HookRegistry, HookEvent
        HookRegistry.dispatch(HookEvent.AGENT_CELL_REVIEW, {
            "ns": self.ns, "auto": auto,
        }, session=self._session)
