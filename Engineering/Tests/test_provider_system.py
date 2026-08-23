"""E-014.1 AI-provider SDK metadata and manifest integration tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from Engineering.cli.app import app
from Engineering.core.exceptions import ProviderError
from Engineering.ManifestSystem import (
    ManifestKind,
    ManifestValidationService,
    default_manifest_adapters,
)
from Engineering.ProviderSystem import (
    AI_PROVIDER_MANIFEST_NAME,
    ProviderAuthentication,
    ProviderCapability,
    ProviderManifestReader,
    ProviderTransport,
)


def _data(**provider_changes: object) -> dict[str, object]:
    provider: dict[str, object] = {
        "id": "example.echo-ai",
        "name": "Echo AI",
        "version": "1.0.0",
        "sdk_version": 1,
        "description": "Deterministic provider metadata fixture.",
        "entry_point": "echo_provider:EchoProvider",
        "transport": "local",
        "authentication": "none",
        "capabilities": ["streaming", "text-generation"],
    }
    provider.update(provider_changes)
    return {"schema_version": 1, "provider": provider}


def _write(path: Path, data: dict[str, object] | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(data or _data(), sort_keys=False),
        encoding="utf-8",
    )
    return path


def test_reads_strict_manifest_without_import_or_network(tmp_path: Path) -> None:
    path = _write(tmp_path / AI_PROVIDER_MANIFEST_NAME)

    manifest = ProviderManifestReader().read(path)

    assert manifest.metadata.provider_id.value == "example.echo-ai"
    assert manifest.metadata.transport == ProviderTransport.LOCAL
    assert manifest.metadata.authentication == ProviderAuthentication.NONE
    assert manifest.capabilities == (
        ProviderCapability.STREAMING,
        ProviderCapability.TEXT_GENERATION,
    )
    assert "echo_provider" not in sys.modules


@pytest.mark.parametrize(
    ("changes", "message"),
    (
        ({"id": "Echo"}, "Provider id"),
        ({"version": "1.0"}, "exactly major.minor.patch"),
        ({"sdk_version": True}, "must be an integer"),
        ({"entry_point": "../provider.py"}, "module.path:ClassName"),
        ({"transport": "socket"}, "must be one of"),
        ({"authentication": "password"}, "must be one of"),
        ({"capabilities": []}, "at least one capability"),
        (
            {"capabilities": ["streaming", "streaming"]},
            "duplicate entries",
        ),
        ({"capabilities": ["unknown"]}, "must be one of"),
    ),
)
def test_rejects_invalid_provider_metadata(changes: dict[str, object], message: str) -> None:
    with pytest.raises(ProviderError, match=message):
        ProviderManifestReader().read_text(yaml.safe_dump(_data(**changes), sort_keys=False))


def test_rejects_unknown_missing_and_secret_like_fields() -> None:
    unknown = _data(extra="value")
    missing = _data()
    assert isinstance(missing["provider"], dict)
    del missing["provider"]["description"]
    secret = _data(api_key="do-not-store")
    reader = ProviderManifestReader()

    with pytest.raises(ProviderError, match="unknown keys: extra"):
        reader.read_text(yaml.safe_dump(unknown))
    with pytest.raises(ProviderError, match="missing keys: description"):
        reader.read_text(yaml.safe_dump(missing))
    with pytest.raises(ProviderError, match="Secret-like"):
        reader.read_text(yaml.safe_dump(secret))


def test_shared_manifest_catalog_registers_plural_provider_family(
    tmp_path: Path,
) -> None:
    adapters = default_manifest_adapters()
    adapter = next(item for item in adapters if item.spec.manifest_id == "ups.ai-provider")
    assert adapter.spec.kind == ManifestKind.AI_PROVIDER
    assert adapter.spec.allow_multiple
    _write(tmp_path / "one" / AI_PROVIDER_MANIFEST_NAME)
    _write(
        tmp_path / "two" / AI_PROVIDER_MANIFEST_NAME,
        _data(id="example.second-ai"),
    )

    report = ManifestValidationService().validate(tmp_path)

    assert report.passed
    assert tuple(item.manifest_id for item in report.records) == (
        "ups.ai-provider",
        "ups.ai-provider",
    )


def test_shared_manifest_catalog_retains_provider_validation_message(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / AI_PROVIDER_MANIFEST_NAME,
        _data(entry_point="../unsafe.py"),
    )

    report = ManifestValidationService().validate(tmp_path)

    assert not report.passed
    assert report.issues[0].code == "manifest.schema.invalid"
    assert "module.path:ClassName" in report.issues[0].message


def test_provider_cli_inspects_without_execution(tmp_path: Path) -> None:
    path = _write(tmp_path / AI_PROVIDER_MANIFEST_NAME)

    result = CliRunner().invoke(app, ["provider", "inspect", str(path)])

    assert result.exit_code == 0
    assert "Provider: example.echo-ai" in result.output
    assert "Capabilities: streaming, text-generation" in result.output
    assert "Provider code imported: no" in result.output
    assert "Network requests: none" in result.output
    assert "Credential access: none" in result.output


def test_provider_cli_reports_invalid_manifest(tmp_path: Path) -> None:
    path = _write(
        tmp_path / AI_PROVIDER_MANIFEST_NAME,
        _data(capabilities=[]),
    )

    result = CliRunner().invoke(app, ["provider", "inspect", str(path)])

    assert result.exit_code == 1
    assert "at least one capability" in result.output


def test_manifest_types_and_provider_help_are_registered() -> None:
    types = CliRunner().invoke(app, ["manifest", "types"])
    help_result = CliRunner().invoke(app, ["provider", "--help"])

    assert types.exit_code == 0
    assert "ups.ai-provider: ai-provider-manifest.yaml" in types.output
    assert "cardinality: many" in types.output
    assert help_result.exit_code == 0
    assert "inspect" in help_result.output
