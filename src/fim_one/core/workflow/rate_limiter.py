"""Per-user workflow run rate limiting.

Provides an in-memory sliding-window rate limiter that enforces both
runs-per-minute and concurrent-run limits on a per-user basis.
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque


class WorkflowRateLimiter:
    """In-memory sliding window rate limiter for workflow executions.

    Parameters
    ----------
    max_runs_per_minute:
        Maximum number of workflow runs a single user can start within
        a rolling 60-second window.
    max_concurrent_runs:
        Maximum number of simultaneously active runs per user.
    """

    def __init__(
        self,
        max_runs_per_minute: int = 10,
        max_concurrent_runs: int = 3,
    ) -> None:
        self.max_runs_per_minute = max_runs_per_minute
        self.max_concurrent_runs = max_concurrent_runs

        # user_id -> deque of timestamps (newest at right)
        self._run_timestamps: dict[str, deque[float]] = defaultdict(deque)

        # user_id -> set of currently active run_ids
        self._active_runs: dict[str, set[str]] = defaultdict(set)

        self._lock = asyncio.Lock()

    async def check_rate_limit(self, user_id: str) -> tuple[bool, str | None]:
        """Check whether the user is allowed to start a new run.

        Returns
        -------
        tuple[bool, str | None]
            ``(True, None)`` if allowed, ``(False, error_message)`` if denied.
        """
        async with self._lock:
            now = time.time()

            # --- concurrent run check ---
            active = self._active_runs.get(user_id, set())
            if len(active) >= self.max_concurrent_runs:
                return (
                    False,
                    f"Too many concurrent workflow runs. "
                    f"Maximum is {self.max_concurrent_runs} simultaneous runs.",
                )

            # --- sliding window check ---
            timestamps = self._run_timestamps[user_id]
            cutoff = now - 60.0

            # Evict expired entries
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()

            if len(timestamps) >= self.max_runs_per_minute:
                return (
                    False,
                    f"Rate limit exceeded. Maximum is "
                    f"{self.max_runs_per_minute} workflow runs per minute.",
                )

            return (True, None)

    async def record_run_start(self, user_id: str, run_id: str) -> None:
        """Record that a workflow run has started."""
        async with self._lock:
            self._run_timestamps[user_id].append(time.time())
            self._active_runs[user_id].add(run_id)

    async def record_run_end(self, user_id: str, run_id: str) -> None:
        """Record that a workflow run has completed (any final status)."""
        async with self._lock:
            self._active_runs[user_id].discard(run_id)
