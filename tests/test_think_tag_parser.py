"""Tests for <think>...</think> tag stripping in OpenAI-compatible LLM.

Covers both the streaming _ThinkTagStreamParser and the non-streaming
_parse_choice_message extraction.
"""

from __future__ import annotations

import re
from unittest.mock import MagicMock

import pytest

from fim_one.core.model.openai_compatible import (
    OpenAICompatibleLLM,
    _THINK_RE,
    _ThinkTagStreamParser,
)


# -----------------------------------------------------------------------
# _THINK_RE (compiled regex) tests
# -----------------------------------------------------------------------


class TestThinkRegex:
    """Tests for the module-level _THINK_RE regex."""

    def test_single_block(self) -> None:
        text = "<think>some reasoning</think>actual content"
        matches = _THINK_RE.findall(text)
        assert matches == ["some reasoning"]
        assert _THINK_RE.sub("", text) == "actual content"

    def test_multiple_blocks(self) -> None:
        text = "<think>first</think>middle<think>second</think>end"
        matches = _THINK_RE.findall(text)
        assert matches == ["first", "second"]
        assert _THINK_RE.sub("", text) == "middleend"

    def test_multiline(self) -> None:
        text = "<think>\nline1\nline2\n</think>\nresult"
        matches = _THINK_RE.findall(text)
        assert matches == ["\nline1\nline2\n"]
        assert _THINK_RE.sub("", text).strip() == "result"

    def test_no_think_tags(self) -> None:
        text = "no thinking here"
        assert _THINK_RE.findall(text) == []
        assert _THINK_RE.sub("", text) == text


# -----------------------------------------------------------------------
# _ThinkTagStreamParser tests
# -----------------------------------------------------------------------


class TestThinkTagStreamParser:
    """Tests for the streaming <think> tag parser state machine."""

    def test_no_think_tag_passthrough(self) -> None:
        """Content without <think> passes through immediately."""
        parser = _ThinkTagStreamParser()
        content, reasoning = parser.feed("Hello world")
        assert content == "Hello world"
        assert reasoning == ""

    def test_simple_think_block(self) -> None:
        """A complete <think>...</think> in one chunk."""
        parser = _ThinkTagStreamParser()
        content, reasoning = parser.feed("<think>my reasoning</think>answer")
        assert reasoning == "my reasoning"
        assert content == "answer"

    def test_think_tag_split_across_chunks(self) -> None:
        """<think> tag arrives in pieces."""
        parser = _ThinkTagStreamParser()
        # First chunk: partial tag
        c, r = parser.feed("<thi")
        assert c == ""
        assert r == ""
        # Second chunk: rest of opening tag
        c, r = parser.feed("nk>reasoning stuff")
        # Should now be in THINKING state
        # May buffer some for safety against split </think>
        assert c == ""
        # Third chunk: closing tag
        all_reasoning = r
        c, r = parser.feed("</think>the answer")
        all_reasoning += r
        assert "reasoning stuff" in all_reasoning
        assert c == "the answer"

    def test_close_tag_split_across_chunks(self) -> None:
        """</think> arrives split across two chunks."""
        parser = _ThinkTagStreamParser()
        parser.feed("<think>")
        c, r = parser.feed("step 1, step 2")
        reasoning_parts = [r]
        # Feed partial close tag
        c, r = parser.feed("</thi")
        reasoning_parts.append(r)
        # Complete the close tag
        c, r = parser.feed("nk>final answer")
        reasoning_parts.append(r)
        all_reasoning = "".join(reasoning_parts)
        assert "step 1, step 2" in all_reasoning
        assert c == "final answer"

    def test_leading_whitespace_before_think(self) -> None:
        """Whitespace before <think> is acceptable."""
        parser = _ThinkTagStreamParser()
        c, r = parser.feed("  \n<think>thoughts</think>content")
        assert r == "thoughts"
        assert c == "content"

    def test_detect_non_think_prefix(self) -> None:
        """Content that doesn't start with <think> goes to CONTENT state."""
        parser = _ThinkTagStreamParser()
        c, r = parser.feed("Just normal text")
        assert c == "Just normal text"
        assert r == ""

    def test_detect_partial_non_matching(self) -> None:
        """Partial text that looks like it could be <think> but isn't."""
        parser = _ThinkTagStreamParser()
        # "<t" could be the start of <think>
        c, r = parser.feed("<t")
        assert c == ""  # still buffering
        assert r == ""
        # Now it becomes clear it's not <think>
        c, r = parser.feed("able>data</table>")
        assert "<t" in c  # buffered prefix comes out
        assert r == ""

    def test_flush_during_thinking(self) -> None:
        """Flush while still inside <think> block emits as reasoning."""
        parser = _ThinkTagStreamParser()
        # feed() may emit the "safe" portion immediately (everything except
        # the last len("</think>")-1 chars that could be a split close tag),
        # so we collect reasoning from both feed() and flush().
        _, r_feed = parser.feed("<think>partial reasoning")
        c, r_flush = parser.flush()
        all_reasoning = r_feed + r_flush
        assert c == ""
        assert "partial reasoning" in all_reasoning

    def test_flush_during_content(self) -> None:
        """Flush in CONTENT state emits as content."""
        parser = _ThinkTagStreamParser()
        parser.feed("<think>r</think>")
        # Now in CONTENT state
        parser.feed("some trailing")
        c, r = parser.flush()
        # flush should be empty since content was already emitted
        # (buffer should be empty after feed in CONTENT state)
        assert r == ""

    def test_flush_empty(self) -> None:
        """Flush with empty buffer returns empty strings."""
        parser = _ThinkTagStreamParser()
        c, r = parser.flush()
        assert c == ""
        assert r == ""

    def test_content_after_think_block_strips_leading_newlines(self) -> None:
        """Content after </think> has leading newlines stripped."""
        parser = _ThinkTagStreamParser()
        c, r = parser.feed("<think>reason</think>\n\nHello")
        assert r == "reason"
        assert c == "Hello"

    def test_incremental_reasoning_emission(self) -> None:
        """Large reasoning blocks are emitted incrementally (not all buffered)."""
        parser = _ThinkTagStreamParser()
        parser.feed("<think>")
        all_reasoning = ""
        # Feed enough data that the parser should emit some reasoning
        for i in range(20):
            c, r = parser.feed(f"step {i} " * 10)
            all_reasoning += r
            assert c == ""  # Still in THINKING state, no content yet
        # Eventually close
        c, r = parser.feed("</think>done")
        all_reasoning += r
        assert "step 0" in all_reasoning
        assert "step 19" in all_reasoning
        assert c == "done"


