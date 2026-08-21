"""Cross-manifest dependency and cardinality validation for E-012.2."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from Engineering.core.exceptions import ManifestError

from .models import ManifestIssue, ManifestRecord
from .registry import ManifestRegistry


@dataclass(frozen=True, slots=True)
class ManifestDependency:
    """A required relationship between two registered manifest families."""

    source_manifest_id: str
    required_manifest_id: str


class ManifestRelationshipValidator:
    """Validate cardinality and required dependencies for an inventory."""

    def __init__(
        self,
        registry: ManifestRegistry,
        dependencies: Iterable[ManifestDependency] = (),
    ) -> None:
        self._registry = registry
        self._dependencies = tuple(
            sorted(
                dependencies,
                key=lambda item: (item.source_manifest_id, item.required_manifest_id),
            )
        )
        self._validate_dependencies()

    def validate(self, records: Iterable[ManifestRecord]) -> tuple[ManifestIssue, ...]:
        """Return deterministic relationship issues for validated records."""

        by_id: dict[str, list[ManifestRecord]] = {}
        for record in records:
            self._registry.resolve_id(record.manifest_id)
            by_id.setdefault(record.manifest_id, []).append(record)

        issues: list[ManifestIssue] = []
        for adapter in self._registry.adapters:
            matches = sorted(
                by_id.get(adapter.spec.manifest_id, ()),
                key=lambda item: item.relative_path,
            )
            if not adapter.spec.allow_multiple and len(matches) > 1:
                for duplicate in matches[1:]:
                    issues.append(
                        ManifestIssue(
                            duplicate.relative_path,
                            "manifest.cardinality",
                            f"Manifest family {adapter.spec.manifest_id} allows only one document.",
                        )
                    )

        for dependency in self._dependencies:
            sources = sorted(
                by_id.get(dependency.source_manifest_id, ()),
                key=lambda item: item.relative_path,
            )
            if sources and not by_id.get(dependency.required_manifest_id):
                for source in sources:
                    issues.append(
                        ManifestIssue(
                            source.relative_path,
                            "manifest.relationship.missing",
                            f"{dependency.source_manifest_id} requires "
                            f"{dependency.required_manifest_id}.",
                        )
                    )

        return tuple(
            sorted(issues, key=lambda item: (item.relative_path, item.code, item.message))
        )

    def _validate_dependencies(self) -> None:
        seen: set[tuple[str, str]] = set()
        graph: dict[str, set[str]] = {}
        for dependency in self._dependencies:
            source = dependency.source_manifest_id
            required = dependency.required_manifest_id
            self._registry.resolve_id(source)
            self._registry.resolve_id(required)
            if source == required:
                raise ManifestError("Manifest dependencies cannot reference themselves.")
            edge = (source, required)
            if edge in seen:
                raise ManifestError(f"Duplicate manifest dependency: {source} -> {required}")
            seen.add(edge)
            graph.setdefault(source, set()).add(required)

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(manifest_id: str) -> None:
            if manifest_id in visiting:
                raise ManifestError("Cyclic manifest dependency detected.")
            if manifest_id in visited:
                return
            visiting.add(manifest_id)
            for required in sorted(graph.get(manifest_id, ())):
                visit(required)
            visiting.remove(manifest_id)
            visited.add(manifest_id)

        for manifest_id in sorted(graph):
            visit(manifest_id)


def default_manifest_dependencies() -> tuple[ManifestDependency, ...]:
    """Return built-in relationships in deterministic order."""

    return (ManifestDependency("ups.release", "ups.build"),)
