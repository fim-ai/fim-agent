"""Model configuration request/response schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ModelConfigCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    provider: str = ""
    model_name: str
    base_url: str | None = None
    api_key: str | None = None
    category: Literal["llm", "embedding", "vision"] = "llm"
    temperature: float | None = None
    max_output_tokens: int | None = None
    context_size: int | None = None
    is_default: bool = False
    role: Literal["general", "fast"] | None = None
    json_mode_enabled: bool = True


class ModelConfigUpdate(BaseModel):
    name: str | None = None
    provider: str | None = None
    model_name: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    category: str | None = None
    temperature: float | None = None
    max_output_tokens: int | None = None
    context_size: int | None = None
    is_default: bool | None = None
    is_active: bool | None = None
    role: str | None = None
    json_mode_enabled: bool | None = None


class ModelConfigResponse(BaseModel):
    id: str
    name: str
    provider: str
    model_name: str
    base_url: str | None
    category: str
    temperature: float | None
    max_output_tokens: int | None
    context_size: int | None
    role: str | None
    is_default: bool
    is_active: bool
    json_mode_enabled: bool
    created_at: str
    updated_at: str | None
    # NEVER expose api_key in responses
