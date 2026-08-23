"""E-015.7 external-theme package, trust, provenance, and installation tests."""

from __future__ import annotations

import json
import os
import stat
import zipfile
from dataclasses import replace
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

import Engineering.ThemeSystem.package as package_module
from Engineering.cli.app import app
from Engineering.core.exceptions import ThemeError
from Engineering.ThemeSystem import (
    THEME_MANIFEST_NAME,
    ThemeDiscoveryRoot,
    ThemeInstallationPlanner,
    ThemeInstaller,
    ThemeInstallPlan,
    ThemePackageInspector,
    ThemeService,
    ThemeTrustPolicy,
    ThemeTrustStatus,
)


def _colors() -> dict[str, str]:
    return {
        "canvas": "#F6F8F8",
        "surface": "#FFFFFF",
        "surface_muted": "#EDF3F2",
        "text": "#182026",
        "text_muted": "#627277",
        "border": "#DFE7E7",
        "primary": "#276A73",
        "primary_text": "#FFFFFF",
        "sidebar": "#12181C",
        "sidebar_text": "#F7FBFB",
        "focus": "#2F7D89",
    }


def _manifest(
    theme_id: str = "example.slate",
    version: str = "1.0.0",
    *,
    sdk_version: int = 1,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "theme": {
            "id": theme_id,
            "name": "Slate",
            "version": version,
            "sdk_version": sdk_version,
            "description": "External declarative theme fixture.",
            "default_appearance": "light",
            "palettes": [{"appearance": "light", "colors": _colors()}],
        },
    }


def _package(
    root: Path,
    theme_id: str = "example.slate",
    version: str = "1.0.0",
    *,
    sdk_version: int = 1,
    extra: tuple[tuple[str | zipfile.ZipInfo, str], ...] = (),
) -> Path:
    path = root / f"{theme_id}-{version}.ups-theme.zip"
    with zipfile.ZipFile(path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            THEME_MANIFEST_NAME,
            yaml.safe_dump(
                _manifest(theme_id, version, sdk_version=sdk_version),
                sort_keys=False,
            ),
        )
        for name, content in extra:
            archive.writestr(name, content)
    return path


def _approved_plan(package: Path, root: Path) -> ThemeInstallPlan:
    inspected = ThemePackageInspector().inspect(package)
    return ThemeInstallationPlanner().plan(
        package,
        ThemeDiscoveryRoot("project", root),
        approved_sha256=inspected.sha256,
        acknowledge_external_theme=True,
    )


def test_inspector_hashes_one_data_only_manifest_without_extraction(tmp_path: Path) -> None:
    package = _package(tmp_path)
    before = tuple(tmp_path.iterdir())

    inspected = ThemePackageInspector().inspect(package)

    assert inspected.theme_id == "example.slate"
    assert inspected.version == "1.0.0"
    assert len(inspected.sha256) == 64
    assert inspected.entries[0].relative_path == THEME_MANIFEST_NAME
    assert tuple(tmp_path.iterdir()) == before


def test_inspector_rejects_extra_nested_symlink_and_wrong_name(tmp_path: Path) -> None:
    extra = _package(tmp_path, theme_id="example.extra", extra=(("README.md", "no"),))
    link = zipfile.ZipInfo(THEME_MANIFEST_NAME)
    link.create_system = 3
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    linked = tmp_path / "example.linked-1.0.0.ups-theme.zip"
    with zipfile.ZipFile(linked, mode="w") as archive:
        archive.writestr(link, "target")
    canonical = _package(tmp_path, theme_id="example.named")
    wrong = tmp_path / "renamed.ups-theme.zip"
    wrong.write_bytes(canonical.read_bytes())

    with pytest.raises(ThemeError, match="contain only"):
        ThemePackageInspector().inspect(extra)
    with pytest.raises(ThemeError, match="Symlinked"):
        ThemePackageInspector().inspect(linked)
    with pytest.raises(ThemeError, match="filename must match"):
        ThemePackageInspector().inspect(wrong)


