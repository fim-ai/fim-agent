"""Pydantic request / response schemas for the billing API.

Kept deliberately thin: the on-disk source of truth for plan rows is the
``BillingPlan`` ORM model; these schemas only shape what the API surfaces
to the frontend (price strings, ``current`` flag, etc.).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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


__all__ = [
    "CheckoutRequest",
    "PlanInfo",
    "PlansResponse",
    "RedirectResponse",
    "SubscriptionInfo",
]
