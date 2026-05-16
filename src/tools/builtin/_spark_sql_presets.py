"""Spark SQL tool presets (interfaces only).

Import this module to reference Spark SQL tool contracts without pulling in
any implementation. Implementation modules register against these presets
via ``ToolRegistry.register_preset()`` + ``ToolRegistry.register_impl()``.

Example alternative implementation::

    from tools import ToolRegistry
    from tools.builtin._spark_sql_presets import SPARK_ANALYZE_QUERY

    ToolRegistry.register_preset(SPARK_ANALYZE_QUERY)
    ToolRegistry.register_impl("spark_analyze_query", "databricks", my_databricks_fn)
"""

from tools.interface import ReturnProperty, ToolPreset

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
    returns={
        "plan": ReturnProperty(type="str", description="Query execution plan text"),
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
    returns={
        "job_id": ReturnProperty(type="str", description="Unique query tracking ID"),
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
    returns={
        "job_id": ReturnProperty(type="str", description="Query ID"),
        "status": ReturnProperty(type="str", description="One of: RUNNING, FINISHED, FAILED, CANCELLED"),
        "sql": ReturnProperty(type="str", description="Submitted SQL text (truncated to 200 chars)"),
        "start_time": ReturnProperty(type="str", description="ISO-8601 start timestamp"),
        "error": ReturnProperty(type="str", description="Error message if status is FAILED"),
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
            "limit": {"type": "integer", "description": "Max rows to return", "default": 100},
        },
        "required": ["query_id"],
    },
    returns={
        "columns": ReturnProperty(
            type="array",
            items=ReturnProperty(type="str"),
            description="Column names",
        ),
        "rows": ReturnProperty(
            type="array",
            items=ReturnProperty(type="object"),
            description="Data rows as dicts",
        ),
        "row_count": ReturnProperty(type="int", description="Number of rows returned"),
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
            "output_dir": {"type": "string", "description": "Output directory", "default": "/tmp"},
        },
        "required": ["query_id"],
    },
    returns={
        "file": ReturnProperty(type="str", description="Absolute path to the CSV file"),
        "format": ReturnProperty(type="str", description="Output format (always 'csv')"),
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
    returns={
        "job_id": ReturnProperty(type="str", description="Query ID"),
        "cancelled": ReturnProperty(type="bool", description="Whether the job was cancelled"),
    },
    group="spark",
)
