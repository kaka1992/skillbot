"""%%agent cell magic — call agent from Jupyter with streaming progress."""

import os
import shlex
import yaml
import sys
import time
from datetime import datetime
from pathlib import Path

from IPython.core.magic import Magics, cell_magic, line_magic, magics_class

from .namespace import Namespace
from .sql import SqlRunner
from .parser import parse
from .render import render_output
from tools import ToolRegistry

from .agent_session import (
    SYSTEM_PROMPT,
    init_session as _init_session,
    get_client,
    get_session_id,
    stream_output as _stream_output,
    _session_id,
)

from .config import pop_flag as _pop_flag, parse_kv as _parse_kv, sql_progress as _sql_progress, load_yaml_config, load_third_party_tools, apply_preferences, set_debug


_LOG_DIR = Path(__file__).resolve().parents[2] / ".run"
_LOG_DIR.mkdir(parents=True, exist_ok=True)


def _log_agent(session: str, vars_: list[str], cells: list[dict],
               prompt: str, result: str, elapsed: float, error: str = "") -> None:
    """Write a human-readable log entry."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_file = _LOG_DIR / f"agent-{datetime.now().strftime('%Y%m%d')}.log"

    lines = [
        f"{'='*60}",
        f"  [{ts}]  session={session}  elapsed={elapsed:.1f}s",
        f"{'='*60}",
    ]
    if vars_:
        lines.append(f"  variables: {', '.join(vars_)}")
    if cells:
        lines.append(f"  cell history ({len(cells)} total):")
        for c in cells[-3:]:
            code = c["code"][:120].replace("\n", "\\n")
            lines.append(f"    › {code}")
            if c.get("output"):
                out = c["output"][:100].replace("\n", "\\n")
                lines.append(f"      → {out}")
    lines.append(f"  {'─'*50}")
    lines.append(f"  prompt: {prompt[:300]}")
    if error:
        lines.append(f"  ERROR: {error}")
    if result:
        lines.append(f"  result ({len(result)} chars):")
        for rline in result[:2000].split("\n")[:30]:
            lines.append(f"    {rline}")
    lines.append("")

    with open(log_file, "a", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ---- magic ----

@magics_class
class AgentMagic(Magics):
    _agent = "claude-code"
    _timeout = 600

    def __init__(self, shell):
        super().__init__(shell)
        self._sql_var_counter = 0
        self.ns = Namespace(shell)
        _init_session(self._agent, self._timeout)
        self.ns.delta()  # establish baseline snapshot
        # track ALL cell executions (not just %%agent)
        shell.events.register("post_run_cell", self._on_cell_run)

    def _next_sql_var(self) -> str:
        """Return next default variable name (var_1, var_2, ...)."""
        self._sql_var_counter += 1
        return f"var_{self._sql_var_counter}"

    def _on_cell_run(self, result):
        """Hook: capture cell code + output for namespace context."""
        info = getattr(result, "info", None)
        if info is None:
            return
        code = getattr(info, "raw_cell", "")
        if not code or code.startswith("%%agent") or code.startswith("%agent"):
            return
        output = str(info.result) if getattr(info, "result", None) else ""
        self.ns.track_cell(code.strip(), output.strip())

    @line_magic
    def agent_config(self, line: str) -> None:
        """Configure agent: %agent_config [--config PATH] [--agent NAME] [--timeout N] [--KEY=VALUE ...]"""
        args = shlex.split(line)

        # 1. 解析命令行参数
        config_path = _pop_flag(args, "--config")
        agent = _pop_flag(args, "--agent")
        timeout = _pop_flag(args, "--timeout", convert=int)
        env_vars = _parse_kv(args)

        # 2. 加载 YAML（命令行未指定时使用默认值）
        cfg: dict = {}
        if config_path:
            try:
                cfg = yaml.safe_load(Path(config_path).read_text()) or {}
            except FileNotFoundError:
                print(f"[agent_config] config file not found: {config_path}", file=sys.stderr)
            except yaml.YAMLError as e:
                print(f"[agent_config] YAML parse error: {e}", file=sys.stderr)

        # 2.5. 加载第三方 tools + 设定偏好
        tools_cfg = cfg.get("tools") or {}
        for path in tools_cfg.get("paths") or []:
            try:
                discovered = ToolRegistry.discover(path)
                if discovered:
                    names = ", ".join(t.name for t in discovered)
                    print(f"[agent_config] loaded from {path}: {names}")
            except Exception as e:
                print(f"[agent_config] failed to load tools from {path}: {e}", file=sys.stderr)

        preferences = tools_cfg.get("preferences") or {}
        for preset_name, impl_name in (preferences.get("presets") or {}).items():
            try:
                ToolRegistry.set_preferred(preset_name, impl_name)
            except KeyError as e:
                print(f"[agent_config] preference error: {e}", file=sys.stderr)
        for group_name, impl_name in (preferences.get("groups") or {}).items():
            try:
                ToolRegistry.set_preferred_for_group(group_name, impl_name)
            except KeyError as e:
                print(f"[agent_config] preference error: {e}", file=sys.stderr)

        agent = agent or cfg.get("agent") or self._agent
        timeout = timeout or cfg.get("timeout") or self._timeout

        # 合并 YAML env + CLI KV（后者覆盖前者）
        merged_env: dict = {**(cfg.get("env") or {}), **env_vars}

        # agent 合法性检查
        from chat import _AGENTS

        if agent not in _AGENTS:
            print(f"[agent_config] unknown agent '{agent}', valid: {', '.join(sorted(_AGENTS))}", file=sys.stderr)
            agent = self._agent

        # 3. 注入 env + 重建 session
        if merged_env:
            os.environ.update({k: str(v) for k, v in merged_env.items()})

        changed = agent != self._agent or timeout != self._timeout
        self._agent = agent
        self._timeout = timeout
        if changed:
            _init_session(self._agent, self._timeout)
        print(f"agent: {self._agent}, timeout: {self._timeout}s")

    @line_magic
    def sql(self, line: str) -> None:
        """%sql status|result|cancel [options] — manage Spark query jobs."""
        args = shlex.split(line)
        sub = args[0] if args else ""
        job_id = _pop_flag(args, "--job_id")
        limit = _pop_flag(args, "--limit", convert=int) or 100

        if not job_id:
            print("\033[91m--job_id is required\033[0m", file=sys.stderr)
            return

        runner = SqlRunner()
        try:
            if sub == "status":
                result = runner.status(job_id, on_progress=_sql_progress)
                data = result.get("data", {})
                print(f"job_id: {data.get('job_id', job_id)}")
                print(f"status: {data.get('status', '?')}")
                print(f"engine:  {data.get('engine_type', '?')}")
            elif sub == "cancel":
                result = runner.cancel(job_id, on_progress=_sql_progress)
                data = result.get("data", {})
                requested = data.get("cancel_requested", "false")
                print(f"job_id: {data.get('job_id', job_id)}  cancel_requested: {requested}")
            elif sub == "result":
                import pandas as pd
                result = runner.result(job_id, limit=limit)
                data = result.get("data", {})
                sample = data.get("sample_data", [])
                if sample:
                    cols = sample[0] if sample else []
                    rows = sample[1:] if len(sample) > 1 else []
                    df = pd.DataFrame(rows, columns=cols)
                    var_name = f"result_{job_id[:8]}"
                    self.ns.inject(var_name, df)
                    print(f"[{var_name}] {len(rows)} rows x {len(cols)} cols")
            else:
                print(f"\033[91munknown subcommand: {sub}. Use: status | cancel | result\033[0m",
                      file=sys.stderr)
        except RuntimeError as e:
            print(f"\033[91m{e}\033[0m", file=sys.stderr)

    @cell_magic
    def sql(self, line: str, cell: str) -> None:
        """%%sql — Spark SQL query in Jupyter.

        Usage::

            %%sql [--var df1] [--timeout 600] [--poll 30]
            select * from table

            %%sql submit
            select * from table

            %%sql result --job_id xxx [--limit 100]
        """
        import pandas as pd

        args = shlex.split(line)
        mode = args[0] if args and not args[0].startswith("--") else "query"

        runner = SqlRunner()

        if mode == "submit":
            try:
                result = runner.submit(cell, on_progress=_sql_progress)
                job_id = result.get("data", {}).get("job_id", "")
                print(f"job submitted: {job_id}")
            except RuntimeError as e:
                print(f"\033[91m{e}\033[0m", file=sys.stderr)

        elif mode == "result":
            job_id = _pop_flag(args, "--job_id")
            limit = _pop_flag(args, "--limit", convert=int) or 100
            if not job_id:
                print("\033[91m--job_id is required\033[0m", file=sys.stderr)
                return
            try:
                result = runner.result(job_id, limit=limit)
                data = result.get("data", {})
                sample = data.get("sample_data", [])
                if sample:
                    cols = sample[0] if sample else []
                    rows = sample[1:] if len(sample) > 1 else []
                    df = pd.DataFrame(rows, columns=cols)
                    var_name = f"result_{job_id[:8]}"
                    self.ns.inject(var_name, df)
                    print(f"[{var_name}] {len(rows)} rows x {len(cols)} cols")
            except RuntimeError as e:
                print(f"\033[91m{e}\033[0m", file=sys.stderr)

        else:  # mode == "query" (direct)
            var_name = _pop_flag(args, "--var")
            timeout = _pop_flag(args, "--timeout", convert=int) or 600
            poll = _pop_flag(args, "--poll", convert=int) or 30

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
                    print(f"[{var_name}] {len(rows)} rows x {len(cols)} cols")
            except (RuntimeError, TimeoutError) as e:
                print(f"\033[91m{e}\033[0m", file=sys.stderr)

    @cell_magic
    def agent(self, line: str, cell: str) -> None:
        timeout = self._timeout
        code_only = False
        args = shlex.split(line)
        i = 0
        while i < len(args):
            if args[i] == "--timeout" and i + 1 < len(args):
                timeout = int(args[i + 1]); i += 2
            elif args[i] == "--code":
                code_only = True; i += 1
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
            raw = _stream_output(prompt, timeout, show_text=code_only)
        except Exception as e:
            _log_agent(_session_id, sorted(self.ns.vars().keys()),
                       self.ns._cells, cell, "", round(time.time() - t0, 1),
                       error=str(e))
            print(f"\033[91mError: {e}\033[0m")
            return

        elapsed = round(time.time() - t0, 1)
        _log_agent(_session_id, sorted(self.ns.vars().keys()),
                   self.ns._cells, cell, raw, elapsed)

        if raw.strip():
            try:
                result = parse(raw)
            except ValueError as e:
                print(f"\033[91mParse error: {e}\033[0m")
                return
            render_output(self.ns, result, skip_text=code_only, inject_code=code_only)

        self.ns.track_cell(cell, raw.strip()[:200])
