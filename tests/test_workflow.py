"""Tests for the workflow execution engine core components.

Covers: parser (validation, topo sort), variable store (interpolation,
snapshot_safe), and engine (linear execution, condition branching, error
strategies, cancellation).
"""

from __future__ import annotations

import asyncio
import json
import pytest
from typing import Any

from fim_one.core.workflow.parser import (
    BlueprintValidationError,
    parse_blueprint,
    topological_sort,
)
from fim_one.core.workflow.types import (
    ErrorStrategy,
    ExecutionContext,
    NodeResult,
    NodeStatus,
    NodeType,
    WorkflowBlueprint,
    WorkflowEdgeDef,
    WorkflowNodeDef,
)
from fim_one.core.workflow.variable_store import VariableStore
from fim_one.core.workflow.engine import WorkflowEngine


# ---------------------------------------------------------------------------
# Fixtures: reusable blueprint builders
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


def _llm_node(node_id: str = "llm_1", **data: Any) -> dict:
    return {
        "id": node_id,
        "type": "llm",
        "position": {"x": 200, "y": 0},
        "data": {"type": "LLM", "prompt": "Hello {{input.name}}", **data},
    }


def _condition_node(node_id: str = "cond_1", **data: Any) -> dict:
    return {
        "id": node_id,
        "type": "conditionBranch",
        "position": {"x": 200, "y": 0},
        "data": {
            "type": "CONDITION_BRANCH",
            "conditions": [
                {"handle": "yes", "expression": "score > 50"},
            ],
            "default_handle": "no",
            **data,
        },
    }


def _edge(source: str, target: str, source_handle: str | None = None) -> dict:
    eid = f"e-{source}-{target}"
    edge: dict[str, Any] = {"id": eid, "source": source, "target": target}
    if source_handle:
        edge["sourceHandle"] = source_handle
    return edge


def _simple_blueprint() -> dict:
    """Start → End, the simplest valid blueprint."""
    return {
        "nodes": [_start_node(), _end_node()],
        "edges": [_edge("start_1", "end_1")],
        "viewport": {"x": 0, "y": 0, "zoom": 1},
    }


# =========================================================================
# Parser tests
# =========================================================================


