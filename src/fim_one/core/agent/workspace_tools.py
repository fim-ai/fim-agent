"""Built-in tools for interacting with the per-conversation AgentWorkspace.

These tools allow the agent to read offloaded tool outputs, browse workspace
files, and write structured handoff notes for context transitions.

They are automatically registered when a workspace is attached to the agent
and should NOT be included in the auto-discovery mechanism (they depend on
a live ``AgentWorkspace`` instance).
"""

from __future__ import annotations

__fim_license__ = "FIM-SAL-1.1"
__fim_origin__ = "https://github.com/fim-ai/fim-one"

import json
from typing import Any

from fim_one.core.tool.base import BaseTool

from .workspace import AgentWorkspace


class ReadWorkspaceFileTool(BaseTool):
    """Read a file from the conversation workspace.

    Supports reading the full file or a specific line range, which is useful
    for large offloaded tool outputs where the agent only needs a subset.
    """

    def __init__(self, workspace: AgentWorkspace) -> None:
        self._workspace = workspace

    @property
    def name(self) -> str:
        return "read_workspace_file"

    @property
    def category(self) -> str:
        return "workspace"

    @property
    def description(self) -> str:
        return (
            "Read a file from the conversation workspace. "
            "Use this to access full tool outputs that were offloaded due to size. "
            "Supports optional start_line and end_line for reading specific sections."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": (
                        "Name of the workspace file to read "
                        "(from the workspace:// URI or list_workspace_files output)."
                    ),
                },
                "start_line": {
                    "type": "integer",
                    "description": "Zero-based starting line (inclusive). Default: 0.",
                },
                "end_line": {
                    "type": "integer",
                    "description": (
                        "Zero-based ending line (exclusive). "
                        "Omit to read to the end of the file."
                    ),
                },
            },
            "required": ["filename"],
        }

    async def run(self, **kwargs: Any) -> str:
        filename: str = kwargs.get("filename", "").strip()
        if not filename:
            return "[Error] No filename provided."

        # Strip workspace:// prefix if the agent passes the full URI.
        if filename.startswith("workspace://"):
            filename = filename[len("workspace://"):]

        start_line: int = kwargs.get("start_line", 0)
        end_line: int | None = kwargs.get("end_line")

        try:
            content = self._workspace.read_file(
                filename, start_line=start_line, end_line=end_line,
            )
        except FileNotFoundError as exc:
            return f"[Error] {exc}"
        except ValueError as exc:
            return f"[Error] {exc}"

        return content


class ListWorkspaceFilesTool(BaseTool):
    """List all files in the conversation workspace."""

    def __init__(self, workspace: AgentWorkspace) -> None:
        self._workspace = workspace

    @property
    def name(self) -> str:
        return "list_workspace_files"

    @property
    def category(self) -> str:
        return "workspace"

    @property
    def description(self) -> str:
        return (
            "List all files in the conversation workspace with their size and "
            "creation time. Use this to discover available offloaded outputs "
            "and handoff notes."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": [],
        }

    async def run(self, **kwargs: Any) -> str:
        files = self._workspace.list_files()
        if not files:
            return "No files in workspace."
        return json.dumps(files, ensure_ascii=False, indent=2)


class WriteHandoffTool(BaseTool):
    """Write a structured handoff note for context transitions.

    Handoff notes are intended for capturing key findings, progress, and
    next steps when the conversation context may be compressed or when
    handing off work to another agent.
    """

    def __init__(self, workspace: AgentWorkspace) -> None:
        self._workspace = workspace

    @property
    def name(self) -> str:
        return "write_handoff"

    @property
    def category(self) -> str:
        return "workspace"

    @property
    def description(self) -> str:
        return (
            "Write a structured handoff note to the workspace. "
            "Use this to record key findings, progress, and next steps "
            "before context compression or agent handoff. "
            "The note should be a markdown-formatted summary."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": (
                        "A markdown-formatted summary of key findings, "
                        "progress, and recommended next steps."
                    ),
                },
            },
            "required": ["summary"],
        }

    async def run(self, **kwargs: Any) -> str:
        summary: str = kwargs.get("summary", "").strip()
        if not summary:
            return "[Error] No summary provided."

        uri = self._workspace.write_handoff(summary)
        return f"Handoff note saved to {uri}"
