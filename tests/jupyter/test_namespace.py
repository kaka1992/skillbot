"""Tests for Namespace."""

import sys
sys.path.insert(0, "src")

import pytest
from jupyter.namespace import Namespace


class FakeShell:
    user_ns: dict = {}


class TestNamespace:
    def test_list_filters_internals(self):
        s = FakeShell()
        s.user_ns = {"_hidden": 1, "In": [1], "my_var": 42, "my_func": lambda: 1}
        ns = Namespace(s)
        assert list(ns.vars().keys()) == ["my_var"]

    def test_get(self):
        s = FakeShell()
        s.user_ns = {"a": 1}
        ns = Namespace(s)
        assert ns.get("a") == 1
        assert ns.get("missing", "x") == "x"

    def test_inject_and_remove(self):
        s = FakeShell()
        ns = Namespace(s)
        ns.inject("x", 42)
        assert s.user_ns["x"] == 42
        assert ns.remove("x") is True
        assert "x" not in s.user_ns
        assert ns.remove("x") is False

    def test_remove_protects_internals(self):
        s = FakeShell()
        s.user_ns = {"In": [1]}
        ns = Namespace(s)
        assert ns.remove("In") is False

    def test_context_full(self):
        s = FakeShell()
        s.user_ns = {"a": 1, "b": "hello"}
        ns = Namespace(s)
        ctx = ns.context()
        assert "Available variables:" in ctx
        assert "a: int" in ctx
        assert "b: str len=5" in ctx

    def test_context_empty(self):
        s = FakeShell()
        ns = Namespace(s)
        assert ns.context() == ""

    def test_delta_new_vars(self):
        s = FakeShell()
        s.user_ns = {"a": 1}
        ns = Namespace(s)
        ns.context()  # mark a as seen
        s.user_ns["b"] = 2
        d = ns.delta()
        assert "b: int" in d
        assert "a: int" not in d

    def test_delta_no_change(self):
        s = FakeShell()
        s.user_ns = {"a": 1}
        ns = Namespace(s)
        ns.context()
        assert ns.delta() == ""

    def test_reset(self):
        s = FakeShell()
        s.user_ns = {"a": 1}
        ns = Namespace(s)
        ns.context()
        ns.reset()
        s.user_ns["b"] = 2
        d = ns.delta()
        assert "a: int" in d
        assert "b: int" in d

    def test_track_cell(self):
        s = FakeShell()
        s.user_ns = {"x": 1}
        ns = Namespace(s)
        ns.track_cell("print(x)", "1")
        ctx = ns.context()
        assert "x: int" in ctx
        assert "print(x)" in ctx
        assert "→ 1" in ctx


class TestDescribe:
    def test_dataframe(self):
        import pandas as pd
        from jupyter.namespace import _describe
        df = pd.DataFrame({"a": [1, 2, 3]})
        assert "DataFrame shape=(3, 1)" in _describe("df", df)

    def test_series(self):
        import pandas as pd
        from jupyter.namespace import _describe
        s = pd.Series([1, 2])
        assert "Series len=2" in _describe("s", s)

    def test_list(self):
        from jupyter.namespace import _describe
        assert "list len=3" in _describe("x", [1, 2, 3])

    def test_dict(self):
        from jupyter.namespace import _describe
        assert "dict len=2" in _describe("d", {"a": 1, "b": 2})

    def test_str(self):
        from jupyter.namespace import _describe
        assert "str len=5" in _describe("s", "hello")
