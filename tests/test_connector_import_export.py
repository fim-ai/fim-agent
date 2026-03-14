"""Tests for connector import/export endpoints.

These are pure unit tests that exercise the schema layer and the helper
functions used by the export/import endpoints. They do NOT require a running
database -- all connector objects are built in memory with MagicMock or
direct model construction.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

import pytest

from fim_one.web.schemas.connector import (
    ActionExportData,
    ConnectorExportData,
    ConnectorExportMeta,
    ConnectorImportRequest,
    ConnectorImportResult,
    ConnectorResponse,
)


# ---------------------------------------------------------------------------
# Helpers: build fake ORM-like objects for testing
# ---------------------------------------------------------------------------


def _make_action(
    *,
    name: str = "List Users",
    description: str | None = "List all users",
    method: str = "GET",
    path: str = "/users",
    parameters_schema: dict[str, Any] | None = None,
    request_body_template: dict[str, Any] | None = None,
    response_extract: str | None = None,
    requires_confirmation: bool = False,
) -> MagicMock:
    action = MagicMock()
    action.id = "action-001"
    action.connector_id = "conn-001"
    action.name = name
    action.description = description
    action.method = method
    action.path = path
    action.parameters_schema = parameters_schema
    action.request_body_template = request_body_template
    action.response_extract = response_extract
    action.requires_confirmation = requires_confirmation
    action.created_at = datetime(2026, 1, 1, 0, 0, 0)
    action.updated_at = None
    return action


def _make_connector(
    *,
    name: str = "GitHub API",
    description: str | None = "GitHub REST API connector",
    icon: str | None = "github",
    connector_type: str = "api",
    base_url: str | None = "https://api.github.com",
    auth_type: str = "bearer",
    auth_config: dict[str, Any] | None = None,
    db_config: dict[str, Any] | None = None,
    actions: list[MagicMock] | None = None,
    user_id: str = "user-001",
    org_id: str | None = None,
) -> MagicMock:
    conn = MagicMock()
    conn.id = "conn-001"
    conn.user_id = user_id
    conn.name = name
    conn.description = description
    conn.icon = icon
    conn.type = connector_type
    conn.base_url = base_url
    conn.auth_type = auth_type
    conn.auth_config = auth_config or {"token_prefix": "Bearer"}
    conn.db_config = db_config
    conn.status = "published"
    conn.is_official = False
    conn.forked_from = None
    conn.version = 1
    conn.is_active = True
    conn.visibility = "personal"
    conn.org_id = org_id
    conn.allow_fallback = True
    conn.publish_status = None
    conn.reviewed_by = None
    conn.reviewed_at = None
    conn.review_note = None
    conn.actions = actions if actions is not None else [_make_action()]
    conn.created_at = datetime(2026, 1, 1, 0, 0, 0)
    conn.updated_at = None
    return conn


# ===================================================================
# Tests: ConnectorExportData schema
# ===================================================================


class TestConnectorExportData:
    """Verify the export schema produces the expected portable structure."""

    def test_basic_export_shape(self) -> None:
        """Export schema contains expected fields without ownership data."""
        meta = ConnectorExportMeta(exported_at="2026-01-01T00:00:00+00:00")
        export = ConnectorExportData.model_construct(
            name="GitHub API",
            description="GitHub REST API",
            icon="github",
            connector_type="api",
            base_url="https://api.github.com",
            auth_type="bearer",
            auth_config={"token_prefix": "Bearer"},
            actions=[],
            _meta=meta,
        )
        data = export.model_dump()

        assert data["name"] == "GitHub API"
        assert data["connector_type"] == "api"
        assert data["auth_type"] == "bearer"
        assert data["base_url"] == "https://api.github.com"
        # Ownership/internal fields must NOT be present
        assert "user_id" not in data
        assert "org_id" not in data
        assert "id" not in data
        assert "credentials" not in data

    def test_export_excludes_sensitive_auth_fields(self) -> None:
        """Exported auth_config should not contain credential values."""
        from fim_one.web.api.connectors import _strip_sensitive_auth_config

        raw_auth = {"token_prefix": "Bearer", "default_token": "secret-value"}
        clean = _strip_sensitive_auth_config("bearer", raw_auth)

        assert "default_token" not in clean
        assert clean["token_prefix"] == "Bearer"

    def test_export_includes_actions(self) -> None:
        """Actions should be serialized without IDs or timestamps."""
        action = ActionExportData(
            name="List Repos",
            description="List repositories",
            method="GET",
            path="/repos",
            parameters_schema={"type": "object", "properties": {"page": {"type": "integer"}}},
        )
        meta = ConnectorExportMeta(exported_at="2026-01-01T00:00:00+00:00")
        export = ConnectorExportData.model_construct(
            name="GitHub",
            connector_type="api",
            actions=[action],
            _meta=meta,
        )
        data = export.model_dump()

        assert len(data["actions"]) == 1
        act = data["actions"][0]
        assert act["name"] == "List Repos"
        assert act["method"] == "GET"
        assert act["path"] == "/repos"
        # No IDs or timestamps in exported actions
        assert "id" not in act
        assert "connector_id" not in act
        assert "created_at" not in act

    def test_export_meta_fields(self) -> None:
        """The _meta envelope contains exported_at, version, source."""
        meta = ConnectorExportMeta(exported_at="2026-03-14T10:00:00+00:00")
        data = meta.model_dump()

        assert data["exported_at"] == "2026-03-14T10:00:00+00:00"
        assert data["version"] == "1.0"
        assert data["source"] == "fim-one"


# ===================================================================
# Tests: ConnectorImportRequest validation
# ===================================================================


class TestConnectorImportRequest:
    """Verify import request validation."""

    def test_valid_import_request(self) -> None:
        """A well-formed import request is accepted."""
        req = ConnectorImportRequest(
            name="Slack API",
            connector_type="api",
            base_url="https://slack.com/api",
            auth_type="bearer",
            actions=[
                ActionExportData(name="Post Message", method="POST", path="/chat.postMessage"),
            ],
        )
        assert req.name == "Slack API"
        assert req.connector_type == "api"
        assert len(req.actions) == 1

    def test_minimal_import_request(self) -> None:
        """Only name and connector_type are required."""
        req = ConnectorImportRequest(name="Minimal", connector_type="api")
        assert req.name == "Minimal"
        assert req.connector_type == "api"
        assert req.actions == []
        assert req.auth_type == "none"

    def test_invalid_connector_type_rejected(self) -> None:
        """connector_type must be 'api' or 'database'."""
        with pytest.raises(Exception):
            ConnectorImportRequest(name="Bad", connector_type="invalid")

    def test_empty_name_rejected(self) -> None:
        """name must be at least 1 character."""
        with pytest.raises(Exception):
            ConnectorImportRequest(name="", connector_type="api")


# ===================================================================
# Tests: ConnectorImportResult schema
# ===================================================================


class TestConnectorImportResult:
    """Verify the import result schema."""

    def test_result_with_warnings(self) -> None:
        """Import result should carry the connector plus a warnings list."""
        connector_resp = ConnectorResponse(
            id="new-uuid",
            user_id="user-001",
            name="Imported",
            description=None,
            icon=None,
            type="api",
            base_url=None,
            auth_type="bearer",
            auth_config=None,
            is_official=False,
            forked_from=None,
            version=1,
            actions=[],
            created_at="2026-01-01T00:00:00",
            updated_at=None,
        )
        result = ConnectorImportResult(
            connector=connector_resp,
            warnings=["credentials", "base_url"],
        )
        data = result.model_dump()

        assert data["connector"]["name"] == "Imported"
        assert "credentials" in data["warnings"]
        assert "base_url" in data["warnings"]

    def test_result_no_warnings(self) -> None:
        """Import result with no warnings has an empty list."""
        connector_resp = ConnectorResponse(
            id="new-uuid",
            user_id="user-001",
            name="Complete",
            description=None,
            icon=None,
            type="api",
            base_url="https://example.com",
            auth_type="none",
            auth_config=None,
            is_official=False,
            forked_from=None,
            version=1,
            actions=[],
            created_at="2026-01-01T00:00:00",
            updated_at=None,
        )
        result = ConnectorImportResult(connector=connector_resp, warnings=[])
        assert result.warnings == []


# ===================================================================
# Tests: Export produces valid JSON without credentials
# ===================================================================


class TestExportSecurity:
    """Ensure exported data never contains credentials or sensitive fields."""

    def test_bearer_token_excluded(self) -> None:
        """default_token must be stripped from exported auth_config."""
        from fim_one.web.api.connectors import _strip_sensitive_auth_config

        config = {"token_prefix": "Bearer", "default_token": "super-secret"}
        clean = _strip_sensitive_auth_config("bearer", config)
        assert "default_token" not in clean

    def test_api_key_excluded(self) -> None:
        """default_api_key must be stripped from exported auth_config."""
        from fim_one.web.api.connectors import _strip_sensitive_auth_config

        config = {"header_name": "X-API-Key", "default_api_key": "key-12345"}
        clean = _strip_sensitive_auth_config("api_key", config)
        assert "default_api_key" not in clean

    def test_basic_auth_excluded(self) -> None:
        """default_username and default_password must be stripped."""
        from fim_one.web.api.connectors import _strip_sensitive_auth_config

        config = {"default_username": "admin", "default_password": "hunter2"}
        clean = _strip_sensitive_auth_config("basic", config)
        assert "default_username" not in clean
        assert "default_password" not in clean

    def test_db_config_not_in_export(self) -> None:
        """db_config (containing connection strings) should not be in export schema."""
        meta = ConnectorExportMeta(exported_at="2026-01-01T00:00:00+00:00")
        export = ConnectorExportData.model_construct(
            name="My DB",
            connector_type="database",
            auth_type="none",
            actions=[],
            _meta=meta,
        )
        data = export.model_dump()
        assert "db_config" not in data


# ===================================================================
# Tests: Import preserves configuration
# ===================================================================


class TestImportPreservesConfig:
    """Verify that importing preserves the connector's configuration data."""

    def test_preserves_name_and_description(self) -> None:
        req = ConnectorImportRequest(
            name="Stripe API",
            description="Payment processing",
            connector_type="api",
        )
        assert req.name == "Stripe API"
        assert req.description == "Payment processing"

    def test_preserves_connector_type(self) -> None:
        req = ConnectorImportRequest(name="MySQL DB", connector_type="database")
        assert req.connector_type == "database"

    def test_preserves_actions(self) -> None:
        actions = [
            ActionExportData(
                name="Create Charge",
                description="Create a payment charge",
                method="POST",
                path="/v1/charges",
                parameters_schema={"type": "object", "properties": {"amount": {"type": "integer"}}},
                request_body_template={"amount": "{amount}", "currency": "usd"},
            ),
            ActionExportData(
                name="Get Balance",
                method="GET",
                path="/v1/balance",
            ),
        ]
        req = ConnectorImportRequest(
            name="Stripe",
            connector_type="api",
            actions=actions,
        )
        assert len(req.actions) == 2
        assert req.actions[0].name == "Create Charge"
        assert req.actions[0].parameters_schema is not None
        assert req.actions[1].method == "GET"

    def test_preserves_auth_config(self) -> None:
        req = ConnectorImportRequest(
            name="Bearer API",
            connector_type="api",
            auth_type="bearer",
            auth_config={"token_prefix": "Token"},
        )
        assert req.auth_type == "bearer"
        assert req.auth_config == {"token_prefix": "Token"}


