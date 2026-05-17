"""Agent trace review — independent review call, SOLVED/NOT_SOLVED parsing."""

import logging
import sys

_log = logging.getLogger(__name__)


def _review_prompt_line_trace(delta: str, variables: str) -> str:
    return f"""Analyze current progress:

## New Context Since Last Agent Call
{delta}

## Current Variables
{variables}

Based on the above, does the task need further action?
Reply ONLY: SOLVED: or NOT_SOLVED: <suggested next step>
"""


def _review_prompt_task(task: str, history: str, variables: str, output: str) -> str:
    from .agent_session import REVIEW_PROMPT
    return REVIEW_PROMPT.format(task=task, history=history, variables=variables, output=output)


def parse_review_result(raw: str) -> str | None:
    """Parse review output. Returns 'SOLVED', 'NOT_SOLVED', or None."""
    text = raw.strip().upper()
    if "NOT_SOLVED" in text:
        return "NOT_SOLVED"
    if "SOLVED" in text:
        return "SOLVED"
    return None


def review_line_trace(delta: str, variables: str, timeout: int) -> str:
    """Review from line magic — analyze progress since last agent call.
    Returns raw agent response text.
    """
    from .agent_session import stream_output
    prompt = _review_prompt_line_trace(delta, variables)
    return stream_output(prompt, timeout, show_text=False)


def review_task(task: str, agent_output: str, variables: dict, cells: list,
                timeout: int = 600, auto: bool = False) -> str | None:
    """Run independent review call.

    Returns 'SOLVED', 'NOT_SOLVED', or None on error.
    """
    from .agent_session import stream_output

    history = "\n".join(
        f"  {c['code'][:100]} -> {c.get('output', '')[:100]}"
        for c in (cells or [])[-10:]
    ) if cells else "(none)"
    var_summary = str({k: type(v).__name__ for k, v in (variables or {}).items()})

    prompt = _review_prompt_task(task, history, var_summary, agent_output[:2000])

    try:
        raw = stream_output(prompt, timeout, show_text=False)
        result = parse_review_result(raw)
        if result == "SOLVED":
            print("[trace] ✓ SOLVED")
            _log.info("review: SOLVED task=%.100s", task)
            return "SOLVED"
        elif result == "NOT_SOLVED":
            fix = raw.strip()[raw.strip().find("NOT_SOLVED"):][:500]
            print(f"[trace] ✗ {fix}")
            _log.info("review: NOT_SOLVED task=%.100s fix=%.200s", task, fix)
            return "NOT_SOLVED"
        else:
            print(f"[trace] ? unexpected: {raw[:200]}")
            _log.warning("review: unexpected response raw=%.200s", raw)
            return None
    except Exception as e:
        print(f"\033[91m[trace] review error: {e}\033[0m", file=sys.stderr)
        _log.error("review: error=%s", e)
        return None
