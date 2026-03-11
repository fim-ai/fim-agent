"""add reset_token to email_verifications

Revision ID: h8j0l2n4p567
Revises: g7i9k1m3n456
Create Date: 2026-03-07 18:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from fim_one.migrations.helpers import table_has_column


# revision identifiers, used by Alembic.
revision: str = "h8j0l2n4p567"
down_revision: Union[str, None] = "g7i9k1m3n456"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if not table_has_column(bind, "email_verifications", "reset_token"):
        op.add_column(
            "email_verifications",
            sa.Column("reset_token", sa.String(36), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("email_verifications", "reset_token")
