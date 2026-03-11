"""KingbaseES driver -- PostgreSQL protocol compatible."""

from __future__ import annotations

from fim_one.core.tool.connector.database.drivers.postgresql import PostgreSQLDriver


class KingbaseESDriver(PostgreSQLDriver):
    """KingbaseES (人大金仓) driver. PG-compatible, uses asyncpg."""

    pass
