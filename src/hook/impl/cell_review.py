"""Agent cell review hook — review agent output after %%agent / %agent execution."""

import logging
from json import dumps

from agent.session import AgentSession
from hook.base import Hook
from hook.events import HookResult, HookStatus
from jupyter.parser import ParsedResult, parse_review_result
from jupyter.render import render_code, render_debug, render_info, render_output, _is_debug
from uuid import uuid4

from task import Task

_log = logging.getLogger(__name__)


CELL_REVIEW_TEMPLATE = """\
Review the progress of this Jupyter cell execution and return JSON:

{{"status": "NOT_SOLVED", "code": "fixed code", "reason": "..."}}
{{"status": "SOLVING", "code": "next step code", "reason": "..."}}
{{"status": "SOLVED", "text": "## Agent Review: SOLVED\\n\\n...", "reason": "..."}}

Context:
- Original cell: {raw_cell}
- Variables: {vars_summary}
{extra_context}

Rules:
- NOT_SOLVED: the task is blocked or failed. Provide fixed code and explain why.
- SOLVING: the task is progressing. Provide next step code and explain.
- SOLVED: the task is complete. {solved_rule}
"""


def _describe_vars(ns) -> str:
    return dumps({k: type(v).__name__ for k, v in ns.vars().items()})


def _build_prompt(ns, error: str, output: str, detail_level: str) -> str:
    extra = ""
    solved_rule = ""
    if detail_level == "detailed":
        extra = (
            "- Cell history: {cell_history}\n"
            "- Output: {output}"
        )
        solved_rule = (
            "Generate a detailed markdown summary including: "
            "original task, execution details, variable changes, "
            "generated files, and conclusion."
        )
    else:
        solved_rule = (
            "Generate a concise markdown summary (3-5 lines, "
            "## heading, bullet points for key results)."
        )

    cell_history = "\n".join(
        f"  {c['code'][:100]} -> {c.get('output', '')[:100]}"
        for c in (ns._cells or [])[-5:]
    ) or "(none)"
    raw_cell = (ns._cells[-1].get("code", "") if ns._cells else "")

    return CELL_REVIEW_TEMPLATE.format(
        raw_cell=raw_cell[:1000],
        vars_summary=_describe_vars(ns),
        extra_context=extra.format(
            cell_history=cell_history,
            output=output[:1000],
        ),
        solved_rule=solved_rule,
    )


class AgentCellReviewHook(Hook):
    """Agent cell review: review agent output after %%agent / %agent execution.

    Triggered when:
    - Agent output has no new cell → review whether task is SOLVED
    - SQL + trailing %agent → review SQL results
    - %agent --trace line magic → review partial cell progress
    - Cell code errored before %agent --trace → review error + suggest fix

    Context keys:
        ns:       Namespace — error sensed from ``ns._cells[-1]``
        auto:     bool — whether fix cells should auto-execute
        output:   agent original output (task review scenario, optional)
    """

    priority = 10

    def __init__(self, timeout: int = 600) -> None:
        self._timeout = timeout

    def on_event(self, event: str, context: dict, session: AgentSession = None) -> HookResult:
        ns = context["ns"]
        auto = context.get("auto", False)
        last_cell = ns._cells[-1] if ns._cells else {}

        # error comes from last cell; output from context OR last cell (SQL result)
        error = last_cell.get("error", "")
        output = context.get("output") or last_cell.get("output", "")

        detail_level = "detailed" if _is_debug() else "concise"
        prompt = _build_prompt(ns, error, output, detail_level)
        if session is None:
            return HookResult(HookStatus.FAILED_CONTINUE, "", "no agent session available")
        try:
            task = Task(task_id=uuid4().hex[:8], subject="review: cell_review",
                        metadata={"sub_name": "cell_review", "prompt": prompt,
                                  "context": ns.context(), "results": []})
            sub = session.get_sub("cell_review")
            sub.execute(task)
            raw = task.metadata["results"][0] if task.metadata["results"] else ""
        except Exception as e:
            _log.warning("AgentCellReviewHook: agent call failed: %s", e)
            return HookResult(HookStatus.FAILED_CONTINUE, "", str(e))

        review = parse_review_result(raw)
        status = review["status"]
        code = review["code"]

        # Inject code if agent provided one (SOLVING or SOLVED with install cmd etc.)
        if code:
            render_code(ns, code, auto=auto, trace=auto)
            render_info("[review] code from review injected")

        if status == "NOT_SOLVED":
            code_before = last_cell.get("code", "")
            reason = review.get("reason", raw.strip()[:500])
            fix = f"# Fix: {reason}\n{code_before}" if code_before else f"# Fix: {reason}"
            render_code(ns, fix, auto=auto, trace=True)
            ns.track_hook(f"[review] NOT_SOLVED → fix cell")
            render_info("[review] ✓ fix cell generated")
        elif status == "SOLVED":
            reason = review.get("reason", "")
            is_md = review.get("is_markdown", False)
            result = ParsedResult(
                text=review.get("text", ""),
                is_markdown=is_md,
            )
            render_output(ns, result)
            ns.track_hook(f"[review] SOLVED: {reason[:100]}")
        elif status == "SOLVING":
            reason = review.get("reason", "")
            ns.track_hook(f"[review] SOLVING: {reason[:100]}")
            render_info(f"[review] ✓ SOLVING: {reason[:200]}" if reason else "[review] ✓ code injected (solving)")
        else:
            ns.track_hook(f"[review] unexpected: {raw[:200]}")
            render_debug(f"[review] unexpected: {raw[:200]}")
        return HookResult(HookStatus.SUCCESS)

