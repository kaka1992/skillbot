"""AgentConfig — CLI + YAML configuration, tools loading, debug toggle."""

import logging
import os
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
        args.pop(i)  # flag with no value — consume flag, return None
        return None
    val = args[i + 1]
    if val.startswith("-"):
        args.pop(i)  # next item is a flag — don't swallow it as our value
        return None
    del args[i + 1]
    del args[i]
    try:
        return convert(val)
    except (ValueError, TypeError):
        _log.warning("pop_flag: invalid value for %s: %r", name, val)
        return None


def parse_kv(args: list[str]) -> dict[str, str]:
    """Parse remaining ``--KEY=VALUE`` items from *args*, returning a dict."""
    result = {}
    for item in args[:]:
        if item.startswith("--") and "=" in item:
            key, val = item[2:].split("=", 1)
            result[key] = val
            args.remove(item)
    return result


def load_yaml_config(path: str | None) -> dict:
    """Load YAML config file. Returns empty dict on error."""
    if not path:
        return {}
    try:
        import yaml
        data = yaml.safe_load(Path(path).read_text()) or {}
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        print(f"[agent_config] config file not found: {path}", file=sys.stderr)
    except Exception as e:
        print(f"[agent_config] YAML parse error: {e}", file=sys.stderr)
    return {}


def _discover_dir(directory: str, label: str = "") -> None:
    """Discover tools from *directory*, logging results."""
    from tools import ToolRegistry

    discovered = ToolRegistry.discover(directory)
    if not discovered:
        return
    names = ", ".join(t.name for t in discovered)
    if label:
        print(f"[agent_config] loaded from {label}: {names}")
    _log.info("tools loaded: %s=%s", label or directory, names)


def load_tools(tools_cfg: dict) -> None:
    """Load builtin tools first, then third-party tool directories."""
    builtin_dir = str(Path(__file__).resolve().parents[2] / "src" / "tools" / "builtin")
    try:
        _discover_dir(builtin_dir, "builtin")
    except Exception as e:
        _log.warning("builtin tools load failed: %s", e)

    paths = tools_cfg.get("paths") if isinstance(tools_cfg.get("paths"), list) else []
    for path in paths:
        try:
            _discover_dir(path, path)
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


def configure_agent(
    config_path: str | None = None,
    cli_agent: str | None = None,
    cli_timeout: int | None = None,
    cli_claude_md: str | None = None,
    cli_debug: bool = False,
    cli_env: dict | None = None,
    enable_hooks: list[str] | None = None,
    disable_hooks: list[str] | None = None,
    *,
    defaults: dict,
    current_agent: str,
    current_timeout: int,
    current_claude_md: str | None,
    current_hook_cfg: dict,
) -> dict:
    """Resolve agent_config from CLI + YAML, inject env, load tools.

    Returns dict with keys: agent, timeout, claude_md, hook_cfg, tools_cfg,
    session_rebuild (bool).
    """
    cfg = load_yaml_config(config_path)

    cfg_debug = cfg.get("debug", False)
    set_debug(cli_debug or cfg_debug)

    agent = cli_agent or cfg.get("agent") or defaults.get("agent") or current_agent
    # explicit None checks so a falsy-but-valid 0 timeout is respected
    timeout = current_timeout
    if defaults.get("timeout") is not None:
        timeout = defaults["timeout"]
    if cfg.get("timeout") is not None:
        timeout = cfg["timeout"]
    if cli_timeout is not None:
        timeout = cli_timeout
    claude_md = cli_claude_md or cfg.get("claude_md") or current_claude_md

    # merge env: YAML base + CLI overrides
    cfg_env = cfg.get("env") if isinstance(cfg.get("env"), dict) else {}
    merged_env = {**cfg_env, **(cli_env or {})}
    if merged_env:
        os.environ.update({k: str(v) for k, v in merged_env.items()})

    # tools: always incremental (malformed YAML sections degrade gracefully)
    tools_cfg = cfg.get("tools") if isinstance(cfg.get("tools"), dict) else {}
    load_tools(tools_cfg)
    prefs = tools_cfg.get("preferences")
    apply_preferences(prefs if isinstance(prefs, dict) else {})

    # hook config: YAML base + CLI overrides
    hook_cfg = cfg.get("hooks") if isinstance(cfg.get("hooks"), dict) else {}
    if enable_hooks or disable_hooks:
        groups = hook_cfg.get("groups")
        if not isinstance(groups, dict):
            groups = hook_cfg["groups"] = {}
        for name in (enable_hooks or []):
            groups.setdefault(name, {})["enabled"] = True
        for name in (disable_hooks or []):
            groups.setdefault(name, {})["enabled"] = False

    session_rebuild = (
        agent != current_agent
        or claude_md != current_claude_md
    )

    return {
        "agent": agent,
        "timeout": timeout,
        "claude_md": claude_md,
        "hook_cfg": hook_cfg,
        "tools_cfg": tools_cfg,
        "session_rebuild": session_rebuild,
    }
