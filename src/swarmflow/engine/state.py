"""Shared LangGraph state definition for SwarmFlow."""

from __future__ import annotations

from typing import Annotated, TypedDict

from langgraph.graph import add_messages

from swarmflow.models import AgentInfo, AgentReport, Message, Task, TeamInfo


def merge_dict(left: dict, right: dict) -> dict:
    """Merge two dicts, right takes precedence."""
    merged = {**left}
    merged.update(right)
    return merged


def _item_key(item):
    """Return a hashable key for a list item."""
    item_id = getattr(item, "id", None)
    if item_id is not None:
        return item_id
    # For objects without an id (e.g. AgentReport), use their JSON repr
    if hasattr(item, "model_dump_json"):
        return item.model_dump_json()
    return id(item)


def merge_list(left: list, right: list) -> list:
    """Append items from right to left, avoiding duplicates by id."""
    existing_keys = {_item_key(item) for item in left}
    merged = list(left)
    for item in right:
        key = _item_key(item)
        if key not in existing_keys:
            merged.append(item)
            existing_keys.add(key)
    return merged


class SwarmState(TypedDict, total=False):
    """The shared state that flows through the LangGraph swarm.

    This state is accessible by all agents (leader + workers) and serves
    as the central coordination medium.
    """

    # Team metadata
    team: TeamInfo

    # Task DAG — the scheduler manages this
    tasks: Annotated[list[Task], merge_list]

    # Agent registry
    agents: Annotated[dict[str, AgentInfo], merge_dict]

    # Inter-agent message bus
    inbox: Annotated[list[Message], merge_list]

    # Collected reports from workers
    reports: Annotated[list[AgentReport], merge_list]

    # Final synthesized output
    final_report: str

    # LangGraph message history (for LLM conversations)
    messages: Annotated[list, add_messages]

    # Current phase of execution
    phase: str

    # Which agent is currently active
    current_agent: str

    # Counter for routing logic
    workers_completed: int

    # Error tracking
    errors: Annotated[list[str], merge_list]