def test_inspector_enforces_archive_and_manifest_limits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = _package(tmp_path)
    monkeypatch.setattr(package_module, "MAX_THEME_PACKAGE_BYTES", 1)
    with pytest.raises(ThemeError, match="maximum archive size"):
        ThemePackageInspector().inspect(package)

    monkeypatch.setattr(package_module, "MAX_THEME_PACKAGE_BYTES", 512 * 1024)
    monkeypatch.setattr(package_module, "MAX_THEME_MANIFEST_BYTES", 1)
    with pytest.raises(ThemeError, match="manifest exceeds"):
        ThemePackageInspector().inspect(package)


def test_trust_requires_hash_pin_and_separate_external_acknowledgement(
    tmp_path: Path,
) -> None:
    inspected = ThemePackageInspector().inspect(_package(tmp_path))
    policy = ThemeTrustPolicy()

    assert policy.assess(inspected, None).status == ThemeTrustStatus.UNAPPROVED
    assert (
        policy.assess(inspected, "0" * 64).status
        == ThemeTrustStatus.HASH_MISMATCH
    )
    assert (
        policy.assess(inspected, inspected.sha256).status
        == ThemeTrustStatus.ACKNOWLEDGEMENT_REQUIRED
    )
    assert policy.assess(
        inspected,
        inspected.sha256,
        acknowledge_external_theme=True,
    ).approved
    with pytest.raises(ThemeError, match="64 lowercase"):
        policy.assess(inspected, "INVALID")


def test_ready_plan_is_read_only_and_uses_host_owned_target(tmp_path: Path) -> None:
    root = tmp_path / "Themes"
    root.mkdir()
    package = _package(tmp_path)
    before = tuple(root.rglob("*"))

    plan = _approved_plan(package, root)

    assert plan.ready
    assert plan.target_relative_path == "Installed/example.slate/1.0.0"
    assert tuple(root.rglob("*")) == before


def test_discovery_ignores_reserved_atomic_staging_directories(tmp_path: Path) -> None:
    root = tmp_path / "Themes"
    staged = root / "Installed" / "example.slate" / ".ups-theme-interrupted"
    staged.mkdir(parents=True)
    (staged / THEME_MANIFEST_NAME).write_text(
        yaml.safe_dump(_manifest(), sort_keys=False),
        encoding="utf-8",
    )

    report = ThemeService().validate(root)

    assert report.passed
    assert report.records == ()


def test_plan_blocks_untrusted_incompatible_and_existing_identity(tmp_path: Path) -> None:
    root = tmp_path / "Themes"
    root.mkdir()
    existing = root / "existing" / THEME_MANIFEST_NAME
    existing.parent.mkdir()
    existing.write_text(
        yaml.safe_dump(_manifest(), sort_keys=False),
        encoding="utf-8",
    )
    package = _package(tmp_path)
    untrusted = ThemeInstallationPlanner().plan(
        package,
        ThemeDiscoveryRoot("project", root),
    )
    future = _package(tmp_path, theme_id="example.future", sdk_version=2)
    incompatible = _approved_plan(future, root)

    assert {issue.code for issue in untrusted.issues} == {
        "theme.install.identity-present",
        "theme.trust.unapproved",
    }
    assert {issue.code for issue in incompatible.issues} == {
        "theme.sdk.incompatible"
    }


