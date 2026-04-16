# 🐝 SwarmFlow

**Lightweight multi-agent swarm orchestration with LangGraph**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-ready-blue.svg)](Dockerfile)

> **One command. Multiple AI agents. Coordinated results.**
>
> SwarmFlow lets AI agents form swarms, divide complex work, communicate in real-time, and deliver synthesized results — all orchestrated by LangGraph.

---

## 🎬 Demo

![SwarmFlow Dashboard Demo](assets/demo.gif)

---

## ✨ What is SwarmFlow?

SwarmFlow is a **LangGraph-native agent swarm orchestration framework**. It orchestrates multiple LLM-powered agents in-process — planning tasks, dividing work, communicating via an inbox system, and synthesizing results — making it self-contained, easy to demo, and production-ready.

```
Human: "Evaluate TSLA, AMD, META for Q2 2026 portfolio allocation"
  │
  ▼
🦞 Leader Agent ──► Plans tasks, assigns to workers
  │
  ├──► 🤖 Buffett Analyst    (value investing analysis)
  ├──► 🤖 Growth Analyst     (disruption & TAM analysis)
  ├──► 🤖 Technical Analyst  (price action & indicators)
  ├──► 🤖 Fundamentals       (financial ratios)
  ├──► 🤖 Sentiment Analyst  (news & insider signals)
  └──► 🤖 Risk Manager       (downside assessment)
          │
          ▼
    📊 Synthesized Report (buy/hold/sell with reasoning)
```

## 🎯 Key Features

- **🦞 Swarm Intelligence** — Leader agent spawns workers, assigns tasks, monitors progress, synthesizes results
- **📋 Task DAG** — Dependency-aware task scheduling with auto-unblocking
- **💬 Inter-Agent Messaging** — Agents communicate via an inbox system (send, receive, broadcast)
- **🎪 Team Templates** — YAML files define reusable team archetypes (hedge fund, research, startup pitch)
- **📊 Real-Time Dashboard** — FastAPI + WebSocket monitoring UI
- **🔌 Dual LLM Backend** — OpenRouter (GPT-4o, Claude, Gemini) + Ollama (local models) — switchable via config
- **🏗️ Built on LangGraph** — StateGraph with conditional edges, concurrent worker execution, state reducers

## 🚀 Quick Start

### Install

```bash
pip install -e .
```

### Set your API key

```bash
# Option A: OpenRouter (recommended — access to GPT-4o, Claude, Gemini, etc.)
export OPENROUTER_API_KEY=sk-or-v1-your-key-here

# Option B: Ollama (free, local)
export OLLAMA_BASE_URL=http://localhost:11434
```

### Launch a swarm

```bash
# AI Hedge Fund — 7 agents analyze stocks
swarmflow launch hedge-fund --goal "Evaluate TSLA, AMD, META for Q2 2026 portfolio allocation"

# AI Research Lab — 5 agents review a topic
swarmflow launch research-lab --goal "Research the state of multi-agent AI systems"

# Startup Pitch Analyzer — 4 agents evaluate a startup idea
swarmflow launch startup-pitch --goal "Evaluate an AI personal finance assistant for Series A"
```

### Or use the Python API

```python
import asyncio
from swarmflow.engine.graph import run_swarm
from swarmflow.engine.templates import load_template_by_name

template = load_template_by_name("hedge-fund")
result = asyncio.run(run_swarm(
    team_name="my-fund",
    goal="Evaluate TSLA, AMD, META for Q2 2026 portfolio allocation",
    worker_configs=template.get_worker_configs(),
))
print(result["final_report"])
```

## 📋 Available Templates

| Template | Agents | Use Case |
|---|---|---|
| `hedge-fund` | 7 (6 analysts + risk manager) | Investment analysis with multi-strategy signals |
| `research-lab` | 5 (survey, methods, frontier, critic, practitioner) | Deep literature review and research synthesis |
| `startup-pitch` | 4 (market, financial, competitor, pitch) | Startup idea evaluation and pitch analysis |

Create your own template — just add a YAML file:

```yaml
name: my-team
description: My custom swarm team
default_goal: "Do something amazing"
workers:
  - name: specialist-1
    system_prompt: "You are an expert in X..."
  - name: specialist-2
    system_prompt: "You are an expert in Y..."
```

## 📊 Real-Time Dashboard

Monitor your swarm from a web browser:

```bash
swarmflow dashboard --port 8080
```

The dashboard shows:
- 🎯 Team goal and phase
- 🤖 Agent roster with live status
- 📋 Task board (pending → in progress → done)
- 💬 Inter-agent message feed
- 📊 Worker reports with confidence scores
- 📝 Final synthesized report

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│             SwarmFlow Engine (LangGraph)          │
│                                                  │
│  ┌──────────┐                  ┌─────────────┐  │
│  │  Leader   │──plan_tasks()──►│  Dispatcher  │  │
│  │  Agent    │                 │             │  │
│  │          │                 │  async.gather│  │
│  │          │◄─synthesize()───│  all workers │  │
│  └──────────┘                 └──────┬──────┘  │
│       │                              │         │
│       ▼                     ┌────────┴───────┐ │
│  Final Report               │  Worker Agents  │ │
│                             │ ┌──┐┌──┐┌──┐  │ │
│                             │ │W1││W2││W3│  │ │
│                             │ └──┘└──┘└──┘  │ │
│                             └────────────────┘ │
└────────────────────────────────────────────────┘
```

**Graph flow:** `leader_plan → dispatch_workers → (loop if blocked tasks) → synthesize → END`

See [ARCHITECTURE.md](ARCHITECTURE.md) for the deep dive.

## ⚙️ Configuration

### Config file (`config.yaml`)

```yaml
llm:
  provider: "openrouter"          # or "ollama"
  model: "openai/gpt-4o"          # any OpenRouter model
  base_url: "https://openrouter.ai/api/v1"
  temperature: 0.3
  max_tokens: 4096

database:
  path: "./data/swarmflow.db"

dashboard:
  host: "0.0.0.0"
  port: 8080
```

### Environment variables

| Variable | Description |
|---|---|
| `OPENROUTER_API_KEY` | OpenRouter API key |
| `SWARMFLOW_MODEL` | Override model (e.g. `anthropic/claude-3.5-sonnet`) |
| `OLLAMA_BASE_URL` | Ollama URL (auto-switches provider to Ollama) |

## 🐳 Docker

```bash
# Build and run dashboard
docker compose up

# Run a swarm
docker compose --profile run up swarm-run
```

## 🧪 Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
make test

# Lint
make lint

# Format
make format
```

## 🗺️ Roadmap

- [x] Core engine (LangGraph StateGraph)
- [x] Leader + Worker agents
- [x] Task DAG with dependency resolution
- [x] Inter-agent messaging
- [x] YAML template system
- [x] 3 built-in templates (hedge fund, research, startup pitch)
- [x] Typer CLI
- [x] FastAPI + WebSocket dashboard
- [x] Docker support
- [x] GitHub Actions CI
- [ ] Human-in-the-loop approval checkpoints
- [ ] SQLite persistence for task/message history
- [ ] Streaming output (token-by-token in dashboard)
- [ ] Agent memory (cross-run learning)
- [ ] Plugin system for custom tools (web search, code execution)

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

[MIT](LICENSE)

