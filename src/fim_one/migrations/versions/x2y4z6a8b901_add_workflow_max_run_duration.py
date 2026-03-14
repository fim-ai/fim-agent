"""add max_run_duration_seconds to workflows

Revision ID: x2y4z6a8b901
Revises: w1x2y3z4a567
Create Date: 2026-03-14
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from fim_one.migrations.helpers import table_has_column

revision: str = "x2y4z6a8b901"
down_revision: Union[str, None] = "d5e6f7g8h901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    if not table_has_column(bind, "workflows", "max_run_duration_seconds"):
        with op.batch_alter_table("workflows") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "max_run_duration_seconds",
                    sa.Integer,
                    nullable=True,
                )
            )


def downgrade() -> None:
    with op.batch_alter_table("workflows") as batch_op:
        batch_op.drop_column("max_run_duration_seconds")
