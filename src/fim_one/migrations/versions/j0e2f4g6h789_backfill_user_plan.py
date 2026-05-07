"""Backfill ``users.plan_id`` to the Free plan for unassigned rows.

Revision ID: j0e2f4g6h789
Revises: i9d1e3f5g678
Create Date: 2026-05-07 21:40:00.000000

Post-Stripe-MVP every user must belong to at least the Free plan so the
quota resolver can find a finite tier without falling through to the
defensive system-wide default. New registrations auto-bind to the Free
plan in the application layer; this migration cleans up rows that
predate that change.

The upgrade is idempotent: re-running it after the table is fully
populated affects zero rows. The downgrade is intentionally a no-op —
reverting plan bindings would not restore the prior "unlimited" state
and could surprise admins who have since priced the Free plan.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

from fim_one.migrations.helpers import table_exists

# revision identifiers, used by Alembic.
revision: str = "j0e2f4g6h789"
down_revision: Union[str, None] = "i9d1e3f5g678"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # Defensive: the stripe_billing migration creates both tables, but
    # if a deploy is somehow ahead of itself, just no-op.
    if not table_exists(bind, "users") or not table_exists(bind, "billing_plans"):
        return

    # Set every user with a NULL plan_id to point at the Free plan.
    # Wrapped in a subselect rather than a Python lookup so the SQL
    # works identically on SQLite and PostgreSQL with a single statement.
    # If the Free plan row is missing (corrupt seed) the UPDATE simply
    # leaves rows untouched — the quota resolver still has the
    # system_settings fallback to fall back on.
    op.execute(
        """
        UPDATE users
           SET plan_id = (SELECT id FROM billing_plans WHERE slug = 'free')
         WHERE plan_id IS NULL
           AND EXISTS (SELECT 1 FROM billing_plans WHERE slug = 'free')
        """
    )


def downgrade() -> None:
    # Intentional no-op: undoing the backfill would unset plan bindings
    # that the application now relies on. Safer to leave rows in place;
    # the next ``upgrade`` is itself idempotent.
    pass
