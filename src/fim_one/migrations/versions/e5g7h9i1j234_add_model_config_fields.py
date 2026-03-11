"""add model_config max_output_tokens and context_size

Revision ID: e5g7h9i1j234
Revises: d4f6a8c0e123
Create Date: 2026-03-05 20:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from fim_one.migrations.helpers import table_has_column


# revision identifiers, used by Alembic.
revision: str = 'e5g7h9i1j234'
down_revision: Union[str, None] = 'd4f6a8c0e123'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if not table_has_column(bind, "model_configs", "max_output_tokens"):
        op.add_column('model_configs', sa.Column('max_output_tokens', sa.Integer(), nullable=True))
    if not table_has_column(bind, "model_configs", "context_size"):
        op.add_column('model_configs', sa.Column('context_size', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('model_configs', 'context_size')
    op.drop_column('model_configs', 'max_output_tokens')
