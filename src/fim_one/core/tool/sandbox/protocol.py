"""Sandbox protocol — shared types and backend interface."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass
class SandboxResult:
    """Unified result from any sandbox backend.

    exit_code semantics:
      0   = success
      124 = timeout (compatible with ``timeout`` command)
      137 = OOM kill (SIGKILL)
      -1  = infrastructure error (docker not found, etc.)
    """

    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool = False
    error: str | None = None  # infra-level error message (not user code errors)
    script_path: Path | None = None  # path to the written script file (if applicable)


@runtime_checkable
class SandboxBackend(Protocol):
    """Protocol that all sandbox backends must implement.

    Designed to be language-agnostic — a single ``run_code`` method handles
    all languages via the *language* parameter, making it easy to add new
    languages (TypeScript, Ruby, etc.) without changing the interface.
    """

    async def run_code(
        self,
        code: str,
        *,
        language: str,
        exec_dir: Path,
        timeout: int,
        memory: str | None = None,
        cpu: float | None = None,
    ) -> SandboxResult:
        """Execute *code* in the given *language*.

        Args:
            code: Source code to execute (passed via stdin in docker mode).
            language: Runtime identifier — ``"python"`` or ``"javascript"``.
            exec_dir: Host-side directory mounted as ``/workspace`` (docker)
                      or used as cwd (local).  Files written here are
                      accessible to other tools via FileOpsTool.
            timeout: Execution timeout in seconds.
            memory: Docker memory limit (e.g. ``"256m"``). Docker only.
            cpu: Docker CPU quota (e.g. ``0.5``). Docker only.

        Returns:
            :class:`SandboxResult` with captured stdout/stderr and exit code.
        """
        ...

    async def run_shell(
        self,
        command: str,
        *,
        sandbox_dir: Path,
        timeout: int,
        memory: str | None = None,
        cpu: float | None = None,
    ) -> SandboxResult:
        """Execute a *command* string in a shell.

        Args:
            command: Shell command to run.
            sandbox_dir: Working directory for the command.
            timeout: Execution timeout in seconds.
            memory: Docker memory limit (e.g. ``"256m"``). Docker only.
            cpu: Docker CPU quota (e.g. ``0.5``). Docker only.

        Returns:
            :class:`SandboxResult` with captured stdout/stderr and exit code.
        """
        ...
