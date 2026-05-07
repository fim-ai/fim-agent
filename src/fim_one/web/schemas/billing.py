"""Pydantic request / response schemas for the billing API.

Kept deliberately thin: the on-disk source of truth for plan rows is the
``BillingPlan`` ORM model; these schemas only shape what the API surfaces
to the frontend (price strings, ``current`` flag, etc.).

Two surfaces share this module:

- ``/api/billing/*`` — user-facing ``PlanInfo``, ``SubscriptionInfo``,
  ``CheckoutRequest``, ``RedirectResponse``, ``PlansResponse``.
- ``/api/admin/billing/*`` — admin CRUD shapes prefixed with ``Admin``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# User-facing
# ---------------------------------------------------------------------------


class PlanInfo(BaseModel):
    """Single row in ``GET /api/billing/plans``."""

    model_config = ConfigDict(from_attributes=True)

    slug: str
    name: str
    monthly_token_quota: int
    stripe_price_id: str | None = None
    price_display: str = Field(
        default="",
        description=(
            "Human-readable price string (e.g. ``$20.00 USD/month``) "
            "resolved from Stripe at request time. ``Free`` for the free "
            "tier; empty when Stripe lookup fails."
        ),
    )
    description: str | None = None
    features: list[str] = Field(default_factory=list)
    sort_order: int = 0
    current: bool = Field(
        default=False,
        description="True when this plan is the user's currently active plan.",
    )


class SubscriptionInfo(BaseModel):
    """Current Subscription state for ``GET /api/billing/subscription``."""

    model_config = ConfigDict(from_attributes=True)

    plan_slug: str
    status: str
    cancel_at_period_end: bool
    current_period_start: datetime
    current_period_end: datetime
    canceled_at: datetime | None = None
    stripe_subscription_id: str


class CheckoutRequest(BaseModel):
    """Body for ``POST /api/billing/checkout``."""

    plan_slug: str = Field(..., min_length=1, max_length=32)


class RedirectResponse(BaseModel):
    """Response carrying a redirect URL (Checkout / Portal)."""

    url: str


class PlansResponse(BaseModel):
    """Envelope for ``GET /api/billing/plans``."""

    plans: list[PlanInfo]


# ---------------------------------------------------------------------------
# Admin-facing
# ---------------------------------------------------------------------------


class AdminBillingPlanCreate(BaseModel):
    """Body for ``POST /api/admin/billing/plans``.

    ``slug`` is set on creation and IMMUTABLE thereafter — the slug is the
    customer-facing key that flows into Stripe metadata, audit logs, and
    referrals. Renaming requires a fresh row + migration of subscriptions.
    """

    slug: str = Field(..., min_length=1, max_length=32, pattern=r"^[a-z0-9_-]+$")
    name: str = Field(..., min_length=1, max_length=64)
    monthly_token_quota: int = Field(..., ge=0)
    stripe_price_id: str | None = Field(default=None, max_length=64)
    description: str | None = None
    features: list[str] = Field(default_factory=list)
    sort_order: int = 0
    is_active: bool = True


class AdminBillingPlanUpdate(BaseModel):
    """Body for ``PATCH /api/admin/billing/plans/{plan_id}``.

    Every field is optional — only the supplied keys are mutated. The
    ``slug`` field is intentionally absent: see :class:`AdminBillingPlanCreate`.
    """

    name: str | None = Field(default=None, min_length=1, max_length=64)
    price_cents: int | None = Field(
        default=None,
        ge=0,
        description=(
            "Display-only override; Stripe Price remains the SoT. Stored "
            "into ``features_json.price_cents`` for the admin UI."
        ),
    )
    monthly_token_quota: int | None = Field(default=None, ge=0)
    stripe_price_id: str | None = Field(default=None, max_length=64)
    description: str | None = None
    features: list[str] | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class AdminBillingPlanRead(BaseModel):
    """Envelope for ``GET /api/admin/billing/plans[/{plan_id}]``."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    monthly_token_quota: int
    stripe_price_id: str | None = None
    price_cents: int | None = Field(
        default=None,
        description=(
            "Optional display-only price override pulled from "
            "``features_json.price_cents``."
        ),
    )
    description: str | None = None
    features: list[str] = Field(default_factory=list)
    features_json: dict[str, Any] = Field(default_factory=dict)
    sort_order: int = 0
    is_active: bool = True
    active_subscription_count: int = 0
    created_at: datetime | None = None


class AdminSubscriptionRead(BaseModel):
    """Single row for the admin subscriptions table."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: str
    user_email: str | None = None
    user_username: str | None = None
    plan_id: int
    plan_slug: str
    plan_name: str
    stripe_subscription_id: str
    stripe_price_id: str
    status: str
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool
    canceled_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AdminSubscriptionListResponse(BaseModel):
    """Paginated envelope for ``GET /api/admin/billing/subscriptions``."""

    items: list[AdminSubscriptionRead]
    total: int
    limit: int
    offset: int


__all__ = [
    "AdminBillingPlanCreate",
    "AdminBillingPlanRead",
    "AdminBillingPlanUpdate",
    "AdminSubscriptionListResponse",
    "AdminSubscriptionRead",
    "CheckoutRequest",
    "PlanInfo",
    "PlansResponse",
    "RedirectResponse",
    "SubscriptionInfo",
]
