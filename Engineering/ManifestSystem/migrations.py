"""Deterministic, non-mutating schema-migration planning for E-012.3."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from pathlib import Path

from Engineering.core.exceptions import ManifestError

from .models import (
    ManifestIssue,
    ManifestMigrationPlan,
    ManifestMigrationReport,
    ManifestMigrationStep,
    ManifestRecord,
    SchemaCompatibility,
)
from .registry import ManifestRegistry
from .service import ManifestInspectionService


class ManifestMigrationRegistry:
    """Validated graph of supported forward-only schema transitions."""

    def __init__(
        self,
        manifest_registry: ManifestRegistry,
        steps: Iterable[ManifestMigrationStep] = (),
    ) -> None:
        self.manifest_registry = manifest_registry
        self._by_transition: dict[tuple[str, int, int], ManifestMigrationStep] = {}
        self._migration_ids: set[str] = set()
        for step in steps:
            self.register(step)

    def register(self, step: ManifestMigrationStep) -> None:
        """Register one safe, unambiguous forward transition."""

        if not step.migration_id or not step.description:
            raise ManifestError("Migration id and description must not be empty.")
        if type(step.source_version) is not int or type(step.target_version) is not int:
            raise ManifestError("Migration schema versions must be integers.")
        if step.source_version >= step.target_version:
            raise ManifestError("Manifest migrations must be forward-only transitions.")
        if step.source_version < 0 or step.target_version < 1:
            raise ManifestError("Migration schema versions are outside the supported range.")
        adapter = self.manifest_registry.resolve_id(step.manifest_id)
        readable = adapter.spec.supported_schema_versions
        if step.source_version not in readable or step.target_version not in readable:
            raise ManifestError(
                f"Migration {step.migration_id} references an unreadable schema version."
            )
        if step.migration_id in self._migration_ids:
            raise ManifestError(f"Duplicate migration id: {step.migration_id}")
        key = (step.manifest_id, step.source_version, step.target_version)
        if key in self._by_transition:
            raise ManifestError(
                f"Duplicate manifest migration: {step.manifest_id} "
                f"{step.source_version}->{step.target_version}"
            )
        self._migration_ids.add(step.migration_id)
        self._by_transition[key] = step

    def route(
        self, manifest_id: str, source_version: int, target_version: int
    ) -> tuple[ManifestMigrationStep, ...] | None:
        """Return the shortest deterministic route, or None when none is registered."""

        self.manifest_registry.resolve_id(manifest_id)
        if source_version == target_version:
            return ()
        queue: deque[tuple[int, tuple[ManifestMigrationStep, ...]]] = deque(
            ((source_version, ()),)
        )
        visited = {source_version}
        while queue:
            version, route = queue.popleft()
            outgoing = sorted(
                (
                    step
                    for (registered_id, registered_source, _), step
                    in self._by_transition.items()
                    if registered_id == manifest_id and registered_source == version
                ),
                key=lambda step: (step.target_version, step.migration_id),
            )
            for step in outgoing:
                next_route = (*route, step)
                if step.target_version == target_version:
                    return next_route
                if step.target_version not in visited:
                    visited.add(step.target_version)
                    queue.append((step.target_version, next_route))
        return None

    @property
    def steps(self) -> tuple[ManifestMigrationStep, ...]:
        """Return registered steps in deterministic order."""

        return tuple(
            self._by_transition[key]
            for key in sorted(self._by_transition)
        )


class ManifestMigrationPlanner:
    """Create plans for validated backward-readable manifest records."""

    def __init__(
        self,
        manifest_registry: ManifestRegistry,
        migration_registry: ManifestMigrationRegistry,
    ) -> None:
        self.manifest_registry = manifest_registry
        self.migration_registry = migration_registry

    def plan(
        self, records: Iterable[ManifestRecord]
    ) -> tuple[tuple[ManifestMigrationPlan, ...], tuple[ManifestIssue, ...]]:
        """Plan upgrades without transforming or writing manifest payloads."""

        plans: list[ManifestMigrationPlan] = []
        issues: list[ManifestIssue] = []
        for record in sorted(records, key=lambda item: item.relative_path):
            if record.compatibility != SchemaCompatibility.READABLE:
                continue
            adapter = self.manifest_registry.resolve_id(record.manifest_id)
            target_version = adapter.spec.schema_contract.current_version
            route = self.migration_registry.route(
                record.manifest_id, record.schema_version, target_version
            )
            if route is None:
                issues.append(
                    ManifestIssue(
                        record.relative_path,
                        "manifest.migration.unavailable",
                        f"No migration route is registered for {record.manifest_id} "
                        f"schema {record.schema_version}->{target_version}.",
                    )
                )
                continue
            plans.append(
                ManifestMigrationPlan(
                    manifest_id=record.manifest_id,
                    relative_path=record.relative_path,
                    source_version=record.schema_version,
                    target_version=target_version,
                    steps=route,
                )
            )
        return tuple(plans), tuple(issues)


class ManifestMigrationService:
    """Inspect a tree and report migration plans without changing any files."""

    def __init__(
        self,
        inspection_service: ManifestInspectionService | None = None,
        migration_registry: ManifestMigrationRegistry | None = None,
    ) -> None:
        self.inspection_service = inspection_service or ManifestInspectionService()
        self.migration_registry = migration_registry or ManifestMigrationRegistry(
            self.inspection_service.registry,
            default_manifest_migrations(),
        )
        self.planner = ManifestMigrationPlanner(
            self.inspection_service.registry,
            self.migration_registry,
        )

    def plan(self, root: Path) -> ManifestMigrationReport:
        """Inspect root and produce deterministic in-memory migration plans."""

        inspection = self.inspection_service.inspect(root)
        plans, planning_issues = self.planner.plan(inspection.records)
        issues = tuple(
            sorted(
                (*inspection.issues, *planning_issues),
                key=lambda item: (item.relative_path, item.code, item.message),
            )
        )
        return ManifestMigrationReport(plans, issues)


def default_manifest_migrations() -> tuple[ManifestMigrationStep, ...]:
    """Return built-in declarative migration steps."""

    return (
        ManifestMigrationStep(
            manifest_id="ups.documentation",
            source_version=0,
            target_version=1,
            migration_id="ups.documentation.v0-to-v1",
            description=(
                "Add root schema_version: 1 while preserving the validated manifest payload."
            ),
        ),
    )
