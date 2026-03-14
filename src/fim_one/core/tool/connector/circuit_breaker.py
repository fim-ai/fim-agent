"""Circuit breaker pattern for connector calls.

Prevents cascading failures when external services are down by tracking
consecutive failures per connector and temporarily blocking calls once a
threshold is exceeded.  After a recovery timeout the breaker transitions
to *half-open*, allowing a probe call through.  A success resets the
breaker; another failure re-opens it.

Thread-safety is provided via ``asyncio.Lock`` — all state mutations go
through the ``CircuitBreakerRegistry`` async methods.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Possible states for a circuit breaker."""

    CLOSED = "closed"  # Normal operation — calls pass through
    OPEN = "open"  # Too many failures — calls are rejected
    HALF_OPEN = "half_open"  # Recovery probe — limited calls allowed


class CircuitOpenError(Exception):
    """Raised when a call is rejected because the circuit is open."""

    def __init__(self, connector_id: str, recovery_at: float) -> None:
        remaining = max(0.0, recovery_at - time.monotonic())
        super().__init__(
            f"Circuit breaker open for connector '{connector_id}'. "
            f"Retry in {remaining:.0f}s."
        )
        self.connector_id = connector_id
        self.recovery_at = recovery_at


@dataclass
class CircuitBreaker:
    """Per-connector circuit breaker with configurable thresholds.

    This class holds the state but does **not** manage its own locking.
    Callers must use ``CircuitBreakerRegistry`` which serializes access
    with an ``asyncio.Lock``.
    """

    failure_threshold: int = 5
    """Consecutive failures required to trip the breaker."""

    recovery_timeout: float = 60.0
    """Seconds to wait in OPEN state before transitioning to HALF_OPEN."""

    half_open_max_calls: int = 1
    """Maximum probe calls allowed while HALF_OPEN."""

    # --- mutable state ---
    state: CircuitState = field(default=CircuitState.CLOSED)
    failure_count: int = 0
    last_failure_time: float = 0.0
    half_open_calls: int = 0
    success_count: int = 0
    total_calls: int = 0
    total_failures: int = 0

    # ---- state queries ----

    def can_execute(self) -> bool:
        """Return ``True`` if a call is currently allowed."""
        if self.state is CircuitState.CLOSED:
            return True

        if self.state is CircuitState.OPEN:
            # Check if enough time has elapsed to transition to half-open
            if time.monotonic() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                logger.info("Circuit breaker transitioning to HALF_OPEN")
                return True
            return False

        # HALF_OPEN — allow up to half_open_max_calls
        return self.half_open_calls < self.half_open_max_calls

    @property
    def recovery_at(self) -> float:
        """Monotonic timestamp when the breaker *may* transition to half-open."""
        return self.last_failure_time + self.recovery_timeout

    # ---- state transitions ----

    def record_success(self) -> None:
        """Record a successful call.  Resets the breaker to CLOSED."""
        self.total_calls += 1
        self.success_count += 1
        if self.state is not CircuitState.CLOSED:
            logger.info(
                "Circuit breaker closing after successful probe "
                "(was %s)",
                self.state.value,
            )
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.half_open_calls = 0

    def record_failure(self) -> None:
        """Record a failed call.  May trip the breaker to OPEN."""
        self.total_calls += 1
        self.total_failures += 1
        self.failure_count += 1
        self.last_failure_time = time.monotonic()

        if self.state is CircuitState.HALF_OPEN:
            # Probe failed — immediately re-open
            self.state = CircuitState.OPEN
            logger.warning(
                "Half-open probe failed — circuit re-opened "
                "(failure_count=%d)",
                self.failure_count,
            )
            return

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                "Circuit breaker opened after %d consecutive failures",
                self.failure_count,
            )

    def record_half_open_attempt(self) -> None:
        """Track that a probe call was dispatched in HALF_OPEN state."""
        self.half_open_calls += 1

    def to_dict(self) -> dict[str, Any]:
        """Serialize breaker state for monitoring endpoints."""
        last_failure_utc: str | None = None
        recovery_utc: str | None = None

        if self.last_failure_time > 0:
            # Convert monotonic offset to wall-clock approximation
            now_mono = time.monotonic()
            now_utc = datetime.now(timezone.utc)
            delta = now_mono - self.last_failure_time
            last_failure_utc = (
                now_utc.__class__.fromtimestamp(
                    now_utc.timestamp() - delta, tz=timezone.utc
                )
                .isoformat()
            )
            if self.state is CircuitState.OPEN:
                recovery_delta = now_mono - self.recovery_at
                recovery_utc = (
                    now_utc.__class__.fromtimestamp(
                        now_utc.timestamp() - recovery_delta, tz=timezone.utc
                    )
                    .isoformat()
                )

        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "total_calls": self.total_calls,
            "total_failures": self.total_failures,
            "last_failure": last_failure_utc,
            "recovery_at": recovery_utc,
        }


