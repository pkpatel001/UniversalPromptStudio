"""E-014.2 provider discovery, compatibility, and catalog hardening tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from Engineering.cli.app import app
from Engineering.core.exceptions import ProviderError
from Engineering.ProviderSystem import (
    AI_PROVIDER_MANIFEST_NAME,
    ProviderCapability,
    ProviderCatalog,
    ProviderDiscoveryRoot,
    ProviderDiscoveryService,
    ProviderSdkCompatibility,
    ProviderSdkContract,
    ProviderSdkVersion,
    ProviderService,
)


def _data(
    provider_id: str,
    version: str = "1.0.0",
    *,
    sdk_version: int = 1,
    capabilities: tuple[str, ...] = ("text-generation",),
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "provider": {
            "id": provider_id,
            "name": f"{provider_id} Provider",
            "version": version,
            "sdk_version": sdk_version,
            "description": f"Metadata for {provider_id}.",
            "entry_point": "provider:ExampleProvider",
            "transport": "local",
            "authentication": "none",
            "capabilities": list(capabilities),
        },
    }


def _write(
    root: Path,
    directory: str,
    provider_id: str,
    version: str = "1.0.0",
    *,
    sdk_version: int = 1,
    capabilities: tuple[str, ...] = ("text-generation",),
) -> Path:
    path = root / directory / AI_PROVIDER_MANIFEST_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            _data(
                provider_id,
                version,
                sdk_version=sdk_version,
                capabilities=capabilities,
            ),
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def test_sdk_contract_classifies_old_compatible_and_new_levels() -> None:
    contract = ProviderSdkContract(2, 3)

    assert contract.classify(ProviderSdkVersion(1)) == ProviderSdkCompatibility.TOO_OLD
    assert contract.classify(ProviderSdkVersion(2)) == ProviderSdkCompatibility.COMPATIBLE
    assert contract.classify(ProviderSdkVersion(4)) == ProviderSdkCompatibility.TOO_NEW


@pytest.mark.parametrize(("minimum", "maximum"), ((0, 1), (2, 1), (True, 1)))
def test_rejects_invalid_sdk_contracts(minimum: int, maximum: int) -> None:
    with pytest.raises(ProviderError, match="compatibility levels"):
        ProviderSdkContract(minimum, maximum)


def test_future_sdk_metadata_is_discovered_but_not_host_compatible(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "future", "example.future-ai", sdk_version=2)

    inspection = ProviderDiscoveryService().inspect(tmp_path)
    validation = ProviderService().validate(tmp_path)

    assert inspection.passed
    assert inspection.records[0].manifest.metadata.sdk_version.api_level == 2
    assert not validation.passed
    assert validation.records == ()
    assert validation.issues[0].code == "provider.sdk.incompatible"
    assert "too-new" in validation.issues[0].message


def test_multi_root_discovery_is_stable_and_preserves_provenance(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    user = tmp_path / "user"
    _write(project, "zeta", "example.zeta-ai")
    _write(user, "alpha", "example.alpha-ai")

    report = ProviderService().validate_roots(
        (
            ProviderDiscoveryRoot("user", user),
            ProviderDiscoveryRoot("project", project),
        )
    )

    assert report.passed
    assert tuple((item.root_id, item.provider_id) for item in report.records) == (
        ("project", "example.zeta-ai"),
        ("user", "example.alpha-ai"),
    )
    assert "provider" not in sys.modules


def test_duplicate_identity_across_roots_is_an_explicit_issue(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    _write(first, "one", "example.echo-ai")
    _write(second, "two", "example.echo-ai")

    report = ProviderDiscoveryService().inspect_roots(
        (
            ProviderDiscoveryRoot("first", first),
            ProviderDiscoveryRoot("second", second),
        )
    )

    assert not report.passed
    assert report.issues[0].code == "provider.identity.duplicate"
    assert "first:one/ai-provider-manifest.yaml" in report.issues[0].message


def test_missing_root_is_reported_and_duplicate_roots_are_rejected(
    tmp_path: Path,
) -> None:
    missing = ProviderDiscoveryService().inspect_roots(
        (ProviderDiscoveryRoot("missing", tmp_path / "missing"),)
    )
    first = tmp_path / "first"
    first.mkdir()

    assert missing.issues[0].code == "provider.root.missing"
    with pytest.raises(ProviderError, match="ids must be unique"):
        ProviderDiscoveryService().inspect_roots(
            (
                ProviderDiscoveryRoot("same", first),
                ProviderDiscoveryRoot("same", tmp_path),
            )
        )
    with pytest.raises(ProviderError, match="paths must be unique"):
        ProviderDiscoveryService().inspect_roots(
            (
                ProviderDiscoveryRoot("first", first),
                ProviderDiscoveryRoot("second", first),
            )
        )


def test_ignores_cache_directories_and_does_not_follow_symlinked_directories(
    tmp_path: Path,
) -> None:
    _write(tmp_path / "node_modules", "ignored", "example.ignored-ai")
    _write(tmp_path, "valid", "example.valid-ai")
    original = Path.is_symlink

    def reported_as_symlink(path: Path) -> bool:
        return path.name == "linked" or original(path)

    linked = tmp_path / "linked"
    _write(linked, "nested", "example.linked-ai")
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(Path, "is_symlink", reported_as_symlink)
        report = ProviderDiscoveryService().inspect(tmp_path)

    assert report.passed
    assert tuple(item.provider_id for item in report.records) == ("example.valid-ai",)


def test_catalog_resolves_highest_version_and_capability_set(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        "v1",
        "example.echo-ai",
        "1.0.0",
        capabilities=("text-generation",),
    )
    _write(
        tmp_path,
        "v2",
        "example.echo-ai",
        "2.0.0",
        capabilities=("streaming", "text-generation"),
    )
    catalog = ProviderService().catalog(tmp_path)

    assert catalog.available_versions("example.echo-ai") == ("1.0.0", "2.0.0")
    assert catalog.resolve("example.echo-ai").version == "2.0.0"
    assert (
        catalog.resolve(
            "example.echo-ai",
            capabilities=(ProviderCapability.STREAMING,),
        ).version
        == "2.0.0"
    )
    assert tuple(
        item.version for item in catalog.supporting((ProviderCapability.TEXT_GENERATION,))
    ) == ("1.0.0", "2.0.0")


def test_catalog_rejects_incompatible_and_unknown_capability_match(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "future", "example.future-ai", sdk_version=2)
    record = ProviderDiscoveryService().inspect(tmp_path).records[0]

    with pytest.raises(ProviderError, match="SDK API level 2"):
        ProviderCatalog((record,))
    with pytest.raises(ProviderError, match="Unknown compatible provider"):
        ProviderCatalog().resolve(
            "example.missing-ai",
            capabilities=(ProviderCapability.VISION,),
        )
    with pytest.raises(ProviderError, match="At least one"):
        ProviderCatalog().supporting(())


def test_cli_lists_validates_and_resolves_with_explicit_roots(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        "echo",
        "example.echo-ai",
        capabilities=("streaming", "text-generation"),
    )
    runner = CliRunner()
    listed = runner.invoke(app, ["provider", "list", "--root", str(tmp_path)])
    validated = runner.invoke(app, ["provider", "validate", "--root", str(tmp_path)])
    resolved = runner.invoke(
        app,
        [
            "provider",
            "resolve",
            "example.echo-ai",
            "--root",
            str(tmp_path),
            "--capability",
            "streaming",
        ],
    )

    assert listed.exit_code == 0
    assert "VALID example.echo-ai version=1.0.0" in listed.output
    assert "Provider validation succeeded: 1 compatible, 0 issues" in listed.output
    assert validated.exit_code == 0
    assert resolved.exit_code == 0
    assert "RESOLVED example.echo-ai version=1.0.0" in resolved.output
    assert "Provider code imported: no" in resolved.output


def test_cli_requires_roots_and_rejects_unknown_capability(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "echo", "example.echo-ai")
    runner = CliRunner()

    missing_root = runner.invoke(app, ["provider", "list"])
    unknown = runner.invoke(
        app,
        [
            "provider",
            "resolve",
            "example.echo-ai",
            "--root",
            str(tmp_path),
            "--capability",
            "unknown",
        ],
    )

    assert missing_root.exit_code == 1
    assert "explicit --root" in missing_root.output
    assert unknown.exit_code == 1
    assert "must be one of" in unknown.output


def test_provider_help_preserves_manifest_inspection_and_lists_catalog_commands() -> None:
    result = CliRunner().invoke(app, ["provider", "--help"])

    assert result.exit_code == 0
    assert "inspect" in result.output
    assert "list" in result.output
    assert "resolve" in result.output
    assert "validate" in result.output
