"""Async engine and session factory for SQLAlchemy.

SQLite concurrency notes
------------------------
SQLite supports only a single writer at a time.  To avoid
``sqlite3.OperationalError: database is locked`` under concurrent requests we
apply three mitigations:

1. **WAL journal mode** — allows readers to proceed while a write is in
   progress, drastically reducing lock contention.
2. **Increased busy timeout** (30 s) — the default is 5 s which is far too
   short when an LLM streaming endpoint holds a session open for tens of
   seconds.
3. **StaticPool** — a single shared connection via ``StaticPool`` so that all
   async tasks serialise through one underlying SQLite connection, eliminating
   multi-connection write contention entirely.
"""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from .base import Base

logger = logging.getLogger(__name__)

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _get_database_url() -> str:
    return os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./data/fim_agent.db")


async def init_db() -> None:
    """Create the async engine and run ``CREATE TABLE`` for all models."""
    global _engine, _session_factory

    # Import all models so Base.metadata is fully populated before create_all.
    import fim_agent.web.models  # noqa: F401

    url = _get_database_url()
    logger.info("Initializing database: %s", url.split("@")[-1] if "@" in url else url)

    connect_args: dict = {}
    kwargs: dict = {}
    is_sqlite = url.startswith("sqlite")

    if is_sqlite:
        connect_args["check_same_thread"] = False
        # Give SQLite 30 seconds to wait for a lock instead of the default 5.
        connect_args["timeout"] = 30
        # Use StaticPool so that all async tasks share the same underlying
        # SQLite connection.  This avoids multi-connection write contention
        # that causes "database is locked" even with WAL mode enabled.
        kwargs["poolclass"] = StaticPool
        # Ensure the data directory exists for SQLite file-based databases.
        db_path = url.split("///", 1)[-1] if "///" in url else None
        if db_path and db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    _engine = create_async_engine(url, connect_args=connect_args, echo=False, **kwargs)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)

    # -- SQLite-specific PRAGMAs -------------------------------------------
    # Enable WAL mode so readers don't block writers and vice-versa.  Also
    # turn on normal synchronous mode (safe with WAL) for better throughput.
    # The listener is registered before any connection is opened (the engine
    # is lazy), so every connection — including the one used by create_all
    # below — will have these pragmas applied.
    if is_sqlite:

        @event.listens_for(_engine.sync_engine, "connect")
        def _set_sqlite_pragmas(dbapi_conn, connection_record):  # noqa: ARG001
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.close()

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database initialized successfully")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an ``AsyncSession`` — intended for use with FastAPI ``Depends``."""
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    async with _session_factory() as session:
        yield session


def create_session() -> AsyncSession:
    """Create an ``AsyncSession`` directly — caller must close it.

    Unlike :func:`get_session` (which is an async-generator suited for FastAPI
    ``Depends``), this returns a plain session object whose lifetime is managed
    by the caller.  Use this inside SSE async generators where breaking out of
    an ``async for`` would prematurely close the generator-managed session.
    """
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _session_factory()


async def shutdown_db() -> None:
    """Dispose of the engine and release all connections."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        logger.info("Database engine disposed")
        _engine = None
        _session_factory = None
