"""Web abstractions — search and fetch provider protocols."""

from .fetch import BaseWebFetch, HttpxFetch, JinaFetch, get_web_fetcher
from .search import (
    BaseWebSearch,
    BraveSearch,
    JinaSearch,
    SearchResult,
    TavilySearch,
    format_results,
    get_web_searcher,
)

__all__ = [
    # Search
    "BaseWebSearch",
    "SearchResult",
    "JinaSearch",
    "TavilySearch",
    "BraveSearch",
    "get_web_searcher",
    "format_results",
    # Fetch
    "BaseWebFetch",
    "JinaFetch",
    "HttpxFetch",
    "get_web_fetcher",
]
