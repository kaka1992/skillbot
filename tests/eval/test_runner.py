"""Tests for AsyncEvalRunner."""

import asyncio
import os
import tempfile

from eval import AsyncEvalRunner, EvalDataset

_DATA = os.path.join(os.path.dirname(__file__), "data", "sample.jsonl")


# ---- helpers ----


async def _collect(runner, ds, concurrency=3):
    return [r async for r in runner.run(ds)]


async def _mock_ok(q: str) -> str:
    await asyncio.sleep(0.01)
    return "ok"


async def _mock_by_question(q: str) -> str:
    await asyncio.sleep(0.01)
    if "1+1" in q:
        return "2"
    if "5*3" in q:
        return "15"
    return "unknown"


# ---- tests ----


class TestAsyncEvalRunnerMock:
    def test_run_and_grade(self):
        ds = EvalDataset(_DATA, limit=3)
        runner = AsyncEvalRunner(_mock_by_question, auto_grade=True)
        results = asyncio.run(_collect(runner, ds))

        assert len(results) == 3
        assert results[0].success is True   # 1+1 → 2 correct
        assert results[1].success is True   # 5*3 → 15 correct
        assert results[2].success is False  # lang-1: "unknown" doesn't contain "hello"

    def test_without_auto_grade(self):
        ds = EvalDataset(_DATA, limit=2)
        runner = AsyncEvalRunner(_mock_ok, auto_grade=False)
        results = asyncio.run(_collect(runner, ds))

        assert results[0].success is None
        assert results[0].error == ""

    def test_error_handling(self):
        async def fail(q: str) -> str:
            if "1+1" in q:
                raise RuntimeError("test boom")
            return "ok"

        ds = EvalDataset(_DATA, limit=2)
        runner = AsyncEvalRunner(fail, auto_grade=True)
        results = asyncio.run(_collect(runner, ds))

        assert results[0].error == "RuntimeError: test boom"
        assert results[0].success is None
        assert results[1].error == ""

    def test_concurrency_limit(self):
        running = 0
        max_running = 0

        async def concurrent(q: str) -> str:
            nonlocal running, max_running
            running += 1
            max_running = max(max_running, running)
            await asyncio.sleep(0.03)
            running -= 1
            return "ok"

        ds = EvalDataset(_DATA, limit=6)
        runner = AsyncEvalRunner(concurrent, concurrency=3)
        asyncio.run(_collect(runner, ds, concurrency=3))
        assert max_running <= 3   # semaphore capped at 3

    def test_stats(self):
        ds = EvalDataset(_DATA, limit=3)
        runner = AsyncEvalRunner(_mock_by_question, auto_grade=True)
        asyncio.run(_collect(runner, ds))

        s = runner.stats
        assert s["total"] == 3
        assert s["graded"] == 3
        assert s["passed"] == 2
        assert s["failed"] == 1
        assert s["errors"] == 0

    def test_save_jsonl(self):
        ds = EvalDataset(_DATA, limit=2)
        runner = AsyncEvalRunner(_mock_ok, auto_grade=True)
        asyncio.run(_collect(runner, ds))

        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            tmp = f.name
        try:
            runner.save(tmp)
            import json

            with open(tmp) as f:
                lines = [json.loads(l) for l in f if l.strip()]
            assert len(lines) == 2
            assert "eval_date" in lines[0]
            assert lines[0]["answer"] == "ok"
        finally:
            os.unlink(tmp)

    def test_report(self):
        ds = EvalDataset(_DATA, limit=2)
        runner = AsyncEvalRunner(_mock_ok, auto_grade=True)
        asyncio.run(_collect(runner, ds))

        r = runner.report()
        assert "2 items" in r
        assert "Passed" in r

    def test_empty_dataset(self):
        ds = EvalDataset(_DATA, tags=["nonexistent"])
        runner = AsyncEvalRunner(_mock_ok)
        results = asyncio.run(_collect(runner, ds))
        assert len(results) == 0
        assert runner.stats["total"] == 0


# ---- real nanobot tests ----


def _nanobot_ready() -> bool:
    import subprocess

    r = subprocess.run(
        ["bash", "scripts/run.sh", "status", "nanobot"],
        capture_output=True, text=True, timeout=10,
    )
    return "RUNNING" in r.stdout


class TestAsyncEvalRunnerNanobot:
    """Integration tests against real nanobot (skipped if not running)."""

    def test_real_eval_math(self):
        if not _nanobot_ready():
            import pytest; pytest.skip("nanobot not running")

        import sys
        sys.path.insert(0, "src")
        from chat import ChatClient

        c = ChatClient("nanobot", timeout=60)
        ds = EvalDataset(_DATA, tags=["math"], limit=2)
        runner = AsyncEvalRunner(
            lambda q: c.async_chat(q, session="eval-real-math"),
            concurrency=2,
            auto_grade=True,
        )
        results = asyncio.run(_collect(runner, ds, concurrency=2))
        assert len(results) == 2
        # math questions should get correct answers
        assert results[0].success is True   # 1+1 → 2
        assert results[1].success is True   # 5*3 → 15

    def test_real_eval_report_and_save(self):
        if not _nanobot_ready():
            import pytest; pytest.skip("nanobot not running")

        import sys
        sys.path.insert(0, "src")
        from chat import ChatClient

        c = ChatClient("nanobot", timeout=60)
        ds = EvalDataset(_DATA, tags=["lang"], limit=2)
        runner = AsyncEvalRunner(
            lambda q: c.async_chat(q, session="eval-real-lang"),
            concurrency=2,
            auto_grade=True,
        )
        asyncio.run(_collect(runner, ds, concurrency=2))

        s = runner.stats
        assert s["total"] == 2
        assert "items" in runner.report()

        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            tmp = f.name
        try:
            runner.save(tmp)
            import json
            with open(tmp) as f:
                lines = [json.loads(l) for l in f if l.strip()]
            assert len(lines) == 2
            assert all("answer" in l for l in lines)
        finally:
            os.unlink(tmp)
