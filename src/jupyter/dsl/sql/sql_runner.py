"""Spark SQL runner — business logic for %%sql magic, tool-preset agnostic."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from typing import Any

from tools import ToolRegistry

ProgressFn = Callable[[str, dict[str, Any] | None], None]

_PRESET_ANALYZE = "spark_analyze_query"
_PRESET_SUBMIT = "spark_submit_query"
_PRESET_STATUS = "spark_get_job_status"
_PRESET_CANCEL = "spark_cancel_job"
_PRESET_RESULT = "spark_get_query_result"


def _run_async(coro):
    """Run an async coroutine, works in both sync and async (Jupyter) contexts."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    # Already in an event loop — run in a new thread with its own loop
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor() as pool:
        return pool.submit(asyncio.run, coro).result()


class SqlRunner:
    """Orchestrates Spark SQL tool calls with progress streaming."""

    def __init__(self, poll_interval: int = 30, timeout: int = 600) -> None:
        self._poll_interval = poll_interval
        self._timeout = timeout

    @staticmethod
    def _check_available() -> None:
        tool = ToolRegistry.get(_PRESET_ANALYZE)
        if tool is None:
            raise RuntimeError(
                "spark tools not available. "
                "Set SPARK_REMOTE via %agent_config or check tool requirements."
            )

    @staticmethod
    async def _call(preset_name: str, params: dict[str, Any]) -> dict[str, Any]:
        tool = ToolRegistry.get(preset_name)
        result = await tool.execute(params)
        if result.error:
            raise RuntimeError(result.error)
        return result.data

    def query(self, sql: str, on_progress: ProgressFn | None = None) -> dict[str, Any]:
        self._check_available()

        def emit(phase: str, data: dict[str, Any] | None = None) -> None:
            if on_progress:
                on_progress(phase, data)

        try:
            r = _run_async(self._call(_PRESET_ANALYZE, {"sql": sql}))
            emit("analyze", {"plan": r.get("data", {}).get("plan", "")})
        except Exception as e:
            emit("error", {"stage": "analyze", "message": str(e)})
            raise

        try:
            r = _run_async(self._call(_PRESET_SUBMIT, {"sql": sql}))
            job_id = r.get("data", {}).get("job_id", "")
            emit("submit", {"job_id": job_id})
        except Exception as e:
            emit("error", {"stage": "submit", "message": str(e)})
            raise

        t0 = time.time()
        while True:
            elapsed = int(time.time() - t0)
            if elapsed >= self._timeout:
                emit("error", {"stage": "poll", "message": f"timeout after {self._timeout}s"})
                raise TimeoutError(
                    f"timeout after {self._timeout}s, check: %sql status --job_id {job_id}"
                )
            time.sleep(self._poll_interval)
            try:
                r = _run_async(self._call(_PRESET_STATUS, {"job_id": job_id}))
                status = r.get("data", {}).get("status", "UNKNOWN")
                emit("poll", {"job_id": job_id, "status": status, "elapsed": int(time.time() - t0)})
            except Exception as e:
                emit("error", {"stage": "poll", "message": str(e)})
                raise

            status_upper = status.upper()
            if status_upper in ("FINISHED", "COMPLETED", "SUCCESS"):
                break
            if status_upper in ("FAILED", "ERROR"):
                err = r.get("data", {}).get("error", "unknown error")
                emit("error", {"stage": "poll", "message": f"query failed: {err}"})
                raise RuntimeError(f"query failed: {err}")
            if status_upper in ("CANCELLED", "CANCELED"):
                emit("error", {"stage": "poll", "message": "query cancelled"})
                raise RuntimeError("query cancelled")

        try:
            r = _run_async(self._call(_PRESET_RESULT, {"job_id": job_id}))
            emit("result", {"row_count": r.get("data", {}).get("content_row_count", 0)})
            return r
        except Exception as e:
            emit("error", {"stage": "result", "message": str(e)})
            raise

    def submit(self, sql: str, on_progress: ProgressFn | None = None) -> dict[str, Any]:
        self._check_available()
        try:
            r = _run_async(self._call(_PRESET_SUBMIT, {"sql": sql}))
            data = r.get("data", {})
            if on_progress:
                on_progress("submit", {"job_id": data.get("job_id", "")})
            return r
        except Exception as e:
            if on_progress:
                on_progress("error", {"stage": "submit", "message": str(e)})
            raise

    def status(self, job_id: str, on_progress: ProgressFn | None = None) -> dict[str, Any]:
        self._check_available()
        if on_progress:
            on_progress("status", {"job_id": job_id})
        r = _run_async(self._call(_PRESET_STATUS, {"job_id": job_id}))
        if on_progress:
            on_progress("status_ok", {"job_id": job_id, "status": r.get("data", {}).get("status", "?")})
        return r

    def cancel(self, job_id: str, on_progress: ProgressFn | None = None) -> dict[str, Any]:
        self._check_available()
        if on_progress:
            on_progress("cancel", {"job_id": job_id})
        r = _run_async(self._call(_PRESET_CANCEL, {"job_id": job_id}))
        if on_progress:
            on_progress("cancel_ok", {"job_id": job_id})
        return r

    def result(self, job_id: str, limit: int = 100,
               on_progress: ProgressFn | None = None) -> dict[str, Any]:
        self._check_available()
        if on_progress:
            on_progress("result", {"job_id": job_id})
        r = _run_async(self._call(_PRESET_RESULT, {"job_id": job_id, "limit": limit}))
        if on_progress:
            on_progress("result_ok", {"row_count": r.get("data", {}).get("content_row_count", 0)})
        return r


def sql_progress(phase: str, data: dict | None = None) -> None:
    """Print spark query progress with real-time flush."""
    import sys
    if data is None:
        data = {}
    job_id = data.get("job_id", "")

    if phase == "analyze":
        plan = data.get("plan", "")
        print(f"\n[spark] analyze:\n{plan}")
    elif phase == "submit":
        print(f"[spark] submit: job_id={job_id}")
    elif phase == "poll":
        status = data.get("status", "?")
        elapsed = data.get("elapsed", 0)
        print(f"\r[spark] poll: {status} ({elapsed}s)  ", end="")
        sys.stdout.flush()
    elif phase == "result":
        print(f"\n[spark] result: {data.get('row_count', 0)} rows")
    elif phase == "status":
        print(f"\r[spark] status: {job_id}...", end="")
        sys.stdout.flush()
    elif phase == "status_ok":
        print(f"\r[spark] status: {job_id} → {data.get('status', '?')}")
    elif phase == "cancel":
        print(f"[spark] cancel: {job_id}...", end=" ")
        sys.stdout.flush()
    elif phase == "cancel_ok":
        print("done")
    elif phase == "error":
        stage = data.get("stage", "?")
        msg = data.get("message", "")
        print(f"\n\033[91m[spark] {stage} error: {msg}\033[0m", file=sys.stderr)
