"""Pydantic request/response schemas for the Channel API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Create / Update
# ---------------------------------------------------------------------------


class ChannelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    type: str = Field(pattern=r"^(feishu|wecom|slack)$")
    org_id: str = Field(min_length=1)
    config: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class ChannelUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    config: dict[str, Any] | None = None
    is_active: bool | None = None


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------


# Config fields considered sensitive — masked in API responses.
_SENSITIVE_KEYS = frozenset(
    {"app_secret", "verification_token", "encrypt_key", "api_secret"}
)


def _mask_config(config: dict[str, Any]) -> dict[str, Any]:
    """Return a shallow copy of ``config`` with sensitive values masked."""
    masked: dict[str, Any] = {}
    for key, value in config.items():
        if key in _SENSITIVE_KEYS and value:
            masked[key] = "***"
        else:
            masked[key] = value
    return masked


class ChannelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    type: str
    org_id: str
    config: dict[str, Any]
    is_active: bool
    created_by: str
    created_at: str
    updated_at: str | None = None
    callback_url: str | None = None

    @classmethod
    def from_orm_masked(
        cls,
        channel: Any,
        *,
        callback_url: str | None = None,
    ) -> ChannelResponse:
        """Build a response with ``config`` sensitive fields masked."""
        return cls(
            id=channel.id,
            name=channel.name,
            type=channel.type,
            org_id=channel.org_id,
            config=_mask_config(dict(channel.config or {})),
            is_active=channel.is_active,
            created_by=channel.created_by,
            created_at=(
                channel.created_at.isoformat() if channel.created_at else ""
            ),
            updated_at=(
                channel.updated_at.isoformat() if channel.updated_at else None
            ),
            callback_url=callback_url,
        )


class ChannelListResponse(BaseModel):
    items: list[ChannelResponse]


class ChannelTestResponse(BaseModel):
    ok: bool
    error: str | None = None


# ---------------------------------------------------------------------------
# Chat discovery (Feishu group picker)
# ---------------------------------------------------------------------------


class ChatDiscoveryRequest(BaseModel):
    """Request to list Feishu groups that the app/bot is a member of.

    The caller passes ``app_id`` + ``app_secret`` when creating a channel
    (no DB row exists yet).  When editing an existing channel, the caller
    may pass ``channel_id`` alone — the server will decrypt the stored
    ``app_secret`` to query Feishu.  If both ``app_secret`` and
    ``channel_id`` are present, ``app_secret`` wins (user explicitly
    re-entered it).
    """

    app_id: str = Field(min_length=1)
    app_secret: str | None = None
    channel_id: str | None = None
    org_id: str | None = None


class ChatInfo(BaseModel):
    chat_id: str
    name: str
    avatar: str | None = None
    description: str | None = None
    member_count: int | None = None
    external: bool = False


class ChatDiscoveryResponse(BaseModel):
    items: list[ChatInfo]


__all__ = [
    "ChannelCreate",
    "ChannelUpdate",
    "ChannelResponse",
    "ChannelListResponse",
    "ChannelTestResponse",
    "ChatDiscoveryRequest",
    "ChatInfo",
    "ChatDiscoveryResponse",
]
