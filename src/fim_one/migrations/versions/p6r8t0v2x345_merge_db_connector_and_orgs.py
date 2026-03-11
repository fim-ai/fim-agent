"""merge database connector and organizations branches

Revision ID: p6r8t0v2x345
Revises: c1d2e3f4, o5q7s9u1w234
Create Date: 2026-03-11 18:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "p6r8t0v2x345"
down_revision: tuple[str, str] = ("c1d2e3f4", "o5q7s9u1w234")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