# -----------------------------------------------------------------------
# _parse_choice_message tests (non-streaming think-tag stripping)
# -----------------------------------------------------------------------


class TestParseChoiceMessageThinkStripping:
    """Tests for think-tag stripping in _parse_choice_message."""

    @staticmethod
    def _make_choice(
        content: str | None,
        reasoning_content: str | None = None,
        tool_calls: list[object] | None = None,
        role: str = "assistant",
    ) -> MagicMock:
        """Create a mock response choice object."""
        msg = MagicMock()
        msg.content = content
        msg.role = role
        msg.tool_calls = tool_calls
        msg.reasoning_content = reasoning_content
        msg.reasoning = None
        return MagicMock(message=msg)

    def test_no_think_tags_unchanged(self) -> None:
        """Content without <think> tags passes through unchanged."""
        choice = self._make_choice("Hello world")
        result = OpenAICompatibleLLM._parse_choice_message(choice)
        assert result.content == "Hello world"
        assert result.reasoning_content is None

    def test_think_tags_extracted(self) -> None:
        """<think> tags are stripped and moved to reasoning_content."""
        choice = self._make_choice(
            "<think>my reasoning here</think>The answer is 42."
        )
        result = OpenAICompatibleLLM._parse_choice_message(choice)
        assert result.content == "The answer is 42."
        assert result.reasoning_content == "my reasoning here"

    def test_think_tags_merged_with_api_reasoning(self) -> None:
        """<think> content merges with existing API-level reasoning_content."""
        choice = self._make_choice(
            "<think>extra reasoning</think>Answer.",
            reasoning_content="API reasoning",
        )
        result = OpenAICompatibleLLM._parse_choice_message(choice)
        assert result.content == "Answer."
        assert result.reasoning_content is not None
        assert "API reasoning" in result.reasoning_content
        assert "extra reasoning" in result.reasoning_content

    def test_multiple_think_blocks(self) -> None:
        """Multiple <think> blocks are all extracted."""
        choice = self._make_choice(
            "<think>part 1</think>middle<think>part 2</think>end"
        )
        result = OpenAICompatibleLLM._parse_choice_message(choice)
        assert result.reasoning_content is not None
        assert "part 1" in result.reasoning_content
        assert "part 2" in result.reasoning_content
        assert result.content == "middleend"

    def test_only_think_block_content_becomes_none(self) -> None:
        """If content is only a <think> block, content becomes None."""
        choice = self._make_choice("<think>all reasoning</think>")
        result = OpenAICompatibleLLM._parse_choice_message(choice)
        assert result.content is None
        assert result.reasoning_content == "all reasoning"

    def test_none_content_unchanged(self) -> None:
        """None content is not processed."""
        choice = self._make_choice(None)
        result = OpenAICompatibleLLM._parse_choice_message(choice)
        assert result.content is None
        assert result.reasoning_content is None

    def test_multiline_think_content(self) -> None:
        """Multiline content inside <think> is extracted correctly."""
        choice = self._make_choice(
            "<think>\nStep 1: analyze\nStep 2: synthesize\n</think>Result."
        )
        result = OpenAICompatibleLLM._parse_choice_message(choice)
        assert result.content == "Result."
        assert result.reasoning_content is not None
        assert "Step 1: analyze" in result.reasoning_content
        assert "Step 2: synthesize" in result.reasoning_content
