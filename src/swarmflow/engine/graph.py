"""LangGraph StateGraph — the core swarm orchestration engine."""

from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, StateGraph

from swarmflow.agents.leader import LeaderAgent
from swarmflow.agents.worker import WorkerAgent
from swarmflow.engine.state import SwarmState
from swarmflow.models import (
    AgentInfo,
    AgentRole,
    TaskStatus,
    TeamInfo,
)

logger = logging.getLogger(__name__)


def _should_continue(state: SwarmState) -> str:
    """Router: decide what happens after the leader plans tasks."""
    phase = state.get("phase", "planning")

    if phase == "complete":
        return END

    if phase == "executing":
        # Check if any workers still have pending/in-progress tasks
        tasks = state.get("tasks", [])
        agents = state.get("agents", {})

        pending_workers = set()
        for task in tasks:
            if task.status in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS):
                if task.owner and task.owner in agents:
                    pending_workers.add(task.owner)

        if pending_workers:
            # Route to the first worker with pending work
            return f"worker_{sorted(pending_workers)[0]}"

        # All tasks done — time to synthesize
        return "synthesize"

    if phase == "synthesizing":
        return "synthesize"

    return END


def build_swarm_graph(
    team: TeamInfo,
    worker_configs: dict[str, str],
) -> StateGraph:
    """Build a LangGraph StateGraph for a swarm team.

    Args:
        team: Team metadata (name, goal, etc.)
        worker_configs: Dict of {worker_name: system_prompt}

    Returns:
        A compiled LangGraph that orchestrates leader + workers.
    """
    # Create agents
    leader = LeaderAgent()
    workers: dict[str, WorkerAgent] = {}
    for name, prompt in worker_configs.items():
        workers[name] = WorkerAgent(name=name, system_prompt=prompt)

    # Build the graph
    graph = StateGraph(SwarmState)

    # --- Node: Leader plans tasks ---
    async def leader_plan(state: SwarmState) -> dict[str, Any]:
        return await leader.invoke(state)

    graph.add_node("leader_plan", leader_plan)

    # --- Node: Each worker executes ---
    for worker_name, worker in workers.items():

        async def make_worker_node(w=worker):
            async def worker_node(state: SwarmState) -> dict[str, Any]:
                return await w.invoke(state)

            return worker_node

        # We need a closure to capture the worker correctly
        async def worker_node(state: SwarmState, _w=worker) -> dict[str, Any]:
            return await _w.invoke(state)

        graph.add_node(f"worker_{worker_name}", worker_node)

    # --- Node: Leader synthesizes results ---
    async def leader_synthesize(state: SwarmState) -> dict[str, Any]:
        state_with_phase = dict(state)
        state_with_phase["phase"] = "synthesizing"
        return await leader.invoke(state_with_phase)

    graph.add_node("synthesize", leader_synthesize)

    # --- Node: Worker dispatcher (runs all ready workers) ---
    async def dispatch_workers(state: SwarmState) -> dict[str, Any]:
        """Run all workers with pending tasks concurrently."""
        import asyncio

        tasks = state.get("tasks", [])

        # Find workers with pending tasks
        pending_workers: set[str] = set()
        for task in tasks:
            if task.status in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS):
                if task.owner and task.owner in workers:
                    pending_workers.add(task.owner)

        if not pending_workers:
            return {"phase": "synthesizing"}

        logger.info(f"Dispatching workers: {pending_workers}")

        # Run all workers concurrently
        results = await asyncio.gather(
            *(workers[name].invoke(state) for name in sorted(pending_workers)),
            return_exceptions=True,
        )

        # Merge results
        merged: dict[str, Any] = {
            "tasks": [],
            "reports": [],
            "inbox": [],
            "errors": [],
        }
        for r in results:
            if isinstance(r, Exception):
                merged["errors"].append(str(r))
                continue
            for key in ("tasks", "reports", "inbox", "errors"):
                if key in r:
                    merged[key].extend(r[key])
            if "agents" in r:
                merged.setdefault("agents", {}).update(r["agents"])

        # Check if all tasks are now done
        all_tasks = list(state.get("tasks", []))
        completed_ids = {t.id for t in merged["tasks"] if t.status == TaskStatus.COMPLETED}
        still_pending = [
            t
            for t in all_tasks
            if t.id not in completed_ids
            and t.status in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED)
        ]

        if not still_pending:
            merged["phase"] = "synthesizing"
        else:
            merged["phase"] = "executing"

        return merged

    graph.add_node("dispatch_workers", dispatch_workers)

    # --- Edges ---
    graph.set_entry_point("leader_plan")
    graph.add_edge("leader_plan", "dispatch_workers")

    # After dispatching, decide: more work or synthesize?
    graph.add_conditional_edges(
        "dispatch_workers",
        lambda state: "synthesize" if state.get("phase") == "synthesizing" else "dispatch_workers",
        {
            "synthesize": "synthesize",
            "dispatch_workers": "dispatch_workers",
        },
    )

    graph.add_edge("synthesize", END)

    return graph


async def run_swarm(
    team_name: str,
    goal: str,
    worker_configs: dict[str, str],
    description: str = "",
    on_state_update: Any = None,
) -> SwarmState:
    """High-level API: build and run a complete swarm.

    Args:
        team_name: Name for the team.
        goal: The team's objective.
        worker_configs: Dict of {worker_name: system_prompt}.
        description: Optional team description.

    Returns:
        The final SwarmState with all results.
    """
    team = TeamInfo(
        name=team_name,
        goal=goal,
        description=description,
        leader="leader",
    )

    # Build agent registry
    agents: dict[str, AgentInfo] = {
        "leader": AgentInfo(name="leader", role=AgentRole.LEADER),
    }
    for name, prompt in worker_configs.items():
        agents[name] = AgentInfo(
            name=name,
            role=AgentRole.WORKER,
            system_prompt=prompt,
        )

    team.agents = agents

    # Build initial state
    initial_state: SwarmState = {
        "team": team,
        "tasks": [],
        "agents": agents,
        "inbox": [],
        "reports": [],
        "final_report": "",
        "messages": [],
        "phase": "planning",
        "current_agent": "leader",
        "workers_completed": 0,
        "errors": [],
    }

    # Build and compile graph
    graph = build_swarm_graph(team, worker_configs)
    compiled = graph.compile()

    # Run the swarm
    logger.info(f"🚀 Launching swarm '{team_name}' with {len(worker_configs)} workers")
    logger.info(f"📎 Goal: {goal}")

    # Notify initial state
    if on_state_update:
        on_state_update(initial_state)

    # Stream execution so we can push updates after each step
    final_state = None
    async for chunk in compiled.astream(initial_state):
        # Each chunk is a dict of {node_name: state_update}
        # Merge into a running view for the callback
        if final_state is None:
            final_state = dict(initial_state)
        for node_name, update in chunk.items():
            if isinstance(update, dict):
                for k, v in update.items():
                    final_state[k] = v
        if on_state_update:
            on_state_update(final_state)

    if final_state is None:
        final_state = initial_state

    logger.info(f"✅ Swarm '{team_name}' completed")
    return final_state
