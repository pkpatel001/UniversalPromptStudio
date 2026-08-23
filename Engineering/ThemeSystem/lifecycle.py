"""E-015.8 managed-theme inventory and reversible atomic lifecycle changes."""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from Engineering.core.exceptions import ThemeError

from .discovery import THEME_STAGING_DIRECTORY_PREFIX, ThemeDiscoveryService
from .models import ThemeDiscoveryRoot, ThemeId, ThemeVersion
from .provenance import (
    THEME_DISABLED_DIRECTORY,
    THEME_MANAGED_DIRECTORY,
    ThemeManagedIssue,
    ThemeManagedRecord,
    ThemeManagedState,
    ThemeManagedThemeVerifier,
    ThemeManagedVerificationReport,
    validate_theme_sha256,
)


class ThemeLifecycleAction(StrEnum):
    """Supported reversible managed-theme state transitions."""

    DISABLE = "disable"
    RESTORE = "restore"


@dataclass(frozen=True, slots=True)
class ThemeLifecyclePlan:
    """Non-mutating readiness plan for one exact managed theme transition."""

    action: ThemeLifecycleAction
    root_id: str
    theme_id: str
    version: str
    source_relative_path: str
    target_relative_path: str
    approved_package_sha256: str | None
    lifecycle_acknowledged: bool
    record: ThemeManagedRecord | None = None
    issues: tuple[ThemeManagedIssue, ...] = ()

    @property
    def ready(self) -> bool:
        return not self.issues and self.record is not None

    @property
    def summary(self) -> str:
        state = "ready" if self.ready else "blocked"
        return f"Theme {self.action.value} plan {state}: {len(self.issues)} issues."


@dataclass(frozen=True, slots=True)
class ThemeLifecycleResult:
    """Result of one atomic managed-theme state transition."""

    action: ThemeLifecycleAction
    theme_id: str
    version: str
    source: Path
    target: Path
    package_sha256: str


