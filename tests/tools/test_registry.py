"""Tests for ToolRegistry, register decorator, and discover."""

import asyncio
import sys

sys.path.insert(0, "src")

import pytest
from tools import ReturnProperty, ToolDef, ToolPreset, ToolRegistry, ToolRequirement, ToolResult, register


class TestToolDef:
    def test_create(self):
        async def fn(p): return ToolResult(data={"ok": True})

        preset = ToolPreset(name="test", description="desc", parameters={})
        t = ToolDef(preset=preset, execute=fn)
        assert t.name == "test"
        assert t.group == "custom"

    def test_custom_group(self):
        async def fn(p): return ToolResult(data={"ok": True})

        preset = ToolPreset(name="t", description="d", parameters={}, group="web")
        t = ToolDef(preset=preset, execute=fn)
        assert t.group == "web"


class TestToolPreset:
    def test_create_preset(self):
        p = ToolPreset(
            name="search",
            description="Search the web",
            parameters={"type": "object", "properties": {"query": {"type": "string"}}},
            returns={"text": ReturnProperty(type="str"), "count": ReturnProperty(type="int")},
            group="web",
        )
        assert p.name == "search"
        assert p.returns["text"].type == "str"
        assert p.returns["count"].type == "int"

    def test_register_preset_and_impl(self):
        async def ddg(params): return ToolResult(data={"text": "results"})

        async def google(params): return ToolResult(data={"text": "better results"})

        preset = ToolPreset(name="search", description="d", parameters={}, returns={"text": ReturnProperty(type="str")})
        ToolRegistry.register_preset(preset)
        ToolRegistry.register_impl("search", "duckduckgo", ddg)

        # default impl not set — fallback to first registered
        ToolRegistry.register_impl("search", "default", ddg)
        ToolRegistry.register_impl("search", "google", google)

        assert ToolRegistry.get("search").preset is preset
        assert ToolRegistry.get("search", "duckduckgo").execute is ddg
        assert ToolRegistry.get("search", "google").execute is google

    def test_list_presets(self):
        ToolRegistry.clear()
        ToolRegistry.register_preset(ToolPreset(name="a", description="d", parameters={}))
        ToolRegistry.register_preset(ToolPreset(name="b", description="d", parameters={}, group="web"))
        assert len(ToolRegistry.list_presets()) == 2
        assert len(ToolRegistry.list_presets(group="web")) == 1

    def test_list_impls(self):
        async def fn(p): return ToolResult(data={})

        preset = ToolPreset(name="x", description="d", parameters={})
        ToolRegistry.register_preset(preset)
        ToolRegistry.register_impl("x", "default", fn)
        ToolRegistry.register_impl("x", "v2", fn)
        assert ToolRegistry.list_impls("x") == ["default", "v2"]

    def test_register_impl_unknown_preset(self):
        async def fn(p): return ToolResult(data={})

        with pytest.raises(KeyError, match="not found"):
            ToolRegistry.register_impl("nonexistent", "default", fn)


