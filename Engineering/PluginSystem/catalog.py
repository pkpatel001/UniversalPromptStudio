"""Deterministic in-memory catalog for validated plugin records."""

from __future__ import annotations

from collections.abc import Iterable

from packaging.specifiers import InvalidSpecifier, SpecifierSet

from Engineering.core.exceptions import PluginError

from .compatibility import PluginSdkContract
from .models import PluginId, PluginRecord, PluginVersion


class PluginCatalog:
    """Register and resolve plugin ID/version pairs without loading code."""

    def __init__(
        self,
        records: Iterable[PluginRecord] = (),
        sdk_contract: PluginSdkContract | None = None,
    ) -> None:
        self._records: dict[tuple[str, str], PluginRecord] = {}
        self._sdk_contract = sdk_contract or PluginSdkContract()
        for record in records:
            self.register(record)

    def register(self, record: PluginRecord) -> None:
        """Register one record and reject an ambiguous identity."""

        key = (record.plugin_id, record.version)
        issue = self._sdk_contract.issue_for(record)
        if issue is not None:
            raise PluginError(issue.message)
        if key in self._records:
            raise PluginError(
                f"Duplicate plugin identity: {record.plugin_id} version {record.version}."
            )
        self._records[key] = record

    def resolve(self, plugin_id: str, version: str | None = None) -> PluginRecord:
        """Resolve an exact version or the highest available version."""

        PluginId(plugin_id)
        if version is not None:
            PluginVersion(version)
        candidates = [
            record
            for (registered_id, registered_version), record in self._records.items()
            if registered_id == plugin_id
            and (version is None or registered_version == version)
        ]
        if not candidates:
            suffix = f" version {version}" if version is not None else ""
            raise PluginError(f"Unknown plugin: {plugin_id}{suffix}.")
        return max(
            candidates,
            key=lambda record: record.manifest.metadata.version.parsed,
        )

    def records_for(self, plugin_id: str) -> tuple[PluginRecord, ...]:
        """Return all compatible versions for an ID in ascending order."""

        PluginId(plugin_id)
        return tuple(
            record
            for record in self.records
            if record.plugin_id == plugin_id
        )

    def resolve_requirement(
        self, plugin_id: str, version_specifier: str
    ) -> PluginRecord:
        """Resolve the highest version satisfying a PEP 440 constraint."""

        PluginId(plugin_id)
        if not version_specifier or version_specifier != version_specifier.strip():
            raise PluginError(
                "Dependency version must be a non-empty, trimmed specifier."
            )
        try:
            specifier = SpecifierSet(version_specifier)
        except InvalidSpecifier as exc:
            raise PluginError(
                f"Invalid dependency version specifier: {version_specifier!r}"
            ) from exc
        candidates = [
            record
            for record in self.records_for(plugin_id)
            if specifier.contains(
                record.manifest.metadata.version.parsed,
                prereleases=True,
            )
        ]
        if not candidates:
            raise PluginError(
                f"No compatible version of {plugin_id} satisfies "
                f"{version_specifier!r}."
            )
        return max(
            candidates,
            key=lambda record: record.manifest.metadata.version.parsed,
        )

    def available_versions(self, plugin_id: str) -> tuple[str, ...]:
        """Return stable version inventory for one plugin ID."""

        return tuple(record.version for record in self.records_for(plugin_id))

    @property
    def records(self) -> tuple[PluginRecord, ...]:
        """Return records in stable identity and version order."""

        return tuple(
            sorted(
                self._records.values(),
                key=lambda record: (
                    record.plugin_id,
                    record.manifest.metadata.version.parsed,
                ),
            )
        )
