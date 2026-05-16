"""Tests for Spark SQL tools — mock pyspark."""
import asyncio
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, "src")

import pytest
from tools import ToolRegistry


# ---- mock Row ----
class MockRow:
    def __init__(self, **kwargs):
        self._data = kwargs

    def asDict(self):
        return dict(self._data)


# ---- mock DataFrame ----
class MockDataFrame:
    def __init__(self, rows, schema=None):
        self._rows = rows
        self._schema = schema

    def collect(self):
        return self._rows

    def explain(self, extended=False):
        return "== Physical Plan ==\nMockPlan"

    def write(self):
        return self

    def csv(self, path, header=True, mode="overwrite"):
        return None

    def _jdf(self):
        return self

    def queryExecution(self):
        return self

    def toString(self):
        return "== Physical Plan ==\nMockPlan"


# ---- mock SparkContext ----
class MockSparkContext:
    def setJobGroup(self, group_id, description):
        pass

    def cancelJobGroup(self, group_id):
        pass


# ---- mock SparkSession ----
class MockSpark:
    def __init__(self):
        self.sparkContext = MockSparkContext()
        self._sql_result = None

    def sql(self, sql):
        return self._sql_result or MockDataFrame([
            MockRow(name="Alice", age=30),
            MockRow(name="Bob", age=25),
        ])

    class builder:
        @staticmethod
        def remote(url):
            return MockSparkBuilder()


class MockSparkBuilder:
    def getOrCreate(self):
        return MockSpark()


@pytest.fixture(autouse=True)
def setup_spark():
    """Replace _get_spark with mock for all tests."""
    import tools.builtin.spark_sql as mod

    mod._spark = MockSpark()
    mod._query_store.clear()
    yield
    mod._spark = None
    mod._query_store.clear()


class TestSparkAnalyzeQuery:
    def test_analyze_returns_plan(self):
        t = ToolRegistry.get("spark_analyze_query")
        result = asyncio.run(t.execute({"sql": "SELECT 1"}))
        assert "Physical Plan" in result.content
        assert result.error is None


class TestSparkSubmitQuery:
    def test_submit_returns_query_id(self):
        t = ToolRegistry.get("spark_submit_query")
        result = asyncio.run(t.execute({"sql": "SELECT * FROM t"}))
        assert "Query ID:" in result.content
        assert result.error is None


class TestSparkJobStatus:
    def test_status_after_submit(self):
        submit = ToolRegistry.get("spark_submit_query")
        status = ToolRegistry.get("spark_get_job_status")

        r = asyncio.run(submit.execute({"sql": "SELECT 1"}))
        qid = r.content.split(": ")[-1].strip()

        r2 = asyncio.run(status.execute({"query_id": qid}))
        assert qid in r2.content
        assert "FINISHED" in r2.content

    def test_status_unknown_id(self):
        t = ToolRegistry.get("spark_get_job_status")
        result = asyncio.run(t.execute({"query_id": "nonexistent"}))
        assert result.error is not None


class TestSparkGetResult:
    def test_result_after_submit(self):
        import tools.builtin.spark_sql as mod

        submit = ToolRegistry.get("spark_submit_query")
        result_tool = ToolRegistry.get("spark_get_query_result")

        r = asyncio.run(submit.execute({"sql": "SELECT * FROM t"}))
        qid = r.content.split(": ")[-1].strip()

        # force immediate finish with mock data
        mod._query_store[qid]["status"] = "FINISHED"
        mod._query_store[qid]["result"] = [
            MockRow(name="Alice", age=30),
            MockRow(name="Bob", age=25),
        ]

        r2 = asyncio.run(result_tool.execute({"query_id": qid}))
        assert "Alice" in r2.content
        assert "Bob" in r2.content

    def test_result_unknown_id(self):
        t = ToolRegistry.get("spark_get_query_result")
        result = asyncio.run(t.execute({"query_id": "nonexistent"}))
        assert result.error is not None

    def test_result_still_running(self):
        submit = ToolRegistry.get("spark_submit_query")
        result_tool = ToolRegistry.get("spark_get_query_result")

        r = asyncio.run(submit.execute({"sql": "SELECT 1"}))
        qid = r.content.split(": ")[-1].strip()

        r2 = asyncio.run(result_tool.execute({"query_id": qid}))
        assert "still running" in r2.content.lower()


class TestSparkDownload:
    def test_download_finished_query(self):
        import tools.builtin.spark_sql as mod
        import tempfile, os

        submit = ToolRegistry.get("spark_submit_query")
        download = ToolRegistry.get("spark_download_result_file")

        r = asyncio.run(submit.execute({"sql": "SELECT 1"}))
        qid = r.content.split(": ")[-1].strip()
        mod._query_store[qid]["status"] = "FINISHED"
        mod._query_store[qid]["df"] = MockDataFrame([])

        with tempfile.TemporaryDirectory() as tmp:
            r2 = asyncio.run(download.execute({"query_id": qid, "output_dir": tmp}))
            assert "Result written to" in r2.content
            assert qid in r2.content


class TestSparkCancel:
    def test_cancel_running_query(self):
        import tools.builtin.spark_sql as mod

        submit = ToolRegistry.get("spark_submit_query")
        cancel = ToolRegistry.get("spark_cancel_job")

        r = asyncio.run(submit.execute({"sql": "SELECT 1"}))
        qid = r.content.split(": ")[-1].strip()

        r2 = asyncio.run(cancel.execute({"query_id": qid}))
        assert "cancelled" in r2.content.lower()
        assert mod._query_store[qid]["status"] == "CANCELLED"

    def test_cancel_unknown_id(self):
        t = ToolRegistry.get("spark_cancel_job")
        result = asyncio.run(t.execute({"query_id": "nonexistent"}))
        assert result.error is not None


# ----------------------------------------------------------------
# Load builtins once for this module
# ----------------------------------------------------------------
ToolRegistry.clear()
ToolRegistry.discover("src/tools/builtin")
