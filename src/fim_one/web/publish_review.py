"""Shared publish review logic for all resource types.

When an organization has per-resource review enabled, resources published to
that org enter a ``pending_review`` state instead of being immediately visible
to other members.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fim_one.web.models.organization import Organization

_REVIEW_COLUMN_MAP = {
    "agent": "review_agents",
    "connector": "review_connectors",
    "knowledge_base": "review_kbs",
    "mcp_server": "review_mcp_servers",
    "workflow": "review_workflows",
    "skill": "review_skills",
}

_TABLE_TO_RESOURCE_TYPE = {
    "agents": "agent",
    "connectors": "connector",
    "knowledge_bases": "knowledge_base",
    "mcp_servers": "mcp_server",
    "workflows": "workflow",
    "skills": "skill",
}


async def get_org_requires_review(
    org_id: str, db: AsyncSession, resource_type: str
) -> bool:
    """Check if an org requires publish review for a given resource type."""
    column_name = _REVIEW_COLUMN_MAP.get(resource_type)
    if not column_name:
        return False

    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()
    if org is None:
        return False
    return bool(getattr(org, column_name, False))


async def apply_publish_status(
    resource,
    org_id: str,
    db: AsyncSession,
    resource_type: str,
    publisher_id: str | None = None,
) -> None:
    """Set publish_status based on org review setting. Call during publish.

    If publisher_id matches the org owner_id (org creator), the review is
    bypassed and publish_status is set to None immediately.
    """
    # Org creator bypass: fetch org to compare owner_id
    if publisher_id is not None:
        result = await db.execute(
            select(Organization).where(Organization.id == org_id)
        )
        org = result.scalar_one_or_none()
        if org is not None and org.owner_id == publisher_id:
            resource.publish_status = None
            return

    if await get_org_requires_review(org_id, db, resource_type):
        resource.publish_status = "pending_review"
    else:
        resource.publish_status = None  # no review needed


async def check_edit_revert(
    resource, db: AsyncSession, resource_type: str | None = None
) -> bool:
    """Auto-revert publish_status on edit if resource is in a review-required org
    and currently approved.

    Returns True if status was reverted (caller may want to include this in response).
    Does NOT revert if status is 'rejected' (user must manually resubmit).
    """
    if getattr(resource, "visibility", None) != "org" or not getattr(resource, "org_id", None):
        return False
    if getattr(resource, "publish_status", None) != "approved":
        return False

    # Auto-detect resource_type from table name if not provided
    if resource_type is None:
        table_name = getattr(resource.__class__, "__tablename__", None)
        resource_type = _TABLE_TO_RESOURCE_TYPE.get(table_name, "")

    if not await get_org_requires_review(resource.org_id, db, resource_type):
        return False
    # Auto-revert
    resource.publish_status = "pending_review"
    resource.reviewed_by = None
    resource.reviewed_at = None
    resource.review_note = None
    return True
