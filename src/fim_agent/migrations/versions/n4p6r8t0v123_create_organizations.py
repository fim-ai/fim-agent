"""create organizations and org_memberships tables

Revision ID: n4p6r8t0v123
Revises: m3o5q7s9u012
Create Date: 2026-03-11 12:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from fim_agent.migrations.helpers import table_exists

# revision identifiers, used by Alembic.
revision: str = "n4p6r8t0v123"
down_revision: Union[str, None] = "m3o5q7s9u012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    if not table_exists(bind, "organizations"):
        op.create_table(
            "organizations",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("slug", sa.String(100), nullable=False, unique=True),
            sa.Column("description", sa.Text, nullable=True),
            sa.Column("icon", sa.String(100), nullable=True),
            sa.Column(
                "owner_id",
                sa.String(36),
                sa.ForeignKey("users.id"),
                nullable=False,
            ),
            sa.Column(
                "parent_id",
                sa.String(36),
                sa.ForeignKey("organizations.id"),
                nullable=True,
            ),
            sa.Column("settings", sa.JSON, nullable=True),
            sa.Column(
                "is_active",
                sa.Boolean,
                nullable=False,
                server_default=sa.text("TRUE"),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_organizations_slug", "organizations", ["slug"])
        op.create_index("ix_organizations_owner_id", "organizations", ["owner_id"])

    if not table_exists(bind, "org_memberships"):
        op.create_table(
            "org_memberships",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "org_id",
                sa.String(36),
                sa.ForeignKey("organizations.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "user_id",
                sa.String(36),
                sa.ForeignKey("users.id"),
                nullable=False,
            ),
            sa.Column("role", sa.String(20), nullable=False),
            sa.Column(
                "invited_by",
                sa.String(36),
                sa.ForeignKey("users.id"),
                nullable=True,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("org_id", "user_id", name="uq_org_membership"),
        )
        op.create_index("ix_org_memberships_org_id", "org_memberships", ["org_id"])
        op.create_index("ix_org_memberships_user_id", "org_memberships", ["user_id"])


def downgrade() -> None:
    op.drop_table("org_memberships")
    op.drop_table("organizations")
