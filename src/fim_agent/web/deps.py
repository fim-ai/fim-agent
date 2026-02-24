"""Dependency providers for the FIM Agent web layer.

All configuration is read from environment variables so that callers only need
to populate the environment (or a ``.env`` file) before importing this module.

Environment variables
---------------------
LLM_API_KEY      : API key for the LLM provider (default: empty string).
LLM_BASE_URL     : Base URL of the OpenAI-compatible endpoint
                    (default: ``https://api.openai.com/v1``).
LLM_MODEL        : Model identifier for the main (smart) model used for
                    planning, analysis, and ReAct (default: ``gpt-4o``).
FAST_LLM_MODEL   : Model identifier for the fast model used for DAG step
                    execution (default: falls back to ``LLM_MODEL``).
LLM_TEMPERATURE  : Default sampling temperature (default: ``0.7``).
MAX_CONCURRENCY  : Max parallel steps in DAG executor (default: ``5``).
MCP_SERVERS      : Optional JSON array of MCP server configs.  Each entry
                    is ``{"name": str, "command": str, "args": [str], "env": {}}``.
"""

from __future__ import annotations

import json
import os
import logging
from typing import TYPE_CHECKING

from fim_agent.core.model import OpenAICompatibleLLM
from fim_agent.core.model.registry import ModelRegistry
from fim_agent.core.tool import ToolRegistry
from fim_agent.core.tool.builtin import discover_builtin_tools

if TYPE_CHECKING:
    from fim_agent.core.mcp import MCPClient

logger = logging.getLogger(__name__)


def _api_key() -> str:
    return os.environ.get("LLM_API_KEY", "")


def _base_url() -> str:
    return os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")


def _main_model() -> str:
    return os.environ.get("LLM_MODEL", "gpt-4o")


def _fast_model() -> str:
    return os.environ.get("FAST_LLM_MODEL", "") or _main_model()


def _temperature() -> float:
    return float(os.environ.get("LLM_TEMPERATURE", "0.7"))


def get_max_concurrency() -> int:
    """Return the max parallel steps for the DAG executor."""
    return int(os.environ.get("MAX_CONCURRENCY", "5"))


def get_llm() -> OpenAICompatibleLLM:
    """Create the main (smart) LLM for planning, analysis, and ReAct."""
    return OpenAICompatibleLLM(
        api_key=_api_key(),
        base_url=_base_url(),
        model=_main_model(),
        default_temperature=_temperature(),
    )


def get_fast_llm() -> OpenAICompatibleLLM:
    """Create the fast LLM for DAG step execution.

    Falls back to the main model if ``FAST_LLM_MODEL`` is not set.
    """
    return OpenAICompatibleLLM(
        api_key=_api_key(),
        base_url=_base_url(),
        model=_fast_model(),
        default_temperature=_temperature(),
    )


def get_model_registry() -> ModelRegistry:
    """Create a :class:`ModelRegistry` with main and fast models."""
    registry = ModelRegistry()

    registry.register(
        "main",
        get_llm(),
        roles=["general", "planning", "analysis"],
    )

    fast = get_fast_llm()
    # Only register as a separate entry if it's actually a different model.
    if _fast_model() != _main_model():
        registry.register("fast", fast, roles=["fast", "execution"])
    else:
        # Same model — register the "fast" role on the main entry.
        registry._roles.setdefault("fast", []).append("main")
        registry._roles.setdefault("execution", []).append("main")

    return registry


def get_tools() -> ToolRegistry:
    """Create a :class:`ToolRegistry` pre-loaded with all discovered built-in tools.

    Tools are auto-discovered from the ``fim_agent.core.tool.builtin`` package.
    To add a new tool, simply drop a module containing a ``BaseTool`` subclass
    into that package — no manual registration needed.
    """
    registry = ToolRegistry()
    for tool in discover_builtin_tools():
        registry.register(tool)
    logger.info("Registered %d built-in tools: %s", len(registry), registry)
    return registry


def get_user_id() -> str:
    """Return the current user identifier.

    This is a placeholder that always returns ``"default"``.  It is pre-wired
    so that future authentication middleware can override the value without
    touching endpoint signatures.
    """
    return "default"


async def get_mcp_tools(registry: ToolRegistry) -> MCPClient | None:
    """Connect to MCP servers defined in ``MCP_SERVERS`` and register their tools.

    The ``MCP_SERVERS`` environment variable should be a JSON array of server
    config objects::

        [
          {
            "name": "filesystem",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
            "env": {}
          }
        ]

    Each server's tools are discovered and registered in *registry* with
    names prefixed by the server name (e.g. ``filesystem__read_file``).

    Returns
    -------
    MCPClient | None
        The connected :class:`MCPClient` instance, or ``None`` if
        ``MCP_SERVERS`` is not set.  The caller is responsible for calling
        ``await client.disconnect_all()`` on shutdown.
    """
    servers_json = os.environ.get("MCP_SERVERS", "")
    if not servers_json:
        return None

    try:
        from fim_agent.core.mcp import MCPClient
    except ImportError:
        logger.warning(
            "MCP_SERVERS is set but the 'mcp' package is not installed. "
            "Install it with: uv sync --extra mcp"
        )
        return None

    servers: list[dict[str, object]] = json.loads(servers_json)
    client = MCPClient()

    for server in servers:
        name = str(server["name"])
        command = str(server["command"])
        args = [str(a) for a in server.get("args", [])]  # type: ignore[union-attr]
        env = server.get("env")  # type: ignore[assignment]

        try:
            tools = await client.connect_stdio(
                name=name,
                command=command,
                args=args,
                env=env,  # type: ignore[arg-type]
            )
            for tool in tools:
                registry.register(tool)
        except Exception:
            logger.exception("Failed to connect to MCP server %r", name)

    return client
