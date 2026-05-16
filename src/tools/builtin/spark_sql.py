"""Spark SQL tools via PySpark Connect.

Environment: ``SPARK_REMOTE`` — Spark Connect endpoint (default ``sc://localhost:15002``).

Each query runs in a background thread to enable async lifecycle management.
Results are stored in an in-memory QueryStore.
"""

import os
import threading
import uuid
from datetime import datetime

from tools import ToolResult, register

_SPARK_REMOTE = os.environ.get("SPARK_REMOTE", "sc://localhost:15002")
_spark = None
_query_store: dict[str, dict] = {}


def _get_spark():
    """Lazy-init SparkSession over Spark Connect."""
    global _spark
    if _spark is None:
        from pyspark.sql import SparkSession

        _spark = SparkSession.builder.remote(_SPARK_REMOTE).getOrCreate()
    return _spark


def _run_query(query_id: str, sql: str) -> None:
    """Background thread: execute SQL and store result/error."""
    rec = _query_store[query_id]
    try:
        spark = _get_spark()
        spark.sparkContext.setJobGroup(query_id, sql)
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

@register(
    name="spark_analyze_query",
    description="Validate a Spark SQL query and show its execution plan without running it",
    parameters={
        "type": "object",
        "properties": {
            "sql": {"type": "string", "description": "Spark SQL statement to analyze"},
        },
        "required": ["sql"],
    },
    group="spark",
)
async def spark_analyze_query(params: dict) -> ToolResult:
    sql = params["sql"]
    try:
        spark = _get_spark()
        df = spark.sql(sql)
        plan = df._jdf.queryExecution().toString() if hasattr(df, "_jdf") else df.explain(extended=True)
    except Exception as e:
        return ToolResult(content="", error=str(e))
    return ToolResult(content=f"SQL analysis:\n{plan}")


# ----------------------------------------------------------------
# spark_submit_query
# ----------------------------------------------------------------

@register(
    name="spark_submit_query",
    description="Submit a Spark SQL query asynchronously and return a query ID for tracking",
    parameters={
        "type": "object",
        "properties": {
            "sql": {"type": "string", "description": "Spark SQL statement to execute"},
        },
        "required": ["sql"],
    },
    group="spark",
)
async def spark_submit_query(params: dict) -> ToolResult:
    query_id = uuid.uuid4().hex[:8]
    _query_store[query_id] = {
        "sql": params["sql"],
        "status": "RUNNING",
        "thread": None,
        "result": None,
        "df": None,
        "error": None,
        "start_time": datetime.now().isoformat(),
    }
    t = threading.Thread(target=_run_query, args=(query_id, params["sql"]), daemon=True)
    _query_store[query_id]["thread"] = t
    t.start()
    return ToolResult(content=f"Query submitted.\nQuery ID: {query_id}")


# ----------------------------------------------------------------
# spark_get_job_status
# ----------------------------------------------------------------

@register(
    name="spark_get_job_status",
    description="Check the execution status of a Spark query by query ID",
    parameters={
        "type": "object",
        "properties": {
            "query_id": {"type": "string", "description": "Query ID from spark_submit_query"},
        },
        "required": ["query_id"],
    },
    group="spark",
)
async def spark_get_job_status(params: dict) -> ToolResult:
    query_id = params["query_id"]
    rec = _query_store.get(query_id)
    if rec is None:
        return ToolResult(content="", error=f"Query ID not found: {query_id}")

    t = rec["thread"]
    alive = t.is_alive() if t else False
    status = "RUNNING" if alive else rec["status"]
    lines = [
        f"Query: {query_id}",
        f"Status: {status}",
        f"SQL: {rec['sql'][:200]}",
        f"Started: {rec['start_time']}",
    ]
    if rec.get("error"):
        lines.append(f"Error: {rec['error']}")
    return ToolResult(content="\n".join(lines))


# ----------------------------------------------------------------
# spark_get_query_result
# ----------------------------------------------------------------

