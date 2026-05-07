"""Tests for the ``backfill_user_plan`` migration (``j0e2f4g6h789``).

Validates the three behaviours the migration promises:

1. Rows with ``plan_id IS NULL`` get rewritten to point at the Free plan.
2. Rows with an explicit ``plan_id`` (Pro / custom) are left alone.
3. The migration is idempotent — re-running on a populated table is a
   no-op.

The downgrade is intentionally a no-op; we just assert it doesn't raise.
"""

from __future__ import annotations

import importlib

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine

MIGRATION_MODULE = "fim_one.migrations.versions.j0e2f4g6h789_backfill_user_plan"


@pytest.fixture()
def engine_with_billing() -> sa.Engine:
    """Bootstrap a sync SQLite DB with ``users`` + ``billing_plans`` rows.

    The migration only needs the two tables and a Free plan row; we
    skip the rest of the schema because the SQL is targeted.
    """
    eng = create_engine("sqlite:///:memory:", future=True)
    with eng.begin() as conn:
        conn.execute(
            sa.text(
                "CREATE TABLE billing_plans ("
                "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "  slug VARCHAR(32) NOT NULL UNIQUE,"
                "  name VARCHAR(64) NOT NULL,"
                "  monthly_token_quota BIGINT NOT NULL"
                ")"
            )
        )
        conn.execute(
            sa.text(
                "CREATE TABLE users ("
                "  id VARCHAR(36) PRIMARY KEY,"
                "  email VARCHAR(255) NOT NULL,"
                "  plan_id INTEGER"
                ")"
            )
        )
    return eng


def _seed_free_plan(engine: sa.Engine) -> int:
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO billing_plans (slug, name, monthly_token_quota) "
                "VALUES ('free', 'Free', 100000)"
            )
        )
        free_id = conn.execute(
            sa.text("SELECT id FROM billing_plans WHERE slug='free'")
        ).scalar_one()
    return int(free_id)


def _seed_pro_plan(engine: sa.Engine) -> int:
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO billing_plans (slug, name, monthly_token_quota) "
                "VALUES ('pro', 'Pro', 5000000)"
            )
        )
        pro_id = conn.execute(
            sa.text("SELECT id FROM billing_plans WHERE slug='pro'")
        ).scalar_one()
    return int(pro_id)


def _seed_user(engine: sa.Engine, *, user_id: str, plan_id: int | None) -> None:
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO users (id, email, plan_id) "
                "VALUES (:id, :email, :plan)"
            ),
            {"id": user_id, "email": f"{user_id}@example.com", "plan": plan_id},
        )


def _run_upgrade(engine: sa.Engine) -> None:
    module = importlib.import_module(MIGRATION_MODULE)
    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            module.upgrade()
        conn.commit()


def _run_downgrade(engine: sa.Engine) -> None:
    module = importlib.import_module(MIGRATION_MODULE)
    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            module.downgrade()
        conn.commit()


# ---------------------------------------------------------------------------
# upgrade()
# ---------------------------------------------------------------------------


class TestUpgrade:
    def test_backfills_null_plan_id_to_free(
        self, engine_with_billing: sa.Engine
    ) -> None:
        free_id = _seed_free_plan(engine_with_billing)
        _seed_user(engine_with_billing, user_id="u1", plan_id=None)
        _seed_user(engine_with_billing, user_id="u2", plan_id=None)

        _run_upgrade(engine_with_billing)

        with engine_with_billing.connect() as conn:
            rows = conn.execute(
                sa.text("SELECT id, plan_id FROM users ORDER BY id")
            ).all()
        assert len(rows) == 2
        assert all(r.plan_id == free_id for r in rows)

    def test_leaves_explicit_plan_id_alone(
        self, engine_with_billing: sa.Engine
    ) -> None:
        free_id = _seed_free_plan(engine_with_billing)
        pro_id = _seed_pro_plan(engine_with_billing)
        _seed_user(engine_with_billing, user_id="u_pro", plan_id=pro_id)
        _seed_user(engine_with_billing, user_id="u_null", plan_id=None)

        _run_upgrade(engine_with_billing)

        with engine_with_billing.connect() as conn:
            pro_user = conn.execute(
                sa.text("SELECT plan_id FROM users WHERE id='u_pro'")
            ).scalar_one()
            null_user = conn.execute(
                sa.text("SELECT plan_id FROM users WHERE id='u_null'")
            ).scalar_one()

        assert pro_user == pro_id  # unchanged
        assert null_user == free_id  # backfilled

    def test_no_users_with_null_plan_id_after_upgrade(
        self, engine_with_billing: sa.Engine
    ) -> None:
        _seed_free_plan(engine_with_billing)
        _seed_user(engine_with_billing, user_id="u1", plan_id=None)
        _seed_user(engine_with_billing, user_id="u2", plan_id=None)

        _run_upgrade(engine_with_billing)

        with engine_with_billing.connect() as conn:
            null_count = conn.execute(
                sa.text("SELECT COUNT(*) FROM users WHERE plan_id IS NULL")
            ).scalar_one()
        assert null_count == 0

    def test_idempotent_replay(
        self, engine_with_billing: sa.Engine
    ) -> None:
        free_id = _seed_free_plan(engine_with_billing)
        _seed_user(engine_with_billing, user_id="u1", plan_id=None)

        _run_upgrade(engine_with_billing)
        _run_upgrade(engine_with_billing)  # should be a no-op

        with engine_with_billing.connect() as conn:
            row = conn.execute(
                sa.text("SELECT plan_id FROM users WHERE id='u1'")
            ).scalar_one()
        assert row == free_id

    def test_no_op_when_free_plan_missing(
        self, engine_with_billing: sa.Engine
    ) -> None:
        # Defensive: if Free plan is somehow missing, the migration must
        # not crash — leaves rows untouched and lets the resolver fall
        # through to the system default.
        _seed_pro_plan(engine_with_billing)  # only Pro
        _seed_user(engine_with_billing, user_id="u1", plan_id=None)

        _run_upgrade(engine_with_billing)  # must not raise

        with engine_with_billing.connect() as conn:
            row = conn.execute(
                sa.text("SELECT plan_id FROM users WHERE id='u1'")
            ).scalar_one()
        assert row is None  # untouched

    def test_no_op_when_tables_missing(self) -> None:
        # If billing_plans isn't built yet (deploy ordering edge case),
        # the upgrade must not crash.
        eng = create_engine("sqlite:///:memory:", future=True)
        _run_upgrade(eng)  # must not raise


# ---------------------------------------------------------------------------
# downgrade() — no-op
# ---------------------------------------------------------------------------


class TestDowngrade:
    def test_downgrade_is_no_op(
        self, engine_with_billing: sa.Engine
    ) -> None:
        free_id = _seed_free_plan(engine_with_billing)
        _seed_user(engine_with_billing, user_id="u1", plan_id=None)
        _run_upgrade(engine_with_billing)

        _run_downgrade(engine_with_billing)  # must not raise

        with engine_with_billing.connect() as conn:
            row = conn.execute(
                sa.text("SELECT plan_id FROM users WHERE id='u1'")
            ).scalar_one()
        # Backfill stays applied.
        assert row == free_id
