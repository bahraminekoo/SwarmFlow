"""Tests for the task DAG scheduler."""

from __future__ import annotations

from swarmflow.engine.scheduler import Scheduler
from swarmflow.models import Task, TaskStatus


class TestScheduler:
    def test_add_task_no_deps(self):
        sched = Scheduler()
        task = Task(id="t1", title="Simple task", owner="w1")
        added = sched.add_task(task)
        assert added.status == TaskStatus.PENDING
        assert len(sched.tasks) == 1

    def test_add_task_with_unresolved_deps(self):
        sched = Scheduler()
        t1 = Task(id="t1", title="Dep task", owner="w1")
        sched.add_task(t1)
        t2 = Task(id="t2", title="Blocked task", owner="w2", blocked_by=["t1"])
        added = sched.add_task(t2)
        assert added.status == TaskStatus.BLOCKED

    def test_complete_task_unblocks_dependents(self):
        sched = Scheduler()
        t1 = Task(id="t1", title="First", owner="w1")
        t2 = Task(id="t2", title="Second", owner="w2", blocked_by=["t1"])
        sched.add_task(t1)
        sched.add_task(t2)

        assert sched.get_task("t2").status == TaskStatus.BLOCKED

        sched.complete_task("t1", result="Done")

        assert sched.get_task("t1").status == TaskStatus.COMPLETED
        assert sched.get_task("t1").result == "Done"
        assert sched.get_task("t2").status == TaskStatus.PENDING

    def test_multiple_deps_all_must_complete(self):
        sched = Scheduler()
        sched.add_task(Task(id="t1", title="A", owner="w1"))
        sched.add_task(Task(id="t2", title="B", owner="w2"))
        sched.add_task(Task(id="t3", title="C", owner="w3", blocked_by=["t1", "t2"]))

        assert sched.get_task("t3").status == TaskStatus.BLOCKED

        sched.complete_task("t1")
        assert sched.get_task("t3").status == TaskStatus.BLOCKED

        sched.complete_task("t2")
        assert sched.get_task("t3").status == TaskStatus.PENDING

    def test_start_task(self):
        sched = Scheduler()
        sched.add_task(Task(id="t1", title="A", owner="w1"))
        sched.start_task("t1")
        assert sched.get_task("t1").status == TaskStatus.IN_PROGRESS

    def test_fail_task(self):
        sched = Scheduler()
        sched.add_task(Task(id="t1", title="A", owner="w1"))
        sched.fail_task("t1", error="Something broke")
        assert sched.get_task("t1").status == TaskStatus.FAILED
        assert sched.get_task("t1").result == "Something broke"

    def test_get_ready_tasks(self):
        sched = Scheduler()
        sched.add_task(Task(id="t1", title="A", owner="w1"))
        sched.add_task(Task(id="t2", title="B", owner="w2"))
        sched.add_task(Task(id="t3", title="C", owner="w3", blocked_by=["t1"]))

        ready = sched.get_ready_tasks()
        assert len(ready) == 2
        assert {t.id for t in ready} == {"t1", "t2"}

    def test_get_tasks_by_owner(self):
        sched = Scheduler()
        sched.add_task(Task(id="t1", title="A", owner="w1"))
        sched.add_task(Task(id="t2", title="B", owner="w1"))
        sched.add_task(Task(id="t3", title="C", owner="w2"))

        w1_tasks = sched.get_tasks_by_owner("w1")
        assert len(w1_tasks) == 2

    def test_all_completed(self):
        sched = Scheduler()
        sched.add_task(Task(id="t1", title="A", owner="w1"))
        sched.add_task(Task(id="t2", title="B", owner="w2"))

        assert not sched.all_completed()

        sched.complete_task("t1")
        assert not sched.all_completed()

        sched.complete_task("t2")
        assert sched.all_completed()

    def test_all_completed_with_failures(self):
        sched = Scheduler()
        sched.add_task(Task(id="t1", title="A", owner="w1"))
        sched.add_task(Task(id="t2", title="B", owner="w2"))

        sched.complete_task("t1")
        sched.fail_task("t2")
        assert sched.all_completed()

    def test_summary(self):
        sched = Scheduler()
        sched.add_task(Task(id="t1", title="A", owner="w1"))
        sched.add_task(Task(id="t2", title="B", owner="w2"))
        sched.add_task(Task(id="t3", title="C", owner="w3", blocked_by=["t1"]))

        summary = sched.summary()
        assert summary["pending"] == 2
        assert summary["blocked"] == 1

    def test_init_with_tasks(self, sample_tasks):
        sched = Scheduler(tasks=sample_tasks)
        assert len(sched.tasks) == 3
