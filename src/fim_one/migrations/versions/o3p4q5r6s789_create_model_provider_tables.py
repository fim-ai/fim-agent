"""Create model_providers, model_provider_models, model_groups tables.

Three-tier model management: Provider -> Model -> Group.

Revision ID: o3p4q5r6s789
Revises: n2l3m4n5o678
Create Date: 2026-03-21
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "o3p4q5r6s789"
down_revision: Union[str, None] = "n2l3m4n5o678"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from fim_one.migrations.helpers import table_exists

    bind = op.get_bind()

    # -- model_providers --
    if not table_exists(bind, "model_providers"):
        op.create_table(
            "model_providers",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("base_url", sa.String(500), nullable=True),
            sa.Column("api_key", sa.Text(), nullable=True),  # EncryptedString stores as Text
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )

    # -- model_provider_models --
    if not table_exists(bind, "model_provider_models"):
        op.create_table(
            "model_provider_models",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "provider_id",
                sa.String(36),
                sa.ForeignKey("model_providers.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("model_name", sa.String(100), nullable=False),
            sa.Column("temperature", sa.Float(), nullable=True),
            sa.Column("max_output_tokens", sa.Integer(), nullable=True),
            sa.Column("context_size", sa.Integer(), nullable=True),
            sa.Column("json_mode_enabled", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )

    # -- model_groups --
    if not table_exists(bind, "model_groups"):
        op.create_table(
            "model_groups",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column(
                "general_model_id",
                sa.String(36),
                sa.ForeignKey("model_provider_models.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "fast_model_id",
                sa.String(36),
                sa.ForeignKey("model_provider_models.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "reasoning_model_id",
                sa.String(36),
                sa.ForeignKey("model_provider_models.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    op.drop_table("model_groups")
    op.drop_table("model_provider_models")
    op.drop_table("model_providers")