class TestParser:
    def test_parse_simple_blueprint(self):
        bp = parse_blueprint(_simple_blueprint())
        assert len(bp.nodes) == 2
        assert len(bp.edges) == 1
        assert bp.nodes[0].type == NodeType.START
        assert bp.nodes[1].type == NodeType.END

    def test_missing_start_node(self):
        raw = {
            "nodes": [_end_node()],
            "edges": [],
        }
        with pytest.raises(BlueprintValidationError, match="Start node"):
            parse_blueprint(raw)

    def test_missing_end_node(self):
        raw = {
            "nodes": [_start_node()],
            "edges": [],
        }
        with pytest.raises(BlueprintValidationError, match="End node"):
            parse_blueprint(raw)

    def test_duplicate_start_node(self):
        raw = {
            "nodes": [_start_node("s1"), _start_node("s2"), _end_node()],
            "edges": [],
        }
        with pytest.raises(BlueprintValidationError, match="exactly 1"):
            parse_blueprint(raw)

    def test_duplicate_node_id(self):
        raw = {
            "nodes": [
                _start_node("dup"),
                {"id": "dup", "type": "end", "data": {"type": "END"}},
            ],
            "edges": [],
        }
        with pytest.raises(BlueprintValidationError, match="Duplicate"):
            parse_blueprint(raw)

    def test_unknown_node_type(self):
        raw = {
            "nodes": [
                _start_node(),
                {"id": "x", "type": "banana", "data": {"type": "BANANA"}},
                _end_node(),
            ],
            "edges": [],
        }
        with pytest.raises(BlueprintValidationError, match="Unknown node type"):
            parse_blueprint(raw)

    def test_edge_references_unknown_node(self):
        raw = {
            "nodes": [_start_node(), _end_node()],
            "edges": [_edge("start_1", "ghost")],
        }
        with pytest.raises(BlueprintValidationError, match="unknown node"):
            parse_blueprint(raw)

    def test_cycle_detection(self):
        raw = {
            "nodes": [
                _start_node(),
                _llm_node("a"),
                _llm_node("b"),
                _end_node(),
            ],
            "edges": [
                _edge("start_1", "a"),
                _edge("a", "b"),
                _edge("b", "a"),  # creates a cycle
                _edge("b", "end_1"),
            ],
        }
        with pytest.raises(BlueprintValidationError, match="cycle"):
            parse_blueprint(raw)

    def test_no_nodes(self):
        with pytest.raises(BlueprintValidationError, match="no nodes"):
            parse_blueprint({"nodes": [], "edges": []})

    def test_error_strategy_parsing(self):
        raw = {
            "nodes": [
                _start_node(),
                {
                    "id": "llm_1",
                    "type": "llm",
                    "data": {
                        "type": "LLM",
                        "error_strategy": "CONTINUE",
                    },
                },
                _end_node(),
            ],
            "edges": [_edge("start_1", "llm_1"), _edge("llm_1", "end_1")],
        }
        bp = parse_blueprint(raw)
        llm_node = next(n for n in bp.nodes if n.type == NodeType.LLM)
        assert llm_node.error_strategy == ErrorStrategy.CONTINUE

    def test_timeout_parsing(self):
        raw = {
            "nodes": [
                _start_node(),
                {
                    "id": "llm_1",
                    "type": "llm",
                    "data": {"type": "LLM", "timeout_ms": 60000},
                },
                _end_node(),
            ],
            "edges": [_edge("start_1", "llm_1"), _edge("llm_1", "end_1")],
        }
        bp = parse_blueprint(raw)
        llm_node = next(n for n in bp.nodes if n.type == NodeType.LLM)
        assert llm_node.timeout_ms == 60000


class TestTopologicalSort:
    def test_linear_order(self):
        bp = parse_blueprint({
            "nodes": [_start_node(), _llm_node("a"), _end_node()],
            "edges": [_edge("start_1", "a"), _edge("a", "end_1")],
        })
        order = topological_sort(bp)
        assert order.index("start_1") < order.index("a")
        assert order.index("a") < order.index("end_1")

    def test_parallel_branches(self):
        """Two parallel nodes should both appear between start and end."""
        bp = parse_blueprint({
            "nodes": [
                _start_node(),
                _llm_node("a"),
                _llm_node("b"),
                _end_node(),
            ],
            "edges": [
                _edge("start_1", "a"),
                _edge("start_1", "b"),
                _edge("a", "end_1"),
                _edge("b", "end_1"),
            ],
        })
        order = topological_sort(bp)
        assert order[0] == "start_1"
        assert set(order[1:3]) == {"a", "b"}
        assert order[-1] == "end_1"


# =========================================================================
# VariableStore tests
# =========================================================================


