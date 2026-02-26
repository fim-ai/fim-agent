"""Smart truncation utilities for conversation history compaction.

Provides token estimation and message truncation so that long conversation
histories fit within a configurable token budget without requiring a separate
LLM call.
"""

from __future__ import annotations

from fim_agent.core.model.types import ChatMessage


class CompactUtils:
    """Stateless helpers for estimating and truncating conversation history."""

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate token count for mixed-language text.

        Uses different heuristics depending on character type:
        - ASCII characters (English, code, punctuation): ~4 chars per token
        - CJK / non-ASCII characters (Chinese, Japanese, Korean, etc.):
          ~1.5 chars per token (each CJK char is typically 1-2 tokens)

        Args:
            text: The string to estimate.

        Returns:
            Approximate number of tokens.
        """
        if not text:
            return 0

        ascii_chars = 0
        non_ascii_chars = 0
        for ch in text:
            if ord(ch) < 128:
                ascii_chars += 1
            else:
                non_ascii_chars += 1

        # ASCII: ~4 chars per token; CJK/non-ASCII: ~1.5 chars per token
        tokens = ascii_chars / 4.0 + non_ascii_chars / 1.5
        return max(1, int(tokens))

    @classmethod
    def estimate_messages_tokens(cls, messages: list[ChatMessage]) -> int:
        """Estimate total token count across multiple messages.

        Each message adds ~4 tokens of overhead (role, delimiters).

        Args:
            messages: The list of messages.

        Returns:
            Approximate total token count.
        """
        total = 0
        for msg in messages:
            total += 4  # per-message overhead
            total += cls.estimate_tokens(msg.content or "")
        return total

    @classmethod
    def smart_truncate(
        cls,
        messages: list[ChatMessage],
        max_tokens: int = 8000,
    ) -> list[ChatMessage]:
        """Truncate messages to fit within a token budget.

        Keeps the most recent messages by scanning backwards from the end.
        Ensures the returned list does not start with an ``assistant`` message
        (which would confuse the LLM).

        Args:
            messages: Full conversation history (oldest first).
            max_tokens: Maximum token budget.

        Returns:
            A suffix of *messages* that fits within *max_tokens*.
        """
        if not messages:
            return []

        if cls.estimate_messages_tokens(messages) <= max_tokens:
            return list(messages)

        # Walk backwards, accumulating messages until we exceed the budget.
        result: list[ChatMessage] = []
        budget = max_tokens
        for msg in reversed(messages):
            cost = 4 + cls.estimate_tokens(msg.content or "")
            if budget - cost < 0:
                break
            result.append(msg)
            budget -= cost

        result.reverse()

        # Drop leading assistant messages — the history must start with a
        # user message so the LLM doesn't see a context-free assistant turn.
        while result and result[0].role == "assistant":
            result.pop(0)

        return result
