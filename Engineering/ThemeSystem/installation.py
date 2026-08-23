"""Controlled external-theme planning, installation, and provenance receipts."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from Engineering.core.exceptions import ThemeError

from .compatibility import ThemeSdkContract
from .discovery import THEME_STAGING_DIRECTORY_PREFIX, ThemeDiscoveryService
from .manifest import THEME_MANIFEST_NAME
from .models import ThemeDiscoveryRoot, ThemeIssue, ThemeRecord
from .package import (
    ThemePackage,
    ThemePackageInspector,
    ThemeTrustAssessment,
    ThemeTrustPolicy,
)

THEME_INSTALLATION_RECEIPT_NAME = "theme-installation.json"
THEME_INSTALLATION_RECEIPT_SCHEMA_VERSION = 1
THEME_MANAGED_DIRECTORY = "Installed"
THEME_TRUST_POLICY_ID = "explicit-external-theme-sha256-v1"


@dataclass(frozen=True, slots=True)
class ThemeInstallPlan:
    """Deterministic readiness plan for one exact external theme package."""

    package: ThemePackage
    root_id: str
    target_relative_path: str
    trust: ThemeTrustAssessment
    issues: tuple[ThemeIssue, ...] = ()

    @property
    def ready(self) -> bool:
        return not self.issues

    @property
    def summary(self) -> str:
        state = "ready" if self.ready else "blocked"
        return f"Theme installation plan {state}: {len(self.issues)} issues."


@dataclass(frozen=True, slots=True)
class ThemeInstallationResult:
    """Result of one new, non-replacing atomic installation."""

    theme_id: str
    version: str
    target: Path
    receipt: Path
    package_sha256: str
    manifest_sha256: str


class ThemeInstallationPlanner:
    """Assess trust, compatibility, collisions, and a host-owned target."""

    def __init__(
        self,
        package_inspector: ThemePackageInspector | None = None,
        discovery: ThemeDiscoveryService | None = None,
        sdk_contract: ThemeSdkContract | None = None,
        trust_policy: ThemeTrustPolicy | None = None,
    ) -> None:
        self._package_inspector = package_inspector or ThemePackageInspector()
        self._discovery = discovery or ThemeDiscoveryService()
        self._sdk_contract = sdk_contract or ThemeSdkContract()
        self._trust_policy = trust_policy or ThemeTrustPolicy()

    def plan(
        self,
        package_path: Path,
        themes_root: ThemeDiscoveryRoot,
        *,
        approved_sha256: str | None = None,
        acknowledge_external_theme: bool = False,
    ) -> ThemeInstallPlan:
        package = self._package_inspector.inspect(package_path)
        trust = self._trust_policy.assess(
            package,
            approved_sha256,
            acknowledge_external_theme=acknowledge_external_theme,
        )
        target = (
            f"{THEME_MANAGED_DIRECTORY}/{package.theme_id}/{package.version}"
        )
        issues: list[ThemeIssue] = []
        if not trust.approved:
            issues.append(
                ThemeIssue(
                    package.filename,
                    f"theme.trust.{trust.status.value}",
                    (
                        "External theme installation requires an exact package "
                        "SHA-256 and explicit external-theme acknowledgement."
                    ),
                    themes_root.root_id,
                )
            )

        package_record = ThemeRecord(
            f"{target}/{THEME_MANIFEST_NAME}",
            package.manifest,
            themes_root.root_id,
        )
        compatibility_issue = self._sdk_contract.issue_for(package_record)
        if compatibility_issue is not None:
            issues.append(compatibility_issue)

        root = themes_root.path
        root_available = True
        if root.is_symlink():
            root_available = False
            issues.append(
                ThemeIssue(
                    ".",
                    "theme.install.root-symlink",
                    "Symlinked theme installation roots are not allowed.",
                    themes_root.root_id,
                )
            )
        elif not root.resolve().is_dir():
            root_available = False
            issues.append(
                ThemeIssue(
                    ".",
                    "theme.install.root-missing",
                    "Theme installation root is not a directory.",
                    themes_root.root_id,
                )
            )

        if root_available:
            resolved_root = root.resolve()
            target_path = resolved_root.joinpath(*target.split("/"))
            if self._has_symlink_component(resolved_root, target_path.parent):
                issues.append(
                    ThemeIssue(
                        target,
                        "theme.install.target-symlink",
                        "Managed theme target must not contain symlinked components.",
                        themes_root.root_id,
                    )
                )
            elif self._has_non_directory_component(
                resolved_root, target_path.parent
            ):
                issues.append(
                    ThemeIssue(
                        target,
                        "theme.install.target-unsafe",
                        "Managed theme target contains a non-directory component.",
                        themes_root.root_id,
                    )
                )
            elif target_path.exists() or target_path.is_symlink():
                issues.append(
                    ThemeIssue(
                        target,
                        "theme.install.target-exists",
                        "Managed theme target already exists; replacement is not allowed.",
                        themes_root.root_id,
                    )
                )

            inspection = self._discovery.inspect_roots((themes_root,))
            issues.extend(inspection.issues)
            if any(
                record.theme_id == package.theme_id
                and record.version == package.version
                for record in inspection.records
            ):
                issues.append(
                    ThemeIssue(
                        package_record.relative_path,
                        "theme.install.identity-present",
                        (
                            f"Theme {package.theme_id} version {package.version} "
                            "is already present."
                        ),
                        themes_root.root_id,
                    )
                )

        return ThemeInstallPlan(
            package,
            themes_root.root_id,
            target,
            trust,
            tuple(
                sorted(
                    issues,
                    key=lambda item: (
                        item.root_id,
                        item.relative_path,
                        item.code,
                        item.message,
                    ),
                )
            ),
        )

    @staticmethod
    def _has_symlink_component(root: Path, target_parent: Path) -> bool:
        current = root
        for part in target_parent.relative_to(root).parts:
            current /= part
            if current.is_symlink():
                return True
        return False

    @staticmethod
    def _has_non_directory_component(root: Path, target_parent: Path) -> bool:
        current = root
        for part in target_parent.relative_to(root).parts:
            current /= part
            if current.exists() and not current.is_dir():
                return True
        return False


class ThemeInstaller:
    """Atomically install one ready snapshot and record deterministic provenance."""

    def install(
        self,
        plan: ThemeInstallPlan,
        themes_root: Path,
        *,
        source_label: str,
    ) -> ThemeInstallationResult:
        if (
            not isinstance(plan, ThemeInstallPlan)
            or not plan.ready
            or not plan.trust.approved
        ):
            raise ThemeError("Only a ready ThemeInstallPlan can be installed.")
        self._validate_source_label(source_label)
        self._validate_plan_snapshot(plan)
        if themes_root.is_symlink() or not themes_root.resolve().is_dir():
            raise ThemeError("Theme installation root changed after planning.")

        resolved_root = themes_root.resolve()
        target = resolved_root.joinpath(*plan.target_relative_path.split("/"))
        parent = target.parent
        current = resolved_root
        try:
            for part in parent.relative_to(resolved_root).parts:
                current /= part
                if current.is_symlink():
                    raise ThemeError("Managed theme target contains a symlinked component.")
                current.mkdir(exist_ok=True)
                if current.is_symlink() or not current.resolve().is_relative_to(
                    resolved_root
                ):
                    raise ThemeError(
                        "Managed theme target contains an unsafe path component."
                    )
        except OSError as exc:
            raise ThemeError(f"Managed theme target could not be prepared: {exc}") from exc
        if target.exists() or target.is_symlink():
            raise ThemeError("Managed theme target appeared after planning; replacement refused.")

        manifest_entry = plan.package.entries[0]
        receipt_content = self._receipt_bytes(plan, source_label)
        staging = Path(
            tempfile.mkdtemp(prefix=THEME_STAGING_DIRECTORY_PREFIX, dir=parent)
        )
        try:
            self._write_fsynced(staging / THEME_MANIFEST_NAME, plan.package.manifest_content)
            self._write_fsynced(
                staging / THEME_INSTALLATION_RECEIPT_NAME,
                receipt_content,
            )
            os.replace(staging, target)
        except OSError as exc:
            if staging.exists():
                shutil.rmtree(staging, ignore_errors=True)
            raise ThemeError(f"Theme package could not be installed atomically: {exc}") from exc

        return ThemeInstallationResult(
            plan.package.theme_id,
            plan.package.version,
            target,
            target / THEME_INSTALLATION_RECEIPT_NAME,
            plan.package.sha256,
            manifest_entry.sha256,
        )

    @staticmethod
    def _validate_source_label(value: str) -> None:
        if (
            not isinstance(value, str)
            or value.strip() != value
            or not value
            or len(value) > 240
            or any(ord(character) < 32 for character in value)
        ):
            raise ThemeError(
                "Theme source label must be 1-240 trimmed characters without controls."
            )

    @staticmethod
    def _validate_plan_snapshot(plan: ThemeInstallPlan) -> None:
        expected_target = (
            f"{THEME_MANAGED_DIRECTORY}/{plan.package.theme_id}/{plan.package.version}"
        )
        if plan.target_relative_path != expected_target:
            raise ThemeError("Theme installation plan target is not host-derived.")
        if (
            plan.trust.approved_sha256 != plan.package.sha256
            or hashlib.sha256(plan.package.archive_content).hexdigest()
            != plan.package.sha256
            or hashlib.sha256(plan.package.manifest_content).hexdigest()
            != plan.package.entries[0].sha256
        ):
            raise ThemeError("Theme installation plan snapshot integrity check failed.")

    @staticmethod
    def _receipt_bytes(plan: ThemeInstallPlan, source_label: str) -> bytes:
        entry = plan.package.entries[0]
        document = {
            "schema_version": THEME_INSTALLATION_RECEIPT_SCHEMA_VERSION,
            "theme": {
                "id": plan.package.theme_id,
                "version": plan.package.version,
            },
            "source": {
                "label": source_label,
                "package_filename": plan.package.filename,
                "package_sha256": plan.package.sha256,
            },
            "content": {
                THEME_MANIFEST_NAME: {
                    "sha256": entry.sha256,
                    "size": entry.size,
                }
            },
            "trust": {
                "policy": THEME_TRUST_POLICY_ID,
                "approved_sha256": plan.trust.approved_sha256,
                "external_theme_acknowledged": (
                    plan.trust.external_theme_acknowledged
                ),
            },
        }
        return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")

    @staticmethod
    def _write_fsynced(path: Path, content: bytes) -> None:
        with path.open("xb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())


__all__ = [
    "THEME_INSTALLATION_RECEIPT_NAME",
    "THEME_INSTALLATION_RECEIPT_SCHEMA_VERSION",
    "THEME_MANAGED_DIRECTORY",
    "THEME_TRUST_POLICY_ID",
    "ThemeInstallPlan",
    "ThemeInstallationPlanner",
    "ThemeInstallationResult",
    "ThemeInstaller",
]
