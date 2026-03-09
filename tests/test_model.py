"""Tests for the Model layer (types, base, openai_compatible)."""

from __future__ import annotations

import json
from typing import Any, AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fim_agent.core.model import (
    BaseLLM,
    ChatMessage,
    LLMResult,
    OpenAICompatibleLLM,
    StreamChunk,
    ToolCallRequest,
)


# ======================================================================
# ChatMessage.to_openai_dict
# ======================================================================


class TestChatMessageToOpenAIDict:
    """Verify ``ChatMessage.to_openai_dict()`` serialisation."""

    def test_basic_user_message(self) -> None:
        msg = ChatMessage(role="user", content="Hello")
        d = msg.to_openai_dict()
        assert d == {"role": "user", "content": "Hello"}

    def test_system_message(self) -> None:
        msg = ChatMessage(role="system", content="You are helpful.")
        d = msg.to_openai_dict()
        assert d == {"role": "system", "content": "You are helpful."}

    def test_assistant_message_no_content(self) -> None:
        """Assistant message with content=None should not include 'content' key."""
        msg = ChatMessage(role="assistant")
        d = msg.to_openai_dict()
        assert d == {"role": "assistant"}
        assert "content" not in d

    def test_message_with_tool_calls(self) -> None:
        tc = ToolCallRequest(id="call_1", name="my_tool", arguments={"x": 1})
        msg = ChatMessage(role="assistant", tool_calls=[tc])
        d = msg.to_openai_dict()

        assert d["role"] == "assistant"
        assert len(d["tool_calls"]) == 1

        tc_dict = d["tool_calls"][0]
        assert tc_dict["id"] == "call_1"
        assert tc_dict["type"] == "function"
        assert tc_dict["function"]["name"] == "my_tool"
        assert json.loads(tc_dict["function"]["arguments"]) == {"x": 1}

    def test_message_with_multiple_tool_calls(self) -> None:
        tc1 = ToolCallRequest(id="call_1", name="tool_a", arguments={"a": 1})
        tc2 = ToolCallRequest(id="call_2", name="tool_b", arguments={"b": 2})
        msg = ChatMessage(role="assistant", tool_calls=[tc1, tc2])
        d = msg.to_openai_dict()
        assert len(d["tool_calls"]) == 2
        assert d["tool_calls"][0]["function"]["name"] == "tool_a"
        assert d["tool_calls"][1]["function"]["name"] == "tool_b"

    def test_message_with_tool_call_id(self) -> None:
        msg = ChatMessage(
            role="tool",
            content="result data",
            tool_call_id="call_1",
        )
        d = msg.to_openai_dict()
        assert d["role"] == "tool"
        assert d["content"] == "result data"
        assert d["tool_call_id"] == "call_1"

    def test_message_with_name(self) -> None:
        msg = ChatMessage(role="tool", content="ok", name="my_fn")
        d = msg.to_openai_dict()
        assert d["name"] == "my_fn"

    def test_message_empty_tool_calls_list_omitted(self) -> None:
        """An empty tool_calls list should NOT produce a 'tool_calls' key."""
        msg = ChatMessage(role="assistant", content="hi", tool_calls=[])
        d = msg.to_openai_dict()
        assert "tool_calls" not in d

    def test_all_fields_combined(self) -> None:
        tc = ToolCallRequest(id="c1", name="fn", arguments={})
        msg = ChatMessage(
            role="assistant",
            content="thinking",
            tool_calls=[tc],
            tool_call_id="c0",
            name="helper",
        )
        d = msg.to_openai_dict()
        assert d["role"] == "assistant"
        assert d["content"] == "thinking"
        assert d["tool_call_id"] == "c0"
        assert d["name"] == "helper"
        assert len(d["tool_calls"]) == 1


# ======================================================================
# ToolCallRequest
# ======================================================================


class TestToolCallRequest:
    """Verify ``ToolCallRequest`` dataclass creation."""

    def test_creation(self) -> None:
        tc = ToolCallRequest(id="abc", name="my_tool", arguments={"k": "v"})
        assert tc.id == "abc"
        assert tc.name == "my_tool"
        assert tc.arguments == {"k": "v"}

    def test_empty_arguments(self) -> None:
        tc = ToolCallRequest(id="x", name="t", arguments={})
        assert tc.arguments == {}

    def test_complex_arguments(self) -> None:
        args: dict[str, Any] = {"nested": {"a": [1, 2, 3]}, "flag": True}
        tc = ToolCallRequest(id="x", name="t", arguments=args)
        assert tc.arguments["nested"]["a"] == [1, 2, 3]


# ======================================================================
# StreamChunk
# ======================================================================


