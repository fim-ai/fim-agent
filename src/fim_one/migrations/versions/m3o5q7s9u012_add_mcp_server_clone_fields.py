"""add mcp_server clone fields

Revision ID: m3o5q7s9u012
Revises: l2n4p6r8t901
Create Date: 2026-03-10 18:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from fim_one.migrations.helpers import table_has_column

# revision identifiers, used by Alembic.
revision: str = "m3o5q7s9u012"
down_revision: Union[str, None] = "l2n4p6r8t901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if not table_has_column(bind, "mcp_servers", "cloned_from_server_id"):
        op.add_column("mcp_servers", sa.Column("cloned_from_server_id", sa.String(36), nullable=True))
    if not table_has_column(bind, "mcp_servers", "cloned_from_user_id"):
        op.add_column("mcp_servers", sa.Column("cloned_from_user_id", sa.String(36), nullable=True))


def downgrade() -> None:
    op.drop_column("mcp_servers", "cloned_from_user_id")
    op.drop_column("mcp_servers", "cloned_from_server_id")
