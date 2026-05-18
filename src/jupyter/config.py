"""AgentConfig — CLI + YAML configuration, tools loading, debug toggle."""

import logging
import os
import shlex
import sys
from pathlib import Path

_log = logging.getLogger(__name__)


def pop_flag(args: list[str], name: str, convert: type = str):
    """Pop ``name`` and its value from *args*, returning the converted value or None."""
    try:
        i = args.index(name)
    except ValueError:
        return None
    if i + 1 >= len(args):
        return None
    val = args.pop(i + 1)
    args.pop(i)
    if convert is int:
        return int(val)
    return val


def parse_kv(args: list[str]) -> dict[str, str]:
    """Parse remaining ``--KEY=VALUE`` items from *args*, returning a dict."""
    result = {}
    remaining = list(args)
    for item in args[:]:
        if item.startswith("--") and "=" in item:
            key, val = item[2:].split("=", 1)
            result[key] = val
            remaining.remove(item)
    args[:] = remaining
    return result


def sql_progress(phase: str, data: dict | None = None) -> None:
    """Print spark query progress to stdout with flush for real-time streaming."""
    if data is None:
        data = {}
    if phase == "analyze":
        plan = data.get("plan", "")
        print(f"\n[analyze] plan:\n{plan}")
    elif phase == "submit":
        print(f"[submit] job_id: {data.get('job_id', '')}")
    elif phase == "poll":
        status = data.get("status", "?")
        elapsed = data.get("elapsed", 0)
        print(f"\r[poll] {status} ({elapsed}s)  ", end="")
        sys.stdout.flush()
    elif phase == "result":
        print(f"\n[result] {data.get('row_count', 0)} rows fetched")
    elif phase == "error":
        print(f"\n\033[91m[{data.get('stage', '?')}] {data.get('message', '')}\033[0m",
              file=sys.stderr)
    elif phase == "submit_ok":
        print(f"[submit] job_id: {data.get('job_id', '')}")


def load_yaml_config(path: str | None) -> dict:
    """Load YAML config file. Returns empty dict on error."""
    if not path:
        return {}
    try:
        import yaml
        return yaml.safe_load(Path(path).read_text()) or {}
    except FileNotFoundError:
        print(f"[agent_config] config file not found: {path}", file=sys.stderr)
    except Exception as e:
        print(f"[agent_config] YAML parse error: {e}", file=sys.stderr)
    return {}


def load_tools(tools_cfg: dict) -> None:
    """Load builtin tools first, then third-party tool directories."""
    from pathlib import Path
    from tools import ToolRegistry

    # 1. Load builtin tools (always first)
    builtin_dir = str(Path(__file__).resolve().parents[3] / "src" / "tools" / "builtin")
    try:
        discovered = ToolRegistry.discover(builtin_dir)
        if discovered:
            names = ", ".join(t.name for t in discovered)
            _log.info("tools loaded: builtin=%s", names)
    except Exception as e:
        _log.warning("builtin tools load failed: %s", e)

    # 2. Load third-party paths
    for path in tools_cfg.get("paths") or []:
        try:
            discovered = ToolRegistry.discover(path)
            if discovered:
                names = ", ".join(t.name for t in discovered)
                print(f"[agent_config] loaded from {path}: {names}")
                _log.info("tools loaded: path=%s tools=%s", path, names)
        except Exception as e:
            print(f"[agent_config] failed to load tools from {path}: {e}", file=sys.stderr)
            _log.warning("tools load failed: path=%s error=%s", path, e)


def apply_preferences(preferences: dict) -> None:
    """Apply tool implementation preferences (preset_name → impl_name)."""
    from tools import ToolRegistry

    for preset_name, impl_name in (preferences or {}).items():
        try:
            ToolRegistry.set_preferred(preset_name, impl_name)
            _log.info("preference: preset=%s impl=%s", preset_name, impl_name)
        except KeyError as e:
            print(f"[agent_config] preference error: {e}", file=sys.stderr)


def set_debug(enabled: bool) -> None:
    """Set debug logging level for jupyter modules."""
    level = logging.DEBUG if enabled else logging.INFO
    logging.getLogger("jupyter").setLevel(level)
    _log.info("debug: %s", "ON" if enabled else "OFF")
