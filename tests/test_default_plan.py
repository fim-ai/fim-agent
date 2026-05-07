"""Tests for ``fim_one.web.services.default_plan``.

The helper resolves the Free plan id at registration time so new users
auto-bind to it. It must:

- Return the id when the seed row exists.
- Return ``None`` when the row is missing (registration falls through
  rather than fails).
- Never raise — the backfill migration covers any orphans.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import fim_one.web.models  # noqa: F401 — register all models with metadata
from fim_one.db.base import Base
from fim_one.web.models import BillingPlan
from fim_one.web.services.default_plan import get_free_plan_id


@pytest_asyncio.fixture()
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


class TestGetFreePlanId:
    @pytest.mark.asyncio
    async def test_returns_id_when_free_plan_seeded(
        self, session: AsyncSession
    ) -> None:
        plan = BillingPlan(slug="free", name="Free", monthly_token_quota=100_000)
        session.add(plan)
        await session.commit()

        plan_id = await get_free_plan_id(session)
        assert plan_id == plan.id

    @pytest.mark.asyncio
    async def test_returns_none_when_free_plan_missing(
        self, session: AsyncSession
    ) -> None:
        # Only Pro exists — Free row was somehow not seeded.
        session.add(
            BillingPlan(slug="pro", name="Pro", monthly_token_quota=5_000_000)
        )
        await session.commit()

        plan_id = await get_free_plan_id(session)
        assert plan_id is None

    @pytest.mark.asyncio
    async def test_returns_none_on_empty_table(
        self, session: AsyncSession
    ) -> None:
        plan_id = await get_free_plan_id(session)
        assert plan_id is None
