"""add json_mode_enabled to model_configs

Revision ID: q7s9u1w3y456
Revises: p6r8t0v2x345
Create Date: 2026-03-11 18:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from fim_one.migrations.helpers import table_has_column

# revision identifiers, used by Alembic.
revision: str = "q7s9u1w3y456"
down_revision: Union[str, None] = "376d120aac52"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    if not table_has_column(bind, "model_configs", "json_mode_enabled"):
        with op.batch_alter_table("model_configs") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "json_mode_enabled",
                    sa.Boolean,
                    nullable=False,
                    server_default=sa.text("TRUE"),
                )
            )


def downgrade() -> None:
    with op.batch_alter_table("model_configs") as batch_op:
        batch_op.drop_column("json_mode_enabled")
