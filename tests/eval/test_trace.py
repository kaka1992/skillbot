"""Tests for TraceCollector."""

import pytest
from chat.base import StreamChunk, TraceBlock
from eval.trace import TraceCollector


class TestTraceCollector:
    def test_empty_collector(self):
        c = TraceCollector()
        assert c.to_dict() == {}

    def test_feed_thinking(self):
        c = TraceCollector()
        c.feed(StreamChunk(
            text="",
            blocks=[TraceBlock(type="thinking", data={"thinking": "hmm"})],
        ))
        d = c.to_dict()
        assert d["thinking"] == [{"thinking": "hmm"}]

    def test_feed_tool_calls(self):
        c = TraceCollector()
        c.feed(StreamChunk(blocks=[
            TraceBlock(type="tool_use", data={"id": "1", "name": "Bash", "input": {"cmd": "ls"}}),
            TraceBlock(type="tool_result", data={"tool_use_id": "1", "content": "ok"}),
        ]))
        d = c.to_dict()
        assert len(d["tool_calls"]) == 2
        assert d["tool_calls"][0]["type"] == "tool_use"
        assert d["tool_calls"][0]["name"] == "Bash"

    def test_feed_subagent_merges_by_task_id(self):
        c = TraceCollector()
        c.feed(StreamChunk(blocks=[
            TraceBlock(type="subagent", data={"task_id": "t1", "event": "started", "description": "test"}),
        ]))
        c.feed(StreamChunk(blocks=[
            TraceBlock(type="subagent", data={"task_id": "t1", "event": "progress", "last_tool_name": "Bash"}),
        ]))
        c.feed(StreamChunk(blocks=[
            TraceBlock(type="subagent", data={"task_id": "t1", "event": "completed", "summary": "done"}),
        ]))
        d = c.to_dict()
        tasks = d["subagent_tasks"]
        assert len(tasks) == 1
        assert tasks[0]["task_id"] == "t1"
        assert len(tasks[0]["events"]) == 3

    def test_feed_usage(self):
        c = TraceCollector()
        c.feed(StreamChunk(blocks=[
            TraceBlock(type="usage", data={"total_cost_usd": 0.05, "num_turns": 3}),
        ]))
        d = c.to_dict()
        assert d["usage"] == [{"total_cost_usd": 0.05, "num_turns": 3}]

    def test_attach_to_result(self):
        from eval.runner import EvalResult

        r = EvalResult(id="test", question="q", answer="a")
        c = TraceCollector()
        c.feed(StreamChunk(blocks=[
            TraceBlock(type="usage", data={"total_cost_usd": 0.01}),
        ]))
        c.attach(r)
        assert r.grade_detail == {"trace": {"usage": [{"total_cost_usd": 0.01}]}}

    def test_attach_merges_existing_grade_detail(self):
        from eval.runner import EvalResult

        r = EvalResult(id="test", question="q", answer="a", grade_detail={"score": 0.9})
        c = TraceCollector()
        c.feed(StreamChunk(blocks=[
            TraceBlock(type="thinking", data={"thinking": "x"}),
        ]))
        c.attach(r)
        assert r.grade_detail["score"] == 0.9
        assert "trace" in r.grade_detail

    def test_feed_no_blocks(self):
        """Text-only chunk with no blocks should not alter collector."""
        c = TraceCollector()
        c.feed(StreamChunk(text="hello"))
        assert c.to_dict() == {}

    def test_multiple_thinking_blocks(self):
        c = TraceCollector()
        c.feed(StreamChunk(blocks=[
            TraceBlock(type="thinking", data={"thinking": "step 1"}),
            TraceBlock(type="thinking", data={"thinking": "step 2"}),
        ]))
        d = c.to_dict()
        assert len(d["thinking"]) == 2

    def test_unknown_block_type_ignored(self):
        """Unknown block types are silently ignored, not crashing."""
        c = TraceCollector()
        c.feed(StreamChunk(blocks=[
            TraceBlock(type="unknown_xyz", data={"a": 1}),
            TraceBlock(type="thinking", data={"thinking": "ok"}),
        ]))
        d = c.to_dict()
        assert "unknown_xyz" not in str(d)
        assert len(d["thinking"]) == 1

    def test_multiple_tool_use_in_one_chunk(self):
        """Multiple tool_use blocks in a single chunk are all collected."""
        c = TraceCollector()
        c.feed(StreamChunk(blocks=[
            TraceBlock(type="tool_use", data={"id": "1", "name": "Bash"}),
            TraceBlock(type="tool_use", data={"id": "2", "name": "Read"}),
        ]))
        d = c.to_dict()
        assert len(d["tool_calls"]) == 2

    def test_multiple_subagent_tasks(self):
        """Two separate subagent tasks are tracked independently."""
        c = TraceCollector()
        c.feed(StreamChunk(blocks=[
            TraceBlock(type="subagent", data={"task_id": "t1", "event": "started"}),
        ]))
        c.feed(StreamChunk(blocks=[
            TraceBlock(type="subagent", data={"task_id": "t2", "event": "started"}),
        ]))
        d = c.to_dict()
        assert len(d["subagent_tasks"]) == 2

    def test_feed_after_attach_preserves_state(self):
        """feed() after attach() still works — collector is reusable."""
        from eval.runner import EvalResult

        c = TraceCollector()
        c.feed(StreamChunk(blocks=[
            TraceBlock(type="usage", data={"total_cost_usd": 0.01}),
        ]))
        r = EvalResult(id="x", question="q", answer="a")
        c.attach(r)
        assert r.grade_detail is not None

        # feed more after attach
        c.feed(StreamChunk(blocks=[
            TraceBlock(type="thinking", data={"thinking": "more"}),
        ]))
        d = c.to_dict()
        assert "thinking" in d
        assert "usage" in d
