"""add conversation fast_llm_tokens

Revision ID: c3e5f7a9b012
Revises: b2d4e6f8a901
Create Date: 2026-03-05 18:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from fim_one.migrations.helpers import table_has_column


# revision identifiers, used by Alembic.
revision: str = 'c3e5f7a9b012'
down_revision: Union[str, None] = 'b2d4e6f8a901'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if not table_has_column(bind, "conversations", "fast_llm_tokens"):
        op.add_column('conversations', sa.Column('fast_llm_tokens', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('conversations', 'fast_llm_tokens')
