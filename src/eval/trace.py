"""TraceCollector — collects process trace data from agent streaming."""

from chat.base import StreamChunk


class TraceCollector:
    """Collects thinking, tool_use, subagent, and usage data from StreamChunks.

    Usage::

        collector = TraceCollector()
        for chunk in backend.stream_chunks(content, session):
            collector.feed(chunk)
            if chunk.text:
                print(chunk.text, end="")

        collector.attach(eval_result)  # writes trace to result.grade_detail["trace"]
    """

    def __init__(self) -> None:
        self.thinking: list[dict] = []
        self.tool_calls: list[dict] = []
        self.subagent_tasks: dict[str, dict] = {}
        self.usage: list[dict] = []

    def feed(self, chunk: StreamChunk) -> None:
        if not chunk.blocks:
            return
        for b in chunk.blocks:
            if b.type == "thinking":
                self.thinking.append(b.data or {})
            elif b.type in ("tool_use", "tool_result"):
                self.tool_calls.append(
                    {"type": b.type, **(b.data or {})}
                )
            elif b.type == "subagent" and b.data:
                task_id = b.data.get("task_id", "")
                if task_id not in self.subagent_tasks:
                    self.subagent_tasks[task_id] = {
                        "task_id": task_id,
                        "events": [],
                    }
                self.subagent_tasks[task_id]["events"].append(b.data)
            elif b.type == "usage":
                self.usage.append(b.data or {})

    def attach(self, result) -> None:
        """Write collected trace data to ``result.grade_detail["trace"]``."""
        if result.grade_detail is None:
            result.grade_detail = {}
        result.grade_detail["trace"] = self.to_dict()

    def to_dict(self) -> dict:
        d: dict = {}
        if self.thinking:
            d["thinking"] = self.thinking
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        if self.subagent_tasks:
            d["subagent_tasks"] = list(self.subagent_tasks.values())
        if self.usage:
            d["usage"] = self.usage
        return d
