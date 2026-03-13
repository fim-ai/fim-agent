"""Tests for the workflow analytics endpoint helper and schema."""

from __future__ import annotations

import math

import pytest

from fim_one.web.api.workflows import _percentile
from fim_one.web.schemas.workflow import (
    MostFailedNode,
    RunsPerDay,
    WorkflowAnalyticsResponse,
)


# ---------------------------------------------------------------------------
# _percentile helper
# ---------------------------------------------------------------------------


class TestPercentile:
    """Tests for the nearest-rank percentile helper."""

    def test_single_element(self):
        assert _percentile([100], 50) == 100
        assert _percentile([100], 95) == 100
        assert _percentile([100], 99) == 100

    def test_two_elements(self):
        assert _percentile([10, 20], 50) == 10
        assert _percentile([10, 20], 99) == 20

    def test_ten_elements(self):
        vals = list(range(1, 11))  # [1..10]
        assert _percentile(vals, 50) == 5
        assert _percentile(vals, 90) == 9
        assert _percentile(vals, 95) == 10
        assert _percentile(vals, 99) == 10

    def test_hundred_elements(self):
        vals = list(range(1, 101))  # [1..100]
        assert _percentile(vals, 50) == 50
        assert _percentile(vals, 95) == 95
        assert _percentile(vals, 99) == 99

    def test_p0_returns_first(self):
        """Edge case: 0th percentile should return the minimum."""
        vals = [5, 10, 15]
        # ceil(0/100 * 3) - 1 = -1, clamped to 0
        assert _percentile(vals, 0) == 5

    def test_p100_returns_last(self):
        """100th percentile should return the maximum."""
        vals = [5, 10, 15]
        assert _percentile(vals, 100) == 15


# ---------------------------------------------------------------------------
# WorkflowAnalyticsResponse schema
# ---------------------------------------------------------------------------


class TestAnalyticsSchema:
    """Tests for the analytics response Pydantic model."""

    def test_minimal_zero_runs(self):
        resp = WorkflowAnalyticsResponse(
            total_runs=0,
            status_distribution={},
        )
        assert resp.total_runs == 0
        assert resp.success_rate is None
        assert resp.avg_duration_ms is None
        assert resp.p50_duration_ms is None
        assert resp.p95_duration_ms is None
        assert resp.p99_duration_ms is None
        assert resp.runs_per_day == []
        assert resp.most_failed_nodes == []
        assert resp.avg_nodes_per_run is None

    def test_full_response(self):
        resp = WorkflowAnalyticsResponse(
            total_runs=42,
            status_distribution={"completed": 35, "failed": 5, "cancelled": 2},
            success_rate=87.5,
            avg_duration_ms=1234,
            p50_duration_ms=1100,
            p95_duration_ms=3500,
            p99_duration_ms=5000,
            runs_per_day=[
                RunsPerDay(date="2026-03-10", count=5, completed=4, failed=1),
                RunsPerDay(date="2026-03-11", count=8, completed=7, failed=1),
            ],
            most_failed_nodes=[
                MostFailedNode(node_id="llm_1", failure_count=3, total_runs=42),
            ],
            avg_nodes_per_run=8.5,
        )
        data = resp.model_dump()
        assert data["total_runs"] == 42
        assert data["status_distribution"]["completed"] == 35
        assert data["success_rate"] == 87.5
        assert len(data["runs_per_day"]) == 2
        assert data["runs_per_day"][0]["date"] == "2026-03-10"
        assert len(data["most_failed_nodes"]) == 1
        assert data["most_failed_nodes"][0]["node_id"] == "llm_1"
        assert data["avg_nodes_per_run"] == 8.5

    def test_runs_per_day_defaults(self):
        rpd = RunsPerDay(date="2026-03-14", count=10)
        assert rpd.completed == 0
        assert rpd.failed == 0

    def test_model_dump_roundtrip(self):
        """Ensure the model can be serialized and deserialized."""
        original = WorkflowAnalyticsResponse(
            total_runs=1,
            status_distribution={"completed": 1},
            success_rate=100.0,
            avg_duration_ms=500,
            p50_duration_ms=500,
            p95_duration_ms=500,
            p99_duration_ms=500,
            runs_per_day=[RunsPerDay(date="2026-03-14", count=1, completed=1, failed=0)],
            most_failed_nodes=[],
            avg_nodes_per_run=3.0,
        )
        data = original.model_dump()
        restored = WorkflowAnalyticsResponse(**data)
        assert restored == original
