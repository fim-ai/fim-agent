"""User-facing Stripe billing endpoints.

Routes:
- ``GET  /api/billing/plans`` — list active plans (with live Stripe prices,
  cached 5 minutes); flags the user's current plan.
- ``GET  /api/billing/subscription`` — return the user's active subscription
  envelope (or ``None`` when on the free tier with no Stripe row).
- ``POST /api/billing/checkout`` — create a Stripe Checkout Session for the
  requested plan; returns the redirect URL.
- ``POST /api/billing/portal`` — create a Stripe Billing Portal Session and
  returns the redirect URL.

Every endpoint short-circuits to ``503`` when billing is disabled, so the
service stays bootable without Stripe credentials.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fim_one.db import get_session
from fim_one.web.auth import get_current_user
from fim_one.web.config import settings
from fim_one.web.models import BillingPlan, Subscription, User
from fim_one.web.schemas.billing import (
    CheckoutRequest,
    PlanInfo,
    PlansResponse,
    RedirectResponse,
    SubscriptionInfo,
)
from fim_one.web.services.stripe_client import billing_enabled, get_stripe

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/billing", tags=["billing"])

# ---------------------------------------------------------------------------
# Stripe Price cache (5 min TTL, in-process)
# ---------------------------------------------------------------------------
#
# The plans listing fetches live ``stripe.Price`` objects so admins can
# re-price by editing the Stripe Dashboard alone. Without a cache every
# settings page hit would fan out N Stripe calls — which is both slow
# (~150ms each) and bumps us up the rate-limit ladder.
#
# Redis is intentionally avoided per the P2 brief: this is a tiny, mostly
# read-only dataset and an in-process dict beats a network hop.

_PRICE_CACHE_TTL_SECONDS: float = 300.0
_price_cache: dict[str, tuple[float, dict[str, Any]]] = {}


def _format_price(amount_cents: int | None, currency: str | None, interval: str | None) -> str:
    """Render a human-readable price string (``"$20.00 USD/month"``)."""
    if amount_cents is None or currency is None:
        return ""
    dollars = amount_cents / 100
    cur = currency.upper()
    suffix = f"/{interval}" if interval else ""
    return f"${dollars:.2f} {cur}{suffix}"


def _fetch_price_details(stripe_price_id: str) -> dict[str, Any]:
    """Return ``{amount_cents, currency, interval}`` for a Stripe Price.

    Cached for ``_PRICE_CACHE_TTL_SECONDS``; on Stripe failure returns an
    empty dict so the caller can render an empty ``price_display`` rather
    than 500-ing the whole list.
    """
    now = time.monotonic()
    cached = _price_cache.get(stripe_price_id)
    if cached is not None and now - cached[0] < _PRICE_CACHE_TTL_SECONDS:
        return cached[1]

    stripe = get_stripe()
    try:
        price = stripe.Price.retrieve(stripe_price_id)
    except Exception:  # noqa: BLE001 — Stripe SDK raises a wide tree
        logger.exception(
            "Failed to fetch Stripe Price %s; returning empty display",
            stripe_price_id,
        )
        # Cache the failure briefly to avoid hammering Stripe on every
        # request when an operator typoed a price id.
        _price_cache[stripe_price_id] = (now, {})
        return {}

    recurring = getattr(price, "recurring", None) or {}
    if not isinstance(recurring, dict):
        recurring = dict(recurring) if recurring else {}
    details: dict[str, Any] = {
        "amount_cents": getattr(price, "unit_amount", None),
        "currency": getattr(price, "currency", None),
        "interval": recurring.get("interval"),
    }
    _price_cache[stripe_price_id] = (now, details)
    return details


def _reset_price_cache() -> None:
    """Drop the price cache — used by tests."""
    _price_cache.clear()


def _ensure_billing_enabled() -> None:
    """Raise 503 when Stripe credentials are not configured."""
    if not billing_enabled():
        raise HTTPException(
            status_code=503,
            detail="Billing is not configured",
        )


# ---------------------------------------------------------------------------
# GET /api/billing/plans
# ---------------------------------------------------------------------------


@router.get("/plans", response_model=PlansResponse)
async def list_plans(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> PlansResponse:
    """Return active plans with live price details and a ``current`` flag."""
    _ensure_billing_enabled()

    rows = (
        await db.execute(
            select(BillingPlan)
            .where(BillingPlan.is_active.is_(True))
            .order_by(BillingPlan.sort_order)
        )
    ).scalars().all()

    plans: list[PlanInfo] = []
    for plan in rows:
        if plan.stripe_price_id is None:
            price_display = "Free"
        else:
            details = _fetch_price_details(plan.stripe_price_id)
            price_display = _format_price(
                details.get("amount_cents"),
                details.get("currency"),
                details.get("interval"),
            )

        features_raw = plan.features_json or {}
        if isinstance(features_raw, dict):
            features = list(features_raw.get("items", []))
        elif isinstance(features_raw, list):
            features = list(features_raw)
        else:
            features = []

        plans.append(
            PlanInfo(
                slug=plan.slug,
                name=plan.name,
                monthly_token_quota=plan.monthly_token_quota,
                stripe_price_id=plan.stripe_price_id,
                price_display=price_display,
                description=plan.description,
                features=features,
                sort_order=plan.sort_order,
                current=(user.plan_id == plan.id),
            )
        )

    return PlansResponse(plans=plans)


# ---------------------------------------------------------------------------
# GET /api/billing/subscription
# ---------------------------------------------------------------------------


@router.get("/subscription", response_model=SubscriptionInfo | None)
async def get_subscription(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> SubscriptionInfo | None:
    """Return the user's current Subscription envelope, or ``None``."""
    _ensure_billing_enabled()

    sub_row = (
        await db.execute(
            select(Subscription).where(Subscription.user_id == user.id)
        )
    ).scalar_one_or_none()
    if sub_row is None:
        return None

    plan = await db.get(BillingPlan, sub_row.plan_id)
    plan_slug = plan.slug if plan is not None else "unknown"
    return SubscriptionInfo(
        plan_slug=plan_slug,
        status=sub_row.status,
        cancel_at_period_end=sub_row.cancel_at_period_end,
        current_period_start=sub_row.current_period_start,
        current_period_end=sub_row.current_period_end,
        canceled_at=sub_row.canceled_at,
        stripe_subscription_id=sub_row.stripe_subscription_id,
    )


