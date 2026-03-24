"""Tests for per-conversation sandbox isolation.

Verifies that FileOpsTool, ShellExecTool, and PythonExecTool can be
configured with custom sandbox directories, and that the auto-discovery
function correctly wires per-conversation paths.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import pytest

import fim_one.core.tool.sandbox as _sandbox_module
from fim_one.core.tool.builtin.file_ops import FileOpsTool, _DEFAULT_WORKSPACE_DIR
from fim_one.core.tool.builtin.shell_exec import ShellExecTool, _DEFAULT_SANDBOX_DIR
from fim_one.core.tool.builtin.python_exec import PythonExecTool, _DEFAULT_EXEC_DIR
from fim_one.core.tool.builtin import discover_builtin_tools


# Docker backend maps sandbox dirs to /workspace inside the container,
# so cwd-based assertions must accept either the host path or "/workspace".
_DOCKER_WORKSPACE = "/workspace"


def _is_docker_backend() -> bool:
    """Return True when the active sandbox backend is Docker."""
    return os.environ.get("CODE_EXEC_BACKEND", "local").lower() == "docker"


@pytest.fixture(autouse=True)
def _reset_sandbox_singleton():
    """Reset the sandbox backend singleton before and after every test.

    This prevents a Docker-mode singleton created by earlier tests
    (e.g. test_sandbox_backend.py) from leaking into these tests.
    """
    _sandbox_module._backend = None
    yield
    _sandbox_module._backend = None


# ======================================================================
# FileOpsTool — per-conversation workspace
# ======================================================================


class TestFileOpsToolSandbox:
    """Verify FileOpsTool respects custom workspace_dir."""

    def test_default_workspace_dir(self) -> None:
        tool = FileOpsTool()
        assert tool._workspace_dir == _DEFAULT_WORKSPACE_DIR

    def test_custom_workspace_dir(self, tmp_path: Path) -> None:
        workspace = tmp_path / "my_workspace"
        tool = FileOpsTool(workspace_dir=workspace)
        assert tool._workspace_dir == workspace

    async def test_write_and_read_in_custom_workspace(self, tmp_path: Path) -> None:
        workspace = tmp_path / "conv_abc" / "workspace"
        tool = FileOpsTool(workspace_dir=workspace)

        # Write a file — workspace dir should be created lazily.
        result = await tool.run(operation="write", path="hello.txt", content="world")
        assert "Written" in result
        assert (workspace / "hello.txt").exists()
        assert (workspace / "hello.txt").read_text() == "world"

        # Read it back.
        result = await tool.run(operation="read", path="hello.txt")
        assert result == "world"

    async def test_list_custom_workspace(self, tmp_path: Path) -> None:
        workspace = tmp_path / "conv_list" / "workspace"
        tool = FileOpsTool(workspace_dir=workspace)

        await tool.run(operation="write", path="a.txt", content="aaa")
        await tool.run(operation="write", path="b.txt", content="bbb")

        result = await tool.run(operation="list", path=".")
        assert "a.txt" in result
        assert "b.txt" in result

    async def test_mkdir_custom_workspace(self, tmp_path: Path) -> None:
        workspace = tmp_path / "conv_mkdir" / "workspace"
        tool = FileOpsTool(workspace_dir=workspace)

        result = await tool.run(operation="mkdir", path="subdir/nested")
        assert "Directory created" in result
        assert (workspace / "subdir" / "nested").is_dir()

    async def test_path_traversal_blocked_in_custom_workspace(
        self,
        tmp_path: Path,
    ) -> None:
        workspace = tmp_path / "conv_safe" / "workspace"
        tool = FileOpsTool(workspace_dir=workspace)

        result = await tool.run(operation="read", path="../../etc/passwd")
        assert "Path traversal detected" in result

    async def test_isolation_between_conversations(self, tmp_path: Path) -> None:
        ws_a = tmp_path / "conv_a" / "workspace"
        ws_b = tmp_path / "conv_b" / "workspace"
        tool_a = FileOpsTool(workspace_dir=ws_a)
        tool_b = FileOpsTool(workspace_dir=ws_b)

        await tool_a.run(operation="write", path="secret.txt", content="only_a")
        await tool_b.run(operation="write", path="secret.txt", content="only_b")

        result_a = await tool_a.run(operation="read", path="secret.txt")
        result_b = await tool_b.run(operation="read", path="secret.txt")

        assert result_a == "only_a"
        assert result_b == "only_b"


# ======================================================================
# ShellExecTool — per-conversation sandbox
# ======================================================================


class TestShellExecToolSandbox:
    """Verify ShellExecTool respects custom sandbox_dir."""

    def test_default_sandbox_dir(self) -> None:
        tool = ShellExecTool()
        assert tool._sandbox_dir == _DEFAULT_SANDBOX_DIR

    def test_custom_sandbox_dir(self, tmp_path: Path) -> None:
        sandbox = tmp_path / "my_sandbox"
        tool = ShellExecTool(sandbox_dir=sandbox)
        assert tool._sandbox_dir == sandbox

    async def test_command_runs_in_custom_sandbox(self, tmp_path: Path) -> None:
        sandbox = tmp_path / "conv_shell" / "sandbox"
        tool = ShellExecTool(sandbox_dir=sandbox)

        result = await tool.run(command="pwd")
        assert "Exit Code: 0" in result
        # Docker backend maps the sandbox dir to /workspace inside the
        # container, so pwd will report /workspace instead of the host path.
        assert str(sandbox) in result or _DOCKER_WORKSPACE in result

    async def test_file_created_in_custom_sandbox(self, tmp_path: Path) -> None:
        sandbox = tmp_path / "conv_shell2" / "sandbox"
        tool = ShellExecTool(sandbox_dir=sandbox)

        await tool.run(command="echo hello > test.txt")
        assert (sandbox / "test.txt").exists()

    async def test_isolation_between_conversations(self, tmp_path: Path) -> None:
        sandbox_a = tmp_path / "conv_a" / "sandbox"
        sandbox_b = tmp_path / "conv_b" / "sandbox"
        tool_a = ShellExecTool(sandbox_dir=sandbox_a)
        tool_b = ShellExecTool(sandbox_dir=sandbox_b)

        await tool_a.run(command="echo A > marker.txt")
        await tool_b.run(command="echo B > marker.txt")

        assert (sandbox_a / "marker.txt").read_text().strip() == "A"
        assert (sandbox_b / "marker.txt").read_text().strip() == "B"


# ======================================================================
# PythonExecTool — per-conversation exec dir
# ======================================================================


class TestPythonExecToolSandbox:
    """Verify PythonExecTool respects custom exec_dir."""

    def test_default_exec_dir(self) -> None:
        tool = PythonExecTool()
        assert tool._exec_dir == _DEFAULT_EXEC_DIR

    def test_custom_exec_dir(self, tmp_path: Path) -> None:
        exec_dir = tmp_path / "my_exec"
        tool = PythonExecTool(exec_dir=exec_dir)
        assert tool._exec_dir == exec_dir

    async def test_cwd_is_custom_exec_dir(self, tmp_path: Path) -> None:
        exec_dir = tmp_path / "conv_py" / "exec"
        tool = PythonExecTool(exec_dir=exec_dir, timeout=10)

        # Prove cwd is the exec_dir by writing a file via a relative path.
        # We avoid `import os` / `import pathlib` because the local sandbox
        # blocks them; writing a relative-path file works on both local and
        # Docker backends.
        result = await tool.run(
            code=(
                "with open('_cwd_probe.txt', 'w') as f:\n"
                "    f.write('ok')\n"
                "print('cwd_verified')"
            )
        )
        assert "cwd_verified" in result
        assert (exec_dir / "_cwd_probe.txt").exists()
        assert (exec_dir / "_cwd_probe.txt").read_text() == "ok"

    async def test_file_io_in_custom_exec_dir(self, tmp_path: Path) -> None:
        exec_dir = tmp_path / "conv_py2" / "exec"
        tool = PythonExecTool(exec_dir=exec_dir, timeout=10)

        code = (
            "with open('output.txt', 'w') as f:\n"
            "    f.write('from python')\n"
            "print('done')"
        )
        result = await tool.run(code=code)
        assert "done" in result
        assert (exec_dir / "output.txt").read_text() == "from python"


# ======================================================================
# discover_builtin_tools — sandbox_root wiring
# ======================================================================


class TestDiscoverBuiltinToolsSandbox:
    """Verify that discover_builtin_tools passes sandbox_root correctly."""

    def test_without_sandbox_root_uses_defaults(self) -> None:
        tools = discover_builtin_tools()
        tool_map = {t.name: t for t in tools}

        file_ops = tool_map.get("file_ops")
        shell_exec = tool_map.get("shell_exec")
        python_exec = tool_map.get("python_exec")

        assert file_ops is not None
        assert shell_exec is not None
        assert python_exec is not None

        assert file_ops._workspace_dir == _DEFAULT_WORKSPACE_DIR
        assert shell_exec._sandbox_dir == _DEFAULT_SANDBOX_DIR
        assert python_exec._exec_dir == _DEFAULT_EXEC_DIR

    def test_with_sandbox_root_configures_subdirs(self, tmp_path: Path) -> None:
        sandbox_root = tmp_path / "conversations" / "conv123"
        tools = discover_builtin_tools(sandbox_root=sandbox_root)
        tool_map = {t.name: t for t in tools}

        file_ops = tool_map.get("file_ops")
        shell_exec = tool_map.get("shell_exec")
        python_exec = tool_map.get("python_exec")

        assert file_ops is not None
        assert shell_exec is not None
        assert python_exec is not None

        # All sandboxed tools share a single "workspace" directory so that
        # files created by one tool (e.g. python_exec) are visible to others
        # (e.g. file_ops, shell_exec).
        shared = sandbox_root / "workspace"
        assert file_ops._workspace_dir == shared
        assert shell_exec._sandbox_dir == shared
        assert python_exec._exec_dir == shared

    def test_non_sandboxed_tools_unaffected(self, tmp_path: Path) -> None:
        """Tools like calculator, web_fetch etc. should still be instantiated."""
        sandbox_root = tmp_path / "conversations" / "conv456"
        tools = discover_builtin_tools(sandbox_root=sandbox_root)
        tool_names = {t.name for t in tools}

        # These tools should still be present.
        assert "calculator" in tool_names
        assert "web_fetch" in tool_names
        assert "web_search" in tool_names
        assert "http_request" in tool_names

    def test_no_instantiation_failures(self, caplog: pytest.LogCaptureFixture) -> None:
        """Every non-skipped BaseTool subclass must instantiate without error.

        Catches the case where a new tool is added to the builtin/ package but
        requires constructor arguments — it must be added to _SKIP_AUTO_DISCOVER.
        """
        with caplog.at_level(logging.WARNING, logger="fim_one.core.tool.builtin"):
            discover_builtin_tools()
        failures = [
            r.message for r in caplog.records
            if "Failed to instantiate" in r.message
        ]
        assert failures == [], (
            f"Builtin tools failed to instantiate (add to _SKIP_AUTO_DISCOVER?): "
            f"{failures}"
        )
