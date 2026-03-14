"""Tests for the workflow batch-run schemas and execution logic.

Covers:
- WorkflowBatchRunRequest validation (min/max items, max_parallel bounds)
- BatchRunResultItem and WorkflowBatchRunResponse construction
- Concurrent batch execution with semaphore control via the engine
"""

from __future__ import annotations

import asyncio
import pytest
from typing import Any

from pydantic import ValidationError

from fim_one.core.workflow.engine import WorkflowEngine
from fim_one.core.workflow.parser import parse_blueprint
from fim_one.web.schemas.workflow import (
    BatchRunResultItem,
    WorkflowBatchRunRequest,
    WorkflowBatchRunResponse,
)


# ---------------------------------------------------------------------------
# Blueprint helpers (mirrored from test_workflow.py)
# ---------------------------------------------------------------------------


def _start_node(node_id: str = "start_1", **data: Any) -> dict:
    return {
        "id": node_id,
        "type": "start",
        "position": {"x": 0, "y": 0},
        "data": {"type": "START", **data},
    }


def _end_node(node_id: str = "end_1", **data: Any) -> dict:
    return {
        "id": node_id,
        "type": "end",
        "position": {"x": 400, "y": 0},
        "data": {"type": "END", **data},
    }


def _edge(source: str, target: str) -> dict:
    return {"id": f"e-{source}-{target}", "source": source, "target": target}


def _simple_blueprint() -> dict:
    return {
        "nodes": [_start_node(), _end_node()],
        "edges": [_edge("start_1", "end_1")],
        "viewport": {"x": 0, "y": 0, "zoom": 1},
    }


# =========================================================================
# Schema validation tests
# =========================================================================


class TestWorkflowBatchRunRequest:
    def test_valid_request(self):
        req = WorkflowBatchRunRequest(
            inputs=[{"name": "Alice"}, {"name": "Bob"}],
            max_parallel=2,
        )
        assert len(req.inputs) == 2
        assert req.max_parallel == 2

    def test_default_max_parallel(self):
        req = WorkflowBatchRunRequest(inputs=[{"x": 1}])
        assert req.max_parallel == 3

    def test_empty_inputs_rejected(self):
        with pytest.raises(ValidationError, match="too_short"):
            WorkflowBatchRunRequest(inputs=[])

    def test_over_100_inputs_rejected(self):
        with pytest.raises(ValidationError, match="too_long"):
            WorkflowBatchRunRequest(inputs=[{"i": i} for i in range(101)])

    def test_max_parallel_lower_bound(self):
        with pytest.raises(ValidationError):
            WorkflowBatchRunRequest(inputs=[{"x": 1}], max_parallel=0)

    def test_max_parallel_upper_bound(self):
        with pytest.raises(ValidationError):
            WorkflowBatchRunRequest(inputs=[{"x": 1}], max_parallel=11)

    def test_max_parallel_boundary_values(self):
        req1 = WorkflowBatchRunRequest(inputs=[{"x": 1}], max_parallel=1)
        assert req1.max_parallel == 1
        req10 = WorkflowBatchRunRequest(inputs=[{"x": 1}], max_parallel=10)
        assert req10.max_parallel == 10

    def test_exactly_100_inputs_accepted(self):
        req = WorkflowBatchRunRequest(inputs=[{"i": i} for i in range(100)])
        assert len(req.inputs) == 100


class TestBatchRunResultItem:
    def test_successful_result(self):
        item = BatchRunResultItem(
            run_id="run-123",
            inputs={"name": "Alice"},
            status="completed",
            outputs={"result": "ok"},
            duration_ms=150,
        )
        assert item.status == "completed"
        assert item.error is None

    def test_failed_result(self):
        item = BatchRunResultItem(
            run_id="run-456",
            inputs={"name": "Bob"},
            status="failed",
            error="Something broke",
            duration_ms=50,
        )
        assert item.status == "failed"
        assert item.outputs is None


class TestWorkflowBatchRunResponse:
    def test_response_construction(self):
        resp = WorkflowBatchRunResponse(
            batch_id="batch-001",
            total=2,
            results=[
                BatchRunResultItem(
                    run_id="r1",
                    inputs={"a": 1},
                    status="completed",
                    outputs={"out": "x"},
                    duration_ms=100,
                ),
                BatchRunResultItem(
                    run_id="r2",
                    inputs={"a": 2},
                    status="failed",
                    error="timeout",
                    duration_ms=5000,
                ),
            ],
        )
        assert resp.total == 2
        assert len(resp.results) == 2
        assert resp.results[0].status == "completed"
        assert resp.results[1].status == "failed"

    def test_empty_results(self):
        resp = WorkflowBatchRunResponse(
            batch_id="batch-002",
            total=0,
            results=[],
        )
        assert resp.total == 0
        assert resp.results == []


# =========================================================================
# Engine-level batch execution tests
# =========================================================================


class TestBatchExecution:
    """Test running the workflow engine multiple times concurrently,
    mimicking what the batch-run endpoint does."""

    @pytest.mark.asyncio
    async def test_batch_of_simple_blueprints(self):
        """Run a simple Start->End blueprint with 3 different input sets."""
        parsed = parse_blueprint(_simple_blueprint())
        input_sets = [{"name": "Alice"}, {"name": "Bob"}, {"name": "Charlie"}]
        semaphore = asyncio.Semaphore(2)

        async def run_one(inputs: dict[str, Any]) -> dict[str, Any]:
            async with semaphore:
                engine = WorkflowEngine(max_concurrency=5)
                final_status = "completed"
                outputs: dict[str, Any] = {}
                error_msg: str | None = None

                async for event_name, event_data in engine.execute_streaming(
                    parsed, inputs
                ):
                    if event_name == "run_completed":
                        outputs = event_data.get("outputs", {})
                        final_status = event_data.get("status", "completed")
                    elif event_name == "run_failed":
                        final_status = "failed"
                        error_msg = event_data.get("error")

                return {
                    "status": final_status,
                    "outputs": outputs,
                    "error": error_msg,
                }

        tasks = [asyncio.create_task(run_one(inp)) for inp in input_sets]
        results = await asyncio.gather(*tasks)

        assert len(results) == 3
        for result in results:
            assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_batch_isolation(self):
        """Each batch item gets its own engine and variable store."""
        parsed = parse_blueprint(_simple_blueprint())
        input_sets = [{"val": str(i)} for i in range(5)]

        results = []

        async def run_one(inputs: dict[str, Any]) -> str:
            engine = WorkflowEngine(max_concurrency=5)
            async for event_name, _ in engine.execute_streaming(parsed, inputs):
                if event_name == "run_completed":
                    return "completed"
                elif event_name == "run_failed":
                    return "failed"
            return "unknown"

        tasks = [asyncio.create_task(run_one(inp)) for inp in input_sets]
        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        assert all(r == "completed" for r in results)
