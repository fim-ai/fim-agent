"""Encrypt MCP server env/headers at rest using Fernet.

Changes column types from JSON to Text for mcp_servers.env and .headers
(EncryptedJSON TypeDecorator stores Fernet ciphertext as plain Text),
then encrypts all existing plaintext values in-place.

mcp_server_credentials.env_blob and .headers_blob are already Text columns,
so only data encryption is needed there.

Revision ID: e7f8g9a1b2c3
Revises: 655b0da054b4
Create Date: 2026-03-13
"""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

from fim_one.migrations.helpers import table_exists, table_has_column

revision = "e7f8g9a1b2c3"
down_revision = "655b0da054b4"
branch_labels = None
depends_on = None


def _encrypt_blob(value: str | None) -> str | None:
    """Encrypt a plaintext JSON string; skip if already encrypted or empty."""
    if not value:
        return value
    # Fernet tokens start with 'gAAAAA'; skip if already encrypted
    if not value.startswith("{"):
        return value
    try:
        from fim_one.core.security.encryption import encrypt_credential

        data = json.loads(value)
        return encrypt_credential(data)
    except Exception:
        return value


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    # 1. Change mcp_servers.env and .headers from JSON to Text (for PG)
    #    SQLite: JSON is stored as TEXT affinity, so this is effectively a no-op
    #    but we use batch_alter_table for safety.
    if table_exists(bind, "mcp_servers"):
        if dialect != "sqlite":
            # PostgreSQL: explicit type change
            with op.batch_alter_table("mcp_servers") as batch_op:
                batch_op.alter_column(
                    "env",
                    type_=sa.Text(),
                    existing_type=sa.JSON(),
                    existing_nullable=True,
                )
                batch_op.alter_column(
                    "headers",
                    type_=sa.Text(),
                    existing_type=sa.JSON(),
                    existing_nullable=True,
                )

        # 2. Encrypt existing plaintext env/headers in mcp_servers
        rows = bind.execute(
            sa.text("SELECT id, env, headers FROM mcp_servers WHERE env IS NOT NULL OR headers IS NOT NULL")
        ).fetchall()
        for row_id, env_val, headers_val in rows:
            new_env = _encrypt_blob(env_val if isinstance(env_val, str) else (json.dumps(env_val) if env_val else None))
            new_headers = _encrypt_blob(headers_val if isinstance(headers_val, str) else (json.dumps(headers_val) if headers_val else None))
            if new_env != env_val or new_headers != headers_val:
                bind.execute(
                    sa.text("UPDATE mcp_servers SET env = :env, headers = :headers WHERE id = :id"),
                    {"env": new_env, "headers": new_headers, "id": row_id},
                )

    # 3. Encrypt existing plaintext env_blob/headers_blob in mcp_server_credentials
    if table_exists(bind, "mcp_server_credentials"):
        rows = bind.execute(
            sa.text("SELECT id, env_blob, headers_blob FROM mcp_server_credentials WHERE env_blob IS NOT NULL OR headers_blob IS NOT NULL")
        ).fetchall()
        for row_id, env_val, headers_val in rows:
            new_env = _encrypt_blob(env_val)
            new_headers = _encrypt_blob(headers_val)
            if new_env != env_val or new_headers != headers_val:
                bind.execute(
                    sa.text("UPDATE mcp_server_credentials SET env_blob = :env, headers_blob = :headers WHERE id = :id"),
                    {"env": new_env, "headers": new_headers, "id": row_id},
                )


def downgrade() -> None:
    # Downgrade is lossy — we cannot reverse encryption without storing the
    # original plaintext.  The decrypt_credential fallback in the TypeDecorator
    # means old code can still read the encrypted values, so downgrade is safe
    # to leave as a no-op.
    pass
