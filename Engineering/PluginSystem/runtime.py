"""Approval-gated, explicit plugin lifecycle orchestration for E-013.5."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Protocol

from Engineering.core.exceptions import PluginError

from .catalog import PluginCatalog
from .manifest import PLUGIN_MANIFEST_NAME, PluginManifestReader
from .models import PluginDiscoveryRoot, PluginRecord, PluginValidationReport
from .runtime_api import PluginContribution, PluginContributionRegistry, PluginRegistrationContext
from .runtime_loader import LoadedPlugin, PluginModuleLoader, TrustedInProcessLoader
from .runtime_snapshot import PluginDirectorySnapshot, PluginDirectorySnapshotter
from .service import PluginService

_SHA256 = re.compile(r"[0-9a-f]{64}")


class PluginLifecycleState(Enum):
    """Observable states for one explicitly controlled runtime session."""

    APPROVED = "approved"
    LOADING = "loading"
    ACTIVE = "active"
    UNLOADING = "unloading"
    INACTIVE = "inactive"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class PluginRuntimeApproval:
    """Ephemeral approval for one exact plugin directory revision."""

    plugin_id: str
    version: str
    root_id: str
    directory_sha256: str
    acknowledge_full_trust: bool = False

    def __post_init__(self) -> None:
        if not _SHA256.fullmatch(self.directory_sha256):
            raise PluginError("Runtime approval SHA-256 must be 64 lowercase hex characters.")


@dataclass(frozen=True, slots=True)
class PluginRuntimeEvent:
    """Host-neutral lifecycle notification emitted only after success."""

    name: str
    plugin_id: str
    version: str
    root_id: str


class PluginRuntimeEventSink(Protocol):
    def publish(self, event: PluginRuntimeEvent) -> None:
        """Publish one successful lifecycle transition."""


class _NullEventSink:
    def publish(self, event: PluginRuntimeEvent) -> None:
        return None


@dataclass(frozen=True, slots=True)
class PluginRuntimeStatus:
    """Current result for one plugin runtime session."""

    plugin_id: str
    version: str
    root_id: str
    directory_sha256: str
    state: PluginLifecycleState
    contributions: tuple[PluginContribution, ...] = ()
    error: str | None = None


@dataclass(slots=True)
class _RuntimeSession:
    record: PluginRecord
    snapshot: PluginDirectorySnapshot
    context: PluginRegistrationContext
    state: PluginLifecycleState
    loaded: LoadedPlugin | None = None
    error: str | None = None


class PluginRuntimeManager:
    """Coordinate explicit trusted loading, activation, rollback, and unloading."""

    def __init__(
        self,
        *,
        service: PluginService | None = None,
        snapshotter: PluginDirectorySnapshotter | None = None,
        loader: PluginModuleLoader | None = None,
        registry: PluginContributionRegistry | None = None,
        events: PluginRuntimeEventSink | None = None,
    ) -> None:
        self._service = service or PluginService()
        self._snapshotter = snapshotter or PluginDirectorySnapshotter()
        self._loader = loader or TrustedInProcessLoader()
        self._registry = registry or PluginContributionRegistry()
        self._events = events or _NullEventSink()
        self._sessions: dict[tuple[str, str, str], _RuntimeSession] = {}

    @property
    def registry(self) -> PluginContributionRegistry:
        return self._registry

    def digest(
        self,
        root: PluginDiscoveryRoot,
        plugin_id: str,
        version: str | None = None,
    ) -> PluginRuntimeStatus:
        """Validate metadata and report the exact directory digest without loading."""

        record, _ = self._resolve(root, plugin_id, version)
        self._require_runtime_policy(record)
        snapshot = self._capture(root, record)
        return PluginRuntimeStatus(
            record.plugin_id,
            record.version,
            record.root_id,
            snapshot.sha256,
            PluginLifecycleState.INACTIVE,
        )

    def activate(
        self,
        root: PluginDiscoveryRoot,
        plugin_id: str,
        version: str | None,
        approval: PluginRuntimeApproval,
    ) -> PluginRuntimeStatus:
        """Explicitly load and activate one exact approved directory snapshot."""

        record, report = self._resolve(root, plugin_id, version)
        self._require_runtime_policy(record)
        self._require_identity_approval(record, approval)
        if not approval.acknowledge_full_trust:
            raise PluginError("Runtime activation requires explicit full-trust acknowledgment.")
        key = self._key(record)
        if key in self._sessions and self._sessions[key].state == PluginLifecycleState.ACTIVE:
            raise PluginError("Plugin runtime session is already active.")
        if any(
            session.record.plugin_id == record.plugin_id
            and session.state == PluginLifecycleState.ACTIVE
            for session in self._sessions.values()
        ):
            raise PluginError("Another version of this plugin is already active.")
        for resolution in report.dependency_resolutions:
            if (
                resolution.owner_plugin_id == record.plugin_id
                and resolution.owner_version == record.version
                and not self._dependency_active(
                    record.root_id,
                    resolution.dependency_plugin_id,
                    resolution.resolved_version,
                )
            ):
                raise PluginError(
                    f"Runtime dependency is not active: "
                    f"{resolution.dependency_plugin_id}@{resolution.resolved_version}."
                )

        snapshot = self._capture(root, record)
        if snapshot.sha256 != approval.directory_sha256:
            raise PluginError("Runtime approval does not match the plugin directory snapshot.")
        context = PluginRegistrationContext(
            record.plugin_id,
            tuple(item.capability_id for item in record.manifest.capabilities),
        )
        session = _RuntimeSession(record, snapshot, context, PluginLifecycleState.APPROVED)
        self._sessions[key] = session
        session.state = PluginLifecycleState.LOADING
        try:
            namespace = f"_ups_plugin_{snapshot.sha256[:24]}"
            session.loaded = self._loader.load(
                snapshot, record.manifest.metadata.entry_point, namespace
            )
            session.loaded.instance.activate(context)
            context.close_registration()
            self._registry.commit(context.staged())
        except Exception as exc:
            context.rollback()
            self._registry.remove_plugin(record.plugin_id)
            if session.loaded is not None:
                self._loader.unload(session.loaded)
                session.loaded = None
            session.state = PluginLifecycleState.FAILED
            session.error = f"{type(exc).__name__}: {exc}"
            return self._status(session)

        session.state = PluginLifecycleState.ACTIVE
        self._events.publish(
            PluginRuntimeEvent("PluginLoaded", record.plugin_id, record.version, record.root_id)
        )
        return self._status(session)

    def deactivate(self, root_id: str, plugin_id: str, version: str) -> PluginRuntimeStatus:
        """Deactivate an active plugin and deterministically clear host-owned state."""

        key = (root_id, plugin_id, version)
        session = self._sessions.get(key)
        if session is None or session.state != PluginLifecycleState.ACTIVE:
            raise PluginError("Plugin runtime session is not active.")
        session.state = PluginLifecycleState.UNLOADING
        failure: Exception | None = None
        try:
            if session.loaded is None:
                raise PluginError("Active plugin has no loaded runtime instance.")
            session.loaded.instance.deactivate(session.context)
        except Exception as exc:
            failure = exc
        finally:
            self._registry.remove_plugin(plugin_id)
            if session.loaded is not None:
                self._loader.unload(session.loaded)
                session.loaded = None

        if failure is not None:
            session.state = PluginLifecycleState.FAILED
            session.error = f"{type(failure).__name__}: {failure}"
            return self._status(session)
        session.state = PluginLifecycleState.INACTIVE
        session.error = None
        self._events.publish(PluginRuntimeEvent("PluginUnloaded", plugin_id, version, root_id))
        return self._status(session)

    def status(self, root_id: str, plugin_id: str, version: str) -> PluginRuntimeStatus | None:
        session = self._sessions.get((root_id, plugin_id, version))
        return None if session is None else self._status(session)

    def _resolve(
        self, root: PluginDiscoveryRoot, plugin_id: str, version: str | None
    ) -> tuple[PluginRecord, PluginValidationReport]:
        report = self._service.validate_roots((root,))
        if not report.passed:
            raise PluginError(report.summary)
        record = PluginCatalog(report.records).resolve(plugin_id, version)
        return record, report

    @staticmethod
    def _require_runtime_policy(record: PluginRecord) -> None:
        if record.manifest.permissions:
            raise PluginError(
                "Plugins requesting permissions cannot run because permission "
                "enforcement is not implemented."
            )

    @staticmethod
    def _require_identity_approval(record: PluginRecord, approval: PluginRuntimeApproval) -> None:
        if (
            approval.plugin_id != record.plugin_id
            or approval.version != record.version
            or approval.root_id != record.root_id
        ):
            raise PluginError("Runtime approval identity does not match the selected plugin.")

    @staticmethod
    def _plugin_directory(root: PluginDiscoveryRoot, record: PluginRecord) -> Path:
        resolved_root = root.path.resolve()
        relative = PurePosixPath(record.relative_path)
        directory = resolved_root.joinpath(*relative.parent.parts).resolve()
        if not directory.is_relative_to(resolved_root):
            raise PluginError("Plugin runtime directory escapes the approved root.")
        return directory

    def _capture(self, root: PluginDiscoveryRoot, record: PluginRecord) -> PluginDirectorySnapshot:
        snapshot = self._snapshotter.capture(self._plugin_directory(root, record))
        manifest_file = snapshot.file(PLUGIN_MANIFEST_NAME)
        if manifest_file is None:
            raise PluginError("Plugin runtime snapshot is missing its manifest.")
        try:
            manifest_text = manifest_file.content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise PluginError("Plugin runtime manifest is not UTF-8.") from exc
        if PluginManifestReader().read_text(manifest_text) != record.manifest:
            raise PluginError("Plugin manifest changed between validation and runtime snapshot.")
        return snapshot

    @staticmethod
    def _key(record: PluginRecord) -> tuple[str, str, str]:
        return (record.root_id, record.plugin_id, record.version)

    def _dependency_active(self, root_id: str, plugin_id: str, version: str) -> bool:
        return any(
            session.record.root_id == root_id
            and session.record.plugin_id == plugin_id
            and session.record.version == version
            and session.state == PluginLifecycleState.ACTIVE
            for session in self._sessions.values()
        )

    def _status(self, session: _RuntimeSession) -> PluginRuntimeStatus:
        return PluginRuntimeStatus(
            session.record.plugin_id,
            session.record.version,
            session.record.root_id,
            session.snapshot.sha256,
            session.state,
            tuple(
                item
                for item in self._registry.contributions()
                if item.plugin_id == session.record.plugin_id
            ),
            session.error,
        )


__all__ = [
    "PluginLifecycleState",
    "PluginRuntimeApproval",
    "PluginRuntimeEvent",
    "PluginRuntimeEventSink",
    "PluginRuntimeManager",
    "PluginRuntimeStatus",
]
