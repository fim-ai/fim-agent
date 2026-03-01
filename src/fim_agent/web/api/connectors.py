"""Connector management API."""

from __future__ import annotations

import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from fim_agent.db import get_session
from fim_agent.web.auth import get_current_user
from fim_agent.web.models.connector import Connector, ConnectorAction
from fim_agent.web.models.user import User
from fim_agent.web.schemas.common import ApiResponse, PaginatedResponse
from fim_agent.web.schemas.connector import (
    ActionCreate,
    ActionResponse,
    ActionUpdate,
    ConnectorCreate,
    ConnectorResponse,
    ConnectorUpdate,
)

router = APIRouter(prefix="/api/connectors", tags=["connectors"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _action_to_response(action: ConnectorAction) -> ActionResponse:
    return ActionResponse(
        id=action.id,
        connector_id=action.connector_id,
        name=action.name,
        description=action.description,
        method=action.method,
        path=action.path,
        parameters_schema=action.parameters_schema,
        request_body_template=action.request_body_template,
        response_extract=action.response_extract,
        requires_confirmation=action.requires_confirmation,
        created_at=action.created_at.isoformat() if action.created_at else "",
        updated_at=action.updated_at.isoformat() if action.updated_at else None,
    )


def _connector_to_response(connector: Connector) -> ConnectorResponse:
    return ConnectorResponse(
        id=connector.id,
        name=connector.name,
        description=connector.description,
        icon=connector.icon,
        type=connector.type,
        base_url=connector.base_url,
        auth_type=connector.auth_type,
        auth_config=connector.auth_config,
        status=connector.status,
        is_official=connector.is_official,
        forked_from=connector.forked_from,
        version=connector.version,
        actions=[_action_to_response(a) for a in (connector.actions or [])],
        created_at=connector.created_at.isoformat() if connector.created_at else "",
        updated_at=connector.updated_at.isoformat() if connector.updated_at else None,
    )


async def _get_owned_connector(
    connector_id: str, user_id: str, db: AsyncSession,
) -> Connector:
    result = await db.execute(
        select(Connector)
        .options(selectinload(Connector.actions))
        .where(Connector.id == connector_id, Connector.user_id == user_id)
    )
    connector = result.scalar_one_or_none()
    if connector is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connector not found",
        )
    return connector


# ---------------------------------------------------------------------------
# Connector CRUD
# ---------------------------------------------------------------------------


@router.post("", response_model=ApiResponse)
async def create_connector(
    body: ConnectorCreate,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_session),  # noqa: B008
) -> ApiResponse:
    connector = Connector(
        user_id=current_user.id,
        name=body.name,
        description=body.description,
        icon=body.icon,
        type=body.type,
        base_url=body.base_url,
        auth_type=body.auth_type,
        auth_config=body.auth_config,
        status="draft",
    )
    db.add(connector)
    await db.commit()
    await db.refresh(connector)
    return ApiResponse(data=_connector_to_response(connector).model_dump())


@router.get("", response_model=PaginatedResponse)
async def list_connectors(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    connector_status: str | None = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_session),  # noqa: B008
) -> PaginatedResponse:
    base = select(Connector).where(Connector.user_id == current_user.id)
    if connector_status is not None:
        base = base.where(Connector.status == connector_status)

    count_result = await db.execute(
        select(func.count()).select_from(base.subquery())
    )
    total = count_result.scalar_one()

    result = await db.execute(
        base.options(selectinload(Connector.actions))
        .order_by(Connector.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    connectors = result.scalars().all()

    return PaginatedResponse(
        items=[_connector_to_response(c).model_dump() for c in connectors],
        total=total,
        page=page,
        size=size,
        pages=math.ceil(total / size) if total else 0,
    )


@router.get("/{connector_id}", response_model=ApiResponse)
async def get_connector(
    connector_id: str,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_session),  # noqa: B008
) -> ApiResponse:
    connector = await _get_owned_connector(connector_id, current_user.id, db)
    return ApiResponse(data=_connector_to_response(connector).model_dump())


@router.put("/{connector_id}", response_model=ApiResponse)
async def update_connector(
    connector_id: str,
    body: ConnectorUpdate,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_session),  # noqa: B008
) -> ApiResponse:
    connector = await _get_owned_connector(connector_id, current_user.id, db)

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(connector, field, value)

    await db.commit()
    await db.refresh(connector)
    return ApiResponse(data=_connector_to_response(connector).model_dump())


