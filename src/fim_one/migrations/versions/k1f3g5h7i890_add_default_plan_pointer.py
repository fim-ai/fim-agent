"""Default plan pointer + ``users.plan_id`` FK guard.

Revision ID: k1f3g5h7i890
Revises: j0e2f4g6h789
Create Date: 2026-05-07 22:30:00.000000

Replaces the brittle ``WHERE slug='free'`` lookup with a stable
pointer in ``system_settings.default_plan_id``. The pointer is set at
migration time when a Free plan row already exists; brand-new installs
that haven't seeded the catalogue yet will have the pointer initialised
by the admin activation flow instead.

Also tightens ``users.plan_id`` with an ``ON DELETE RESTRICT`` foreign
key so an admin can't accidentally orphan billing relationships by
deleting a plan that still has users on it. ``RESTRICT`` (rather than
``SET NULL``) makes the failure loud instead of silent — the soft-
delete semantics in the admin API already cover the "retire a plan"
workflow without dropping the row.

The migration is idempotent: re-running over an install that already
has the pointer / FK is a no-op.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from fim_one.migrations.helpers import table_exists

# revision identifiers, used by Alembic.
revision: str = "k1f3g5h7i890"
down_revision: Union[str, None] = "j0e2f4g6h789"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_DEFAULT_PLAN_ID_KEY = "default_plan_id"


def _has_fk_named(bind: sa.engine.Connection, table: str, fk_name: str) -> bool:
    """Return True if a foreign key with the given name exists on *table*."""
    insp = sa.inspect(bind)
    try:
        for fk in insp.get_foreign_keys(table):
            if fk.get("name") == fk_name:
                return True
    except Exception:
        return False
    return False


def upgrade() -> None:
    bind = op.get_bind()

    if not table_exists(bind, "system_settings") or not table_exists(
        bind, "billing_plans"
    ):
        # Defensive: prior migrations ought to have created both, but a
        # partial deploy shouldn't blow up the upgrade chain.
        return

    # ── Insert the pointer row when missing ──────────────────────────────
    # Resolve the Free plan id at migration time; brand-new installs that
    # haven't seeded the catalogue yet will have the pointer set by the
    # admin activation flow instead — so a NULL result here is fine.
    free_id_row = bind.execute(
        sa.text("SELECT id FROM billing_plans WHERE slug = 'free' LIMIT 1")
    ).first()

    if free_id_row is not None:
        free_plan_id = int(free_id_row[0])
        bind.execute(
            sa.text(
                """
                INSERT INTO system_settings (key, value)
                SELECT :k, :v
                WHERE NOT EXISTS (
                    SELECT 1 FROM system_settings WHERE key = :k
                )
                """
            ),
            {"k": _DEFAULT_PLAN_ID_KEY, "v": str(free_plan_id)},
        )

    # ── FK on users.plan_id (RESTRICT) ───────────────────────────────────
    # The original ``i9d1e3f5g678`` migration added the column without
    # an FK constraint (because SQLite ALTER COLUMN is limited and
    # batch_alter_table at the time didn't include FK semantics). We
    # close the loop here. SQLite happens to be tolerant if the FK
    # already exists (it just lives in the table redefinition); PG
    # would refuse — so we gate the alter on a name check.
    if not table_exists(bind, "users"):
        return

    fk_name = "fk_users_plan_id_billing_plans"
    if _has_fk_named(bind, "users", fk_name):
        return

    try:
        with op.batch_alter_table("users") as batch_op:
            batch_op.create_foreign_key(
                fk_name,
                "billing_plans",
                ["plan_id"],
                ["id"],
                ondelete="RESTRICT",
            )
    except Exception:
        # SQLite's batch_alter_table will rebuild the table; on some
        # broken-state databases (e.g. corrupt unique-constraint
        # metadata) the rebuild can fail. We log via Alembic's stdout
        # but don't block the rest of the upgrade — operators can fix
        # the constraint manually after the dust settles.
        import logging

        logging.getLogger("alembic.runtime.migration").exception(
            "Failed to create %s; continuing without FK", fk_name
        )


def downgrade() -> None:
    bind = op.get_bind()

    if table_exists(bind, "users"):
        fk_name = "fk_users_plan_id_billing_plans"
        if _has_fk_named(bind, "users", fk_name):
            try:
                with op.batch_alter_table("users") as batch_op:
                    batch_op.drop_constraint(fk_name, type_="foreignkey")
            except Exception:
                pass

    if table_exists(bind, "system_settings"):
        bind.execute(
            sa.text(
                "DELETE FROM system_settings WHERE key = :k"
            ),
            {"k": _DEFAULT_PLAN_ID_KEY},
        )
