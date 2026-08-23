"""Deterministic non-applying catalog for compatible themes."""

from __future__ import annotations

from collections.abc import Iterable

from Engineering.core.exceptions import ThemeError

from .compatibility import ThemeSdkContract
from .models import ThemeAppearance, ThemeId, ThemeRecord, ThemeVersion


class ThemeCatalog:
    """Register and resolve theme ID/version/appearance metadata."""

    def __init__(
        self,
        records: Iterable[ThemeRecord] = (),
        sdk_contract: ThemeSdkContract | None = None,
    ) -> None:
        self._records: dict[tuple[str, str], ThemeRecord] = {}
        self._sdk_contract = sdk_contract or ThemeSdkContract()
        for record in records:
            self.register(record)

    def register(self, record: ThemeRecord) -> None:
        issue = self._sdk_contract.issue_for(record)
        if issue is not None:
            raise ThemeError(issue.message)
        key = (record.theme_id, record.version)
        if key in self._records:
            raise ThemeError(
                f"Duplicate theme identity: {record.theme_id} version {record.version}."
            )
        self._records[key] = record

    def resolve(
        self,
        theme_id: str,
        version: str | None = None,
        *,
        appearances: Iterable[ThemeAppearance] = (),
    ) -> ThemeRecord:
        ThemeId(theme_id)
        if version is not None:
            ThemeVersion(version)
        required = frozenset(appearances)
        candidates = [
            record
            for (registered_id, registered_version), record in self._records.items()
            if registered_id == theme_id
            and (version is None or registered_version == version)
            and required.issubset(self._appearances(record))
        ]
        if not candidates:
            suffix = f" version {version}" if version is not None else ""
            appearance_suffix = (
                " with appearances " + ", ".join(sorted(item.value for item in required))
                if required
                else ""
            )
            raise ThemeError(
                f"Unknown compatible theme: {theme_id}{suffix}{appearance_suffix}."
            )
        return max(candidates, key=lambda item: item.manifest.metadata.version.parsed)

    def records_for(self, theme_id: str) -> tuple[ThemeRecord, ...]:
        ThemeId(theme_id)
        return tuple(item for item in self.records if item.theme_id == theme_id)

    def supporting(self, appearances: Iterable[ThemeAppearance]) -> tuple[ThemeRecord, ...]:
        required = frozenset(appearances)
        if not required:
            raise ThemeError("At least one theme appearance is required for filtering.")
        return tuple(
            record for record in self.records if required.issubset(self._appearances(record))
        )

    def available_versions(self, theme_id: str) -> tuple[str, ...]:
        return tuple(item.version for item in self.records_for(theme_id))

    @property
    def records(self) -> tuple[ThemeRecord, ...]:
        return tuple(
            sorted(
                self._records.values(),
                key=lambda item: (item.theme_id, item.manifest.metadata.version.parsed),
            )
        )

    @staticmethod
    def _appearances(record: ThemeRecord) -> frozenset[ThemeAppearance]:
        return frozenset(item.appearance for item in record.manifest.palettes)


__all__ = ["ThemeCatalog"]
