"""Dependency analyzer for Solution-type resources (agent, skill, workflow).

Resolves the content dependencies (KBs, skills, connectors, MCP servers)
that a Solution references, so the subscribe/unsubscribe flow can cascade.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fim_one.web.models.agent import Agent
from fim_one.web.models.skill import Skill
from fim_one.web.models.workflow import Workflow

# Resource types considered "Solutions" — they can depend on content deps
SOLUTION_TYPES: frozenset[str] = frozenset({"agent", "skill", "workflow"})

# Resource types considered "content deps" — things Solutions reference
CONTENT_DEP_TYPES: frozenset[str] = frozenset({
    "knowledge_base", "connector", "mcp_server", "skill",
})


@dataclass(frozen=True)
class ContentDep:
    """A single content dependency of a Solution."""
    resource_type: str
    resource_id: str


@dataclass
class DependencyManifest:
    """The full set of content dependencies for a Solution."""
    solution_type: str
    solution_id: str
    content_deps: list[ContentDep] = field(default_factory=list)


async def resolve_solution_dependencies(
    resource_type: str,
    resource_id: str,
    db: AsyncSession,
) -> DependencyManifest:
    """Resolve all content dependencies for a Solution-type resource.

    For **agents**: reads ``kb_ids``, ``connector_ids``, ``skill_ids`` JSON columns.
    For **skills**: reads ``resource_refs`` JSON column.
    For **workflows**: scans blueprint nodes for connector_id, kb_id/knowledge_base_id,
        server_id (MCP), agent_id references.

    Returns a :class:`DependencyManifest` with deduplicated content deps.
    """
    manifest = DependencyManifest(solution_type=resource_type, solution_id=resource_id)

    if resource_type == "agent":
        manifest.content_deps = await _resolve_agent_deps(resource_id, db)
    elif resource_type == "skill":
        manifest.content_deps = await _resolve_skill_deps(resource_id, db)
    elif resource_type == "workflow":
        manifest.content_deps = await _resolve_workflow_deps(resource_id, db)

    return manifest


async def _resolve_agent_deps(agent_id: str, db: AsyncSession) -> list[ContentDep]:
    """Extract content deps from an Agent's JSON ID columns."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if agent is None:
        return []

    deps: list[ContentDep] = []
    for kb_id in (agent.kb_ids or []):
        if kb_id:
            deps.append(ContentDep(resource_type="knowledge_base", resource_id=kb_id))
    for conn_id in (agent.connector_ids or []):
        if conn_id:
            deps.append(ContentDep(resource_type="connector", resource_id=conn_id))
    for skill_id in (agent.skill_ids or []):
        if skill_id:
            deps.append(ContentDep(resource_type="skill", resource_id=skill_id))

    return _deduplicate(deps)


async def _resolve_skill_deps(skill_id: str, db: AsyncSession) -> list[ContentDep]:
    """Extract content deps from a Skill's resource_refs."""
    result = await db.execute(select(Skill).where(Skill.id == skill_id))
    skill = result.scalar_one_or_none()
    if skill is None:
        return []

    deps: list[ContentDep] = []
    for ref in (skill.resource_refs or []):
        ref_type = ref.get("type", "")
        ref_id = ref.get("id", "")
        if ref_type and ref_id:
            deps.append(ContentDep(resource_type=ref_type, resource_id=ref_id))

    return _deduplicate(deps)


async def _resolve_workflow_deps(workflow_id: str, db: AsyncSession) -> list[ContentDep]:
    """Extract content deps by scanning a Workflow's blueprint nodes."""
    result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
    workflow = result.scalar_one_or_none()
    if workflow is None:
        return []

    blueprint = workflow.blueprint or {}
    nodes = blueprint.get("nodes", [])

    deps: list[ContentDep] = []
    for node in nodes:
        data = node.get("data", {})
        node_type = data.get("type", "")

        # Connector node
        connector_id = data.get("connector_id", "")
        if connector_id:
            deps.append(ContentDep(resource_type="connector", resource_id=connector_id))

        # Knowledge retrieval node
        kb_id = data.get("knowledge_base_id", "") or data.get("kb_id", "")
        if kb_id:
            deps.append(ContentDep(resource_type="knowledge_base", resource_id=kb_id))

        # KB IDs list (legacy)
        for kid in (data.get("kb_ids", []) or []):
            if kid:
                deps.append(ContentDep(resource_type="knowledge_base", resource_id=kid))

        # MCP node
        server_id = data.get("server_id", "")
        if server_id:
            deps.append(ContentDep(resource_type="mcp_server", resource_id=server_id))

        # Agent node (sub-agent)
        agent_id = data.get("agent_id", "")
        if agent_id:
            deps.append(ContentDep(resource_type="agent", resource_id=agent_id))

        # Sub-workflow node
        wf_id = data.get("workflow_id", "")
        if wf_id:
            deps.append(ContentDep(resource_type="workflow", resource_id=wf_id))

    return _deduplicate(deps)


def _deduplicate(deps: list[ContentDep]) -> list[ContentDep]:
    """Remove duplicate content deps while preserving order."""
    seen: set[tuple[str, str]] = set()
    result: list[ContentDep] = []
    for dep in deps:
        key = (dep.resource_type, dep.resource_id)
        if key not in seen:
            seen.add(key)
            result.append(dep)
    return result
