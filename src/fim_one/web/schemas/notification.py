"""Pydantic schemas for notification API endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class NotificationSendRequest(BaseModel):
    """Request body for ``POST /api/notifications/send``."""

    provider: str = Field(..., description="Provider name: email, slack, lark, wecom.")
    title: str = Field(..., min_length=1, max_length=200, description="Notification title.")
    body: str = Field(..., min_length=1, max_length=10000, description="Notification body.")
    channel: str | None = Field(
        None,
        description="Target channel / recipient. Required for email (recipient address).",
    )


class NotificationTestRequest(BaseModel):
    """Request body for ``POST /api/notifications/test``."""

    provider: str = Field(..., description="Provider name to test: email, slack, lark, wecom.")
    channel: str | None = Field(
        None,
        description="Optional target for the test message. Required for email.",
    )


class NotificationProviderInfo(BaseModel):
    """Info about a single notification provider."""

    name: str
    display_name: str
    description: str
    configured: bool
