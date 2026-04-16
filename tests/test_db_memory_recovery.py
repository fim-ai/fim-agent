"""Tests for DbMemory conversation trajectory recovery.

Covers the ``_repair_dangling_tool_calls`` helper which heals message
lists whose ``assistant`` turns contain ``tool_calls`` that never
received matching ``role="tool"`` responses.  Such gaps happen when a
turn is interrupted mid-flight (Stop button, SSE disconnect, backend
crash) and would otherwise cause Anthropic / OpenAI compatible endpoints
to reject the message list with a 400 error on the next turn.

All tests operate on pure in-memory ``ChatMessage`` data — no DB, no
network — per the project's test rules.
"""

from __future__ import annotations

import logging

import pytest

from fim_one.core.memory.db import (
    _INTERRUPTED_TOOL_RESULT,
    _repair_dangling_tool_calls,
)
from fim_one.core.model.types import ChatMessage, ToolCallRequest


def _tc(tc_id: str, name: str = "noop") -> ToolCallRequest:
    """Build a minimal ``ToolCallRequest`` for tests."""
    return ToolCallRequest(id=tc_id, name=name, arguments={})


class TestRepairDanglingToolCalls:
    """Exercise the private repair helper end-to-end."""

    def test_no_dangling_tool_use_passthrough(self) -> None:
        """Well-formed message lists must pass through unchanged."""
        messages: list[ChatMessage] = [
            ChatMessage(role="user", content="what is 2+2?"),
            ChatMessage(
                role="assistant",
                content="",
                tool_calls=[_tc("call_1", "calculator")],
            ),
            ChatMessage(role="tool", content="4", tool_call_id="call_1"),
            ChatMessage(role="assistant", content="The answer is 4."),
        ]

        repaired = _repair_dangling_tool_calls(messages, "conv-abc")

        assert len(repaired) == len(messages)
        # Order and identity preserved — no new objects inserted.
        for before, after in zip(messages, repaired):
            assert before is after

    def test_single_dangling_tool_use_repaired(self) -> None:
        """A lone dangling tool_call gets one synthetic tool_result."""
        messages: list[ChatMessage] = [
            ChatMessage(role="user", content="search the docs"),
            ChatMessage(
                role="assistant",
                content="",
                tool_calls=[_tc("call_1", "web_search")],
            ),
            # User fired again before the tool result landed.
            ChatMessage(role="user", content="never mind, thanks"),
        ]

        repaired = _repair_dangling_tool_calls(messages, "conv-xyz")

        assert len(repaired) == 4
        assert repaired[0].role == "user"
        assert repaired[1].role == "assistant"
        # Synthetic tool message inserted immediately after the assistant.
        assert repaired[2].role == "tool"
        assert repaired[2].tool_call_id == "call_1"
        assert repaired[2].content == _INTERRUPTED_TOOL_RESULT
        # Trailing user message preserved and not re-ordered.
        assert repaired[3].role == "user"
        assert repaired[3].content == "never mind, thanks"

    def test_multiple_dangling_tool_uses_all_repaired(self) -> None:
        """Three tool_calls, one satisfied, two need repair."""
        messages: list[ChatMessage] = [
            ChatMessage(role="user", content="do three things"),
            ChatMessage(
                role="assistant",
                content="",
                tool_calls=[
                    _tc("call_a", "read_file"),
                    _tc("call_b", "list_dir"),
                    _tc("call_c", "grep"),
                ],
            ),
            # Only call_b has a real result.
            ChatMessage(
                role="tool",
                content="dir listing",
                tool_call_id="call_b",
            ),
        ]

        repaired = _repair_dangling_tool_calls(messages, "conv-multi")

        # Original 3 + 2 synthetic tool results = 5.
        assert len(repaired) == 5
        # Assistant intact.
        assert repaired[1].role == "assistant"
        assert repaired[1].tool_calls is not None
        assert len(repaired[1].tool_calls) == 3
        # Existing tool_result preserved in place.
        assert repaired[2].role == "tool"
        assert repaired[2].tool_call_id == "call_b"
        assert repaired[2].content == "dir listing"
        # Synthetic results for call_a and call_c appended after.
        synth_ids = {m.tool_call_id for m in repaired[3:]}
        assert synth_ids == {"call_a", "call_c"}
        for m in repaired[3:]:
            assert m.role == "tool"
            assert m.content == _INTERRUPTED_TOOL_RESULT

    def test_dangling_at_end_of_conversation(self) -> None:
        """Last message is a tool-calling assistant with no follow-up."""
        messages: list[ChatMessage] = [
            ChatMessage(role="user", content="start the job"),
            ChatMessage(
                role="assistant",
                content="",
                tool_calls=[
                    _tc("call_end_1", "run_job"),
                    _tc("call_end_2", "notify"),
                ],
            ),
        ]

        repaired = _repair_dangling_tool_calls(messages, "conv-tail")

        assert len(repaired) == 4
        assert repaired[0].role == "user"
        assert repaired[1].role == "assistant"
        assert repaired[2].role == "tool"
        assert repaired[2].tool_call_id == "call_end_1"
        assert repaired[2].content == _INTERRUPTED_TOOL_RESULT
        assert repaired[3].role == "tool"
        assert repaired[3].tool_call_id == "call_end_2"
        assert repaired[3].content == _INTERRUPTED_TOOL_RESULT

    def test_partial_repair_preserves_existing_tool_results(self) -> None:
        """Existing tool_results must not be duplicated or mutated."""
        messages: list[ChatMessage] = [
            ChatMessage(role="user", content="lookup"),
            ChatMessage(
                role="assistant",
                content="",
                tool_calls=[
                    _tc("id_1", "lookup"),
                    _tc("id_2", "lookup"),
                ],
            ),
            ChatMessage(
                role="tool",
                content="real result for 1",
                tool_call_id="id_1",
            ),
            ChatMessage(
                role="tool",
                content="real result for 2",
                tool_call_id="id_2",
            ),
            ChatMessage(role="assistant", content="all done"),
        ]

        repaired = _repair_dangling_tool_calls(messages, "conv-full")

        # No synthetic messages — both calls satisfied.
        assert len(repaired) == len(messages)
        # Verify the real tool_results are untouched (same objects).
        assert repaired[2] is messages[2]
        assert repaired[3] is messages[3]
        # And that no duplicate synthetic results were added anywhere.
        synthetic_hits = [
            m for m in repaired
            if m.role == "tool" and m.content == _INTERRUPTED_TOOL_RESULT
        ]
        assert synthetic_hits == []

    def test_repair_logs_warning(
        self, caplog: pytest.LogCaptureFixture,
    ) -> None:
        """A repair must emit a WARNING log carrying the conversation id."""
        messages: list[ChatMessage] = [
            ChatMessage(role="user", content="hi"),
            ChatMessage(
                role="assistant",
                content="",
                tool_calls=[_tc("call_log", "demo")],
            ),
        ]

        with caplog.at_level(logging.WARNING, logger="fim_one.core.memory.db"):
            _repair_dangling_tool_calls(messages, "conv-log-42")

        warning_records = [
            r for r in caplog.records
            if r.levelno == logging.WARNING and "repaired" in r.getMessage()
        ]
        assert len(warning_records) == 1
        rendered = warning_records[0].getMessage()
        assert "conv-log-42" in rendered
        assert "1" in rendered  # number of repairs

    def test_no_warning_when_clean(
        self, caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Clean trajectories must not log any WARNING from the repair."""
        messages: list[ChatMessage] = [
            ChatMessage(role="user", content="hi"),
            ChatMessage(role="assistant", content="hello"),
        ]

        with caplog.at_level(logging.WARNING, logger="fim_one.core.memory.db"):
            _repair_dangling_tool_calls(messages, "conv-clean")

        repair_warnings = [
            r for r in caplog.records
            if r.levelno == logging.WARNING and "repaired" in r.getMessage()
        ]
        assert repair_warnings == []

    def test_empty_message_list_is_noop(self) -> None:
        """Empty input returns an empty list without error."""
        assert _repair_dangling_tool_calls([], "conv-empty") == []

    def test_repair_does_not_mutate_input_list(self) -> None:
        """The repair must return a new list and never mutate the input."""
        original: list[ChatMessage] = [
            ChatMessage(role="user", content="go"),
            ChatMessage(
                role="assistant",
                content="",
                tool_calls=[_tc("call_m", "tool")],
            ),
        ]
        snapshot_len = len(original)
        snapshot_ids = [id(m) for m in original]

        repaired = _repair_dangling_tool_calls(original, "conv-immut")

        assert len(original) == snapshot_len
        assert [id(m) for m in original] == snapshot_ids
        assert repaired is not original
        assert len(repaired) == snapshot_len + 1
