"""add review_skills to organizations

Revision ID: o5p6q7r8s901
Revises: n4o5p6q7r890
Create Date: 2026-03-14
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from fim_one.migrations.helpers import table_exists, table_has_column

revision: str = "o5p6q7r8s901"
down_revision: Union[str, None] = "n4o5p6q7r890"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    if table_exists(bind, "organizations") and not table_has_column(
        bind, "organizations", "review_skills"
    ):
        with op.batch_alter_table("organizations") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "review_skills",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("FALSE"),
                )
            )


def downgrade() -> None:
    bind = op.get_bind()

    if table_has_column(bind, "organizations", "review_skills"):
        with op.batch_alter_table("organizations") as batch_op:
            batch_op.drop_column("review_skills")
