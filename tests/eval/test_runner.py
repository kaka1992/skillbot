"""Tests for AsyncEvalRunner."""

import asyncio
import os
import tempfile
from pathlib import Path

from eval import (
    AsyncEvalRunner,
    EvalDataset,
    GraderOutput,
    default_grader,
)

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
        runner = AsyncEvalRunner(_mock_by_question)
        results = asyncio.run(_collect(runner, ds))

        assert len(results) == 3
        assert results[0].success is True   # 1+1 → 2 correct
        assert results[1].success is True   # 5*3 → 15 correct
        assert results[2].success is False  # lang-1: "unknown" doesn't contain "hello"

    def test_grader_none_disables_grading(self):
        ds = EvalDataset(_DATA, limit=2)
        runner = AsyncEvalRunner(_mock_ok, grader=None)
        results = asyncio.run(_collect(runner, ds))

        assert results[0].success is None
        assert results[0].error == ""

    def test_error_handling(self):
        async def fail(q: str) -> str:
            if "1+1" in q:
                raise RuntimeError("test boom")
            return "ok"

        ds = EvalDataset(_DATA, limit=2)
        runner = AsyncEvalRunner(fail)
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
        runner = AsyncEvalRunner(_mock_by_question)
        asyncio.run(_collect(runner, ds))

        s = runner.stats
        assert s["total"] == 3
        assert s["graded"] == 3
        assert s["passed"] == 2
        assert s["failed"] == 1
        assert s["errors"] == 0

    def test_save_jsonl(self):
        ds = EvalDataset(_DATA, limit=2)
        runner = AsyncEvalRunner(_mock_ok)
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

            # verify report file written alongside results
            report_path = Path(tmp).with_suffix(".report.txt")
            assert report_path.exists()
            assert "2 items" in report_path.read_text()
        finally:
            os.unlink(tmp)
            if report_path.exists():
                os.unlink(report_path)

    def test_report(self):
        ds = EvalDataset(_DATA, limit=2)
        runner = AsyncEvalRunner(_mock_ok)
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

            report_path = Path(tmp).with_suffix(".report.txt")
            assert report_path.exists()
        finally:
            os.unlink(tmp)
            if report_path.exists():
                os.unlink(report_path)


# ----------------------------------------------------------------
# custom grader tests
# ----------------------------------------------------------------


class TestDefaultGrader:
    """Tests for the built-in default_grader function."""

    def test_substring_match_pass(self):
        result = default_grader("hello", "hello world", {})
        assert result.success is True

    def test_substring_match_fail(self):
        result = default_grader("hello", "goodbye", {})
        assert result.success is False

    def test_empty_expected_returns_none(self):
        result = default_grader("", "anything", {})
        assert result.success is None

    def test_case_insensitive(self):
        result = default_grader("HELLO", "Hello World", {})
        assert result.success is True


class TestCustomGrader:
    """Tests for custom grader functions in AsyncEvalRunner."""

    async def _mock_echo(self, q: str) -> str:
        await asyncio.sleep(0.01)
        return q.upper()

    def test_custom_grader_replaces_default(self):
        """custom grader replaces the default substring matcher."""

        def my_grader(expected, answer, extra):
            return GraderOutput(success=True, score=0.8)

        ds = EvalDataset(_DATA, limit=2)
        runner = AsyncEvalRunner(self._mock_echo, grader=my_grader)
        results = asyncio.run(_collect(runner, ds))
        assert results[0].success is True
        assert results[0].score == 0.8
        assert results[1].success is True

    def test_custom_grader_with_score(self):
        """custom grader can set both success and score."""

        def score_grader(expected, answer, extra):
            score = 1.0 if expected.lower() in answer.lower() else 0.0
            return GraderOutput(success=score >= 1.0, score=score)

        ds = EvalDataset(_DATA, limit=3)
        runner = AsyncEvalRunner(self._mock_echo, grader=score_grader)
        results = asyncio.run(_collect(runner, ds))
        assert all(r.score is not None for r in results)

    def test_grader_uses_extra_field(self):
        """grader can access extra fields from the dataset."""

        def extra_grader(expected, answer, extra):
            threshold = extra.get("min_score", 0.5)
            return GraderOutput(success=True, score=threshold)

        ds = EvalDataset(_DATA, limit=2)
        runner = AsyncEvalRunner(self._mock_echo, grader=extra_grader)
        results = asyncio.run(_collect(runner, ds))
        assert all(r.success is True for r in results)

    def test_grader_none_disables_grading(self):
        """grader=None skips grading; success stays None."""
        ds = EvalDataset(_DATA, limit=2)
        runner = AsyncEvalRunner(self._mock_echo, grader=None)
        results = asyncio.run(_collect(runner, ds))
        assert results[0].success is None
        assert results[1].success is None

    def test_grader_with_detail(self):
        """custom grader can attach grade_detail."""

        def detail_grader(expected, answer, extra):
            return GraderOutput(
                success=True,
                detail={"matched": expected.lower() in answer.lower()},
            )

        ds = EvalDataset(_DATA, tags=["math"], limit=1)
        runner = AsyncEvalRunner(self._mock_echo, grader=detail_grader)
        results = asyncio.run(_collect(runner, ds))
        assert results[0].grade_detail == {"matched": False}

    def test_stats_includes_avg_score(self):
        """stats computes avg_score when scores are present."""

        def uniform_grader(expected, answer, extra):
            return GraderOutput(success=True, score=0.8)

        ds = EvalDataset(_DATA, limit=3)
        runner = AsyncEvalRunner(self._mock_echo, grader=uniform_grader)
        asyncio.run(_collect(runner, ds))
        s = runner.stats
        assert s["avg_score"] == 0.8

    def test_save_includes_score_and_detail(self):
        """save() writes score and grade_detail when present."""

        def rich_grader(expected, answer, extra):
            return GraderOutput(
                success=True, score=0.95, detail={"tokens": 42},
            )

        ds = EvalDataset(_DATA, limit=1)
        runner = AsyncEvalRunner(self._mock_echo, grader=rich_grader)
        asyncio.run(_collect(runner, ds))

        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            tmp = f.name
        try:
            runner.save(tmp)
            import json

            with open(tmp) as f:
                lines = [json.loads(l) for l in f if l.strip()]
            assert len(lines) == 1
            assert lines[0]["score"] == 0.95
            assert lines[0]["grade_detail"] == {"tokens": 42}

            report_path = Path(tmp).with_suffix(".report.txt")
            assert report_path.exists()
            assert "Avg score: 0.95" in report_path.read_text()
        finally:
            os.unlink(tmp)
            if report_path.exists():
                os.unlink(report_path)

    def test_report_shows_avg_score(self):
        """report() includes avg_score when scores are present."""

        def scored_grader(expected, answer, extra):
            return GraderOutput(success=True, score=0.75)

        ds = EvalDataset(_DATA, limit=2)
        runner = AsyncEvalRunner(self._mock_echo, grader=scored_grader)
        asyncio.run(_collect(runner, ds))
        r = runner.report()
        assert "Avg score: 0.75" in r
