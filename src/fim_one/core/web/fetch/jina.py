"""Jina Reader web fetch backend (https://r.jina.ai)."""

from __future__ import annotations

import os

import httpx

from .base import BaseWebFetch

_JINA_READER_URL = "https://r.jina.ai/"
_DEFAULT_TIMEOUT = 30


class JinaFetch(BaseWebFetch):
    """Fetches pages via Jina Reader, returning clean Markdown."""

    def __init__(self, *, api_key: str = "", timeout: int = _DEFAULT_TIMEOUT) -> None:
        self._api_key = api_key or os.environ.get("JINA_API_KEY", "")
        self._timeout = timeout

    async def fetch(self, url: str) -> str:
        headers: dict[str, str] = {"Accept": "text/markdown"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(f"{_JINA_READER_URL}{url}", headers=headers)
            resp.raise_for_status()
            return resp.text
