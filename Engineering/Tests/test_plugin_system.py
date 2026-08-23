"""E-013.1 plugin metadata, discovery, catalog, integration, and CLI tests."""

from __future__ import annotations

import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from Engineering.cli.app import app
from Engineering.core.exceptions import PluginError
from Engineering.ManifestSystem import (
    ManifestKind,
    ManifestValidationService,
    default_manifest_adapters,
)
from Engineering.PluginSystem import (
    PLUGIN_MANIFEST_NAME,
    PluginCatalog,
    PluginDiscoveryService,
    PluginId,
    PluginManifestReader,
    PluginService,
    PluginVersion,
)


def _manifest_data(
    plugin_id: str = "example.echo", version: str = "1.0.0"
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "plugin": {
            "id": plugin_id,
            "name": "Echo Plugin",
            "version": version,
            "sdk_version": 1,
            "description": "Provides deterministic echo metadata.",
            "entry_point": "example_echo.plugin:EchoPlugin",
            "capabilities": ["views", "commands"],
            "permissions": ["network.read"],
            "dependencies": [
                {"id": "example.base", "version": ">=1,<2"},
            ],
        },
    }


def _write_manifest(
    path: Path,
    plugin_id: str = "example.echo",
    version: str = "1.0.0",
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            _manifest_data(plugin_id, version),
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


class TestPluginModelsAndReader:
    def test_reads_canonical_manifest_into_immutable_models(
        self, tmp_path: Path
    ) -> None:
        path = _write_manifest(tmp_path / PLUGIN_MANIFEST_NAME)

        manifest = PluginManifestReader().read(path)

        assert manifest.metadata.plugin_id.value == "example.echo"
        assert manifest.metadata.version.value == "1.0.0"
        assert manifest.metadata.sdk_version.api_level == 1
        assert tuple(item.capability_id for item in manifest.capabilities) == (
            "commands",
            "views",
        )
        assert manifest.dependencies[0].version_specifier == "<2,>=1"
        assert "example_echo.plugin" not in sys.modules
        with pytest.raises(FrozenInstanceError):
            manifest.schema_version = 2  # type: ignore[misc]

    @pytest.mark.parametrize(
        "plugin_id",
        ("example", "Example.echo", "example_echo.plugin", "example..echo"),
    )
    def test_rejects_invalid_plugin_ids(self, plugin_id: str) -> None:
        with pytest.raises(PluginError, match="Plugin id"):
            PluginId(plugin_id)

    @pytest.mark.parametrize(
        "version",
        ("1.0", "01.0.0", "v1.0.0", "1.0.0+local", "not-a-version"),
    )
    def test_rejects_noncanonical_plugin_versions(self, version: str) -> None:
        with pytest.raises(PluginError, match="(?i)plugin version"):
            PluginVersion(version)

    def test_rejects_malformed_and_non_mapping_yaml(self, tmp_path: Path) -> None:
        malformed = tmp_path / "malformed.yaml"
        malformed.write_text("plugin: [", encoding="utf-8")
        sequence = tmp_path / "sequence.yaml"
        sequence.write_text("- plugin", encoding="utf-8")

        with pytest.raises(PluginError, match="malformed"):
            PluginManifestReader().read(malformed)
        with pytest.raises(PluginError, match="root object must be a mapping"):
            PluginManifestReader().read(sequence)

    def test_rejects_missing_unknown_and_secret_like_fields(
        self, tmp_path: Path
    ) -> None:
        missing = _manifest_data()
        assert isinstance(missing["plugin"], dict)
        del missing["plugin"]["name"]
        unknown = _manifest_data()
        assert isinstance(unknown["plugin"], dict)
        unknown["plugin"]["resources"] = ["../escape"]
        secret = _manifest_data()
        assert isinstance(secret["plugin"], dict)
        secret["plugin"]["api_key"] = "must-not-be-accepted"

        for name, data, message in (
            ("missing", missing, "missing keys: name"),
            ("unknown", unknown, "unknown keys: resources"),
            ("secret", secret, "Secret-like manifest field"),
        ):
            path = tmp_path / name / PLUGIN_MANIFEST_NAME
            path.parent.mkdir()
            path.write_text(yaml.safe_dump(data), encoding="utf-8")
            with pytest.raises(PluginError, match=message):
                PluginManifestReader().read(path)

    @pytest.mark.parametrize(
        ("field", "value", "message"),
        (
            ("schema_version", True, "schema_version must be an integer"),
            ("sdk_version", True, "sdk_version must be an integer"),
            ("entry_point", "../plugin.py", "module.path:ClassName"),
        ),
    )
    def test_rejects_invalid_scalar_contracts(
        self, tmp_path: Path, field: str, value: object, message: str
    ) -> None:
        data = _manifest_data()
        if field == "schema_version":
            data[field] = value
        else:
            assert isinstance(data["plugin"], dict)
            data["plugin"][field] = value
        path = tmp_path / field / PLUGIN_MANIFEST_NAME
        path.parent.mkdir()
        path.write_text(yaml.safe_dump(data), encoding="utf-8")

        with pytest.raises(PluginError, match=message):
            PluginManifestReader().read(path)

    @pytest.mark.parametrize("field", ("capabilities", "permissions"))
    def test_rejects_duplicate_metadata_items(
        self, tmp_path: Path, field: str
    ) -> None:
        data = _manifest_data()
        assert isinstance(data["plugin"], dict)
        data["plugin"][field] = ["commands", "commands"]
        path = tmp_path / field / PLUGIN_MANIFEST_NAME
        path.parent.mkdir()
        path.write_text(yaml.safe_dump(data), encoding="utf-8")

        with pytest.raises(PluginError, match="duplicate entries"):
            PluginManifestReader().read(path)

    def test_rejects_duplicate_and_self_dependencies(self, tmp_path: Path) -> None:
        duplicate = _manifest_data()
        assert isinstance(duplicate["plugin"], dict)
        duplicate["plugin"]["dependencies"] = [
            {"id": "example.base", "version": ">=1"},
            {"id": "example.base", "version": "<2"},
        ]
        self_dependency = _manifest_data()
        assert isinstance(self_dependency["plugin"], dict)
        self_dependency["plugin"]["dependencies"] = [
            {"id": "example.echo", "version": ">=1"},
        ]

        for name, data, message in (
            ("duplicate", duplicate, "Duplicate plugin dependency"),
            ("self", self_dependency, "cannot depend on itself"),
        ):
            path = tmp_path / name / PLUGIN_MANIFEST_NAME
            path.parent.mkdir()
            path.write_text(yaml.safe_dump(data), encoding="utf-8")
            with pytest.raises(PluginError, match=message):
                PluginManifestReader().read(path)


class TestPluginDiscoveryAndCatalog:
    def test_discovers_exact_filenames_in_stable_order_and_ignores_caches(
        self, tmp_path: Path
    ) -> None:
        _write_manifest(
            tmp_path / "zeta" / PLUGIN_MANIFEST_NAME,
            "example.zeta",
        )
        _write_manifest(
            tmp_path / "alpha" / PLUGIN_MANIFEST_NAME,
            "example.alpha",
        )
        _write_manifest(
            tmp_path / "node_modules" / PLUGIN_MANIFEST_NAME,
            "example.ignored",
        )
        _write_manifest(
            tmp_path / "alpha" / "not-plugin-manifest.yaml",
            "example.not-discovered",
        )

        report = PluginDiscoveryService().inspect(tmp_path)

        assert report.passed
        assert tuple(record.plugin_id for record in report.records) == (
            "example.alpha",
            "example.zeta",
        )
        assert tuple(record.relative_path for record in report.records) == (
            "alpha/plugin-manifest.yaml",
            "zeta/plugin-manifest.yaml",
        )

    def test_missing_root_is_explicit(self, tmp_path: Path) -> None:
        with pytest.raises(PluginError, match="not a directory"):
            PluginDiscoveryService().inspect(tmp_path / "missing")

    def test_aggregates_invalid_manifests_and_duplicate_id_versions(
        self, tmp_path: Path
    ) -> None:
        _write_manifest(tmp_path / "a" / PLUGIN_MANIFEST_NAME)
        _write_manifest(tmp_path / "b" / PLUGIN_MANIFEST_NAME)
        invalid = _manifest_data()
        assert isinstance(invalid["plugin"], dict)
        invalid["plugin"]["entry_point"] = "unsafe.py"
        invalid_path = tmp_path / "c" / PLUGIN_MANIFEST_NAME
        invalid_path.parent.mkdir()
        invalid_path.write_text(yaml.safe_dump(invalid), encoding="utf-8")

        report = PluginService().inspect(tmp_path)

        assert not report.passed
        assert tuple(issue.code for issue in report.issues) == (
            "plugin.identity.duplicate",
            "plugin.manifest.invalid",
        )

    def test_catalog_resolves_exact_and_highest_versions(
        self, tmp_path: Path
    ) -> None:
        _write_manifest(
            tmp_path / "v1" / PLUGIN_MANIFEST_NAME,
            version="1.0.0",
        )
        _write_manifest(
            tmp_path / "v2" / PLUGIN_MANIFEST_NAME,
            version="2.0.0",
        )
        report = PluginService().inspect(tmp_path)
        catalog = PluginCatalog(report.records)

        assert catalog.resolve("example.echo").version == "2.0.0"
        assert catalog.resolve("example.echo", "1.0.0").version == "1.0.0"
        with pytest.raises(PluginError, match="Unknown plugin"):
            catalog.resolve("example.missing")

    def test_symlinked_manifest_is_not_inspected(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _write_manifest(tmp_path / PLUGIN_MANIFEST_NAME)
        original = Path.is_symlink

        def reported_as_symlink(path: Path) -> bool:
            return path.name == PLUGIN_MANIFEST_NAME or original(path)

        monkeypatch.setattr(Path, "is_symlink", reported_as_symlink)

        report = PluginDiscoveryService().inspect(tmp_path)

        assert report.records == ()
        assert report.issues[0].code == "plugin.symlink"


class TestPluginManifestIntegrationAndCli:
    def test_registers_plural_plugin_family_with_e012(self, tmp_path: Path) -> None:
        adapters = default_manifest_adapters()
        plugin_adapter = next(
            adapter for adapter in adapters if adapter.spec.manifest_id == "ups.plugin"
        )
        assert plugin_adapter.spec.kind == ManifestKind.PLUGIN
        assert plugin_adapter.spec.allow_multiple

        _write_manifest(
            tmp_path / "one" / PLUGIN_MANIFEST_NAME,
            "example.one",
        )
        _write_manifest(
            tmp_path / "two" / PLUGIN_MANIFEST_NAME,
            "example.two",
        )
        report = ManifestValidationService().validate(tmp_path)

        assert report.passed
        assert tuple(record.manifest_id for record in report.records) == (
            "ups.plugin",
            "ups.plugin",
        )

    def test_e012_retains_plugin_owned_validation_message(
        self, tmp_path: Path
    ) -> None:
        data = _manifest_data()
        assert isinstance(data["plugin"], dict)
        data["plugin"]["entry_point"] = "../unsafe.py"
        path = tmp_path / PLUGIN_MANIFEST_NAME
        path.write_text(yaml.safe_dump(data), encoding="utf-8")

        report = ManifestValidationService().validate(tmp_path)

        assert not report.passed
        assert report.issues[0].code == "manifest.schema.invalid"
        assert "module.path:ClassName" in report.issues[0].message

    def test_manifest_types_lists_plugin_family(self) -> None:
        result = CliRunner().invoke(app, ["manifest", "types"])

        assert result.exit_code == 0
        assert "ups.plugin: plugin-manifest.yaml" in result.output
        assert "cardinality: many" in result.output

    def test_plugin_help_is_registered(self) -> None:
        result = CliRunner().invoke(app, ["plugin", "--help"])

        assert result.exit_code == 0
        assert "list" in result.output
        assert "inspect" in result.output
        assert "validate" in result.output

    def test_plugin_cli_lists_inspects_and_validates(self, tmp_path: Path) -> None:
        _write_manifest(tmp_path / "echo" / PLUGIN_MANIFEST_NAME)
        base = _manifest_data("example.base")
        assert isinstance(base["plugin"], dict)
        base["plugin"]["dependencies"] = []
        base_path = tmp_path / "base" / PLUGIN_MANIFEST_NAME
        base_path.parent.mkdir()
        base_path.write_text(yaml.safe_dump(base), encoding="utf-8")
        runner = CliRunner()

        listed = runner.invoke(app, ["plugin", "list", "--root", str(tmp_path)])
        inspected = runner.invoke(
            app,
            [
                "plugin",
                "inspect",
                "example.echo",
                "--root",
                str(tmp_path),
            ],
        )
        validated = runner.invoke(
            app, ["plugin", "validate", "--root", str(tmp_path)]
        )

        assert listed.exit_code == 0
        assert "VALID example.echo version=1.0.0" in listed.output
        assert inspected.exit_code == 0
        assert "Entry point: example_echo.plugin:EchoPlugin" in inspected.output
        assert "Permissions (metadata only): network.read" in inspected.output
        assert validated.exit_code == 0
        assert "RESOLVED example.echo@1.0.0 -> example.base@1.0.0" in validated.output
        assert (
            "Plugin validation succeeded: 2 compatible, "
            "1 dependencies resolved, 0 issues."
        ) in validated.output

    def test_plugin_cli_returns_stable_failure_for_invalid_manifest(
        self, tmp_path: Path
    ) -> None:
        path = tmp_path / PLUGIN_MANIFEST_NAME
        path.write_text("schema_version: true\nplugin: {}\n", encoding="utf-8")

        result = CliRunner().invoke(
            app, ["plugin", "validate", "--root", str(tmp_path)]
        )

        assert result.exit_code == 1
        assert "FAILED plugin.manifest.invalid" in result.output
        assert (
            "Plugin validation failed: 0 compatible, "
            "0 dependencies resolved, 1 issues."
        ) in result.output
