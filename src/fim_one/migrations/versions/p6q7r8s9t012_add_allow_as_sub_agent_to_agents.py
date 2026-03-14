"""add allow_as_sub_agent to agents

Revision ID: p6q7r8s9t012
Revises: o5p6q7r8s901
Create Date: 2026-03-15
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from fim_one.migrations.helpers import table_exists, table_has_column

revision: str = "p6q7r8s9t012"
down_revision: Union[str, None] = "o5p6q7r8s901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if table_exists(op.get_bind(), "agents") and not table_has_column(
        op.get_bind(), "agents", "allow_as_sub_agent"
    ):
        op.add_column(
            "agents",
            sa.Column(
                "allow_as_sub_agent",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("TRUE"),
            ),
        )


def downgrade() -> None:
    if table_exists(op.get_bind(), "agents") and table_has_column(
        op.get_bind(), "agents", "allow_as_sub_agent"
    ):
        op.drop_column("agents", "allow_as_sub_agent")