def test_plan_blocks_symlinked_and_non_directory_managed_components(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = _package(tmp_path)
    non_directory_root = tmp_path / "non-directory" / "Themes"
    non_directory_root.mkdir(parents=True)
    (non_directory_root / "Installed").write_text("not a directory", encoding="utf-8")

    blocked_file = _approved_plan(package, non_directory_root)
    assert {issue.code for issue in blocked_file.issues} == {
        "theme.install.target-unsafe"
    }

    symlink_root = tmp_path / "symlink" / "Themes"
    symlink_root.mkdir(parents=True)
    original_is_symlink = Path.is_symlink

    def report_managed_root_as_symlink(path: Path) -> bool:
        return path.name == "Installed" or original_is_symlink(path)

    monkeypatch.setattr(Path, "is_symlink", report_managed_root_as_symlink)
    blocked_link = _approved_plan(package, symlink_root)
    assert {issue.code for issue in blocked_link.issues} == {
        "theme.install.target-symlink"
    }


def test_atomic_install_writes_exact_manifest_and_provenance_receipt(
    tmp_path: Path,
) -> None:
    root = tmp_path / "Themes"
    root.mkdir()
    package = _package(tmp_path)
    plan = _approved_plan(package, root)

    result = ThemeInstaller().install(
        plan,
        root,
        source_label="local-review/example-slate",
    )

    assert result.target == root / "Installed" / "example.slate" / "1.0.0"
    assert (result.target / THEME_MANIFEST_NAME).read_bytes() == (
        plan.package.manifest_content
    )
    receipt = json.loads(result.receipt.read_text(encoding="utf-8"))
    assert receipt["source"]["package_sha256"] == result.package_sha256
    assert receipt["source"]["label"] == "local-review/example-slate"
    assert receipt["content"][THEME_MANIFEST_NAME]["sha256"] == result.manifest_sha256
    assert receipt["trust"]["policy"] == "explicit-external-theme-sha256-v1"
    assert ThemeService().catalog(root).resolve("example.slate").version == "1.0.0"
    assert not (tmp_path / "Frontend").exists()


def test_install_rejects_replacement_and_invalid_source_label(tmp_path: Path) -> None:
    root = tmp_path / "Themes"
    root.mkdir()
    package = _package(tmp_path)
    plan = _approved_plan(package, root)
    installer = ThemeInstaller()

    with pytest.raises(ThemeError, match="source label"):
        installer.install(plan, root, source_label=" untrimmed")
    installer.install(plan, root, source_label="reviewed-local")
    with pytest.raises(ThemeError, match="appeared after planning"):
        installer.install(plan, root, source_label="reviewed-local")


def test_installer_rechecks_plan_snapshot_integrity(tmp_path: Path) -> None:
    root = tmp_path / "Themes"
    root.mkdir()
    package = _package(tmp_path)
    plan = _approved_plan(package, root)
    tampered = replace(
        plan,
        package=replace(plan.package, archive_content=b"tampered"),
    )

    with pytest.raises(ThemeError, match="snapshot integrity"):
        ThemeInstaller().install(tampered, root, source_label="reviewed-local")
    assert not (root / "Installed").exists()


def test_failed_atomic_replace_leaves_no_target_or_staging_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "Themes"
    root.mkdir()
    package = _package(tmp_path)
    plan = _approved_plan(package, root)

    def fail_replace(source: object, destination: object) -> None:
        raise OSError("simulated replacement failure")

    monkeypatch.setattr(os, "replace", fail_replace)
    with pytest.raises(ThemeError, match="atomically"):
        ThemeInstaller().install(
            plan,
            root,
            source_label="reviewed-local",
        )

    parent = root / "Installed" / "example.slate"
    assert not (parent / "1.0.0").exists()
    assert not tuple(parent.glob(".ups-theme-*"))


def test_cli_inspects_plans_and_installs_without_activation(tmp_path: Path) -> None:
    root = tmp_path / "Themes"
    root.mkdir()
    package = _package(tmp_path)
    digest = ThemePackageInspector().inspect(package).sha256
    runner = CliRunner()

    inspected = runner.invoke(app, ["theme", "package", "inspect", str(package)])
    blocked = runner.invoke(
        app,
        [
            "theme",
            "install",
            "plan",
            str(package),
            "--root",
            str(root),
            "--approve-sha256",
            digest,
        ],
    )
    installed = runner.invoke(
        app,
        [
            "theme",
            "install",
            "apply",
            str(package),
            "--root",
            str(root),
            "--approve-sha256",
            digest,
            "--acknowledge-external-theme",
            "--source-label",
            "reviewed-local",
        ],
    )

    assert inspected.exit_code == 0
    assert "Publisher authentication: unavailable" in inspected.output
    assert blocked.exit_code == 1
    assert "theme.trust.acknowledgement-required" in blocked.output
    assert installed.exit_code == 0, installed.output
    assert "Frontend catalog synchronized: no" in installed.output
    assert "Theme activated: no" in installed.output
    assert (root / "Installed" / "example.slate" / "1.0.0").is_dir()
