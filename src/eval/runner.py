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
    elapsed: float = 0.0
    tags: list[str] = field(default_factory=list)
    error: str = ""
    extra: dict = field(default_factory=dict)


AsyncChatFn = Callable[[str], Any]  # async (str) -> str


class AsyncEvalRunner:
    """Run evaluation over a dataset with async chat and concurrency control.

    Usage::

        from eval import EvalDataset, AsyncEvalRunner
        from chat import ChatClient

        c = ChatClient("nanobot")
        ds = EvalDataset("questions.jsonl", limit=10)
        runner = AsyncEvalRunner(
            lambda q: c.async_chat(q, session="eval"),
            concurrency=5,
            auto_grade=True,
        )

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
        auto_grade: bool = False,
    ) -> None:
        self._chat = chat_fn
        self._concurrency = concurrency
        self._auto_grade = auto_grade
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
                try:
                    answer = await self._chat(item.question)
                except Exception as exc:
                    error = f"{type(exc).__name__}: {exc}"
                elapsed = time.monotonic() - t0

                success = None
                if self._auto_grade and item.expected and not error:
                    success = (
                        item.expected.strip().lower()
                        in answer.strip().lower()
                    )

                result = EvalResult(
                    id=item.id,
                    question=item.question,
                    expected=item.expected,
                    answer=answer,
                    success=success,
                    elapsed=round(elapsed, 2),
                    tags=item.tags,
                    error=error,
                    extra=item.extra,
                )
                self.results.append(result)
                print(
                    f"[{idx + 1}/{total}] {item.id} "
                    f"({'OK' if success else ('ERR' if error else '--')}) "
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
        return {
            "total": total,
            "graded": len(graded),
            "passed": passed,
            "failed": len(graded) - passed,
            "errors": len(errors),
            "avg_elapsed": avg_elapsed,
        }

    def report(self) -> str:
        s = self.stats
        lines = [
            f"Eval Report ({s['total']} items)",
            f"  Passed:  {s.get('passed', 0)}",
            f"  Failed:  {s.get('failed', 0)}",
            f"  Errors:  {s.get('errors', 0)}",
            f"  Avg time: {s.get('avg_elapsed', 0)}s",
        ]
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
                if r.extra:
                    obj["extra"] = r.extra
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")
