"""E-015.8 managed-theme integrity and reversible lifecycle tests."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from Engineering.cli.app import app
from Engineering.core.exceptions import ThemeError
from Engineering.Tests.test_theme_installation import _manifest, _package
from Engineering.ThemeSystem import (
    THEME_DISABLED_DIRECTORY,
    THEME_INSTALLATION_RECEIPT_NAME,
    THEME_MANIFEST_NAME,
    ThemeDiscoveryRoot,
    ThemeInstallationPlanner,
    ThemeInstallationReceiptReader,
    ThemeInstaller,
    ThemeLifecycleAction,
    ThemeLifecycleManager,
    ThemeLifecyclePlan,
    ThemeLifecyclePlanner,
    ThemeManagedState,
    ThemeManagedThemeService,
    ThemeService,
)


def _install(tmp_path: Path) -> tuple[Path, str]:
    root = tmp_path / "Themes"
    root.mkdir(parents=True)
    package = _package(tmp_path)
    inspected_plan = ThemeInstallationPlanner().plan(
        package,
        ThemeDiscoveryRoot("project", root),
    )
    digest = inspected_plan.package.sha256
    plan = ThemeInstallationPlanner().plan(
        package,
        ThemeDiscoveryRoot("project", root),
        approved_sha256=digest,
        acknowledge_external_theme=True,
    )
    assert plan.ready
    ThemeInstaller().install(plan, root, source_label="reviewed-local")
    return root, digest


def _active(root: Path) -> Path:
    return root / "Installed" / "example.slate" / "1.0.0"


def _disabled(root: Path) -> Path:
    return root / THEME_DISABLED_DIRECTORY / "example.slate" / "1.0.0"


def _lifecycle_plan(
    root: Path,
    digest: str,
    action: ThemeLifecycleAction,
) -> ThemeLifecyclePlan:
    return ThemeLifecyclePlanner().plan(
        ThemeDiscoveryRoot("project", root),
        "example.slate",
        "1.0.0",
        action,
        approved_package_sha256=digest,
        acknowledge_lifecycle_change=True,
    )


def test_receipt_reader_returns_strict_typed_provenance(tmp_path: Path) -> None:
    root, digest = _install(tmp_path)

    receipt = ThemeInstallationReceiptReader().read(
        _active(root) / THEME_INSTALLATION_RECEIPT_NAME
    )

    assert receipt.theme_id.value == "example.slate"
    assert receipt.version.value == "1.0.0"
    assert receipt.package_sha256 == digest
    assert receipt.approved_sha256 == digest
    assert receipt.external_theme_acknowledged
    assert receipt.manifest_size > 0


@pytest.mark.parametrize("mutation", ("duplicate", "unknown", "approval"))
def test_receipt_reader_rejects_duplicate_unknown_and_inconsistent_data(
    tmp_path: Path, mutation: str
) -> None:
    root, _ = _install(tmp_path)
    receipt_path = _active(root) / THEME_INSTALLATION_RECEIPT_NAME
    original = receipt_path.read_text(encoding="utf-8")
    if mutation == "duplicate":
        receipt_path.write_text(
            original.replace("{\n", '{\n  "schema_version": 1,\n', 1),
            encoding="utf-8",
        )
        message = "duplicate key"
    else:
        document = json.loads(original)
        if mutation == "unknown":
            document["unexpected"] = True
            message = "unknown keys"
        else:
            document["trust"]["approved_sha256"] = "0" * 64
            message = "does not match"
        receipt_path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ThemeError, match=message):
        ThemeInstallationReceiptReader().read(receipt_path)


def test_managed_discovery_fails_closed_for_tampering_and_missing_receipt(
    tmp_path: Path,
) -> None:
    root, _ = _install(tmp_path)
    manifest = _active(root) / THEME_MANIFEST_NAME
    manifest.write_bytes(manifest.read_bytes().replace(b"#276A73", b"#336699"))

    tampered = ThemeService().validate(root)

    assert not tampered.passed
    assert tampered.records == ()
    assert tampered.issues[0].code == "theme.provenance.invalid"
    assert "SHA-256" in tampered.issues[0].message

    root_two, _ = _install(tmp_path / "second")
    (_active(root_two) / THEME_INSTALLATION_RECEIPT_NAME).unlink()
    missing = ThemeService().validate(root_two)
    assert not missing.passed
    assert missing.issues[0].code == "theme.provenance.invalid"
    assert "missing" in missing.issues[0].message


def test_project_authored_theme_does_not_require_installation_receipt(
    tmp_path: Path,
) -> None:
    root = tmp_path / "Themes"
    manifest = root / "project-authored" / THEME_MANIFEST_NAME
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        yaml.safe_dump(_manifest(theme_id="example.authored"), sort_keys=False),
        encoding="utf-8",
    )

    report = ThemeService().validate(root)

    assert report.passed
    assert report.records[0].theme_id == "example.authored"


def test_managed_inventory_reports_active_disabled_and_integrity_failures(
    tmp_path: Path,
) -> None:
    root, digest = _install(tmp_path)
    service = ThemeManagedThemeService()

    active = service.verify(ThemeDiscoveryRoot("project", root))
    plan = _lifecycle_plan(root, digest, ThemeLifecycleAction.DISABLE)
    ThemeLifecycleManager().apply(plan, root)
    disabled = service.verify(ThemeDiscoveryRoot("project", root))
    (_disabled(root) / "unexpected.txt").write_text("unexpected", encoding="utf-8")
    invalid = service.verify(ThemeDiscoveryRoot("project", root))

    assert active.passed and active.records[0].state == ThemeManagedState.ACTIVE
    assert disabled.passed and disabled.records[0].state == ThemeManagedState.DISABLED
    assert not invalid.passed
    assert invalid.issues[0].code == "theme.managed.integrity-invalid"


def test_disable_plan_requires_exact_hash_acknowledgement_and_writes_nothing(
    tmp_path: Path,
) -> None:
    root, digest = _install(tmp_path)
    planner = ThemeLifecyclePlanner()
    lifecycle_root = ThemeDiscoveryRoot("project", root)

    blocked = planner.plan(
        lifecycle_root,
        "example.slate",
        "1.0.0",
        ThemeLifecycleAction.DISABLE,
    )
    mismatch = planner.plan(
        lifecycle_root,
        "example.slate",
        "1.0.0",
        ThemeLifecycleAction.DISABLE,
        approved_package_sha256="0" * 64,
        acknowledge_lifecycle_change=True,
    )
    ready = _lifecycle_plan(root, digest, ThemeLifecycleAction.DISABLE)

    assert {issue.code for issue in blocked.issues} == {
        "theme.lifecycle.acknowledgement-required",
        "theme.lifecycle.hash-unapproved",
    }
    assert {issue.code for issue in mismatch.issues} == {
        "theme.lifecycle.hash-mismatch"
    }
    assert ready.ready
    assert _active(root).is_dir()
    assert not _disabled(root).exists()


def test_disable_and_restore_are_atomic_reversible_and_catalog_safe(tmp_path: Path) -> None:
    root, digest = _install(tmp_path)
    original_manifest = (_active(root) / THEME_MANIFEST_NAME).read_bytes()
    original_receipt = (_active(root) / THEME_INSTALLATION_RECEIPT_NAME).read_bytes()
    manager = ThemeLifecycleManager()

    disabled_result = manager.apply(
        _lifecycle_plan(root, digest, ThemeLifecycleAction.DISABLE),
        root,
    )
    inactive_catalog = ThemeService().validate(root)
    assert not _active(root).exists()
    restore_plan = _lifecycle_plan(root, digest, ThemeLifecycleAction.RESTORE)
    restored_result = manager.apply(restore_plan, root)

    assert disabled_result.action == ThemeLifecycleAction.DISABLE
    assert inactive_catalog.passed and inactive_catalog.records == ()
    assert restored_result.action == ThemeLifecycleAction.RESTORE
    assert (_active(root) / THEME_MANIFEST_NAME).read_bytes() == original_manifest
    assert (
        _active(root) / THEME_INSTALLATION_RECEIPT_NAME
    ).read_bytes() == original_receipt
    assert ThemeService().catalog(root).resolve("example.slate").version == "1.0.0"


def test_lifecycle_rejects_path_traversal_target_collision_and_changed_source(
    tmp_path: Path,
) -> None:
    root, digest = _install(tmp_path)
    planner = ThemeLifecyclePlanner()
    lifecycle_root = ThemeDiscoveryRoot("project", root)

    with pytest.raises(ThemeError, match="Theme id"):
        planner.plan(
            lifecycle_root,
            "../escape",
            "1.0.0",
            ThemeLifecycleAction.DISABLE,
        )

    target = _disabled(root)
    target.mkdir(parents=True)
    collision = _lifecycle_plan(root, digest, ThemeLifecycleAction.DISABLE)
    assert "theme.lifecycle.target-exists" in {
        issue.code for issue in collision.issues
    }
    target.rmdir()

    ready = _lifecycle_plan(root, digest, ThemeLifecycleAction.DISABLE)
    manifest = _active(root) / THEME_MANIFEST_NAME
    manifest.write_bytes(manifest.read_bytes().replace(b"#276A73", b"#112233"))
    with pytest.raises(ThemeError, match="SHA-256"):
        ThemeLifecycleManager().apply(ready, root)
    assert _active(root).is_dir()


def test_failed_atomic_lifecycle_move_preserves_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, digest = _install(tmp_path)
    plan = _lifecycle_plan(root, digest, ThemeLifecycleAction.DISABLE)

    def fail_replace(source: object, destination: object) -> None:
        raise OSError("simulated move failure")

    monkeypatch.setattr(os, "replace", fail_replace)
    with pytest.raises(ThemeError, match="atomically"):
        ThemeLifecycleManager().apply(plan, root)
    assert _active(root).is_dir()
    assert not _disabled(root).exists()


def test_cli_verifies_plans_disables_and_restores_without_implicit_sync(
    tmp_path: Path,
) -> None:
    root, digest = _install(tmp_path)
    runner = CliRunner()

    verified = runner.invoke(
        app, ["theme", "install", "verify", "--root", str(root)]
    )
    planned = runner.invoke(
        app,
        [
            "theme",
            "install",
            "disable",
            "example.slate",
            "--version",
            "1.0.0",
            "--approve-package-sha256",
            digest,
            "--acknowledge-disable",
            "--root",
            str(root),
        ],
    )
    disabled = runner.invoke(
        app,
        [
            "theme",
            "install",
            "disable",
            "example.slate",
            "--version",
            "1.0.0",
            "--approve-package-sha256",
            digest,
            "--acknowledge-disable",
            "--apply",
            "--root",
            str(root),
        ],
    )
    restored = runner.invoke(
        app,
        [
            "theme",
            "install",
            "restore",
            "example.slate",
            "--version",
            "1.0.0",
            "--approve-package-sha256",
            digest,
            "--acknowledge-restore",
            "--apply",
            "--root",
            str(root),
        ],
    )

    assert verified.exit_code == 0
    assert "state=active" in verified.output
    assert planned.exit_code == 0
    assert "Filesystem changes: none" in planned.output
    assert _active(root).is_dir()
    assert disabled.exit_code == 0, disabled.output
    assert "DISABLED example.slate" in disabled.output
    assert "Frontend catalog synchronized: no" in disabled.output
    assert restored.exit_code == 0, restored.output
    assert "RESTORED example.slate" in restored.output
    assert _active(root).is_dir()
