"""Shared pytest fixtures for fim-one tests."""

from __future__ import annotations

import json
from typing import Any, AsyncIterator

import pytest

from fim_one.core.agent import ReActAgent
from fim_one.core.model import BaseLLM, ChatMessage, LLMResult, StreamChunk
from fim_one.core.tool import BaseTool, ToolRegistry


# ---------------------------------------------------------------------------
# FakeLLM -- a configurable mock LLM for deterministic testing
# ---------------------------------------------------------------------------


class FakeLLM(BaseLLM):
    """A fake LLM that returns pre-configured responses in sequence.

    Each call to ``chat()`` pops the next response from the queue.  If the
    queue is exhausted, the last response is reused indefinitely.

    Args:
        responses: Ordered list of ``LLMResult`` objects to return.
        abilities: Optional dict to override the default abilities.
    """

    def __init__(
        self,
        responses: list[LLMResult] | None = None,
        *,
        abilities: dict[str, bool] | None = None,
    ) -> None:
        self._responses: list[LLMResult] = responses or []
        self._call_count: int = 0
        self._abilities = abilities

    @property
    def call_count(self) -> int:
        return self._call_count

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
        reasoning_effort: Any = None,
    ) -> LLMResult:
        idx = min(self._call_count, len(self._responses) - 1)
        self._call_count += 1
        return self._responses[idx]

    async def stream_chat(
        self,
        messages: list[ChatMessage],
        *,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """Streaming variant that replays the same pre-configured responses.

        Emits the response content/reasoning as delta chunks and flushes
        any tool_calls on the final chunk, matching the real stream_chat
        behaviour used by ``_stream_tool_decision``.
        """
        idx = min(self._call_count, len(self._responses) - 1)
        self._call_count += 1
        resp = self._responses[idx]
        msg = resp.message

        # Emit content / reasoning deltas.
        if msg.reasoning_content:
            yield StreamChunk(delta_reasoning=msg.reasoning_content)
        if isinstance(msg.content, str) and msg.content:
            yield StreamChunk(delta_content=msg.content)

        # Final chunk with tool_calls and usage (mirrors real provider).
        finish = "tool_calls" if msg.tool_calls else "stop"
        yield StreamChunk(
            finish_reason=finish,
            tool_calls=msg.tool_calls,
            usage=resp.usage,
        )

    @property
    def abilities(self) -> dict[str, bool]:
        if self._abilities is not None:
            return self._abilities
        return {
            "tool_call": False,
            "json_mode": False,
            "vision": False,
            "streaming": False,
        }


# ---------------------------------------------------------------------------
# EchoTool -- a trivial tool that echoes its input
# ---------------------------------------------------------------------------


class EchoTool(BaseTool):
    """A simple tool that returns its ``text`` argument verbatim."""

    @property
    def name(self) -> str:
        return "echo"

    @property
    def description(self) -> str:
        return "Echoes the input text back."

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Text to echo.",
                },
            },
            "required": ["text"],
        }

    async def run(self, **kwargs: Any) -> str:
        return kwargs.get("text", "")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_llm() -> FakeLLM:
    """Return a ``FakeLLM`` with a single default final-answer response."""
    default_response = LLMResult(
        message=ChatMessage(
            role="assistant",
            content=json.dumps(
                {
                    "type": "final_answer",
                    "reasoning": "No further action needed.",
                    "answer": "42",
                }
            ),
        ),
        usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    )
    return FakeLLM(responses=[default_response])


@pytest.fixture()
def tool_registry() -> ToolRegistry:
    """Return a ``ToolRegistry`` pre-loaded with an ``EchoTool``."""
    registry = ToolRegistry()
    registry.register(EchoTool())
    return registry


@pytest.fixture()
def mock_agent(mock_llm: FakeLLM, tool_registry: ToolRegistry) -> ReActAgent:
    """Return a ``ReActAgent`` wired to the fake LLM and echo tool registry."""
    return ReActAgent(llm=mock_llm, tools=tool_registry, max_iterations=5)
