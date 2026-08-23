"""Bounded, deterministic discovery of exact plugin manifest filenames."""

from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path

from Engineering.core.exceptions import PluginError

from .manifest import PLUGIN_MANIFEST_NAME, PluginManifestReader
from .models import (
    PluginDiscoveryRoot,
    PluginInspectionReport,
    PluginIssue,
    PluginRecord,
)

DEFAULT_IGNORED_PLUGIN_DIRECTORIES = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
        "target",
    }
)


class PluginDiscoveryService:
    """Discover and parse metadata below explicitly approved roots."""

    def __init__(self, reader: PluginManifestReader | None = None) -> None:
        self._reader = reader or PluginManifestReader()

    def inspect(self, root: Path) -> PluginInspectionReport:
        """Inspect one root without importing code or changing the filesystem."""

        if root.is_symlink():
            raise PluginError(f"Plugin discovery root must not be a symlink: {root}")
        if not root.resolve().is_dir():
            raise PluginError(f"Plugin discovery root is not a directory: {root}")
        return self.inspect_roots((PluginDiscoveryRoot("project", root),))

    def inspect_roots(
        self, roots: Iterable[PluginDiscoveryRoot]
    ) -> PluginInspectionReport:
        """Inspect multiple labeled roots with deterministic aggregation."""

        ordered_roots = tuple(sorted(roots, key=lambda item: item.root_id))
        if not ordered_roots:
            raise PluginError("At least one plugin discovery root is required.")
        root_ids = tuple(item.root_id for item in ordered_roots)
        if len(set(root_ids)) != len(root_ids):
            raise PluginError("Plugin discovery root ids must be unique.")

        resolved_paths: set[Path] = set()
        records: list[PluginRecord] = []
        issues: list[PluginIssue] = []
        for discovery_root in ordered_roots:
            root = discovery_root.path
            resolved_root = root.resolve()
            if resolved_root in resolved_paths:
                raise PluginError("Plugin discovery root paths must be unique.")
            resolved_paths.add(resolved_root)
            if root.is_symlink():
                issues.append(
                    PluginIssue(
                        ".",
                        "plugin.root.symlink",
                        "Symlinked plugin discovery roots are not inspected.",
                        discovery_root.root_id,
                    )
                )
                continue
            if not resolved_root.is_dir():
                issues.append(
                    PluginIssue(
                        ".",
                        "plugin.root.missing",
                        "Plugin discovery root is not a directory.",
                        discovery_root.root_id,
                    )
                )
                continue
            root_records, root_issues = self._inspect_root(
                discovery_root.root_id, resolved_root
            )
            records.extend(root_records)
            issues.extend(root_issues)

        records.sort(key=lambda record: (record.root_id, record.relative_path))
        seen: dict[tuple[str, str], tuple[str, str]] = {}
        for record in records:
            key = (record.plugin_id, record.version)
            previous = seen.get(key)
            if previous is not None:
                previous_root, previous_path = previous
                issues.append(
                    PluginIssue(
                        record.relative_path,
                        "plugin.identity.duplicate",
                        f"Duplicate plugin identity {record.plugin_id} version "
                        f"{record.version}; first declared at "
                        f"{previous_root}:{previous_path}.",
                        record.root_id,
                    )
                )
            else:
                seen[key] = (record.root_id, record.relative_path)

        return PluginInspectionReport(
            records=tuple(records),
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

    def _inspect_root(
        self, root_id: str, resolved_root: Path
    ) -> tuple[list[PluginRecord], list[PluginIssue]]:
        records: list[PluginRecord] = []
        issues: list[PluginIssue] = []
        for path in self._discover(resolved_root):
            relative_path = path.relative_to(resolved_root).as_posix()
            if path.is_symlink():
                issues.append(
                    PluginIssue(
                        relative_path,
                        "plugin.symlink",
                        "Symlinked plugin manifests are not inspected.",
                        root_id,
                    )
                )
                continue
            try:
                resolved_path = path.resolve(strict=True)
                if not resolved_path.is_relative_to(resolved_root):
                    raise PluginError(
                        "Plugin manifest resolves outside the discovery root."
                    )
                manifest = self._reader.read(resolved_path)
            except (OSError, PluginError) as exc:
                issues.append(
                    PluginIssue(
                        relative_path,
                        "plugin.manifest.invalid",
                        str(exc),
                        root_id,
                    )
                )
                continue
            records.append(PluginRecord(relative_path, manifest, root_id))
        return records, issues

    @staticmethod
    def _discover(root: Path) -> tuple[Path, ...]:
        paths: list[Path] = []
        for directory, names, filenames in os.walk(root, followlinks=False):
            directory_path = Path(directory)
            names[:] = sorted(
                name
                for name in names
                if name not in DEFAULT_IGNORED_PLUGIN_DIRECTORIES
                and not (directory_path / name).is_symlink()
            )
            if PLUGIN_MANIFEST_NAME in filenames:
                paths.append(directory_path / PLUGIN_MANIFEST_NAME)
        return tuple(paths)
