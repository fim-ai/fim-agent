"""HighGo driver -- PostgreSQL protocol compatible."""

from __future__ import annotations

from fim_one.core.tool.connector.database.drivers.postgresql import PostgreSQLDriver


class HighGoDriver(PostgreSQLDriver):
    """HighGo (瀚高) driver. PG-compatible, uses asyncpg."""

    pass