class TestVariableStore:
    @pytest.mark.asyncio
    async def test_set_and_get(self):
        store = VariableStore()
        await store.set("x", 42)
        assert await store.get("x") == 42

    @pytest.mark.asyncio
    async def test_get_default(self):
        store = VariableStore()
        assert await store.get("missing", "default") == "default"

    @pytest.mark.asyncio
    async def test_interpolate_simple(self):
        store = VariableStore()
        await store.set("input.name", "Alice")
        result = await store.interpolate("Hello {{input.name}}!")
        assert result == "Hello Alice!"

    @pytest.mark.asyncio
    async def test_interpolate_flat_fallback(self):
        """Flat variable name matches last segment of dotted key."""
        store = VariableStore()
        await store.set("llm_1.output", "result text")
        result = await store.interpolate("Got: {{output}}")
        assert result == "Got: result text"

    @pytest.mark.asyncio
    async def test_interpolate_unknown_kept(self):
        store = VariableStore()
        result = await store.interpolate("{{unknown_var}}")
        assert result == "{{unknown_var}}"

    @pytest.mark.asyncio
    async def test_interpolate_non_string_json(self):
        store = VariableStore()
        await store.set("data", {"key": "value"})
        result = await store.interpolate("Result: {{data}}")
        assert '"key"' in result
        assert '"value"' in result

    @pytest.mark.asyncio
    async def test_env_vars_injection(self):
        store = VariableStore(env_vars={"API_KEY": "secret123"})
        assert await store.get("env.API_KEY") == "secret123"

    @pytest.mark.asyncio
    async def test_snapshot_safe_excludes_env(self):
        store = VariableStore(env_vars={"SECRET": "hidden"})
        await store.set("visible", "ok")
        safe = await store.snapshot_safe()
        assert "visible" in safe
        assert "env.SECRET" not in safe

    @pytest.mark.asyncio
    async def test_snapshot_includes_env(self):
        store = VariableStore(env_vars={"SECRET": "hidden"})
        full = await store.snapshot()
        assert "env.SECRET" in full

    @pytest.mark.asyncio
    async def test_set_many(self):
        store = VariableStore()
        await store.set_many({"a": 1, "b": 2})
        assert await store.get("a") == 1
        assert await store.get("b") == 2

    @pytest.mark.asyncio
    async def test_get_node_outputs(self):
        store = VariableStore()
        await store.set("llm_1.output", "text")
        await store.set("llm_1.tokens", 150)
        await store.set("other.val", "x")
        outputs = await store.get_node_outputs("llm_1")
        assert outputs == {"output": "text", "tokens": 150}
        assert "val" not in outputs

    @pytest.mark.asyncio
    async def test_list_available_variables(self):
        store = VariableStore(env_vars={"K": "V"})
        await store.set("input.q", "query")
        await store.set("llm_1.output", "answer")
        variables = await store.list_available_variables()
        # Should exclude env.* and input.*
        names = [v["var_name"] for v in variables]
        assert "output" in names
        assert "q" not in names


# =========================================================================
# Engine tests (unit-level, with mocked executors)
# =========================================================================


class TestEngineLinear:
    """Test engine with Start → End (no LLM calls needed)."""

    @pytest.mark.asyncio
    async def test_start_to_end_execution(self):
        """Simplest workflow: Start → End should complete successfully."""
        raw = _simple_blueprint()
        parsed = parse_blueprint(raw)

        engine = WorkflowEngine(
            run_id="test-run-1",
            user_id="test-user",
            workflow_id="test-wf",
        )

        events: list[tuple[str, dict]] = []
        async for event_name, event_data in engine.execute_streaming(
            parsed, inputs={"greeting": "hello"}
        ):
            events.append((event_name, event_data))

        event_types = [e[0] for e in events]
        assert "run_started" in event_types or "node_started" in event_types
        # Should have node_started and node_completed for both nodes
        started_nodes = [
            e[1]["node_id"] for e in events if e[0] == "node_started"
        ]
        completed_nodes = [
            e[1]["node_id"] for e in events if e[0] == "node_completed"
        ]
        assert "start_1" in started_nodes
        assert "start_1" in completed_nodes

    @pytest.mark.asyncio
    async def test_inputs_available_in_store(self):
        """Verify that inputs are passed through Start node to downstream."""
        raw = {
            "nodes": [
                _start_node(),
                _end_node(output_mapping={"result": "{{start_1.name}}"}),
            ],
            "edges": [_edge("start_1", "end_1")],
        }
        parsed = parse_blueprint(raw)

        engine = WorkflowEngine(run_id="r", user_id="u", workflow_id="w")

        events: list[tuple[str, dict]] = []
        async for event_name, event_data in engine.execute_streaming(
            parsed, inputs={"name": "World"}
        ):
            events.append((event_name, event_data))

        # End node should complete
        completed_events = [
            e for e in events if e[0] == "node_completed" and e[1].get("node_id") == "end_1"
        ]
        assert len(completed_events) == 1


