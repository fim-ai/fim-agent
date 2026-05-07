"""Billing feature flag — admin-controlled gate for the Stripe pipeline.

Implements the "front-loaded data, switch-only state" architectural
principle: the activation flow seeds plans and backfills users **once**;
toggling ``billing_enabled`` from ``true`` → ``false`` and back is a
pure flag flip with **no** data side-effects.

Public API
----------
- :func:`is_billing_enabled` — read the live flag from
  ``system_settings.billing_enabled``. Returns ``False`` for any
  representation other than the literal string ``"true"``.
- :func:`require_billing_enabled` — FastAPI dependency that raises
  ``HTTPException(503)`` when the flag is off.
- :func:`activate_billing` — idempotent activation procedure. Seeds
  the catalogue, backfills user plan bindings, then flips the flag.
- :func:`deactivate_billing` — pure flag flip; no data mutated.

The flag column lives in the existing ``system_settings`` key/value
store rather than its own column on a dedicated row, mirroring how the
rest of the platform's runtime knobs (registration mode, default token
quota, maintenance mode) are persisted.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from fim_one.db import get_session
from fim_one.web.config import settings
from fim_one.web.models import BillingPlan, SystemSetting, User

logger = logging.getLogger(__name__)

#: Stable name for the system_settings row that gates the billing pipeline.
SETTING_BILLING_ENABLED = "billing_enabled"

#: Stable name for the pointer that replaces ``WHERE slug='free'`` lookups.
SETTING_DEFAULT_PLAN_ID = "default_plan_id"


async def is_billing_enabled(db: AsyncSession) -> bool:
    """Return ``True`` when the operator has flipped the billing switch on.

    The default for fresh installs and pre-flag deployments is ``False`` —
    admins must opt in via :func:`activate_billing` (or the admin UI) so
    that private/self-hosted boxes don't accidentally surface payment
    UX they didn't configure.
    """
    result = await db.execute(
        select(SystemSetting.value).where(
            SystemSetting.key == SETTING_BILLING_ENABLED
        )
    )
    raw = result.scalar_one_or_none()
    if raw is None:
        return False
    return raw.strip().lower() == "true"


async def require_billing_enabled(
    db: AsyncSession = Depends(get_session),  # noqa: B008
) -> None:
    """FastAPI dependency: 503 when billing is gated off.

    Apply to every billing-related router (user-facing, admin, webhook)
    so the whole pipeline goes silent in lock-step. This keeps the gate
    centralised — sprinkling ``if not flag: raise`` into each handler
    is exactly the kind of drift this dependency exists to prevent.
    """
    if not await is_billing_enabled(db):
        raise HTTPException(
            status_code=503,
            detail="Billing is not enabled on this instance",
        )


async def _set_setting(db: AsyncSession, key: str, value: str) -> None:
    """Upsert a row in ``system_settings``."""
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == key)
    )
    row = result.scalar_one_or_none()
    if row is None:
        db.add(SystemSetting(key=key, value=value))
    else:
        row.value = value


async def _get_setting(
    db: AsyncSession, key: str
) -> str | None:
    result = await db.execute(
        select(SystemSetting.value).where(SystemSetting.key == key)
    )
    raw = result.scalar_one_or_none()
    if raw is None:
        return None
    raw = raw.strip()
    return raw if raw else None


# ---------------------------------------------------------------------------
# Activation / deactivation
# ---------------------------------------------------------------------------


# The seed catalogue mirrors the original ``i9d1e3f5g678`` migration.
# Re-running activation against an install that already has these rows is
# a no-op (we conflict on slug). Operators should refine the Pro
# stripe_price_id via the admin UI before going live.
_SEED_PLANS: tuple[dict[str, Any], ...] = (
    {
        "slug": "free",
        "name": "Free",
        "stripe_price_id": None,
        "monthly_token_quota": 100_000,
        "description": "100K tokens / month, basic features",
        "sort_order": 0,
        "is_active": True,
    },
    {
        "slug": "pro",
        "name": "Pro",
        "stripe_price_id": "price_1TULYLPQaxUGYm0zj6R3Mpne",
        "monthly_token_quota": 5_000_000,
        "description": "5M tokens / month, priority support",
        "sort_order": 1,
        "is_active": True,
    },
)

_DEFAULT_TOKEN_QUOTA_KEY = "default_token_quota"


def _stripe_env_configured() -> tuple[bool, str | None]:
    """Verify Stripe credentials are set in the runtime config.

    Returns a ``(ok, missing_key)`` tuple. ``missing_key`` names the
    first missing variable so the API surface can render a precise
    error message without leaking secret values.
    """
    try:
        secret = settings.STRIPE_SECRET_KEY
        webhook = settings.STRIPE_WEBHOOK_SECRET
    except Exception:  # noqa: BLE001 — bad config surfaces here
        return False, "STRIPE_SECRET_KEY"
    if secret is None:
        return False, "STRIPE_SECRET_KEY"
    if webhook is None:
        return False, "STRIPE_WEBHOOK_SECRET"
    return True, None


async def activate_billing(db: AsyncSession) -> dict[str, Any]:
    """Run the one-time activation procedure, then flip the flag on.

    Idempotent: re-running on an already-activated install touches no
    data and reports zero seeded / backfilled.

    Steps (all guarded by IF-NOT-EXISTS / IF-NULL checks):

    1. Verify Stripe env vars exist; raise 400 with the missing key name
       when they don't (the flag stays off).
    2. Insert Free + Pro plans if their slug rows are absent.
    3. Set ``system_settings.default_plan_id = free.id`` if unset.
    4. Backfill ``users.plan_id`` to Free for any NULL rows.
    5. If a legacy ``default_token_quota`` value exists, mirror it onto
       Free's ``monthly_token_quota`` (covers old installs that priced
       Free via the legacy admin knob).
    6. Flip ``billing_enabled = "true"``.

    Returns a summary dict useful for ops debugging:
    ``{"plans_seeded": int, "users_backfilled": int, "default_plan_id": int | None}``.
    """
    ok, missing = _stripe_env_configured()
    if not ok:
        raise HTTPException(
            status_code=400,
            detail=(
                "Configure STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET in "
                ".env first"
            ),
        )

    # ── Seed plans ────────────────────────────────────────────────────────
    plans_seeded = 0
    for spec in _SEED_PLANS:
        existing = await db.execute(
            select(BillingPlan).where(BillingPlan.slug == spec["slug"])
        )
        if existing.scalar_one_or_none() is not None:
            continue
        db.add(
            BillingPlan(
                slug=spec["slug"],
                name=spec["name"],
                stripe_price_id=spec["stripe_price_id"],
                monthly_token_quota=spec["monthly_token_quota"],
                description=spec["description"],
                features_json={},
                sort_order=spec["sort_order"],
                is_active=spec["is_active"],
            )
        )
        plans_seeded += 1
    if plans_seeded:
        # Flush so we can read back the assigned ids in the next step.
        await db.flush()

    # Look up Free plan id — could be either freshly inserted or a
    # pre-existing row, so we re-query rather than relying on the loop.
    free_row = await db.execute(
        select(BillingPlan.id).where(BillingPlan.slug == "free")
    )
    free_plan_id = free_row.scalar_one_or_none()

    # ── default_plan_id pointer ──────────────────────────────────────────
    if free_plan_id is not None:
        existing_pointer = await _get_setting(db, SETTING_DEFAULT_PLAN_ID)
        if existing_pointer is None:
            await _set_setting(db, SETTING_DEFAULT_PLAN_ID, str(free_plan_id))

    # ── Backfill user plan_id ────────────────────────────────────────────
    users_backfilled = 0
    if free_plan_id is not None:
        # Count first, then update — keeps the return value typed
        # (``CursorResult.rowcount`` isn't exposed on the async
        # ``Result`` shape mypy infers).
        # Pre-count so we can return how many rows we'll touch — the
        # async ``Result`` doesn't surface ``rowcount`` cleanly. We
        # query through raw SQL (rather than ``select(func.count())``)
        # because the User ORM's eager-joined relationship confuses
        # mypy's overload resolution into expecting a BillingPlan.
        from sqlalchemy import text as _text

        count_row = await db.execute(
            _text("SELECT COUNT(*) FROM users WHERE plan_id IS NULL")
        )
        users_backfilled = int(count_row.scalar_one() or 0)
        if users_backfilled:
            await db.execute(
                update(User)
                .where(User.plan_id.is_(None))
                .values(plan_id=free_plan_id)
            )

    # ── Legacy default_token_quota → Free plan quota ─────────────────────
    legacy_quota = await _get_setting(db, _DEFAULT_TOKEN_QUOTA_KEY)
    if legacy_quota is not None and free_plan_id is not None:
        try:
            quota_int = int(legacy_quota)
        except ValueError:
            quota_int = 0
        if quota_int > 0:
            await db.execute(
                update(BillingPlan)
                .where(BillingPlan.slug == "free")
                .values(monthly_token_quota=quota_int)
            )

    # ── Flip the flag ────────────────────────────────────────────────────
    await _set_setting(db, SETTING_BILLING_ENABLED, "true")

    await db.commit()

    logger.info(
        "Billing activation: plans_seeded=%s users_backfilled=%s "
        "default_plan_id=%s",
        plans_seeded,
        users_backfilled,
        free_plan_id,
    )

    return {
        "plans_seeded": plans_seeded,
        "users_backfilled": users_backfilled,
        "default_plan_id": free_plan_id,
        "billing_enabled": True,
    }


async def deactivate_billing(db: AsyncSession) -> dict[str, Any]:
    """Pure flag flip: turn billing off without touching any data.

    Plans, subscriptions, user.plan_id bindings — all remain intact. A
    later re-activation finds the catalogue already seeded and runs as
    a no-op.
    """
    await _set_setting(db, SETTING_BILLING_ENABLED, "false")
    await db.commit()
    return {"billing_enabled": False}


__all__ = [
    "SETTING_BILLING_ENABLED",
    "SETTING_DEFAULT_PLAN_ID",
    "activate_billing",
    "deactivate_billing",
    "is_billing_enabled",
    "require_billing_enabled",
]
