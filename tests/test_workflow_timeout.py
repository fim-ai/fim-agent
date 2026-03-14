"""Tests for workflow global run timeout."""

from __future__ import annotations

import pytest

from fim_one.core.workflow.engine import WorkflowEngine
from fim_one.core.workflow.types import (
    NodeType,
    WorkflowBlueprint,
    WorkflowEdgeDef,
    WorkflowNodeDef,
)


def _make_slow_blueprint(delay_seconds: float = 5.0) -> WorkflowBlueprint:
    """Create a minimal blueprint whose CODE_EXECUTION node sleeps longer than the timeout."""
    return WorkflowBlueprint(
        nodes=[
            WorkflowNodeDef(id="start", type=NodeType.START, data={}),
            WorkflowNodeDef(
                id="slow",
                type=NodeType.CODE_EXECUTION,
                data={
                    "code": f"import time; time.sleep({delay_seconds})",
                    "language": "python",
                },
            ),
            WorkflowNodeDef(id="end", type=NodeType.END, data={}),
        ],
        edges=[
            WorkflowEdgeDef(id="e1", source="start", target="slow"),
            WorkflowEdgeDef(id="e2", source="slow", target="end"),
        ],
    )


def _make_fast_blueprint() -> WorkflowBlueprint:
    """Create a blueprint that completes quickly."""
    return WorkflowBlueprint(
        nodes=[
            WorkflowNodeDef(id="start", type=NodeType.START, data={}),
            WorkflowNodeDef(id="end", type=NodeType.END, data={}),
        ],
        edges=[
            WorkflowEdgeDef(id="e1", source="start", target="end"),
        ],
    )


@pytest.mark.asyncio
async def test_timeout_cancels_workflow() -> None:
    """A workflow exceeding the timeout should emit run_failed with timeout message."""
    engine = WorkflowEngine(
        workflow_timeout_ms=1000,  # 1 second timeout
        run_id="test-run-timeout",
        user_id="test-user",
        workflow_id="test-wf",
    )

    blueprint = _make_slow_blueprint(delay_seconds=10.0)

    events: list[tuple[str, dict]] = []
    async for event_name, event_data in engine.execute_streaming(blueprint):
        events.append((event_name, event_data))

    event_names = [e[0] for e in events]

    # Should have a run_failed event
    assert "run_failed" in event_names, f"Expected run_failed, got: {event_names}"

    # Find the run_failed event
    run_failed_events = [e for e in events if e[0] == "run_failed"]
    assert len(run_failed_events) >= 1

    failed_data = run_failed_events[-1][1]
    assert failed_data["status"] == "failed"
    assert "timed out" in failed_data["error"]


@pytest.mark.asyncio
async def test_partial_results_preserved_on_timeout() -> None:
    """Nodes that completed before timeout should have their events emitted."""
    blueprint = WorkflowBlueprint(
        nodes=[
            WorkflowNodeDef(id="start", type=NodeType.START, data={}),
            WorkflowNodeDef(
                id="fast",
                type=NodeType.CODE_EXECUTION,
                data={"code": "result = 42", "language": "python"},
            ),
            WorkflowNodeDef(
                id="slow",
                type=NodeType.CODE_EXECUTION,
                data={"code": "import time; time.sleep(30)", "language": "python"},
            ),
            WorkflowNodeDef(id="end", type=NodeType.END, data={}),
        ],
        edges=[
            WorkflowEdgeDef(id="e1", source="start", target="fast"),
            WorkflowEdgeDef(id="e2", source="fast", target="slow"),
            WorkflowEdgeDef(id="e3", source="slow", target="end"),
        ],
    )

    engine = WorkflowEngine(
        workflow_timeout_ms=2000,  # 2 second timeout
        run_id="test-partial",
        user_id="test-user",
        workflow_id="test-wf",
    )

    events: list[tuple[str, dict]] = []
    async for event_name, event_data in engine.execute_streaming(blueprint):
        events.append((event_name, event_data))

    event_names = [e[0] for e in events]

    # Start node should have completed
    start_completed = any(
        e[0] == "node_completed" and e[1].get("node_id") == "start"
        for e in events
    )
    assert start_completed, "Start node should have completed before timeout"

    # Should still end with run_failed
    assert "run_failed" in event_names


@pytest.mark.asyncio
async def test_custom_timeout_overrides_default() -> None:
    """When a custom timeout is provided, it should override the default."""
    engine = WorkflowEngine(
        workflow_timeout_ms=1000,  # Custom 1s timeout
        run_id="test-custom-timeout",
        user_id="test-user",
        workflow_id="test-wf",
    )

    blueprint = _make_slow_blueprint(delay_seconds=10.0)

    events: list[tuple[str, dict]] = []
    async for event_name, event_data in engine.execute_streaming(blueprint):
        events.append((event_name, event_data))

    # Should have timed out
    run_failed = [e for e in events if e[0] == "run_failed"]
    assert len(run_failed) >= 1
    assert "timed out" in run_failed[-1][1]["error"]


@pytest.mark.asyncio
async def test_default_timeout() -> None:
    """When no custom timeout is set, the engine uses its default (600s = 600000ms)."""
    engine = WorkflowEngine(
        run_id="test-default",
        user_id="test-user",
        workflow_id="test-wf",
    )
    # Verify the internal default
    assert engine._workflow_timeout_ms == 600_000


@pytest.mark.asyncio
async def test_fast_workflow_completes_normally() -> None:
    """A workflow that finishes before timeout should complete normally."""
    engine = WorkflowEngine(
        workflow_timeout_ms=60_000,
        run_id="test-fast",
        user_id="test-user",
        workflow_id="test-wf",
    )

    blueprint = _make_fast_blueprint()

    events: list[tuple[str, dict]] = []
    async for event_name, event_data in engine.execute_streaming(blueprint):
        events.append((event_name, event_data))

    event_names = [e[0] for e in events]

    # Should complete successfully, no timeout
    assert "run_completed" in event_names
    assert "run_failed" not in event_names
