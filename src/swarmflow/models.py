"""Pydantic data models for SwarmFlow."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# --- Task Models ---


class TaskStatus(str, Enum):
    PENDING = "pending"
    BLOCKED = "blocked"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    title: str
    description: str = ""
    owner: str = ""
    status: TaskStatus = TaskStatus.PENDING
    blocked_by: list[str] = Field(default_factory=list)
    result: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


# --- Message Models ---


class Message(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    sender: str
    recipient: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    read: bool = False


# --- Agent Models ---


class AgentRole(str, Enum):
    LEADER = "leader"
    WORKER = "worker"


class AgentStatus(str, Enum):
    IDLE = "idle"
    WORKING = "working"
    DONE = "done"
    FAILED = "failed"


class AgentInfo(BaseModel):
    name: str
    role: AgentRole
    status: AgentStatus = AgentStatus.IDLE
    system_prompt: str = ""
    task_ids: list[str] = Field(default_factory=list)
    spawned_at: datetime = Field(default_factory=datetime.utcnow)


# --- Team Models ---


class TeamInfo(BaseModel):
    name: str
    description: str = ""
    goal: str = ""
    leader: str = ""
    agents: dict[str, AgentInfo] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


# --- Report Models ---


class AgentReport(BaseModel):
    agent_name: str
    task_id: str
    summary: str
    details: str = ""
    score: float | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class SwarmReport(BaseModel):
    team_name: str
    goal: str
    agent_reports: list[AgentReport] = Field(default_factory=list)
    final_summary: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
