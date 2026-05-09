"""Error chain inspection helpers for retry / fallback decisions.

These helpers walk the ``__cause__`` and ``__context__`` chain of an
exception to find the actual underlying transport error.  Useful when an
LLM client (litellm, OpenAI SDK, anthropic, etc.) wraps the real network
error in a generic provider exception -- the top-level type alone is not
enough to decide whether to retry.

Functions:
    iter_error_chain -- yield exception + its cause chain
    get_status_code -- first non-None HTTP status code in the chain
    get_error_code -- first non-None provider error code
    is_network_like_error -- any timeout/connection/network error in chain

Adapted from OpenAI Agents SDK Python (src/agents/run_internal/model_retry.py),
MIT License, Copyright (c) 2025 OpenAI.  Renamed to drop the underscore
prefix since these are now public to ``fim_one.core.model``.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping


def iter_error_chain(error: BaseException) -> Iterator[BaseException]:
    """Yield ``error`` and each ancestor in its ``__cause__`` / ``__context__`` chain.

    Iteration stops if the chain cycles back to an already-yielded
    exception, guaranteeing termination on self-referencing chains.

    Args:
        error: The starting exception.

    Yields:
        The exception and each subsequent cause/context in the chain.
    """
    current: BaseException | None = error
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        yield current
        next_error = current.__cause__ or current.__context__
        current = next_error if isinstance(next_error, BaseException) else None


def get_status_code(error: BaseException) -> int | None:
    """Return the first HTTP status code found in the exception chain.

    Walks the cause-chain (``__cause__`` then ``__context__``) and
    returns the first integer found on a ``status_code`` or ``status``
    attribute.  Returns ``None`` if no status code is present anywhere
    in the chain.

    Args:
        error: The exception to inspect.

    Returns:
        The first HTTP status code, or ``None``.
    """
    for candidate in iter_error_chain(error):
        for attr_name in ("status_code", "status"):
            value = getattr(candidate, attr_name, None)
            if isinstance(value, int):
                return value
    return None


def get_error_code(error: BaseException) -> str | None:
    """Return the first provider error code found in the exception chain.

    Looks for a ``code`` attribute (string) or, failing that, a
    ``body`` attribute that is a mapping containing either
    ``error.code`` or ``code``.  Mirrors how OpenAI / litellm-style
    SDKs surface provider error codes.

    Args:
        error: The exception to inspect.

    Returns:
        The first error code string, or ``None``.
    """
    for candidate in iter_error_chain(error):
        error_code = getattr(candidate, "code", None)
        if isinstance(error_code, str):
            return error_code

        body = getattr(candidate, "body", None)
        if isinstance(body, Mapping):
            nested_error = body.get("error")
            if isinstance(nested_error, Mapping):
                nested_code = nested_error.get("code")
                if isinstance(nested_code, str):
                    return nested_code
            body_code = body.get("code")
            if isinstance(body_code, str):
                return body_code
    return None


def is_network_like_error(error: BaseException) -> bool:
    """Return True if the exception (or any of its causes) is a transport-layer error.

    A "network-like" error is any of:
      - :class:`TimeoutError` (stdlib)
      - :class:`ConnectionError` (stdlib)
      - An ``httpx`` connection / read / write / timeout error, detected
        structurally (by class module + name) so we don't take a hard
        runtime dep on httpx.
      - A ``websockets`` ``ConnectionClosed*`` error (also detected
        structurally).
      - Any exception whose string representation contains common
        transport-failure phrases ("connection error", "network error",
        "socket hang up").

    Args:
        error: The exception to inspect.

    Returns:
        ``True`` if any link in the chain is network-like.
    """
    network_stdlib_types: tuple[type[BaseException], ...] = (TimeoutError, ConnectionError)

    for candidate in iter_error_chain(error):
        if isinstance(candidate, network_stdlib_types):
            return True

        cls = candidate.__class__
        module = cls.__module__ or ""
        name = cls.__name__

        # httpx transport errors -- detect structurally to avoid a hard import.
        if module.startswith("httpx"):
            if name in {
                "ConnectError",
                "ReadError",
                "WriteError",
                "RemoteProtocolError",
                "TimeoutException",
                "ConnectTimeout",
                "ReadTimeout",
                "WriteTimeout",
                "PoolTimeout",
            }:
                return True

        # OpenAI SDK transport errors (also detected structurally).
        if module.startswith("openai"):
            if name in {"APIConnectionError", "APITimeoutError"}:
                return True

        # websockets connection-closed family.
        if module.startswith("websockets") and name.startswith("ConnectionClosed"):
            return True

    message = str(error).lower()
    return (
        "connection error" in message
        or "network error" in message
        or "socket hang up" in message
    )
