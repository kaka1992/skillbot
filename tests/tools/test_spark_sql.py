"""Tests for Spark SQL tools — mock pyspark."""
import asyncio
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, "src")

import pytest
from tools import ToolRegistry


class MockRow:
    def __init__(self, **kwargs):
        self._data = kwargs

    def asDict(self):
        return dict(self._data)


class _MockWriter:
    def csv(self, path, header=True, mode="overwrite"):
        pass


class MockDataFrame:
    def __init__(self, rows=None, schema=None):
        self._rows = rows or []
        self._schema = schema

    def collect(self):
        return self._rows

    def explain(self, extended=False):
        pass

    @property
    def write(self):
        return _MockWriter()

    @property
    def _jdf(self):
        return _MockJdf()


class _MockJdf:
    def queryExecution(self):
        return self

    def toString(self):
        return "== Physical Plan ==\nMockPlan"


class MockSparkContext:
    def setJobGroup(self, group_id, description):
        pass

    def cancelJobGroup(self, group_id):
        pass


class MockSpark:
    def __init__(self):
        self.sparkContext = MockSparkContext()

    def sql(self, sql):
        return MockDataFrame(
            [MockRow(name="Alice", age=30), MockRow(name="Bob", age=25)]
        )

    class builder:
        @staticmethod
        def remote(url):
            return MockSparkBuilder()


class MockSparkBuilder:
    def getOrCreate(self):
        return MockSpark()


@pytest.fixture(autouse=True)
def setup_spark():
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
        assert "Physical Plan" in result.data["data"]["plan"]
        assert result.error is None


class TestSparkSubmitQuery:
    def test_submit_returns_query_id(self):
        t = ToolRegistry.get("spark_submit_query")
        result = asyncio.run(t.execute({"sql": "SELECT * FROM t"}))
        assert "job_id" in result.data["data"]
        assert result.error is None


class TestSparkJobStatus:
    def test_status_after_submit(self):
        submit = ToolRegistry.get("spark_submit_query")
        status = ToolRegistry.get("spark_get_job_status")

        r = asyncio.run(submit.execute({"sql": "SELECT 1"}))
        job_id = r.data["data"]["job_id"]

        r2 = asyncio.run(status.execute({"job_id": job_id}))
        assert r2.data["data"]["job_id"] == job_id
        assert r2.data["data"]["status"] == "FINISHED"

    def test_status_unknown_id(self):
        t = ToolRegistry.get("spark_get_job_status")
        result = asyncio.run(t.execute({"job_id": "nonexistent"}))
        assert result.error is not None


class TestSparkGetResult:
    def test_result_after_submit(self):
        import tools.builtin.spark_sql as mod

        submit = ToolRegistry.get("spark_submit_query")
        result_tool = ToolRegistry.get("spark_get_query_result")

        r = asyncio.run(submit.execute({"sql": "SELECT * FROM t"}))
        job_id = r.data["data"]["job_id"]

        mod._query_store[job_id]["status"] = "FINISHED"
        mod._query_store[job_id]["result"] = [
            MockRow(name="Alice", age=30),
            MockRow(name="Bob", age=25),
        ]

        r2 = asyncio.run(result_tool.execute({"job_id": job_id}))
        assert r2.data["data"]["sample_data"] == [["name", "age"], ["Alice", 30], ["Bob", 25]]
        assert r2.data["data"]["content_row_count"] == 2

    def test_result_unknown_id(self):
        t = ToolRegistry.get("spark_get_query_result")
        result = asyncio.run(t.execute({"job_id": "nonexistent"}))
        assert result.error is not None

    def test_result_still_running(self):
        import tools.builtin.spark_sql as mod

        submit = ToolRegistry.get("spark_submit_query")
        result_tool = ToolRegistry.get("spark_get_query_result")

        r = asyncio.run(submit.execute({"sql": "SELECT 1"}))
        job_id = r.data["data"]["job_id"]
        mod._query_store[job_id]["status"] = "RUNNING"

        r2 = asyncio.run(result_tool.execute({"job_id": job_id}))
        assert "still running" in r2.error.lower()


class TestSparkCancel:
    def test_cancel_running_query(self):
        import tools.builtin.spark_sql as mod

        submit = ToolRegistry.get("spark_submit_query")
        cancel = ToolRegistry.get("spark_cancel_job")

        r = asyncio.run(submit.execute({"sql": "SELECT 1"}))
        job_id = r.data["data"]["job_id"]
        mod._query_store[job_id]["status"] = "RUNNING"

        r2 = asyncio.run(cancel.execute({"job_id": job_id}))
        assert r2.data["data"]["cancel_requested"] == "true"
        assert mod._query_store[job_id]["status"] == "CANCELLED"

    def test_cancel_unknown_id(self):
        t = ToolRegistry.get("spark_cancel_job")
        result = asyncio.run(t.execute({"job_id": "nonexistent"}))
        assert result.error is not None


ToolRegistry.clear()
ToolRegistry.discover("src/tools/builtin")
