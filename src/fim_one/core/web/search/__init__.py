"""Web search backends and provider factory."""

from __future__ import annotations

import os

from .base import BaseWebSearch, SearchResult
from .brave import BraveSearch
from .jina import JinaSearch
from .tavily import TavilySearch

__all__ = [
    "BaseWebSearch",
    "SearchResult",
    "JinaSearch",
    "TavilySearch",
    "BraveSearch",
    "get_web_searcher",
    "format_results",
]


def get_web_searcher(*, timeout: int = 30) -> BaseWebSearch:
    """Return the configured web search backend.

    Selection order:
    1. ``WEB_SEARCH_PROVIDER`` env var (jina / tavily / brave)
    2. Auto-detect: use Tavily if TAVILY_API_KEY set, Brave if BRAVE_API_KEY set
    3. Default: Jina (works without an API key, rate-limited)
    """
    provider = os.environ.get("WEB_SEARCH_PROVIDER", "").lower()

    if provider == "tavily" or (not provider and os.environ.get("TAVILY_API_KEY")):
        return TavilySearch(timeout=timeout)
    if provider == "brave" or (not provider and os.environ.get("BRAVE_API_KEY")):
        return BraveSearch(timeout=timeout)
    return JinaSearch(timeout=timeout)


def format_results(results: list[SearchResult], *, max_chars: int = 15_000) -> str:
    """Format a list of SearchResults as Markdown for LLM consumption."""
    parts: list[str] = []
    for i, r in enumerate(results, 1):
        header = f"## {i}. [{r.title}]({r.url})" if r.url else f"## {i}. {r.title}"
        parts.append(f"{header}\n\n{r.snippet}")
    text = "\n\n---\n\n".join(parts)
    if len(text) > max_chars:
        text = text[:max_chars] + f"\n\n[Truncated — {len(text)} chars total]"
    return text
