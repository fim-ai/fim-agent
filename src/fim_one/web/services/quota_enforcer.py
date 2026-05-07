"""Plan-aware quota lookup.

Centralises the precedence chain for resolving a user's effective monthly
token budget so the chat layer (mid-stream guard) and the billing layer
(checkout / display) agree on a single number.

Resolution order, top wins:

1. ``user.plan.monthly_token_quota`` — the Stripe-billed plan tier.
2. ``user.token_quota`` — legacy admin override for individual users
   (kept around so admin-set quotas continue to work post-billing).
3. The system-wide ``default_token_quota`` admin setting.
4. ``None`` — unlimited (treated by chat.py as "skip enforcement").

The ``None`` semantic is critical: chat.py's ``_get_quota_status`` returns
``(0, 0)`` to mean "no cap" and skips enforcement.  Returning ``None``
here propagates through that contract.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fim_one.web.models import BillingPlan, User

logger = logging.getLogger(__name__)


async def get_user_quota(user: User, db: AsyncSession) -> int | None:
    """Return the effective ``monthly_token_quota`` for *user*.

    The function never raises for "no plan" / "no quota": those map to
    ``None`` (unlimited), matching chat.py's existing semantic where
    ``user_quota <= 0`` means "skip enforcement".

    Args:
        user: The authenticated user.  Read-only here; this function
            never mutates the row.
        db: An async session to fetch :class:`BillingPlan` when the
            relationship is not already eager-loaded (lazy="raise" on
            ``User.plan`` means we must explicitly query).

    Returns:
        The effective monthly token quota, or ``None`` for "unlimited".
    """
    if user.plan_id is not None:
        plan = await db.get(BillingPlan, user.plan_id)
        if plan is not None and plan.monthly_token_quota is not None:
            return int(plan.monthly_token_quota)

    if user.token_quota is not None:
        return int(user.token_quota)

    return None


async def get_user_quota_by_id(user_id: str, db: AsyncSession) -> int | None:
    """Like :func:`get_user_quota` but takes a user id.

    Useful from chat.py's ``_get_quota_status`` which only has the id in
    scope. Performs a single ``SELECT`` joining ``BillingPlan`` so that a
    plan-bound quota wins over the legacy user-level field in one round-trip.
    """
    result = await db.execute(
        select(User.token_quota, User.plan_id, BillingPlan.monthly_token_quota)
        .select_from(User)
        .outerjoin(BillingPlan, User.plan_id == BillingPlan.id)
        .where(User.id == user_id)
    )
    row = result.one_or_none()
    if row is None:
        return None

    legacy_quota, plan_id, plan_quota = row
    if plan_id is not None and plan_quota is not None:
        return int(plan_quota)
    if legacy_quota is not None:
        return int(legacy_quota)
    return None


__all__ = ["get_user_quota", "get_user_quota_by_id"]
