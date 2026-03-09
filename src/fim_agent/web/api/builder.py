"""Builder Session API."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fim_agent.db import get_session
from fim_agent.web.auth import get_current_user
from fim_agent.web.exceptions import AppError
from fim_agent.web.models import Agent
from fim_agent.web.models.connector import Connector
from fim_agent.web.models.user import User
from fim_agent.web.schemas.common import ApiResponse

router = APIRouter(prefix="/api/builder", tags=["builder"])


class BuilderSessionRequest(BaseModel):
    target_type: str  # "connector"
    target_id: str


@router.post("/session", response_model=ApiResponse)
async def create_builder_session(
    body: BuilderSessionRequest,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_session),  # noqa: B008
) -> ApiResponse:
    if body.target_type == "connector":
        result = await db.execute(
            select(Connector).where(
                Connector.id == body.target_id,
                Connector.user_id == current_user.id,
            )
        )
        target = result.scalar_one_or_none()
        if target is None:
            raise AppError("connector_not_found", status_code=404)

        agent_name = f"__builder_connector_{body.target_id}"
        instructions = (
            f"You are a Connector Builder Agent.\n"
            f"connector_id={body.target_id}\n"
            f"Connector name: {target.name}\n"
            f"Base URL: {target.base_url}\n\n"
            f"You have specialized tools to manage this connector's actions:\n"
            f"- connector_list_actions: List all existing actions\n"
            f"- connector_create_action: Create a new API action\n"
            f"- connector_update_action: Update an existing action\n"
            f"- connector_delete_action: Delete an action\n"
            f"- connector_update_settings: Update connector settings\n"
            f"- connector_test_action: Test an action with sample parameters\n\n"
            f"Strategy for large API documents:\n"
            f"1. First call connector_list_actions to see what already exists\n"
            f"2. Parse the API document and identify endpoints to add\n"
            f"3. Create actions in batches of 5-10\n"
            f"4. After each batch, call connector_list_actions to verify\n"
            f"5. Continue iterating until all endpoints are covered\n"
        )
    else:
        raise AppError("unsupported_target_type", status_code=400)

    # Find or create builder agent
    result = await db.execute(
        select(Agent).where(
            Agent.name == agent_name,
            Agent.user_id == current_user.id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return ApiResponse(data={"builder_agent_id": existing.id})

    agent = Agent(
        user_id=current_user.id,
        name=agent_name,
        icon="\U0001f527",
        description=f"Builder agent for connector {body.target_id}",
        instructions=instructions,
        execution_mode="react",
        tool_categories=["builder", "web"],
        status="draft",
    )
    db.add(agent)
    await db.commit()
    return ApiResponse(data={"builder_agent_id": agent.id})
