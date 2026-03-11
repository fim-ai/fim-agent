"""Tests for OpenAPI spec parser."""

from __future__ import annotations

import pytest

from fim_one.core.tool.connector.openapi_parser import parse_openapi_spec


# ---------------------------------------------------------------------------
# Fixtures — sample specs
# ---------------------------------------------------------------------------

PETSTORE_SPEC: dict = {
    "openapi": "3.0.3",
    "info": {
        "title": "Petstore",
        "version": "1.0.0",
        "description": "A sample pet store",
    },
    "servers": [{"url": "https://petstore.example.com/v1"}],
    "paths": {
        "/pets": {
            "get": {
                "operationId": "listPets",
                "summary": "List all pets",
                "parameters": [
                    {
                        "name": "limit",
                        "in": "query",
                        "required": False,
                        "schema": {"type": "integer", "maximum": 100},
                        "description": "How many items to return",
                    }
                ],
                "responses": {"200": {"description": "A list of pets"}},
            },
            "post": {
                "operationId": "createPet",
                "summary": "Create a pet",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "tag": {"type": "string"},
                                },
                                "required": ["name"],
                            }
                        }
                    },
                },
                "responses": {"201": {"description": "Null response"}},
            },
        },
        "/pets/{petId}": {
            "get": {
                "operationId": "showPetById",
                "summary": "Info for a specific pet",
                "parameters": [
                    {
                        "name": "petId",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                        "description": "The id of the pet",
                    }
                ],
                "responses": {"200": {"description": "Pet details"}},
            },
            "delete": {
                "operationId": "deletePet",
                "summary": "Delete a pet",
                "parameters": [
                    {
                        "name": "petId",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
                "responses": {"204": {"description": "Pet deleted"}},
            },
        },
    },
}

GITHUB_SNIPPET_SPEC: dict = {
    "openapi": "3.0.0",
    "info": {"title": "GitHub API", "version": "1.0.0"},
    "servers": [{"url": "https://api.github.com"}],
    "paths": {
        "/repos/{owner}/{repo}/issues": {
            "get": {
                "operationId": "issues/list-for-repo",
                "summary": "List repository issues",
                "parameters": [
                    {
                        "name": "owner",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    },
                    {
                        "name": "repo",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    },
                    {
                        "name": "state",
                        "in": "query",
                        "schema": {"type": "string", "enum": ["open", "closed", "all"]},
                    },
                    {"name": "per_page", "in": "query", "schema": {"type": "integer"}},
                ],
                "responses": {"200": {"description": "OK"}},
            },
            "post": {
                "operationId": "issues/create",
                "summary": "Create an issue",
                "parameters": [
                    {
                        "name": "owner",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    },
                    {
                        "name": "repo",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    },
                ],
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "body": {"type": "string"},
                                    "labels": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    },
                                },
                                "required": ["title"],
                            }
                        }
                    }
                },
                "responses": {"201": {"description": "Created"}},
            },
        },
    },
}

SPEC_WITH_REFS: dict = {
    "openapi": "3.0.3",
    "info": {"title": "RefTest", "version": "0.1"},
    "servers": [{"url": "https://example.com"}],
    "components": {
        "schemas": {
            "Pet": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                    "category": {"$ref": "#/components/schemas/Category"},
                },
                "required": ["name"],
            },
            "Category": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                },
            },
        }
    },
    "paths": {
        "/pets": {
            "post": {
                "operationId": "addPet",
                "summary": "Add a new pet",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/Pet"}
                        }
                    }
                },
                "responses": {"201": {"description": "Created"}},
            }
        }
    },
}


YAML_SPEC_STRING = """\
openapi: "3.0.0"
info:
  title: YAML API
  version: "1.0"
servers:
  - url: https://yaml.example.com
paths:
  /items:
    get:
      operationId: getItems
      summary: List items
      parameters:
        - name: page
          in: query
          schema:
            type: integer
      responses:
        '200':
          description: OK
"""


# ---------------------------------------------------------------------------
# Tests — Petstore
# ---------------------------------------------------------------------------


