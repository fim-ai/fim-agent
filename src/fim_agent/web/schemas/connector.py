"""Connector request/response schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# --- Action Schemas ---


class ActionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    method: str = "GET"
    path: str = Field(min_length=1, max_length=500)
    parameters_schema: dict[str, Any] | None = None
    request_body_template: dict[str, Any] | None = None
    response_extract: str | None = None
    requires_confirmation: bool = False


class ActionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    method: str | None = None
    path: str | None = None
    parameters_schema: dict[str, Any] | None = None
    request_body_template: dict[str, Any] | None = None
    response_extract: str | None = None
    requires_confirmation: bool | None = None


class ActionResponse(BaseModel):
    id: str
    connector_id: str
    name: str
    description: str | None
    method: str
    path: str
    parameters_schema: dict[str, Any] | None
    request_body_template: dict[str, Any] | None
    response_extract: str | None
    requires_confirmation: bool
    created_at: str
    updated_at: str | None


# --- Connector Schemas ---


class ConnectorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    icon: str | None = None
    type: str = "api"
    base_url: str = Field(min_length=1, max_length=500)
    auth_type: str = "none"
    auth_config: dict[str, Any] | None = None


class ConnectorUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    icon: str | None = None
    type: str | None = None
    base_url: str | None = None
    auth_type: str | None = None
    auth_config: dict[str, Any] | None = None


class ConnectorResponse(BaseModel):
    id: str
    name: str
    description: str | None
    icon: str | None
    type: str
    base_url: str
    auth_type: str
    auth_config: dict[str, Any] | None
    status: str
    is_official: bool
    forked_from: str | None
    version: int
    actions: list[ActionResponse]
    created_at: str
    updated_at: str | None
