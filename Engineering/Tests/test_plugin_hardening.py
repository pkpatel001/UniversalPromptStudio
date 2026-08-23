"""E-013.2 discovery, compatibility, dependency, and catalog hardening tests."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from Engineering.cli.app import app
from Engineering.core.exceptions import PluginError
from Engineering.ManifestSystem import ManifestValidationService
from Engineering.PluginSystem import (
    PLUGIN_MANIFEST_NAME,
    PluginCatalog,
    PluginDiscoveryRoot,
    PluginDiscoveryService,
    PluginManifestReader,
    PluginSdkCompatibility,
    PluginSdkContract,
    PluginSdkVersion,
    PluginService,
)


def _data(
    plugin_id: str,
    version: str = "1.0.0",
    *,
    sdk_version: int = 1,
    dependencies: tuple[tuple[str, str], ...] = (),
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "plugin": {
            "id": plugin_id,
            "name": f"{plugin_id} Plugin",
            "version": version,
            "sdk_version": sdk_version,
            "description": f"Metadata for {plugin_id}.",
            "entry_point": "example.plugin:Plugin",
            "capabilities": [],
            "permissions": [],
            "dependencies": [
                {"id": dependency_id, "version": specifier}
                for dependency_id, specifier in dependencies
            ],
        },
    }


def _write(
    root: Path,
    directory: str,
    plugin_id: str,
    version: str = "1.0.0",
    *,
    sdk_version: int = 1,
    dependencies: tuple[tuple[str, str], ...] = (),
) -> Path:
    path = root / directory / PLUGIN_MANIFEST_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            _data(
                plugin_id,
                version,
                sdk_version=sdk_version,
                dependencies=dependencies,
            ),
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


class TestPluginSdkCompatibility:
    def test_reader_parses_future_sdk_level_without_claiming_compatibility(
        self, tmp_path: Path
    ) -> None:
        path = _write(
            tmp_path,
            "future",
            "example.future",
            sdk_version=2,
        )

        manifest = PluginManifestReader().read(path)
        manifest_report = ManifestValidationService().validate(tmp_path)
        report = PluginService().validate(tmp_path)

        assert manifest.metadata.sdk_version.api_level == 2
        assert manifest_report.passed
        assert not report.passed
        assert report.issues[0].code == "plugin.sdk.incompatible"
        assert "too-new" in report.issues[0].message

    def test_contract_classifies_old_compatible_and_new_levels(self) -> None:
        contract = PluginSdkContract(2, 3)

        assert contract.classify(PluginSdkVersion(1)) == PluginSdkCompatibility.TOO_OLD
        assert (
            contract.classify(PluginSdkVersion(2))
            == PluginSdkCompatibility.COMPATIBLE
        )
        assert contract.classify(PluginSdkVersion(4)) == PluginSdkCompatibility.TOO_NEW

    @pytest.mark.parametrize(
        ("minimum", "maximum"),
        ((0, 1), (2, 1), (True, 1)),
    )
    def test_rejects_invalid_sdk_contracts(
        self, minimum: int, maximum: int
    ) -> None:
        with pytest.raises(PluginError, match="compatibility levels"):
            PluginSdkContract(minimum, maximum)

    def test_custom_host_contract_can_accept_future_level(
        self, tmp_path: Path
    ) -> None:
        _write(
            tmp_path,
            "future",
            "example.future",
            sdk_version=2,
        )

        report = PluginService(sdk_contract=PluginSdkContract(1, 2)).validate(
            tmp_path
        )

        assert report.passed
        assert report.summary == (
            "Plugin validation succeeded: 1 compatible, "
            "0 dependencies resolved, 0 issues."
        )


class TestPluginMultiRootDiscovery:
    def test_aggregates_labeled_roots_in_stable_root_order(
        self, tmp_path: Path
    ) -> None:
        project = tmp_path / "project"
        user = tmp_path / "user"
        _write(project, "zeta", "example.zeta")
        _write(user, "alpha", "example.alpha")

        report = PluginService().validate_roots(
            (
                PluginDiscoveryRoot("user", user),
                PluginDiscoveryRoot("project", project),
            )
        )

        assert report.passed
        assert tuple(
            (record.root_id, record.plugin_id) for record in report.records
        ) == (
            ("project", "example.zeta"),
            ("user", "example.alpha"),
        )

    def test_rejects_duplicate_identity_across_roots(
        self, tmp_path: Path
    ) -> None:
        project = tmp_path / "project"
        user = tmp_path / "user"
        _write(project, "one", "example.echo")
        _write(user, "two", "example.echo")

        report = PluginDiscoveryService().inspect_roots(
            (
                PluginDiscoveryRoot("project", project),
                PluginDiscoveryRoot("user", user),
            )
        )

        assert not report.passed
        assert report.issues[0].code == "plugin.identity.duplicate"
        assert report.issues[0].root_id == "user"
        assert "project:one/plugin-manifest.yaml" in report.issues[0].message

    def test_aggregates_missing_root_as_a_stable_issue(self, tmp_path: Path) -> None:
        report = PluginService().validate_roots(
            (PluginDiscoveryRoot("user", tmp_path / "missing"),)
        )

        assert not report.passed
        assert report.issues[0].code == "plugin.root.missing"
        assert report.issues[0].root_id == "user"

    def test_rejects_duplicate_root_ids_and_paths(self, tmp_path: Path) -> None:
        first = tmp_path / "first"
        second = tmp_path / "second"
        first.mkdir()
        second.mkdir()
        discovery = PluginDiscoveryService()

        with pytest.raises(PluginError, match="ids must be unique"):
            discovery.inspect_roots(
                (
                    PluginDiscoveryRoot("same", first),
                    PluginDiscoveryRoot("same", second),
                )
            )
        with pytest.raises(PluginError, match="paths must be unique"):
            discovery.inspect_roots(
                (
                    PluginDiscoveryRoot("first", first),
                    PluginDiscoveryRoot("second", first),
                )
            )


class TestPluginDependencyResolution:
    def test_selects_highest_version_satisfying_constraint(
        self, tmp_path: Path
    ) -> None:
        _write(tmp_path, "base-v1", "example.base", "1.0.0")
        _write(tmp_path, "base-v15", "example.base", "1.5.0")
        _write(tmp_path, "base-v2", "example.base", "2.0.0")
        _write(
            tmp_path,
            "consumer",
            "example.consumer",
            dependencies=(("example.base", ">=1,<2"),),
        )

        report = PluginService().validate(tmp_path)

        assert report.passed
        assert len(report.dependency_resolutions) == 1
        resolution = report.dependency_resolutions[0]
        assert resolution.dependency_plugin_id == "example.base"
        assert resolution.resolved_version == "1.5.0"

    def test_reports_missing_dependency_without_cascading(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "consumer",
            "example.consumer",
            dependencies=(("example.missing", ">=1"),),
        )

        report = PluginService().validate(tmp_path)

        assert tuple(issue.code for issue in report.issues) == (
            "plugin.dependency.missing",
        )
        assert report.dependency_resolutions == ()
        with pytest.raises(PluginError, match="Plugin validation failed"):
            PluginService().catalog(tmp_path)

    def test_reports_unsatisfied_dependency_with_available_versions(
        self, tmp_path: Path
    ) -> None:
        _write(tmp_path, "base", "example.base", "2.0.0")
        _write(
            tmp_path,
            "consumer",
            "example.consumer",
            dependencies=(("example.base", "<2"),),
        )

        report = PluginService().validate(tmp_path)

        assert report.issues[0].code == "plugin.dependency.unsatisfied"
        assert "available versions: 2.0.0" in report.issues[0].message

    def test_reports_dependency_cycle_deterministically(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "alpha",
            "example.alpha",
            dependencies=(("example.beta", ">=1"),),
        )
        _write(
            tmp_path,
            "beta",
            "example.beta",
            dependencies=(("example.alpha", ">=1"),),
        )

        report = PluginService().validate(tmp_path)

        assert tuple(issue.code for issue in report.issues) == (
            "plugin.dependency.cycle",
        )
        assert (
            "example.alpha@1.0.0 -> example.beta@1.0.0 -> "
            "example.alpha@1.0.0"
        ) in report.issues[0].message

    def test_compatibility_failure_suppresses_dependency_cascade(
        self, tmp_path: Path
    ) -> None:
        _write(
            tmp_path,
            "future",
            "example.future",
            sdk_version=2,
            dependencies=(("example.missing", ">=1"),),
        )

        report = PluginService().validate(tmp_path)

        assert tuple(issue.code for issue in report.issues) == (
            "plugin.sdk.incompatible",
        )


class TestPluginCatalogHardening:
    def test_lists_versions_and_resolves_requirement(self, tmp_path: Path) -> None:
        _write(tmp_path, "v1", "example.echo", "1.0.0")
        _write(tmp_path, "v2", "example.echo", "2.0.0")
        records = PluginDiscoveryService().inspect(tmp_path).records
        catalog = PluginCatalog(records)

        assert catalog.available_versions("example.echo") == ("1.0.0", "2.0.0")
        assert catalog.resolve_requirement("example.echo", "<2").version == "1.0.0"
        with pytest.raises(PluginError, match="No compatible version"):
            catalog.resolve_requirement("example.echo", ">=3")
        with pytest.raises(PluginError, match="non-empty"):
            catalog.resolve_requirement("example.echo", "")

    def test_catalog_rejects_incompatible_sdk_record(self, tmp_path: Path) -> None:
        _write(
            tmp_path,
            "future",
            "example.future",
            sdk_version=2,
        )
        record = PluginDiscoveryService().inspect(tmp_path).records[0]

        with pytest.raises(PluginError, match="SDK API level 2"):
            PluginCatalog((record,))


class TestPluginHardeningCli:
    def test_dependencies_command_supports_repeatable_roots(
        self, tmp_path: Path
    ) -> None:
        project = tmp_path / "project"
        user = tmp_path / "user"
        _write(
            project,
            "consumer",
            "example.consumer",
            dependencies=(("example.base", ">=1"),),
        )
        _write(user, "base", "example.base")

        result = CliRunner().invoke(
            app,
            [
                "plugin",
                "dependencies",
                "--root",
                str(project),
                "--root",
                str(user),
            ],
        )

        assert result.exit_code == 0
        assert "RESOLVED example.consumer@1.0.0 -> example.base@1.0.0" in result.output
        assert "2 compatible, 1 dependencies resolved, 0 issues" in result.output

    def test_help_lists_dependencies_command(self) -> None:
        result = CliRunner().invoke(app, ["plugin", "--help"])

        assert result.exit_code == 0
        assert "dependencies" in result.output
