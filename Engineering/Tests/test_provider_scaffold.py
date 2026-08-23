"""E-014.3 controlled AI-provider scaffold generation tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from Engineering.cli.app import app
from Engineering.CodeGeneration import OverwritePolicy, ProjectGenerationInfo
from Engineering.core.exceptions import ProviderError
from Engineering.ProviderSystem import (
    AI_PROVIDER_MANIFEST_NAME,
    ProviderAuthentication,
    ProviderCapability,
    ProviderManifestReader,
    ProviderScaffoldRequest,
    ProviderScaffoldService,
    ProviderTransport,
)
from Engineering.Templates import TemplateCategory, built_in_definition_repository


def _project() -> ProjectGenerationInfo:
    return ProjectGenerationInfo("Project", "P", "1.0.0", "Company", "MPL-2.0")


def _service(root: Path) -> ProviderScaffoldService:
    return ProviderScaffoldService.built_in(root, _project())


def _request(**changes: object) -> ProviderScaffoldRequest:
    values: dict[str, object] = {
        "provider_id": "example.echo-ai",
        "name": "Echo AI Provider",
        "description": "Provides deterministic echo metadata.",
        "transport": "http",
        "authentication": "api-key",
        "capabilities": ("text-generation", "streaming"),
    }
    values.update(changes)
    return ProviderScaffoldRequest(**values)  # type: ignore[arg-type]


def test_builtin_provider_template_is_valid_and_bounded() -> None:
    definition = built_in_definition_repository().resolve("provider.python-basic")

    assert definition.metadata.category == TemplateCategory.PROVIDER
    assert tuple(item.relative_path for item in definition.artifacts) == (
        "ai-provider-manifest.yaml",
        "provider.py",
        "README.md",
    )


def test_generates_valid_scaffold_through_e009_and_e008(tmp_path: Path) -> None:
    result = _service(tmp_path).generate(_request())
    root = tmp_path / "Providers" / "example-echo-ai"

    assert result.execution.report.success
    assert result.destination == "Providers/example-echo-ai"
    assert result.execution.manifest is not None
    assert result.execution.manifest.verify(root).passed
    manifest = ProviderManifestReader().read(root / AI_PROVIDER_MANIFEST_NAME)
    assert manifest == result.provider_manifest
    assert manifest.metadata.entry_point.value == "provider:EchoAiProvider"
    assert manifest.metadata.transport == ProviderTransport.HTTP
    assert manifest.metadata.authentication == ProviderAuthentication.API_KEY
    assert manifest.capabilities == (
        ProviderCapability.STREAMING,
        ProviderCapability.TEXT_GENERATION,
    )
    source = (root / "provider.py").read_text(encoding="utf-8")
    assert "class EchoAiProvider:" in source
    assert "def execute(" not in source
    assert "Backend" not in source


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    result = _service(tmp_path).generate(_request(dry_run=True))

    assert result.execution.report.success
    assert result.execution.report.dry_run
    assert result.execution.manifest is None
    assert not (tmp_path / "Providers").exists()


def test_conflicts_by_default_and_overwrites_only_when_explicit(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    first = service.generate(_request())
    assert first.execution.report.success
    readme = tmp_path / "Providers" / "example-echo-ai" / "README.md"
    readme.write_text("user content\n", encoding="utf-8")

    conflict = service.generate(_request())
    assert not conflict.execution.report.success
    assert readme.read_text(encoding="utf-8") == "user content\n"

    replaced = service.generate(_request(overwrite=OverwritePolicy.ALLOWED))
    assert replaced.execution.report.success
    assert "# Echo AI Provider" in readme.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "destination",
    (
        "outside",
        "Providers/nested/provider",
        "../Providers/example",
        "C:/Providers/example",
    ),
)
def test_rejects_destinations_outside_direct_provider_root(
    tmp_path: Path, destination: str
) -> None:
    with pytest.raises(ProviderError, match="direct child of Providers"):
        _service(tmp_path).generate(_request(destination=destination))


@pytest.mark.parametrize(
    ("changes", "message"),
    (
        ({"capabilities": ("streaming", "streaming")}, "duplicate capability"),
        ({"capabilities": ("unknown",)}, "capability must be one of"),
        ({"transport": "socket"}, "transport must be one of"),
        ({"authentication": "password"}, "authentication must be one of"),
        ({"class_name": "private_provider"}, "public Python class"),
    ),
)
def test_rejects_invalid_scaffold_inputs(
    tmp_path: Path, changes: dict[str, object], message: str
) -> None:
    with pytest.raises(ProviderError, match=message):
        _service(tmp_path).generate(_request(**changes))


def test_cli_exposes_controlled_generation_and_dry_run() -> None:
    runner = CliRunner()
    help_result = runner.invoke(app, ["generate", "provider", "--help"])
    dry_run = runner.invoke(
        app,
        [
            "generate",
            "provider",
            "example.cli-ai",
            "--transport",
            "http",
            "--authentication",
            "api-key",
            "--capability",
            "streaming",
            "--dry-run",
        ],
    )

    assert help_result.exit_code == 0
    assert "--authentication" in help_result.output
    assert "--overwrite" in help_result.output
    assert dry_run.exit_code == 0
    assert "Dry-run Generation completed: 3 created" in dry_run.output
    assert "Destination: Providers/example-cli-ai" in dry_run.output


def test_cli_rejects_invalid_capability() -> None:
    result = CliRunner().invoke(
        app,
        [
            "generate",
            "provider",
            "example.invalid-ai",
            "--capability",
            "unknown",
            "--dry-run",
        ],
    )

    assert result.exit_code == 1
    assert "capability must be one of" in result.output
