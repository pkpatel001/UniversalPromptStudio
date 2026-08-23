"""Deterministic, non-installing plugin dependency analysis."""

from __future__ import annotations

from dataclasses import dataclass

from packaging.specifiers import SpecifierSet

from .catalog import PluginCatalog
from .models import (
    PluginDependencyResolution,
    PluginIssue,
    PluginRecord,
)

PluginKey = tuple[str, str]


@dataclass(frozen=True, slots=True)
class PluginDependencyReport:
    """Resolved dependency selections and deterministic graph issues."""

    resolutions: tuple[PluginDependencyResolution, ...] = ()
    issues: tuple[PluginIssue, ...] = ()

    @property
    def passed(self) -> bool:
        return not self.issues


class PluginDependencyResolver:
    """Resolve installed catalog metadata without downloading or loading code."""

    def resolve(self, catalog: PluginCatalog) -> PluginDependencyReport:
        """Resolve constraints and report missing, unsatisfied, and cyclic edges."""

        resolutions: list[PluginDependencyResolution] = []
        issues: list[PluginIssue] = []
        records_by_key = {
            (record.plugin_id, record.version): record for record in catalog.records
        }
        graph: dict[PluginKey, set[PluginKey]] = {
            key: set() for key in records_by_key
        }

        for owner in catalog.records:
            owner_key = (owner.plugin_id, owner.version)
            for dependency in owner.manifest.dependencies:
                dependency_id = dependency.plugin_id.value
                available = catalog.records_for(dependency_id)
                if not available:
                    issues.append(
                        self._issue(
                            owner,
                            "plugin.dependency.missing",
                            f"Plugin {owner.plugin_id} version {owner.version} "
                            f"requires missing plugin {dependency_id} "
                            f"{dependency.version_specifier}.",
                        )
                    )
                    continue
                specifier = SpecifierSet(dependency.version_specifier)
                matching = tuple(
                    record
                    for record in available
                    if specifier.contains(
                        record.manifest.metadata.version.parsed,
                        prereleases=True,
                    )
                )
                if not matching:
                    versions = ", ".join(record.version for record in available)
                    issues.append(
                        self._issue(
                            owner,
                            "plugin.dependency.unsatisfied",
                            f"Plugin {owner.plugin_id} version {owner.version} "
                            f"requires {dependency_id} "
                            f"{dependency.version_specifier}; available versions: "
                            f"{versions}.",
                        )
                    )
                    continue
                selected = max(
                    matching,
                    key=lambda record: record.manifest.metadata.version.parsed,
                )
                graph[owner_key].add((selected.plugin_id, selected.version))
                resolutions.append(
                    PluginDependencyResolution(
                        owner_plugin_id=owner.plugin_id,
                        owner_version=owner.version,
                        dependency_plugin_id=dependency_id,
                        version_specifier=dependency.version_specifier,
                        resolved_version=selected.version,
                        owner_relative_path=owner.relative_path,
                        owner_root_id=owner.root_id,
                    )
                )

        for cycle in self._cycles(graph):
            owner = records_by_key[cycle[0]]
            path = " -> ".join(f"{item[0]}@{item[1]}" for item in (*cycle, cycle[0]))
            issues.append(
                self._issue(
                    owner,
                    "plugin.dependency.cycle",
                    f"Plugin dependency cycle detected: {path}.",
                )
            )

        return PluginDependencyReport(
            resolutions=tuple(
                sorted(
                    resolutions,
                    key=lambda item: (
                        item.owner_plugin_id,
                        item.owner_version,
                        item.dependency_plugin_id,
                    ),
                )
            ),
            issues=tuple(
                sorted(
                    issues,
                    key=lambda issue: (
                        issue.root_id,
                        issue.relative_path,
                        issue.code,
                        issue.message,
                    ),
                )
            ),
        )

    @staticmethod
    def _issue(owner: PluginRecord, code: str, message: str) -> PluginIssue:
        return PluginIssue(
            owner.relative_path,
            code,
            message,
            owner.root_id,
        )

    @staticmethod
    def _cycles(graph: dict[PluginKey, set[PluginKey]]) -> tuple[tuple[PluginKey, ...], ...]:
        state: dict[PluginKey, int] = {}
        stack: list[PluginKey] = []
        cycles: set[tuple[PluginKey, ...]] = set()

        def canonical(items: tuple[PluginKey, ...]) -> tuple[PluginKey, ...]:
            rotations = tuple(items[index:] + items[:index] for index in range(len(items)))
            return min(rotations)

        def visit(node: PluginKey) -> None:
            state[node] = 1
            stack.append(node)
            for target in sorted(graph.get(node, ())):
                target_state = state.get(target, 0)
                if target_state == 0:
                    visit(target)
                elif target_state == 1:
                    start = stack.index(target)
                    cycles.add(canonical(tuple(stack[start:])))
            stack.pop()
            state[node] = 2

        for node in sorted(graph):
            if state.get(node, 0) == 0:
                visit(node)
        return tuple(sorted(cycles))
