"""MCP (Model Context Protocol) client integration.

Provides :class:`MCPClient` for connecting to external MCP servers and
:class:`MCPToolAdapter` for wrapping MCP tools into the FIM Agent ``Tool``
protocol.

The ``mcp`` package is an optional dependency — import errors are deferred
so the rest of the framework works without it installed.
"""

from __future__ import annotations

from .adapter import MCPToolAdapter
from .client import MCPClient

__all__ = ["MCPClient", "MCPToolAdapter"]
