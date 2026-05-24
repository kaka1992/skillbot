"""Tests for Task + TaskManager."""

import sys
sys.path.insert(0, "src")

from uuid import uuid4

from task import Task, TaskManager


class TestTask:
    def test_create(self):
        t = Task(task_id="1", subject="test")
        assert t.task_id == "1"
        assert t.status == "pending"
        assert t.is_ready

    def test_blocked_by(self):
        t1 = Task(task_id="1", subject="a")
        t2 = Task(task_id="2", subject="b")
        t2.blocked_by("1")
        t1.block("2")
        assert not t2.is_ready
        assert "1" in t2._blocked_by
        assert "2" in t1._blocks

    def test_is_ready_when_done(self):
        t = Task(task_id="1", subject="a", status="done")
        assert not t.is_ready

    def test_metadata(self):
        t = Task(task_id="1", subject="r", metadata={"prompt": "hello", "results": []})
        assert t.metadata["prompt"] == "hello"


class TestTaskManager:
    def test_add_and_get(self):
        mgr = TaskManager()
        mgr.add(Task(task_id="1", subject="a"))
        assert mgr.get("1").subject == "a"

    def test_list_by_status(self):
        mgr = TaskManager()
        mgr.add(Task(task_id="1", subject="a", status="done"))
        mgr.add(Task(task_id="2", subject="b", status="pending"))
        assert len(mgr.list(status="pending")) == 1

    def test_set_dep(self):
        mgr = TaskManager()
        mgr.add(Task(task_id="1", subject="a"))
        mgr.add(Task(task_id="2", subject="b"))
        mgr.set_dep("2", ["1"])
        assert not mgr.get("2").is_ready

    def test_ready_tasks(self):
        mgr = TaskManager()
        mgr.add(Task(task_id="1", subject="a"))
        mgr.add(Task(task_id="2", subject="b"))
        mgr.set_dep("2", ["1"])
        ready = mgr.ready_tasks()
        assert len(ready) == 1
        assert ready[0].task_id == "1"

    def test_update(self):
        mgr = TaskManager()
        mgr.add(Task(task_id="1", subject="a"))
        mgr.update("1", status="done", owner="worker")
        t = mgr.get("1")
        assert t.status == "done"
        assert t.owner == "worker"

    def test_remove(self):
        mgr = TaskManager()
        mgr.add(Task(task_id="1", subject="a"))
        assert mgr.remove("1")
        assert mgr.get("1") is None


class TestTaskMetadata:
    def test_review_metadata(self):
        t = Task(task_id=uuid4().hex[:8], subject="review: cell_review",
                 metadata={"sub_name": "cell_review", "prompt": "is this done?",
                           "context": "ctx: var x=1", "results": []})
        assert t.subject == "review: cell_review"
        assert t.metadata["prompt"] == "is this done?"
        assert t.metadata["results"] == []
