"""Task DAG scheduler with dependency resolution and auto-unblocking."""

from __future__ import annotations

from datetime import datetime

from swarmflow.models import Task, TaskStatus


class Scheduler:
    """Manages a task DAG with dependency tracking.

    Tasks can declare `blocked_by` dependencies. The scheduler automatically
    transitions tasks from BLOCKED → PENDING when all their dependencies
    are resolved (completed).
    """

    def __init__(self, tasks: list[Task] | None = None):
        self._tasks: dict[str, Task] = {}
        for task in tasks or []:
            self._tasks[task.id] = task

    @property
    def tasks(self) -> list[Task]:
        return list(self._tasks.values())

    def add_task(self, task: Task) -> Task:
        """Add a task to the DAG. Auto-sets status to BLOCKED if it has unresolved dependencies."""
        if task.blocked_by:
            unresolved = [
                dep_id
                for dep_id in task.blocked_by
                if dep_id in self._tasks and self._tasks[dep_id].status != TaskStatus.COMPLETED
            ]
            if unresolved:
                task.status = TaskStatus.BLOCKED
        self._tasks[task.id] = task
        return task

    def complete_task(self, task_id: str, result: str = "") -> Task:
        """Mark a task as completed and auto-unblock dependents."""
        task = self._tasks[task_id]
        task.status = TaskStatus.COMPLETED
        task.result = result
        task.updated_at = datetime.utcnow()
        self._unblock_dependents(task_id)
        return task

    def fail_task(self, task_id: str, error: str = "") -> Task:
        """Mark a task as failed."""
        task = self._tasks[task_id]
        task.status = TaskStatus.FAILED
        task.result = error
        task.updated_at = datetime.utcnow()
        return task

    def start_task(self, task_id: str) -> Task:
        """Mark a task as in-progress."""
        task = self._tasks[task_id]
        if task.status in (TaskStatus.PENDING, TaskStatus.BLOCKED):
            task.status = TaskStatus.IN_PROGRESS
            task.updated_at = datetime.utcnow()
        return task

    def get_ready_tasks(self) -> list[Task]:
        """Get all tasks that are PENDING (not blocked, not started)."""
        return [t for t in self._tasks.values() if t.status == TaskStatus.PENDING]

    def get_blocked_tasks(self) -> list[Task]:
        """Get all tasks that are still BLOCKED."""
        return [t for t in self._tasks.values() if t.status == TaskStatus.BLOCKED]

    def get_task(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    def get_tasks_by_owner(self, owner: str) -> list[Task]:
        return [t for t in self._tasks.values() if t.owner == owner]

    def get_tasks_by_status(self, status: TaskStatus) -> list[Task]:
        return [t for t in self._tasks.values() if t.status == status]

    def all_completed(self) -> bool:
        """Check if all tasks are completed or failed (none pending/blocked/in_progress)."""
        return all(
            t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED) for t in self._tasks.values()
        )

    def _unblock_dependents(self, completed_task_id: str) -> list[Task]:
        """Auto-unblock tasks whose dependencies are now fully resolved."""
        unblocked = []
        for task in self._tasks.values():
            if task.status != TaskStatus.BLOCKED:
                continue
            if completed_task_id not in task.blocked_by:
                continue
            # Check if ALL dependencies are now completed
            all_resolved = all(
                self._tasks.get(dep_id) is not None
                and self._tasks[dep_id].status == TaskStatus.COMPLETED
                for dep_id in task.blocked_by
            )
            if all_resolved:
                task.status = TaskStatus.PENDING
                task.updated_at = datetime.utcnow()
                unblocked.append(task)
        return unblocked

    def summary(self) -> dict[str, int]:
        """Get a summary count by status."""
        counts: dict[str, int] = {}
        for task in self._tasks.values():
            counts[task.status.value] = counts.get(task.status.value, 0) + 1
        return counts
