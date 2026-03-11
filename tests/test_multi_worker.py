"""Tests for JWT-based stateless tickets (multi-worker safe)."""

import time

import jwt
import pytest

from fim_one.web.auth import (
    create_bind_ticket,
    create_oauth_state,
    create_sse_ticket,
    verify_bind_ticket,
    verify_oauth_state,
    verify_sse_ticket,
)


class TestSseTicket:
    def test_roundtrip(self):
        token = create_sse_ticket("user-123")
        assert verify_sse_ticket(token) == "user-123"

    def test_expired(self):
        token = create_sse_ticket("user-123", ttl=0)
        time.sleep(0.1)
        with pytest.raises(jwt.ExpiredSignatureError):
            verify_sse_ticket(token)

    def test_wrong_type_rejected(self):
        """A bind ticket must not pass SSE ticket verification."""
        token = create_bind_ticket("user-123")
        with pytest.raises(jwt.InvalidTokenError, match="wrong token type"):
            verify_sse_ticket(token)


class TestOauthState:
    def test_login_roundtrip(self):
        token = create_oauth_state(action="login", user_id=None)
        result = verify_oauth_state(token)
        assert result is not None
        assert result["action"] == "login"
        assert result.get("sub") is None

    def test_bind_roundtrip(self):
        token = create_oauth_state(action="bind", user_id="user-456")
        result = verify_oauth_state(token)
        assert result is not None
        assert result["action"] == "bind"
        assert result["sub"] == "user-456"

    def test_expired_returns_none(self):
        token = create_oauth_state(action="login", user_id=None, ttl=0)
        time.sleep(0.1)
        assert verify_oauth_state(token) is None

    def test_wrong_type_returns_none(self):
        """An SSE ticket must not pass OAuth state verification."""
        token = create_sse_ticket("user-123")
        assert verify_oauth_state(token) is None


class TestBindTicket:
    def test_roundtrip(self):
        token = create_bind_ticket("user-789")
        assert verify_bind_ticket(token) == "user-789"

    def test_expired_returns_none(self):
        token = create_bind_ticket("user-789", ttl=0)
        time.sleep(0.1)
        assert verify_bind_ticket(token) is None

    def test_wrong_type_returns_none(self):
        """An SSE ticket must not pass bind ticket verification."""
        token = create_sse_ticket("user-123")
        assert verify_bind_ticket(token) is None
