"""App-owned theme and trusted-extension lifecycle orchestration for A-006."""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

from Engineering.PluginSystem import (
    PluginDiscoveryRoot,
    PluginIssue,
    PluginLifecycleState,
    PluginRuntimeApproval,
    PluginRuntimeManager,
    PluginRuntimeStatus,
    PluginService,
)
from Engineering.ThemeSystem import (
    THEME_PACKAGE_SUFFIX,
    ThemeCatalog,
    ThemeDiscoveryRoot,
    ThemeFrontendCatalogCompiler,
    ThemeFrontendSelection,
    ThemeInstallationPlanner,
    ThemeInstaller,
    ThemeIssue,
    ThemeLifecycleAction,
    ThemeLifecycleManager,
    ThemeLifecyclePlanner,
    ThemeManagedIssue,
    ThemeManagedRecord,
    ThemeManagedState,
    ThemeManagedThemeService,
    ThemePackageInspector,
    ThemeRecord,
)

MAX_CUSTOMIZATION_ITEMS = 20
MAX_CUSTOMIZATION_ISSUES = 10
THEME_ROOT_ID = "managed-themes"
EXTENSION_ROOT_ID = "managed-extensions"
_FRONTEND_VERSION = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")


class ManagedCustomizationService:
    """Expose only fixed app-data roots and Engineering-approved transitions."""

    def __init__(self, app_data_directory: Path | None = None) -> None:
        self._temporary: tempfile.TemporaryDirectory[str] | None = None
        if app_data_directory is None:
            self._temporary = tempfile.TemporaryDirectory(prefix="ups-customizations-")
            app_data_directory = Path(self._temporary.name)
        root = app_data_directory.resolve()
        self._theme_root = root / "themes"
        self._theme_inbox = root / "theme-packages"
        self._extension_root = root / "extensions"
        for directory in (self._theme_root, self._theme_inbox, self._extension_root):
            directory.mkdir(parents=True, exist_ok=True)
            if directory.is_symlink() or not directory.is_dir():
                raise OSError("Customization storage is unavailable.")
        self._theme_discovery_root = ThemeDiscoveryRoot(THEME_ROOT_ID, self._theme_root)
        self._extension_discovery_root = PluginDiscoveryRoot(
            EXTENSION_ROOT_ID, self._extension_root
        )
        self._theme_inventory = ThemeManagedThemeService()
        self._theme_installation_planner = ThemeInstallationPlanner()
        self._theme_installer = ThemeInstaller()
        self._theme_lifecycle_planner = ThemeLifecyclePlanner()
        self._theme_lifecycle_manager = ThemeLifecycleManager()
        self._theme_package_inspector = ThemePackageInspector()
        self._plugin_service = PluginService()
        self._plugin_runtime = PluginRuntimeManager(service=self._plugin_service)

    def catalog(self) -> dict[str, object]:
        """Return bounded, verified theme, package, and extension state."""

        theme_report = self._theme_inventory.verify(self._theme_discovery_root)
        active_records = (
            tuple(
                ThemeRecord(record.relative_path, record.manifest, record.root_id)
                for record in theme_report.records
                if record.state is ThemeManagedState.ACTIVE
            )
            if theme_report.passed
            else ()
        )
        selections: list[dict[str, object]] = []
        if active_records:
            compiled = ThemeFrontendCatalogCompiler().compile(ThemeCatalog(active_records))
            selections = [self._theme_selection(item) for item in compiled.selections]

        extensions, extension_issues = self._extensions()
        return {
            "schema_version": 1,
            "boundaries": {
                "theme_install": "managed-inbox-only",
                "theme_remove": "unsupported",
                "extension_install": "unsupported",
                "extension_remove": "unsupported",
                "extension_runtime": "explicit-session-full-trust",
                "remote_discovery": "unsupported",
            },
            "theme_selections": selections[:MAX_CUSTOMIZATION_ITEMS],
            "themes": [
                self._theme_record(record)
                for record in theme_report.records[:MAX_CUSTOMIZATION_ITEMS]
            ],
            "theme_packages": self._theme_packages(),
            "extensions": extensions,
            "issues": (
                [self._managed_issue(item) for item in theme_report.issues] + extension_issues
            )[:MAX_CUSTOMIZATION_ISSUES],
        }

    def install_theme(
        self,
        package_filename: str,
        approved_sha256: str,
        *,
        acknowledge_external_theme: bool,
    ) -> dict[str, object]:
        """Install one exact package from the fixed app-owned inbox."""

        package_path = self._inbox_package(package_filename)
        plan = self._theme_installation_planner.plan(
            package_path,
            self._theme_discovery_root,
            approved_sha256=approved_sha256,
            acknowledge_external_theme=acknowledge_external_theme,
        )
        if plan.package.theme_id.startswith("ups."):
            return self._blocked_action(
                "install",
                [
                    {
                        "area": "theme",
                        "code": "theme.identity.reserved",
                        "message": (
                            "The ups theme identity namespace is reserved for built-in themes."
                        ),
                    }
                ],
            )
        if _FRONTEND_VERSION.fullmatch(plan.package.version) is None:
            return self._blocked_action(
                "install",
                [
                    {
                        "area": "theme",
                        "code": "theme.version.unsupported",
                        "message": "Desktop themes require a stable major.minor.patch version.",
                    }
                ],
            )
        if not plan.ready:
            return self._blocked_action(
                "install", [self._theme_issue(item) for item in plan.issues]
            )
        result = self._theme_installer.install(
            plan,
            self._theme_root,
            source_label=f"managed-inbox/{package_filename}",
        )
        return {
            "action": "install",
            "applied": True,
            "theme_id": result.theme_id,
            "version": result.version,
            "package_sha256": result.package_sha256,
            "state": "active",
            "issues": [],
        }

    def change_theme_state(
        self,
        theme_id: str,
        version: str,
        action: str,
        approved_package_sha256: str,
        *,
        acknowledge_lifecycle_change: bool,
    ) -> dict[str, object]:
        """Apply one reversible exact managed-theme transition."""

        lifecycle_action = ThemeLifecycleAction(action)
        plan = self._theme_lifecycle_planner.plan(
            self._theme_discovery_root,
            theme_id,
            version,
            lifecycle_action,
            approved_package_sha256=approved_package_sha256,
            acknowledge_lifecycle_change=acknowledge_lifecycle_change,
        )
        if not plan.ready:
            return self._blocked_action(action, [self._managed_issue(item) for item in plan.issues])
        result = self._theme_lifecycle_manager.apply(plan, self._theme_root)
        return {
            "action": result.action.value,
            "applied": True,
            "theme_id": result.theme_id,
            "version": result.version,
            "package_sha256": result.package_sha256,
            "state": "disabled" if result.action is ThemeLifecycleAction.DISABLE else "active",
            "issues": [],
        }

    def activate_extension(
        self,
        plugin_id: str,
        version: str,
        directory_sha256: str,
        *,
        acknowledge_full_trust: bool,
    ) -> dict[str, object]:
        """Activate one permission-free exact extension snapshot for this process only."""

        approval = PluginRuntimeApproval(
            plugin_id,
            version,
            EXTENSION_ROOT_ID,
            directory_sha256,
            acknowledge_full_trust,
        )
        status = self._plugin_runtime.activate(
            self._extension_discovery_root, plugin_id, version, approval
        )
        return self._extension_status(status)

    def deactivate_extension(
        self, plugin_id: str, version: str, directory_sha256: str
    ) -> dict[str, object]:
        """Deactivate one exact active in-process extension session."""

        current = self._plugin_runtime.status(EXTENSION_ROOT_ID, plugin_id, version)
        if (
            current is None
            or current.state is not PluginLifecycleState.ACTIVE
            or current.directory_sha256 != directory_sha256
        ):
            raise ValueError("Extension lifecycle approval does not match the active session.")
        return self._extension_status(
            self._plugin_runtime.deactivate(EXTENSION_ROOT_ID, plugin_id, version)
        )

    def _extensions(self) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
        report = self._plugin_service.validate_roots((self._extension_discovery_root,))
        issues = [self._plugin_issue(item) for item in report.issues]
        extensions: list[dict[str, object]] = []
        if not report.passed:
            return extensions, issues
        for record in report.records[:MAX_CUSTOMIZATION_ITEMS]:
            if _FRONTEND_VERSION.fullmatch(record.version) is None:
                issues.append(
                    {
                        "area": "extension",
                        "code": "extension.version.unsupported",
                        "message": "Desktop extensions require a stable major.minor.patch version.",
                    }
                )
                continue
            permissions = [item.permission_id for item in record.manifest.permissions]
            digest: str | None = None
            trust_state = "permission-request-blocked" if permissions else "full-trust-required"
            runtime_state = "inactive"
            if not permissions:
                status = self._plugin_runtime.status(
                    record.root_id, record.plugin_id, record.version
                )
                if status is None:
                    status = self._plugin_runtime.digest(
                        self._extension_discovery_root,
                        record.plugin_id,
                        record.version,
                    )
                digest = status.directory_sha256
                runtime_state = status.state.value
                if status.state is PluginLifecycleState.ACTIVE:
                    trust_state = "approved-for-session"
            metadata = record.manifest.metadata
            extensions.append(
                {
                    "plugin_id": record.plugin_id,
                    "name": metadata.name,
                    "version": record.version,
                    "description": metadata.description[:240],
                    "sdk_version": metadata.sdk_version.api_level,
                    "origin": "managed-app-data",
                    "compatibility": "compatible",
                    "trust_state": trust_state,
                    "runtime_state": runtime_state,
                    "directory_sha256": digest,
                    "capabilities": [item.capability_id for item in record.manifest.capabilities],
                    "permissions": permissions,
                    "restart_behavior": "inactive-after-restart",
                }
            )
        return extensions, issues

    def _theme_packages(self) -> list[dict[str, object]]:
        packages: list[dict[str, object]] = []
        for path in sorted(self._theme_inbox.iterdir(), key=lambda item: item.name):
            if len(packages) >= MAX_CUSTOMIZATION_ITEMS or not path.name.endswith(
                THEME_PACKAGE_SUFFIX
            ):
                continue
            try:
                package = self._theme_package_inspector.inspect(path)
                packages.append(
                    {
                        "filename": package.filename,
                        "theme_id": package.theme_id,
                        "name": package.manifest.metadata.name,
                        "version": package.version,
                        "package_sha256": package.sha256,
                        "compatibility": "pending-approved-install-plan",
                        "trust_state": "exact-hash-and-ack-required",
                        "valid": True,
                    }
                )
            except Exception:
                packages.append(
                    {
                        "filename": path.name[:240],
                        "theme_id": None,
                        "name": None,
                        "version": None,
                        "package_sha256": None,
                        "compatibility": "invalid",
                        "trust_state": "blocked",
                        "valid": False,
                    }
                )
        return packages

    def _inbox_package(self, filename: str) -> Path:
        if (
            not filename
            or len(filename) > 240
            or not filename.endswith(THEME_PACKAGE_SUFFIX)
            or Path(filename).name != filename
        ):
            raise ValueError("Theme package filename is invalid.")
        path = self._theme_inbox / filename
        if path.is_symlink() or not path.is_file() or path.resolve().parent != self._theme_inbox:
            raise ValueError("Theme package is unavailable in the managed inbox.")
        return path

    @staticmethod
    def _theme_selection(item: ThemeFrontendSelection) -> dict[str, object]:
        return {
            "theme_id": item.theme_id.value,
            "theme_name": item.theme_name,
            "version": item.version.value,
            "appearance": item.appearance.value,
            "tokens": {token.name.value: token.value.value for token in item.tokens},
        }

    @staticmethod
    def _theme_record(record: ThemeManagedRecord) -> dict[str, object]:
        metadata = record.manifest.metadata
        return {
            "theme_id": record.theme_id,
            "name": metadata.name,
            "version": record.version,
            "description": metadata.description[:240],
            "sdk_version": metadata.sdk_version.api_level,
            "state": record.state.value,
            "origin": "verified-external-package",
            "compatibility": "compatible",
            "trust_state": "verified-exact-package-sha256",
            "package_sha256": record.receipt.package_sha256,
            "source_label": record.receipt.source_label,
            "appearances": [item.appearance.value for item in record.manifest.palettes],
        }

    @staticmethod
    def _extension_status(status: PluginRuntimeStatus) -> dict[str, object]:
        return {
            "plugin_id": status.plugin_id,
            "version": status.version,
            "directory_sha256": status.directory_sha256,
            "runtime_state": status.state.value,
            "contribution_count": len(status.contributions),
            "error": "Extension activation failed safely."
            if status.state is PluginLifecycleState.FAILED
            else None,
            "restart_behavior": "inactive-after-restart",
        }

    @staticmethod
    def _blocked_action(action: str, issues: list[dict[str, str]]) -> dict[str, object]:
        return {
            "action": action,
            "applied": False,
            "theme_id": None,
            "version": None,
            "package_sha256": None,
            "state": None,
            "issues": issues[:MAX_CUSTOMIZATION_ISSUES],
        }

    @staticmethod
    def _theme_issue(issue: ThemeIssue) -> dict[str, str]:
        return {"area": "theme", "code": issue.code, "message": issue.message[:240]}

    @staticmethod
    def _managed_issue(issue: ThemeManagedIssue) -> dict[str, str]:
        return {"area": "theme", "code": issue.code, "message": issue.message[:240]}

    @staticmethod
    def _plugin_issue(issue: PluginIssue) -> dict[str, str]:
        return {"area": "extension", "code": issue.code, "message": issue.message[:240]}


__all__ = [
    "EXTENSION_ROOT_ID",
    "MAX_CUSTOMIZATION_ITEMS",
    "ManagedCustomizationService",
    "THEME_ROOT_ID",
]