# ---------------------------------------------------------------------------
# POST /api/billing/checkout
# ---------------------------------------------------------------------------


@router.post("/checkout", response_model=RedirectResponse)
async def create_checkout(
    body: CheckoutRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> RedirectResponse:
    """Create a Stripe Checkout Session for ``body.plan_slug``."""
    _ensure_billing_enabled()

    plan = (
        await db.execute(
            select(BillingPlan).where(BillingPlan.slug == body.plan_slug)
        )
    ).scalar_one_or_none()
    if plan is None or not plan.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown or inactive plan: {body.plan_slug}",
        )
    if not plan.stripe_price_id:
        raise HTTPException(
            status_code=400,
            detail="Plan is not purchasable",
        )

    stripe = get_stripe()

    # Lazily create the Stripe Customer the first time a user hits
    # checkout. We persist immediately so the next call (or a webhook
    # arriving before the user finishes the redirect) can find them.
    if not user.stripe_customer_id:
        customer = stripe.Customer.create(
            email=user.email,
            metadata={"user_id": user.id},
        )
        user.stripe_customer_id = customer.id
        await db.commit()
        await db.refresh(user)

    return_url = settings.STRIPE_BILLING_RETURN_URL
    session = stripe.checkout.Session.create(
        customer=user.stripe_customer_id,
        mode="subscription",
        line_items=[{"price": plan.stripe_price_id, "quantity": 1}],
        success_url=f"{return_url}?status=success",
        cancel_url=f"{return_url}?status=cancel",
        client_reference_id=str(user.id),
        metadata={"user_id": user.id, "plan_id": plan.id},
    )
    url = getattr(session, "url", None)
    if not url:
        # Stripe should always return a URL; if it doesn't we have no
        # way to redirect the user — surface a 502 so the frontend
        # toasts a system error.
        raise HTTPException(
            status_code=502,
            detail="Stripe did not return a checkout URL",
        )
    return RedirectResponse(url=url)


# ---------------------------------------------------------------------------
# POST /api/billing/portal
# ---------------------------------------------------------------------------


@router.post("/portal", response_model=RedirectResponse)
async def create_portal(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),  # noqa: ARG001 — keeps signature uniform with checkout
) -> RedirectResponse:
    """Create a Stripe Billing Portal Session for the current user."""
    _ensure_billing_enabled()

    if not user.stripe_customer_id:
        raise HTTPException(
            status_code=400,
            detail="No Stripe customer record. Subscribe first.",
        )

    stripe = get_stripe()
    session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=settings.STRIPE_BILLING_RETURN_URL,
    )
    url = getattr(session, "url", None)
    if not url:
        raise HTTPException(
            status_code=502,
            detail="Stripe did not return a portal URL",
        )
    return RedirectResponse(url=url)


__all__ = ["router"]
