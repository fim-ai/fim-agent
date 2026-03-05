"""Tool registry for managing available tools."""

from __future__ import annotations

from typing import Any

from .base import Tool


class ToolRegistry:
    """Central registry that holds and manages tool instances.

    Provides lookup by name, registration/unregistration, and conversion
    to the OpenAI function-calling format for seamless LLM integration.
    """

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def register(self, tool: Tool) -> None:
        """Register a tool instance.

        Args:
            tool: A tool implementing the ``Tool`` protocol.

        Raises:
            ValueError: If a tool with the same name is already registered.
        """
        if tool.name in self._tools:
            raise ValueError(
                f"Tool '{tool.name}' is already registered. "
                "Unregister it first or use a different name."
            )
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> None:
        """Remove a tool by name.

        Args:
            name: The unique name of the tool to remove.

        Raises:
            KeyError: If no tool with the given name is registered.
        """
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' is not registered.")
        del self._tools[name]

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get(self, name: str) -> Tool | None:
        """Return the tool registered under *name*, or ``None``."""
        return self._tools.get(name)

    def list_tools(self) -> list[Tool]:
        """Return all registered tools as a list."""
        return list(self._tools.values())

    def list_categories(self) -> list[str]:
        """Return all unique categories of registered tools."""
        return sorted({tool.category for tool in self._tools.values()})

    def tool_summaries(self) -> list[str]:
        """Return 'name (category): description' for each tool."""
        return [
            f"- {t.name} ({t.category}): {t.description[:80]}"
            for t in self._tools.values()
        ]

    def filter_by_category(self, *categories: str) -> ToolRegistry:
        """Return a new ToolRegistry containing only tools in the given categories."""
        filtered = ToolRegistry()
        for tool in self._tools.values():
            if tool.category in categories:
                filtered.register(tool)
        return filtered

    def exclude_by_name(self, *names: str) -> ToolRegistry:
        """Return a new ToolRegistry excluding tools with the given names."""
        filtered = ToolRegistry()
        for tool in self._tools.values():
            if tool.name not in names:
                filtered.register(tool)
        return filtered

    def to_catalog(self) -> list[dict[str, str]]:
        """Return metadata for all registered tools (for frontend display)."""
        return [
            {
                "name": t.name,
                "display_name": t.display_name,
                "category": t.category,
                "description": t.description,
            }
            for t in self._tools.values()
        ]

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    def to_openai_tools(
        self, categories: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Convert registered tools to OpenAI function-calling format.

        Args:
            categories: If provided, only include tools whose category is
                in this list.  When ``None`` (default), all tools are included.

        Returns:
            A list of dicts conforming to the OpenAI ``tools`` parameter
            schema used in chat completion requests.
        """
        tools = self._tools.values()
        if categories is not None:
            tools = [t for t in tools if t.category in categories]
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters_schema,
                },
            }
            for tool in tools
        ]

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __repr__(self) -> str:
        tool_names = ", ".join(self._tools.keys())
        return f"ToolRegistry([{tool_names}])"
