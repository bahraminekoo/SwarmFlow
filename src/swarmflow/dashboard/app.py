"""FastAPI dashboard with WebSocket real-time updates."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)

# In-memory store for dashboard state (updated by the swarm engine)
_dashboard_state: dict[str, Any] = {
    "team": None,
    "agents": {},
    "tasks": [],
    "messages": [],
    "reports": [],
    "phase": "idle",
    "final_report": "",
    "errors": [],
    "updated_at": None,
}

_connected_clients: set[WebSocket] = set()


def update_dashboard_state(state: dict[str, Any]) -> None:
    """Update the dashboard state from the swarm engine."""
    global _dashboard_state

    if "team" in state and state["team"] is not None:
        team = state["team"]
        _dashboard_state["team"] = {
            "name": team.name,
            "goal": team.goal,
            "description": team.description,
        }

    if "agents" in state:
        agents = {}
        for name, info in state["agents"].items():
            agents[name] = {
                "name": info.name,
                "role": info.role.value,
                "status": info.status.value,
            }
        _dashboard_state["agents"] = agents

    if "tasks" in state:
        tasks = []
        for task in state["tasks"]:
            tasks.append(
                {
                    "id": task.id,
                    "title": task.title,
                    "description": task.description,
                    "owner": task.owner,
                    "status": task.status.value,
                    "result": task.result,
                    "blocked_by": task.blocked_by,
                }
            )
        _dashboard_state["tasks"] = tasks

    if "inbox" in state:
        messages = []
        for msg in state["inbox"]:
            messages.append(
                {
                    "id": msg.id,
                    "sender": msg.sender,
                    "recipient": msg.recipient,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "read": msg.read,
                }
            )
        _dashboard_state["messages"] = messages

    if "reports" in state:
        reports = []
        for report in state["reports"]:
            reports.append(
                {
                    "agent_name": report.agent_name,
                    "task_id": report.task_id,
                    "summary": report.summary,
                    "score": report.score,
                    "data": report.data,
                }
            )
        _dashboard_state["reports"] = reports

    if "phase" in state:
        _dashboard_state["phase"] = state["phase"]

    if "final_report" in state:
        _dashboard_state["final_report"] = state["final_report"]

    if "errors" in state:
        _dashboard_state["errors"] = state["errors"]

    _dashboard_state["updated_at"] = datetime.utcnow().isoformat()

    # Broadcast to all connected WebSocket clients
    asyncio.ensure_future(_broadcast_state())


async def _broadcast_state() -> None:
    """Send current state to all connected WebSocket clients."""
    global _connected_clients
    if not _connected_clients:
        return
    data = json.dumps(_dashboard_state, default=str)
    disconnected = set()
    for ws in _connected_clients:
        try:
            await ws.send_text(data)
        except Exception:
            disconnected.add(ws)
    _connected_clients -= disconnected


def create_app() -> FastAPI:
    """Create the FastAPI dashboard application."""
    app = FastAPI(title="SwarmFlow Dashboard", version="0.1.0")

    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def index():
        """Serve the dashboard HTML."""
        html_path = Path(__file__).parent / "static" / "index.html"
        if html_path.exists():
            return html_path.read_text()
        return _get_inline_dashboard_html()

    @app.get("/api/state")
    async def get_state():
        """Get current swarm state as JSON."""
        return _dashboard_state

    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket):
        """WebSocket endpoint for real-time updates."""
        await ws.accept()
        _connected_clients.add(ws)
        logger.info(f"Dashboard client connected ({len(_connected_clients)} total)")
        try:
            # Send current state immediately
            await ws.send_text(json.dumps(_dashboard_state, default=str))
            # Keep connection alive
            while True:
                await ws.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            _connected_clients.discard(ws)
            logger.info(f"Dashboard client disconnected ({len(_connected_clients)} total)")

    return app


def _get_inline_dashboard_html() -> str:
    """Fallback inline HTML if static file is missing."""
    return (
        "<!DOCTYPE html><html><head>"
        "<title>SwarmFlow Dashboard</title></head>"
        "<body><h1>SwarmFlow Dashboard</h1>"
        "<p>Static files not found. Run from project root.</p>"
        "</body></html>"
    )
