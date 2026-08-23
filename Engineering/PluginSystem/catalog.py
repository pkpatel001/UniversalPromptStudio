"""Deterministic in-memory catalog for validated plugin records."""

from __future__ import annotations

from collections.abc import Iterable

from Engineering.core.exceptions import PluginError

from .models import PluginId, PluginRecord, PluginVersion


class PluginCatalog:
    """Register and resolve plugin ID/version pairs without loading code."""

    def __init__(self, records: Iterable[PluginRecord] = ()) -> None:
        self._records: dict[tuple[str, str], PluginRecord] = {}
        for record in records:
            self.register(record)

    def register(self, record: PluginRecord) -> None:
        """Register one record and reject an ambiguous identity."""

        key = (record.plugin_id, record.version)
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
