"""Spark SQL tool presets (interfaces only).

Import this module to reference Spark SQL tool contracts without pulling in
any implementation. Implementation modules register against these presets
via ``ToolRegistry.register_preset()`` + ``ToolRegistry.register_impl()``.

Example alternative implementation::

    from tools import ToolRegistry
    from tools.builtin.spark_sql_presets import SPARK_ANALYZE_QUERY

    ToolRegistry.register_preset(SPARK_ANALYZE_QUERY)
    ToolRegistry.register_impl("spark_analyze_query", "databricks", my_databricks_fn)
"""

from tools.interface import ToolPreset

# ----------------------------------------------------------------
# spark_analyze_query
# ----------------------------------------------------------------

SPARK_ANALYZE_QUERY = ToolPreset(
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

# ----------------------------------------------------------------
# spark_submit_query
# ----------------------------------------------------------------

SPARK_SUBMIT_QUERY = ToolPreset(
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

# ----------------------------------------------------------------
# spark_get_job_status
# ----------------------------------------------------------------

SPARK_GET_JOB_STATUS = ToolPreset(
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

# ----------------------------------------------------------------
# spark_get_query_result
# ----------------------------------------------------------------

SPARK_GET_QUERY_RESULT = ToolPreset(
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

# ----------------------------------------------------------------
# spark_download_result_file
# ----------------------------------------------------------------

SPARK_DOWNLOAD_RESULT_FILE = ToolPreset(
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

# ----------------------------------------------------------------
# spark_cancel_job
# ----------------------------------------------------------------

SPARK_CANCEL_JOB = ToolPreset(
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
