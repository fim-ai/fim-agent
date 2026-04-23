"""Tests for ``normalize_alternating_messages``.

The normalizer is inserted at the ``OpenAICompatibleLLM`` entry point to
collapse consecutive same-role message runs before the list reaches any
provider.  The primary driver is Claude's strict user/assistant
alternation requirement — an orphan user message left behind by a
stopped-then-retried turn would otherwise 400 the request.
"""

from __future__ import annotations

from fim_one.core.model.normalize import normalize_alternating_messages
from fim_one.core.model.types import ChatMessage, ToolCallRequest


class TestNormalizeAlternatingMessages:
    def test_empty_input_returns_empty(self) -> None:
        assert normalize_alternating_messages([]) == []

    def test_single_message_passthrough(self) -> None:
        msgs = [ChatMessage(role="user", content="hello")]
        out = normalize_alternating_messages(msgs)
        assert len(out) == 1
        assert out[0].role == "user"
        assert out[0].content == "hello"

    def test_already_alternating_passthrough(self) -> None:
        msgs = [
            ChatMessage(role="system", content="s"),
            ChatMessage(role="user", content="u1"),
            ChatMessage(role="assistant", content="a1"),
            ChatMessage(role="user", content="u2"),
        ]
        out = normalize_alternating_messages(msgs)
        assert len(out) == 4
        assert [m.content for m in out] == ["s", "u1", "a1", "u2"]

    def test_merges_consecutive_user_messages(self) -> None:
        # The headline scenario: three orphan user messages from repeated
        # stop-and-retry collapse into a single user turn.
        msgs = [
            ChatMessage(role="user", content="Simulate Monty Hall"),
            ChatMessage(role="user", content="Simulate Monty Hall"),
            ChatMessage(role="user", content="hi"),
        ]
        out = normalize_alternating_messages(msgs)
        assert len(out) == 1
        assert out[0].role == "user"
        assert out[0].content == (
            "Simulate Monty Hall\n\nSimulate Monty Hall\n\nhi"
        )

    def test_merges_across_runs_preserving_alternation(self) -> None:
        msgs = [
            ChatMessage(role="user", content="u1"),
            ChatMessage(role="user", content="u2"),
            ChatMessage(role="assistant", content="a1"),
            ChatMessage(role="user", content="u3"),
            ChatMessage(role="user", content="u4"),
        ]
        out = normalize_alternating_messages(msgs)
        assert [m.role for m in out] == ["user", "assistant", "user"]
        assert out[0].content == "u1\n\nu2"
        assert out[1].content == "a1"
        assert out[2].content == "u3\n\nu4"

    def test_never_merges_tool_messages(self) -> None:
        # Tool replies must stay 1-to-1 with their call ids.
        msgs = [
            ChatMessage(
                role="tool", content="result-1", tool_call_id="call_a"
            ),
            ChatMessage(
                role="tool", content="result-2", tool_call_id="call_b"
            ),
        ]
        out = normalize_alternating_messages(msgs)
        assert len(out) == 2
        assert out[0].tool_call_id == "call_a"
        assert out[1].tool_call_id == "call_b"

    def test_never_merges_assistant_with_tool_calls(self) -> None:
        # Each assistant tool-call step is a discrete agent action.
        tc = ToolCallRequest(id="c1", name="calc", arguments={"x": 1})
        msgs = [
            ChatMessage(role="assistant", content=None, tool_calls=[tc]),
            ChatMessage(role="assistant", content="text"),
        ]
        out = normalize_alternating_messages(msgs)
        assert len(out) == 2
        assert out[0].tool_calls is not None
        assert out[1].content == "text"

    def test_merges_multimodal_user_messages(self) -> None:
        mm_a = ChatMessage(
            role="user",
            content=[
                {"type": "text", "text": "look at this"},
                {
                    "type": "image_url",
                    "image_url": {"url": "data:image/png;base64,AAAA"},
                },
            ],
        )
        mm_b = ChatMessage(role="user", content="and summarize")
        out = normalize_alternating_messages([mm_a, mm_b])
        assert len(out) == 1
        content = out[0].content
        assert isinstance(content, list)
        # Original two parts + the text-converted second message = 3 parts
        assert len(content) == 3
        assert content[-1] == {"type": "text", "text": "and summarize"}

    def test_tail_biased_cache_control_and_signature(self) -> None:
        # Prompt-cache breakpoint + extended-thinking signature belong to
        # the LAST message of the merged run (that is what the provider
        # actually consumes).
        msgs = [
            ChatMessage(role="user", content="early", cache_control=None),
            ChatMessage(
                role="user",
                content="late",
                cache_control={"type": "ephemeral"},
                signature="sig-xyz",
            ),
        ]
        out = normalize_alternating_messages(msgs)
        assert len(out) == 1
        assert out[0].cache_control == {"type": "ephemeral"}
        assert out[0].signature == "sig-xyz"

    def test_pinned_flag_propagates_if_any_input_pinned(self) -> None:
        msgs = [
            ChatMessage(role="user", content="a", pinned=False),
            ChatMessage(role="user", content="b", pinned=True),
        ]
        out = normalize_alternating_messages(msgs)
        assert len(out) == 1
        assert out[0].pinned is True

    def test_empty_content_does_not_introduce_extra_separators(self) -> None:
        msgs = [
            ChatMessage(role="user", content=""),
            ChatMessage(role="user", content="real text"),
        ]
        out = normalize_alternating_messages(msgs)
        assert len(out) == 1
        assert out[0].content == "real text"

    def test_does_not_mutate_input(self) -> None:
        msgs = [
            ChatMessage(role="user", content="a"),
            ChatMessage(role="user", content="b"),
        ]
        snapshot = [(m.role, m.content) for m in msgs]
        normalize_alternating_messages(msgs)
        assert [(m.role, m.content) for m in msgs] == snapshot

    def test_merges_consecutive_system_messages(self) -> None:
        # Double-system-message pattern found in react.py synthesis phase
        # collapses to a single system block, which Anthropic requires.
        msgs = [
            ChatMessage(role="system", content="rule 1"),
            ChatMessage(role="system", content="rule 2"),
            ChatMessage(role="user", content="do it"),
        ]
        out = normalize_alternating_messages(msgs)
        assert len(out) == 2
        assert out[0].role == "system"
        assert out[0].content == "rule 1\n\nrule 2"
        assert out[1].role == "user"

    def test_realistic_retry_scenario(self) -> None:
        # End-to-end: conversation with one completed turn, then two
        # aborted retries, then the new user request.
        msgs = [
            ChatMessage(role="system", content="You are helpful."),
            ChatMessage(role="user", content="First question"),
            ChatMessage(role="assistant", content="First answer"),
            ChatMessage(role="user", content="Aborted attempt"),
            ChatMessage(role="user", content="Aborted attempt"),
            ChatMessage(role="user", content="hi"),
        ]
        out = normalize_alternating_messages(msgs)
        assert [m.role for m in out] == [
            "system",
            "user",
            "assistant",
            "user",
        ]
        assert out[-1].content == "Aborted attempt\n\nAborted attempt\n\nhi"
