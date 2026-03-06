"""Built-in tool for fetching web page content.

Delegates to the configured BaseWebFetch backend (Jina or plain httpx).
Backend selection is controlled by the WEB_FETCH_PROVIDER environment variable.
"""

from __future__ import annotations

import ipaddress
import socket
import urllib.parse
from typing import Any

import httpx

from fim_agent.core.web.fetch import get_web_fetcher

from ..base import BaseTool

_DEFAULT_TIMEOUT: int = 30
_MAX_CHARS: int = 20_000


def _validate_url(url: str) -> None:
    """Validate a URL against SSRF risks.

    Raises ValueError if:
    - The scheme is not http or https.
    - The resolved IP falls in a private, loopback, or link-local range.

    DNS resolution failures are treated as non-blocking: if the hostname
    cannot be resolved here, the request is allowed to proceed and will
    fail naturally at the HTTP layer.
    """
    parsed = urllib.parse.urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise ValueError(
            f"Blocked URL scheme '{parsed.scheme}': only http and https are allowed."
        )

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL contains no hostname.")

    try:
        addr_infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        # DNS resolution failed — not an SSRF issue; let the fetcher handle it.
        return

    for _family, _type, _proto, _canonname, sockaddr in addr_infos:
        raw_ip = sockaddr[0]
        try:
            addr = ipaddress.ip_address(raw_ip)
        except ValueError:
            continue

        if addr.is_loopback or addr.is_private or addr.is_link_local:
            raise ValueError(
                f"Blocked request to internal/reserved address '{raw_ip}' "
                f"resolved from hostname '{hostname}'."
            )


class WebFetchTool(BaseTool):
    """Fetch a URL and return its content as clean Markdown or plain text.

    Supports Jina Reader (clean Markdown output) and plain httpx (text extraction).
    Backend is selected via the WEB_FETCH_PROVIDER environment variable.
    """

    def __init__(self, *, timeout: int = _DEFAULT_TIMEOUT) -> None:
        self._timeout = timeout

    @property
    def name(self) -> str:
        return "web_fetch"

    @property
    def category(self) -> str:
        return "web"

    @property
    def description(self) -> str:
        return (
            "Fetch the content of a web page and return it as Markdown text. "
            "Provide a full URL (e.g. https://example.com). "
            "Useful for reading articles, documentation, API responses, etc."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to fetch (must start with http:// or https://).",
                },
            },
            "required": ["url"],
        }

    async def run(self, **kwargs: Any) -> str:
        url: str = kwargs.get("url", "").strip()
        if not url:
            return "[Error] No URL provided."

        try:
            _validate_url(url)
        except ValueError as exc:
            return f"[Blocked] {exc}"

        fetcher = get_web_fetcher(timeout=self._timeout)
        try:
            content = await fetcher.fetch(url)
        except httpx.TimeoutException:
            return f"[Timeout] Request exceeded {self._timeout} seconds."
        except httpx.HTTPStatusError as exc:
            return f"[HTTP {exc.response.status_code}] {exc.response.text[:500]}"
        except httpx.RequestError as exc:
            return f"[Error] {exc}"

        if len(content) > _MAX_CHARS:
            content = content[:_MAX_CHARS] + f"\n\n[Truncated — {len(content)} chars total]"
        return content
