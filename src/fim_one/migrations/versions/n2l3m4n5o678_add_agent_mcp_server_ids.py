"""Add mcp_server_ids to agents table.

Revision ID: n2l3m4n5o678
Revises: m1k2t3r4d567
Create Date: 2026-03-18
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "n2l3m4n5o678"
down_revision = "m1k2t3r4d567"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from fim_one.migrations.helpers import table_has_column

    bind = op.get_bind()
    if not table_has_column(bind, "agents", "mcp_server_ids"):
        op.add_column("agents", sa.Column("mcp_server_ids", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("agents", "mcp_server_ids")
