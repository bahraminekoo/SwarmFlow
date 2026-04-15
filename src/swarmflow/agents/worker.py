"""Worker agent — receives a task, executes it via LLM, and reports back."""

from __future__ import annotations

import logging
from typing import Any

from swarmflow.agents.base import BaseAgent
from swarmflow.engine.state import SwarmState
from swarmflow.models import (
    AgentReport,
    AgentRole,
    Message,
    Task,
    TaskStatus,
)

logger = logging.getLogger(__name__)


class WorkerAgent(BaseAgent):
    """A specialized worker agent that executes a single task and reports results."""

    def __init__(self, name: str, system_prompt: str = ""):
        super().__init__(
            name=name,
            role=AgentRole.WORKER,
            system_prompt=system_prompt or f"You are {name}, a specialized worker agent.",
        )

    async def _run(self, state: SwarmState) -> dict[str, Any]:
        """Execute assigned tasks and produce reports."""
        tasks = state.get("tasks", [])
        my_tasks = [t for t in tasks if t.owner == self.name]

        reports: list[AgentReport] = []
        inbox_messages: list[Message] = []
        updated_tasks: list[Task] = []

        for task in my_tasks:
            if task.status not in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS):
                continue

            logger.info(f"[{self.name}] Working on task: {task.title}")
            task.status = TaskStatus.IN_PROGRESS

            # Check inbox for context from other agents
            incoming = [
                m for m in state.get("inbox", []) if m.recipient == self.name and not m.read
            ]
            context = ""
            if incoming:
                context = "\n\nMessages from teammates:\n"
                for msg in incoming:
                    context += f"- From {msg.sender}: {msg.content}\n"
                    msg.read = True

            # Build the execution prompt
            team = state["team"]
            prompt = f"""You are working on a task for the team.

Team Goal: {team.goal}

Your Task: {task.title}
Description: {task.description}
{context}

Execute this task thoroughly. Provide:
1. A detailed analysis or implementation based on your specialty
2. Key findings or results
3. Any recommendations or concerns

Respond with JSON:
{{
  "summary": "One-line summary of your findings",
  "details": "Detailed analysis in markdown format",
  "data": {{"key_metric_1": "value", "key_metric_2": "value"}},
  "score": 0.0
}}

The score should be 0.0-1.0 representing your confidence or a relevant metric.
For investment analysis: 0.0 = strong sell, 0.5 = hold, 1.0 = strong buy.
For research: 0.0 = low confidence, 1.0 = high confidence.
For code review: 0.0 = critical issues, 1.0 = excellent quality."""

            try:
                result = await self._call_llm_json(prompt, state)

                report = AgentReport(
                    agent_name=self.name,
                    task_id=task.id,
                    summary=result.get("summary", "Task completed"),
                    details=result.get("details", ""),
                    score=result.get("score"),
                    data=result.get("data", {}),
                )
                reports.append(report)

                task.status = TaskStatus.COMPLETED
                task.result = report.summary

                # Report back to leader
                inbox_messages.append(
                    Message(
                        sender=self.name,
                        recipient="leader",
                        content=f"TASK COMPLETE [{task.id}]: {report.summary}",
                    )
                )

                logger.info(f"[{self.name}] Completed task: {task.title}")

            except Exception as e:
                logger.error(f"[{self.name}] Failed task {task.id}: {e}")
                task.status = TaskStatus.FAILED
                task.result = str(e)

                inbox_messages.append(
                    Message(
                        sender=self.name,
                        recipient="leader",
                        content=f"TASK FAILED [{task.id}]: {str(e)}",
                    )
                )

            updated_tasks.append(task)

        return {
            "tasks": updated_tasks,
            "reports": reports,
            "inbox": inbox_messages,
        }
