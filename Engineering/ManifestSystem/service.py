"""Read-only discovery and validation service for E-012 manifests."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from Engineering.core.exceptions import EngineeringError, ManifestError
from Engineering.core.filesystem import read_bytes

from .adapters import default_manifest_adapters
from .models import (
    ManifestInspectionReport,
    ManifestIssue,
    ManifestRecord,
    ManifestValidationReport,
    SchemaCompatibility,
)
from .registry import ManifestRegistry
from .relationships import (
    ManifestRelationshipValidator,
    default_manifest_dependencies,
)

DEFAULT_IGNORED_DIRECTORIES = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "node_modules",
        "target",
    }
)


class ManifestInspectionService:
    """Discover registered filenames and validate them through their owners."""

    def __init__(self, registry: ManifestRegistry | None = None) -> None:
        self.registry = registry or ManifestRegistry(default_manifest_adapters())

    def inspect(self, root: Path) -> ManifestInspectionReport:
        """Inspect manifests below root without changing filesystem state."""

        resolved_root = root.resolve()
        if not resolved_root.is_dir():
            raise ManifestError(f"Manifest inspection root is not a directory: {root}")

        records: list[ManifestRecord] = []
        issues: list[ManifestIssue] = []
        for path in self._discover(resolved_root):
            relative_path = path.relative_to(resolved_root).as_posix()
            adapter = self.registry.resolve_filename(path.name)
            if adapter is None:
                continue
            if path.is_symlink():
                issues.append(
                    ManifestIssue(relative_path, "manifest.symlink", "Symlinks are not inspected.")
                )
                continue
            try:
                resolved_path = path.resolve(strict=True)
                if not resolved_path.is_relative_to(resolved_root):
                    raise ManifestError("Manifest resolves outside the inspection root.")
                schema_version = adapter.detect_schema_version(resolved_path)
                compatibility = adapter.spec.schema_contract.compatibility(schema_version)
                if compatibility == SchemaCompatibility.UNSUPPORTED:
                    issues.append(
                        ManifestIssue(
                            relative_path,
                            "manifest.schema.unsupported",
                            f"Schema version {schema_version} is not readable for "
                            f"{adapter.spec.manifest_id}.",
                        )
                    )
                    continue
                validated_version = adapter.validate(resolved_path)
                if validated_version != schema_version:
                    raise ManifestError(
                        f"Adapter for {adapter.spec.manifest_id} returned schema version "
                        f"{validated_version}, expected {schema_version}."
                    )
                digest = hashlib.sha256(read_bytes(resolved_path)).hexdigest()
            except (EngineeringError, KeyError, OSError, TypeError, ValueError) as exc:
                issues.append(
                    ManifestIssue(relative_path, "manifest.schema.invalid", str(exc))
                )
                continue
            records.append(
                ManifestRecord(
                    manifest_id=adapter.spec.manifest_id,
                    kind=adapter.spec.kind,
                    relative_path=relative_path,
                    schema_version=schema_version,
                    sha256=digest,
                    compatibility=compatibility,
                )
            )

        return ManifestInspectionReport(
            records=tuple(sorted(records, key=lambda item: item.relative_path)),
            issues=tuple(
                sorted(issues, key=lambda item: (item.relative_path, item.code, item.message))
            ),
        )

    @staticmethod
    def _discover(root: Path) -> tuple[Path, ...]:
        paths: list[Path] = []
        for directory, names, filenames in os.walk(root, followlinks=False):
            names[:] = sorted(
                name for name in names if name not in DEFAULT_IGNORED_DIRECTORIES
            )
            directory_path = Path(directory)
            paths.extend(directory_path / name for name in sorted(filenames))
        return tuple(paths)


class ManifestValidationService:
    """Validate a complete manifest set and its cross-family relationships."""

    def __init__(
        self,
        inspection_service: ManifestInspectionService | None = None,
        relationship_validator: ManifestRelationshipValidator | None = None,
    ) -> None:
        self.inspection_service = inspection_service or ManifestInspectionService()
        self.relationship_validator = relationship_validator or ManifestRelationshipValidator(
            self.inspection_service.registry,
            default_manifest_dependencies(),
        )

    def validate(self, root: Path) -> ManifestValidationReport:
        """Inspect root and validate relationships when documents are readable."""

        inspection = self.inspection_service.inspect(root)
        relationship_issues: tuple[ManifestIssue, ...] = ()
        if inspection.passed:
            relationship_issues = self.relationship_validator.validate(inspection.records)
        issues = tuple(
            sorted(
                (*inspection.issues, *relationship_issues),
                key=lambda item: (item.relative_path, item.code, item.message),
            )
        )
        return ManifestValidationReport(inspection.records, issues)
