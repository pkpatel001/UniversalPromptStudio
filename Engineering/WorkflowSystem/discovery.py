"""Bounded deterministic discovery of exact workflow manifest filenames."""

from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path

from Engineering.core.exceptions import WorkflowError

from .manifest import WORKFLOW_MANIFEST_NAME, WorkflowManifestReader
from .models import (
    WorkflowDiscoveryRoot,
    WorkflowInspectionReport,
    WorkflowIssue,
    WorkflowRecord,
)

DEFAULT_IGNORED_WORKFLOW_DIRECTORIES = frozenset(
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
MAX_WORKFLOW_DISCOVERY_DEPTH = 16
MAX_WORKFLOW_MANIFESTS_PER_ROOT = 1024
MAX_WORKFLOW_MANIFEST_BYTES = 1_048_576


class WorkflowDiscoveryService:
    """Discover workflow definitions below explicitly approved roots."""

    def __init__(self, reader: WorkflowManifestReader | None = None) -> None:
        self._reader = reader or WorkflowManifestReader()

    def inspect(self, root: Path) -> WorkflowInspectionReport:
        if root.is_symlink():
            raise WorkflowError(f"Workflow discovery root must not be a symlink: {root}")
        if not root.resolve().is_dir():
            raise WorkflowError(f"Workflow discovery root is not a directory: {root}")
        return self.inspect_roots((WorkflowDiscoveryRoot("project", root),))

    def inspect_roots(self, roots: Iterable[WorkflowDiscoveryRoot]) -> WorkflowInspectionReport:
        ordered_roots = tuple(sorted(roots, key=lambda item: item.root_id))
        if not ordered_roots:
            raise WorkflowError("At least one workflow discovery root is required.")
        root_ids = tuple(item.root_id for item in ordered_roots)
        if len(set(root_ids)) != len(root_ids):
            raise WorkflowError("Workflow discovery root ids must be unique.")

        resolved_paths: set[Path] = set()
        records: list[WorkflowRecord] = []
        issues: list[WorkflowIssue] = []
        for discovery_root in ordered_roots:
            resolved_root = discovery_root.path.resolve()
            if resolved_root in resolved_paths:
                raise WorkflowError("Workflow discovery root paths must be unique.")
            resolved_paths.add(resolved_root)
            if discovery_root.path.is_symlink():
                issues.append(
                    WorkflowIssue(
                        ".",
                        "workflow.root.symlink",
                        "Symlinked workflow discovery roots are not inspected.",
                        discovery_root.root_id,
                    )
                )
                continue
            if not resolved_root.is_dir():
                issues.append(
                    WorkflowIssue(
                        ".",
                        "workflow.root.missing",
                        "Workflow discovery root is not a directory.",
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
            key = (record.workflow_id, record.version)
            previous = seen.get(key)
            if previous is not None:
                issues.append(
                    WorkflowIssue(
                        record.relative_path,
                        "workflow.identity.duplicate",
                        (
                            f"Duplicate workflow identity {record.workflow_id} "
                            f"version {record.version}; first declared at "
                            f"{previous[0]}:{previous[1]}."
                        ),
                        record.root_id,
                    )
                )
            else:
                seen[key] = (record.root_id, record.relative_path)
        return WorkflowInspectionReport(
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
    ) -> tuple[list[WorkflowRecord], list[WorkflowIssue]]:
        records: list[WorkflowRecord] = []
        issues: list[WorkflowIssue] = []
        paths, discovery_issues = self._discover(root_id, resolved_root)
        issues.extend(discovery_issues)
        for path in paths:
            relative_path = path.relative_to(resolved_root).as_posix()
            if path.is_symlink():
                issues.append(
                    WorkflowIssue(
                        relative_path,
                        "workflow.symlink",
                        "Symlinked workflow manifests are not inspected.",
                        root_id,
                    )
                )
                continue
            try:
                resolved_path = path.resolve(strict=True)
                if not resolved_path.is_relative_to(resolved_root):
                    raise WorkflowError("Workflow manifest resolves outside the discovery root.")
                size = resolved_path.stat().st_size
                if size > MAX_WORKFLOW_MANIFEST_BYTES:
                    issues.append(
                        WorkflowIssue(
                            relative_path,
                            "workflow.manifest.oversized",
                            (
                                f"Workflow manifest size {size} exceeds "
                                f"{MAX_WORKFLOW_MANIFEST_BYTES} bytes."
                            ),
                            root_id,
                        )
                    )
                    continue
                manifest = self._reader.read(resolved_path)
            except (OSError, WorkflowError) as exc:
                issues.append(
                    WorkflowIssue(
                        relative_path,
                        "workflow.manifest.invalid",
                        str(exc),
                        root_id,
                    )
                )
                continue
            records.append(WorkflowRecord(relative_path, manifest, root_id))
        return records, issues

    @staticmethod
    def _discover(root_id: str, root: Path) -> tuple[tuple[Path, ...], tuple[WorkflowIssue, ...]]:
        paths: list[Path] = []
        issues: list[WorkflowIssue] = []
        for directory, names, filenames in os.walk(root, followlinks=False):
            directory_path = Path(directory)
            relative = directory_path.relative_to(root)
            depth = len(relative.parts)
            names[:] = sorted(
                name
                for name in names
                if name not in DEFAULT_IGNORED_WORKFLOW_DIRECTORIES
                and not (directory_path / name).is_symlink()
            )
            if depth >= MAX_WORKFLOW_DISCOVERY_DEPTH and names:
                issues.append(
                    WorkflowIssue(
                        relative.as_posix(),
                        "workflow.discovery.depth",
                        (
                            f"Workflow discovery depth exceeds "
                            f"{MAX_WORKFLOW_DISCOVERY_DEPTH} directories."
                        ),
                        root_id,
                    )
                )
                names.clear()
            if WORKFLOW_MANIFEST_NAME in filenames:
                if len(paths) >= MAX_WORKFLOW_MANIFESTS_PER_ROOT:
                    issues.append(
                        WorkflowIssue(
                            ".",
                            "workflow.discovery.limit",
                            (
                                f"Workflow discovery exceeds "
                                f"{MAX_WORKFLOW_MANIFESTS_PER_ROOT} manifests per root."
                            ),
                            root_id,
                        )
                    )
                    break
                paths.append(directory_path / WORKFLOW_MANIFEST_NAME)
        return tuple(paths), tuple(issues)
