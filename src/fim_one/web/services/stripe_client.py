"""Stripe SDK singleton.

Lazy-initialized at import time.  Safe to import even when billing is
disabled — :func:`billing_enabled` reports the live state and
:func:`get_stripe` raises if callers try to use the SDK without
configuration.

Why a singleton instead of a factory:

- The official ``stripe`` Python SDK uses module-level globals
  (``stripe.api_key`` / ``stripe.api_version``); spinning up a "client
  per request" would just stomp on those globals anyway.
- Pinning ``api_version`` here means upstream Stripe API revisions
  cannot silently change response shapes — we upgrade explicitly.
"""

from __future__ import annotations

from types import ModuleType

import stripe

from fim_one.web.config import settings

#: Pinned Stripe API version. Bump deliberately and run the test suite
#: when migrating; never let the floating "latest" version of Stripe
#: rewrite our parser contracts mid-flight.
STRIPE_API_VERSION = "2024-12-18.acacia"


def _initialize() -> bool:
    """Configure the Stripe SDK if a secret key is present.

    Returns:
        ``True`` if the SDK was configured, ``False`` if billing is
        disabled (no key set) **or** the config is invalid (which
        :class:`fim_one.web.config.Settings` will surface as a
        :class:`ValueError` on attribute access).
    """
    try:
        secret = settings.STRIPE_SECRET_KEY
    except Exception:
        # Invalid/partial config — keep the SDK disabled and let the
        # operator see the underlying ValueError when they actually
        # invoke a billing endpoint via ``get_stripe()``.
        return False
    if secret is None:
        return False
    stripe.api_key = secret.get_secret_value()
    stripe.api_version = STRIPE_API_VERSION
    return True


_INITIALIZED: bool = _initialize()


def billing_enabled() -> bool:
    """Return ``True`` when the Stripe SDK has been configured.

    Use this as a feature flag in API handlers and the admin UI:
    when ``False``, billing endpoints should respond ``503`` (or
    omit themselves) and the frontend should hide payment CTAs.
    """
    return _INITIALIZED


def get_stripe() -> ModuleType:
    """Return the configured ``stripe`` module.

    Raises:
        RuntimeError: when billing is disabled. Callers should check
            :func:`billing_enabled` first and degrade gracefully.
    """
    if not _INITIALIZED:
        raise RuntimeError(
            "Billing disabled: STRIPE_SECRET_KEY not configured. "
            "Set STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET to enable Stripe."
        )
    return stripe


def reset_for_testing() -> None:
    """Reset the singleton's initialized flag.

    Tests that monkeypatch ``STRIPE_SECRET_KEY`` should call this
    after invalidating the cached ``settings`` (``settings.reset()``)
    so the next ``billing_enabled()`` / ``get_stripe()`` call reflects
    the new env.
    """
    global _INITIALIZED
    stripe.api_key = None
    _INITIALIZED = _initialize()
