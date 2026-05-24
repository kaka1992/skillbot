"""Agent-backed code review hook."""

import json
from uuid import uuid4

from hook.base import Hook
from hook.events import HookResult, HookStatus
from agent.session import AgentSession
from task import Task


class AgentCodeReviewHook(Hook):
    priority = 10

    def on_event(self, event: str, context: dict, session: AgentSession = None) -> HookResult:
        code_list = context.get("code_list", [])
        if not code_list or len(code_list) < 2:
            return HookResult(HookStatus.SUCCESS)

        prompt = (
            "Review these code cells for logic consistency.\n"
            "Fix variable name mismatches (e.g., SQL returns var_3 but Python uses var_1).\n"
            "Return ONLY the corrected code array in JSON:\n"
            f'{{"code": {code_list!r}}}\n'
            "Do NOT add explanations — only fix bugs."
        )
        if session is None:
            return HookResult(HookStatus.FAILED_CONTINUE, "", "no agent session available")

        try:
            task = Task(task_id=uuid4().hex[:8], subject="review: code_review",
                        metadata={"sub_name": "code_review", "prompt": prompt, "results": []})
            sub = session.get_sub("code_review")
            sub.execute(task)
            raw = task.metadata["results"][0] if task.metadata["results"] else ""
        except Exception:
            return HookResult(HookStatus.FAILED_CONTINUE, "", "code review agent call failed")

        fixed = json.loads(raw.strip()) if raw.strip().startswith("{") else {"code": code_list}
        new_list = fixed.get("code", code_list)
        if isinstance(new_list, str):
            new_list = [new_list]
        new_list = [str(c) for c in new_list if str(c).strip()]

        if new_list != code_list:
            import difflib
            from jupyter.render import render_info
            lines: list[str] = ["[code review] changes:"]
            for i, (old, new) in enumerate(zip(code_list, new_list)):
                if old != new:
                    diff = difflib.unified_diff(
                        old.splitlines(keepends=True),
                        new.splitlines(keepends=True),
                        fromfile=f"cell {i + 1} (old)",
                        tofile=f"cell {i + 1} (new)",
                        lineterm="",
                    )
                    lines.extend(diff)
            render_info("\n".join(lines))

        context["code_list"] = new_list
        return HookResult(HookStatus.SUCCESS, "", f"code review: {len(new_list)} cells")
