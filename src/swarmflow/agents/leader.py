"""Leader agent — plans tasks, spawns workers, monitors progress, synthesizes results."""

from __future__ import annotations

import logging
from typing import Any

from swarmflow.agents.base import BaseAgent
from swarmflow.engine.state import SwarmState
from swarmflow.models import (
    AgentRole,
    Message,
    Task,
    TaskStatus,
)

logger = logging.getLogger(__name__)

LEADER_SYSTEM_PROMPT = """You are the Leader Agent in a SwarmFlow multi-agent swarm.

Your responsibilities:
1. PLAN: Break down the team's goal into specific tasks with clear descriptions.
2. ASSIGN: Each task gets assigned to a named worker agent.
3. MONITOR: Track task completion and handle failures.
4. SYNTHESIZE: Combine all worker reports into a final cohesive report.

You coordinate a team of specialized worker agents. Each worker has a specific role
and expertise defined by their system prompt.

Always respond with structured JSON when asked to plan or synthesize."""


class LeaderAgent(BaseAgent):
    """The swarm leader — orchestrates the entire workflow."""

    def __init__(self, name: str = "leader"):
        super().__init__(
            name=name,
            role=AgentRole.LEADER,
            system_prompt=LEADER_SYSTEM_PROMPT,
        )

    async def plan_tasks(self, state: SwarmState) -> dict[str, Any]:
        """Phase 1: Analyze the goal and create a task plan for workers."""
        team = state["team"]
        agents = state.get("agents", {})

        worker_names = [name for name, info in agents.items() if info.role == AgentRole.WORKER]
        worker_descriptions = "\n".join(
            f"- **{name}**: {agents[name].system_prompt[:200]}" for name in worker_names
        )

        prompt = f"""The team goal is: {team.goal}

Available worker agents:
{worker_descriptions}

Create a task plan. For each worker, create exactly ONE task that plays to their specialty.
Tasks can have dependencies using `blocked_by` (list of task IDs that must complete first).

Respond with JSON:
{{
  "tasks": [
    {{
      "id": "t1",
      "title": "Short task title",
      "description": "Detailed description of what to do",
      "owner": "worker_name",
      "blocked_by": []
    }}
  ]
}}"""

        result = await self._call_llm_json(prompt, state)
        tasks = []
        for t in result.get("tasks", []):
            task = Task(
                id=t["id"],
                title=t["title"],
                description=t.get("description", ""),
                owner=t["owner"],
                blocked_by=t.get("blocked_by", []),
            )
            # Set status based on dependencies
            if task.blocked_by:
                task.status = TaskStatus.BLOCKED
            tasks.append(task)

        logger.info(f"[{self.name}] Created {len(tasks)} tasks")

        # Send task assignments via inbox
        inbox_messages = []
        for task in tasks:
            if task.owner:
                msg = Message(
                    sender=self.name,
                    recipient=task.owner,
                    content=f"TASK ASSIGNMENT [{task.id}]: {task.title}\n\n{task.description}",
                )
                inbox_messages.append(msg)

        return {
            "tasks": tasks,
            "inbox": inbox_messages,
            "phase": "executing",
            "current_agent": worker_names[0] if worker_names else self.name,
        }

    async def synthesize(self, state: SwarmState) -> dict[str, Any]:
        """Phase 3: Combine all worker reports into a final report."""
        team = state["team"]
        reports = state.get("reports", [])
        tasks = state.get("tasks", [])

        # Build context from reports
        report_text = ""
        for report in reports:
            report_text += f"\n### {report.agent_name} — {report.summary}\n"
            report_text += f"{report.details}\n"
            if report.data:
                report_text += f"Data: {report.data}\n"

        # Build task completion status
        task_summary = ""
        for task in tasks:
            status_icon = {
                TaskStatus.COMPLETED: "✅",
                TaskStatus.FAILED: "❌",
                TaskStatus.IN_PROGRESS: "🔄",
                TaskStatus.PENDING: "⏳",
                TaskStatus.BLOCKED: "🚫",
            }.get(task.status, "❓")
            task_summary += f"{status_icon} [{task.id}] {task.title} → {task.owner}\n"

        prompt = f"""You are synthesizing the results from a multi-agent swarm.

Team Goal: {team.goal}

Task Completion Status:
{task_summary}

Worker Reports:
{report_text}

Create a comprehensive final report that:
1. Summarizes key findings from each worker
2. Identifies patterns and connections across reports
3. Provides actionable recommendations
4. Highlights any conflicts or gaps between worker findings

Write the report in clear, professional Markdown format."""

        final_report = await self._call_llm(prompt, state)
        logger.info(f"[{self.name}] Final report synthesized ({len(final_report)} chars)")

        return {
            "final_report": final_report,
            "phase": "complete",
        }

    async def _run(self, state: SwarmState) -> dict[str, Any]:
        """Route to the appropriate phase."""
        phase = state.get("phase", "planning")
        if phase == "planning":
            return await self.plan_tasks(state)
        elif phase == "synthesizing":
            return await self.synthesize(state)
        else:
            return {}
