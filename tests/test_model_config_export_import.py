"""Tests for model config export/import schemas and logic."""

from __future__ import annotations

import json

import pytest

from fim_one.web.schemas.model_provider import (
    GroupExportData,
    GroupModelRef,
    ModelConfigExportEnvelope,
    ModelConfigExportResponse,
    ModelConfigImportRequest,
    ModelConfigImportSummary,
    ModelExportData,
    ProviderExportData,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _sample_export_envelope() -> ModelConfigExportEnvelope:
    """Build a representative export envelope for testing."""
    return ModelConfigExportEnvelope(
        exported_at="2026-03-21T10:00:00+00:00",
        providers=[
            ProviderExportData(
                name="Uniapi",
                base_url="https://api.uniapi.io/v1",
                api_key=None,
                is_active=True,
                models=[
                    ModelExportData(
                        name="GPT-5.4",
                        model_name="gpt-5.4",
                        temperature=None,
                        max_output_tokens=None,
                        context_size=None,
                        json_mode_enabled=True,
                        is_active=True,
                    ),
                    ModelExportData(
                        name="GPT-5.4 Mini",
                        model_name="gpt-5.4-mini",
                        json_mode_enabled=True,
                        is_active=True,
                    ),
                ],
            ),
            ProviderExportData(
                name="Anthropic",
                base_url="https://api.anthropic.com/v1",
                api_key=None,
                is_active=True,
                models=[
                    ModelExportData(
                        name="Claude Opus 4",
                        model_name="claude-opus-4-20250514",
                        temperature=0.7,
                        max_output_tokens=8192,
                        context_size=200000,
                        json_mode_enabled=True,
                        is_active=True,
                    ),
                ],
            ),
        ],
        groups=[
            GroupExportData(
                name="OpenAI",
                description="OpenAI models via Uniapi",
                general_model=GroupModelRef(provider="Uniapi", model_name="gpt-5.4"),
                fast_model=GroupModelRef(provider="Uniapi", model_name="gpt-5.4-mini"),
                reasoning_model=None,
                is_active=False,
            ),
            GroupExportData(
                name="Anthropic",
                general_model=GroupModelRef(
                    provider="Anthropic", model_name="claude-opus-4-20250514"
                ),
                fast_model=None,
                reasoning_model=None,
                is_active=True,
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Schema construction & serialization tests
# ---------------------------------------------------------------------------


class TestExportSchemas:
    """Test export schema construction and serialization."""

    def test_model_export_data_defaults(self) -> None:
        m = ModelExportData(name="Test", model_name="test-model")
        assert m.temperature is None
        assert m.max_output_tokens is None
        assert m.context_size is None
        assert m.json_mode_enabled is True
        assert m.is_active is True

    def test_provider_export_data_api_key_always_none(self) -> None:
        p = ProviderExportData(name="Test", base_url="https://example.com")
        assert p.api_key is None

        # Even if someone tries to set it, the type annotation forces None
        p2 = ProviderExportData(
            name="Test", base_url="https://example.com", api_key=None
        )
        assert p2.api_key is None

    def test_group_model_ref(self) -> None:
        ref = GroupModelRef(provider="Uniapi", model_name="gpt-5.4")
        assert ref.provider == "Uniapi"
        assert ref.model_name == "gpt-5.4"

    def test_group_export_data_nullable_slots(self) -> None:
        g = GroupExportData(name="Empty Group")
        assert g.general_model is None
        assert g.fast_model is None
        assert g.reasoning_model is None
        assert g.description is None
        assert g.is_active is False

    def test_full_export_response_roundtrip(self) -> None:
        """Export response can be serialized to JSON and back."""
        envelope = _sample_export_envelope()
        response = ModelConfigExportResponse(fim_model_config_v1=envelope)

        # Serialize
        data = response.model_dump()
        json_str = json.dumps(data, indent=2)

        # Deserialize back
        parsed = json.loads(json_str)
        restored = ModelConfigExportResponse.model_validate(parsed)

        assert len(restored.fim_model_config_v1.providers) == 2
        assert len(restored.fim_model_config_v1.groups) == 2
        assert restored.fim_model_config_v1.providers[0].name == "Uniapi"
        assert restored.fim_model_config_v1.providers[0].api_key is None
        assert len(restored.fim_model_config_v1.providers[0].models) == 2

    def test_export_envelope_structure(self) -> None:
        """Verify the top-level key is 'fim_model_config_v1'."""
        envelope = _sample_export_envelope()
        response = ModelConfigExportResponse(fim_model_config_v1=envelope)
        data = response.model_dump()

        assert "fim_model_config_v1" in data
        inner = data["fim_model_config_v1"]
        assert "exported_at" in inner
        assert "providers" in inner
        assert "groups" in inner


# ---------------------------------------------------------------------------
# Import schema tests
# ---------------------------------------------------------------------------


class TestImportSchemas:
    """Test import request validation."""

    def test_import_request_with_api_keys(self) -> None:
        envelope = _sample_export_envelope()
        req = ModelConfigImportRequest(
            fim_model_config_v1=envelope,
            api_keys={"Uniapi": "sk-uniapi-123", "Anthropic": "sk-ant-456"},
        )
        assert req.api_keys["Uniapi"] == "sk-uniapi-123"
        assert req.api_keys["Anthropic"] == "sk-ant-456"

    def test_import_request_api_keys_defaults_to_empty(self) -> None:
        envelope = _sample_export_envelope()
        req = ModelConfigImportRequest(fim_model_config_v1=envelope)
        assert req.api_keys == {}

    def test_import_request_from_export_json(self) -> None:
        """The export JSON format can be used directly as import input."""
        envelope = _sample_export_envelope()
        export_resp = ModelConfigExportResponse(fim_model_config_v1=envelope)
        export_json = export_resp.model_dump()

        # Add api_keys for import
        import_data = {**export_json, "api_keys": {"Uniapi": "sk-test"}}
        req = ModelConfigImportRequest.model_validate(import_data)

        assert len(req.fim_model_config_v1.providers) == 2
        assert req.api_keys == {"Uniapi": "sk-test"}

    def test_import_summary_schema(self) -> None:
        summary = ModelConfigImportSummary(
            created={"providers": 2, "models": 3, "groups": 1},
            skipped={"providers": 0, "models": 1, "groups": 0},
            warnings=["Group 'X' general_model: model 'A/b' not found, set to null"],
        )
        data = summary.model_dump()
        assert data["created"]["providers"] == 2
        assert data["created"]["models"] == 3
        assert data["created"]["groups"] == 1
        assert data["skipped"]["models"] == 1
        assert len(data["warnings"]) == 1

    def test_import_summary_empty_warnings(self) -> None:
        summary = ModelConfigImportSummary(
            created={"providers": 0, "models": 0, "groups": 0},
            skipped={"providers": 0, "models": 0, "groups": 0},
        )
        assert summary.warnings == []


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Test edge cases in the schemas."""

    def test_empty_export(self) -> None:
        """Export with no providers or groups."""
        envelope = ModelConfigExportEnvelope(
            exported_at="2026-03-21T00:00:00Z",
            providers=[],
            groups=[],
        )
        response = ModelConfigExportResponse(fim_model_config_v1=envelope)
        data = response.model_dump()
        assert data["fim_model_config_v1"]["providers"] == []
        assert data["fim_model_config_v1"]["groups"] == []

    def test_provider_with_no_models(self) -> None:
        p = ProviderExportData(name="EmptyProvider", base_url="https://example.com")
        assert p.models == []

    def test_model_with_all_fields(self) -> None:
        m = ModelExportData(
            name="Full Model",
            model_name="full-model",
            temperature=0.5,
            max_output_tokens=4096,
            context_size=128000,
            json_mode_enabled=False,
            is_active=False,
        )
        data = m.model_dump()
        assert data["temperature"] == 0.5
        assert data["max_output_tokens"] == 4096
        assert data["context_size"] == 128000
        assert data["json_mode_enabled"] is False
        assert data["is_active"] is False

    def test_group_with_all_slots_filled(self) -> None:
        g = GroupExportData(
            name="Full Group",
            description="All slots filled",
            general_model=GroupModelRef(provider="A", model_name="a1"),
            fast_model=GroupModelRef(provider="B", model_name="b1"),
            reasoning_model=GroupModelRef(provider="C", model_name="c1"),
            is_active=True,
        )
        data = g.model_dump()
        assert data["general_model"]["provider"] == "A"
        assert data["fast_model"]["provider"] == "B"
        assert data["reasoning_model"]["provider"] == "C"
