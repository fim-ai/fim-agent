"""Add channels and confirmation_requests tables for Feishu Channel integration.

Revision ID: e5f7g9h1i234
Revises: d4e5f6g7h123
Create Date: 2026-04-18
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "e5f7g9h1i234"
down_revision = "d4e5f6g7h123"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    from fim_one.migrations.helpers import index_exists, table_exists

    # --- channels -----------------------------------------------------------
    if not table_exists(bind, "channels"):
        op.create_table(
            "channels",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("type", sa.String(50), nullable=False),
            sa.Column(
                "org_id",
                sa.String(36),
                sa.ForeignKey("organizations.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("config", sa.Text, nullable=False),
            sa.Column(
                "is_active",
                sa.Boolean,
                nullable=False,
                server_default=sa.text("TRUE"),
            ),
            sa.Column(
                "created_by",
                sa.String(36),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
        )

    if not index_exists(bind, "channels", "ix_channels_type"):
        op.create_index("ix_channels_type", "channels", ["type"])
    if not index_exists(bind, "channels", "ix_channels_org_id"):
        op.create_index("ix_channels_org_id", "channels", ["org_id"])
    if not index_exists(bind, "channels", "ix_channels_created_by"):
        op.create_index("ix_channels_created_by", "channels", ["created_by"])

    # --- confirmation_requests ----------------------------------------------
    if not table_exists(bind, "confirmation_requests"):
        op.create_table(
            "confirmation_requests",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("tool_call_id", sa.String(128), nullable=True),
            sa.Column("agent_id", sa.String(36), nullable=True),
            sa.Column(
                "user_id",
                sa.String(36),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "org_id",
                sa.String(36),
                sa.ForeignKey("organizations.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "channel_id",
                sa.String(36),
                sa.ForeignKey("channels.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "status",
                sa.String(20),
                nullable=False,
                server_default="pending",
            ),
            sa.Column("payload", sa.JSON, nullable=True),
            sa.Column(
                "responded_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
            sa.Column("responded_by_open_id", sa.String(128), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=True,
            ),
        )

    if not index_exists(
        bind, "confirmation_requests", "ix_confirmation_requests_agent_id"
    ):
        op.create_index(
            "ix_confirmation_requests_agent_id",
            "confirmation_requests",
            ["agent_id"],
        )
    if not index_exists(
        bind, "confirmation_requests", "ix_confirmation_requests_user_id"
    ):
        op.create_index(
            "ix_confirmation_requests_user_id",
            "confirmation_requests",
            ["user_id"],
        )
    if not index_exists(
        bind, "confirmation_requests", "ix_confirmation_requests_org_id"
    ):
        op.create_index(
            "ix_confirmation_requests_org_id",
            "confirmation_requests",
            ["org_id"],
        )
    if not index_exists(
        bind, "confirmation_requests", "ix_confirmation_requests_channel_id"
    ):
        op.create_index(
            "ix_confirmation_requests_channel_id",
            "confirmation_requests",
            ["channel_id"],
        )
    if not index_exists(
        bind, "confirmation_requests", "ix_confirmation_requests_status"
    ):
        op.create_index(
            "ix_confirmation_requests_status",
            "confirmation_requests",
            ["status"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    from fim_one.migrations.helpers import table_exists

    if table_exists(bind, "confirmation_requests"):
        op.drop_table("confirmation_requests")
    if table_exists(bind, "channels"):
        op.drop_table("channels")
