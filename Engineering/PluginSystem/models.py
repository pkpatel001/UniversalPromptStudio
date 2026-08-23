"""Immutable domain models for the E-013.1 plugin SDK foundation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version

from Engineering.core.exceptions import PluginError

from .validation import (
    require_entry_point,
    require_metadata_id,
    require_nonempty_text,
    require_plugin_id,
)


@dataclass(frozen=True, slots=True)
class PluginId:
    """Stable, vendor-qualified plugin identity."""

    value: str

    def __post_init__(self) -> None:
        require_plugin_id(self.value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class PluginVersion:
    """Canonical PEP 440 plugin version used for deterministic ordering."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or len(self.value) > 64:
            raise PluginError(
                "Plugin version must be a non-empty value of at most 64 characters."
            )
        try:
            parsed = Version(self.value)
        except InvalidVersion as exc:
            raise PluginError(f"Invalid plugin version: {self.value!r}") from exc
        if (
            str(parsed) != self.value
            or len(parsed.release) != 3
            or parsed.epoch != 0
            or parsed.local is not None
        ):
            raise PluginError(
                "Plugin version must use canonical PEP 440 form with exactly "
                "major.minor.patch release components and no epoch or local version."
            )

    @property
    def parsed(self) -> Version:
        """Return the comparable packaging version."""

        return Version(self.value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class PluginSdkVersion:
    """Positive UPS Plugin SDK API level declared by a plugin."""

    api_level: int

    def __post_init__(self) -> None:
        if type(self.api_level) is not int or self.api_level < 1:
            raise PluginError("Plugin sdk_version must be a positive integer API level.")


class PluginSdkCompatibility(Enum):
    """Compatibility of a plugin SDK level with the current host contract."""

    COMPATIBLE = "compatible"
    TOO_OLD = "too-old"
    TOO_NEW = "too-new"


@dataclass(frozen=True, slots=True)
class PluginEntryPoint:
    """Unresolved Python entry-point metadata; this value is never imported."""

    value: str

    def __post_init__(self) -> None:
        require_entry_point(self.value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class PluginCapability:
    """A contribution category declared as descriptive metadata."""

    capability_id: str

    def __post_init__(self) -> None:
        require_metadata_id(self.capability_id, "Plugin capability")


@dataclass(frozen=True, slots=True)
class PluginPermission:
    """A requested permission label; E-013.1 does not enforce it."""

    permission_id: str

    def __post_init__(self) -> None:
        require_metadata_id(self.permission_id, "Plugin permission")


@dataclass(frozen=True, slots=True)
class PluginDependency:
    """A dependency on another UPS plugin and its PEP 440 version range."""

    plugin_id: PluginId
    version_specifier: str

    def __post_init__(self) -> None:
        if (
            not self.version_specifier
            or self.version_specifier != self.version_specifier.strip()
        ):
            raise PluginError(
                "Plugin dependency version must be a non-empty, trimmed specifier."
            )
        try:
            parsed = SpecifierSet(self.version_specifier)
        except InvalidSpecifier as exc:
            raise PluginError(
                f"Invalid dependency version specifier: {self.version_specifier!r}"
            ) from exc
        object.__setattr__(self, "version_specifier", str(parsed))


@dataclass(frozen=True, slots=True)
class PluginMetadata:
    """Identity, compatibility, and descriptive metadata for one plugin."""

    plugin_id: PluginId
    name: str
    version: PluginVersion
    sdk_version: PluginSdkVersion
    description: str
    entry_point: PluginEntryPoint

    def __post_init__(self) -> None:
        require_nonempty_text(self.name, "Plugin name", maximum=120)
        require_nonempty_text(self.description, "Plugin description", maximum=1000)


@dataclass(frozen=True, slots=True)
class PluginManifest:
    """Canonical schema-1 plugin metadata document."""

    schema_version: int
    metadata: PluginMetadata
    capabilities: tuple[PluginCapability, ...] = ()
    permissions: tuple[PluginPermission, ...] = ()
    dependencies: tuple[PluginDependency, ...] = ()

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise PluginError("Plugin manifest schema_version must be integer 1.")


@dataclass(frozen=True, slots=True)
class PluginDiscoveryRoot:
    """One explicitly approved, stable-labeled discovery root."""

    root_id: str
    path: Path

    def __post_init__(self) -> None:
        require_metadata_id(self.root_id, "Plugin discovery root id")
        if not isinstance(self.path, Path):
            raise PluginError("Plugin discovery root path must be a pathlib Path.")


@dataclass(frozen=True, slots=True)
class PluginRecord:
    """One valid plugin manifest and its portable path below a discovery root."""

    relative_path: str
    manifest: PluginManifest
    root_id: str = "project"

    def __post_init__(self) -> None:
        require_metadata_id(self.root_id, "Plugin discovery root id")

    @property
    def plugin_id(self) -> str:
        """Return the stable plugin id."""

        return self.manifest.metadata.plugin_id.value

    @property
    def version(self) -> str:
        """Return the canonical plugin version."""

        return self.manifest.metadata.version.value


@dataclass(frozen=True, slots=True)
class PluginIssue:
    """One deterministic discovery or validation problem."""

    relative_path: str
    code: str
    message: str
    root_id: str = "project"


@dataclass(frozen=True, slots=True)
class PluginDependencyResolution:
    """One deterministic dependency selection for a plugin version."""

    owner_plugin_id: str
    owner_version: str
    dependency_plugin_id: str
    version_specifier: str
    resolved_version: str
    owner_relative_path: str
    owner_root_id: str = "project"


@dataclass(frozen=True, slots=True)
class PluginInspectionReport:
    """Aggregate result of read-only plugin discovery."""

    records: tuple[PluginRecord, ...] = ()
    issues: tuple[PluginIssue, ...] = ()

    @property
    def passed(self) -> bool:
        """Return whether every discovered manifest is valid and unique."""

        return not self.issues

    @property
    def summary(self) -> str:
        """Return a stable human-readable result summary."""

        state = "succeeded" if self.passed else "failed"
        return (
            f"Plugin inspection {state}: {len(self.records)} valid, "
            f"{len(self.issues)} issues."
        )


@dataclass(frozen=True, slots=True)
class PluginValidationReport:
    """Aggregate compatibility and dependency validation result."""

    records: tuple[PluginRecord, ...] = ()
    dependency_resolutions: tuple[PluginDependencyResolution, ...] = ()
    issues: tuple[PluginIssue, ...] = ()

    @property
    def passed(self) -> bool:
        """Return whether all plugins are compatible and dependency-complete."""

        return not self.issues

    @property
    def summary(self) -> str:
        """Return a stable human-readable validation summary."""

        state = "succeeded" if self.passed else "failed"
        return (
            f"Plugin validation {state}: {len(self.records)} compatible, "
            f"{len(self.dependency_resolutions)} dependencies resolved, "
            f"{len(self.issues)} issues."
        )
