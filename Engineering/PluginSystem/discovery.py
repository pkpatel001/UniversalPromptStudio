"""Bounded, deterministic discovery of exact plugin manifest filenames."""

from __future__ import annotations

import os
from pathlib import Path

from Engineering.core.exceptions import PluginError

from .manifest import PLUGIN_MANIFEST_NAME, PluginManifestReader
from .models import PluginInspectionReport, PluginIssue, PluginRecord

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
    """Discover and parse plugin metadata below one explicitly approved root."""

    def __init__(self, reader: PluginManifestReader | None = None) -> None:
        self._reader = reader or PluginManifestReader()

    def inspect(self, root: Path) -> PluginInspectionReport:
        """Inspect one root without importing code or changing the filesystem."""

        resolved_root = root.resolve()
        if not resolved_root.is_dir():
            raise PluginError(f"Plugin discovery root is not a directory: {root}")

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
                    )
                )
                continue
            records.append(PluginRecord(relative_path, manifest))

        records.sort(key=lambda record: record.relative_path)
        seen: dict[tuple[str, str], str] = {}
        for record in records:
            key = (record.plugin_id, record.version)
            previous = seen.get(key)
            if previous is not None:
                issues.append(
                    PluginIssue(
                        record.relative_path,
                        "plugin.identity.duplicate",
                        f"Duplicate plugin identity {record.plugin_id} version "
                        f"{record.version}; first declared at {previous}.",
                    )
                )
            else:
                seen[key] = record.relative_path

        return PluginInspectionReport(
            records=tuple(records),
            issues=tuple(
                sorted(
                    issues,
                    key=lambda issue: (
                        issue.relative_path,
                        issue.code,
                        issue.message,
                    ),
                )
            ),
        )

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
