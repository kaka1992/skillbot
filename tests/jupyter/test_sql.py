"""Tests for SqlRunner."""
import sys

sys.path.insert(0, "src")

import pytest
from tools import ToolRegistry, ToolPreset, ToolResult
from jupyter.dsl.sql import SqlRunner


# mock spark tool implementations
async def _mock_analyze(params):
    return ToolResult(data={"success": "true", "command": "spark_analyze_query", "data": {"plan": "== Physical Plan ==\nMockPlan"}})

async def _mock_submit(params):
    return ToolResult(data={"success": "true", "command": "spark_submit_query", "data": {"job_id": "abc123", "status": "RUNNING"}})

async def _mock_status_running(params):
    return ToolResult(data={"success": "true", "command": "spark_get_job_status", "data": {"job_id": "abc123", "status": "RUNNING"}})

async def _mock_status_finished(params):
    return ToolResult(data={"success": "true", "command": "spark_get_job_status", "data": {"job_id": "abc123", "status": "FINISHED"}})

async def _mock_cancel(params):
    return ToolResult(data={"success": "true", "command": "spark_cancel_job", "data": {"job_id": "abc123", "cancel_requested": "true"}})

async def _mock_result(params):
    return ToolResult(data={"success": "true", "command": "spark_get_query_result", "data": {"job_id": "abc123", "sample_data": [["name", "age"], ["Alice", 30]], "content_row_count": 1}})


@pytest.fixture(autouse=True)
def _register_mock_tools():
    ToolRegistry.clear()
    for name, fn in [
        ("spark_analyze_query", _mock_analyze),
        ("spark_submit_query", _mock_submit),
        ("spark_get_job_status", _mock_status_running),
        ("spark_cancel_job", _mock_cancel),
        ("spark_get_query_result", _mock_result),
    ]:
        preset = ToolPreset(name=name, description="d", parameters={"type": "object", "properties": {}})
        ToolRegistry.register_preset(preset)
        ToolRegistry.register_impl(name, "default", fn)
    yield
    ToolRegistry.clear()


class TestSqlRunnerSubmit:
    def test_submit_returns_job_id(self):
        runner = SqlRunner()
        result = runner.submit("SELECT 1")
        assert result["data"]["job_id"] == "abc123"

    def test_submit_progress(self):
        events = []
        runner = SqlRunner()
        runner.submit("SELECT 1", on_progress=lambda p, d: events.append((p, d)))
        assert ("submit", {"job_id": "abc123"}) in events


class TestSqlRunnerQuery:
    def test_query_full_flow(self):
        # register finished status for poll to succeed
        ToolRegistry.clear()
        for name, fn in [
            ("spark_analyze_query", _mock_analyze),
            ("spark_submit_query", _mock_submit),
            ("spark_get_job_status", _mock_status_finished),
            ("spark_cancel_job", _mock_cancel),
            ("spark_get_query_result", _mock_result),
        ]:
            preset = ToolPreset(name=name, description="d", parameters={"type": "object", "properties": {}})
            ToolRegistry.register_preset(preset)
            ToolRegistry.register_impl(name, "default", fn)

        events = []
        runner = SqlRunner(poll_interval=0, timeout=10)
        result = runner.query("SELECT 1", on_progress=lambda p, d: events.append(p))
        assert result["data"]["sample_data"] == [["name", "age"], ["Alice", 30]]
        assert "analyze" in events
        assert "submit" in events
        assert "poll" in events
        assert "result" in events

    def test_query_raises_when_tools_unavailable(self):
        ToolRegistry.clear()
        runner = SqlRunner()
        with pytest.raises(RuntimeError, match="spark tools not available"):
            runner.query("SELECT 1")

    def test_query_timeout(self):
        # _mock_status_running never finishes → timeout
        ToolRegistry.clear()
        for name, fn in [
            ("spark_analyze_query", _mock_analyze),
            ("spark_submit_query", _mock_submit),
            ("spark_get_job_status", _mock_status_running),
            ("spark_cancel_job", _mock_cancel),
            ("spark_get_query_result", _mock_result),
        ]:
            preset = ToolPreset(name=name, description="d", parameters={"type": "object", "properties": {}})
            ToolRegistry.register_preset(preset)
            ToolRegistry.register_impl(name, "default", fn)

        runner = SqlRunner(poll_interval=0, timeout=1)
        with pytest.raises(TimeoutError):
            runner.query("SELECT 1")


class TestSqlRunnerCancel:
    def test_cancel(self):
        runner = SqlRunner()
        result = runner.cancel("abc123")
        assert result["data"]["cancel_requested"] == "true"


class TestSqlRunnerResult:
    def test_result(self):
        runner = SqlRunner()
        result = runner.result("abc123", limit=50)
        assert result["data"]["content_row_count"] == 1


class TestAgentConfigTools:
    def test_tools_section_parsed(self):
        """Verify YAML tools section is parsed without crashing."""
        import yaml
        yaml_str = """
tools:
  paths:
    - /tmp/nonexistent_tools/
  preferences:
    presets:
      spark_analyze_query: v2
    groups:
      spark: databricks
"""
        cfg = yaml.safe_load(yaml_str) or {}
        tools_cfg = cfg.get("tools") or {}
        assert tools_cfg["paths"] == ["/tmp/nonexistent_tools/"]
        assert tools_cfg["preferences"]["presets"]["spark_analyze_query"] == "v2"
        assert tools_cfg["preferences"]["groups"]["spark"] == "databricks"

    def test_tools_section_optional(self):
        """Verify missing tools section is handled gracefully."""
        import yaml
        cfg = yaml.safe_load("agent: claude-code") or {}
        tools_cfg = cfg.get("tools") or {}
        assert tools_cfg.get("paths") is None
        assert tools_cfg.get("preferences") is None
