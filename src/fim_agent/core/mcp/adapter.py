"""Adapter that wraps an MCP tool definition into the FIM Agent Tool protocol."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from fim_agent.core.tool.base import BaseTool


class MCPToolAdapter(BaseTool):
    """Wraps a single MCP tool into the FIM Agent ``Tool`` protocol.

    Tool names are prefixed with the server name to avoid collisions when
    multiple MCP servers expose tools with the same name:
    ``"{server_name}__{tool_name}"``.

    Parameters
    ----------
    server_name:
        Unique identifier of the MCP server this tool belongs to.
    tool_def:
        Dictionary with ``name``, ``description``, and ``inputSchema`` keys
        as returned by the MCP ``tools/list`` endpoint.
    call_fn:
        An async callable that sends ``tools/call`` to the MCP server.
        Signature: ``(tool_name: str, arguments: dict) -> CallToolResult``.
    """

    def __init__(
        self,
        server_name: str,
        tool_def: dict[str, Any],
        call_fn: Callable[..., Coroutine[Any, Any, Any]],
    ) -> None:
        self._name = f"{server_name}__{tool_def['name']}"
        self._description = tool_def.get("description", "")
        self._schema: dict[str, Any] = tool_def.get(
            "inputSchema", {"type": "object", "properties": {}}
        )
        self._original_name = tool_def["name"]
        self._call_fn = call_fn

    # ------------------------------------------------------------------
    # Tool protocol
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return self._name

    @property
    def display_name(self) -> str:
        server = self._name.split("__")[0].replace("_", " ").title()
        action = self._original_name.replace("_", " ").title()
        return f"{server}: {action}"

    @property
    def category(self) -> str:
        return "mcp"

    @property
    def description(self) -> str:
        return self._description

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return self._schema

    async def run(self, **kwargs: Any) -> str:
        """Call the MCP server's ``tools/call`` endpoint and extract text."""
        result = await self._call_fn(self._original_name, kwargs)
        return self._extract_text(result)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_text(result: Any) -> str:
        """Extract a plain-text string from an MCP ``CallToolResult``.

        The result object exposes:
        - ``content``: a list of content items (each with ``.type`` and
          ``.text`` for text items, or ``.data`` for binary items).
        - ``isError``: boolean flag indicating whether the call failed.
        """
        parts: list[str] = []
        for item in result.content:
            if hasattr(item, "text"):
                parts.append(item.text)
            elif hasattr(item, "data"):
                parts.append(f"[{item.type}: {len(item.data)} bytes]")
        output = "\n".join(parts)
        if result.isError:
            output = f"[MCP Error] {output}"
        return output

    def __repr__(self) -> str:
        return f"MCPToolAdapter(name={self._name!r}, original={self._original_name!r})"
