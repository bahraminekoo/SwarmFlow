"""Shared test fixtures for SwarmFlow tests."""

from __future__ import annotations

import pytest

from swarmflow.config import reset_config
from swarmflow.models import (
    AgentInfo,
    AgentRole,
    Task,
    TaskStatus,
    TeamInfo,
)


@pytest.fixture(autouse=True)
def _reset_global_config():
    """Reset the global config singleton between tests."""
    reset_config()
    yield
    reset_config()


@pytest.fixture
def sample_team() -> TeamInfo:
    return TeamInfo(
        name="test-team",
        goal="Analyze test stocks",
        description="A test team",
        leader="leader",
    )


@pytest.fixture
def sample_tasks() -> list[Task]:
    return [
        Task(id="t1", title="Task A", owner="worker1", status=TaskStatus.PENDING),
        Task(id="t2", title="Task B", owner="worker2", status=TaskStatus.PENDING),
        Task(
            id="t3", title="Task C", owner="worker3",
            blocked_by=["t1", "t2"], status=TaskStatus.BLOCKED,
        ),
    ]


@pytest.fixture
def sample_agents() -> dict[str, AgentInfo]:
    return {
        "leader": AgentInfo(name="leader", role=AgentRole.LEADER),
        "worker1": AgentInfo(name="worker1", role=AgentRole.WORKER, system_prompt="Analyst 1"),
        "worker2": AgentInfo(name="worker2", role=AgentRole.WORKER, system_prompt="Analyst 2"),
        "worker3": AgentInfo(name="worker3", role=AgentRole.WORKER, system_prompt="Analyst 3"),
    }
