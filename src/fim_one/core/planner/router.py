"""Auto-routing classifier for execution mode selection.

Uses a fast LLM to classify whether a user query is better served by
ReAct (single-step, conversational) or DAG (multi-step, decomposable).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

from fim_one.core.model.base import BaseLLM
from fim_one.core.model.structured import structured_llm_call
from fim_one.core.model.types import ChatMessage

logger = logging.getLogger(__name__)

# Specialist domains that trigger model escalation and domain-aware routing.
# Configurable via env var (comma-separated).  Each domain gets:
# - Reasoning model escalation in ReAct mode
# - Mandatory web_search instructions
# - Citation verification in DAG mode
# - Routing bias toward ReAct for deep analysis tasks
ESCALATION_DOMAINS: list[str] = [
    d.strip()
    for d in os.getenv(
        "DAG_ESCALATION_DOMAINS",
        "legal,medical,financial,tax,compliance,patent",
    ).split(",")
    if d.strip()
]

# Pre-built description map for the classification prompt.
_DOMAIN_DESCRIPTIONS: dict[str, str] = {
    "legal": "laws, regulations, compliance, trademarks, contracts, litigation",
    "medical": "health, drugs, clinical trials, diagnosis, medical devices",
    "financial": "securities, accounting, audit, financial regulations",
    "tax": "tax law, tax codes, VAT, income tax, transfer pricing",
    "compliance": "GDPR, SOX, data protection, industry regulations, certifications",
    "patent": "patent law, claims, prior art, IP prosecution, utility models",
}


def _build_domain_prompt_block() -> str:
    """Build the domain_hint section of the classification prompt."""
    lines = []
    for domain in ESCALATION_DOMAINS:
        desc = _DOMAIN_DESCRIPTIONS.get(domain, domain)
        lines.append(f'- "{domain}": {desc}')
    lines.append("- null: general purpose, no domain expertise required")
    return "\n".join(lines)


def _build_domain_enum() -> list[str | None]:
    """Build the JSON schema enum for domain_hint."""
    return [*ESCALATION_DOMAINS, None]


_CLASSIFICATION_PROMPT = """\
You are an execution-mode classifier for an AI agent system.

Given a user query, decide:

1. **mode** — how to execute:
- "react": Simple, single-step, conversational, or exploratory queries. \
Queries that need back-and-forth or are open-ended.
- "dag": Complex, multi-step tasks that can be decomposed into independent \
subtasks with dependencies. Tasks that benefit from parallel execution.

2. **domain_hint** — the specialist domain (or null for general):
{domain_block}

## Domain-aware routing guidance
- Queries in specialist domains that require **deep analysis \
or report writing** → prefer "react".  These domains have tightly coupled \
analysis dimensions; splitting into DAG steps loses cross-reference context \
and increases citation hallucination risk.
- Domain queries that are clearly decomposable with **independent subtasks** \
(e.g. "check trademark status in 5 separate countries") → "dag" is fine.
- When in doubt for domain queries, prefer "react" — a single capable agent \
with full context produces higher-accuracy results.

## Examples
- "What is the weather?" -> react, null
- "Summarize this document" -> react, null
- "Find all customers who churned last month, analyze the reasons, and \
draft an email campaign" -> dag, null
- "Evaluate the legal risks of using a competitor's brand name" -> react, legal
- "Compare drug efficacy across 3 clinical trials" -> react, medical
- "Research competitor pricing in 5 markets, create comparison table" -> dag, null
- "Hello" -> react, null

## Query
{{query}}

Respond with JSON: {{{{"mode": "react" or "dag", "domain_hint": one of {domain_names_str} or null, "reasoning": "brief explanation"}}}}
""".format(
    domain_block=_build_domain_prompt_block(),
    domain_names_str="/".join(f'"{d}"' for d in ESCALATION_DOMAINS),
)

_CLASSIFICATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "mode": {"type": "string", "enum": ["react", "dag"]},
        "domain_hint": {
            "type": ["string", "null"],
            "enum": _build_domain_enum(),
        },
        "reasoning": {"type": "string"},
    },
    "required": ["mode", "reasoning"],
}


@dataclass
class RouteDecision:
    """Result of the auto-routing classification.

    Attributes:
        mode: Either ``"react"`` or ``"dag"``.
        domain_hint: Specialist domain (``"legal"``, ``"medical"``,
            ``"financial"``) or ``None`` for general-purpose queries.
        reasoning: Brief explanation from the classifier.
    """

    mode: str  # "react" or "dag"
    domain_hint: str | None = None
    reasoning: str = ""


async def classify_execution_mode(
    query: str,
    llm: BaseLLM,
) -> RouteDecision:
    """Classify a user query into react or dag execution mode.

    Uses a structured LLM call to classify the query.  On any error,
    defaults to ``"react"`` (safe fallback -- ReAct can handle everything,
    just less efficiently for complex multi-step tasks).

    Args:
        query: The user query to classify (truncated to 2000 chars).
        llm: The LLM to use for classification (typically the fast model).

    Returns:
        A :class:`RouteDecision` with the selected mode and reasoning.
    """
    _query_limit = int(os.getenv("DAG_ROUTER_QUERY_TRUNCATION", "2000"))
    truncated_query = query[:_query_limit]
    prompt = _CLASSIFICATION_PROMPT.format(query=truncated_query)

    messages = [
        ChatMessage(role="user", content=prompt),
    ]

    try:
        call_result = await structured_llm_call(
            llm=llm,
            messages=messages,
            schema=_CLASSIFICATION_SCHEMA,
            function_name="classify_mode",
            default_value={"mode": "react", "domain_hint": None, "reasoning": "Classification fallback"},
            temperature=0.0,
        )

        data = call_result.value
        mode = data.get("mode", "react") if isinstance(data, dict) else "react"
        if mode not in ("react", "dag"):
            mode = "react"
        reasoning = data.get("reasoning", "") if isinstance(data, dict) else ""

        _valid_domains = set(ESCALATION_DOMAINS)
        raw_domain = data.get("domain_hint") if isinstance(data, dict) else None
        domain_hint = raw_domain if raw_domain in _valid_domains else None

        return RouteDecision(mode=mode, domain_hint=domain_hint, reasoning=reasoning)
    except Exception as exc:
        logger.warning(
            "Auto-routing classification failed, defaulting to react: %s", exc,
        )
        return RouteDecision(
            mode="react",
            reasoning=f"Classification error: {exc}",
        )
