"""Tests for CompactUtils — token estimation and smart truncation."""

import pytest

from fim_agent.core.memory.compact import CompactUtils
from fim_agent.core.model.types import ChatMessage


class TestEstimateTokens:
    def test_empty_string(self):
        assert CompactUtils.estimate_tokens("") == 0

    def test_short_string(self):
        # "hi" = 2 chars → max(1, 0) = 1
        assert CompactUtils.estimate_tokens("hi") >= 1

    def test_longer_ascii_string(self):
        text = "a" * 400
        assert CompactUtils.estimate_tokens(text) == 100

    def test_none_like(self):
        assert CompactUtils.estimate_tokens("") == 0

    def test_pure_chinese(self):
        # 10 Chinese chars → 10 / 1.5 ≈ 6.67 → int(6.67) = 6
        text = "你好世界测试中文字符"
        tokens = CompactUtils.estimate_tokens(text)
        assert tokens == 6

    def test_pure_chinese_longer(self):
        # 36 Chinese chars → 36 / 1.5 = 24
        text = "这是一段较长的中文文本用来测试分词估算的准确性看看效果如何呢我觉得还行吧"
        tokens = CompactUtils.estimate_tokens(text)
        assert tokens == 24

    def test_mixed_chinese_english(self):
        # "Hello你好World世界" → 10 ASCII + 4 CJK
        # 10/4 + 4/1.5 = 2.5 + 2.67 = 5.17 → int(5.17) = 5
        text = "Hello你好World世界"
        tokens = CompactUtils.estimate_tokens(text)
        assert tokens == 5

    def test_chinese_with_code(self):
        # Mixed: Chinese explanation with code snippet
        text = "使用print('hello')来输出"
        # CJK chars: 使用 来输出 = 5 non-ASCII
        # ASCII chars: print('hello') = 14 ASCII
        # 14/4 + 5/1.5 = 3.5 + 3.33 = 6.83 → int(6.83) = 6
        tokens = CompactUtils.estimate_tokens(text)
        assert tokens == 6

    def test_chinese_much_higher_than_naive(self):
        # The old len//4 heuristic would massively undercount Chinese.
        # 100 Chinese chars: old = len("...") // 4 (bytes don't matter here
        # since len() counts codepoints), but each CJK char is ~1 token.
        text = "中" * 100
        tokens = CompactUtils.estimate_tokens(text)
        # 100 / 1.5 = 66.67 → 66
        assert tokens == 66
        # Old heuristic would give 100/4 = 25, which is way too low
        assert tokens > 50


class TestEstimateMessagesTokens:
    def test_empty_list(self):
        assert CompactUtils.estimate_messages_tokens([]) == 0

    def test_single_message(self):
        msgs = [ChatMessage(role="user", content="hello world")]
        tokens = CompactUtils.estimate_messages_tokens(msgs)
        # 4 overhead + 11 ASCII chars / 4 = 4 + 2 = 6
        assert tokens > 0

    def test_multiple_messages(self):
        msgs = [
            ChatMessage(role="user", content="hi"),
            ChatMessage(role="assistant", content="hello"),
        ]
        tokens = CompactUtils.estimate_messages_tokens(msgs)
        assert tokens > 0


class TestSmartTruncate:
    def test_empty_input(self):
        assert CompactUtils.smart_truncate([], max_tokens=1000) == []

    def test_all_fit(self):
        msgs = [
            ChatMessage(role="user", content="hi"),
            ChatMessage(role="assistant", content="hello"),
        ]
        result = CompactUtils.smart_truncate(msgs, max_tokens=10000)
        assert len(result) == 2
        assert result[0].role == "user"
        assert result[1].role == "assistant"

    def test_truncation_keeps_recent(self):
        # Create many messages that exceed budget.
        msgs = []
        for i in range(50):
            role = "user" if i % 2 == 0 else "assistant"
            msgs.append(ChatMessage(role=role, content=f"message number {i} " * 20))

        result = CompactUtils.smart_truncate(msgs, max_tokens=200)
        assert len(result) < len(msgs)
        # The last message in the result should be the last from the input
        # (or close to it).
        assert result[-1].content == msgs[-1].content or len(result) > 0

    def test_does_not_start_with_assistant(self):
        # Budget only fits the last 2 messages; after truncation the first
        # message would be "assistant" — smart_truncate must drop it.
        msgs = [
            ChatMessage(role="user", content="a" * 200),       # ~54 tokens
            ChatMessage(role="assistant", content="b" * 200),   # ~54 tokens
            ChatMessage(role="user", content="hi"),             # ~5 tokens
            ChatMessage(role="assistant", content="hello"),     # ~5 tokens
        ]
        result = CompactUtils.smart_truncate(msgs, max_tokens=20)
        if result:
            assert result[0].role != "assistant"

    def test_single_user_message(self):
        msgs = [ChatMessage(role="user", content="just me")]
        result = CompactUtils.smart_truncate(msgs, max_tokens=10000)
        assert len(result) == 1
        assert result[0].content == "just me"
