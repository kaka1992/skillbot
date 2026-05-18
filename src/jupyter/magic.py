"""%%agent / %%sql cell magics — thin scheduling layer."""

import logging
import os
import shlex
import sys
import time
from pathlib import Path

from IPython.core.magic import Magics, cell_magic, line_magic, magics_class

from .agent_session import (
    SYSTEM_PROMPT,
    init_session,
    get_session_id,
    stream_output,
)
from .config import (
    pop_flag,
    parse_kv,
    load_yaml_config,
    load_tools,
    apply_preferences,
    set_debug,
    sql_progress as _sql_progress,
)
from .namespace import Namespace
from .parser import parse
from .render import render_output
from .review import parse_review_result, review_line_trace, review_task
from .dsl.sql import SqlRunner

_log = logging.getLogger(__name__)


@magics_class
class AgentMagic(Magics):
    _agent = "claude-code"
    _timeout = 600
    _claude_md_path: str | None = None
    _tools_cfg: dict = {}

    def __init__(self, shell):
        super().__init__(shell)
        self.ns = Namespace(shell)
        init_session(self._agent, self._timeout)
        self.ns.delta()
        self._sql_var_counter = 0
        shell.events.register("post_run_cell", self._on_cell_run)

    def _on_cell_run(self, result):
        info = getattr(result, "info", None)
        if info is None:
            return
        code = getattr(info, "raw_cell", "")
        if not code or code.startswith("%%agent") or code.startswith("%agent"):
            return
        output = str(info.result) if getattr(info, "result", None) else ""
        self.ns.track_cell(code.strip(), output.strip())

    def _next_sql_var(self) -> str:
        self._sql_var_counter += 1
        return f"var_{self._sql_var_counter}"

    # ---- agent_config ----

    @line_magic
    def agent_config(self, line: str) -> None:
        """%agent_config [--config PATH] [--agent NAME] [--timeout N] [--claude-md PATH] [--debug] [--KEY=VALUE ...]"""
        args = shlex.split(line)

        config_path = pop_flag(args, "--config")
        agent = pop_flag(args, "--agent")
        timeout = pop_flag(args, "--timeout", convert=int)
        claude_md_path = pop_flag(args, "--claude-md")
        debug = "--debug" in args
        if debug:
            args.remove("--debug")
        if "--no-debug" in args:
            args.remove("--no-debug")
            debug = False
        env_vars = parse_kv(args)

        cfg = load_yaml_config(config_path)

        cfg_debug = cfg.get("debug", False)
        set_debug(debug or cfg_debug)

        agent = agent or cfg.get("agent") or self._agent
        timeout = timeout or cfg.get("timeout") or self._timeout
        claude_md_path = claude_md_path or cfg.get("claude_md")

        merged_env = {**(cfg.get("env") or {}), **env_vars}

        from chat import _AGENTS
        if agent not in _AGENTS:
            print(f"[agent_config] unknown agent '{agent}', valid: {', '.join(sorted(_AGENTS))}",
                  file=sys.stderr)
            agent = self._agent

        # inject env first (tools may depend on env vars)
        if merged_env:
            os.environ.update({k: str(v) for k, v in merged_env.items()})

        # tools: always incremental (never triggers session rebuild)
        tools_cfg = cfg.get("tools") or {}
        load_tools(tools_cfg)
        apply_preferences(tools_cfg.get("preferences") or {})

        # session rebuild: only when agent or CLAUDE.md changes
        session_rebuild = (
            agent != self._agent or claude_md_path != self._claude_md_path
        )
        if session_rebuild:
            init_session(agent, timeout, claude_md_path=claude_md_path)
        elif timeout != self._timeout:
            cl = get_client()
            if cl is not None:
                cl._backend._timeout = timeout

        self._agent = agent
        self._timeout = timeout
        self._claude_md_path = claude_md_path
        self._tools_cfg = tools_cfg
        print(f"agent: {self._agent}, timeout: {self._timeout}s")

    # ---- %sql (line magic) ----

    @line_magic
    def sql(self, line: str) -> None:
        """%sql status|result|cancel [options] — manage Spark query jobs."""
        args = shlex.split(line)
        sub = args[0] if args else ""
        job_id = pop_flag(args, "--job_id")
        limit = pop_flag(args, "--limit", convert=int) or 100

        if not job_id:
            print("\033[91m--job_id is required\033[0m", file=sys.stderr)
            return

        runner = SqlRunner()
        try:
            if sub == "status":
                result = runner.status(job_id)
                data = result.get("data", {})
                print(f"job_id: {data.get('job_id', job_id)}")
                print(f"status: {data.get('status', '?')}")
                print(f"engine:  {data.get('engine_type', '?')}")
            elif sub == "cancel":
                result = runner.cancel(job_id)
                data = result.get("data", {})
                requested = data.get("cancel_requested", "false")
                print(f"job_id: {data.get('job_id', job_id)}  cancel_requested: {requested}")
            elif sub == "result":
                import pandas as pd
                var_name = pop_flag(args, "--var") or f"result_{job_id[:8]}"
                result = runner.result(job_id, limit=limit)
                data = result.get("data", {})
                sample = data.get("sample_data", [])
                # print preview from sample_data
                if sample and len(sample) > 1:
                    cols = sample[0] if sample else []
                    print(f"[{var_name}] preview: {len(sample)-1} rows x {len(cols)} cols")
                    if cols:
                        print(f"  columns: {', '.join(str(c) for c in cols)}")
                    for row in sample[1:4]:
                        print(f"  [{', '.join(str(v) for v in row)}]")
                # load from CSV output_path
                output_path = data.get("output_path", "")
                if output_path and Path(output_path).is_file():
                    df = pd.read_csv(output_path)
                    self.ns.inject(var_name, df)
                    print(f"[{var_name}] loaded from {output_path}: {len(df)} rows x {len(df.columns)} cols")
                elif sample and len(sample) > 1:
                    cols = sample[0] if sample else []
                    rows = sample[1:] if len(sample) > 1 else []
                    df = pd.DataFrame(rows, columns=cols)
                    self.ns.inject(var_name, df)
                    print(f"[{var_name}] {len(rows)} rows x {len(cols)} cols (from sample)")
                else:
                    print(f"\033[91m[{var_name}] no data available\033[0m", file=sys.stderr)
            else:
                print(f"\033[91munknown subcommand: {sub}. Use: status | cancel | result\033[0m",
                      file=sys.stderr)
        except RuntimeError as e:
            print(f"\033[91m{e}\033[0m", file=sys.stderr)

    # ---- %%sql (cell magic) ----

    @cell_magic
    def sql(self, line: str, cell: str) -> None:
        """%%sql [--var NAME] [--timeout N] [--poll N] | submit | result --job_id ID [--limit N]"""
        import pandas as pd
        args = shlex.split(line)
        mode = args[0] if args and not args[0].startswith("--") else "query"

        if mode == "submit":
            try:
                result = SqlRunner().submit(cell)
                job_id = result.get("data", {}).get("job_id", "")
                _log.info("sql submit: job_id=%s sql=%.100s", job_id, cell)
                print(f"job submitted: {job_id}")
            except RuntimeError as e:
                print(f"\033[91m{e}\033[0m", file=sys.stderr)
        elif mode == "result":
            job_id = pop_flag(args, "--job_id")
            limit = pop_flag(args, "--limit", convert=int) or 100
            var_name = pop_flag(args, "--var") or f"result_{job_id[:8]}"
            if not job_id:
                print("\033[91m--job_id is required\033[0m", file=sys.stderr)
                return
            try:
                result = SqlRunner().result(job_id, limit=limit)
                data = result.get("data", {})
                sample = data.get("sample_data", [])
                # print preview from sample_data
                if sample and len(sample) > 1:
                    cols = sample[0] if sample else []
                    print(f"[{var_name}] preview: {len(sample)-1} rows x {len(cols)} cols")
                    if cols:
                        print(f"  columns: {', '.join(str(c) for c in cols)}")
                    for row in sample[1:4]:
                        print(f"  [{', '.join(str(v) for v in row)}]")
                # load from CSV output_path
                output_path = data.get("output_path", "")
                if output_path and Path(output_path).is_file():
                    df = pd.read_csv(output_path)
                    self.ns.inject(var_name, df)
                    print(f"[{var_name}] loaded from {output_path}: {len(df)} rows x {len(df.columns)} cols")
                elif sample and len(sample) > 1:
                    cols = sample[0] if sample else []
                    rows = sample[1:] if len(sample) > 1 else []
                    df = pd.DataFrame(rows, columns=cols)
                    self.ns.inject(var_name, df)
                    print(f"[{var_name}] {len(rows)} rows x {len(cols)} cols (from sample)")
                else:
                    print(f"\033[91m[{var_name}] no data available\033[0m", file=sys.stderr)
            except RuntimeError as e:
                print(f"\033[91m{e}\033[0m", file=sys.stderr)
        else:
            var_name = pop_flag(args, "--var")
            timeout = pop_flag(args, "--timeout", convert=int) or 600
            poll = pop_flag(args, "--poll", convert=int) or 30
            runner = SqlRunner(poll_interval=poll, timeout=timeout)
            try:
                result = runner.query(cell, on_progress=_sql_progress)
                data = result.get("data", {})
                sample = data.get("sample_data", [])
                if sample:
                    cols = sample[0] if sample else []
                    rows = sample[1:] if len(sample) > 1 else []
                    df = pd.DataFrame(rows, columns=cols)
                    if not var_name:
                        var_name = self._next_sql_var()
                    self.ns.inject(var_name, df)
                    _log.info("sql query: var=%s rows=%d sql=%.100s", var_name, len(rows), cell)
                    print(f"[{var_name}] {len(rows)} rows x {len(cols)} cols")
            except (RuntimeError, TimeoutError) as e:
                _log.error("sql query error: %s", e)
                print(f"\033[91m{e}\033[0m", file=sys.stderr)

    # ---- %%agent (cell magic) ----

    @cell_magic
    def agent(self, line: str, cell: str) -> None:
        """%%agent [--timeout N] [--code] [--trace] [--auto]"""
        timeout = self._timeout
        code_only = False
        trace = False
        auto = False
        args = shlex.split(line)
        i = 0
        while i < len(args):
            if args[i] == "--timeout" and i + 1 < len(args):
                timeout = int(args[i + 1]); i += 2
            elif args[i] == "--code":
                code_only = True; i += 1
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
        session = get_session_id()

        t0 = time.time()
        raw = ""
        try:
            raw = stream_output(prompt, timeout, show_text=code_only)
        except Exception as e:
            _log.error("agent error: session=%s elapsed=%.1fs error=%s",
                       session, round(time.time() - t0, 1), e)
            print(f"\033[91mError: {e}\033[0m")
            if trace and auto:
                retry_cell = (
                    f"%%agent --trace --auto\n"
                    f"# Fix the error and retry:\n# {str(e)[:200]}\n{cell}"
                )
                self.ns.set_next_input(retry_cell)
                _log.info("trace: auto retry cell after error")
            return

        elapsed = round(time.time() - t0, 1)
        _log.info("agent done: session=%s elapsed=%.1fs output=%d chars trace=%s auto=%s",
                  session, elapsed, len(raw), trace, auto)
        _log.debug("agent output:\n%s", raw[:5000])

        has_new_cell = False
        if raw.strip():
            try:
                result = parse(raw)
                _log.debug("agent parse: text=%d chars files=%d code=%d chars",
                          len(result.text or ""), len(result.files),
                          len(result.code or ""))
            except ValueError as e:
                _log.warning("agent parse error: %s", e)
                print(f"\033[91mParse error: {e}\033[0m")
                return
            render_output(self.ns, result, skip_text=code_only, inject_code=code_only)
            has_new_cell = bool(result.code)

        self.ns.track_cell(cell, raw.strip()[:200])

        # ---- trace post-execution ----
        if not trace:
            return

        agent_output = raw.strip()[:2000] if raw.strip() else "(no output)"

        if has_new_cell:
            new_code = self.ns._next_input or ""
            if new_code and "%agent --trace" not in new_code:
                suffix = "%agent --trace --auto" if auto else "%agent --trace"
                self.ns.set_next_input(new_code + "\n" + suffix)
            _log.info("trace: new cell with %%agent --trace marker")
            print(f"[trace] new cell with %agent --trace")
        else:
            result = review_task(
                cell, agent_output,
                variables=self.ns.vars(),
                cells=self.ns._cells,
                timeout=self._timeout,
                auto=auto,
            )
            if result == "NOT_SOLVED":
                mode = "--trace --auto" if auto else "--trace"
                retry_cell = f"%%agent {mode}\n# Fix: {agent_output[:200]}\n{cell}"
                self.ns.set_next_input(retry_cell)
                _log.info("trace: retry cell generated")
                print("[trace] retry cell generated")

    # ---- %agent (line magic) ----

    @line_magic
    def agent(self, line: str) -> None:
        """%agent --trace [--auto] — trigger trace review from current cell."""
        args = shlex.split(line)
        trace = "--trace" in args
        auto = "--auto" in args

        if not trace:
            print("[agent] use %agent --trace to trigger trace review", file=sys.stderr)
            return

        code_before = self.ns.flush_current_cell()
        if not code_before:
            print("[trace] no cell content found before %agent --trace", file=sys.stderr)
            return

        delta = self.ns.delta()
        variables = str({k: type(v).__name__ for k, v in self.ns.vars().items()})

        try:
            raw = review_line_trace(delta, variables, self._timeout)
            result = parse_review_result(raw)
            if result == "NOT_SOLVED":
                mode = "--trace --auto" if auto else "--trace"
                fix = raw.strip()[:500]
                retry_cell = f"%%agent {mode}\n# Review: {fix}\n"
                self.ns.set_next_input(retry_cell)
                _log.info("trace: review cell from line magic")
                print("[trace] review cell generated")
            elif result == "SOLVED":
                print("[trace] ✓ SOLVED")
                _log.info("trace: SOLVED from line magic")
            else:
                print(f"[trace] ? {raw[:200]}")
        except Exception as e:
            print(f"\033[91m[trace] error: {e}\033[0m", file=sys.stderr)
            _log.error("trace line magic error: %s", e)