class TestToolRegistry:
    def setup_method(self):
        ToolRegistry.clear()

    def test_add_and_get(self):
        async def fn(p): return ToolResult(data={"ok": True})

        preset = ToolPreset(name="a", description="d", parameters={})
        t = ToolDef(preset=preset, execute=fn)
        ToolRegistry.add(t)
        assert ToolRegistry.get("a") is t

    def test_add_duplicate_overwrites(self):
        async def fn1(p): return ToolResult(data={"ok": True})

        async def fn2(p): return ToolResult(data={"updated": True})

        p1 = ToolPreset(name="a", description="d", parameters={})
        p2 = ToolPreset(name="a", description="d", parameters={})
        ToolRegistry.add(ToolDef(preset=p1, execute=fn1))
        ToolRegistry.add(ToolDef(preset=p2, execute=fn2))
        assert ToolRegistry.get("a").execute is fn2

    def test_remove(self):
        async def fn(p): return ToolResult(data={"ok": True})

        preset = ToolPreset(name="a", description="d", parameters={})
        ToolRegistry.add(ToolDef(preset=preset, execute=fn))
        assert ToolRegistry.remove("a") is True
        assert ToolRegistry.get("a") is None

    def test_remove_missing(self):
        assert ToolRegistry.remove("nonexistent") is False

    def test_list_all(self):
        async def fn(p): return ToolResult(data={"ok": True})

        ToolRegistry.add(ToolDef(preset=ToolPreset(name="b", description="d", parameters={}), execute=fn))
        ToolRegistry.add(ToolDef(preset=ToolPreset(name="a", description="d", parameters={}), execute=fn))
        assert [t.name for t in ToolRegistry.list()] == ["a", "b"]

    def test_list_by_group(self):
        async def fn(p): return ToolResult(data={"ok": True})

        ToolRegistry.add(ToolDef(preset=ToolPreset(name="a", description="d", parameters={}, group="web"), execute=fn))
        ToolRegistry.add(ToolDef(preset=ToolPreset(name="b", description="d", parameters={}, group="file"), execute=fn))
        assert len(ToolRegistry.list(group="web")) == 1
        assert ToolRegistry.list(group="web")[0].name == "a"


class TestRegisterDecorator:
    def setup_method(self):
        ToolRegistry.clear()

    def test_decorator_registers_tool(self):
        @register(name="hello", description="Say hello", parameters={"type": "object"})
        async def hello(params: dict) -> ToolResult:
            return ToolResult(data={"text": "hello"})

        t = ToolRegistry.get("hello")
        assert t is not None
        assert t.name == "hello"
        assert t.preset.name == "hello"

    def test_decorator_execute(self):
        @register(name="echo", description="Echo", parameters={})
        async def echo(params: dict) -> ToolResult:
            return ToolResult(data={"msg": params.get("msg", "")})

        t = ToolRegistry.get("echo")
        assert t is not None
        import asyncio

        result = asyncio.run(t.execute({"msg": "hi"}))
        assert result.data["msg"] == "hi"

    def test_decorator_with_returns(self):
        @register(
            name="r",
            description="d",
            parameters={},
            returns={"text": ReturnProperty(type="str"), "count": ReturnProperty(type="int")},
        )
        async def r_fn(params: dict) -> ToolResult:
            return ToolResult(data={"text": "ok", "count": 1})

        t = ToolRegistry.get("r")
        assert t.preset.returns["text"].type == "str"
        assert t.preset.returns["count"].type == "int"


class TestDiscover:
    def setup_method(self):
        ToolRegistry.clear()

    def test_discover_loads_tools(self):
        import os
        import tempfile

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
    return ToolResult(data={"found": True})
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


