"""Tests for the connector circuit breaker pattern."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import patch

import pytest

from fim_one.core.tool.connector.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerRegistry,
    CircuitOpenError,
    CircuitState,
    get_circuit_breaker_registry,
    set_circuit_breaker_registry,
)


# ---------------------------------------------------------------------------
# CircuitBreaker unit tests
# ---------------------------------------------------------------------------


class TestCircuitBreakerClosed:
    """Tests for the CLOSED (normal) state."""

    def test_initial_state_is_closed(self) -> None:
        cb = CircuitBreaker()
        assert cb.state is CircuitState.CLOSED

    def test_closed_allows_calls(self) -> None:
        cb = CircuitBreaker()
        assert cb.can_execute() is True

    def test_success_keeps_closed(self) -> None:
        cb = CircuitBreaker()
        cb.record_success()
        assert cb.state is CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_single_failure_stays_closed(self) -> None:
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        assert cb.state is CircuitState.CLOSED
        assert cb.failure_count == 1

    def test_failures_below_threshold_stay_closed(self) -> None:
        cb = CircuitBreaker(failure_threshold=5)
        for _ in range(4):
            cb.record_failure()
        assert cb.state is CircuitState.CLOSED
        assert cb.can_execute() is True


class TestCircuitBreakerOpen:
    """Tests for the OPEN (failing) state."""

    def test_opens_at_threshold(self) -> None:
        cb = CircuitBreaker(failure_threshold=3)
        for _ in range(3):
            cb.record_failure()
        assert cb.state is CircuitState.OPEN

    def test_open_rejects_calls(self) -> None:
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=9999)
        cb.record_failure()
        cb.record_failure()
        assert cb.state is CircuitState.OPEN
        assert cb.can_execute() is False

    def test_success_resets_failure_count(self) -> None:
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.failure_count == 0
        assert cb.state is CircuitState.CLOSED
        # Now need 3 more failures to open again
        cb.record_failure()
        cb.record_failure()
        assert cb.state is CircuitState.CLOSED

    def test_total_counters(self) -> None:
        cb = CircuitBreaker(failure_threshold=5)
        cb.record_success()
        cb.record_failure()
        cb.record_success()
        assert cb.total_calls == 3
        assert cb.total_failures == 1
        assert cb.success_count == 2


class TestCircuitBreakerHalfOpen:
    """Tests for the HALF_OPEN (recovery probe) state."""

    def test_transitions_to_half_open_after_timeout(self) -> None:
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01)
        cb.record_failure()
        assert cb.state is CircuitState.OPEN

        # Wait for recovery timeout
        time.sleep(0.02)
        assert cb.can_execute() is True
        assert cb.state is CircuitState.HALF_OPEN

    def test_half_open_limits_calls(self) -> None:
        cb = CircuitBreaker(
            failure_threshold=1,
            recovery_timeout=0.01,
            half_open_max_calls=1,
        )
        cb.record_failure()
        time.sleep(0.02)

        # First call allowed (transitions to half-open)
        assert cb.can_execute() is True
        assert cb.state is CircuitState.HALF_OPEN

        # Track the probe
        cb.record_half_open_attempt()

        # Second call rejected (max probe calls reached)
        assert cb.can_execute() is False

    def test_half_open_success_closes_circuit(self) -> None:
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01)
        cb.record_failure()
        time.sleep(0.02)

        assert cb.can_execute() is True  # transitions to half-open
        cb.record_success()
        assert cb.state is CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_half_open_failure_reopens_circuit(self) -> None:
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01)
        cb.record_failure()
        time.sleep(0.02)

        assert cb.can_execute() is True  # transitions to half-open
        cb.record_failure()
        assert cb.state is CircuitState.OPEN


class TestCircuitBreakerSerialization:
    """Tests for the to_dict() monitoring output."""

    def test_closed_breaker_serialization(self) -> None:
        cb = CircuitBreaker()
        d = cb.to_dict()
        assert d["state"] == "closed"
        assert d["failure_count"] == 0
        assert d["last_failure"] is None

    def test_open_breaker_serialization(self) -> None:
        cb = CircuitBreaker(failure_threshold=1)
        cb.record_failure()
        d = cb.to_dict()
        assert d["state"] == "open"
        assert d["failure_count"] == 1
        assert d["last_failure"] is not None
        assert d["recovery_at"] is not None

    def test_serialization_has_all_fields(self) -> None:
        cb = CircuitBreaker()
        d = cb.to_dict()
        expected_keys = {
            "state",
            "failure_count",
            "total_calls",
            "total_failures",
            "last_failure",
            "recovery_at",
        }
        assert set(d.keys()) == expected_keys


# ---------------------------------------------------------------------------
# CircuitBreakerRegistry tests
# ---------------------------------------------------------------------------


class TestCircuitBreakerRegistry:
    """Tests for the async registry."""

    @pytest.fixture()
    def registry(self) -> CircuitBreakerRegistry:
        return CircuitBreakerRegistry(
            failure_threshold=3,
            recovery_timeout=0.05,
        )

    @pytest.mark.asyncio
    async def test_get_breaker_creates_new(
        self, registry: CircuitBreakerRegistry
    ) -> None:
        breaker = await registry.get_breaker("conn-1")
        assert breaker.state is CircuitState.CLOSED
        assert breaker.failure_threshold == 3

    @pytest.mark.asyncio
    async def test_get_breaker_returns_same_instance(
        self, registry: CircuitBreakerRegistry
    ) -> None:
        b1 = await registry.get_breaker("conn-1")
        b2 = await registry.get_breaker("conn-1")
        assert b1 is b2

    @pytest.mark.asyncio
    async def test_different_connectors_have_independent_breakers(
        self, registry: CircuitBreakerRegistry
    ) -> None:
        b1 = await registry.get_breaker("conn-1")
        b2 = await registry.get_breaker("conn-2")
        assert b1 is not b2

        # Failures on one do not affect the other
        await registry.record_failure("conn-1")
        await registry.record_failure("conn-1")
        await registry.record_failure("conn-1")

        b1 = await registry.get_breaker("conn-1")
        b2 = await registry.get_breaker("conn-2")
        assert b1.state is CircuitState.OPEN
        assert b2.state is CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_check_and_acquire_allows_closed(
        self, registry: CircuitBreakerRegistry
    ) -> None:
        breaker = await registry.check_and_acquire("conn-1")
        assert breaker.state is CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_check_and_acquire_rejects_open(
        self, registry: CircuitBreakerRegistry
    ) -> None:
        # Trip the breaker
        for _ in range(3):
            await registry.record_failure("conn-1")

        with pytest.raises(CircuitOpenError) as exc_info:
            await registry.check_and_acquire("conn-1")

        assert "conn-1" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_record_success_closes_breaker(
        self, registry: CircuitBreakerRegistry
    ) -> None:
        await registry.record_failure("conn-1")
        await registry.record_failure("conn-1")
        await registry.record_success("conn-1")

        breaker = await registry.get_breaker("conn-1")
        assert breaker.state is CircuitState.CLOSED
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_record_failure_auto_creates_breaker(
        self, registry: CircuitBreakerRegistry
    ) -> None:
        # record_failure should auto-create the breaker
        await registry.record_failure("new-conn")
        breaker = await registry.get_breaker("new-conn")
        assert breaker.failure_count == 1

    @pytest.mark.asyncio
    async def test_record_success_auto_creates_breaker(
        self, registry: CircuitBreakerRegistry
    ) -> None:
        # record_success should auto-create the breaker
        await registry.record_success("new-conn")
        breaker = await registry.get_breaker("new-conn")
        assert breaker.success_count == 1

    @pytest.mark.asyncio
    async def test_get_status_returns_all_breakers(
        self, registry: CircuitBreakerRegistry
    ) -> None:
        await registry.get_breaker("conn-1")
        await registry.get_breaker("conn-2")

        status = registry.get_status()
        assert "conn-1" in status
        assert "conn-2" in status
        assert status["conn-1"]["state"] == "closed"

    @pytest.mark.asyncio
    async def test_get_status_empty_when_no_breakers(
        self, registry: CircuitBreakerRegistry
    ) -> None:
        status = registry.get_status()
        assert status == {}

    @pytest.mark.asyncio
    async def test_reset_closes_open_breaker(
        self, registry: CircuitBreakerRegistry
    ) -> None:
        for _ in range(3):
            await registry.record_failure("conn-1")

        breaker = await registry.get_breaker("conn-1")
        assert breaker.state is CircuitState.OPEN

        result = await registry.reset("conn-1")
        assert result is True
        assert breaker.state is CircuitState.CLOSED
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_reset_nonexistent_returns_false(
        self, registry: CircuitBreakerRegistry
    ) -> None:
        result = await registry.reset("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_half_open_recovery_flow(
        self, registry: CircuitBreakerRegistry
    ) -> None:
        """Full lifecycle: closed -> open -> half-open -> closed."""
        # Trip the breaker
        for _ in range(3):
            await registry.record_failure("conn-1")

        breaker = await registry.get_breaker("conn-1")
        assert breaker.state is CircuitState.OPEN

        # Wait for recovery timeout (0.05s)
        await asyncio.sleep(0.06)

        # Should transition to half-open and allow a probe
        probe_breaker = await registry.check_and_acquire("conn-1")
        assert probe_breaker.state is CircuitState.HALF_OPEN

        # Probe succeeds
        await registry.record_success("conn-1")
        assert breaker.state is CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_failure_reopens(
        self, registry: CircuitBreakerRegistry
    ) -> None:
        """Half-open probe failure should re-open the circuit."""
        for _ in range(3):
            await registry.record_failure("conn-1")

        await asyncio.sleep(0.06)

        # Transition to half-open
        await registry.check_and_acquire("conn-1")

        # Probe fails
        await registry.record_failure("conn-1")

        breaker = await registry.get_breaker("conn-1")
        assert breaker.state is CircuitState.OPEN


# ---------------------------------------------------------------------------
# Singleton / module-level helpers
# ---------------------------------------------------------------------------


class TestRegistrySingleton:
    """Tests for the module-level singleton helpers."""

    @pytest.mark.asyncio
    async def test_get_returns_same_instance(self) -> None:
        # Reset to ensure clean state
        set_circuit_breaker_registry(CircuitBreakerRegistry())

        r1 = await get_circuit_breaker_registry()
        r2 = await get_circuit_breaker_registry()
        assert r1 is r2

    @pytest.mark.asyncio
    async def test_set_replaces_registry(self) -> None:
        original = await get_circuit_breaker_registry()
        replacement = CircuitBreakerRegistry(failure_threshold=99)
        set_circuit_breaker_registry(replacement)

        current = await get_circuit_breaker_registry()
        assert current is replacement
        assert current is not original

        # Clean up
        set_circuit_breaker_registry(CircuitBreakerRegistry())


# ---------------------------------------------------------------------------
# CircuitOpenError tests
# ---------------------------------------------------------------------------


class TestCircuitOpenError:
    """Tests for the error class."""

    def test_message_contains_connector_id(self) -> None:
        err = CircuitOpenError("my-conn", time.monotonic() + 30)
        assert "my-conn" in str(err)

    def test_attributes(self) -> None:
        recovery = time.monotonic() + 60
        err = CircuitOpenError("my-conn", recovery)
        assert err.connector_id == "my-conn"
        assert err.recovery_at == recovery

    def test_message_shows_retry_time(self) -> None:
        err = CircuitOpenError("x", time.monotonic() + 10)
        msg = str(err)
        assert "Retry in" in msg


# ---------------------------------------------------------------------------
# Concurrency safety
# ---------------------------------------------------------------------------


class TestConcurrency:
    """Basic concurrency tests to verify lock behavior."""

    @pytest.mark.asyncio
    async def test_concurrent_failures_are_safe(self) -> None:
        registry = CircuitBreakerRegistry(failure_threshold=100)
        await registry.get_breaker("conn-1")

        async def fail_many() -> None:
            for _ in range(50):
                await registry.record_failure("conn-1")

        # Run two concurrent failure streams
        await asyncio.gather(fail_many(), fail_many())

        breaker = await registry.get_breaker("conn-1")
        assert breaker.failure_count == 100
        assert breaker.state is CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_concurrent_get_breaker_returns_same_instance(self) -> None:
        registry = CircuitBreakerRegistry()

        async def get() -> CircuitBreaker:
            return await registry.get_breaker("conn-1")

        results = await asyncio.gather(*[get() for _ in range(20)])
        # All should be the same instance
        assert all(r is results[0] for r in results)
