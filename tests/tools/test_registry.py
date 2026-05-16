"""Tests for ToolRegistry, register decorator, and discover."""

import sys
sys.path.insert(0, "src")

import pytest
from tools import ToolDef, ToolRegistry, ToolResult, register


class TestToolDef:
    def test_create(self):
        async def fn(p): return ToolResult(content="ok")
        t = ToolDef(name="test", description="desc", parameters={}, execute=fn)
        assert t.name == "test"
        assert t.group == "custom"

    def test_custom_group(self):
        async def fn(p): return ToolResult(content="ok")
        t = ToolDef(name="t", description="d", parameters={}, execute=fn, group="web")
        assert t.group == "web"


class TestToolRegistry:
    def setup_method(self):
        ToolRegistry.clear()

    def test_add_and_get(self):
        async def fn(p): return ToolResult(content="ok")
        t = ToolDef(name="a", description="d", parameters={}, execute=fn)
        ToolRegistry.add(t)
        assert ToolRegistry.get("a") is t

    def test_add_duplicate_raises(self):
        async def fn(p): return ToolResult(content="ok")
        t = ToolDef(name="a", description="d", parameters={}, execute=fn)
        ToolRegistry.add(t)
        with pytest.raises(ValueError, match="already registered"):
            ToolRegistry.add(t)

    def test_remove(self):
        async def fn(p): return ToolResult(content="ok")
        ToolRegistry.add(ToolDef(name="a", description="d", parameters={}, execute=fn))
        assert ToolRegistry.remove("a") is True
        assert ToolRegistry.get("a") is None

    def test_remove_missing(self):
        assert ToolRegistry.remove("nonexistent") is False

    def test_list_all(self):
        async def fn(p): return ToolResult(content="ok")
        ToolRegistry.add(ToolDef(name="b", description="d", parameters={}, execute=fn))
        ToolRegistry.add(ToolDef(name="a", description="d", parameters={}, execute=fn))
        assert [t.name for t in ToolRegistry.list()] == ["a", "b"]

    def test_list_by_group(self):
        async def fn(p): return ToolResult(content="ok")
        ToolRegistry.add(ToolDef(name="a", description="d", parameters={}, execute=fn, group="web"))
        ToolRegistry.add(ToolDef(name="b", description="d", parameters={}, execute=fn, group="file"))
        assert len(ToolRegistry.list(group="web")) == 1
        assert ToolRegistry.list(group="web")[0].name == "a"


class TestRegisterDecorator:
    def setup_method(self):
        ToolRegistry.clear()

    def test_decorator_registers_tool(self):
        @register(name="hello", description="Say hello", parameters={"type": "object"})
        async def hello(params: dict) -> ToolResult:
            return ToolResult(content="hello")

        t = ToolRegistry.get("hello")
        assert t is not None
        assert t.name == "hello"
        assert t.description == "Say hello"

    def test_decorator_execute(self):
        @register(name="echo", description="Echo", parameters={})
        async def echo(params: dict) -> ToolResult:
            return ToolResult(content=params.get("msg", ""))

        t = ToolRegistry.get("echo")  # type: ignore[assignment]
        assert t is not None
        import asyncio
        result = asyncio.run(t.execute({"msg": "hi"}))
        assert result.content == "hi"


class TestDiscover:
    def setup_method(self):
        ToolRegistry.clear()

    def test_discover_loads_tools(self):
        import tempfile, os
        with tempfile.TemporaryDirectory() as tmp:
            tool_file = os.path.join(tmp, "my_tool.py")
            with open(tool_file, "w") as f:
                f.write("""
from tools import ToolResult, register

@register(
    name="discovered_tool",
    description="found via discover",
    parameters={"type": "object"}
)
async def discovered_tool(params: dict) -> ToolResult:
    return ToolResult(content="found")
""")
            new = ToolRegistry.discover(tmp)
            assert len(new) == 1
            assert new[0].name == "discovered_tool"

    def test_discover_empty_dir(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            new = ToolRegistry.discover(tmp)
            assert new == []

    def test_discover_missing_dir(self):
        new = ToolRegistry.discover("/nonexistent/path")
        assert new == []
