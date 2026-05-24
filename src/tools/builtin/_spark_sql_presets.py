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
            "sql": {"type": "str", "description": "Spark SQL statement to analyze"},
        },
        "required": ["sql"],
    },
    returns={
        "success": ReturnProperty(type="str", description="Request status"),
        "command": ReturnProperty(type="str", description="Request command"),
        "data": ReturnProperty(type="object", description="Result data", properties={
            "plan": ReturnProperty(type="str", description="Query execution plan text"),
        }),
        "error": ReturnProperty(type="str", description="Error message"),
    },
    group="spark",
)

# ----------------------------------------------------------------
# spark_submit_query
# ----------------------------------------------------------------

SPARK_SUBMIT_QUERY = ToolPreset(
    name="spark_submit_query",
    description="Submit a Spark SQL query asynchronously and return a job ID for tracking",
    parameters={
        "type": "object",
        "properties": {
            "sql": {"type": "str", "description": "Spark SQL statement to execute"},
        },
        "required": ["sql"],
    },
    returns={
        "success": ReturnProperty(type="str", description="Request status"),
        "command": ReturnProperty(type="str", description="Request command"),
        "data": ReturnProperty(type="object", description="Result data", properties={
            "job_id":ReturnProperty(type="str", description="Unique query tracking ID"),
            "status": ReturnProperty(type="str", description="Submitted status"),
        }),
        "error": ReturnProperty(type="str", description="Error message"),
    },
    group="spark",
)

# ----------------------------------------------------------------
# spark_get_job_status
# ----------------------------------------------------------------

SPARK_GET_JOB_STATUS = ToolPreset(
    name="spark_get_job_status",
    description="Check the execution status of a Spark query by Job ID",
    parameters={
        "type": "object",
        "properties": {
            "job_id": {"type": "str", "description": "Job ID from spark_submit_query"},
        },
        "required": ["job_id"],
    },
    returns={
        "success": ReturnProperty(type="str", description="Request status"),
        "command": ReturnProperty(type="str", description="Request command"),
        "data": ReturnProperty(type="object", description="Result data", properties={
            "job_id": ReturnProperty(type="str", description="Unique query tracking ID"),
            "status": ReturnProperty(type="str", description="Job status"),
            "query_log_url": ReturnProperty(type="str", description="Query log file URL"),
            "engine_type": ReturnProperty(type="str", description="Query engine type"),
            "result_url": ReturnProperty(type="str", description="Result data file URL"),
            "log_url": ReturnProperty(type="str", description="Submitted log file URL"),
        }),
        "error": ReturnProperty(type="str", description="Error message"),
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
            "job_id": {"type": "str", "description": "Job ID from spark_submit_query"},
            "limit": {"type": "int", "description": "Max rows for sample to return", "default": 8},
            "output": {"type": "str", "description": "Output result file path"},
            "output_format": {"type": "str", "description": "Output format (e.g. csv, table, json)", "default": "csv"},
            "output_encoding": {"type": "str", "description": "Output encoding (e.g. utf-8, gbk)", "default": "utf-8"},
        },
        "required": ["job_id"],
    },
    returns={
        "success": ReturnProperty(type="str", description="Request status"),
        "command": ReturnProperty(type="str", description="Request command"),
        "data": ReturnProperty(type="object", description="Result data", properties={
            "job_id":ReturnProperty(type="str", description="Unique query tracking ID"),
            "status": ReturnProperty(type="str", description="Job status"),
            "sample_data":ReturnProperty(type="array", description="Sample data with json array format", items=ReturnProperty(
            type="array",
            items=ReturnProperty(type="str"),
        )),
            "content_row_count":ReturnProperty(type="int", description="Return sample data count"),
            "result_url":ReturnProperty(type="str", description="Result data file URL"),
            "output_path": ReturnProperty(type="str", description="Output result data file path"),
        }),
        "error": ReturnProperty(type="str", description="Error message"),
    },
    group="spark",
)

# ----------------------------------------------------------------
# spark_cancel_job
# ----------------------------------------------------------------

SPARK_CANCEL_JOB = ToolPreset(
    name="spark_cancel_job",
    description="Cancel a running Spark query by Job ID",
    parameters={
        "type": "object",
        "properties": {
            "job_id": {"type": "string", "description": "Job ID from spark_submit_query"},
        },
        "required": ["job_id"],
    },
    returns={
        "success": ReturnProperty(type="str", description="Request status"),
        "command": ReturnProperty(type="str", description="Request command"),
        "data": ReturnProperty(type="object", description="Result data", properties={
            "job_id":ReturnProperty(type="str", description="Unique query tracking ID"),
            "cancel_requested": ReturnProperty(type="str", description="Cancel requested status"),
        }),
        "error": ReturnProperty(type="str", description="Error message"),
    },
    group="spark",
)
