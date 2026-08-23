"""E-013.4 package inspection, trust assessment, and install planning tests."""

from __future__ import annotations

import stat
import sys
import zipfile
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

import Engineering.PluginSystem.package as package_module
from Engineering.cli.app import app
from Engineering.core.exceptions import PluginError
from Engineering.PluginSystem import (
    PLUGIN_MANIFEST_NAME,
    PluginDiscoveryRoot,
    PluginInstallationPlanner,
    PluginPackageInspector,
    PluginTrustPolicy,
    PluginTrustStatus,
)


def _manifest(
    plugin_id: str = "example.echo",
    version: str = "1.0.0",
    *,
    sdk_version: int = 1,
    entry_point: str = "plugin:EchoPlugin",
    dependencies: tuple[tuple[str, str], ...] = (),
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "plugin": {
            "id": plugin_id,
            "name": "Echo Plugin",
            "version": version,
            "sdk_version": sdk_version,
            "description": "Package inspection fixture.",
            "entry_point": entry_point,
            "capabilities": ["commands"],
            "permissions": [],
            "dependencies": [
                {"id": dependency_id, "version": specifier}
                for dependency_id, specifier in dependencies
            ],
        },
    }


def _package(
    root: Path,
    *,
    plugin_id: str = "example.echo",
    version: str = "1.0.0",
    sdk_version: int = 1,
    entry_point: str = "plugin:EchoPlugin",
    dependencies: tuple[tuple[str, str], ...] = (),
    extra: tuple[tuple[str | zipfile.ZipInfo, str], ...] = (),
    include_module: bool = True,
) -> Path:
    path = root / f"{plugin_id}-{version}.ups-plugin.zip"
    backslash_names = tuple(
        name for name, _ in extra if isinstance(name, str) and "\\" in name
    )
    with zipfile.ZipFile(path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            PLUGIN_MANIFEST_NAME,
            yaml.safe_dump(
                _manifest(
                    plugin_id,
                    version,
                    sdk_version=sdk_version,
                    entry_point=entry_point,
                    dependencies=dependencies,
                ),
                sort_keys=False,
            ),
        )
        if include_module:
            module = entry_point.partition(":")[0].replace(".", "/") + ".py"
            archive.writestr(module, "class EchoPlugin:\n    pass\n")
        archive.writestr("README.md", "# Echo\n")
        for name, content in extra:
            if isinstance(name, str) and "\\" in name:
                zip_info = zipfile.ZipInfo("placeholder.py")
                zip_info.filename = name
                name = zip_info
            archive.writestr(name, content)
    if backslash_names:
        package_bytes = path.read_bytes()
        for raw_member in backslash_names:
            package_bytes = package_bytes.replace(
                raw_member.replace("\\", "/").encode(), raw_member.encode()
            )
        path.write_bytes(package_bytes)
    return path


def _write_installed(
    root: Path,
    plugin_id: str,
    version: str = "1.0.0",
    *,
    dependencies: tuple[tuple[str, str], ...] = (),
) -> None:
    path = root / plugin_id / version / PLUGIN_MANIFEST_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            _manifest(plugin_id, version, dependencies=dependencies),
            sort_keys=False,
        ),
        encoding="utf-8",
    )


class TestPluginPackageInspector:
    def test_inspects_hashes_and_validates_entry_point_without_import(
        self, tmp_path: Path
    ) -> None:
        package = _package(tmp_path)

        inspected = PluginPackageInspector().inspect(package)

        assert inspected.plugin_id == "example.echo"
        assert inspected.version == "1.0.0"
        assert len(inspected.sha256) == 64
        assert tuple(entry.relative_path for entry in inspected.entries) == (
            "README.md",
            "plugin-manifest.yaml",
            "plugin.py",
        )
        assert "plugin" not in sys.modules

    @pytest.mark.parametrize(
        "member",
        (
            "../escape.py",
            "/absolute.py",
            "folder\\windows.py",
            ".env",
            "CON.txt",
            "résumé.txt",
        ),
    )
    def test_rejects_unsafe_or_secret_member_paths(
        self, tmp_path: Path, member: str
    ) -> None:
        package = _package(tmp_path, extra=((member, "bad"),))

        with pytest.raises(PluginError, match="package member"):
            PluginPackageInspector().inspect(package)

    def test_rejects_casefold_duplicates_and_symlinks(self, tmp_path: Path) -> None:
        duplicate = _package(
            tmp_path,
            plugin_id="example.duplicate",
            extra=(("readme.md", "duplicate"),),
        )
        link = zipfile.ZipInfo("linked.py")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        symlink = _package(
            tmp_path,
            plugin_id="example.symlink",
            extra=((link, "plugin.py"),),
        )

        with pytest.raises(PluginError, match="duplicate member"):
            PluginPackageInspector().inspect(duplicate)
        with pytest.raises(PluginError, match="Symlinked"):
            PluginPackageInspector().inspect(symlink)

    def test_requires_canonical_name_manifest_and_entry_point(
        self, tmp_path: Path
    ) -> None:
        package = _package(tmp_path, include_module=False)
        wrong_name = tmp_path / "renamed.ups-plugin.zip"
        wrong_name.write_bytes(package.read_bytes())

        with pytest.raises(PluginError, match="missing entry-point module"):
            PluginPackageInspector().inspect(package)
        with pytest.raises(PluginError, match="filename must match"):
            PluginPackageInspector().inspect(wrong_name)

    @pytest.mark.parametrize(
        ("setting", "limit", "message"),
        (
            ("MAX_PLUGIN_PACKAGE_BYTES", 1, "maximum archive size"),
            ("MAX_PLUGIN_PACKAGE_ENTRIES", 2, "too many archive entries"),
            ("MAX_PLUGIN_MEMBER_BYTES", 1, "member exceeds the size limit"),
        ),
    )
    def test_enforces_archive_entry_and_expanded_member_limits(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        setting: str,
        limit: int,
        message: str,
    ) -> None:
        package = _package(tmp_path)
        monkeypatch.setattr(package_module, setting, limit)

        with pytest.raises(PluginError, match=message):
            PluginPackageInspector().inspect(package)

    def test_rejects_malformed_zip(self, tmp_path: Path) -> None:
        package = tmp_path / "example.echo-1.0.0.ups-plugin.zip"
        package.write_bytes(b"not a ZIP archive")

        with pytest.raises(PluginError, match="could not be inspected"):
            PluginPackageInspector().inspect(package)


