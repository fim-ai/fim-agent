"""add user preferred_language

Revision ID: a1c2d3e4f567
Revises: e4b8e690b124
Create Date: 2026-03-04 12:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from fim_one.migrations.helpers import table_has_column


# revision identifiers, used by Alembic.
revision: str = 'a1c2d3e4f567'
down_revision: Union[str, None] = 'e4b8e690b124'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if not table_has_column(bind, "users", "preferred_language"):
        op.add_column('users', sa.Column('preferred_language', sa.String(10), nullable=False, server_default='auto'))


def downgrade() -> None:
    op.drop_column('users', 'preferred_language')
