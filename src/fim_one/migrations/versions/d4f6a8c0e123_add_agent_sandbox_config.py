"""add agent sandbox_config

Revision ID: d4f6a8c0e123
Revises: c3e5f7a9b012
Create Date: 2026-03-05 19:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from fim_one.migrations.helpers import table_has_column


# revision identifiers, used by Alembic.
revision: str = 'd4f6a8c0e123'
down_revision: Union[str, None] = 'c3e5f7a9b012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if not table_has_column(bind, "agents", "sandbox_config"):
        op.add_column('agents', sa.Column('sandbox_config', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('agents', 'sandbox_config')
