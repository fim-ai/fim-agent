"""add model_config role

Revision ID: f6h8j0k2l345
Revises: e5g7h9i1j234
Create Date: 2026-03-05 21:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from fim_one.migrations.helpers import table_has_column


# revision identifiers, used by Alembic.
revision: str = 'f6h8j0k2l345'
down_revision: Union[str, None] = 'e5g7h9i1j234'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if not table_has_column(bind, "model_configs", "role"):
        op.add_column('model_configs', sa.Column('role', sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column('model_configs', 'role')
