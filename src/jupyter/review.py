"""Agent trace review — independent review call, SOLVED/NOT_SOLVED parsing."""

import logging
import sys

_log = logging.getLogger(__name__)


def review_task(task: str, agent_output: str, variables: dict, cells: list,
                timeout: int = 600, auto: bool = False) -> str | None:
    """Run independent review call.

    Returns 'SOLVED', 'NOT_SOLVED', or None on error.
    """
    from .agent_session import REVIEW_PROMPT, stream_output

    history = "\n".join(
        f"  {c['code'][:100]} -> {c.get('output', '')[:100]}"
        for c in (cells or [])[-10:]
    ) if cells else "(none)"
    var_summary = str({k: type(v).__name__ for k, v in (variables or {}).items()})

    prompt = REVIEW_PROMPT.format(
        task=task,
        history=history,
        variables=var_summary,
        output=agent_output[:2000],
    )

    try:
        raw = stream_output(prompt, timeout, show_text=False)
        result = raw.strip().upper()
        if "SOLVED" in result:
            print("[trace] ✓ SOLVED")
            _log.info("review: SOLVED task=%.100s", task)
            return "SOLVED"
        elif "NOT_SOLVED" in result:
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
