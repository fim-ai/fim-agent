"""Request Tools — dynamically load additional tools mid-conversation."""

from __future__ import annotations

import logging
from typing import Any

from fim_one.core.tool.base import BaseTool, Tool
from fim_one.core.tool.registry import ToolRegistry

logger = logging.getLogger(__name__)


class RequestToolsTool(BaseTool):
    """Dynamically load additional tools into the current session.

    This meta-tool is automatically registered when the agent's tool-selection
    phase has filtered the tool set.  It allows the LLM to discover and load
    tools that weren't included in the initial selection, without requiring a
    new selection round-trip.

    The tool maintains references to both the full tool registry (read-only)
    and the active/effective tool registry (mutated on load).  When ``run()``
    is called, requested tools are copied from the full registry into the
    active registry so subsequent iterations can use them.
    """

    def __init__(
        self,
        all_tools: ToolRegistry,
        active_tools: ToolRegistry,
    ) -> None:
        """Initialise with full and active registries.

        Args:
            all_tools: The complete registry of all available tools (read-only).
            active_tools: The currently active/loaded tools.  This is a mutable
                reference shared with the agent loop — tools registered here
                become immediately available.
        """
        self._all_tools = all_tools
        self._active_tools = active_tools

    # ------------------------------------------------------------------
    # Tool protocol
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "request_tools"

    @property
    def display_name(self) -> str:
        return "Request Tools"

    @property
    def category(self) -> str:
        return "system"

    @property
    def cacheable(self) -> bool:
        # Side-effect: modifies the available tool set.
        return False

    @property
    def description(self) -> str:
        """Dynamically list unloaded tools so the LLM knows what's available."""
        unloaded = self._get_unloaded_tools()
        if not unloaded:
            return "Load additional tools. (All tools are currently loaded.)"

        catalog = "\n".join(
            f"- {t.name}: {t.description.replace(chr(10), ' ').strip()[:80]}"
            for t in unloaded
        )
        return (
            "Load additional tools into the current session. "
            "Available tools not yet loaded:\n" + catalog
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "tool_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Names of tools to load into the current session.",
                },
            },
            "required": ["tool_names"],
        }

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def run(self, **kwargs: Any) -> str:
        """Load requested tools into the active registry.

        Returns a summary of which tools were loaded, already loaded, or
        not found.
        """
        tool_names: list[str] = kwargs.get("tool_names", [])
        if not tool_names:
            return "No tool names provided."

        active_names = {t.name for t in self._active_tools.list_tools()}

        loaded: list[str] = []
        not_found: list[str] = []
        already_loaded: list[str] = []

        for name in tool_names:
            if name == self.name:
                # Prevent requesting itself.
                already_loaded.append(name)
                continue
            if name in active_names:
                already_loaded.append(name)
                continue
            tool = self._all_tools.get(name)
            if tool is not None:
                self._active_tools.register(tool)
                active_names.add(name)
                loaded.append(name)
                logger.info("request_tools: loaded '%s' into active set", name)
            else:
                not_found.append(name)

        parts: list[str] = []
        if loaded:
            parts.append(f"Loaded: {', '.join(loaded)}")
        if already_loaded:
            parts.append(f"Already loaded: {', '.join(already_loaded)}")
        if not_found:
            parts.append(f"Not found: {', '.join(not_found)}")
        return ". ".join(parts) if parts else "No tools to load."

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_unloaded_tools(self) -> list["Tool"]:
        """Return tools in the full registry that are not yet active."""
        active_names = {t.name for t in self._active_tools.list_tools()}
        return [
            t for t in self._all_tools.list_tools()
            if t.name not in active_names and t.name != self.name
        ]
