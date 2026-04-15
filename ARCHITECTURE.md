# SwarmFlow Architecture

SwarmFlow is a lightweight multi-agent swarm orchestration framework built on LangGraph. This document explains the system design.

## Overview

```
User: "Evaluate TSLA, AMD, META"
        │
        ▼
┌─────────────────────────────────────────────────┐
│             SwarmFlow Engine (LangGraph)          │
│                                                  │
│  ┌──────────┐    plan_tasks()   ┌────────────┐  │
│  │  Leader   │─────────────────►│ Dispatcher  │  │
│  │  Agent    │                  │             │  │
│  │          │                  │  Runs all   │  │
│  │  Plans    │                  │  workers    │  │
│  │  tasks,   │                  │  concurrently│ │
│  │  assigns, │   synthesize()   │             │  │
│  │  merges   │◄─────────────────│  Collects   │  │
│  └──────────┘                  │  reports    │  │
│       │                        └─────┬──────┘  │
│       ▼                              │         │
│  Final Report              ┌─────────┴───────┐ │
│                            │   Worker Pool    │ │
│                            │  ┌───┐┌───┐┌───┐│ │
│                            │  │W1 ││W2 ││W3 ││ │
│                            │  └───┘└───┘└───┘│ │
│                            └─────────────────┘ │
└────────────────────────────────────────────────┘
```

## Core Components

### 1. LangGraph StateGraph (`engine/graph.py`)

The orchestration engine is a LangGraph `StateGraph` with three main nodes:

- **`leader_plan`** — The leader agent analyzes the goal and creates a task plan
- **`dispatch_workers`** — Runs all workers with pending tasks concurrently via `asyncio.gather`
- **`synthesize`** — The leader combines all worker reports into a final output

The graph flow is: `leader_plan → dispatch_workers → (loop if tasks remain) → synthesize → END`

Conditional edges handle the loop: after dispatching, if tasks are still pending (e.g., blocked by dependencies), the dispatcher runs again. Once all tasks complete, it routes to synthesis.

### 2. Shared State (`engine/state.py`)

A `TypedDict` that flows through the graph. Key fields:

| Field | Type | Purpose |
|---|---|---|
| `team` | `TeamInfo` | Team metadata (name, goal) |
| `tasks` | `list[Task]` | Task DAG with statuses |
| `agents` | `dict[str, AgentInfo]` | Agent registry |
| `inbox` | `list[Message]` | Inter-agent messages |
| `reports` | `list[AgentReport]` | Worker output reports |
| `phase` | `str` | Current execution phase |
| `final_report` | `str` | Synthesized output |

State fields use custom reducers (e.g., `merge_list`, `merge_dict`) so partial updates from different agents merge cleanly.

### 3. Task Scheduler (`engine/scheduler.py`)

Manages a DAG of tasks with dependency tracking:

- Tasks declare `blocked_by` dependencies (list of task IDs)
- When a task completes, dependents are auto-unblocked
- The scheduler provides `get_ready_tasks()` to find executable work
- Supports topological ordering via dependency chains

### 4. Inter-Agent Inbox (`engine/inbox.py`)

A message bus for agent coordination:

- **Point-to-point**: `send(sender, recipient, content)`
- **Broadcast**: `broadcast(sender, content)` to all known agents
- **Receive**: `receive(recipient)` gets unread messages and marks them read
- **Peek**: `peek(recipient)` reads without consuming

### 5. Agents

#### Leader Agent (`agents/leader.py`)
- **Plan phase**: Calls LLM to break goal into tasks, assigns to workers
- **Synthesize phase**: Combines all worker reports into a final report
- Sends task assignments via inbox messages

#### Worker Agent (`agents/worker.py`)
- Receives assigned tasks from state
- Checks inbox for context from other agents
- Calls LLM with task description + context
- Reports results back to leader via inbox

#### Base Agent (`agents/base.py`)
- Common LLM access (`_call_llm`, `_call_llm_json`)
- Status tracking (idle → working → done/failed)
- Standard `invoke()` interface for LangGraph nodes

### 6. Template System (`engine/templates.py`)

YAML files define team archetypes:

```yaml
name: hedge-fund
description: AI Hedge Fund team
default_goal: "Analyze stocks"
workers:
  - name: buffett-analyst
    system_prompt: "You analyze using value investing..."
  - name: growth-analyst
    system_prompt: "You evaluate growth potential..."
```

One command launches a complete team: `swarmflow launch hedge-fund --goal "..."`

### 7. LLM Factory (`llm.py`)

Creates `ChatOpenAI`-compatible instances for both backends:

- **OpenRouter**: Remote API, supports GPT-4o, Claude, Gemini, etc.
- **Ollama**: Local models, no API key needed

Switchable via `config.yaml` or environment variables.

## Data Flow

```
1. User provides: template name + goal
2. Template → worker_configs (name → system_prompt mapping)
3. Leader agent calls LLM → task plan (JSON)
4. Tasks injected into state, assignments sent via inbox
5. Dispatcher runs all ready workers concurrently
6. Each worker: reads task + inbox → calls LLM → produces report
7. Reports collected in state
8. If blocked tasks remain, unblock check → dispatch again
9. Leader synthesizes all reports → final report
```

## Configuration

Layered config resolution:
1. `config.yaml` (file)
2. Environment variables (override)
3. CLI flags (highest priority)

Key env vars:
- `OPENROUTER_API_KEY` — API key for OpenRouter
- `SWARMFLOW_MODEL` — Override model name
- `OLLAMA_BASE_URL` — Switch to local Ollama

## Dashboard

FastAPI + WebSocket real-time monitoring:
- `/` — Dashboard UI (vanilla HTML/JS)
- `/ws` — WebSocket for live state updates
- `/api/state` — REST endpoint for current state

The dashboard receives state updates from the engine and broadcasts to all connected browser clients.
