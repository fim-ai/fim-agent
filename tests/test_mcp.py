"""Tests for the MCP (Model Context Protocol) client integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock

import pytest

from fim_agent.core.mcp.adapter import MCPToolAdapter
from fim_agent.core.mcp.client import MCPClient
from fim_agent.core.tool import Tool, ToolRegistry


# ---------------------------------------------------------------------------
# Fake MCP result types for testing the adapter
# ---------------------------------------------------------------------------


@dataclass
class FakeTextContent:
    type: str = "text"
    text: str = "hello world"


@dataclass
class FakeBinaryContent:
    type: str = "image"
    data: bytes = b"\x89PNG"


@dataclass
class FakeCallToolResult:
    content: list[Any] = field(default_factory=lambda: [FakeTextContent()])
    isError: bool = False


# ======================================================================
# MCPToolAdapter
# ======================================================================


class TestMCPToolAdapter:
    """Tests for the ``MCPToolAdapter`` class."""

    @pytest.fixture()
    def mock_call_fn(self) -> AsyncMock:
        call_fn = AsyncMock()
        call_fn.return_value = FakeCallToolResult()
        return call_fn

    @pytest.fixture()
    def adapter(self, mock_call_fn: AsyncMock) -> MCPToolAdapter:
        return MCPToolAdapter(
            server_name="test_server",
            tool_def={
                "name": "read_file",
                "description": "Read a file from disk.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path."},
                    },
                    "required": ["path"],
                },
            },
            call_fn=mock_call_fn,
        )

    def test_name_is_prefixed(self, adapter: MCPToolAdapter) -> None:
        assert adapter.name == "test_server__read_file"

    def test_description(self, adapter: MCPToolAdapter) -> None:
        assert adapter.description == "Read a file from disk."

    def test_parameters_schema(self, adapter: MCPToolAdapter) -> None:
        schema = adapter.parameters_schema
        assert schema["type"] == "object"
        assert "path" in schema["properties"]

    def test_implements_tool_protocol(self, adapter: MCPToolAdapter) -> None:
        assert isinstance(adapter, Tool)

    async def test_run_calls_mcp_server(
        self, adapter: MCPToolAdapter, mock_call_fn: AsyncMock
    ) -> None:
        result = await adapter.run(path="/tmp/test.txt")
        mock_call_fn.assert_awaited_once_with("read_file", {"path": "/tmp/test.txt"})
        assert result == "hello world"

    async def test_run_with_error_result(
        self, adapter: MCPToolAdapter, mock_call_fn: AsyncMock
    ) -> None:
        mock_call_fn.return_value = FakeCallToolResult(
            content=[FakeTextContent(text="file not found")],
            isError=True,
        )
        result = await adapter.run(path="/nonexistent")
        assert result.startswith("[MCP Error]")
        assert "file not found" in result

    async def test_run_with_binary_content(
        self, adapter: MCPToolAdapter, mock_call_fn: AsyncMock
    ) -> None:
        mock_call_fn.return_value = FakeCallToolResult(
            content=[FakeBinaryContent()],
            isError=False,
        )
        result = await adapter.run(path="/image.png")
        assert "[image:" in result
        assert "bytes]" in result

    async def test_run_with_mixed_content(
        self, adapter: MCPToolAdapter, mock_call_fn: AsyncMock
    ) -> None:
        mock_call_fn.return_value = FakeCallToolResult(
            content=[
                FakeTextContent(text="line 1"),
                FakeTextContent(text="line 2"),
            ],
            isError=False,
        )
        result = await adapter.run(path="/multi.txt")
        assert "line 1" in result
        assert "line 2" in result
        assert result == "line 1\nline 2"

    async def test_run_with_empty_content(
        self, adapter: MCPToolAdapter, mock_call_fn: AsyncMock
    ) -> None:
        mock_call_fn.return_value = FakeCallToolResult(content=[], isError=False)
        result = await adapter.run(path="/empty")
        assert result == ""

    def test_default_schema_when_missing(self, mock_call_fn: AsyncMock) -> None:
        adapter = MCPToolAdapter(
            server_name="s",
            tool_def={"name": "bare_tool"},
            call_fn=mock_call_fn,
        )
        assert adapter.parameters_schema == {"type": "object", "properties": {}}

    def test_default_description_when_missing(self, mock_call_fn: AsyncMock) -> None:
        adapter = MCPToolAdapter(
            server_name="s",
            tool_def={"name": "bare_tool"},
            call_fn=mock_call_fn,
        )
        assert adapter.description == ""

    def test_repr(self, adapter: MCPToolAdapter) -> None:
        r = repr(adapter)
        assert "test_server__read_file" in r
        assert "read_file" in r


# ======================================================================
# MCPToolAdapter + ToolRegistry integration
# ======================================================================


class TestMCPToolRegistryIntegration:
    """Verify MCP tool adapters integrate correctly with the ToolRegistry."""

    async def test_register_and_lookup(self) -> None:
        call_fn = AsyncMock(return_value=FakeCallToolResult())
        adapter = MCPToolAdapter(
            server_name="fs",
            tool_def={
                "name": "list_dir",
                "description": "List directory contents.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                },
            },
            call_fn=call_fn,
        )
        registry = ToolRegistry()
        registry.register(adapter)

        assert "fs__list_dir" in registry
        tool = registry.get("fs__list_dir")
        assert tool is not None
        assert tool.name == "fs__list_dir"

    async def test_openai_tools_format(self) -> None:
        call_fn = AsyncMock(return_value=FakeCallToolResult())
        adapter = MCPToolAdapter(
            server_name="db",
            tool_def={
                "name": "query",
                "description": "Run a SQL query.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"sql": {"type": "string"}},
                    "required": ["sql"],
                },
            },
            call_fn=call_fn,
        )
        registry = ToolRegistry()
        registry.register(adapter)

        openai_tools = registry.to_openai_tools()
        assert len(openai_tools) == 1
        func = openai_tools[0]["function"]
        assert func["name"] == "db__query"
        assert func["description"] == "Run a SQL query."
        assert "sql" in func["parameters"]["properties"]

    async def test_multiple_servers_no_collision(self) -> None:
        call_fn = AsyncMock(return_value=FakeCallToolResult())
        adapter_a = MCPToolAdapter(
            server_name="server_a",
            tool_def={"name": "run", "description": "A", "inputSchema": {}},
            call_fn=call_fn,
        )
        adapter_b = MCPToolAdapter(
            server_name="server_b",
            tool_def={"name": "run", "description": "B", "inputSchema": {}},
            call_fn=call_fn,
        )
        registry = ToolRegistry()
        registry.register(adapter_a)
        registry.register(adapter_b)

        assert len(registry) == 2
        assert "server_a__run" in registry
        assert "server_b__run" in registry


# ======================================================================
# MCPClient
# ======================================================================


class TestMCPClient:
    """Tests for the ``MCPClient`` class."""

    def test_initial_state(self) -> None:
        client = MCPClient()
        assert client.connected_servers == []
        assert "MCPClient" in repr(client)

    async def test_disconnect_all_on_empty_client(self) -> None:
        """disconnect_all should be safe to call even with no connections."""
        client = MCPClient()
        await client.disconnect_all()
        assert client.connected_servers == []

    async def test_context_manager(self) -> None:
        """The client should be usable as an async context manager."""
        async with MCPClient() as client:
            assert client.connected_servers == []
        # After exit, should be cleaned up
        assert client.connected_servers == []
