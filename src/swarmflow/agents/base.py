"""Base agent class for SwarmFlow agents."""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from swarmflow.engine.state import SwarmState
from swarmflow.llm import create_llm
from swarmflow.models import AgentInfo, AgentRole, AgentStatus

logger = logging.getLogger(__name__)


class BaseAgent:
    """Base class for all SwarmFlow agents.

    Provides:
    - LLM access via `self.llm`
    - State read/write helpers
    - Message sending/receiving via inbox
    - Standard invoke interface for LangGraph nodes
    """

    def __init__(self, name: str, role: AgentRole, system_prompt: str = ""):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.llm = create_llm()

    def get_info(self) -> AgentInfo:
        return AgentInfo(
            name=self.name,
            role=self.role,
            system_prompt=self.system_prompt,
        )

    async def invoke(self, state: SwarmState) -> dict[str, Any]:
        """Main entry point — called by LangGraph as a node function.

        Subclasses must override `_run` to implement their logic.
        Returns a partial state dict to merge back into the graph state.
        """
        logger.info(f"[{self.name}] Starting execution")
        try:
            # Update agent status
            agents = dict(state.get("agents", {}))
            if self.name in agents:
                agents[self.name].status = AgentStatus.WORKING
            result = await self._run(state)
            if self.name in agents:
                agents[self.name].status = AgentStatus.DONE
            result["agents"] = agents
            return result
        except Exception as e:
            logger.error(f"[{self.name}] Error: {e}")
            agents = dict(state.get("agents", {}))
            if self.name in agents:
                agents[self.name].status = AgentStatus.FAILED
            return {
                "agents": agents,
                "errors": [f"[{self.name}] {str(e)}"],
            }

    async def _run(self, state: SwarmState) -> dict[str, Any]:
        """Implement agent logic. Must return a partial state dict."""
        raise NotImplementedError

    async def _call_llm(self, prompt: str, state: SwarmState | None = None) -> str:
        """Call the LLM with a system prompt + user prompt."""
        messages = [SystemMessage(content=self.system_prompt)]
        if state and state.get("messages"):
            # Include recent conversation context (last 10 messages max)
            messages.extend(state["messages"][-10:])
        messages.append(HumanMessage(content=prompt))

        response = await self.llm.ainvoke(messages)
        return response.content if isinstance(response.content, str) else str(response.content)

    async def _call_llm_json(self, prompt: str, state: SwarmState | None = None) -> dict[str, Any]:
        """Call the LLM and parse JSON from the response."""
        raw = await self._call_llm(prompt, state)
        # Extract JSON from markdown code blocks if present
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0]
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0]
        return json.loads(raw.strip())
