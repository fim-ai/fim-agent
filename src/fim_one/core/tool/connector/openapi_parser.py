"""Parse OpenAPI 3.x specs into ConnectorAction-compatible dicts."""

from __future__ import annotations

import re
from typing import Any


def parse_openapi_spec(spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract actions from an OpenAPI 3.x specification.

    Each path+method combination becomes one action dict compatible with
    ``ActionCreate``.  The parser resolves local ``$ref`` pointers
    (``#/components/schemas/...``) but ignores external refs.

    Returns a list of dicts with keys:
        name, description, method, path, parameters_schema,
        request_body_template, requires_confirmation
    """
    components = spec.get("components", {})
    schemas = components.get("schemas", {})

    actions: list[dict[str, Any]] = []
    paths = spec.get("paths") or {}

    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        # Path-level parameters apply to all operations
        path_level_params = path_item.get("parameters", [])

        for method in ("get", "post", "put", "patch", "delete", "head", "options"):
            operation = path_item.get(method)
            if not operation or not isinstance(operation, dict):
                continue

            action = _parse_operation(
                method=method,
                path=path,
                operation=operation,
                path_level_params=path_level_params,
                schemas=schemas,
            )
            actions.append(action)

    return actions


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_MUTATING_METHODS = {"post", "put", "patch", "delete"}


def _parse_operation(
    method: str,
    path: str,
    operation: dict[str, Any],
    path_level_params: list[dict[str, Any]],
    schemas: dict[str, Any],
) -> dict[str, Any]:
    """Convert a single OpenAPI operation into an action dict."""
    name = _derive_name(method, path, operation)
    description = (
        operation.get("summary")
        or operation.get("description")
        or f"{method.upper()} {path}"
    )
    # Truncate long descriptions
    if len(description) > 500:
        description = description[:497] + "..."

    requires_confirmation = method in _MUTATING_METHODS

    # Merge path-level and operation-level parameters (operation wins)
    merged_params = _merge_parameters(path_level_params, operation.get("parameters", []))

    # Build the unified parameters_schema
    parameters_schema = _build_parameters_schema(merged_params, operation, path, schemas)

    return {
        "name": name,
        "description": description,
        "method": method.upper(),
        "path": path,
        "parameters_schema": parameters_schema if parameters_schema["properties"] else None,
        "request_body_template": None,
        "requires_confirmation": requires_confirmation,
    }


def _derive_name(method: str, path: str, operation: dict[str, Any]) -> str:
    """Derive an action name from operationId or method+path."""
    op_id = operation.get("operationId")
    if op_id:
        # Sanitise: keep alphanumeric and underscores, collapse runs
        name = re.sub(r"[^a-zA-Z0-9_]", "_", op_id)
        name = re.sub(r"_+", "_", name).strip("_")
        return name[:200]

    # Fallback: method + path slug
    slug = re.sub(r"[^a-zA-Z0-9]", "_", path)
    slug = re.sub(r"_+", "_", slug).strip("_")
    name = f"{method}_{slug}"
    return name[:200]


def _merge_parameters(
    path_params: list[dict[str, Any]],
    operation_params: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Merge path-level and operation-level parameters; operation wins on conflict."""
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for p in path_params:
        if isinstance(p, dict) and "name" in p:
            by_key[(p["name"], p.get("in", "query"))] = p
    for p in operation_params:
        if isinstance(p, dict) and "name" in p:
            by_key[(p["name"], p.get("in", "query"))] = p
    return list(by_key.values())


def _build_parameters_schema(
    params: list[dict[str, Any]],
    operation: dict[str, Any],
    path: str,
    schemas: dict[str, Any],
) -> dict[str, Any]:
    """Build a JSON-Schema-style parameters_schema for the tool.

    Combines path params, query params, and request body into a single
    flat object schema that the LLM can fill in.
    """
    properties: dict[str, Any] = {}
    required: list[str] = []

    # 1. Path and query parameters
    for param in params:
        p_name = param.get("name", "")
        if not p_name:
            continue
        p_in = param.get("in", "query")
        if p_in not in ("path", "query", "header"):
            continue

        p_schema = _resolve_schema(param.get("schema", {"type": "string"}), schemas)
        prop: dict[str, Any] = {**p_schema}
        if param.get("description"):
            prop["description"] = param["description"]

        properties[p_name] = prop
        if param.get("required") or p_in == "path":
            if p_name not in required:
                required.append(p_name)

    # 2. Request body
    request_body = operation.get("requestBody", {})
    if isinstance(request_body, dict):
        content = request_body.get("content", {})
        json_media = content.get("application/json", {})
        body_schema = json_media.get("schema")
        if body_schema:
            body_schema = _resolve_schema(body_schema, schemas)
            _flatten_body_schema(body_schema, properties, required, schemas)

    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


def _flatten_body_schema(
    body_schema: dict[str, Any],
    properties: dict[str, Any],
    required: list[str],
    schemas: dict[str, Any],
) -> None:
    """Flatten a request body schema into the top-level properties dict.

    For object schemas, each property becomes a top-level param.
    For non-object schemas (array, primitive), add as ``body``.
    """
    if body_schema.get("type") == "object" and "properties" in body_schema:
        for prop_name, prop_schema in body_schema["properties"].items():
            resolved = _resolve_schema(prop_schema, schemas)
            if prop_name not in properties:
                properties[prop_name] = resolved
        for r in body_schema.get("required", []):
            if r not in required:
                required.append(r)
    else:
        # Non-object body: expose as a single "body" parameter
        properties["body"] = body_schema
        required.append("body")


def _resolve_schema(
    schema: dict[str, Any],
    schemas: dict[str, Any],
    _depth: int = 0,
) -> dict[str, Any]:
    """Resolve local ``$ref`` pointers (``#/components/schemas/...``).

    Only resolves local refs up to 10 levels deep to avoid infinite loops.
    External refs and deeply nested refs are returned as-is minus the $ref key.
    """
    if _depth > 10:
        return {k: v for k, v in schema.items() if k != "$ref"}

    ref = schema.get("$ref")
    if ref and isinstance(ref, str):
        prefix = "#/components/schemas/"
        if ref.startswith(prefix):
            ref_name = ref[len(prefix):]
            if ref_name in schemas:
                resolved = schemas[ref_name]
                return _resolve_schema(dict(resolved), schemas, _depth + 1)
        # External or unresolvable ref -- return a generic object
        return {"type": "object"}

    result: dict[str, Any] = {}
    for key, value in schema.items():
        if key == "properties" and isinstance(value, dict):
            result[key] = {
                k: _resolve_schema(v, schemas, _depth + 1) if isinstance(v, dict) else v
                for k, v in value.items()
            }
        elif key == "items" and isinstance(value, dict):
            result[key] = _resolve_schema(value, schemas, _depth + 1)
        elif key in ("allOf", "oneOf", "anyOf") and isinstance(value, list):
            result[key] = [
                _resolve_schema(v, schemas, _depth + 1) if isinstance(v, dict) else v
                for v in value
            ]
        else:
            result[key] = value

    return result
