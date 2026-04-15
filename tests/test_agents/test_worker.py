"""Tests for the worker agent."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from swarmflow.agents.worker import WorkerAgent
from swarmflow.models import (
    AgentInfo,
    AgentRole,
    Message,
    Task,
    TaskStatus,
    TeamInfo,
)


@pytest.fixture
def worker():
    return WorkerAgent(name="test-worker", system_prompt="You are a test analyst.")


@pytest.fixture
def worker_state():
    return {
        "team": TeamInfo(name="test", goal="Test goal", leader="leader"),
        "tasks": [
            Task(
                id="t1",
                title="Analyze X",
                description="Do analysis",
                owner="test-worker",
                status=TaskStatus.PENDING,
            ),
        ],
        "agents": {
            "leader": AgentInfo(name="leader", role=AgentRole.LEADER),
            "test-worker": AgentInfo(name="test-worker", role=AgentRole.WORKER),
        },
        "inbox": [],
        "reports": [],
        "messages": [],
        "errors": [],
    }


class TestWorkerAgent:
    def test_init(self, worker):
        assert worker.name == "test-worker"
        assert worker.role == AgentRole.WORKER

    @pytest.mark.asyncio
    async def test_run_completes_task(self, worker, worker_state):
        mock_response = {
            "summary": "Analysis complete",
            "details": "Found interesting patterns",
            "data": {"metric": 0.85},
            "score": 0.85,
        }

        with patch.object(
            worker,
            "_call_llm_json",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await worker._run(worker_state)

        assert len(result["reports"]) == 1
        assert result["reports"][0].summary == "Analysis complete"
        assert result["reports"][0].score == 0.85
        assert len(result["inbox"]) == 1
        assert "TASK COMPLETE" in result["inbox"][0].content

    @pytest.mark.asyncio
    async def test_run_skips_completed_tasks(self, worker, worker_state):
        worker_state["tasks"][0].status = TaskStatus.COMPLETED

        with patch.object(worker, "_call_llm_json", new_callable=AsyncMock) as mock_llm:
            result = await worker._run(worker_state)

        mock_llm.assert_not_called()
        assert len(result["reports"]) == 0

    @pytest.mark.asyncio
    async def test_run_handles_llm_error(self, worker, worker_state):
        with patch.object(
            worker,
            "_call_llm_json",
            new_callable=AsyncMock,
            side_effect=Exception("LLM error"),
        ):
            result = await worker._run(worker_state)

        assert len(result["tasks"]) == 1
        assert result["tasks"][0].status == TaskStatus.FAILED
        assert "TASK FAILED" in result["inbox"][0].content

    @pytest.mark.asyncio
    async def test_run_reads_inbox_context(self, worker, worker_state):
        worker_state["inbox"] = [
            Message(sender="leader", recipient="test-worker", content="Focus on risk analysis"),
        ]

        mock_response = {
            "summary": "Done with context",
            "details": "Used leader guidance",
            "data": {},
            "score": 0.9,
        }

        with patch.object(
            worker,
            "_call_llm_json",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_llm:
            await worker._run(worker_state)

        # Verify the prompt included inbox context
        call_args = mock_llm.call_args[0][0]
        assert "Focus on risk analysis" in call_args
