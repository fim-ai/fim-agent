"""Jina Search backend (https://s.jina.ai)."""

from __future__ import annotations

import os
import re

import httpx

from .base import BaseWebSearch, SearchResult

_JINA_SEARCH_URL = "https://s.jina.ai/"
_DEFAULT_TIMEOUT = 30

# Matches Jina's markdown blocks: ## N. [Title](URL)\n...body...
_RESULT_RE = re.compile(
    r"##\s+\d+\.\s+\[([^\]]+)\]\(([^)]+)\)(.*?)(?=\n##\s+\d+\.|\Z)",
    re.DOTALL,
)


class JinaSearch(BaseWebSearch):
    """Uses Jina's s.jina.ai search endpoint.

    Works without an API key (rate-limited); set JINA_API_KEY for higher limits.
    """

    def __init__(self, *, api_key: str = "", timeout: int = _DEFAULT_TIMEOUT) -> None:
        self._api_key = api_key or os.environ.get("JINA_API_KEY", "")
        self._timeout = timeout

    async def search(self, query: str, *, num_results: int = 10) -> list[SearchResult]:
        headers: dict[str, str] = {"Accept": "text/markdown"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(f"{_JINA_SEARCH_URL}{query}", headers=headers)
            resp.raise_for_status()
            raw = resp.text

        return _parse_jina_markdown(raw, num_results)


def _parse_jina_markdown(text: str, max_results: int) -> list[SearchResult]:
    results: list[SearchResult] = []
    for m in _RESULT_RE.finditer(text):
        title = m.group(1)
        url = m.group(2)
        body = m.group(3).strip()
        # Strip metadata lines (Published:, URL:, etc.)
        snippet = re.sub(r"^(?:Published|Date|Source|URL):.*\n?", "", body, flags=re.MULTILINE).strip()
        results.append(SearchResult(title=title, url=url, snippet=snippet[:800]))
        if len(results) >= max_results:
            break

    if not results:
        # Fallback: whole response as one result
        results.append(SearchResult(title="Search Results", url="", snippet=text[:3000]))

    return results
