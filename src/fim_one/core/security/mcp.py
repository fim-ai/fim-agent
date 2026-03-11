"""MCP transport security policies."""

from __future__ import annotations

import os
from pathlib import PurePosixPath


def is_stdio_allowed() -> bool:
    """Check whether stdio MCP transport is permitted.

    Default: **False** (secure by default).  Set ``ALLOW_STDIO_MCP=true``
    to enable stdio servers.
    """
    return os.getenv("ALLOW_STDIO_MCP", "").lower() in ("1", "true", "yes")


def get_allowed_stdio_commands() -> set[str]:
    """Return the set of allowed base command names for stdio MCP servers.

    Configured via ``ALLOWED_STDIO_COMMANDS`` (comma-separated).
    """
    raw = os.getenv(
        "ALLOWED_STDIO_COMMANDS",
        "npx,uvx,node,python,python3,deno,bun",
    )
    return {cmd.strip() for cmd in raw.split(",") if cmd.strip()}


def validate_stdio_command(command: str) -> None:
    """Validate that *command* is in the allowed list.

    Extracts the base name (e.g. ``/usr/bin/npx`` -> ``npx``) and checks
    against :func:`get_allowed_stdio_commands`.

    Raises:
        ValueError: If the command is not allowed.
    """
    if not command or not command.strip():
        raise ValueError("MCP stdio command must not be empty")

    base = PurePosixPath(command.strip()).name
    allowed = get_allowed_stdio_commands()
    if base not in allowed:
        raise ValueError(
            f"Command '{base}' is not in the allowed stdio command list: "
            f"{sorted(allowed)}. Configure via ALLOWED_STDIO_COMMANDS env var."
        )
