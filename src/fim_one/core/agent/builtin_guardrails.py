"""Built-in guardrails shipped with FIM One.

The active default set is controlled at runtime by the ``FIM_GUARDRAILS_INPUT``
and ``FIM_GUARDRAILS_OUTPUT`` environment variables — comma-separated lists of
guardrail names.  See :mod:`fim_one.core.agent.guardrail` for the abstract
types these classes inherit from.

Currently shipped:

============================ ====== =================================================
Name                         Side   Purpose
============================ ====== =================================================
``jailbreak``                input  Regex-based detector for known prompt-override
                                    phrases ("ignore previous instructions", DAN, …).
``max_length``               output Tripwires when the agent answer exceeds a
                                    configurable character cap.  Lightweight stand-in
                                    for the future PII redactor.
============================ ====== =================================================
"""

from __future__ import annotations

__fim_license__ = "FIM-SAL-1.1"
__fim_origin__ = "https://github.com/fim-ai/fim-one"

import logging
import os
import re
from typing import Any

from .guardrail import (
    GuardrailFunctionOutput,
    InputGuardrail,
    OutputGuardrail,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Jailbreak detector — regex-based input guardrail
# ---------------------------------------------------------------------------


# Each pattern is matched case-insensitively with word-boundary awareness so
# benign occurrences inside larger words do not trip the wire.  The list is
# intentionally small and well-known — a smarter classifier-based detector
# is reserved for v0.5.
_JAILBREAK_PATTERNS: tuple[str, ...] = (
    r"\bignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions?\b",
    r"\bdisregard\s+(?:your|the|all)\s+(?:system\s+)?prompt\b",
    r"\b(?:you\s+are\s+now\s+in|enter|enable|activate)\s+DAN\s+mode\b",
    r"\bdeveloper\s+mode\s+(?:enabled|activated|on)\b",
    r"\bact\s+as\s+if\s+you\s+have\s+no\s+(?:restrictions|rules|guidelines)\b",
    r"\bpretend\s+(?:you\s+are|to\s+be)\s+(?:an?\s+)?unrestricted\b",
    r"\boverride\s+(?:your|the)\s+(?:safety|content)\s+(?:policy|policies|filters?)\b",
    r"\bbypass\s+(?:your|the|all)\s+(?:safety|content|moderation)\s+(?:rules?|filters?)\b",
    r"\bjailbreak\s+(?:mode|prompt)\b",
    r"\bforget\s+(?:everything|all)\s+(?:above|before|prior)\b",
)


class JailbreakDetector(InputGuardrail):
    """Detect classic prompt-override / jailbreak phrasing.

    On the first match the tripwire is set to ``True`` and ``output_info``
    records both the matched pattern and its index in :data:`_JAILBREAK_PATTERNS`
    for auditing.
    """

    name: str = "jailbreak_detector"

    def __init__(self, patterns: tuple[str, ...] | None = None) -> None:
        raw_patterns = patterns if patterns is not None else _JAILBREAK_PATTERNS
        self._patterns: list[re.Pattern[str]] = [
            re.compile(p, re.IGNORECASE) for p in raw_patterns
        ]
        self._raw: tuple[str, ...] = raw_patterns

    async def run(
        self,
        input: str | list[Any],
        context: dict[str, Any] | None = None,
    ) -> GuardrailFunctionOutput:
        text = _coerce_to_text(input)
        if not text:
            return GuardrailFunctionOutput(output_info=None, tripwire_triggered=False)
        for idx, pattern in enumerate(self._patterns):
            match = pattern.search(text)
            if match:
                return GuardrailFunctionOutput(
                    output_info={
                        "matched_pattern": self._raw[idx],
                        "pattern_index": idx,
                        "match_text": match.group(0),
                    },
                    tripwire_triggered=True,
                )
        return GuardrailFunctionOutput(output_info=None, tripwire_triggered=False)


# ---------------------------------------------------------------------------
# Max-length output guardrail — trivial stand-in for richer detectors
# ---------------------------------------------------------------------------


_DEFAULT_MAX_OUTPUT_CHARS = int(os.getenv("FIM_GUARDRAIL_MAX_OUTPUT_CHARS", "50000"))


class MaxLengthGuardrail(OutputGuardrail):
    """Tripwire when the model's final answer exceeds a character cap."""

    name: str = "max_length"

    def __init__(self, max_chars: int = _DEFAULT_MAX_OUTPUT_CHARS) -> None:
        if max_chars <= 0:
            raise ValueError("max_chars must be > 0")
        self._max_chars: int = max_chars

    async def run(
        self,
        agent_output: str,
        context: dict[str, Any] | None = None,
    ) -> GuardrailFunctionOutput:
        text = agent_output if isinstance(agent_output, str) else str(agent_output)
        length = len(text)
        if length > self._max_chars:
            return GuardrailFunctionOutput(
                output_info={"length": length, "max_chars": self._max_chars},
                tripwire_triggered=True,
            )
        return GuardrailFunctionOutput(
            output_info={"length": length, "max_chars": self._max_chars},
            tripwire_triggered=False,
        )


# ---------------------------------------------------------------------------
# Registry / env-var configuration
# ---------------------------------------------------------------------------


_INPUT_REGISTRY: dict[str, type[InputGuardrail]] = {
    "jailbreak": JailbreakDetector,
}


_OUTPUT_REGISTRY: dict[str, type[OutputGuardrail]] = {
    "max_length": MaxLengthGuardrail,
}


def _parse_names(env_value: str | None) -> list[str]:
    if not env_value:
        return []
    return [name.strip().lower() for name in env_value.split(",") if name.strip()]


def get_default_input_guardrails() -> list[InputGuardrail]:
    """Return the active list of input guardrails for this process.

    Reads ``FIM_GUARDRAILS_INPUT`` (comma-separated names).  Unknown names
    are logged and skipped — this keeps the agent loop robust when the env
    is mis-configured.  Defaults to ``"jailbreak"`` when the variable is
    unset.
    """
    raw = os.getenv("FIM_GUARDRAILS_INPUT", "jailbreak")
    names = _parse_names(raw)
    out: list[InputGuardrail] = []
    for name in names:
        cls = _INPUT_REGISTRY.get(name)
        if cls is None:
            logger.warning(
                "Unknown input guardrail '%s' in FIM_GUARDRAILS_INPUT — skipping",
                name,
            )
            continue
        out.append(cls())
    return out


def get_default_output_guardrails() -> list[OutputGuardrail]:
    """Return the active list of output guardrails.

    Reads ``FIM_GUARDRAILS_OUTPUT`` (comma-separated names).  Defaults to
    no output guardrails (``""``) — operators must opt in explicitly.
    """
    raw = os.getenv("FIM_GUARDRAILS_OUTPUT", "")
    names = _parse_names(raw)
    out: list[OutputGuardrail] = []
    for name in names:
        cls = _OUTPUT_REGISTRY.get(name)
        if cls is None:
            logger.warning(
                "Unknown output guardrail '%s' in FIM_GUARDRAILS_OUTPUT — skipping",
                name,
            )
            continue
        out.append(cls())
    return out


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _coerce_to_text(value: str | list[Any]) -> str:
    """Best-effort flatten a guardrail ``input`` arg to plain text.

    Strings pass through.  Lists (e.g. multimodal parts) are joined into a
    single space-delimited string by extracting any ``"text"`` field on
    dicts and ``str()``-coercing everything else.  Empty / non-text inputs
    yield ``""``.
    """
    if isinstance(value, str):
        return value
    parts: list[str] = []
    for item in value:
        if isinstance(item, str):
            parts.append(item)
        elif isinstance(item, dict):
            text = item.get("text")
            if isinstance(text, str):
                parts.append(text)
        else:
            parts.append(str(item))
    return " ".join(p for p in parts if p)
