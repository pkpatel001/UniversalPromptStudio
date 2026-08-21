"""Local release preconditions for E-011."""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
import tomllib
from pathlib import Path

from packaging.version import InvalidVersion, Version

from Engineering.core.filesystem import read_yaml

from .models import (
    PackageFormat,
    ReleaseContext,
    ReleasePreconditionIssue,
    ReleasePreconditionReport,
)

_VERSION_COMPONENT_PATTERN = re.compile(
    r'^(MAJOR|MINOR|PATCH|STAGE)\s*=\s*(?:([0-9]+)|["\']([^"\']+)["\'])',
    re.MULTILINE,
)
_REQUIRED_BUILD_STEPS = {
    "build.validate-project",
    "build.python-syntax",
    "build.backend-inventory",
    "build.frontend-readiness",
}


class ReleasePreconditionChecker:
    """Check metadata, tooling, build evidence, and local safety boundaries."""

    def check(
        self,
        context: ReleaseContext,
        formats: tuple[PackageFormat, ...],
    ) -> ReleasePreconditionReport:
        """Return every deterministic release-readiness issue."""

        issues: list[ReleasePreconditionIssue] = []
        self._check_output(context, issues)
        self._check_required_files(context.project_root, issues)
        self._check_metadata(context, issues)
        self._check_build_manifest(context.project_root, issues)
        self._check_tools(issues, formats)
        if PackageFormat.FRONTEND_ZIP in formats:
            self._check_frontend_lock(context.project_root, issues)
        self._check_worktree(context.project_root, issues)
        return ReleasePreconditionReport(tuple(sorted(issues, key=lambda item: item.code)))

    @staticmethod
    def _add(
        issues: list[ReleasePreconditionIssue], code: str, message: str
    ) -> None:
        issues.append(ReleasePreconditionIssue(code, message))

    def _check_output(
        self,
        context: ReleaseContext,
        issues: list[ReleasePreconditionIssue],
    ) -> None:
        expected = (context.project_root / "release").resolve()
        if context.output_root.resolve() != expected:
            self._add(
                issues,
                "output.noncanonical",
                "Release output must be the canonical project release/ directory.",
            )
        if context.output_root.exists() and any(context.output_root.iterdir()):
            if not context.overwrite:
                self._add(
                    issues,
                    "output.exists",
                    "Release output is not empty; pass --overwrite or clean it first.",
                )

    def _check_required_files(
        self, root: Path, issues: list[ReleasePreconditionIssue]
    ) -> None:
        for relative in ("LICENSE", "NOTICE", "COPYRIGHT", "README.md"):
            if not (root / relative).is_file():
                self._add(
                    issues,
                    f"metadata.missing-{relative.lower()}",
                    f"Required release file is missing: {relative}.",
                )

    def _check_metadata(
        self,
        context: ReleaseContext,
        issues: list[ReleasePreconditionIssue],
    ) -> None:
        root = context.project_root
        try:
            pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
            package = json.loads((root / "Frontend" / "package.json").read_text(encoding="utf-8"))
            tauri = json.loads(
                (root / "Frontend" / "src-tauri" / "tauri.conf.json").read_text(
                    encoding="utf-8"
                )
            )
            project_config = read_yaml(root / "Engineering" / "config" / "project.yaml")
            engineering_version = (root / "Engineering" / "core" / "version.py").read_text(
                encoding="utf-8"
            )
        except (OSError, UnicodeError, ValueError, TypeError) as exc:
            self._add(issues, "metadata.unreadable", f"Cannot read release metadata: {exc}")
            return

        project = pyproject.get("project")
        configured = project_config.get("project")
        components = {
            match.group(1): match.group(2) or match.group(3)
            for match in _VERSION_COMPONENT_PATTERN.finditer(engineering_version)
        }
        toolkit_version = None
        if all(key in components for key in ("MAJOR", "MINOR", "PATCH", "STAGE")):
            toolkit_version = (
                f"{components['MAJOR']}.{components['MINOR']}.{components['PATCH']}"
                f"-{components['STAGE']}"
            )
        if not isinstance(project, dict) or not isinstance(configured, dict):
            self._add(issues, "metadata.invalid", "Project metadata mappings are invalid.")
            return
        values: dict[str, object] = {
            "pyproject.toml": project.get("version"),
            "Engineering/config/project.yaml": configured.get("version"),
            "Engineering/core/version.py": toolkit_version,
            "Frontend/package.json": (
                package.get("version") if isinstance(package, dict) else None
            ),
            "Frontend/src-tauri/tauri.conf.json": (
                tauri.get("version") if isinstance(tauri, dict) else None
            ),
        }
        expected = Version(context.version.value)
        for source, value in values.items():
            try:
                actual = Version(value) if isinstance(value, str) else None
            except InvalidVersion:
                actual = None
            if actual != expected:
                self._add(
                    issues,
                    f"version.mismatch-{source.lower().replace('/', '-').replace('.', '-')}",
                    f"{source} does not represent release version {context.version.value}.",
                )

        urls = project.get("urls")
        if not isinstance(urls, dict) or any(
            not isinstance(value, str) or "<your-github>" in value
            for value in urls.values()
        ):
            self._add(issues, "metadata.urls", "Project URLs are missing or contain placeholders.")

        scripts = project.get("scripts")
        if not isinstance(scripts, dict) or not isinstance(
            scripts.get("ups-engineering"), str
        ):
            self._add(issues, "metadata.entry-point", "Python console entry point is missing.")

        setuptools = pyproject.get("tool", {}).get("setuptools", {})
        package_data = setuptools.get("package-data", {}) if isinstance(setuptools, dict) else {}
        if not isinstance(package_data, dict) or "Engineering" not in package_data:
            self._add(
                issues,
                "metadata.package-data",
                "Engineering package data is not configured.",
            )

    def _check_build_manifest(
        self, root: Path, issues: list[ReleasePreconditionIssue]
    ) -> None:
        path = root / "build" / "build-manifest.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            raw_steps = data.get("steps") if isinstance(data, dict) else None
            if not isinstance(raw_steps, list):
                raise ValueError("steps must be a list")
            succeeded = {
                step.get("step_id")
                for step in raw_steps
                if isinstance(step, dict) and step.get("state") == "succeeded"
            }
            if not _REQUIRED_BUILD_STEPS.issubset(succeeded):
                raise ValueError("required full-build steps did not succeed")
        except (OSError, UnicodeError, ValueError, TypeError, json.JSONDecodeError) as exc:
            self._add(
                issues,
                "build.manifest",
                f"A successful E-010 full build manifest is required: {exc}",
            )

    def _check_tools(
        self,
        issues: list[ReleasePreconditionIssue],
        formats: tuple[PackageFormat, ...],
    ) -> None:
        if any(item in formats for item in (PackageFormat.SDIST, PackageFormat.WHEEL)):
            missing = [
                name
                for name in ("build", "setuptools", "wheel")
                if importlib.util.find_spec(name) is None
            ]
        else:
            missing = []
        if missing:
            self._add(
                issues,
                "packaging.python-tools",
                f"Missing Python packaging tools: {', '.join(missing)}.",
            )
        if PackageFormat.FRONTEND_ZIP in formats and shutil.which("npm") is None:
            self._add(issues, "packaging.npm-tool", "npm is required for frontend packaging.")

    def _check_frontend_lock(
        self, root: Path, issues: list[ReleasePreconditionIssue]
    ) -> None:
        package_path = root / "Frontend" / "package.json"
        lock_path = root / "Frontend" / "package-lock.json"
        try:
            package = json.loads(package_path.read_text(encoding="utf-8"))
            lock = json.loads(lock_path.read_text(encoding="utf-8"))
            locked_root = lock["packages"][""]
            if not isinstance(package, dict) or not isinstance(locked_root, dict):
                raise TypeError("package roots must be mappings")
            if lock.get("lockfileVersion") != 3:
                raise ValueError("lockfileVersion must be 3")
            for key in ("name", "version"):
                if locked_root.get(key) != package.get(key):
                    raise ValueError(f"locked frontend {key} does not match package.json")
            if locked_root.get("dependencies") != package.get("dependencies"):
                raise ValueError("locked frontend dependencies do not match package.json")
            if locked_root.get("devDependencies") != package.get("devDependencies"):
                raise ValueError("locked frontend devDependencies do not match package.json")
        except (OSError, UnicodeError, ValueError, KeyError, TypeError) as exc:
            self._add(
                issues,
                "packaging.frontend-lock",
                f"A synchronized npm lockfile is required: {exc}",
            )

    def _check_worktree(
        self, root: Path, issues: list[ReleasePreconditionIssue]
    ) -> None:
        completed = subprocess.run(
            [
                "git",
                "-c",
                f"safe.directory={root.as_posix()}",
                "-C",
                str(root),
                "status",
                "--porcelain",
                "--untracked-files=all",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            self._add(issues, "git.unavailable", "Cannot verify the Git working tree.")
        elif completed.stdout.strip():
            self._add(issues, "git.dirty", "The Git working tree must be clean.")
