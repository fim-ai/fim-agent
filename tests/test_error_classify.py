"""Tests for ``fim_one.core.model.error_classify``."""

from __future__ import annotations

from typing import Any

import pytest

from fim_one.core.model.error_classify import (
    get_error_code,
    get_status_code,
    is_network_like_error,
    iter_error_chain,
)


# ---------------------------------------------------------------------------
# Helpers / fakes
# ---------------------------------------------------------------------------


class FakeStatusError(Exception):
    """Mimic an SDK exception that carries an HTTP status code."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class FakeStatusFieldError(Exception):
    """Mimic an SDK error that uses ``status`` instead of ``status_code``."""

    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class FakeCodedError(Exception):
    """Mimic an SDK exception that carries a string ``code`` attribute."""

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code


class FakeBodyError(Exception):
    """Mimic an SDK error that carries a structured ``body`` mapping."""

    def __init__(self, message: str, *, body: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.body = body


# ---------------------------------------------------------------------------
# iter_error_chain
# ---------------------------------------------------------------------------


class TestIterErrorChain:
    def test_single_exception_yields_only_self(self) -> None:
        exc = ValueError("boom")
        chain = list(iter_error_chain(exc))
        assert chain == [exc]

    def test_explicit_cause_yields_both(self) -> None:
        inner = ConnectionError("inner")
        outer: Exception
        try:
            try:
                raise inner
            except ConnectionError as e:
                raise RuntimeError("outer") from e
        except RuntimeError as e:
            outer = e

        chain = list(iter_error_chain(outer))
        assert chain[0] is outer
        assert inner in chain
        # __cause__ should be set, __suppress_context__ True.
        assert outer.__cause__ is inner

    def test_implicit_context_yields_both(self) -> None:
        inner = ConnectionError("inner")
        outer: Exception
        try:
            try:
                raise inner
            except ConnectionError:
                # Implicit chaining via __context__ (no `from`).
                raise RuntimeError("outer")
        except RuntimeError as e:
            outer = e

        chain = list(iter_error_chain(outer))
        assert chain[0] is outer
        assert inner in chain
        assert outer.__context__ is inner

    def test_cycle_protection(self) -> None:
        # Manually build a self-referencing chain.
        a = RuntimeError("a")
        b = RuntimeError("b")
        a.__cause__ = b
        b.__cause__ = a  # cycle: a -> b -> a -> ...

        chain = list(iter_error_chain(a))
        # Each exception appears at most once -- iteration must terminate.
        assert chain == [a, b]

    def test_self_loop_terminates(self) -> None:
        a = RuntimeError("self-loop")
        a.__cause__ = a
        chain = list(iter_error_chain(a))
        assert chain == [a]


# ---------------------------------------------------------------------------
# get_status_code
# ---------------------------------------------------------------------------


class TestGetStatusCode:
    def test_top_level_status_code(self) -> None:
        exc = FakeStatusError("rate limited", status_code=429)
        assert get_status_code(exc) == 429

    def test_status_field_alias(self) -> None:
        exc = FakeStatusFieldError("server down", status=503)
        assert get_status_code(exc) == 503

    def test_walks_cause_chain(self) -> None:
        inner = FakeStatusError("svc unavailable", status_code=503)
        outer: Exception
        try:
            try:
                raise inner
            except FakeStatusError as e:
                raise RuntimeError("wrapped") from e
        except RuntimeError as e:
            outer = e

        # Outer has no status_code, but the cause does.
        assert get_status_code(outer) == 503

    def test_returns_none_when_absent(self) -> None:
        assert get_status_code(ValueError("nothing here")) is None

    def test_returns_first_match_top_down(self) -> None:
        inner = FakeStatusError("inner", status_code=503)
        outer = FakeStatusError("outer", status_code=429)
        outer.__cause__ = inner
        # Top-down -> outer's 429 wins.
        assert get_status_code(outer) == 429

    def test_non_int_status_code_ignored(self) -> None:
        # Some SDKs set status_code = None or a string -- must skip.
        exc = FakeStatusError("weird", status_code=None)
        # Attach a real-status cause.
        exc.__cause__ = FakeStatusError("real", status_code=500)
        assert get_status_code(exc) == 500


# ---------------------------------------------------------------------------
# get_error_code
# ---------------------------------------------------------------------------


class TestGetErrorCode:
    def test_top_level_code(self) -> None:
        exc = FakeCodedError("bad", code="rate_limit_exceeded")
        assert get_error_code(exc) == "rate_limit_exceeded"

    def test_walks_cause_chain(self) -> None:
        inner = FakeCodedError("inner", code="context_length_exceeded")
        outer: Exception
        try:
            try:
                raise inner
            except FakeCodedError as e:
                raise RuntimeError("wrapped") from e
        except RuntimeError as e:
            outer = e

        assert get_error_code(outer) == "context_length_exceeded"

    def test_body_nested_error_code(self) -> None:
        exc = FakeBodyError(
            "bad",
            body={"error": {"code": "invalid_request_error", "message": "x"}},
        )
        assert get_error_code(exc) == "invalid_request_error"

    def test_body_top_level_code(self) -> None:
        exc = FakeBodyError("bad", body={"code": "fallback_code"})
        assert get_error_code(exc) == "fallback_code"

    def test_returns_none_when_absent(self) -> None:
        assert get_error_code(ValueError("nope")) is None

    def test_first_match_wins_top_down(self) -> None:
        inner = FakeCodedError("inner", code="inner_code")
        outer = FakeCodedError("outer", code="outer_code")
        outer.__cause__ = inner
        assert get_error_code(outer) == "outer_code"

    def test_non_string_code_skipped(self) -> None:
        # ``code`` set to a non-string (e.g. int) should not be returned;
        # walking continues to find the first *string* code in the chain.
        # Use a dynamically-typed exception class so we can attach an int
        # ``code`` without type-checker complaints.
        class DynamicErr(Exception):
            code: object

        exc = DynamicErr("weird")
        exc.code = 42  # int, not a string -- must be skipped.
        cause = FakeCodedError("real", code="real_code")
        exc.__cause__ = cause
        assert get_error_code(exc) == "real_code"


# ---------------------------------------------------------------------------
# is_network_like_error
# ---------------------------------------------------------------------------


class TestIsNetworkLikeError:
    def test_timeout_error(self) -> None:
        assert is_network_like_error(TimeoutError("slow")) is True

    def test_connection_error(self) -> None:
        assert is_network_like_error(ConnectionError("refused")) is True

    def test_connection_subclass(self) -> None:
        assert is_network_like_error(ConnectionResetError("rst")) is True

    def test_plain_exception_not_network(self) -> None:
        # A vanilla Exception with an unrelated message -- not network.
        assert is_network_like_error(Exception("something else")) is False

    def test_message_heuristic_connection_error(self) -> None:
        # Message-based heuristic when the type itself isn't network-like.
        assert is_network_like_error(Exception("Upstream connection error")) is True

    def test_message_heuristic_socket_hang_up(self) -> None:
        assert is_network_like_error(Exception("socket hang up")) is True

    def test_walks_cause_chain(self) -> None:
        outer: Exception
        try:
            try:
                raise TimeoutError("real timeout")
            except TimeoutError as e:
                raise RuntimeError("wrapped non-network") from e
        except RuntimeError as e:
            outer = e

        # RuntimeError alone wouldn't qualify, but the cause does.
        assert is_network_like_error(outer) is True

    def test_walks_implicit_context(self) -> None:
        outer: Exception
        try:
            try:
                raise ConnectionError("dropped")
            except ConnectionError:
                raise RuntimeError("wrapped")  # implicit __context__
        except RuntimeError as e:
            outer = e

        assert is_network_like_error(outer) is True


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-x", "-q"])
