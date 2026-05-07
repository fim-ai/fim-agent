"""Tests for ``fim_one.web.services.quota_enforcer``.

Validates the precedence chain:
- ``user.plan.monthly_token_quota`` wins over ``user.token_quota``
- ``user.token_quota`` returns when no plan is bound
- Both unset returns ``None`` (treated as "unlimited" by chat.py)
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import fim_one.web.models  # noqa: F401 — register all models with metadata
from fim_one.db.base import Base
from fim_one.web.models import BillingPlan, User
from fim_one.web.services.quota_enforcer import (
    get_user_quota,
    get_user_quota_by_id,
)


@pytest_asyncio.fixture()
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


async def _make_user(
    session: AsyncSession,
    *,
    token_quota: int | None = None,
    plan_id: int | None = None,
) -> User:
    user = User(
        id=str(uuid.uuid4()),
        username=f"u_{uuid.uuid4().hex[:8]}",
        email=f"{uuid.uuid4().hex[:6]}@example.com",
        token_quota=token_quota,
        plan_id=plan_id,
    )
    session.add(user)
    await session.commit()
    return user


async def _make_plan(
    session: AsyncSession, *, slug: str, quota: int
) -> BillingPlan:
    plan = BillingPlan(
        slug=slug,
        name=slug.title(),
        monthly_token_quota=quota,
    )
    session.add(plan)
    await session.commit()
    return plan


class TestGetUserQuota:
    """``get_user_quota`` precedence chain."""

    @pytest.mark.asyncio
    async def test_plan_quota_wins_over_legacy_token_quota(
        self, session: AsyncSession
    ) -> None:
        plan = await _make_plan(session, slug="pro", quota=5_000_000)
        user = await _make_user(session, token_quota=999, plan_id=plan.id)

        # ``get_user_quota`` requires the relationship to be loaded;
        # the helper uses ``user.plan_id`` and falls back to a fresh
        # ``db.get`` so we don't need to eager-load ourselves.
        quota = await get_user_quota(user, session)
        assert quota == 5_000_000

    @pytest.mark.asyncio
    async def test_legacy_token_quota_returns_when_no_plan(
        self, session: AsyncSession
    ) -> None:
        user = await _make_user(session, token_quota=12_345, plan_id=None)
        quota = await get_user_quota(user, session)
        assert quota == 12_345

    @pytest.mark.asyncio
    async def test_returns_none_when_both_unset(
        self, session: AsyncSession
    ) -> None:
        user = await _make_user(session, token_quota=None, plan_id=None)
        quota = await get_user_quota(user, session)
        assert quota is None

    @pytest.mark.asyncio
    async def test_plan_id_set_but_plan_missing_falls_back_to_legacy(
        self, session: AsyncSession
    ) -> None:
        # Defensive case: plan_id points at a row that no longer exists
        # (data corruption / stale FK). Should fall back to legacy.
        user = await _make_user(session, token_quota=42, plan_id=99999)
        quota = await get_user_quota(user, session)
        assert quota == 42


class TestGetUserQuotaById:
    """``get_user_quota_by_id`` mirrors ``get_user_quota`` for chat.py."""

    @pytest.mark.asyncio
    async def test_plan_quota_wins(self, session: AsyncSession) -> None:
        plan = await _make_plan(session, slug="pro", quota=5_000_000)
        user = await _make_user(session, token_quota=100, plan_id=plan.id)
        quota = await get_user_quota_by_id(user.id, session)
        assert quota == 5_000_000

    @pytest.mark.asyncio
    async def test_legacy_quota_returns_when_no_plan(
        self, session: AsyncSession
    ) -> None:
        user = await _make_user(session, token_quota=200, plan_id=None)
        quota = await get_user_quota_by_id(user.id, session)
        assert quota == 200

    @pytest.mark.asyncio
    async def test_unknown_user_returns_none(
        self, session: AsyncSession
    ) -> None:
        quota = await get_user_quota_by_id("does-not-exist", session)
        assert quota is None
