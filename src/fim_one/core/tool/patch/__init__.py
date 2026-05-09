"""V4A diff format support for FIM One file editing tools.

The implementation in :mod:`fim_one.core.tool.patch.v4a` is vendored from
OpenAI Agents SDK Python (MIT License, Copyright (c) 2025 OpenAI). See the
header of ``v4a.py`` for the full license text.
"""

from __future__ import annotations

from .v4a import (
    ApplyDiffMode,
    Chunk,
    ParsedUpdateDiff,
    apply_diff,
)

__all__ = [
    "ApplyDiffMode",
    "Chunk",
    "ParsedUpdateDiff",
    "apply_diff",
]
