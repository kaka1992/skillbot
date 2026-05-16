"""Tests for builtin tools."""

import json
import sys

sys.path.insert(0, "src")

import pytest
from tools import ToolRegistry


class TestBuiltinTools:
    """Test that builtin tools are registered and executable."""

    @classmethod
    def setup_class(cls):
        ToolRegistry.clear()
        ToolRegistry.discover("src/tools/builtin")

    def test_all_builtins_registered(self):
        names = {t.name for t in ToolRegistry.list()}
        assert "web_search" in names
        assert "file_read" in names
        assert "json_extract" in names

    def test_groups(self):
        by_group = {
            t.name: t.group for t in ToolRegistry.list()
        }
        assert by_group["web_search"] == "web"
        assert by_group["file_read"] == "file"
        assert by_group["json_extract"] == "data"

    def test_json_extract_simple_key(self):
        t = ToolRegistry.get("json_extract")
        import asyncio

        result = asyncio.run(t.execute({
            "json_str": json.dumps({"name": "Alice", "age": 30}),
            "key_path": "name",
        }))
        assert result.content == '"Alice"'

    def test_json_extract_nested_key(self):
        t = ToolRegistry.get("json_extract")
        import asyncio

        result = asyncio.run(t.execute({
            "json_str": json.dumps({"data": {"users": [{"name": "Bob"}]}}),
            "key_path": "data.users.0.name",
        }))
        assert result.content == '"Bob"'

    def test_json_extract_invalid_json(self):
        t = ToolRegistry.get("json_extract")
        import asyncio

        result = asyncio.run(t.execute({
            "json_str": "{not json}",
            "key_path": "x",
        }))
        assert result.error is not None
        assert "Invalid JSON" in result.error

    def test_json_extract_missing_key(self):
        t = ToolRegistry.get("json_extract")
        import asyncio

        result = asyncio.run(t.execute({
            "json_str": json.dumps({"a": 1}),
            "key_path": "b",
        }))
        assert result.error is not None

    def test_file_read_success(self):
        import tempfile, os

        t = ToolRegistry.get("file_read")
        import asyncio

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("hello from file")
            tmp = f.name
        try:
            result = asyncio.run(t.execute({"path": tmp}))
            assert result.content == "hello from file"
        finally:
            os.unlink(tmp)

    def test_file_read_not_found(self):
        t = ToolRegistry.get("file_read")
        import asyncio

        result = asyncio.run(t.execute({"path": "/nonexistent/file.txt"}))
        assert result.error is not None
        assert "not found" in result.error
