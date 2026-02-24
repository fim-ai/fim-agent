"""Built-in tools with auto-discovery.

Any module in this package that defines a concrete ``BaseTool`` subclass will
be automatically discovered by :func:`discover_builtin_tools`.  No manual
registration is needed — just drop a new ``<name>.py`` file here.
"""

from __future__ import annotations

import importlib
import inspect
import logging
import pkgutil
from typing import TYPE_CHECKING

from fim_agent.core.tool.base import BaseTool

if TYPE_CHECKING:
    from fim_agent.core.tool.base import Tool

logger = logging.getLogger(__name__)

# Explicit re-exports (for convenience — callers can still import directly)
from .calculator import CalculatorTool
from .file_ops import FileOpsTool
from .python_exec import PythonExecTool
from .web_fetch import WebFetchTool
from .web_search import WebSearchTool

__all__ = [
    "CalculatorTool",
    "FileOpsTool",
    "PythonExecTool",
    "WebFetchTool",
    "WebSearchTool",
    "discover_builtin_tools",
]


def discover_builtin_tools() -> list[Tool]:
    """Auto-discover and instantiate all built-in tools.

    Scans every module in this package, finds concrete ``BaseTool`` subclasses,
    and returns a fresh instance of each (via zero-arg constructor).

    Tools that fail to import or instantiate are logged and skipped.
    """
    tools: list[Tool] = []
    package_path = __path__  # type: ignore[name-defined]
    package_name = __name__

    for finder, module_name, _is_pkg in pkgutil.iter_modules(package_path):
        fqn = f"{package_name}.{module_name}"
        try:
            mod = importlib.import_module(fqn)
        except Exception:
            logger.warning("Failed to import tool module %s", fqn, exc_info=True)
            continue

        for _attr_name, obj in inspect.getmembers(mod, inspect.isclass):
            if (
                issubclass(obj, BaseTool)
                and obj is not BaseTool
                and not inspect.isabstract(obj)
            ):
                try:
                    tools.append(obj())
                except Exception:
                    logger.warning(
                        "Failed to instantiate tool %s.%s",
                        fqn,
                        obj.__name__,
                        exc_info=True,
                    )
    return tools