class TestPreferredImpl:
    def setup_method(self):
        ToolRegistry.clear()

    def _register_two_impls(self):
        async def default_fn(p): return ToolResult(data={"impl": "default"})
        async def v2_fn(p): return ToolResult(data={"impl": "v2"})

        preset = ToolPreset(name="t", description="d", parameters={})
        ToolRegistry.register_preset(preset)
        ToolRegistry.register_impl("t", "default", default_fn)
        ToolRegistry.register_impl("t", "v2", v2_fn)

    def test_get_returns_default_when_no_preference(self):
        self._register_two_impls()
        t = ToolRegistry.get("t")
        result = asyncio.run(t.execute({}))
        assert result.data["impl"] == "default"

    def test_get_returns_preferred_impl(self):
        self._register_two_impls()
        ToolRegistry.set_preferred("t", "v2")
        t = ToolRegistry.get("t")
        result = asyncio.run(t.execute({}))
        assert result.data["impl"] == "v2"

    def test_explicit_impl_overrides_preference(self):
        self._register_two_impls()
        ToolRegistry.set_preferred("t", "v2")
        t = ToolRegistry.get("t", impl="default")
        result = asyncio.run(t.execute({}))
        assert result.data["impl"] == "default"

    def test_set_preferred_for_group(self):
        async def fn(p): return ToolResult(data={"impl": "v2"})

        p1 = ToolPreset(name="a", description="d", parameters={}, group="spark")
        p2 = ToolPreset(name="b", description="d", parameters={}, group="spark")
        p3 = ToolPreset(name="c", description="d", parameters={}, group="file")

        for p in [p1, p2, p3]:
            ToolRegistry.register_preset(p)
            ToolRegistry.register_impl(p.name, "default", fn)
            ToolRegistry.register_impl(p.name, "v2", fn)

        ToolRegistry.set_preferred_for_group("spark", "v2")

        assert ToolRegistry.get_preferred("a") == "v2"
        assert ToolRegistry.get_preferred("b") == "v2"
        assert ToolRegistry.get_preferred("c") is None  # file group not affected

    def test_set_preferred_unknown_preset_raises(self):
        with pytest.raises(KeyError, match="not found"):
            ToolRegistry.set_preferred("nonexistent", "v2")

    def test_set_preferred_unknown_impl_raises(self):
        preset = ToolPreset(name="t", description="d", parameters={})
        ToolRegistry.register_preset(preset)

        with pytest.raises(KeyError, match="not found"):
            ToolRegistry.set_preferred("t", "nonexistent")

    def test_reset_preferred_single(self):
        self._register_two_impls()
        ToolRegistry.set_preferred("t", "v2")
        ToolRegistry.reset_preferred("t")
        assert ToolRegistry.get_preferred("t") is None
        t = ToolRegistry.get("t")
        result = asyncio.run(t.execute({}))
        assert result.data["impl"] == "default"

    def test_reset_preferred_all(self):
        self._register_two_impls()

        p2 = ToolPreset(name="t2", description="d", parameters={})
        ToolRegistry.register_preset(p2)
        ToolRegistry.register_impl("t2", "default", lambda p: ToolResult(data={}))
        ToolRegistry.register_impl("t2", "v2", lambda p: ToolResult(data={}))

        ToolRegistry.set_preferred("t", "v2")
        ToolRegistry.set_preferred("t2", "v2")
        ToolRegistry.reset_preferred()

        assert ToolRegistry.get_preferred("t") is None
        assert ToolRegistry.get_preferred("t2") is None


class TestParameterDefaults:
    def setup_method(self):
        ToolRegistry.clear()

    def test_default_value_applied(self):
        async def fn(p): return ToolResult(data={"x": p["x"]})

        preset = ToolPreset(
            name="t",
            description="d",
            parameters={
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "default": 42},
                },
            },
        )
        ToolRegistry.register_preset(preset)
        ToolRegistry.register_impl("t", "default", fn)
        t = ToolRegistry.get("t")
        result = asyncio.run(t.execute({}))
        assert result.data["x"] == 42

    def test_explicit_overrides_default(self):
        async def fn(p): return ToolResult(data={"x": p["x"]})

        preset = ToolPreset(
            name="t",
            description="d",
            parameters={
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "default": 42},
                },
            },
        )
        ToolRegistry.register_preset(preset)
        ToolRegistry.register_impl("t", "default", fn)
        t = ToolRegistry.get("t")
        result = asyncio.run(t.execute({"x": 99}))
        assert result.data["x"] == 99

    def test_no_defaults_no_effect(self):
        async def fn(p): return ToolResult(data={"y": p.get("y")})

        preset = ToolPreset(
            name="t",
            description="d",
            parameters={
                "type": "object",
                "properties": {
                    "y": {"type": "string"},
                },
            },
        )
        ToolRegistry.register_preset(preset)
        ToolRegistry.register_impl("t", "default", fn)
        t = ToolRegistry.get("t")
        result = asyncio.run(t.execute({}))
        assert result.data["y"] is None


