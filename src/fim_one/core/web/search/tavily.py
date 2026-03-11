"""Tavily Search backend (https://tavily.com)."""

from __future__ import annotations

import os

import httpx

from .base import BaseWebSearch, SearchResult

_TAVILY_URL = "https://api.tavily.com/search"
_DEFAULT_TIMEOUT = 30


class TavilySearch(BaseWebSearch):
    """Uses the Tavily Search API. Requires TAVILY_API_KEY."""

    def __init__(self, *, api_key: str = "", timeout: int = _DEFAULT_TIMEOUT) -> None:
        self._api_key = api_key or os.environ.get("TAVILY_API_KEY", "")
        if not self._api_key:
            raise ValueError("TAVILY_API_KEY is required for TavilySearch")
        self._timeout = timeout

    async def search(self, query: str, *, num_results: int = 10) -> list[SearchResult]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                _TAVILY_URL,
                json={
                    "api_key": self._api_key,
                    "query": query,
                    "max_results": num_results,
                    "search_depth": "basic",
                    "include_answer": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        return [
            SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("content", "")[:800],
                score=float(item.get("score", 0.0)),
            )
            for item in data.get("results", [])
        ]
