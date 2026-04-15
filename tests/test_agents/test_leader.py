"""Tests for the leader agent."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from swarmflow.agents.leader import LeaderAgent
from swarmflow.models import (
    AgentInfo,
    AgentReport,
    AgentRole,
    Task,
    TaskStatus,
    TeamInfo,
)


@pytest.fixture
def leader():
    return LeaderAgent()


@pytest.fixture
def leader_state():
    return {
        "team": TeamInfo(name="test", goal="Analyze stocks", leader="leader"),
        "tasks": [],
        "agents": {
            "leader": AgentInfo(name="leader", role=AgentRole.LEADER),
            "analyst1": AgentInfo(
                name="analyst1",
                role=AgentRole.WORKER,
                system_prompt="Value analyst",
            ),
            "analyst2": AgentInfo(
                name="analyst2",
                role=AgentRole.WORKER,
                system_prompt="Growth analyst",
            ),
        },
        "inbox": [],
        "reports": [],
        "messages": [],
        "phase": "planning",
        "errors": [],
    }


class TestLeaderAgent:
    def test_init(self, leader):
        assert leader.name == "leader"
        assert leader.role == AgentRole.LEADER

    @pytest.mark.asyncio
    async def test_plan_tasks(self, leader, leader_state):
        mock_plan = {
            "tasks": [
                {
                    "id": "t1",
                    "title": "Value analysis",
                    "description": "Analyze value",
                    "owner": "analyst1",
                    "blocked_by": [],
                },
                {
                    "id": "t2",
                    "title": "Growth analysis",
                    "description": "Analyze growth",
                    "owner": "analyst2",
                    "blocked_by": [],
                },
            ]
        }

        with patch.object(leader, "_call_llm_json", new_callable=AsyncMock, return_value=mock_plan):
            result = await leader.plan_tasks(leader_state)

        assert len(result["tasks"]) == 2
        assert result["tasks"][0].title == "Value analysis"
        assert result["tasks"][0].owner == "analyst1"
        assert result["phase"] == "executing"
        assert len(result["inbox"]) == 2  # Task assignment messages

    @pytest.mark.asyncio
    async def test_plan_tasks_with_deps(self, leader, leader_state):
        mock_plan = {
            "tasks": [
                {
                    "id": "t1",
                    "title": "Gather data",
                    "description": "Get data",
                    "owner": "analyst1",
                    "blocked_by": [],
                },
                {
                    "id": "t2",
                    "title": "Analyze data",
                    "description": "Analyze",
                    "owner": "analyst2",
                    "blocked_by": ["t1"],
                },
            ]
        }

        with patch.object(leader, "_call_llm_json", new_callable=AsyncMock, return_value=mock_plan):
            result = await leader.plan_tasks(leader_state)

        assert result["tasks"][0].status == TaskStatus.PENDING
        assert result["tasks"][1].status == TaskStatus.BLOCKED

    @pytest.mark.asyncio
    async def test_synthesize(self, leader, leader_state):
        leader_state["reports"] = [
            AgentReport(
                agent_name="analyst1",
                task_id="t1",
                summary="Value looks good",
                details="Strong moat",
                score=0.8,
            ),
            AgentReport(
                agent_name="analyst2",
                task_id="t2",
                summary="Growth promising",
                details="TAM expanding",
                score=0.7,
            ),
        ]
        leader_state["tasks"] = [
            Task(id="t1", title="Value analysis", owner="analyst1", status=TaskStatus.COMPLETED),
            Task(id="t2", title="Growth analysis", owner="analyst2", status=TaskStatus.COMPLETED),
        ]

        mock_report = "# Final Report\nBuy recommendation"
        with patch.object(
            leader,
            "_call_llm",
            new_callable=AsyncMock,
            return_value=mock_report,
        ):
            result = await leader.synthesize(leader_state)

        assert result["final_report"] == "# Final Report\nBuy recommendation"
        assert result["phase"] == "complete"

    @pytest.mark.asyncio
    async def test_run_routes_to_plan(self, leader, leader_state):
        mock_plan = {"tasks": []}
        with patch.object(leader, "_call_llm_json", new_callable=AsyncMock, return_value=mock_plan):
            result = await leader._run(leader_state)
        assert "phase" in result

    @pytest.mark.asyncio
    async def test_run_routes_to_synthesize(self, leader, leader_state):
        leader_state["phase"] = "synthesizing"
        with patch.object(leader, "_call_llm", new_callable=AsyncMock, return_value="Report"):
            result = await leader._run(leader_state)
        assert result["phase"] == "complete"