class TestPluginTrustAndInstallationPlanning:
    def test_trust_requires_exact_canonical_hash(self, tmp_path: Path) -> None:
        inspected = PluginPackageInspector().inspect(_package(tmp_path))
        policy = PluginTrustPolicy()

        assert policy.assess(inspected, None).status == PluginTrustStatus.UNAPPROVED
        assert (
            policy.assess(inspected, "0" * 64).status
            == PluginTrustStatus.HASH_MISMATCH
        )
        assert policy.assess(inspected, inspected.sha256).approved
        with pytest.raises(PluginError, match="64 lowercase"):
            policy.assess(inspected, "INVALID")

    def test_ready_plan_resolves_dependencies_and_writes_nothing(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "plugins"
        root.mkdir()
        _write_installed(root, "example.base")
        package_path = _package(
            tmp_path,
            plugin_id="example.consumer",
            dependencies=(("example.base", ">=1,<2"),),
        )
        inspected = PluginPackageInspector().inspect(package_path)
        before = tuple(sorted(path.as_posix() for path in root.rglob("*")))

        plan = PluginInstallationPlanner().plan(
            package_path,
            PluginDiscoveryRoot("project", root),
            approved_sha256=inspected.sha256,
        )

        after = tuple(sorted(path.as_posix() for path in root.rglob("*")))
        assert plan.ready
        assert plan.target_relative_path == "example.consumer/1.0.0"
        assert plan.dependency_resolutions[0].resolved_version == "1.0.0"
        assert before == after

    def test_blocks_unapproved_missing_dependency_and_existing_target(
        self, tmp_path: Path
    ) -> None:
        root = tmp_path / "plugins"
        root.mkdir()
        package_path = _package(
            tmp_path,
            plugin_id="example.consumer",
            dependencies=(("example.missing", ">=1"),),
        )
        (root / "example.consumer" / "1.0.0").mkdir(parents=True)

        plan = PluginInstallationPlanner().plan(
            package_path,
            PluginDiscoveryRoot("project", root),
        )

        assert not plan.ready
        assert {issue.code for issue in plan.issues} == {
            "plugin.dependency.missing",
            "plugin.install.target-exists",
            "plugin.trust.unapproved",
        }

    def test_blocks_incompatible_sdk_and_missing_root(self, tmp_path: Path) -> None:
        package_path = _package(tmp_path, sdk_version=2)
        inspected = PluginPackageInspector().inspect(package_path)

        plan = PluginInstallationPlanner().plan(
            package_path,
            PluginDiscoveryRoot("project", tmp_path / "missing"),
            approved_sha256=inspected.sha256,
        )

        assert not plan.ready
        assert {issue.code for issue in plan.issues} == {
            "plugin.install.root-missing",
            "plugin.sdk.incompatible",
        }

    def test_blocks_installed_duplicate_identity(self, tmp_path: Path) -> None:
        root = tmp_path / "plugins"
        root.mkdir()
        _write_installed(root, "example.echo")
        package_path = _package(tmp_path)
        inspected = PluginPackageInspector().inspect(package_path)

        plan = PluginInstallationPlanner().plan(
            package_path,
            PluginDiscoveryRoot("project", root),
            approved_sha256=inspected.sha256,
        )

        assert not plan.ready
        assert {issue.code for issue in plan.issues} == {
            "plugin.install.identity-present",
            "plugin.install.target-exists",
        }


class TestPluginPackageCli:
    def test_inspect_and_approved_plan_are_read_only(self, tmp_path: Path) -> None:
        root = tmp_path / "plugins"
        root.mkdir()
        package = _package(tmp_path)
        digest = PluginPackageInspector().inspect(package).sha256
        runner = CliRunner()

        inspected = runner.invoke(app, ["plugin", "package", "inspect", str(package)])
        planned = runner.invoke(
            app,
            [
                "plugin",
                "install",
                "plan",
                str(package),
                "--root",
                str(root),
                "--approve-sha256",
                digest,
            ],
        )

        assert inspected.exit_code == 0
        assert "Signature verification: unavailable" in inspected.output
        assert planned.exit_code == 0
        assert "Plugin installation plan ready" in planned.output
        assert "Filesystem changes: none" in planned.output
        assert not (root / "example.echo").exists()

    def test_unapproved_plan_is_blocked(self, tmp_path: Path) -> None:
        root = tmp_path / "plugins"
        root.mkdir()
        package = _package(tmp_path)

        result = CliRunner().invoke(
            app,
            ["plugin", "install", "plan", str(package), "--root", str(root)],
        )

        assert result.exit_code == 1
        assert "plugin.trust.unapproved" in result.output

    def test_help_lists_package_and_install_groups(self) -> None:
        result = CliRunner().invoke(app, ["plugin", "--help"])

        assert result.exit_code == 0
        assert "package" in result.output
        assert "install" in result.output