class CircuitBreakerRegistry:
    """Registry of per-connector circuit breakers.

    All public methods are coroutines that serialize access via an
    ``asyncio.Lock`` so the registry is safe for concurrent use.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 1,
    ) -> None:
        self._breakers: dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._half_open_max_calls = half_open_max_calls

    async def get_breaker(self, connector_id: str) -> CircuitBreaker:
        """Get or create a circuit breaker for *connector_id*."""
        async with self._lock:
            if connector_id not in self._breakers:
                self._breakers[connector_id] = CircuitBreaker(
                    failure_threshold=self._failure_threshold,
                    recovery_timeout=self._recovery_timeout,
                    half_open_max_calls=self._half_open_max_calls,
                )
            return self._breakers[connector_id]

    async def check_and_acquire(self, connector_id: str) -> CircuitBreaker:
        """Check if a call is allowed and return the breaker.

        Raises ``CircuitOpenError`` if the circuit is open.  When the
        breaker is in HALF_OPEN state, this method also increments the
        probe-call counter atomically.
        """
        async with self._lock:
            breaker = self._breakers.get(connector_id)
            if breaker is None:
                breaker = CircuitBreaker(
                    failure_threshold=self._failure_threshold,
                    recovery_timeout=self._recovery_timeout,
                    half_open_max_calls=self._half_open_max_calls,
                )
                self._breakers[connector_id] = breaker

            if not breaker.can_execute():
                raise CircuitOpenError(connector_id, breaker.recovery_at)

            if breaker.state is CircuitState.HALF_OPEN:
                breaker.record_half_open_attempt()

            return breaker

    async def record_success(self, connector_id: str) -> None:
        """Record a successful call for *connector_id*."""
        async with self._lock:
            breaker = self._breakers.get(connector_id)
            if breaker is None:
                breaker = CircuitBreaker(
                    failure_threshold=self._failure_threshold,
                    recovery_timeout=self._recovery_timeout,
                    half_open_max_calls=self._half_open_max_calls,
                )
                self._breakers[connector_id] = breaker
            breaker.record_success()

    async def record_failure(self, connector_id: str) -> None:
        """Record a failed call for *connector_id*."""
        async with self._lock:
            breaker = self._breakers.get(connector_id)
            if breaker is None:
                breaker = CircuitBreaker(
                    failure_threshold=self._failure_threshold,
                    recovery_timeout=self._recovery_timeout,
                    half_open_max_calls=self._half_open_max_calls,
                )
                self._breakers[connector_id] = breaker
            breaker.record_failure()

    def get_status(self) -> dict[str, dict[str, Any]]:
        """Return a snapshot of all breaker states (non-async, read-only)."""
        return {cid: b.to_dict() for cid, b in self._breakers.items()}

    async def reset(self, connector_id: str) -> bool:
        """Manually reset a breaker to CLOSED. Returns True if it existed."""
        async with self._lock:
            breaker = self._breakers.get(connector_id)
            if breaker is None:
                return False
            breaker.state = CircuitState.CLOSED
            breaker.failure_count = 0
            breaker.half_open_calls = 0
            return True


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_default_registry: CircuitBreakerRegistry | None = None
_registry_lock = asyncio.Lock()


async def get_circuit_breaker_registry() -> CircuitBreakerRegistry:
    """Return the process-wide circuit-breaker registry (lazy-created)."""
    global _default_registry
    if _default_registry is not None:
        return _default_registry
    async with _registry_lock:
        if _default_registry is None:
            _default_registry = CircuitBreakerRegistry()
        return _default_registry


def set_circuit_breaker_registry(registry: CircuitBreakerRegistry) -> None:
    """Replace the global registry (useful for testing)."""
    global _default_registry
    _default_registry = registry
