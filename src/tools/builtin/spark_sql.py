"""Spark SQL tools via PySpark Connect — default implementation.

Environment: ``SPARK_REMOTE`` — Spark Connect endpoint (default ``sc://localhost:15002``).

Presets live in ``_spark_sql_presets.py`` so that alternative implementations
can import the contracts without pulling in this module.
"""

import os
import threading
import uuid
from datetime import datetime

from tools import impl
from tools.interface import ToolRequirement, ToolResult
from tools.builtin._spark_sql_presets import (
    SPARK_ANALYZE_QUERY,
    SPARK_CANCEL_JOB,
    SPARK_GET_JOB_STATUS,
    SPARK_GET_QUERY_RESULT,
    SPARK_SUBMIT_QUERY,
)

_SPARK_REMOTE = os.environ.get("SPARK_REMOTE", "sc://localhost:15002")
_spark = None
_query_store: dict[str, dict] = {}

_SPARK_REQUIRES = [
    ToolRequirement(type="env", key="SPARK_REMOTE", description="Spark Connect endpoint"),
    ToolRequirement(type="import", key="pyspark", description="PySpark library"),
]


def _get_spark():
    global _spark
    if _spark is None:
        from pyspark.sql import SparkSession

        _spark = SparkSession.builder.remote(_SPARK_REMOTE).getOrCreate()
    return _spark


def _run_query(job_id: str, sql: str) -> None:
    rec = _query_store[job_id]
    try:
        spark = _get_spark()
        spark.sparkContext.setJobGroup(job_id, sql)
        df = spark.sql(sql)
        rec["df"] = df
        rec["result"] = df.collect()
        rec["status"] = "FINISHED"
    except Exception as e:
        rec["error"] = str(e)
        rec["status"] = "FAILED"


# ----------------------------------------------------------------
# spark_analyze_query
# ----------------------------------------------------------------

@impl(SPARK_ANALYZE_QUERY, requires=_SPARK_REQUIRES)
async def spark_analyze_query(params: dict) -> ToolResult:
    sql = params["sql"]
    try:
        spark = _get_spark()
        df = spark.sql(sql)
        plan = df._jdf.queryExecution().toString() if hasattr(df, "_jdf") else df.explain(extended=True)
    except Exception as e:
        return ToolResult(error=str(e))
    return ToolResult(data={
        "success": "true",
        "command": "spark_analyze_query",
        "data": {"plan": plan},
    })


# ----------------------------------------------------------------
# spark_submit_query
# ----------------------------------------------------------------

@impl(SPARK_SUBMIT_QUERY, requires=_SPARK_REQUIRES)
async def spark_submit_query(params: dict) -> ToolResult:
    job_id = uuid.uuid4().hex[:8]
    _query_store[job_id] = {
        "sql": params["sql"],
        "status": "RUNNING",
        "thread": None,
        "result": None,
        "df": None,
        "error": None,
        "start_time": datetime.now().isoformat(),
    }
    t = threading.Thread(target=_run_query, args=(job_id, params["sql"]), daemon=True)
    _query_store[job_id]["thread"] = t
    t.start()
    return ToolResult(data={
        "success": "true",
        "command": "spark_submit_query",
        "data": {"job_id": job_id, "status": "RUNNING"},
    })


# ----------------------------------------------------------------
# spark_get_job_status
# ----------------------------------------------------------------

@impl(SPARK_GET_JOB_STATUS, requires=_SPARK_REQUIRES)
async def spark_get_job_status(params: dict) -> ToolResult:
    job_id = params["job_id"]
    rec = _query_store.get(job_id)
    if rec is None:
        return ToolResult(error=f"Job ID not found: {job_id}")

    t = rec["thread"]
    alive = t.is_alive() if t else False
    status = "RUNNING" if alive else rec["status"]
    return ToolResult(data={
        "success": "true",
        "command": "spark_get_job_status",
        "data": {
            "job_id": job_id,
            "status": status,
            "query_log_url": "",
            "engine_type": "spark",
            "result_url": "",
            "log_url": "",
        },
    })


# ----------------------------------------------------------------
# spark_get_query_result
# ----------------------------------------------------------------

@impl(SPARK_GET_QUERY_RESULT, requires=_SPARK_REQUIRES)
async def spark_get_query_result(params: dict) -> ToolResult:
    job_id = params["job_id"]
    limit = params["limit"]
    output = params.get("output")

    rec = _query_store.get(job_id)
    if rec is None:
        return ToolResult(error=f"Job ID not found: {job_id}")
    if rec["status"] == "RUNNING":
        return ToolResult(error="Query still running")
    if rec["status"] == "FAILED":
        return ToolResult(error=rec.get("error", "Unknown error"))
    if rec["status"] == "CANCELLED":
        return ToolResult(error="Query was cancelled")

    rows = rec["result"]
    if rows is None or len(rows) == 0:
        return ToolResult(data={
            "success": "true",
            "command": "spark_get_query_result",
            "data": {
                "job_id": job_id,
                "status": rec["status"],
                "sample_data": [],
                "content_row_count": 0,
                "result_url": "",
                "output_path": output or "",
            },
        })

    row_dicts = [r.asDict() if hasattr(r, "asDict") else r for r in rows[:limit]]
    cols = list(row_dicts[0].keys())
    sample_data = [cols] + [list(r.values()) for r in row_dicts]

    return ToolResult(data={
        "success": "true",
        "command": "spark_get_query_result",
        "data": {
            "job_id": job_id,
            "status": rec["status"],
            "sample_data": sample_data,
            "content_row_count": len(row_dicts),
            "result_url": "",
            "output_path": output or "",
        },
    })


# ----------------------------------------------------------------
# spark_cancel_job
# ----------------------------------------------------------------

@impl(SPARK_CANCEL_JOB, requires=_SPARK_REQUIRES)
async def spark_cancel_job(params: dict) -> ToolResult:
    job_id = params["job_id"]
    rec = _query_store.get(job_id)
    if rec is None:
        return ToolResult(error=f"Job ID not found: {job_id}")
    if rec["status"] != "RUNNING":
        return ToolResult(data={
            "success": "true",
            "command": "spark_cancel_job",
            "data": {"job_id": job_id, "cancel_requested": "false"},
        })

    try:
        spark = _get_spark()
        spark.sparkContext.cancelJobGroup(job_id)
    except Exception as e:
        return ToolResult(error=str(e))
    rec["status"] = "CANCELLED"
    return ToolResult(data={
        "success": "true",
        "command": "spark_cancel_job",
        "data": {"job_id": job_id, "cancel_requested": "true"},
    })