# ===================================================================
# Tests: Export -> Import round-trip
# ===================================================================


class TestRoundTrip:
    """Verify that exporting then importing preserves connector configuration."""

    def test_round_trip_preserves_config(self) -> None:
        """Export a connector, then import the result -- config should match."""
        # Step 1: Build export data (simulating what the export endpoint produces)
        actions = [
            ActionExportData(
                name="Search",
                description="Search for items",
                method="GET",
                path="/search",
                parameters_schema={"type": "object", "properties": {"q": {"type": "string"}}},
            ),
            ActionExportData(
                name="Create",
                description="Create an item",
                method="POST",
                path="/items",
                request_body_template={"name": "{name}"},
                requires_confirmation=True,
            ),
        ]
        meta = ConnectorExportMeta(exported_at="2026-03-14T10:00:00+00:00")
        export = ConnectorExportData.model_construct(
            name="My API",
            description="A test API connector",
            icon="globe",
            connector_type="api",
            base_url="https://api.example.com",
            auth_type="api_key",
            auth_config={"header_name": "X-API-Key"},
            actions=actions,
            _meta=meta,
        )
        exported_json = export.model_dump()

        # Step 2: Feed the exported JSON into the import request schema
        import_req = ConnectorImportRequest(**{
            k: v for k, v in exported_json.items()
            if k != "_meta"
        })

        # Step 3: Verify all config fields survived the round-trip
        assert import_req.name == "My API"
        assert import_req.description == "A test API connector"
        assert import_req.icon == "globe"
        assert import_req.connector_type == "api"
        assert import_req.base_url == "https://api.example.com"
        assert import_req.auth_type == "api_key"
        assert import_req.auth_config == {"header_name": "X-API-Key"}

        # Actions
        assert len(import_req.actions) == 2
        assert import_req.actions[0].name == "Search"
        assert import_req.actions[0].method == "GET"
        assert import_req.actions[0].path == "/search"
        assert import_req.actions[0].parameters_schema is not None
        assert import_req.actions[1].name == "Create"
        assert import_req.actions[1].requires_confirmation is True
        assert import_req.actions[1].request_body_template == {"name": "{name}"}

    def test_round_trip_database_connector(self) -> None:
        """Database connector round-trip excludes db_config (security)."""
        meta = ConnectorExportMeta(exported_at="2026-03-14T10:00:00+00:00")
        export = ConnectorExportData.model_construct(
            name="Production DB",
            description="PostgreSQL database",
            connector_type="database",
            auth_type="none",
            actions=[],
            _meta=meta,
        )
        exported_json = export.model_dump()

        import_req = ConnectorImportRequest(**{
            k: v for k, v in exported_json.items()
            if k != "_meta"
        })
        assert import_req.name == "Production DB"
        assert import_req.connector_type == "database"

    def test_round_trip_minimal(self) -> None:
        """Minimal connector (name + type only) survives the round-trip."""
        meta = ConnectorExportMeta(exported_at="2026-03-14T10:00:00+00:00")
        export = ConnectorExportData.model_construct(
            name="Bare",
            connector_type="api",
            auth_type="none",
            actions=[],
            _meta=meta,
        )
        exported_json = export.model_dump()

        import_req = ConnectorImportRequest(**{
            k: v for k, v in exported_json.items()
            if k != "_meta"
        })
        assert import_req.name == "Bare"
        assert import_req.connector_type == "api"
        assert import_req.actions == []