class TestEngineCancellation:
    @pytest.mark.asyncio
    async def test_cancel_stops_execution(self):
        """Cancelling mid-run should skip remaining nodes."""
        raw = {
            "nodes": [
                _start_node(),
                _llm_node("a"),  # This will fail (no LLM configured) but tests cancel path
                _end_node(),
            ],
            "edges": [_edge("start_1", "a"), _edge("a", "end_1")],
        }
        parsed = parse_blueprint(raw)

        cancel = asyncio.Event()
        engine = WorkflowEngine(
            cancel_event=cancel,
            run_id="r",
            user_id="u",
            workflow_id="w",
        )

        events: list[tuple[str, dict]] = []

        async def collect():
            async for event_name, event_data in engine.execute_streaming(
                parsed, inputs={}
            ):
                events.append((event_name, event_data))
                # Cancel after the first node starts
                if event_name == "node_started":
                    cancel.set()

        # Should complete (not hang)
        await asyncio.wait_for(collect(), timeout=10.0)


class TestEngineErrorStrategies:
    @pytest.mark.asyncio
    async def test_default_stop_workflow(self):
        """Default STOP_WORKFLOW: a failed node should skip all remaining."""
        raw = {
            "nodes": [
                _start_node(),
                {
                    "id": "code_1",
                    "type": "codeExecution",
                    "data": {
                        "type": "CODE_EXECUTION",
                        "code": "raise ValueError('boom')",
                    },
                },
                _end_node(),
            ],
            "edges": [_edge("start_1", "code_1"), _edge("code_1", "end_1")],
        }
        parsed = parse_blueprint(raw)
        engine = WorkflowEngine(run_id="r", user_id="u", workflow_id="w")

        events: list[tuple[str, dict]] = []
        async for event_name, event_data in engine.execute_streaming(parsed):
            events.append((event_name, event_data))

        event_types = [e[0] for e in events]
        assert "node_failed" in event_types
        # End node should be skipped due to STOP_WORKFLOW
        skipped = [e for e in events if e[0] == "node_skipped"]
        skipped_ids = [e[1]["node_id"] for e in skipped]
        assert "end_1" in skipped_ids

    @pytest.mark.asyncio
    async def test_continue_strategy(self):
        """CONTINUE strategy: failed node doesn't block downstream."""
        raw = {
            "nodes": [
                _start_node(),
                {
                    "id": "code_1",
                    "type": "codeExecution",
                    "data": {
                        "type": "CODE_EXECUTION",
                        "code": "raise ValueError('boom')",
                        "error_strategy": "CONTINUE",
                    },
                },
                _end_node(),
            ],
            "edges": [_edge("start_1", "code_1"), _edge("code_1", "end_1")],
        }
        parsed = parse_blueprint(raw)
        engine = WorkflowEngine(run_id="r", user_id="u", workflow_id="w")

        events: list[tuple[str, dict]] = []
        async for event_name, event_data in engine.execute_streaming(parsed):
            events.append((event_name, event_data))

        event_types = [e[0] for e in events]
        assert "node_failed" in event_types
        # End node should still run (not skipped)
        end_started = any(
            e[0] == "node_started" and e[1].get("node_id") == "end_1"
            for e in events
        )
        assert end_started, "End node should still run with CONTINUE strategy"


