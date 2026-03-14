"""Predefined semantic tags for connector action parameter annotations.

Semantic tags help the LLM agent understand the intent and data type of
connector parameters without guessing from column names.  Each tag maps
to a short human-readable description that is included in tool descriptions.
"""

from __future__ import annotations

from typing import Any

# Canonical set of semantic tags.  Keys are used in the ``semantic_tag``
# field of a parameter annotation; values are human-readable descriptions
# shown to the LLM.
SEMANTIC_TAGS: dict[str, str] = {
    "email": "Email address",
    "phone": "Phone number",
    "name": "Person or entity name",
    "address": "Physical or mailing address",
    "currency": "Monetary amount",
    "date": "Date or datetime value",
    "url": "URL or web link",
    "id": "Unique identifier",
    "password": "Password or secret (handle with care)",
    "api_key": "API key or token",
    "file_path": "File system path",
    "json": "JSON-structured data",
    "html": "HTML content",
    "markdown": "Markdown content",
    "code": "Source code",
    "query": "Search or database query",
}


def get_all_semantic_tags() -> dict[str, str]:
    """Return all available semantic tags with their descriptions."""
    return dict(SEMANTIC_TAGS)


def is_valid_semantic_tag(tag: str) -> bool:
    """Check whether *tag* is a recognised semantic tag."""
    return tag in SEMANTIC_TAGS


def build_annotated_description(
    base_description: str | None,
    semantic_tag: str | None,
    pii: bool | None,
) -> str | None:
    """Build an enriched parameter description from annotation fields.

    Combines the original description with semantic tag hints and PII
    warnings into a single string suitable for LLM consumption.

    Args:
        base_description: The original human-written description (may be ``None``).
        semantic_tag: A semantic tag key from :data:`SEMANTIC_TAGS` (may be ``None``).
        pii: Whether the parameter contains PII (may be ``None`` or ``False``).

    Returns:
        An enriched description string, or ``None`` if no annotations are present
        and *base_description* is also ``None``.
    """
    parts: list[str] = []

    if base_description:
        parts.append(base_description)

    if semantic_tag and semantic_tag in SEMANTIC_TAGS:
        parts.append(f"(type: {semantic_tag})")

    if pii:
        parts.append("[PII - handle with care]")

    return " ".join(parts) if parts else None


def enrich_parameters_schema(
    schema: dict[str, Any],
) -> dict[str, Any]:
    """Return a copy of *schema* with enriched property descriptions.

    For each property in the schema that contains ``semantic_tag``,
    ``description``, or ``pii`` annotation fields, the ``description``
    value is rebuilt to include semantic hints and PII warnings.

    The annotation keys (``semantic_tag``, ``pii``) are **not** removed
    from the returned schema so downstream consumers can still inspect them.

    This function does not mutate the input.
    """
    if not schema or "properties" not in schema:
        return schema

    enriched = dict(schema)
    enriched_props: dict[str, Any] = {}

    for prop_name, prop_def in schema["properties"].items():
        if not isinstance(prop_def, dict):
            enriched_props[prop_name] = prop_def
            continue

        semantic_tag = prop_def.get("semantic_tag")
        pii = prop_def.get("pii")
        base_desc = prop_def.get("description")

        new_desc = build_annotated_description(base_desc, semantic_tag, pii)

        if new_desc and new_desc != base_desc:
            new_prop = dict(prop_def)
            new_prop["description"] = new_desc
            enriched_props[prop_name] = new_prop
        else:
            enriched_props[prop_name] = prop_def

    enriched["properties"] = enriched_props
    return enriched