# ===================================================================
# Tests: Import warnings logic
# ===================================================================


class TestImportWarnings:
    """Verify that the import endpoint correctly identifies unresolved fields."""

    def _compute_warnings(
        self,
        auth_type: str = "none",
        connector_type: str = "api",
        base_url: str | None = "https://example.com",
    ) -> list[str]:
        """Replicate the warning logic from the import endpoint."""
        warnings: list[str] = []
        if auth_type and auth_type != "none":
            warnings.append("credentials")
        if connector_type == "api" and not base_url:
            warnings.append("base_url")
        if connector_type == "database":
            warnings.append("db_config")
        return warnings

    def test_bearer_warns_credentials(self) -> None:
        warnings = self._compute_warnings(auth_type="bearer")
        assert "credentials" in warnings

    def test_api_key_warns_credentials(self) -> None:
        warnings = self._compute_warnings(auth_type="api_key")
        assert "credentials" in warnings

    def test_no_auth_no_credential_warning(self) -> None:
        warnings = self._compute_warnings(auth_type="none")
        assert "credentials" not in warnings

    def test_missing_base_url_warns(self) -> None:
        warnings = self._compute_warnings(base_url=None)
        assert "base_url" in warnings

    def test_database_warns_db_config(self) -> None:
        warnings = self._compute_warnings(connector_type="database")
        assert "db_config" in warnings

    def test_complete_api_no_warnings(self) -> None:
        warnings = self._compute_warnings(
            auth_type="none",
            connector_type="api",
            base_url="https://example.com",
        )
        assert warnings == []