@register(
    name="spark_get_query_result",
    description="Get the result rows of a completed Spark query",
    parameters={
        "type": "object",
        "properties": {
            "query_id": {"type": "string", "description": "Query ID from spark_submit_query"},
            "limit": {"type": "integer", "description": "Max rows to return (default 100)"},
        },
        "required": ["query_id"],
    },
    group="spark",
)
async def spark_get_query_result(params: dict) -> ToolResult:
    query_id = params["query_id"]
    limit = params.get("limit", 100)
    rec = _query_store.get(query_id)
    if rec is None:
        return ToolResult(content="", error=f"Query ID not found: {query_id}")
    if rec["status"] == "RUNNING":
        return ToolResult(content=f"Query {query_id} is still running. Check status first.")
    if rec["status"] == "FAILED":
        return ToolResult(content="", error=rec.get("error", "Unknown error"))
    if rec["status"] == "CANCELLED":
        return ToolResult(content="", error="Query was cancelled")

    rows = rec["result"]
    if rows is None or len(rows) == 0:
        return ToolResult(content="(no rows)")
    cols = rows[0].asDict().keys() if hasattr(rows[0], "asDict") else []
    header = " | ".join(cols)
    sep = "-+-".join("-" * len(c) for c in cols)
    lines = [header, sep]
    for row in rows[:limit]:
        d = row.asDict() if hasattr(row, "asDict") else row
        lines.append(" | ".join(str(d.get(c, "")) for c in cols))
    return ToolResult(content=f"Query result ({min(len(rows), limit)} of {len(rows)} rows):\n" + "\n".join(lines))


# ----------------------------------------------------------------
# spark_download_result_file
# ----------------------------------------------------------------

@register(
    name="spark_download_result_file",
    description="Download the full result of a Spark query as a CSV file",
    parameters={
        "type": "object",
        "properties": {
            "query_id": {"type": "string", "description": "Query ID from spark_submit_query"},
            "output_dir": {"type": "string", "description": "Output directory (default /tmp)"},
        },
        "required": ["query_id"],
    },
    group="spark",
)
async def spark_download_result_file(params: dict) -> ToolResult:
    query_id = params["query_id"]
    output_dir = params.get("output_dir", "/tmp")
    rec = _query_store.get(query_id)
    if rec is None:
        return ToolResult(content="", error=f"Query ID not found: {query_id}")
    if rec["status"] != "FINISHED":
        return ToolResult(content="", error=f"Query not finished (status: {rec['status']})")

    df = rec.get("df")
    if df is None:
        return ToolResult(content="", error="No DataFrame available for download")

    file_path = os.path.join(output_dir, f"{query_id}.csv")
    os.makedirs(output_dir, exist_ok=True)
    df.write.csv(file_path, header=True, mode="overwrite")
    return ToolResult(content=f"Result written to {file_path}", files=[file_path])


# ----------------------------------------------------------------
# spark_cancel_job
# ----------------------------------------------------------------

@register(
    name="spark_cancel_job",
    description="Cancel a running Spark query by query ID",
    parameters={
        "type": "object",
        "properties": {
            "query_id": {"type": "string", "description": "Query ID from spark_submit_query"},
        },
        "required": ["query_id"],
    },
    group="spark",
)
async def spark_cancel_job(params: dict) -> ToolResult:
    query_id = params["query_id"]
    rec = _query_store.get(query_id)
    if rec is None:
        return ToolResult(content="", error=f"Query ID not found: {query_id}")
    if rec["status"] != "RUNNING":
        return ToolResult(content=f"Query {query_id} is not running (status: {rec['status']})")

    try:
        spark = _get_spark()
        spark.sparkContext.cancelJobGroup(query_id)
    except Exception as e:
        return ToolResult(content="", error=str(e))
    rec["status"] = "CANCELLED"
    return ToolResult(content=f"Query {query_id} cancelled")
