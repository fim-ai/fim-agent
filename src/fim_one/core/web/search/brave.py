"""Brave Search backend (https://brave.com/search/api/)."""

from __future__ import annotations

import os

import httpx

from .base import BaseWebSearch, SearchResult

_BRAVE_URL = "https://api.search.brave.com/res/v1/web/search"
_DEFAULT_TIMEOUT = 30


class BraveSearch(BaseWebSearch):
    """Uses the Brave Search API. Requires BRAVE_API_KEY."""

    def __init__(self, *, api_key: str = "", timeout: int = _DEFAULT_TIMEOUT) -> None:
        self._api_key = api_key or os.environ.get("BRAVE_API_KEY", "")
        if not self._api_key:
            raise ValueError("BRAVE_API_KEY is required for BraveSearch")
        self._timeout = timeout

    async def search(self, query: str, *, num_results: int = 10) -> list[SearchResult]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(
                _BRAVE_URL,
                headers={
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip",
                    "X-Subscription-Token": self._api_key,
                },
                params={"q": query, "count": min(num_results, 20)},
            )
            resp.raise_for_status()
            data = resp.json()

        return [
            SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("description", "")[:800],
            )
            for item in data.get("web", {}).get("results", [])
        ]
