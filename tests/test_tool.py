"""Tests for the Tool system (protocol, registry, built-in tools)."""

from __future__ import annotations

from typing import Any

import pytest

from fim_one.core.tool import BaseTool, Tool, ToolRegistry
from fim_one.core.tool.builtin.python_exec import PythonExecTool

from .conftest import EchoTool


# ======================================================================
# Tool protocol compliance
# ======================================================================


class TestToolProtocol:
    """Verify that concrete tools satisfy the ``Tool`` runtime protocol."""

    def test_echo_tool_is_tool_instance(self) -> None:
        assert isinstance(EchoTool(), Tool)

    def test_python_exec_tool_is_tool_instance(self) -> None:
        assert isinstance(PythonExecTool(), Tool)

    def test_plain_object_is_not_tool(self) -> None:
        assert not isinstance(object(), Tool)

    def test_incomplete_tool_not_protocol(self) -> None:
        """A class missing required attributes should not pass the check."""

        class Incomplete:
            @property
            def name(self) -> str:
                return "incomplete"

        assert not isinstance(Incomplete(), Tool)

    def test_custom_tool_properties(self) -> None:
        tool = EchoTool()
        assert tool.name == "echo"
        assert tool.description == "Echoes the input text back."
        assert "text" in tool.parameters_schema["properties"]


# ======================================================================
# ToolRegistry
# ======================================================================


class TestToolRegistry:
    """Tests for ``ToolRegistry`` CRUD and serialisation."""

    def test_register_and_get(self, tool_registry: ToolRegistry) -> None:
        tool = tool_registry.get("echo")
        assert tool is not None
        assert tool.name == "echo"

    def test_get_returns_none_for_unknown(self, tool_registry: ToolRegistry) -> None:
        assert tool_registry.get("nonexistent") is None

    def test_list_tools(self, tool_registry: ToolRegistry) -> None:
        tools = tool_registry.list_tools()
        assert len(tools) == 1
        assert tools[0].name == "echo"

    def test_len(self, tool_registry: ToolRegistry) -> None:
        assert len(tool_registry) == 1

    def test_contains(self, tool_registry: ToolRegistry) -> None:
        assert "echo" in tool_registry
        assert "missing" not in tool_registry

    def test_repr(self, tool_registry: ToolRegistry) -> None:
        assert "echo" in repr(tool_registry)

    def test_duplicate_registration_raises(self, tool_registry: ToolRegistry) -> None:
        with pytest.raises(ValueError, match="already registered"):
            tool_registry.register(EchoTool())

    def test_unregister(self, tool_registry: ToolRegistry) -> None:
        tool_registry.unregister("echo")
        assert tool_registry.get("echo") is None
        assert len(tool_registry) == 0

    def test_unregister_unknown_raises(self, tool_registry: ToolRegistry) -> None:
        with pytest.raises(KeyError, match="not registered"):
            tool_registry.unregister("ghost")

    def test_to_openai_tools_format(self, tool_registry: ToolRegistry) -> None:
        openai_tools = tool_registry.to_openai_tools()
        assert len(openai_tools) == 1

        tool_def = openai_tools[0]
        assert tool_def["type"] == "function"
        assert tool_def["function"]["name"] == "echo"
        assert tool_def["function"]["description"] == "Echoes the input text back."
        assert "properties" in tool_def["function"]["parameters"]

    def test_to_openai_tools_empty_registry(self) -> None:
        registry = ToolRegistry()
        assert registry.to_openai_tools() == []

    def test_register_multiple_tools(self) -> None:
        registry = ToolRegistry()
        registry.register(EchoTool())
        registry.register(PythonExecTool())
        assert len(registry) == 2
        names = {t.name for t in registry.list_tools()}
        assert names == {"echo", "python_exec"}

    def test_re_register_after_unregister(self) -> None:
        registry = ToolRegistry()
        registry.register(EchoTool())
        registry.unregister("echo")
        registry.register(EchoTool())  # Should not raise
        assert registry.get("echo") is not None


# ======================================================================
# PythonExecTool
# ======================================================================


class TestPythonExecTool:
    """Tests for the built-in ``PythonExecTool``."""

    @pytest.fixture()
    def python_tool(self) -> PythonExecTool:
        return PythonExecTool(timeout=5)

    def test_tool_properties(self, python_tool: PythonExecTool) -> None:
        assert python_tool.name == "python_exec"
        assert "Execute Python code" in python_tool.description
        assert "code" in python_tool.parameters_schema["properties"]

    async def test_basic_print(self, python_tool: PythonExecTool) -> None:
        result = await python_tool.run(code='print("hello")')
        assert "hello" in result
        # Output now includes a [Script: ...] prefix line
        assert result.strip().endswith("hello")

    async def test_multiline_code(self, python_tool: PythonExecTool) -> None:
        code = "x = 2 + 3\nprint(x)"
        result = await python_tool.run(code=code)
        assert "5" in result
        assert result.strip().endswith("5")

    async def test_exception_handling(self, python_tool: PythonExecTool) -> None:
        result = await python_tool.run(code="raise ValueError('boom')")
        assert "ValueError" in result
        assert "boom" in result

    async def test_syntax_error(self, python_tool: PythonExecTool) -> None:
        result = await python_tool.run(code="def foo(")
        assert "SyntaxError" in result

    async def test_empty_code(self, python_tool: PythonExecTool) -> None:
        result = await python_tool.run(code="")
        assert result == ""

    async def test_whitespace_only_code(self, python_tool: PythonExecTool) -> None:
        result = await python_tool.run(code="   \n  ")
        assert result == ""

    async def test_no_code_kwarg(self, python_tool: PythonExecTool) -> None:
        result = await python_tool.run()
        assert result == ""

    async def test_timeout_protection(self) -> None:
        """Code that runs longer than the timeout should be stopped."""
        tool = PythonExecTool(timeout=1)
        result = await tool.run(code="import time; time.sleep(10)")
        assert "Timeout" in result

    async def test_no_output(self, python_tool: PythonExecTool) -> None:
        """Code that produces no output should return the script prefix only."""
        result = await python_tool.run(code="x = 42")
        # Output now includes a [Script: ...] prefix even with no printed output
        assert "[Script:" in result or result == ""
