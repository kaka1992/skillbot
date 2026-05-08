"""Async-first evaluation runner with concurrency control."""

import asyncio
import json
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional, Union


@dataclass
class EvalResult:
    """Result of a single evaluation item."""

    id: str
    question: str
    expected: str = ""
    answer: str = ""
    success: Optional[bool] = None
    score: Optional[float] = None
    elapsed: float = 0.0
    tags: list[str] = field(default_factory=list)
    error: str = ""
    extra: dict = field(default_factory=dict)
    grade_detail: dict | None = None


@dataclass
class GraderOutput:
    """Output of a grader function."""

    success: bool | None = None
    score: float | None = None
    detail: dict | None = None


GraderFn = Callable[[str, str, dict], GraderOutput]
"""Grader function: (expected, answer, extra) -> GraderOutput."""

AsyncChatFn = Callable[[str], Any]  # async (str) -> str


def default_grader(expected: str, answer: str, extra: dict) -> GraderOutput:
    """Default grader: case-insensitive substring match."""
    if not expected:
        return GraderOutput()
    ok = expected.strip().lower() in answer.strip().lower()
    return GraderOutput(success=ok)


class AsyncEvalRunner:
    """Run evaluation over a dataset with async chat and concurrency control.

    Usage::

        from eval import EvalDataset, AsyncEvalRunner
        from chat import ChatClient

        c = ChatClient("nanobot")
        ds = EvalDataset("questions.jsonl", limit=10)

        # default grader (substring match)
        runner = AsyncEvalRunner(
            lambda q: c.async_chat(q, session="eval"),
            concurrency=5,
        )

        # custom grader
        runner = AsyncEvalRunner(chat_fn, grader=my_grader)

        # no grading
        runner = AsyncEvalRunner(chat_fn, grader=None)

        async for result in runner.run(ds):
            print(f"{result.id}: {'OK' if result.success else 'FAIL'}")

        print(runner.report())
        runner.save("results.jsonl")
    """

    def __init__(
        self,
        chat_fn: AsyncChatFn,
        *,
        concurrency: int = 5,
        grader: GraderFn | None = default_grader,
        trace: bool = False,
    ) -> None:
        self._chat = chat_fn
        self._concurrency = concurrency
        self._grader = grader
        self._trace = trace
        self.results: list[EvalResult] = []

    async def run(self, dataset) -> AsyncIterator[EvalResult]:
        """Run evaluation over *dataset*, yielding results as they complete.

        Uses ``asyncio.Semaphore`` to cap concurrent calls.
        """
        sem = asyncio.Semaphore(self._concurrency)
        total = len(dataset)

        async def _eval_one(idx: int, item) -> EvalResult:
            async with sem:
                t0 = time.monotonic()
                error = ""
                answer = ""
                trace_dict = None
                try:
                    raw = await self._chat(item.question)
                    if self._trace and isinstance(raw, tuple):
                        answer, trace_dict = raw
                    else:
                        answer = raw
                except Exception as exc:
                    error = f"{type(exc).__name__}: {exc}"
                elapsed = time.monotonic() - t0

                success = None
                score = None
                grade_detail = None
                if not error and self._grader is not None:
                    go = self._grader(item.expected, answer, item.extra)
                    success = go.success
                    score = go.score
                    grade_detail = go.detail

                if trace_dict:
                    if grade_detail is None:
                        grade_detail = {"trace": trace_dict}
                    else:
                        grade_detail["trace"] = trace_dict

                result = EvalResult(
                    id=item.id,
                    question=item.question,
                    expected=item.expected,
                    answer=answer,
                    success=success,
                    score=score,
                    elapsed=round(elapsed, 2),
                    tags=item.tags,
                    error=error,
                    extra=item.extra,
                    grade_detail=grade_detail,
                )
                self.results.append(result)
                status = (
                    "OK" if success else
                    ("ERR" if error else "--")
                )
                print(
                    f"[{idx + 1}/{total}] {item.id} "
                    f"({status}) "
                    f"{elapsed:.1f}s"
                )
                return result

        tasks = [
            asyncio.ensure_future(_eval_one(i, item))
            for i, item in enumerate(dataset)
        ]
        for coro in asyncio.as_completed(tasks):
            yield await coro

    @property
    def stats(self) -> dict:
        total = len(self.results)
        if not total:
            return {"total": 0}
        graded = [r for r in self.results if r.success is not None]
        errors = [r for r in self.results if r.error]
        avg_elapsed = round(sum(r.elapsed for r in self.results) / total, 2)
        passed = sum(1 for r in graded if r.success)
        scored = [r for r in self.results if r.score is not None]
        s = {
            "total": total,
            "graded": len(graded),
            "passed": passed,
            "failed": len(graded) - passed,
            "errors": len(errors),
            "avg_elapsed": avg_elapsed,
        }
        if scored:
            s["avg_score"] = round(
                sum(r.score for r in scored) / len(scored), 4
            )
        return s

    def report(self) -> str:
        s = self.stats
        lines = [
            f"Eval Report ({s['total']} items)",
            f"  Passed:  {s.get('passed', 0)}",
            f"  Failed:  {s.get('failed', 0)}",
            f"  Errors:  {s.get('errors', 0)}",
            f"  Avg time: {s.get('avg_elapsed', 0)}s",
        ]
        if "avg_score" in s:
            lines.append(f"  Avg score: {s['avg_score']}")
        if s.get("graded", 0) > 0:
            rate = s["passed"] / s["graded"] * 100
            lines.append(f"  Accuracy: {rate:.1f}%")
        return "\n".join(lines)

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for r in self.results:
                obj = {
                    "id": r.id,
                    "question": r.question,
                    "expected": r.expected,
                    "answer": r.answer,
                    "success": r.success,
                    "elapsed": r.elapsed,
                    "tags": r.tags,
                    "error": r.error,
                    "eval_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
                if r.score is not None:
                    obj["score"] = r.score
                if r.grade_detail:
                    obj["grade_detail"] = r.grade_detail
                if r.extra:
                    obj["extra"] = r.extra
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")

        # also write report alongside results
        report_path = path.with_suffix(".report.txt")
        report_text = self.report()
        report_path.write_text(report_text, encoding="utf-8")
        print(report_text)
