"""Tests for EvalTask + load_tasks + run_tasks."""

import asyncio
import os
import tempfile
from pathlib import Path

import pytest
import yaml

from eval.runner import GraderOutput, default_grader
from eval.task import (
    EvalTask,
    load_tasks,
    register_grader,
    resolve_grader,
    run_tasks,
)

_DATA = os.path.join(os.path.dirname(__file__), "data", "sample.jsonl")


def _write_config(tasks: list[dict], output_dir: str = "results") -> str:
    """Write a temporary YAML config and return its path."""
    data = {"output_dir": output_dir, "tasks": tasks}
    with tempfile.NamedTemporaryFile(
        suffix=".yaml", mode="w", delete=False, encoding="utf-8"
    ) as f:
        yaml.dump(data, f)
        return f.name


class TestLoadTasks:
    def test_load_basic(self):
        cfg = _write_config(
            [{"name": "t1", "dataset": _DATA, "agent": "nanobot"}]
        )
        try:
            tasks, out_dir = load_tasks(cfg)
            assert out_dir == "results"
            assert len(tasks) == 1
            assert tasks[0].name == "t1"
            assert tasks[0].agent == "nanobot"
        finally:
            os.unlink(cfg)

    def test_load_with_defaults(self):
        cfg = _write_config([{"name": "t1", "dataset": _DATA}])
        try:
            tasks, _ = load_tasks(cfg)
            t = tasks[0]
            assert t.agent == "nanobot"       # default
            assert t.concurrency == 5          # default
            assert t.timeout == 120            # default
            assert t.tags is None
            assert t.limit is None
        finally:
            os.unlink(cfg)

    def test_load_with_all_fields(self):
        cfg = _write_config(
            [
                {
                    "name": "full",
                    "dataset": _DATA,
                    "agent": "claude-code",
                    "model": "sonnet",
                    "tags": ["math", "easy"],
                    "limit": 10,
                    "concurrency": 3,
                    "timeout": 180,
                    "shuffle": True,
                    "output": "custom.jsonl",
                }
            ]
        )
        try:
            tasks, _ = load_tasks(cfg)
            t = tasks[0]
            assert t.name == "full"
            assert t.agent == "claude-code"
            assert t.model == "sonnet"
            assert t.tags == ["math", "easy"]
            assert t.limit == 10
            assert t.concurrency == 3
            assert t.timeout == 180
            assert t.shuffle is True
            assert t.output == "custom.jsonl"
        finally:
            os.unlink(cfg)

    def test_load_multiple_tasks(self):
        cfg = _write_config(
            [
                {"name": "t1", "dataset": _DATA},
                {"name": "t2", "dataset": _DATA},
                {"name": "t3", "dataset": _DATA},
            ]
        )
        try:
            tasks, _ = load_tasks(cfg)
            assert len(tasks) == 3
            assert [t.name for t in tasks] == ["t1", "t2", "t3"]
        finally:
            os.unlink(cfg)

    def test_load_custom_output_dir(self):
        cfg = _write_config(
            [{"name": "t1", "dataset": _DATA}], output_dir="my_results"
        )
        try:
            _, out_dir = load_tasks(cfg)
            assert out_dir == "my_results"
        finally:
            os.unlink(cfg)

    def test_missing_tasks_key_raises(self):
        with tempfile.NamedTemporaryFile(
            suffix=".yaml", mode="w", delete=False, encoding="utf-8"
        ) as f:
            yaml.dump({"other": 1}, f)
            cfg = f.name
        try:
            with pytest.raises(ValueError, match="No 'tasks' key"):
                load_tasks(cfg)
        finally:
            os.unlink(cfg)


class TestRunTasks:
    async def _mock_chat(self, q: str) -> str:
        await asyncio.sleep(0.01)
        return q.upper()

    def test_run_tasks_creates_output(self):
        tasks = [
            EvalTask(name="mock-t1", dataset=_DATA, agent="nanobot", limit=2),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            asyncio.run(run_tasks(tasks, tmp))
            assert os.path.exists(os.path.join(tmp, "mock-t1.jsonl"))
            assert os.path.exists(os.path.join(tmp, "mock-t1.report.txt"))
            assert os.path.exists(os.path.join(tmp, "summary.txt"))

    def test_eval_task_output_path(self):
        t = EvalTask(name="my-task", dataset=_DATA)
        assert t.output_path("results") == Path("results/my-task.jsonl")


class TestEvalTaskDataclass:
    def test_default_values(self):
        t = EvalTask(name="test", dataset="data.jsonl")
        assert t.agent == "nanobot"
        assert t.model is None
        assert t.tags is None
        assert t.limit is None
        assert t.shuffle is False
        assert t.concurrency == 5
        assert t.timeout == 120
        assert t.output is None
        assert t.grader is None  # defaults to default_grader

    def test_get_grader_default(self):
        t = EvalTask(name="test", dataset="data.jsonl")
        assert t.get_grader() is default_grader

    def test_get_grader_none_disables(self):
        t = EvalTask(name="test", dataset="data.jsonl", grader="none")
        assert t.get_grader() is None


class TestGraderRegistry:
    def test_resolve_default(self):
        assert resolve_grader("default") is default_grader

    def test_register_and_resolve(self):
        def my_grader(expected, answer, extra):
            return GraderOutput(success=True, score=1.0)

        register_grader("my_grader", my_grader)
        assert resolve_grader("my_grader") is my_grader

    def test_resolve_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown grader"):
            resolve_grader("nonexistent_grader")

    def test_resolve_import_path(self):
        fn = resolve_grader("eval.runner:default_grader")
        assert fn is default_grader

    def test_resolve_import_bad_path(self):
        with pytest.raises(ValueError, match="Cannot import"):
            resolve_grader("no_such_module:no_such_fn")

    def test_load_tasks_with_grader_name(self):
        cfg = _write_config(
            [{"name": "t1", "dataset": _DATA, "grader": "default"}]
        )
        try:
            tasks, _ = load_tasks(cfg)
            assert tasks[0].grader == "default"
            assert tasks[0].get_grader() is default_grader
        finally:
            os.unlink(cfg)

    def test_load_tasks_with_grader_none(self):
        cfg = _write_config(
            [{"name": "t1", "dataset": _DATA, "grader": "none"}]
        )
        try:
            tasks, _ = load_tasks(cfg)
            assert tasks[0].get_grader() is None
        finally:
            os.unlink(cfg)
