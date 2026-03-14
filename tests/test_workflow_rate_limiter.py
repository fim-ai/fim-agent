"""Tests for WorkflowRateLimiter — per-user sliding window rate limiting."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import patch

import pytest

from fim_one.core.workflow.rate_limiter import WorkflowRateLimiter


@pytest.fixture
def limiter() -> WorkflowRateLimiter:
    """Rate limiter with low limits for testing."""
    return WorkflowRateLimiter(max_runs_per_minute=3, max_concurrent_runs=2)


@pytest.mark.asyncio
async def test_allows_runs_under_limit(limiter: WorkflowRateLimiter) -> None:
    """Runs within the per-minute limit should be allowed."""
    for i in range(3):
        allowed, err = await limiter.check_rate_limit("user-1")
        assert allowed is True, f"Run {i} should be allowed"
        assert err is None
        await limiter.record_run_start("user-1", f"run-{i}")
        await limiter.record_run_end("user-1", f"run-{i}")


@pytest.mark.asyncio
async def test_blocks_when_per_minute_exceeded(limiter: WorkflowRateLimiter) -> None:
    """The 4th run within one minute should be rejected."""
    for i in range(3):
        allowed, _ = await limiter.check_rate_limit("user-1")
        assert allowed is True
        await limiter.record_run_start("user-1", f"run-{i}")
        # Runs complete immediately — concurrent slots free
        await limiter.record_run_end("user-1", f"run-{i}")

    # 4th run should hit the per-minute limit
    allowed, err = await limiter.check_rate_limit("user-1")
    assert allowed is False
    assert err is not None
    assert "per minute" in err.lower()


@pytest.mark.asyncio
async def test_blocks_when_concurrent_exceeded(limiter: WorkflowRateLimiter) -> None:
    """Exceeding concurrent run slots should be rejected."""
    # Start 2 runs without ending them
    for i in range(2):
        allowed, _ = await limiter.check_rate_limit("user-1")
        assert allowed is True
        await limiter.record_run_start("user-1", f"run-{i}")

    # 3rd concurrent run should be blocked
    allowed, err = await limiter.check_rate_limit("user-1")
    assert allowed is False
    assert err is not None
    assert "concurrent" in err.lower()


@pytest.mark.asyncio
async def test_per_user_isolation(limiter: WorkflowRateLimiter) -> None:
    """User A's runs should not affect user B's limits."""
    # Fill user-A's concurrent slots
    for i in range(2):
        await limiter.record_run_start("user-a", f"run-a-{i}")

    # User A is blocked
    allowed_a, _ = await limiter.check_rate_limit("user-a")
    assert allowed_a is False

    # User B should still be allowed
    allowed_b, err_b = await limiter.check_rate_limit("user-b")
    assert allowed_b is True
    assert err_b is None


@pytest.mark.asyncio
async def test_run_end_frees_concurrent_slot(limiter: WorkflowRateLimiter) -> None:
    """Completing a run should free up a concurrent slot."""
    # Fill concurrent slots
    await limiter.record_run_start("user-1", "run-0")
    await limiter.record_run_start("user-1", "run-1")

    allowed, _ = await limiter.check_rate_limit("user-1")
    assert allowed is False

    # Complete one run
    await limiter.record_run_end("user-1", "run-0")

    # Now should be allowed again
    allowed, err = await limiter.check_rate_limit("user-1")
    assert allowed is True
    assert err is None


@pytest.mark.asyncio
async def test_sliding_window_expiry(limiter: WorkflowRateLimiter) -> None:
    """Timestamps older than 60 seconds should be evicted."""
    # Inject 3 old timestamps (> 60s ago) by patching time
    old_time = time.time() - 120.0
    with patch("fim_one.core.workflow.rate_limiter.time") as mock_time:
        mock_time.time.return_value = old_time
        for i in range(3):
            await limiter.record_run_start("user-1", f"old-run-{i}")
            await limiter.record_run_end("user-1", f"old-run-{i}")

    # Now at real time, the old timestamps should have expired
    allowed, err = await limiter.check_rate_limit("user-1")
    assert allowed is True
    assert err is None


@pytest.mark.asyncio
async def test_record_run_end_idempotent(limiter: WorkflowRateLimiter) -> None:
    """Calling record_run_end for a non-existent run should not error."""
    # Should not raise
    await limiter.record_run_end("user-1", "nonexistent-run")


@pytest.mark.asyncio
async def test_default_limits() -> None:
    """Default constructor should have sensible limits."""
    limiter = WorkflowRateLimiter()
    assert limiter.max_runs_per_minute == 10
    assert limiter.max_concurrent_runs == 3
