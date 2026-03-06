"""Shared response-truncation utilities for tool adapters.

Both ConnectorToolAdapter and MCPToolAdapter call :func:`truncate_tool_output`
so that oversized responses are handled consistently across all tool types.

Truncation strategy
-------------------
- **JSON array** (too many items): keep first *max_items* complete entries and
  append a hint showing total count and available keys so the agent knows what
  was omitted and can refine its query parameters.
- **JSON array** (few items, but raw text too large): character-based truncation
  with a key-list hint.
- **JSON object**: character-based truncation with top-level key list.
- **Non-JSON**: plain character truncation.
"""

from __future__ import annotations

import json


def truncate_tool_output(
    content: str,
    max_chars: int = 50_000,
    max_items: int = 10,
) -> str:
    """Truncate *content* with JSON-aware structure hints.

    Parameters
    ----------
    content:
        Raw string output from a tool call.
    max_chars:
        Maximum number of characters to return for non-array or large-item
        responses.
    max_items:
        Maximum number of array items to include when the response is a JSON
        array.

    Returns
    -------
    str
        Possibly-truncated content with an appended hint describing what was
        omitted and the data structure, so the agent can act on the hint.
    """
    # Fast path: short enough to return as-is (still check array item count).
    if len(content) <= max_chars:
        try:
            data = json.loads(content)
        except (json.JSONDecodeError, ValueError):
            return content
        if isinstance(data, list) and len(data) > max_items:
            return _truncate_array(data, max_items)
        return content

    # Content exceeds max_chars — parse to add a structure hint.
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, ValueError):
        return content[:max_chars] + f"\n\n[Truncated: {len(content)} chars total]"

    if isinstance(data, list):
        if len(data) > max_items:
            return _truncate_array(data, max_items)
        # Small array but items are large — char-truncate with key hint.
        keys = _item_keys(data[0]) if data else []
        hint = f" Item keys: {keys}." if keys else ""
        return content[:max_chars] + f"\n\n[Truncated: {len(content)} chars total.{hint}]"

    if isinstance(data, dict):
        keys = list(data.keys())
        return (
            content[:max_chars]
            + f"\n\n[Truncated: {len(content)} chars total. Top-level keys: {keys}]"
        )

    return content[:max_chars] + f"\n\n[Truncated: {len(content)} chars total]"


def _truncate_array(data: list, max_items: int) -> str:
    sample = data[0] if data else {}
    keys = _item_keys(sample)
    truncated = json.dumps(data[:max_items], ensure_ascii=False, indent=2)
    key_hint = f"Each item has keys: {keys}. " if keys else ""
    return (
        truncated
        + f"\n\n[Showing {max_items}/{len(data)} items. "
        + key_hint
        + "Use more specific query parameters to narrow results.]"
    )


def _item_keys(item: object) -> list[str]:
    return list(item.keys()) if isinstance(item, dict) else []
