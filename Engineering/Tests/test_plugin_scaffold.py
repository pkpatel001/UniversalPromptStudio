"""E-013.3 controlled plugin scaffold generation tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from Engineering.cli.app import app
from Engineering.CodeGeneration import OverwritePolicy, ProjectGenerationInfo
from Engineering.core.exceptions import PluginError
from Engineering.PluginSystem import (
    PLUGIN_MANIFEST_NAME,
    PluginDependency,
    PluginId,
    PluginManifestReader,
    PluginScaffoldRequest,
    PluginScaffoldService,
)
from Engineering.Templates import TemplateCategory, built_in_definition_repository


def _project() -> ProjectGenerationInfo:
    return ProjectGenerationInfo("Project", "P", "1.0.0", "Company", "MPL-2.0")


def _service(root: Path) -> PluginScaffoldService:
    return PluginScaffoldService.built_in(root, _project())


def _request(**changes: object) -> PluginScaffoldRequest:
    values: dict[str, object] = {
        "plugin_id": "example.echo-tools",
        "name": "Echo Tools Plugin",
        "description": "Provides deterministic echo tooling.",
        "capabilities": ("views", "commands"),
        "permissions": ("network.read",),
        "dependencies": (
            PluginDependency(PluginId("example.base"), ">=1,<2"),
        ),
    }
    values.update(changes)
    return PluginScaffoldRequest(**values)  # type: ignore[arg-type]


def test_builtin_plugin_template_is_valid_and_bounded() -> None:
    definition = built_in_definition_repository().resolve("plugin.python-basic")

    assert definition.metadata.category == TemplateCategory.PLUGIN
    assert tuple(item.relative_path for item in definition.artifacts) == (
        "plugin-manifest.yaml",
        "plugin.py",
        "README.md",
    )


def test_generates_valid_scaffold_through_e009_and_e008(tmp_path: Path) -> None:
    result = _service(tmp_path).generate(_request())
    root = tmp_path / "Plugins" / "example-echo-tools"

    assert result.execution.report.success
    assert result.destination == "Plugins/example-echo-tools"
    assert result.execution.manifest is not None
    assert result.execution.manifest.verify(root).passed
    manifest = PluginManifestReader().read(root / PLUGIN_MANIFEST_NAME)
    assert manifest == result.plugin_manifest
    assert manifest.metadata.entry_point.value == "plugin:EchoToolsPlugin"
    assert [item.capability_id for item in manifest.capabilities] == [
        "commands",
        "views",
    ]
    source = (root / "plugin.py").read_text(encoding="utf-8")
    assert "class EchoToolsPlugin:" in source
    assert "def activate(self, context: PluginRegistrationContext)" in source
    assert "def deactivate(self, context: PluginRegistrationContext)" in source


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    result = _service(tmp_path).generate(_request(dry_run=True))

    assert result.execution.report.success
    assert result.execution.report.dry_run
    assert result.execution.manifest is None
    assert not (tmp_path / "Plugins").exists()


def test_conflicts_by_default_and_overwrites_only_when_explicit(tmp_path: Path) -> None:
    service = _service(tmp_path)
    first = service.generate(_request())
    assert first.execution.report.success
    readme = tmp_path / "Plugins" / "example-echo-tools" / "README.md"
    readme.write_text("user content\n", encoding="utf-8")

    conflict = service.generate(_request())
    assert not conflict.execution.report.success
    assert readme.read_text(encoding="utf-8") == "user content\n"

    replaced = service.generate(_request(overwrite=OverwritePolicy.ALLOWED))
    assert replaced.execution.report.success
    assert "# Echo Tools Plugin" in readme.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "destination",
    ("outside", "Plugins/nested/plugin", "../Plugins/example", "C:/Plugins/example"),
)
def test_rejects_destinations_outside_direct_plugin_root(
    tmp_path: Path, destination: str
) -> None:
    with pytest.raises(PluginError, match="direct child of Plugins"):
        _service(tmp_path).generate(_request(destination=destination))


def test_rejects_duplicate_and_self_dependency_metadata(tmp_path: Path) -> None:
    with pytest.raises(PluginError, match="duplicate capability"):
        _service(tmp_path).generate(_request(capabilities=("commands", "commands")))
    with pytest.raises(PluginError, match="cannot depend on itself"):
        _service(tmp_path).generate(
            _request(
                dependencies=(
                    PluginDependency(PluginId("example.echo-tools"), ">=1"),
                )
            )
        )


def test_cli_exposes_controlled_generation_and_dry_run() -> None:
    runner = CliRunner()
    help_result = runner.invoke(app, ["generate", "plugin", "--help"])
    dry_run = runner.invoke(
        app,
        [
            "generate",
            "plugin",
            "example.cli-dry-run",
            "--capability",
            "commands",
            "--dry-run",
        ],
    )

    assert help_result.exit_code == 0
    assert "--dependency" in help_result.output
    assert "--overwrite" in help_result.output
    assert dry_run.exit_code == 0
    assert "Dry-run Generation completed" in dry_run.output
    assert "Destination: Plugins/example-cli-dry-run" in dry_run.output


def test_cli_rejects_invalid_dependency_syntax() -> None:
    result = CliRunner().invoke(
        app,
        ["generate", "plugin", "example.invalid", "--dependency", "missing-spec"],
    )

    assert result.exit_code == 1
    assert "PLUGIN_ID=SPECIFIER" in result.output
