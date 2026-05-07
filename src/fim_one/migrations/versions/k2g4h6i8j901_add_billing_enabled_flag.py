"""Billing pipeline feature flag.

Revision ID: k2g4h6i8j901
Revises: k1f3g5h7i890
Create Date: 2026-05-07 22:35:00.000000

Adds the ``system_settings.billing_enabled`` row — a runtime flag that
gates the Stripe billing pipeline (user-facing endpoints, webhook,
admin CRUD) and the corresponding frontend tabs / nav items.

Default value is ``"false"`` for both fresh installs and upgrades:
admins must explicitly opt in via the activation flow (or the system
settings UI) so a private deployment without Stripe credentials never
accidentally surfaces a non-functional payment UX.

The migration is idempotent: re-running over an install that already
has the row leaves the existing value (so an admin who has already
turned billing on doesn't get reset to ``false`` on a routine upgrade).
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from fim_one.migrations.helpers import table_exists

# revision identifiers, used by Alembic.
revision: str = "k2g4h6i8j901"
down_revision: Union[str, None] = "k1f3g5h7i890"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_BILLING_ENABLED_KEY = "billing_enabled"


def upgrade() -> None:
    bind = op.get_bind()

    if not table_exists(bind, "system_settings"):
        return

    # IF NOT EXISTS — preserves an admin's prior choice on re-runs.
    bind.execute(
        sa.text(
            """
            INSERT INTO system_settings (key, value)
            SELECT :k, 'false'
            WHERE NOT EXISTS (
                SELECT 1 FROM system_settings WHERE key = :k
            )
            """
        ),
        {"k": _BILLING_ENABLED_KEY},
    )


def downgrade() -> None:
    bind = op.get_bind()

    if table_exists(bind, "system_settings"):
        bind.execute(
            sa.text("DELETE FROM system_settings WHERE key = :k"),
            {"k": _BILLING_ENABLED_KEY},
        )
