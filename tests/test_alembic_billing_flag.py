"""Tests for the billing-flag Alembic migrations.

Validates the two migrations introduced alongside the
``billing_enabled`` feature flag:

- ``k1f3g5h7i890`` — adds the ``system_settings.default_plan_id``
  pointer and an ``ON DELETE RESTRICT`` FK on ``users.plan_id``.
- ``k2g4h6i8j901`` — adds the ``system_settings.billing_enabled`` row.

Both must be idempotent on replay (no duplicate rows, no FK churn) and
must work cleanly against a fresh in-memory SQLite database.
"""

from __future__ import annotations

import importlib

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect

# Import the migration modules by file path so this test does not
# depend on the (long, monolithic) project Alembic graph.
DEFAULT_PLAN_POINTER_MODULE = (
    "fim_one.migrations.versions.k1f3g5h7i890_add_default_plan_pointer"
)
BILLING_FLAG_MODULE = (
    "fim_one.migrations.versions.k2g4h6i8j901_add_billing_enabled_flag"
)


@pytest.fixture()
def synchronous_engine() -> sa.Engine:
    return create_engine("sqlite:///:memory:", future=True)


def _bootstrap_schema(engine: sa.Engine, *, with_free_plan: bool) -> None:
    """Stand up the minimum tables our migrations touch.

    ``users`` and ``billing_plans`` are created with the columns the
    real app uses; ``system_settings`` mirrors the project's actual
    ORM model (key text PK, value text NOT NULL).
    """
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "CREATE TABLE users ("
                "  id VARCHAR(36) PRIMARY KEY,"
                "  email VARCHAR(255) NOT NULL,"
                "  plan_id INTEGER"
                ")"
            )
        )
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
                "CREATE TABLE system_settings ("
                "  key VARCHAR(100) PRIMARY KEY,"
                "  value TEXT NOT NULL"
                ")"
            )
        )
        if with_free_plan:
            conn.execute(
                sa.text(
                    "INSERT INTO billing_plans (slug, name, monthly_token_quota) "
                    "VALUES ('free', 'Free', 100000)"
                )
            )


def _run_upgrade(engine: sa.Engine, module_name: str) -> None:
    module = importlib.import_module(module_name)
    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            module.upgrade()
        conn.commit()


def _run_downgrade(engine: sa.Engine, module_name: str) -> None:
    module = importlib.import_module(module_name)
    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            module.downgrade()
        conn.commit()


# ---------------------------------------------------------------------------
# default_plan_id pointer migration
# ---------------------------------------------------------------------------


class TestDefaultPlanPointer:
    def test_inserts_pointer_when_free_plan_exists(
        self, synchronous_engine: sa.Engine
    ) -> None:
        _bootstrap_schema(synchronous_engine, with_free_plan=True)
        _run_upgrade(synchronous_engine, DEFAULT_PLAN_POINTER_MODULE)

        with synchronous_engine.connect() as conn:
            row = conn.execute(
                sa.text(
                    "SELECT value FROM system_settings WHERE key='default_plan_id'"
                )
            ).first()
        assert row is not None
        # Free plan id is auto-incremented to 1 on the empty table.
        assert int(row[0]) == 1

    def test_skips_pointer_when_no_free_plan(
        self, synchronous_engine: sa.Engine
    ) -> None:
        _bootstrap_schema(synchronous_engine, with_free_plan=False)
        _run_upgrade(synchronous_engine, DEFAULT_PLAN_POINTER_MODULE)

        with synchronous_engine.connect() as conn:
            row = conn.execute(
                sa.text(
                    "SELECT value FROM system_settings WHERE key='default_plan_id'"
                )
            ).first()
        assert row is None

    def test_idempotent_replay(
        self, synchronous_engine: sa.Engine
    ) -> None:
        """Re-running the upgrade must not duplicate the pointer row."""
        _bootstrap_schema(synchronous_engine, with_free_plan=True)
        _run_upgrade(synchronous_engine, DEFAULT_PLAN_POINTER_MODULE)
        _run_upgrade(synchronous_engine, DEFAULT_PLAN_POINTER_MODULE)

        with synchronous_engine.connect() as conn:
            count = conn.execute(
                sa.text(
                    "SELECT COUNT(*) FROM system_settings "
                    "WHERE key='default_plan_id'"
                )
            ).scalar()
        assert count == 1

    def test_creates_users_plan_id_fk(
        self, synchronous_engine: sa.Engine
    ) -> None:
        _bootstrap_schema(synchronous_engine, with_free_plan=True)
        _run_upgrade(synchronous_engine, DEFAULT_PLAN_POINTER_MODULE)

        insp = inspect(synchronous_engine)
        fks = insp.get_foreign_keys("users")
        # SQLite reports the FK without a name in some dialects; we
        # accept either the explicit name or any FK pointing at billing_plans.
        assert any(
            fk["referred_table"] == "billing_plans" for fk in fks
        ), f"expected an FK on users.plan_id → billing_plans, got {fks}"


# ---------------------------------------------------------------------------
# billing_enabled flag migration
# ---------------------------------------------------------------------------


class TestBillingFlagMigration:
    def test_inserts_flag_with_false_default(
        self, synchronous_engine: sa.Engine
    ) -> None:
        _bootstrap_schema(synchronous_engine, with_free_plan=False)
        _run_upgrade(synchronous_engine, BILLING_FLAG_MODULE)

        with synchronous_engine.connect() as conn:
            value = conn.execute(
                sa.text(
                    "SELECT value FROM system_settings WHERE key='billing_enabled'"
                )
            ).scalar()
        assert value == "false"

    def test_preserves_existing_value_on_replay(
        self, synchronous_engine: sa.Engine
    ) -> None:
        """Re-runs MUST NOT reset an admin's prior 'true' choice."""
        _bootstrap_schema(synchronous_engine, with_free_plan=False)
        _run_upgrade(synchronous_engine, BILLING_FLAG_MODULE)

        # Admin flips the flag on after the first migration.
        with synchronous_engine.begin() as conn:
            conn.execute(
                sa.text(
                    "UPDATE system_settings SET value='true' "
                    "WHERE key='billing_enabled'"
                )
            )

        # Re-run: should leave the admin's true intact.
        _run_upgrade(synchronous_engine, BILLING_FLAG_MODULE)

        with synchronous_engine.connect() as conn:
            value = conn.execute(
                sa.text(
                    "SELECT value FROM system_settings "
                    "WHERE key='billing_enabled'"
                )
            ).scalar()
        assert value == "true"

    def test_downgrade_removes_flag(
        self, synchronous_engine: sa.Engine
    ) -> None:
        _bootstrap_schema(synchronous_engine, with_free_plan=False)
        _run_upgrade(synchronous_engine, BILLING_FLAG_MODULE)
        _run_downgrade(synchronous_engine, BILLING_FLAG_MODULE)

        with synchronous_engine.connect() as conn:
            value = conn.execute(
                sa.text(
                    "SELECT value FROM system_settings "
                    "WHERE key='billing_enabled'"
                )
            ).first()
        assert value is None
