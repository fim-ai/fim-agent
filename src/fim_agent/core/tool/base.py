"""Tool protocol and base class definitions."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Tool(Protocol):
    """Protocol that all tools must implement."""

    @property
    def name(self) -> str:
        """Unique tool name."""
        ...

    @property
    def description(self) -> str:
        """Human-readable description for LLM."""
        ...

    @property
    def category(self) -> str:
        """Tool category for grouping and filtering."""
        ...

    @property
    def display_name(self) -> str:
        """Human-friendly display name."""
        ...

    @property
    def parameters_schema(self) -> dict[str, Any]:
        """JSON Schema for tool parameters."""
        ...

    async def run(self, **kwargs: Any) -> str:
        """Execute the tool and return string result."""
        ...


class BaseTool:
    """Convenience base class implementing the Tool protocol."""

    @property
    def name(self) -> str:
        raise NotImplementedError

    @property
    def description(self) -> str:
        raise NotImplementedError

    @property
    def category(self) -> str:
        return "general"

    @property
    def display_name(self) -> str:
        return self.name.replace("_", " ").title()

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}, "required": []}

    @abstractmethod
    async def run(self, **kwargs: Any) -> str:
        ...
