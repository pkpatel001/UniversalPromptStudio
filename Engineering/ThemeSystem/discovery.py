"""Bounded deterministic discovery of exact theme manifest filenames."""

from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path

from Engineering.core.exceptions import ThemeError

from .manifest import THEME_MANIFEST_NAME, ThemeManifestReader
from .models import ThemeDiscoveryRoot, ThemeInspectionReport, ThemeIssue, ThemeRecord
from .provenance import (
    THEME_MANAGED_DIRECTORY,
    ThemeManagedState,
    ThemeManagedThemeVerifier,
)

DEFAULT_IGNORED_THEME_DIRECTORIES = frozenset(
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
THEME_STAGING_DIRECTORY_PREFIX = ".ups-theme-"


class ThemeDiscoveryService:
    """Discover declarative theme metadata below explicitly approved roots."""

    def __init__(
        self,
        reader: ThemeManifestReader | None = None,
        managed_verifier: ThemeManagedThemeVerifier | None = None,
    ) -> None:
        self._reader = reader or ThemeManifestReader()
        self._managed_verifier = managed_verifier or ThemeManagedThemeVerifier(
            manifest_reader=self._reader
        )

    def inspect(self, root: Path) -> ThemeInspectionReport:
        if root.is_symlink():
            raise ThemeError(f"Theme discovery root must not be a symlink: {root}")
        if not root.resolve().is_dir():
            raise ThemeError(f"Theme discovery root is not a directory: {root}")
        return self.inspect_roots((ThemeDiscoveryRoot("project", root),))

    def inspect_roots(self, roots: Iterable[ThemeDiscoveryRoot]) -> ThemeInspectionReport:
        ordered_roots = tuple(sorted(roots, key=lambda item: item.root_id))
        if not ordered_roots:
            raise ThemeError("At least one theme discovery root is required.")
        root_ids = tuple(item.root_id for item in ordered_roots)
        if len(set(root_ids)) != len(root_ids):
            raise ThemeError("Theme discovery root ids must be unique.")

        resolved_paths: set[Path] = set()
        records: list[ThemeRecord] = []
        issues: list[ThemeIssue] = []
        for discovery_root in ordered_roots:
            resolved_root = discovery_root.path.resolve()
            if resolved_root in resolved_paths:
                raise ThemeError("Theme discovery root paths must be unique.")
            resolved_paths.add(resolved_root)
            if discovery_root.path.is_symlink():
                issues.append(
                    ThemeIssue(
                        ".",
                        "theme.root.symlink",
                        "Symlinked theme discovery roots are not inspected.",
                        discovery_root.root_id,
                    )
                )
                continue
            if not resolved_root.is_dir():
                issues.append(
                    ThemeIssue(
                        ".",
                        "theme.root.missing",
                        "Theme discovery root is not a directory.",
                        discovery_root.root_id,
                    )
                )
                continue
            root_records, root_issues = self._inspect_root(
                discovery_root.root_id, resolved_root
            )
            records.extend(root_records)
            issues.extend(root_issues)

        records.sort(key=lambda item: (item.root_id, item.relative_path))
        seen: dict[tuple[str, str], tuple[str, str]] = {}
        for record in records:
            key = (record.theme_id, record.version)
            previous = seen.get(key)
            if previous is not None:
                issues.append(
                    ThemeIssue(
                        record.relative_path,
                        "theme.identity.duplicate",
                        (
                            f"Duplicate theme identity {record.theme_id} "
                            f"version {record.version}; first declared at "
                            f"{previous[0]}:{previous[1]}."
                        ),
                        record.root_id,
                    )
                )
            else:
                seen[key] = (record.root_id, record.relative_path)
        return ThemeInspectionReport(
            tuple(records),
            tuple(
                sorted(
                    issues,
                    key=lambda item: (
                        item.root_id,
                        item.relative_path,
                        item.code,
                        item.message,
                    ),
                )
            ),
        )

    def _inspect_root(
        self, root_id: str, resolved_root: Path
    ) -> tuple[list[ThemeRecord], list[ThemeIssue]]:
        records: list[ThemeRecord] = []
        issues: list[ThemeIssue] = []
        for path in self._discover(resolved_root):
            relative_path = path.relative_to(resolved_root).as_posix()
            if path.is_symlink():
                issues.append(
                    ThemeIssue(
                        relative_path,
                        "theme.symlink",
                        "Symlinked theme manifests are not inspected.",
                        root_id,
                    )
                )
                continue
            try:
                resolved_path = path.resolve(strict=True)
                if not resolved_path.is_relative_to(resolved_root):
                    raise ThemeError("Theme manifest resolves outside the discovery root.")
                managed_container = self._managed_container(resolved_root, resolved_path)
                if managed_container is None:
                    manifest = self._reader.read(resolved_path)
                else:
                    managed = self._managed_verifier.verify_directory(
                        resolved_path.parent,
                        managed_container,
                        ThemeManagedState.ACTIVE,
                        root_id=root_id,
                    )
                    manifest = managed.manifest
            except (OSError, ThemeError) as exc:
                code = (
                    "theme.provenance.invalid"
                    if self._managed_container(resolved_root, path) is not None
                    else "theme.manifest.invalid"
                )
                issues.append(
                    ThemeIssue(
                        relative_path,
                        code,
                        str(exc),
                        root_id,
                    )
                )
                continue
            records.append(ThemeRecord(relative_path, manifest, root_id))
        return records, issues

    @staticmethod
    def _managed_container(root: Path, manifest_path: Path) -> Path | None:
        if root.name.casefold() == THEME_MANAGED_DIRECTORY.casefold():
            return root
        try:
            relative = manifest_path.relative_to(root)
        except ValueError:
            return None
        if (
            relative.parts
            and relative.parts[0].casefold() == THEME_MANAGED_DIRECTORY.casefold()
        ):
            return root / relative.parts[0]
        return None

    @staticmethod
    def _discover(root: Path) -> tuple[Path, ...]:
        paths: list[Path] = []
        for directory, names, filenames in os.walk(root, followlinks=False):
            directory_path = Path(directory)
            names[:] = sorted(
                name
                for name in names
                if name not in DEFAULT_IGNORED_THEME_DIRECTORIES
                and not name.startswith(THEME_STAGING_DIRECTORY_PREFIX)
                and not (directory_path / name).is_symlink()
            )
            if THEME_MANIFEST_NAME in filenames:
                paths.append(directory_path / THEME_MANIFEST_NAME)
        return tuple(paths)


__all__ = [
    "DEFAULT_IGNORED_THEME_DIRECTORIES",
    "THEME_STAGING_DIRECTORY_PREFIX",
    "ThemeDiscoveryService",
]
