"""Builder tools for managing Agent settings via LLM agent."""

from __future__ import annotations

import json
import logging
from abc import ABC
from typing import Any

from sqlalchemy import select

from ..base import BaseTool

logger = logging.getLogger(__name__)


class _AgentBuilderBase(BaseTool, ABC):
    """Shared base for all agent-builder tools."""

    def __init__(self, agent_id: str, user_id: str) -> None:
        self.agent_id = agent_id
        self.user_id = user_id

    @property
    def category(self) -> str:
        return "agent_builder"

    async def _get_agent(self, db):
        from fim_agent.web.models.agent import Agent
        result = await db.execute(
            select(Agent).where(
                Agent.id == self.agent_id,
                Agent.user_id == self.user_id,
            )
        )
        return result.scalar_one_or_none()


class AgentGetSettingsTool(_AgentBuilderBase):
    """Get current settings of the target agent."""

    @property
    def name(self) -> str:
        return "agent_get_settings"

    @property
    def display_name(self) -> str:
        return "Get Agent Settings"

    @property
    def description(self) -> str:
        return "Get the current settings of the target agent including instructions, tool categories, execution mode, and more."

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}, "required": []}

    async def run(self, **kwargs: Any) -> str:
        from fim_agent.db import create_session
        async with create_session() as db:
            agent = await self._get_agent(db)
            if agent is None:
                return "[Error] Agent not found or access denied."
            result = {
                "id": agent.id,
                "name": agent.name,
                "description": agent.description,
                "instructions": agent.instructions,
                "execution_mode": agent.execution_mode,
                "tool_categories": agent.tool_categories or [],
                "status": agent.status,
                "model_config": agent.model_config_json,
                "suggested_prompts": agent.suggested_prompts or [],
            }
            return json.dumps(result, ensure_ascii=False, indent=2)


class AgentUpdateSettingsTool(_AgentBuilderBase):
    """Update settings of the target agent."""

    @property
    def name(self) -> str:
        return "agent_update_settings"

    @property
    def display_name(self) -> str:
        return "Update Agent Settings"

    @property
    def description(self) -> str:
        return (
            "Update one or more settings of the target agent. "
            "Only provided fields are changed. "
            "Updatable fields: name, description, instructions, execution_mode, tool_categories, suggested_prompts."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "New agent name."},
                "description": {"type": "string", "description": "New agent description."},
                "instructions": {"type": "string", "description": "New system prompt / instructions for the agent."},
                "execution_mode": {
                    "type": "string",
                    "enum": ["react", "dag"],
                    "description": "New execution mode.",
                },
                "tool_categories": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "New list of tool categories. Valid values: computation, web, filesystem, knowledge, connector, general, mcp.",
                },
                "suggested_prompts": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "New list of suggested prompts shown at conversation start.",
                },
            },
            "required": [],
        }

    async def run(self, **kwargs: Any) -> str:
        from fim_agent.db import create_session
        async with create_session() as db:
            agent = await self._get_agent(db)
            if agent is None:
                return "[Error] Agent not found or access denied."

            _updatable = {"name", "description", "instructions", "execution_mode", "tool_categories", "suggested_prompts"}
            updates = {k: v for k, v in kwargs.items() if k in _updatable}
            if not updates:
                return "[Error] At least one updatable field must be provided."

            for field, value in updates.items():
                setattr(agent, field, value)

            await db.commit()
            return json.dumps(
                {"updated": True, "fields": list(updates.keys())},
                ensure_ascii=False,
            )
