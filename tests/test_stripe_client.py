"""Tests for the Stripe SDK singleton and the Settings validator.

Covers:
- ``billing_enabled() is False`` when ``STRIPE_SECRET_KEY`` is unset.
- A valid ``sk_test_*`` key initializes the SDK and ``get_stripe()``
  returns the configured ``stripe`` module.
- Settings validator rejects partial Stripe config (key without
  webhook secret, or vice versa).
- Settings validator rejects an obviously-wrong prefix
  (``pk_live_*``, garbage).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from fim_one.web.config import Settings


# ---------------------------------------------------------------------------
# Settings validator
# ---------------------------------------------------------------------------


class TestSettingsStripeValidator:
    """Cross-field validation on Stripe config."""

    def test_no_stripe_config_is_valid(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
        monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
        s = Settings.from_env()
        assert s.STRIPE_SECRET_KEY is None
        assert s.STRIPE_WEBHOOK_SECRET is None

    def test_full_stripe_config_is_valid(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_abc123")
        monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_xyz")
        s = Settings.from_env()
        assert s.STRIPE_SECRET_KEY is not None
        assert s.STRIPE_SECRET_KEY.get_secret_value() == "sk_test_abc123"
        assert s.STRIPE_WEBHOOK_SECRET is not None

    def test_partial_only_secret_key_rejected(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_abc")
        monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
        with pytest.raises(ValidationError) as exc_info:
            Settings.from_env()
        assert "Partial Stripe config" in str(exc_info.value)

    def test_partial_only_webhook_secret_rejected(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
        monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_xyz")
        with pytest.raises(ValidationError) as exc_info:
            Settings.from_env()
        assert "Partial Stripe config" in str(exc_info.value)

    @pytest.mark.parametrize(
        "bad_key",
        [
            "pk_live_oops_publishable_key",
            "pk_test_oops_publishable_key",
            "garbage_no_prefix_at_all",
            "sk_LIVE_wrong_case",  # case-sensitive
        ],
    )
    def test_invalid_secret_key_prefix_rejected(
        self, monkeypatch: pytest.MonkeyPatch, bad_key: str
    ) -> None:
        monkeypatch.setenv("STRIPE_SECRET_KEY", bad_key)
        monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_xyz")
        with pytest.raises(ValidationError) as exc_info:
            Settings.from_env()
        assert "Invalid Stripe secret key prefix" in str(exc_info.value)

    @pytest.mark.parametrize(
        "good_key",
        ["sk_test_abc", "sk_live_abc", "rk_test_abc", "rk_live_abc"],
    )
    def test_accepts_all_legitimate_prefixes(
        self, monkeypatch: pytest.MonkeyPatch, good_key: str
    ) -> None:
        monkeypatch.setenv("STRIPE_SECRET_KEY", good_key)
        monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_xyz")
        s = Settings.from_env()
        assert s.STRIPE_SECRET_KEY is not None
        assert s.STRIPE_SECRET_KEY.get_secret_value() == good_key

    def test_blank_value_treated_as_unset(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Empty / whitespace-only env values count as 'not set'.

        Operators frequently blank a value rather than delete the line;
        we should not treat that as a half-configured deploy.
        """
        monkeypatch.setenv("STRIPE_SECRET_KEY", "   ")
        monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "")
        s = Settings.from_env()
        assert s.STRIPE_SECRET_KEY is None
        assert s.STRIPE_WEBHOOK_SECRET is None

    def test_default_billing_return_url(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
        monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
        monkeypatch.delenv("STRIPE_BILLING_RETURN_URL", raising=False)
        s = Settings.from_env()
        assert s.STRIPE_BILLING_RETURN_URL == (
            "http://localhost:3000/settings/billing"
        )

    def test_custom_billing_return_url(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
        monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
        monkeypatch.setenv(
            "STRIPE_BILLING_RETURN_URL", "https://one.fim.ai/settings/billing"
        )
        s = Settings.from_env()
        assert s.STRIPE_BILLING_RETURN_URL == "https://one.fim.ai/settings/billing"


# ---------------------------------------------------------------------------
# stripe_client singleton
# ---------------------------------------------------------------------------


def _reload_client() -> object:
    """Reset the lazy ``settings`` cache and re-init the stripe singleton.

    The settings/client modules are imported once per test session;
    forcing a real ``importlib.reload`` would discard their lazy proxy
    object identity. Calling ``settings.reset()`` + ``reset_for_testing()``
    achieves the same effect (re-read env on next access) without losing
    the proxy.
    """
    import fim_one.web.config as cfg
    import fim_one.web.services.stripe_client as sc

    cfg.settings.reset()
    sc.reset_for_testing()
    return sc


class TestStripeClientSingleton:
    """``billing_enabled`` / ``get_stripe`` flag behavior."""

    def test_disabled_when_no_secret_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
        monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
        sc = _reload_client()
        assert sc.billing_enabled() is False  # type: ignore[attr-defined]
        with pytest.raises(RuntimeError, match="Billing disabled"):
            sc.get_stripe()  # type: ignore[attr-defined]

    def test_enabled_with_valid_test_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_dummy_key_for_unit_test")
        monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_dummy")
        sc = _reload_client()

        assert sc.billing_enabled() is True  # type: ignore[attr-defined]
        stripe_module = sc.get_stripe()  # type: ignore[attr-defined]
        # The returned object is the real stripe SDK module with our key set.
        assert stripe_module.api_key == "sk_test_dummy_key_for_unit_test"
        assert stripe_module.api_version == sc.STRIPE_API_VERSION  # type: ignore[attr-defined]

    def test_reset_for_testing_picks_up_new_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``reset_for_testing()`` must re-read env after monkeypatch."""
        monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
        monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
        sc = _reload_client()
        assert sc.billing_enabled() is False  # type: ignore[attr-defined]

        # Now set the env and rebuild settings + re-init client.
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_late_init")
        monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_late")
        import fim_one.web.config as cfg

        cfg.settings.reset()
        sc.reset_for_testing()  # type: ignore[attr-defined]

        assert sc.billing_enabled() is True  # type: ignore[attr-defined]

    def test_get_stripe_disabled_when_partial_config(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A partial Stripe config must keep billing disabled (not crash imports).

        litellm's ``load_dotenv()`` lands ``.env`` into ``os.environ`` at
        import time — if a developer's local ``.env`` only has
        ``STRIPE_SECRET_KEY`` and an empty ``STRIPE_WEBHOOK_SECRET``,
        the singleton must degrade gracefully instead of crashing
        every importer of ``fim_one.web.services``.
        """
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_partial")
        monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
        sc = _reload_client()
        assert sc.billing_enabled() is False  # type: ignore[attr-defined]
