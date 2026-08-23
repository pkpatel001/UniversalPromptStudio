"""Deterministic non-executing catalog for compatible AI providers."""

from __future__ import annotations

from collections.abc import Iterable

from Engineering.core.exceptions import ProviderError

from .compatibility import ProviderSdkContract
from .models import (
    ProviderCapability,
    ProviderId,
    ProviderRecord,
    ProviderVersion,
)


class ProviderCatalog:
    """Register and resolve provider ID/version/capability metadata."""

    def __init__(
        self,
        records: Iterable[ProviderRecord] = (),
        sdk_contract: ProviderSdkContract | None = None,
    ) -> None:
        self._records: dict[tuple[str, str], ProviderRecord] = {}
        self._sdk_contract = sdk_contract or ProviderSdkContract()
        for record in records:
            self.register(record)

    def register(self, record: ProviderRecord) -> None:
        issue = self._sdk_contract.issue_for(record)
        if issue is not None:
            raise ProviderError(issue.message)
        key = (record.provider_id, record.version)
        if key in self._records:
            raise ProviderError(
                f"Duplicate provider identity: {record.provider_id} " f"version {record.version}."
            )
        self._records[key] = record

    def resolve(
        self,
        provider_id: str,
        version: str | None = None,
        *,
        capabilities: Iterable[ProviderCapability] = (),
    ) -> ProviderRecord:
        ProviderId(provider_id)
        if version is not None:
            ProviderVersion(version)
        required = frozenset(capabilities)
        candidates = [
            record
            for (registered_id, registered_version), record in self._records.items()
            if registered_id == provider_id
            and (version is None or registered_version == version)
            and required.issubset(record.manifest.capabilities)
        ]
        if not candidates:
            suffix = f" version {version}" if version is not None else ""
            capability_suffix = (
                " with capabilities " + ", ".join(sorted(item.value for item in required))
                if required
                else ""
            )
            raise ProviderError(
                f"Unknown compatible provider: {provider_id}{suffix}" f"{capability_suffix}."
            )
        return max(
            candidates,
            key=lambda item: item.manifest.metadata.version.parsed,
        )

    def records_for(self, provider_id: str) -> tuple[ProviderRecord, ...]:
        ProviderId(provider_id)
        return tuple(item for item in self.records if item.provider_id == provider_id)

    def supporting(self, capabilities: Iterable[ProviderCapability]) -> tuple[ProviderRecord, ...]:
        required = frozenset(capabilities)
        if not required:
            raise ProviderError("At least one provider capability is required for filtering.")
        return tuple(
            record for record in self.records if required.issubset(record.manifest.capabilities)
        )

    def available_versions(self, provider_id: str) -> tuple[str, ...]:
        return tuple(item.version for item in self.records_for(provider_id))

    @property
    def records(self) -> tuple[ProviderRecord, ...]:
        return tuple(
            sorted(
                self._records.values(),
                key=lambda item: (
                    item.provider_id,
                    item.manifest.metadata.version.parsed,
                ),
            )
        )
