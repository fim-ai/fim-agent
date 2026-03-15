"""add resource_refs JSON column to skills table

Revision ID: p7q8r9s0t123
Revises: o5p6q7r8s901
Create Date: 2026-03-16
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from fim_one.migrations.helpers import table_exists, table_has_column

revision: str = "p7q8r9s0t123"
down_revision: Union[str, None] = "o5p6q7r8s901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    if table_exists(bind, "skills") and not table_has_column(
        bind, "skills", "resource_refs"
    ):
        op.add_column(
            "skills",
            sa.Column("resource_refs", sa.JSON, nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()

    if table_has_column(bind, "skills", "resource_refs"):
        op.drop_column("skills", "resource_refs")