@router.delete("/{connector_id}", response_model=ApiResponse)
async def delete_connector(
    connector_id: str,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_session),  # noqa: B008
) -> ApiResponse:
    connector = await _get_owned_connector(connector_id, current_user.id, db)
    await db.delete(connector)
    await db.commit()
    return ApiResponse(data={"deleted": connector_id})


@router.post("/{connector_id}/publish", response_model=ApiResponse)
async def publish_connector(
    connector_id: str,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_session),  # noqa: B008
) -> ApiResponse:
    connector = await _get_owned_connector(connector_id, current_user.id, db)
    connector.status = "published"
    await db.commit()
    await db.refresh(connector)
    return ApiResponse(data=_connector_to_response(connector).model_dump())


@router.post("/{connector_id}/unpublish", response_model=ApiResponse)
async def unpublish_connector(
    connector_id: str,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_session),  # noqa: B008
) -> ApiResponse:
    connector = await _get_owned_connector(connector_id, current_user.id, db)
    connector.status = "draft"
    await db.commit()
    await db.refresh(connector)
    return ApiResponse(data=_connector_to_response(connector).model_dump())


# ---------------------------------------------------------------------------
# Action CRUD (nested under connector)
# ---------------------------------------------------------------------------


@router.post("/{connector_id}/actions", response_model=ApiResponse)
async def create_action(
    connector_id: str,
    body: ActionCreate,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_session),  # noqa: B008
) -> ApiResponse:
    # Verify connector ownership
    await _get_owned_connector(connector_id, current_user.id, db)

    action = ConnectorAction(
        connector_id=connector_id,
        name=body.name,
        description=body.description,
        method=body.method,
        path=body.path,
        parameters_schema=body.parameters_schema,
        request_body_template=body.request_body_template,
        response_extract=body.response_extract,
        requires_confirmation=body.requires_confirmation,
    )
    db.add(action)
    await db.commit()
    await db.refresh(action)
    return ApiResponse(data=_action_to_response(action).model_dump())


@router.put("/{connector_id}/actions/{action_id}", response_model=ApiResponse)
async def update_action(
    connector_id: str,
    action_id: str,
    body: ActionUpdate,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_session),  # noqa: B008
) -> ApiResponse:
    # Verify connector ownership
    await _get_owned_connector(connector_id, current_user.id, db)

    result = await db.execute(
        select(ConnectorAction).where(
            ConnectorAction.id == action_id,
            ConnectorAction.connector_id == connector_id,
        )
    )
    action = result.scalar_one_or_none()
    if action is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action not found",
        )

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(action, field, value)

    await db.commit()
    await db.refresh(action)
    return ApiResponse(data=_action_to_response(action).model_dump())


@router.delete("/{connector_id}/actions/{action_id}", response_model=ApiResponse)
async def delete_action(
    connector_id: str,
    action_id: str,
    current_user: User = Depends(get_current_user),  # noqa: B008
    db: AsyncSession = Depends(get_session),  # noqa: B008
) -> ApiResponse:
    # Verify connector ownership
    await _get_owned_connector(connector_id, current_user.id, db)

    result = await db.execute(
        select(ConnectorAction).where(
            ConnectorAction.id == action_id,
            ConnectorAction.connector_id == connector_id,
        )
    )
    action = result.scalar_one_or_none()
    if action is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Action not found",
        )

    await db.delete(action)
    await db.commit()
    return ApiResponse(data={"deleted": action_id})