class ThemeManagedThemeService:
    """Inventory active and disabled managed themes without mutating them."""

    def __init__(self, verifier: ThemeManagedThemeVerifier | None = None) -> None:
        self._verifier = verifier or ThemeManagedThemeVerifier()

    def verify(self, themes_root: ThemeDiscoveryRoot) -> ThemeManagedVerificationReport:
        root = themes_root.path
        if root.is_symlink():
            return ThemeManagedVerificationReport(
                issues=(
                    ThemeManagedIssue(
                        ThemeManagedState.ACTIVE,
                        ".",
                        "theme.managed.root-symlink",
                        "Symlinked theme roots cannot be verified.",
                        themes_root.root_id,
                    ),
                )
            )
        resolved_root = root.resolve()
        if not resolved_root.is_dir():
            return ThemeManagedVerificationReport(
                issues=(
                    ThemeManagedIssue(
                        ThemeManagedState.ACTIVE,
                        ".",
                        "theme.managed.root-missing",
                        "Theme root is not a directory.",
                        themes_root.root_id,
                    ),
                )
            )

        records: list[ThemeManagedRecord] = []
        issues: list[ThemeManagedIssue] = []
        for state, name in (
            (ThemeManagedState.ACTIVE, THEME_MANAGED_DIRECTORY),
            (ThemeManagedState.DISABLED, THEME_DISABLED_DIRECTORY),
        ):
            container_records, container_issues = self._verify_container(
                resolved_root / name,
                state,
                themes_root.root_id,
            )
            records.extend(container_records)
            issues.extend(container_issues)

        records.sort(key=lambda item: (item.theme_id, item.version, item.state.value))
        seen: dict[tuple[str, str], ThemeManagedRecord] = {}
        for record in records:
            key = (record.theme_id, record.version)
            previous = seen.get(key)
            if previous is not None:
                issues.append(
                    ThemeManagedIssue(
                        record.state,
                        record.relative_path,
                        "theme.managed.identity-duplicate",
                        (
                            f"Managed theme {record.theme_id} version {record.version} "
                            f"also exists in {previous.state.value} state."
                        ),
                        record.root_id,
                    )
                )
            else:
                seen[key] = record
        return ThemeManagedVerificationReport(
            tuple(records),
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

    def _verify_container(
        self,
        container: Path,
        state: ThemeManagedState,
        root_id: str,
    ) -> tuple[list[ThemeManagedRecord], list[ThemeManagedIssue]]:
        if not container.exists() and not container.is_symlink():
            return [], []
        if container.is_symlink() or not container.is_dir():
            return [], [
                ThemeManagedIssue(
                    state,
                    container.name,
                    "theme.managed.container-invalid",
                    "Managed theme state container must be a regular directory.",
                    root_id,
                )
            ]
        records: list[ThemeManagedRecord] = []
        issues: list[ThemeManagedIssue] = []
        try:
            identity_paths = tuple(
                sorted(container.iterdir(), key=lambda item: item.name)
            )
        except OSError:
            return [], [
                ThemeManagedIssue(
                    state,
                    container.name,
                    "theme.managed.container-unreadable",
                    "Managed theme state container could not be inspected.",
                    root_id,
                )
            ]
        for identity_path in identity_paths:
            if identity_path.name.startswith(THEME_STAGING_DIRECTORY_PREFIX):
                continue
            if identity_path.is_symlink() or not identity_path.is_dir():
                issues.append(
                    self._layout_issue(state, identity_path.name, root_id)
                )
                continue
            try:
                version_paths = tuple(
                    sorted(identity_path.iterdir(), key=lambda item: item.name)
                )
            except OSError:
                issues.append(
                    ThemeManagedIssue(
                        state,
                        f"{container.name}/{identity_path.name}",
                        "theme.managed.identity-unreadable",
                        "Managed theme identity directory could not be inspected.",
                        root_id,
                    )
                )
                continue
            for version_path in version_paths:
                relative = f"{container.name}/{identity_path.name}/{version_path.name}"
                if version_path.name.startswith(THEME_STAGING_DIRECTORY_PREFIX):
                    continue
                try:
                    records.append(
                        self._verifier.verify_directory(
                            version_path,
                            container,
                            state,
                            root_id=root_id,
                        )
                    )
                except (OSError, ThemeError) as exc:
                    issues.append(
                        ThemeManagedIssue(
                            state,
                            relative,
                            "theme.managed.integrity-invalid",
                            str(exc),
                            root_id,
                        )
                    )
        return records, issues

    @staticmethod
    def _layout_issue(
        state: ThemeManagedState, relative_path: str, root_id: str
    ) -> ThemeManagedIssue:
        return ThemeManagedIssue(
            state,
            relative_path,
            "theme.managed.layout-invalid",
            "Managed theme identity entries must be regular directories.",
            root_id,
        )


class ThemeLifecyclePlanner:
    """Plan one exact disable or restore without moving any files."""

    def __init__(
        self,
        managed_service: ThemeManagedThemeService | None = None,
        discovery: ThemeDiscoveryService | None = None,
    ) -> None:
        self._managed_service = managed_service or ThemeManagedThemeService()
        self._discovery = discovery or ThemeDiscoveryService()

    def plan(
        self,
        themes_root: ThemeDiscoveryRoot,
        theme_id: str,
        version: str,
        action: ThemeLifecycleAction,
        *,
        approved_package_sha256: str | None = None,
        acknowledge_lifecycle_change: bool = False,
    ) -> ThemeLifecyclePlan:
        if not isinstance(action, ThemeLifecycleAction):
            raise ThemeError("Theme lifecycle action must be ThemeLifecycleAction.")
        canonical_theme_id = ThemeId(theme_id).value
        canonical_version = ThemeVersion(version).value
        source_state = (
            ThemeManagedState.ACTIVE
            if action == ThemeLifecycleAction.DISABLE
            else ThemeManagedState.DISABLED
        )
        target_state = (
            ThemeManagedState.DISABLED
            if action == ThemeLifecycleAction.DISABLE
            else ThemeManagedState.ACTIVE
        )
        source_prefix = self._state_directory(source_state)
        target_prefix = self._state_directory(target_state)
        source = f"{source_prefix}/{canonical_theme_id}/{canonical_version}"
        target = f"{target_prefix}/{canonical_theme_id}/{canonical_version}"
        issues: list[ThemeManagedIssue] = []

        report = self._managed_service.verify(themes_root)
        issues.extend(report.issues)
        matches = tuple(
            record
            for record in report.records
            if record.state == source_state
            and record.theme_id == canonical_theme_id
            and record.version == canonical_version
        )
        record = matches[0] if len(matches) == 1 else None
        if record is None:
            issues.append(
                ThemeManagedIssue(
                    source_state,
                    source,
                    "theme.lifecycle.source-missing",
                    f"Exact {source_state.value} managed theme was not found.",
                    themes_root.root_id,
                )
            )

        approved: str | None = None
        if approved_package_sha256 is None:
            issues.append(
                ThemeManagedIssue(
                    source_state,
                    source,
                    "theme.lifecycle.hash-unapproved",
                    "Lifecycle change requires the exact installed package SHA-256.",
                    themes_root.root_id,
                )
            )
        else:
            approved = validate_theme_sha256(
                approved_package_sha256,
                "Approved managed theme package SHA-256",
            )
            if record is not None and approved != record.receipt.package_sha256:
                issues.append(
                    ThemeManagedIssue(
                        source_state,
                        source,
                        "theme.lifecycle.hash-mismatch",
                        "Approved SHA-256 does not match managed theme provenance.",
                        themes_root.root_id,
                    )
                )
        if not acknowledge_lifecycle_change:
            issues.append(
                ThemeManagedIssue(
                    source_state,
                    source,
                    "theme.lifecycle.acknowledgement-required",
                    "Lifecycle change requires an explicit acknowledgement.",
                    themes_root.root_id,
                )
            )

        root = themes_root.path.resolve()
        target_path = root.joinpath(*target.split("/"))
        if target_path.exists() or target_path.is_symlink():
            issues.append(
                ThemeManagedIssue(
                    target_state,
                    target,
                    "theme.lifecycle.target-exists",
                    "Lifecycle target already exists; replacement is not allowed.",
                    themes_root.root_id,
                )
            )

        if action == ThemeLifecycleAction.RESTORE and record is not None:
            inspection = self._discovery.inspect(themes_root.path)
            if any(
                item.theme_id == canonical_theme_id
                and item.version == canonical_version
                for item in inspection.records
            ):
                issues.append(
                    ThemeManagedIssue(
                        target_state,
                        target,
                        "theme.lifecycle.identity-present",
                        "Theme identity is already present in the active catalog.",
                        themes_root.root_id,
                    )
                )

        return ThemeLifecyclePlan(
            action,
            themes_root.root_id,
            canonical_theme_id,
            canonical_version,
            source,
            target,
            approved,
            acknowledge_lifecycle_change,
            record,
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
    def _state_directory(state: ThemeManagedState) -> str:
        return (
            THEME_MANAGED_DIRECTORY
            if state == ThemeManagedState.ACTIVE
            else THEME_DISABLED_DIRECTORY
        )


class ThemeLifecycleManager:
    """Apply one ready lifecycle plan as an atomic same-volume directory move."""

    def __init__(self, verifier: ThemeManagedThemeVerifier | None = None) -> None:
        self._verifier = verifier or ThemeManagedThemeVerifier()

    def apply(self, plan: ThemeLifecyclePlan, themes_root: Path) -> ThemeLifecycleResult:
        if not isinstance(plan, ThemeLifecyclePlan) or not plan.ready or plan.record is None:
            raise ThemeError("Only a ready ThemeLifecyclePlan can be applied.")
        if themes_root.is_symlink() or not themes_root.resolve().is_dir():
            raise ThemeError("Theme lifecycle root changed after planning.")
        resolved_root = themes_root.resolve()
        source = resolved_root.joinpath(*plan.source_relative_path.split("/"))
        target = resolved_root.joinpath(*plan.target_relative_path.split("/"))
        expected_source = (
            f"{ThemeLifecyclePlanner._state_directory(plan.record.state)}/"
            f"{plan.record.theme_id}/{plan.record.version}"
        )
        if plan.source_relative_path != expected_source:
            raise ThemeError("Theme lifecycle source is not host-derived.")
        target_state = (
            ThemeManagedState.DISABLED
            if plan.action == ThemeLifecycleAction.DISABLE
            else ThemeManagedState.ACTIVE
        )
        expected_target = (
            f"{ThemeLifecyclePlanner._state_directory(target_state)}/"
            f"{plan.record.theme_id}/{plan.record.version}"
        )
        if plan.target_relative_path != expected_target:
            raise ThemeError("Theme lifecycle target is not host-derived.")
        if (
            plan.approved_package_sha256 != plan.record.receipt.package_sha256
            or not plan.lifecycle_acknowledged
        ):
            raise ThemeError("Theme lifecycle approval no longer matches the plan.")

        source_container = source.parents[1]
        current = self._verifier.verify_directory(
            source,
            source_container,
            plan.record.state,
            root_id=plan.root_id,
        )
        if (
            current.receipt.package_sha256 != plan.record.receipt.package_sha256
            or current.receipt.manifest_sha256 != plan.record.receipt.manifest_sha256
        ):
            raise ThemeError("Managed theme changed after lifecycle planning.")
        self._prepare_parent(resolved_root, target.parent)
        if target.exists() or target.is_symlink():
            raise ThemeError("Theme lifecycle target appeared after planning.")
        try:
            os.replace(source, target)
        except OSError as exc:
            raise ThemeError(
                f"Theme lifecycle change could not be applied atomically: {exc}"
            ) from exc
        return ThemeLifecycleResult(
            plan.action,
            plan.theme_id,
            plan.version,
            source,
            target,
            current.receipt.package_sha256,
        )

    @staticmethod
    def _prepare_parent(root: Path, parent: Path) -> None:
        current = root
        try:
            for part in parent.relative_to(root).parts:
                current /= part
                if current.is_symlink():
                    raise ThemeError("Theme lifecycle target contains a symlink.")
                current.mkdir(exist_ok=True)
                if current.is_symlink() or not current.resolve().is_relative_to(root):
                    raise ThemeError("Theme lifecycle target escapes its approved root.")
        except OSError as exc:
            raise ThemeError(f"Theme lifecycle target could not be prepared: {exc}") from exc


__all__ = [
    "ThemeLifecycleAction",
    "ThemeLifecycleManager",
    "ThemeLifecyclePlan",
    "ThemeLifecyclePlanner",
    "ThemeLifecycleResult",
    "ThemeManagedThemeService",
]