class TestVariableAssignNode:
    @pytest.mark.asyncio
    async def test_variable_assign_execution(self):
        """VariableAssign node should set variables in the store."""
        raw = {
            "nodes": [
                _start_node(),
                {
                    "id": "va_1",
                    "type": "variableAssign",
                    "data": {
                        "type": "VARIABLE_ASSIGN",
                        "assignments": [
                            {"variable": "greeting", "value": "hello"},
                        ],
                    },
                },
                _end_node(output_mapping={"msg": "{{va_1.greeting}}"}),
            ],
            "edges": [_edge("start_1", "va_1"), _edge("va_1", "end_1")],
        }
        parsed = parse_blueprint(raw)
        engine = WorkflowEngine(run_id="r", user_id="u", workflow_id="w")

        events: list[tuple[str, dict]] = []
        async for event_name, event_data in engine.execute_streaming(parsed):
            events.append((event_name, event_data))

        # VariableAssign should complete
        va_completed = any(
            e[0] == "node_completed" and e[1].get("node_id") == "va_1"
            for e in events
        )
        assert va_completed


class TestCodeExecutionNode:
    @pytest.mark.asyncio
    async def test_simple_code_execution(self):
        """Code execution should run Python and capture output."""
        raw = {
            "nodes": [
                _start_node(),
                {
                    "id": "code_1",
                    "type": "codeExecution",
                    "data": {
                        "type": "CODE_EXECUTION",
                        "code": "result = 2 + 3",
                    },
                },
                _end_node(),
            ],
            "edges": [_edge("start_1", "code_1"), _edge("code_1", "end_1")],
        }
        parsed = parse_blueprint(raw)
        engine = WorkflowEngine(run_id="r", user_id="u", workflow_id="w")

        events: list[tuple[str, dict]] = []
        async for event_name, event_data in engine.execute_streaming(parsed):
            events.append((event_name, event_data))

        code_completed = [
            e for e in events
            if e[0] == "node_completed" and e[1].get("node_id") == "code_1"
        ]
        assert len(code_completed) == 1
        # The output should contain "5"
        assert "5" in str(code_completed[0][1].get("output_preview", ""))

    @pytest.mark.asyncio
    async def test_code_with_variables(self):
        """Code execution should have access to workflow variables."""
        raw = {
            "nodes": [
                _start_node(),
                {
                    "id": "code_1",
                    "type": "codeExecution",
                    "data": {
                        "type": "CODE_EXECUTION",
                        "code": "result = variables.get('input.name', 'unknown')",
                    },
                },
                _end_node(),
            ],
            "edges": [_edge("start_1", "code_1"), _edge("code_1", "end_1")],
        }
        parsed = parse_blueprint(raw)
        engine = WorkflowEngine(run_id="r", user_id="u", workflow_id="w")

        events: list[tuple[str, dict]] = []
        async for event_name, event_data in engine.execute_streaming(
            parsed, inputs={"name": "TestUser"}
        ):
            events.append((event_name, event_data))

        code_completed = [
            e for e in events
            if e[0] == "node_completed" and e[1].get("node_id") == "code_1"
        ]
        assert len(code_completed) == 1

    @pytest.mark.asyncio
    async def test_code_error_returns_failed(self):
        """Code with a syntax error should produce a failed node result."""
        raw = {
            "nodes": [
                _start_node(),
                {
                    "id": "code_1",
                    "type": "codeExecution",
                    "data": {
                        "type": "CODE_EXECUTION",
                        "code": "this is not valid python!!!",
                        "error_strategy": "CONTINUE",
                    },
                },
                _end_node(),
            ],
            "edges": [_edge("start_1", "code_1"), _edge("code_1", "end_1")],
        }
        parsed = parse_blueprint(raw)
        engine = WorkflowEngine(run_id="r", user_id="u", workflow_id="w")

        events: list[tuple[str, dict]] = []
        async for event_name, event_data in engine.execute_streaming(parsed):
            events.append((event_name, event_data))

        code_failed = [
            e for e in events
            if e[0] == "node_failed" and e[1].get("node_id") == "code_1"
        ]
        assert len(code_failed) == 1
        assert "error" in code_failed[0][1]
