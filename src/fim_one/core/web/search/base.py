"""Base protocol and data types for web search backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class SearchResult:
    """A single web search result."""

    title: str
    url: str
    snippet: str
    score: float = field(default=0.0)


class BaseWebSearch(ABC):
    """Abstract web search backend."""

    @abstractmethod
    async def search(self, query: str, *, num_results: int = 10) -> list[SearchResult]:
        """Search the web and return structured results.

        Args:
            query: The search query string.
            num_results: Maximum number of results to return.

        Returns:
            List of SearchResult ordered by relevance (best first).
        """
        ...
