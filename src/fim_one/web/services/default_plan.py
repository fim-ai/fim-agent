"""Helper for resolving the Free plan id at user-registration time.

Post-Stripe-MVP every newly registered user must be bound to at least
the Free plan so the quota resolver can report a finite tier without
falling through to the defensive system-wide ``default_token_quota``.

This helper is intentionally tiny and side-effect-free: it returns the
id (or ``None`` if the seed row is missing) and never raises so a
registration never fails because of a transient billing-table issue.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fim_one.web.models import BillingPlan

logger = logging.getLogger(__name__)

_FREE_PLAN_SLUG = "free"


async def get_free_plan_id(db: AsyncSession) -> int | None:
    """Return the id of the Free plan, or ``None`` if it isn't seeded.

    Failures are logged at WARNING and surfaced as ``None`` so the
    registration code path can fall through gracefully — the backfill
    migration covers any rows we miss here.
    """
    try:
        result = await db.execute(
            select(BillingPlan.id).where(BillingPlan.slug == _FREE_PLAN_SLUG)
        )
        plan_id = result.scalar_one_or_none()
        if plan_id is None:
            logger.warning(
                "Free plan (slug=%s) not found; new user will be created "
                "without plan binding.",
                _FREE_PLAN_SLUG,
            )
            return None
        return int(plan_id)
    except Exception:  # noqa: BLE001 — registration must not fail here
        logger.exception(
            "Failed to look up Free plan id; falling through to NULL plan_id."
        )
        return None


__all__ = ["get_free_plan_id"]
