"""Bounded deterministic discovery of exact AI-provider manifest filenames."""

from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path

from Engineering.core.exceptions import ProviderError

from .manifest import AI_PROVIDER_MANIFEST_NAME, ProviderManifestReader
from .models import (
    ProviderDiscoveryRoot,
    ProviderInspectionReport,
    ProviderIssue,
    ProviderRecord,
)

DEFAULT_IGNORED_PROVIDER_DIRECTORIES = frozenset(
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


class ProviderDiscoveryService:
    """Discover provider metadata below explicitly approved roots."""

    def __init__(self, reader: ProviderManifestReader | None = None) -> None:
        self._reader = reader or ProviderManifestReader()

    def inspect(self, root: Path) -> ProviderInspectionReport:
        if root.is_symlink():
            raise ProviderError(f"Provider discovery root must not be a symlink: {root}")
        if not root.resolve().is_dir():
            raise ProviderError(f"Provider discovery root is not a directory: {root}")
        return self.inspect_roots((ProviderDiscoveryRoot("project", root),))

    def inspect_roots(self, roots: Iterable[ProviderDiscoveryRoot]) -> ProviderInspectionReport:
        ordered_roots = tuple(sorted(roots, key=lambda item: item.root_id))
        if not ordered_roots:
            raise ProviderError("At least one provider discovery root is required.")
        root_ids = tuple(item.root_id for item in ordered_roots)
        if len(set(root_ids)) != len(root_ids):
            raise ProviderError("Provider discovery root ids must be unique.")

        resolved_paths: set[Path] = set()
        records: list[ProviderRecord] = []
        issues: list[ProviderIssue] = []
        for discovery_root in ordered_roots:
            resolved_root = discovery_root.path.resolve()
            if resolved_root in resolved_paths:
                raise ProviderError("Provider discovery root paths must be unique.")
            resolved_paths.add(resolved_root)
            if discovery_root.path.is_symlink():
                issues.append(
                    ProviderIssue(
                        ".",
                        "provider.root.symlink",
                        "Symlinked provider discovery roots are not inspected.",
                        discovery_root.root_id,
                    )
                )
                continue
            if not resolved_root.is_dir():
                issues.append(
                    ProviderIssue(
                        ".",
                        "provider.root.missing",
                        "Provider discovery root is not a directory.",
                        discovery_root.root_id,
                    )
                )
                continue
            root_records, root_issues = self._inspect_root(discovery_root.root_id, resolved_root)
            records.extend(root_records)
            issues.extend(root_issues)

        records.sort(key=lambda item: (item.root_id, item.relative_path))
        seen: dict[tuple[str, str], tuple[str, str]] = {}
        for record in records:
            key = (record.provider_id, record.version)
            previous = seen.get(key)
            if previous is not None:
                issues.append(
                    ProviderIssue(
                        record.relative_path,
                        "provider.identity.duplicate",
                        (
                            f"Duplicate provider identity {record.provider_id} "
                            f"version {record.version}; first declared at "
                            f"{previous[0]}:{previous[1]}."
                        ),
                        record.root_id,
                    )
                )
            else:
                seen[key] = (record.root_id, record.relative_path)
        return ProviderInspectionReport(
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
    ) -> tuple[list[ProviderRecord], list[ProviderIssue]]:
        records: list[ProviderRecord] = []
        issues: list[ProviderIssue] = []
        for path in self._discover(resolved_root):
            relative_path = path.relative_to(resolved_root).as_posix()
            if path.is_symlink():
                issues.append(
                    ProviderIssue(
                        relative_path,
                        "provider.symlink",
                        "Symlinked provider manifests are not inspected.",
                        root_id,
                    )
                )
                continue
            try:
                resolved_path = path.resolve(strict=True)
                if not resolved_path.is_relative_to(resolved_root):
                    raise ProviderError("Provider manifest resolves outside the discovery root.")
                manifest = self._reader.read(resolved_path)
            except (OSError, ProviderError) as exc:
                issues.append(
                    ProviderIssue(
                        relative_path,
                        "provider.manifest.invalid",
                        str(exc),
                        root_id,
                    )
                )
                continue
            records.append(ProviderRecord(relative_path, manifest, root_id))
        return records, issues

    @staticmethod
    def _discover(root: Path) -> tuple[Path, ...]:
        paths: list[Path] = []
        for directory, names, filenames in os.walk(root, followlinks=False):
            directory_path = Path(directory)
            names[:] = sorted(
                name
                for name in names
                if name not in DEFAULT_IGNORED_PROVIDER_DIRECTORIES
                and not (directory_path / name).is_symlink()
            )
            if AI_PROVIDER_MANIFEST_NAME in filenames:
                paths.append(directory_path / AI_PROVIDER_MANIFEST_NAME)
        return tuple(paths)
