"""Content guardrails for input/output validation.

Distinct from ``core/hooks/*`` (which gate tool execution after the model
decides) and ``core/security/*`` (which protects credentials and protocols).
Guardrails validate the *content* of user input or model output.

The three orthogonal safety layers:

============= ================================ ===============================
Layer          Owner                            What it gates
============= ================================ ===============================
Permission     ``core/hooks/*``                 Whether a tool call may execute
Security       ``core/security/*``              Credentials, SSRF, MCP auth
Guardrail      ``core/agent/guardrail.py``      Content of input or output
============= ================================ ===============================

Two distinct guardrail flavours:

* :class:`InputGuardrail` runs **before** any LLM call.  When its tripwire
  is triggered the turn is aborted before tokens are spent.
* :class:`OutputGuardrail` runs **after** the agent has produced its final
  answer.  When tripwired the answer is suppressed and the caller receives a
  structured "blocked" notification instead.

Adapted from OpenAI Agents SDK Python (MIT, Copyright (c) 2025 OpenAI),
``src/agents/guardrail.py``.  We dropped the ``RunContextWrapper`` /
``Agent[TContext]`` generics — FIM One uses a plain ``dict[str, Any]`` for
context and looks the agent up via ``agent_id`` when needed.
"""

from __future__ import annotations

__fim_license__ = "FIM-SAL-1.1"
__fim_origin__ = "https://github.com/fim-ai/fim-one"

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class GuardrailFunctionOutput:
    """Result of a single guardrail invocation."""

    output_info: Any = None
    """Optional debug payload describing what the guardrail saw.  Surfaced
    verbatim in the SSE ``guardrail_tripwired`` event so the frontend can
    show context (matched pattern, score, etc.)."""

    tripwire_triggered: bool = False
    """When ``True`` the agent run is halted and the corresponding
    ``*Tripwire`` exception is raised."""


@dataclass
class InputGuardrailResult:
    """Outcome of an :class:`InputGuardrail` check."""

    guardrail: "InputGuardrail"
    output: GuardrailFunctionOutput


@dataclass
class OutputGuardrailResult:
    """Outcome of an :class:`OutputGuardrail` check."""

    guardrail: "OutputGuardrail"
    agent_output: Any
    output: GuardrailFunctionOutput


class InputGuardrail(ABC):
    """Abstract base for content guardrails that run on *user input*.

    Subclasses implement :meth:`run` and expose a stable :attr:`name`.
    Inputs may be a plain string or a structured list (e.g. multimodal
    parts) — guardrails decide which shapes they understand.
    """

    name: str = "input_guardrail"

    @abstractmethod
    async def run(
        self,
        input: str | list[Any],
        context: dict[str, Any] | None = None,
    ) -> GuardrailFunctionOutput:
        """Inspect *input* and return a :class:`GuardrailFunctionOutput`.

        ``context`` is a free-form dict carrying at least ``agent_id`` and
        ``conversation_id`` when called from the chat endpoints.  Concrete
        guardrails should treat unknown keys as best-effort hints and never
        raise on missing context.
        """


class OutputGuardrail(ABC):
    """Abstract base for content guardrails that run on the *agent's final
    answer* before it is returned to the caller."""

    name: str = "output_guardrail"

    @abstractmethod
    async def run(
        self,
        agent_output: str,
        context: dict[str, Any] | None = None,
    ) -> GuardrailFunctionOutput:
        """Inspect *agent_output* and return a :class:`GuardrailFunctionOutput`."""


class InputGuardrailTripwireTriggered(Exception):
    """Raised when an :class:`InputGuardrail` trips its tripwire.

    Carries the originating :class:`InputGuardrailResult` so the SSE layer
    can serialise the matched info.
    """

    def __init__(self, result: InputGuardrailResult) -> None:
        self.result = result
        super().__init__(
            f"Input guardrail '{result.guardrail.name}' tripwire triggered"
        )


class OutputGuardrailTripwireTriggered(Exception):
    """Raised when an :class:`OutputGuardrail` trips its tripwire."""

    def __init__(self, result: OutputGuardrailResult) -> None:
        self.result = result
        super().__init__(
            f"Output guardrail '{result.guardrail.name}' tripwire triggered"
        )


@dataclass
class GuardrailRunSummary:
    """Aggregate of guardrail invocations for diagnostics/logging."""

    input_results: list[InputGuardrailResult] = field(default_factory=list)
    output_results: list[OutputGuardrailResult] = field(default_factory=list)
