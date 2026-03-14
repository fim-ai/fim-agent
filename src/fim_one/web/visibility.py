"""Shared visibility filter — two-tier: personal | org.

Market org resources are visible only via ResourceSubscription.
Nobody joins Market org, so MARKET_ORG_ID is never in user_org_ids and the
org condition is naturally skipped for Market resources.  Subscribed Market
resources flow through the subscribed_ids path instead.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import and_, or_, select

from fim_one.web.models.resource_subscription import ResourceSubscription

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


def build_visibility_filter(
    model,
    user_id: str,
    user_org_ids: list[str],
    subscribed_ids: list[str] | None = None,
):
    """Build a SQLAlchemy WHERE clause for visibility filtering.

    Returns rows where:
    - user owns the resource (any visibility), OR
    - resource is published to an org the user belongs to, OR
    - resource id is in the user's subscription list

    Market org resources: Nobody joins Market org, so MARKET_ORG_ID is never
    present in ``user_org_ids`` and the org-membership condition is skipped.
    Subscribed Market resources are included via ``subscribed_ids``.

    For a higher-level helper that auto-fetches org IDs and subscriptions,
    see :func:`resolve_visibility`.
    """
    conditions = [
        model.user_id == user_id,  # own resources (any visibility)
    ]

    if user_org_ids:
        # Only show org resources that either don't need review or are approved.
        # pending_review and rejected resources are hidden from other org members
        # (the owner still sees them via the user_id == user_id condition above).
        conditions.append(
            and_(
                model.visibility == "org",
                model.org_id.in_(user_org_ids),
                or_(
                    model.publish_status == None,  # noqa: E711 — no review needed
                    model.publish_status == "approved",
                ),
            )
        )

    if subscribed_ids:
        conditions.append(model.id.in_(subscribed_ids))

    return or_(*conditions)


async def resolve_visibility(
    model: Any,
    user_id: str,
    resource_type: str,
    db: AsyncSession,
) -> tuple[Any, list[str], list[str]]:
    """High-level visibility resolver: org IDs + subscriptions in one call.

    Parameters
    ----------
    model:
        SQLAlchemy model class (Agent, Connector, MCPServer, etc.)
    user_id:
        Current user ID.
    resource_type:
        Subscription resource type (``"agent"``, ``"connector"``,
        ``"mcp_server"``, ``"knowledge_base"``, ``"skill"``, ``"workflow"``).
    db:
        Async DB session.

    Returns
    -------
    (filter_clause, user_org_ids, subscribed_ids)
        - ``filter_clause``: ready-to-use SQLAlchemy WHERE clause
        - ``user_org_ids``: list of org IDs the user belongs to
        - ``subscribed_ids``: list of subscribed resource IDs
    """
    from fim_one.web.auth import get_user_org_ids

    user_org_ids = await get_user_org_ids(user_id, db)
    sub_result = await db.execute(
        select(ResourceSubscription.resource_id).where(
            ResourceSubscription.user_id == user_id,
            ResourceSubscription.resource_type == resource_type,
        )
    )
    subscribed_ids = sub_result.scalars().all()
    clause = build_visibility_filter(
        model, user_id, user_org_ids, subscribed_ids=subscribed_ids,
    )
    return clause, user_org_ids, subscribed_ids
