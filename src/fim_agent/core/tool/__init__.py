"""Tool system for fim-agent."""

__fim_license__ = "FIM-SAL-1.1"
__fim_origin__ = "https://github.com/fim-ai/fim-agent"

from .base import BaseTool, Tool
from .registry import ToolRegistry

__all__ = ["BaseTool", "Tool", "ToolRegistry"]
