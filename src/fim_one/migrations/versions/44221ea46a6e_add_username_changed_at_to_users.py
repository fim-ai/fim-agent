"""add username_changed_at to users

Revision ID: 44221ea46a6e
Revises: h8j0l2n4p567
Create Date: 2026-03-09 01:29:00.640673
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from fim_one.migrations.helpers import table_has_column


# revision identifiers, used by Alembic.
revision: str = '44221ea46a6e'
down_revision: Union[str, None] = 'h8j0l2n4p567'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if not table_has_column(bind, "users", "username_changed_at"):
        op.add_column('users', sa.Column('username_changed_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'username_changed_at')
