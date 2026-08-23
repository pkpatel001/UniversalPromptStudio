"""Read-only E-013.4 plugin installation and trust planning."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .catalog import PluginCatalog
from .compatibility import PluginSdkContract
from .dependencies import PluginDependencyResolver
from .discovery import PluginDiscoveryService
from .models import (
    PluginDependencyResolution,
    PluginDiscoveryRoot,
    PluginIssue,
    PluginRecord,
)
from .package import (
    PluginPackage,
    PluginPackageInspector,
    PluginTrustAssessment,
    PluginTrustPolicy,
)


@dataclass(frozen=True, slots=True)
class PluginInstallPlan:
    """Deterministic plan only; no archive member is extracted or copied."""

    package: PluginPackage
    root_id: str
    target_relative_path: str
    trust: PluginTrustAssessment
    dependency_resolutions: tuple[PluginDependencyResolution, ...] = ()
    issues: tuple[PluginIssue, ...] = ()

    @property
    def ready(self) -> bool:
        return not self.issues

    @property
    def summary(self) -> str:
        state = "ready" if self.ready else "blocked"
        return (
            f"Plugin installation plan {state}: "
            f"{len(self.dependency_resolutions)} dependencies resolved, "
            f"{len(self.issues)} issues."
        )


class PluginInstallationPlanner:
    """Inspect a package and plan installation against one approved local root."""

    def __init__(
        self,
        package_inspector: PluginPackageInspector | None = None,
        discovery: PluginDiscoveryService | None = None,
        sdk_contract: PluginSdkContract | None = None,
        dependency_resolver: PluginDependencyResolver | None = None,
        trust_policy: PluginTrustPolicy | None = None,
    ) -> None:
        self._package_inspector = package_inspector or PluginPackageInspector()
        self._discovery = discovery or PluginDiscoveryService()
        self._sdk_contract = sdk_contract or PluginSdkContract()
        self._dependency_resolver = dependency_resolver or PluginDependencyResolver()
        self._trust_policy = trust_policy or PluginTrustPolicy()

    def plan(
        self,
        package_path: Path,
        install_root: PluginDiscoveryRoot,
        *,
        approved_sha256: str | None = None,
    ) -> PluginInstallPlan:
        """Return a complete non-mutating installation readiness plan."""

        package = self._package_inspector.inspect(package_path)
        trust = self._trust_policy.assess(package, approved_sha256)
        target = f"{package.plugin_id}/{package.version}"
        package_record = PluginRecord(
            f"{target}/plugin-manifest.yaml",
            package.manifest,
            install_root.root_id,
        )
        issues: list[PluginIssue] = []
        if not trust.approved:
            code = (
                "plugin.trust.unapproved"
                if trust.approved_sha256 is None
                else "plugin.trust.hash-mismatch"
            )
            issues.append(
                PluginIssue(
                    package.filename,
                    code,
                    "Package bytes require an explicit matching SHA-256 approval.",
                    install_root.root_id,
                )
            )

        root = install_root.path
        resolved_root = root.resolve()
        root_available = True
        if root.is_symlink():
            root_available = False
            issues.append(
                PluginIssue(
                    ".",
                    "plugin.install.root-symlink",
                    "Symlinked plugin installation roots are not allowed.",
                    install_root.root_id,
                )
            )
        elif not resolved_root.is_dir():
            root_available = False
            issues.append(
                PluginIssue(
                    ".",
                    "plugin.install.root-missing",
                    "Plugin installation root is not a directory.",
                    install_root.root_id,
                )
            )

        installed_records: tuple[PluginRecord, ...] = ()
        metadata_blocked = not root_available
        if root_available:
            target_path = (resolved_root / package.plugin_id / package.version).resolve()
            if not target_path.is_relative_to(resolved_root):
                metadata_blocked = True
                issues.append(
                    PluginIssue(
                        target,
                        "plugin.install.target-unsafe",
                        "Planned plugin target escapes the approved root.",
                        install_root.root_id,
                    )
                )
            elif target_path.exists() or target_path.is_symlink():
                issues.append(
                    PluginIssue(
                        target,
                        "plugin.install.target-exists",
                        "Planned plugin target already exists; replacement is not planned.",
                        install_root.root_id,
                    )
                )
            inspection = self._discovery.inspect_roots((install_root,))
            installed_records = inspection.records
            if inspection.issues:
                metadata_blocked = True
                issues.extend(inspection.issues)

        all_records = (*installed_records, package_record)
        identities = tuple((item.plugin_id, item.version) for item in all_records)
        if len(set(identities)) != len(identities):
            metadata_blocked = True
            issues.append(
                PluginIssue(
                    package_record.relative_path,
                    "plugin.install.identity-present",
                    f"Plugin {package.plugin_id} version {package.version} is already present.",
                    install_root.root_id,
                )
            )

        for record in all_records:
            issue = self._sdk_contract.issue_for(record)
            if issue is not None:
                metadata_blocked = True
                issues.append(issue)

        resolutions: tuple[PluginDependencyResolution, ...] = ()
        if not metadata_blocked:
            catalog = PluginCatalog(all_records, self._sdk_contract)
            dependency_report = self._dependency_resolver.resolve(catalog)
            resolutions = dependency_report.resolutions
            issues.extend(dependency_report.issues)

        return PluginInstallPlan(
            package=package,
            root_id=install_root.root_id,
            target_relative_path=target,
            trust=trust,
            dependency_resolutions=resolutions,
            issues=tuple(
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


__all__ = ["PluginInstallPlan", "PluginInstallationPlanner"]