class TestPetstoreSpec:
    def test_action_count(self) -> None:
        actions = parse_openapi_spec(PETSTORE_SPEC)
        assert len(actions) == 4

    def test_list_pets(self) -> None:
        actions = parse_openapi_spec(PETSTORE_SPEC)
        by_name = {a["name"]: a for a in actions}
        action = by_name["listPets"]
        assert action["method"] == "GET"
        assert action["path"] == "/pets"
        assert action["requires_confirmation"] is False
        assert action["description"] == "List all pets"
        # Should have 'limit' as a query param
        props = action["parameters_schema"]["properties"]
        assert "limit" in props
        assert props["limit"]["type"] == "integer"

    def test_create_pet(self) -> None:
        actions = parse_openapi_spec(PETSTORE_SPEC)
        by_name = {a["name"]: a for a in actions}
        action = by_name["createPet"]
        assert action["method"] == "POST"
        assert action["requires_confirmation"] is True
        schema = action["parameters_schema"]
        assert "name" in schema["properties"]
        assert "tag" in schema["properties"]
        assert "name" in schema["required"]

    def test_show_pet_by_id(self) -> None:
        actions = parse_openapi_spec(PETSTORE_SPEC)
        by_name = {a["name"]: a for a in actions}
        action = by_name["showPetById"]
        assert action["method"] == "GET"
        assert action["path"] == "/pets/{petId}"
        schema = action["parameters_schema"]
        assert "petId" in schema["properties"]
        assert "petId" in schema["required"]

    def test_delete_pet(self) -> None:
        actions = parse_openapi_spec(PETSTORE_SPEC)
        by_name = {a["name"]: a for a in actions}
        action = by_name["deletePet"]
        assert action["method"] == "DELETE"
        assert action["requires_confirmation"] is True


# ---------------------------------------------------------------------------
# Tests — GitHub snippet
# ---------------------------------------------------------------------------


class TestGitHubSpec:
    def test_action_count(self) -> None:
        actions = parse_openapi_spec(GITHUB_SNIPPET_SPEC)
        assert len(actions) == 2

    def test_operation_id_sanitisation(self) -> None:
        actions = parse_openapi_spec(GITHUB_SNIPPET_SPEC)
        names = {a["name"] for a in actions}
        # "issues/list-for-repo" → "issues_list_for_repo"
        assert "issues_list_for_repo" in names
        assert "issues_create" in names

    def test_path_params_required(self) -> None:
        actions = parse_openapi_spec(GITHUB_SNIPPET_SPEC)
        by_name = {a["name"]: a for a in actions}
        action = by_name["issues_list_for_repo"]
        required = action["parameters_schema"]["required"]
        assert "owner" in required
        assert "repo" in required

    def test_create_issue_body(self) -> None:
        actions = parse_openapi_spec(GITHUB_SNIPPET_SPEC)
        by_name = {a["name"]: a for a in actions}
        action = by_name["issues_create"]
        props = action["parameters_schema"]["properties"]
        assert "title" in props
        assert "body" in props
        assert "labels" in props
        assert action["requires_confirmation"] is True


# ---------------------------------------------------------------------------
# Tests — $ref resolution
# ---------------------------------------------------------------------------


class TestRefResolution:
    def test_ref_is_resolved(self) -> None:
        actions = parse_openapi_spec(SPEC_WITH_REFS)
        assert len(actions) == 1
        action = actions[0]
        assert action["name"] == "addPet"
        props = action["parameters_schema"]["properties"]
        assert "name" in props
        assert "id" in props
        # Nested ref: category should be resolved
        assert "category" in props
        category = props["category"]
        assert category["type"] == "object"
        assert "name" in category["properties"]
        assert "id" in category["properties"]

    def test_external_ref_handled_gracefully(self) -> None:
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "T", "version": "1"},
            "servers": [{"url": "https://x.com"}],
            "paths": {
                "/things": {
                    "post": {
                        "operationId": "createThing",
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "https://ext.com/schema.json"}
                                }
                            }
                        },
                        "responses": {"201": {}},
                    }
                }
            },
        }
        actions = parse_openapi_spec(spec)
        assert len(actions) == 1
        # External ref: body flattened as generic object → "body" param
        schema = actions[0]["parameters_schema"]
        assert "body" in schema["properties"]


# ---------------------------------------------------------------------------
# Tests — YAML input (parsed externally, parser takes dict)
# ---------------------------------------------------------------------------


class TestYAMLInput:
    def test_yaml_parsed_spec(self) -> None:
        import yaml

        spec = yaml.safe_load(YAML_SPEC_STRING)
        actions = parse_openapi_spec(spec)
        assert len(actions) == 1
        action = actions[0]
        assert action["name"] == "getItems"
        assert action["method"] == "GET"
        assert action["path"] == "/items"
        props = action["parameters_schema"]["properties"]
        assert "page" in props


