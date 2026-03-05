"""Built-in tool for executing JavaScript (Node.js) code in a sandbox."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from ..base import BaseTool
from ..sandbox import get_sandbox_backend

_DEFAULT_TIMEOUT_SECONDS: int = 120

# Default directory for code execution outputs.
_DEFAULT_EXEC_DIR = Path(__file__).resolve().parents[4] / "tmp" / "default" / "exec"

# Maximum captured output size (bytes) before truncation.
_MAX_OUTPUT_BYTES: int = 100 * 1024  # 100 KB


def _truncate_output(text: str) -> str:
    """Truncate *text* if it exceeds ``_MAX_OUTPUT_BYTES``."""
    encoded = text.encode("utf-8", errors="replace")
    if len(encoded) <= _MAX_OUTPUT_BYTES:
        return text
    truncated = encoded[:_MAX_OUTPUT_BYTES].decode("utf-8", errors="replace")
    return (
        truncated
        + f"\n\n[Output truncated — exceeded {_MAX_OUTPUT_BYTES // 1024} KB limit]"
    )


class NodeExecTool(BaseTool):
    """Execute JavaScript (Node.js) code and capture its output.

    Local mode:  requires Node.js on PATH (``node -e <code>``).
                 If Node.js is not installed, returns a helpful error message.
    Docker mode: runs in ``node:20-slim`` container with full isolation.
                 Switch via ``CODE_EXEC_BACKEND=docker``.

    Files written to the execution directory are accessible to FileOpsTool
    via the shared per-conversation workspace.
    """

    def __init__(
        self,
        *,
        timeout: int = _DEFAULT_TIMEOUT_SECONDS,
        exec_dir: Path | None = None,
    ) -> None:
        self._timeout = timeout
        self._exec_dir = exec_dir or _DEFAULT_EXEC_DIR

    @property
    def name(self) -> str:
        return "node_exec"

    @property
    def display_name(self) -> str:
        return "JavaScript"

    @property
    def category(self) -> str:
        return "computation"

    @property
    def description(self) -> str:
        return (
            "Execute JavaScript (Node.js) code and return the output. "
            "Use console.log() to produce output. "
            "Only Node.js built-in modules are guaranteed to be available. "
            "Do NOT attempt to install packages (npm install) — "
            "it will likely fail or timeout. "
            "In local mode, Node.js must be installed on the host. "
            "Switch to docker mode (CODE_EXEC_BACKEND=docker) for a fully "
            "isolated Node.js environment."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "JavaScript code to execute.",
                },
            },
            "required": ["code"],
        }

    async def run(self, **kwargs: Any) -> str:
        code: str = kwargs.get("code", "")
        if not code.strip():
            return ""

        backend = get_sandbox_backend()
        result = await backend.run_code(
            code,
            language="javascript",
            exec_dir=self._exec_dir,
            timeout=self._timeout,
        )

        if result.timed_out:
            return f"[Timeout] Execution exceeded {self._timeout} seconds."
        if result.error:
            return f"[Error] {result.error}"

        output = result.stdout
        if result.stderr:
            output = output + "[stderr]\n" + result.stderr
        if result.script_path is not None:
            output = f"[Script: {result.script_path.name}]\n" + output
        return _truncate_output(output)
