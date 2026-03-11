"""Base protocol for web fetch backends."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseWebFetch(ABC):
    """Abstract web fetch backend."""

    @abstractmethod
    async def fetch(self, url: str) -> str:
        """Fetch a URL and return its content as text/Markdown.

        Args:
            url: The URL to fetch (http:// or https://).

        Returns:
            Page content as Markdown or plain text.
        """
        ...