class TestStreamChunk:
    """Verify ``StreamChunk`` dataclass creation."""

    def test_defaults(self) -> None:
        chunk = StreamChunk()
        assert chunk.delta_content is None
        assert chunk.finish_reason is None
        assert chunk.tool_calls is None

    def test_with_content(self) -> None:
        chunk = StreamChunk(delta_content="hello")
        assert chunk.delta_content == "hello"

    def test_with_finish_reason(self) -> None:
        chunk = StreamChunk(finish_reason="stop")
        assert chunk.finish_reason == "stop"

    def test_with_tool_calls(self) -> None:
        tc = ToolCallRequest(id="c1", name="fn", arguments={})
        chunk = StreamChunk(tool_calls=[tc])
        assert chunk.tool_calls is not None
        assert len(chunk.tool_calls) == 1


# ======================================================================
# LLMResult
# ======================================================================


class TestLLMResult:
    """Verify ``LLMResult`` dataclass creation."""

    def test_basic(self) -> None:
        msg = ChatMessage(role="assistant", content="answer")
        result = LLMResult(message=msg)
        assert result.message.content == "answer"
        assert result.usage == {}

    def test_with_usage(self) -> None:
        msg = ChatMessage(role="assistant", content="ok")
        usage = {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        result = LLMResult(message=msg, usage=usage)
        assert result.usage["total_tokens"] == 15

    def test_usage_default_factory(self) -> None:
        """Each LLMResult should get its own default dict, not a shared one."""
        r1 = LLMResult(message=ChatMessage(role="assistant"))
        r2 = LLMResult(message=ChatMessage(role="assistant"))
        r1.usage["x"] = 1
        assert "x" not in r2.usage


# ======================================================================
# BaseLLM abstract class
# ======================================================================


class TestBaseLLM:
    """Verify ``BaseLLM`` is abstract and cannot be directly instantiated."""

    def test_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            BaseLLM()  # type: ignore[abstract]

    def test_default_abilities(self) -> None:
        """A minimal concrete subclass should inherit the default abilities."""

        class MinimalLLM(BaseLLM):
            async def chat(self, messages, **kwargs):  # type: ignore[override]
                return LLMResult(message=ChatMessage(role="assistant"))

            async def stream_chat(self, messages, **kwargs):  # type: ignore[override]
                yield StreamChunk()

        llm = MinimalLLM()
        abilities = llm.abilities
        assert abilities["tool_call"] is False
        assert abilities["json_mode"] is False
        assert abilities["vision"] is False
        assert abilities["streaming"] is False


# ======================================================================
# OpenAICompatibleLLM init (no real API calls)
# ======================================================================


class TestOpenAICompatibleLLMInit:
    """Verify ``OpenAICompatibleLLM`` stores its configuration correctly."""

    @patch("fim_agent.core.model.openai_compatible.AsyncOpenAI")
    def test_stores_model(self, mock_openai_cls: MagicMock) -> None:
        llm = OpenAICompatibleLLM(
            api_key="sk-test",
            base_url="https://api.example.com/v1",
            model="gpt-4o",
        )
        assert llm._model == "gpt-4o"

    @patch("fim_agent.core.model.openai_compatible.AsyncOpenAI")
    def test_stores_default_temperature(self, mock_openai_cls: MagicMock) -> None:
        llm = OpenAICompatibleLLM(
            api_key="sk-test",
            base_url="https://api.example.com/v1",
            model="gpt-4o",
            default_temperature=0.2,
        )
        assert llm._default_temperature == 0.2

    @patch("fim_agent.core.model.openai_compatible.AsyncOpenAI")
    def test_stores_default_max_tokens(self, mock_openai_cls: MagicMock) -> None:
        llm = OpenAICompatibleLLM(
            api_key="sk-test",
            base_url="https://api.example.com/v1",
            model="gpt-4o",
            default_max_tokens=2048,
        )
        assert llm._default_max_tokens == 2048

    @patch("fim_agent.core.model.openai_compatible.AsyncOpenAI")
    def test_creates_async_client(self, mock_openai_cls: MagicMock) -> None:
        OpenAICompatibleLLM(
            api_key="sk-key",
            base_url="https://api.example.com/v1",
            model="m",
        )
        mock_openai_cls.assert_called_once_with(
            api_key="sk-key",
            base_url="https://api.example.com/v1",
        )

    @patch("fim_agent.core.model.openai_compatible.AsyncOpenAI")
    def test_abilities_all_true(self, mock_openai_cls: MagicMock) -> None:
        llm = OpenAICompatibleLLM(
            api_key="sk-test",
            base_url="https://api.example.com/v1",
            model="gpt-4o",
        )
        abilities = llm.abilities
        assert abilities["tool_call"] is True
        assert abilities["json_mode"] is True
        assert abilities["vision"] is True
        assert abilities["streaming"] is True

    @patch("fim_agent.core.model.openai_compatible.AsyncOpenAI")
    def test_default_config_values(self, mock_openai_cls: MagicMock) -> None:
        """Verify factory defaults when no optional kwargs are provided."""
        llm = OpenAICompatibleLLM(
            api_key="sk-test",
            base_url="https://api.example.com/v1",
            model="gpt-4o",
        )
        assert llm._default_temperature == 0.7
        assert llm._default_max_tokens == 64000
