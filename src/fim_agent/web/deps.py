"""Dependency providers for the FIM Agent web layer.

All configuration is read from environment variables so that callers only need
to populate the environment (or a ``.env`` file) before importing this module.

Environment variables
---------------------
LLM_API_KEY   : API key for the LLM provider (default: empty string).
LLM_BASE_URL  : Base URL of the OpenAI-compatible endpoint
                 (default: ``https://api.openai.com/v1``).
LLM_MODEL     : Model identifier (default: ``gpt-4o``).
"""

from __future__ import annotations

import os
import logging

from fim_agent.core.model import OpenAICompatibleLLM
from fim_agent.core.tool import ToolRegistry
from fim_agent.core.tool.builtin.python_exec import PythonExecTool

logger = logging.getLogger(__name__)


def get_llm() -> OpenAICompatibleLLM:
    """Create an :class:`OpenAICompatibleLLM` configured from environment variables."""
    return OpenAICompatibleLLM(
        api_key=os.environ.get("LLM_API_KEY", ""),
        base_url=os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1"),
        model=os.environ.get("LLM_MODEL", "gpt-4o"),
    )


def get_tools() -> ToolRegistry:
    """Create a :class:`ToolRegistry` pre-loaded with the default tool set."""
    registry = ToolRegistry()
    registry.register(PythonExecTool())
    return registry


def get_user_id() -> str:
    """Return the current user identifier.

    This is a placeholder that always returns ``"default"``.  It is pre-wired
    so that future authentication middleware can override the value without
    touching endpoint signatures.
    """
    return "default"
