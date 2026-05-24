"""Tests for hook system — HookRegistry, HookGroup, HookResult, dispatch."""
import sys
sys.path.insert(0, "src")

import pytest
from jupyter.hook import (
    Hook, HookEvent, HookStatus, HookResult, HookGroup, HookRegistry,
    AgentCodeReviewHook,
)


@pytest.fixture(autouse=True)
def _clear_registry():
    HookRegistry.clear()
    yield
    HookRegistry.clear()


# ---- HookResult ----

class TestHookResult:
    def test_defaults(self):
        r = HookResult(HookStatus.SUCCESS)
        assert r.status == "success"
        assert r.message == ""
        assert r.detail == ""

    def test_with_message_and_detail(self):
        r = HookResult(HookStatus.FAILED_STOP, "msg", "detail")
        assert r.status == "failed_stop"
        assert r.message == "msg"
        assert r.detail == "detail"


# ---- Hook priority ----

class TestHookPriority:
    def test_priority_ordering(self):
        class A(Hook):
            def on_event(self, event, context):
                return HookResult(HookStatus.SUCCESS)
        class B(Hook):
            def on_event(self, event, context):
                return HookResult(HookStatus.SUCCESS)
        a = A()
        b = B()
        a.priority = 5
        b.priority = 1
        assert b < a
        assert not a < b

    def test_default_priority(self):
        class H(Hook):
            def on_event(self, event, context):
                return HookResult(HookStatus.SUCCESS)
        assert H().priority == 0


# ---- HookGroup ----

class TestHookGroup:
    def test_add_and_retrieve(self):
        class A(Hook):
            def on_event(self, event, context):
                return HookResult(HookStatus.SUCCESS)
        class B(Hook):
            def on_event(self, event, context):
                return HookResult(HookStatus.SUCCESS)
        g = HookGroup("test")
        h1 = A()
        h1.priority = 5
        h2 = B()
        h2.priority = 1
        g.add(h1)
        g.add(h2)
        assert g.hooks[0].priority == 1
        assert g.hooks[1].priority == 5

    def test_disabled_returns_empty(self):
        class H(Hook):
            def on_event(self, event, context):
                return HookResult(HookStatus.SUCCESS)
        g = HookGroup("test", enabled=False)
        g.add(H())
        assert g.hooks == []

    def test_enabled_returns_hooks(self):
        class H(Hook):
            def on_event(self, event, context):
                return HookResult(HookStatus.SUCCESS)
        g = HookGroup("test", enabled=True)
        g.add(H())
        assert len(g.hooks) == 1


# ---- HookRegistry ----

class TestRegistry:
    def test_register_group_to_events(self):
        class H(Hook):
            def on_event(self, event, context):
                return HookResult(HookStatus.SUCCESS)
        g = HookGroup("test")
        h = H()
        g.add(h)
        HookRegistry.register_group(g, HookEvent.CODE_REVIEW)
        assert HookEvent.CODE_REVIEW in HookRegistry._events
        assert HookRegistry._events[HookEvent.CODE_REVIEW] == [h]

    def test_dispatch_empty_returns_success(self):
        r = HookRegistry.dispatch(HookEvent.CODE_REVIEW, {})
        assert r.status == HookStatus.SUCCESS

    def test_dispatch_runs_hooks_in_priority_order(self):
        order = []
        class A(Hook):
            priority = 1
            def on_event(self, event, context):
                order.append(1)
                return HookResult(HookStatus.SUCCESS)
        class B(Hook):
            priority = 2
            def on_event(self, event, context):
                order.append(2)
                return HookResult(HookStatus.SUCCESS)

        g = HookGroup("test")
        g.add(B()); g.add(A())
        HookRegistry.register_group(g, HookEvent.AGENT_CELL_REVIEW)
        HookRegistry.dispatch(HookEvent.AGENT_CELL_REVIEW, {})
        assert order == [1, 2]

    def test_dispatch_stops_on_failed_stop(self):
        called = []
        class Stopper(Hook):
            priority = 1
            def on_event(self, event, context):
                called.append("stopper")
                return HookResult(HookStatus.FAILED_STOP, "handled")
        class Never(Hook):
            priority = 2
            def on_event(self, event, context):
                called.append("never")
                return HookResult(HookStatus.SUCCESS)

        g = HookGroup("test")
        g.add(Stopper()); g.add(Never())
        HookRegistry.register_group(g, HookEvent.AGENT_CELL_REVIEW)
        r = HookRegistry.dispatch(HookEvent.AGENT_CELL_REVIEW, {})
        assert r.status == HookStatus.FAILED_STOP
        assert called == ["stopper"]

    def test_dispatch_continues_on_failed_continue(self):
        called = []
        class Failer(Hook):
            priority = 1
            def on_event(self, event, context):
                called.append("failer")
                return HookResult(HookStatus.FAILED_CONTINUE, "oops")
        class Next(Hook):
            priority = 2
            def on_event(self, event, context):
                called.append("next")
                return HookResult(HookStatus.SUCCESS)

        g = HookGroup("test")
        g.add(Failer()); g.add(Next())
        HookRegistry.register_group(g, HookEvent.AGENT_CELL_REVIEW)
        r = HookRegistry.dispatch(HookEvent.AGENT_CELL_REVIEW, {})
        assert r.status == HookStatus.SUCCESS
        assert called == ["failer", "next"]

    def test_clear_removes_all(self):
        class H(Hook):
            def on_event(self, event, context):
                return HookResult(HookStatus.SUCCESS)
        g = HookGroup("test")
        g.add(H())
        HookRegistry.register_group(g, HookEvent.CODE_REVIEW)
        HookRegistry.clear()
        assert HookRegistry._events == {}


# ---- CodeReview dispatch ----

class TestCodeReviewDispatch:
    def test_hook_mutates_code_list_in_context(self):
        class UppercaseHook(Hook):
            def on_event(self, event, context):
                context["code_list"] = [c.upper() for c in context["code_list"]]
                return HookResult(HookStatus.SUCCESS)

        g = HookGroup("test")
        g.add(UppercaseHook())
        HookRegistry.register_group(g, HookEvent.CODE_REVIEW)
        ctx = {"code_list": ["hello", "world"]}
        HookRegistry.dispatch(HookEvent.CODE_REVIEW, ctx)
        assert ctx["code_list"] == ["HELLO", "WORLD"]


# ---- AgentCodeReviewHook ----

class TestAgentCodeReviewHook:
    def test_single_cell_skips(self):
        hook = AgentCodeReviewHook()
        ctx = {"code_list": ["print(1)"]}
        r = hook.on_event(HookEvent.CODE_REVIEW, ctx)
        assert r.status == HookStatus.SUCCESS
        assert ctx["code_list"] == ["print(1)"]

    def test_empty_list_skips(self):
        hook = AgentCodeReviewHook()
        ctx = {"code_list": []}
        r = hook.on_event(HookEvent.CODE_REVIEW, ctx)
        assert r.status == HookStatus.SUCCESS