# ---------------------------------------------------------------------------
# Tests — Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_paths(self) -> None:
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "Empty", "version": "1"},
            "paths": {},
        }
        actions = parse_openapi_spec(spec)
        assert actions == []

    def test_no_paths_key(self) -> None:
        spec = {"openapi": "3.0.0", "info": {"title": "Empty", "version": "1"}}
        actions = parse_openapi_spec(spec)
        assert actions == []

    def test_no_operation_id_generates_name(self) -> None:
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "T", "version": "1"},
            "paths": {
                "/users/{id}": {
                    "get": {
                        "summary": "Get user",
                        "parameters": [
                            {
                                "name": "id",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "string"},
                            }
                        ],
                        "responses": {"200": {}},
                    }
                }
            },
        }
        actions = parse_openapi_spec(spec)
        assert len(actions) == 1
        # Should generate a name from method+path
        assert "get" in actions[0]["name"].lower()
        assert "users" in actions[0]["name"].lower()

    def test_path_level_parameters_merged(self) -> None:
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "T", "version": "1"},
            "paths": {
                "/orgs/{org}/repos": {
                    "parameters": [
                        {
                            "name": "org",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "get": {
                        "operationId": "listOrgRepos",
                        "summary": "List repos",
                        "parameters": [
                            {
                                "name": "page",
                                "in": "query",
                                "schema": {"type": "integer"},
                            }
                        ],
                        "responses": {"200": {}},
                    },
                }
            },
        }
        actions = parse_openapi_spec(spec)
        action = actions[0]
        props = action["parameters_schema"]["properties"]
        assert "org" in props
        assert "page" in props
        assert "org" in action["parameters_schema"]["required"]

    def test_requires_confirmation_methods(self) -> None:
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "T", "version": "1"},
            "paths": {
                "/items": {
                    "get": {"operationId": "getItems", "responses": {"200": {}}},
                    "post": {"operationId": "createItem", "responses": {"201": {}}},
                    "put": {"operationId": "updateItem", "responses": {"200": {}}},
                    "patch": {"operationId": "patchItem", "responses": {"200": {}}},
                    "delete": {"operationId": "deleteItem", "responses": {"204": {}}},
                }
            },
        }
        actions = parse_openapi_spec(spec)
        by_name = {a["name"]: a for a in actions}
        assert by_name["getItems"]["requires_confirmation"] is False
        assert by_name["createItem"]["requires_confirmation"] is True
        assert by_name["updateItem"]["requires_confirmation"] is True
        assert by_name["patchItem"]["requires_confirmation"] is True
        assert by_name["deleteItem"]["requires_confirmation"] is True

    def test_long_description_truncated(self) -> None:
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "T", "version": "1"},
            "paths": {
                "/x": {
                    "get": {
                        "operationId": "longDesc",
                        "summary": "A" * 600,
                        "responses": {"200": {}},
                    }
                }
            },
        }
        actions = parse_openapi_spec(spec)
        assert len(actions[0]["description"]) <= 500

    def test_no_parameters_gives_none_schema(self) -> None:
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "T", "version": "1"},
            "paths": {
                "/health": {
                    "get": {
                        "operationId": "healthCheck",
                        "summary": "Health check",
                        "responses": {"200": {}},
                    }
                }
            },
        }
        actions = parse_openapi_spec(spec)
        # No params, no body → parameters_schema should be None
        assert actions[0]["parameters_schema"] is None

    def test_allof_in_request_body(self) -> None:
        spec = {
            "openapi": "3.0.0",
            "info": {"title": "T", "version": "1"},
            "components": {
                "schemas": {
                    "Base": {
                        "type": "object",
                        "properties": {"id": {"type": "integer"}},
                    }
                }
            },
            "paths": {
                "/items": {
                    "post": {
                        "operationId": "createItem",
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "allOf": [
                                            {"$ref": "#/components/schemas/Base"},
                                            {
                                                "type": "object",
                                                "properties": {
                                                    "name": {"type": "string"}
                                                },
                                            },
                                        ]
                                    }
                                }
                            }
                        },
                        "responses": {"201": {}},
                    }
                }
            },
        }
        actions = parse_openapi_spec(spec)
        assert len(actions) == 1
        # allOf non-object body → exposed as "body" param
        schema = actions[0]["parameters_schema"]
        assert "body" in schema["properties"]
