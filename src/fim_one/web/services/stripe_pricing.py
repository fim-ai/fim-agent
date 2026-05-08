"""Shared Stripe Price lookup + formatting.

Both the user-facing ``/api/billing/plans`` endpoint and the admin
``/api/admin/billing/plans`` endpoint need to render the live amount /
currency / interval for a Stripe Price. They MUST agree byte-for-byte —
otherwise the admin sees one number and users see another, which is
exactly the drift this module exists to prevent.

The helper sits in ``services/`` (rather than each api module owning
its own copy) so the in-process cache is shared and Stripe gets one
``Price.retrieve`` call per ``stripe_price_id`` per cache window
regardless of how many endpoints are asking.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from fim_one.web.services.stripe_client import get_stripe

logger = logging.getLogger(__name__)


_PRICE_CACHE_TTL_SECONDS: float = 300.0
_price_cache: dict[str, tuple[float, dict[str, Any]]] = {}


def format_price(
    amount_cents: int | None,
    currency: str | None,
    interval: str | None,
) -> str:
    """Render a human-readable price string (``"$20.00 USD/month"``).

    Returns an empty string when the amount or currency is missing —
    callers display their own fallback (``"Free"`` for a null
    ``stripe_price_id``, an em-dash for a Stripe lookup failure).
    """
    if amount_cents is None or currency is None:
        return ""
    dollars = amount_cents / 100
    cur = currency.upper()
    suffix = f"/{interval}" if interval else ""
    return f"${dollars:.2f} {cur}{suffix}"


def fetch_price_details(stripe_price_id: str) -> dict[str, Any]:
    """Return ``{amount_cents, currency, interval}`` for a Stripe Price.

    Cached for :data:`_PRICE_CACHE_TTL_SECONDS`; on Stripe failure
    returns an empty dict so the caller can render an empty
    ``price_display`` rather than 500-ing the whole list.
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


def reset_price_cache() -> None:
    """Drop the price cache — used by tests."""
    _price_cache.clear()


__all__ = [
    "fetch_price_details",
    "format_price",
    "reset_price_cache",
]