class TestToolRequirements:
    def setup_method(self):
        ToolRegistry.clear()

    def test_all_satisfied_returns_empty_errors(self):
        preset = ToolPreset(name="t", description="d", parameters={})
        ToolRegistry.register_preset(preset)
        ToolRegistry.register_impl("t", "default", lambda p: ToolResult(data={}),
                                   requires=[ToolRequirement(type="env", key="PATH")])
        t = ToolRegistry.get("t")
        assert t.check_requirements() == []

    def test_missing_env_var(self):
        preset = ToolPreset(name="t", description="d", parameters={})
        ToolRegistry.register_preset(preset)
        ToolRegistry.register_impl("t", "default", lambda p: ToolResult(data={}),
                                   requires=[ToolRequirement(type="env", key="NONEXISTENT_VAR_XYZ")])
        t = ToolRegistry.get("t")
        errors = t.check_requirements()
        assert len(errors) == 1
        assert "NONEXISTENT_VAR_XYZ" in errors[0]

    def test_missing_import(self):
        preset = ToolPreset(name="t", description="d", parameters={})
        ToolRegistry.register_preset(preset)
        ToolRegistry.register_impl("t", "default", lambda p: ToolResult(data={}),
                                   requires=[ToolRequirement(type="import", key="nonexistent_pkg_xyz")])
        t = ToolRegistry.get("t")
        errors = t.check_requirements()
        assert len(errors) == 1
        assert "nonexistent_pkg_xyz" in errors[0]

    def test_description_in_error(self):
        preset = ToolPreset(name="t", description="d", parameters={})
        ToolRegistry.register_preset(preset)
        ToolRegistry.register_impl("t", "default", lambda p: ToolResult(data={}),
                                   requires=[ToolRequirement(type="env", key="NONEXISTENT_VAR",
                                                             description="My custom dep")])
        t = ToolRegistry.get("t")
        errors = t.check_requirements()
        assert "My custom dep" in errors[0]

    def test_multiple_errors_collected(self):
        preset = ToolPreset(name="t", description="d", parameters={})
        ToolRegistry.register_preset(preset)
        ToolRegistry.register_impl("t", "default", lambda p: ToolResult(data={}),
                                   requires=[
                                       ToolRequirement(type="env", key="NONEXISTENT_A"),
                                       ToolRequirement(type="env", key="NONEXISTENT_B"),
                                   ])
        t = ToolRegistry.get("t")
        assert len(t.check_requirements()) == 2

    def test_no_requires_returns_empty(self):
        preset = ToolPreset(name="t", description="d", parameters={})
        ToolRegistry.register_preset(preset)
        ToolRegistry.register_impl("t", "default", lambda p: ToolResult(data={}))
        t = ToolRegistry.get("t")
        assert t.check_requirements() == []

    def test_check_all(self):
        ToolRegistry.register_preset(ToolPreset(name="ok", description="d", parameters={}))
        ToolRegistry.register_impl("ok", "default", lambda p: ToolResult(data={}))
        ToolRegistry.register_preset(ToolPreset(name="bad", description="d", parameters={}))
        ToolRegistry.register_impl("bad", "default", lambda p: ToolResult(data={}),
                                   requires=[ToolRequirement(type="env", key="NONEXISTENT_VAR")])
        result = ToolRegistry.check_all()
        assert "ok" not in result
        assert "bad" in result
        assert len(result["bad"]) == 1

    def test_impl_decorator_passes_requires(self):
        preset = ToolPreset(name="t", description="d", parameters={})
        ToolRegistry.register_preset(preset)

        # register via register_impl directly (same path @impl uses internally)
        ToolRegistry.register_impl("t", "default", lambda p: ToolResult(data={}),
                                   requires=[ToolRequirement(type="env", key="NONEXISTENT_VAR_XYZ")])
        t = ToolRegistry.get("t")
        errors = t.check_requirements()
        assert len(errors) == 1
