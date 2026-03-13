"""create workflow_versions table

Revision ID: v1w2x3y4z567
Revises: s1k2l3m4n567
Create Date: 2026-03-14
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from fim_one.migrations.helpers import table_exists

revision: str = "v1w2x3y4z567"
down_revision: Union[str, None] = "s1k2l3m4n567"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    if not table_exists(bind, "workflow_versions"):
        op.create_table(
            "workflow_versions",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "workflow_id",
                sa.String(36),
                sa.ForeignKey("workflows.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("version_number", sa.Integer, nullable=False),
            sa.Column("blueprint", sa.JSON, nullable=False),
            sa.Column("input_schema", sa.JSON, nullable=True),
            sa.Column("output_schema", sa.JSON, nullable=True),
            sa.Column("change_summary", sa.Text, nullable=True),
            sa.Column(
                "created_by",
                sa.String(36),
                sa.ForeignKey("users.id"),
                nullable=True,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=False,
            ),
        )


def downgrade() -> None:
    op.drop_table("workflow_versions")
