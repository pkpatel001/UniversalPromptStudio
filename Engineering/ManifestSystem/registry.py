"""Typed registry for E-012 manifest-family adapters."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Protocol

from Engineering.core.exceptions import ManifestError

from .models import ManifestSpec


class ManifestAdapter(Protocol):
    """Producer-owned validation adapter exposed to the shared catalog."""

    @property
    def spec(self) -> ManifestSpec:
        """Return stable registration metadata."""

    def validate(self, path: Path) -> int:
        """Validate a manifest and return its schema version."""


class ManifestRegistry:
    """Deterministic registry resolving adapters by id or exact filename."""

    def __init__(self, adapters: Iterable[ManifestAdapter] = ()) -> None:
        self._by_id: dict[str, ManifestAdapter] = {}
        self._by_filename: dict[str, ManifestAdapter] = {}
        for adapter in adapters:
            self.register(adapter)

    def register(self, adapter: ManifestAdapter) -> None:
        """Register one unambiguous manifest adapter."""

        spec = adapter.spec
        if not spec.manifest_id or not spec.filename:
            raise ManifestError("Manifest id and filename must not be empty.")
        if not spec.supported_schema_versions or any(
            version < 1 for version in spec.supported_schema_versions
        ):
            raise ManifestError("Manifest schema versions must be positive integers.")
        if spec.manifest_id in self._by_id:
            raise ManifestError(f"Duplicate manifest id: {spec.manifest_id}")
        if spec.filename in self._by_filename:
            raise ManifestError(f"Duplicate manifest filename: {spec.filename}")
        self._by_id[spec.manifest_id] = adapter
        self._by_filename[spec.filename] = adapter

    def resolve_id(self, manifest_id: str) -> ManifestAdapter:
        """Resolve a registered adapter by stable id."""

        try:
            return self._by_id[manifest_id]
        except KeyError as exc:
            raise ManifestError(f"Unknown manifest id: {manifest_id}") from exc

    def resolve_filename(self, filename: str) -> ManifestAdapter | None:
        """Resolve an adapter by its exact, registered filename."""

        return self._by_filename.get(filename)

    @property
    def adapters(self) -> tuple[ManifestAdapter, ...]:
        """Return adapters in deterministic manifest-id order."""

        return tuple(self._by_id[key] for key in sorted(self._by_id))
