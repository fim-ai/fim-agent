"""Tests for the V4A diff helper.

Ported from OpenAI Agents SDK Python's ``tests/test_apply_diff.py`` and
``tests/test_apply_diff_helpers.py`` with imports rewritten to FIM One paths.
"""

from __future__ import annotations

import pytest

from fim_one.core.tool.patch import apply_diff
from fim_one.core.tool.patch.v4a import (
    Chunk,
    ParserState,
    _apply_chunks,
    _find_context,
    _find_context_core,
    _is_done,
    _normalize_diff_lines,
    _read_section,
    _read_str,
)


# ---------------------------------------------------------------------------
# Public apply_diff() behaviour
# ---------------------------------------------------------------------------


def test_apply_diff_with_floating_hunk_adds_lines() -> None:
    diff = "\n".join(["@@", "+hello", "+world"])  # no trailing newline
    assert apply_diff("", diff) == "hello\nworld\n"


def test_apply_diff_with_empty_input_and_crlf_diff_preserves_crlf() -> None:
    diff = "\r\n".join(["@@", "+hello", "+world"])
    assert apply_diff("", diff) == "hello\r\nworld\r\n"


def test_apply_diff_create_mode_requires_plus_prefix() -> None:
    diff = "plain line"
    with pytest.raises(ValueError):
        apply_diff("", diff, mode="create")


def test_apply_diff_create_mode_preserves_trailing_newline() -> None:
    diff = "\n".join(["+hello", "+world", "+"])
    assert apply_diff("", diff, mode="create") == "hello\nworld\n"


def test_apply_diff_applies_contextual_replacement() -> None:
    input_text = "line1\nline2\nline3\n"
    diff = "\n".join(["@@ line1", "-line2", "+updated", " line3"])
    assert apply_diff(input_text, diff) == "line1\nupdated\nline3\n"


def test_apply_diff_raises_on_context_mismatch() -> None:
    input_text = "one\ntwo\n"
    diff = "\n".join(["@@ -1,2 +1,2 @@", " x", "-two", "+2"])
    with pytest.raises(ValueError):
        apply_diff(input_text, diff)


def test_apply_diff_with_crlf_input_and_lf_diff_preserves_crlf() -> None:
    input_text = "line1\r\nline2\r\nline3\r\n"
    diff = "\n".join(["@@ line1", "-line2", "+updated", " line3"])
    assert apply_diff(input_text, diff) == "line1\r\nupdated\r\nline3\r\n"


def test_apply_diff_with_lf_input_and_crlf_diff_preserves_lf() -> None:
    input_text = "line1\nline2\nline3\n"
    diff = "\r\n".join(["@@ line1", "-line2", "+updated", " line3"])
    assert apply_diff(input_text, diff) == "line1\nupdated\nline3\n"


def test_apply_diff_with_crlf_input_and_crlf_diff_preserves_crlf() -> None:
    input_text = "line1\r\nline2\r\nline3\r\n"
    diff = "\r\n".join(["@@ line1", "-line2", "+updated", " line3"])
    assert apply_diff(input_text, diff) == "line1\r\nupdated\r\nline3\r\n"


def test_apply_diff_create_mode_preserves_crlf_newlines() -> None:
    diff = "\r\n".join(["+hello", "+world", "+"])
    assert apply_diff("", diff, mode="create") == "hello\r\nworld\r\n"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def test_normalize_diff_lines_drops_trailing_blank() -> None:
    assert _normalize_diff_lines("a\nb\n") == ["a", "b"]


def test_is_done_true_when_index_out_of_range() -> None:
    state = ParserState(lines=["line"], index=1)
    assert _is_done(state, [])


def test_read_str_returns_empty_when_missing_prefix() -> None:
    state = ParserState(lines=["value"], index=0)
    assert _read_str(state, "nomatch") == ""
    assert state.index == 0


def test_read_section_returns_eof_flag() -> None:
    result = _read_section(["*** End of File"], 0)
    assert result.eof


def test_read_section_raises_on_invalid_marker() -> None:
    with pytest.raises(ValueError):
        _read_section(["*** Bad Marker"], 0)


def test_read_section_raises_when_empty_segment() -> None:
    with pytest.raises(ValueError):
        _read_section([], 0)


def test_find_context_eof_fallbacks() -> None:
    match = _find_context(["one"], ["missing"], start=0, eof=True)
    assert match.new_index == -1
    assert match.fuzz >= 10000


def test_find_context_core_stripped_matches() -> None:
    match = _find_context_core([" line "], ["line"], start=0)
    assert match.new_index == 0
    assert match.fuzz == 100


def test_apply_chunks_rejects_bad_chunks() -> None:
    with pytest.raises(ValueError):
        _apply_chunks("abc", [Chunk(orig_index=10, del_lines=[], ins_lines=[])], newline="\n")

    with pytest.raises(ValueError):
        _apply_chunks(
            "abc",
            [
                Chunk(orig_index=0, del_lines=["a"], ins_lines=[]),
                Chunk(orig_index=0, del_lines=["b"], ins_lines=[]),
            ],
            newline="\n",
        )
