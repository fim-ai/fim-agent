"""Public version endpoint — no authentication required."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter

from fim_one import __version__

router = APIRouter(prefix="/api", tags=["system"])

# Captured once at module load time (≈ server startup).
_SERVER_START_TIME = datetime.now(UTC).isoformat()


@router.get("/version")
async def get_version() -> dict:
    """Return application version metadata.

    This is a public endpoint — no authentication required.
    """
    return {
        "version": __version__,
        "build_time": _SERVER_START_TIME,
        "app_name": "FIM One",
    }
