"""Local release preconditions for E-011."""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
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


def _find_tool(name: str) -> str | None:
    """Find a tool, including rustup's standard per-user Windows location."""

    located = shutil.which(name)
    if located is not None or os.name != "nt":
        return located
    candidate = Path.home() / ".cargo" / "bin" / f"{name}.exe"
    return str(candidate) if candidate.is_file() else None


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
        self._check_metadata(context, formats, issues)
        self._check_build_manifest(context.project_root, issues)
        self._check_tools(issues, formats)
        if any(
            item in formats
            for item in (PackageFormat.FRONTEND_ZIP, PackageFormat.DESKTOP_NSIS)
        ):
            self._check_frontend_lock(context.project_root, issues)
        if PackageFormat.DESKTOP_NSIS in formats:
            self._check_desktop_project(context.project_root, issues)
            self._check_desktop_host(issues)
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
        formats: tuple[PackageFormat, ...],
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
        if PackageFormat.DESKTOP_NSIS in formats:
            try:
                cargo = tomllib.loads(
                    (root / "Frontend" / "src-tauri" / "Cargo.toml").read_text(
                        encoding="utf-8"
                    )
                )
                cargo_package = cargo.get("package")
                values["Frontend/src-tauri/Cargo.toml"] = (
                    cargo_package.get("version")
                    if isinstance(cargo_package, dict)
                    else None
                )
            except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
                self._add(
                    issues,
                    "metadata.cargo-unreadable",
                    f"Cannot read desktop Cargo metadata: {exc}",
                )
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
        if any(
            item in formats
            for item in (PackageFormat.FRONTEND_ZIP, PackageFormat.DESKTOP_NSIS)
        ) and shutil.which("npm") is None:
            self._add(issues, "packaging.npm-tool", "npm is required for frontend packaging.")
        if PackageFormat.DESKTOP_NSIS in formats:
            missing_rust = [
                name for name in ("rustup", "rustc", "cargo") if _find_tool(name) is None
            ]
            if missing_rust:
                self._add(
                    issues,
                    "packaging.rust-tools",
                    f"Missing Rust tools: {', '.join(missing_rust)}.",
                )

    def _check_desktop_project(
        self, root: Path, issues: list[ReleasePreconditionIssue]
    ) -> None:
        cargo_path = root / "Frontend" / "src-tauri" / "Cargo.toml"
        lock_path = root / "Frontend" / "src-tauri" / "Cargo.lock"
        config_path = root / "Frontend" / "src-tauri" / "tauri.conf.json"
        try:
            cargo = tomllib.loads(cargo_path.read_text(encoding="utf-8"))
            lock = tomllib.loads(lock_path.read_text(encoding="utf-8"))
            config = json.loads(config_path.read_text(encoding="utf-8"))
            dependencies = cargo.get("dependencies")
            build_dependencies = cargo.get("build-dependencies")
            if not isinstance(dependencies, dict) or "tauri" not in dependencies:
                raise ValueError("Cargo.toml must declare tauri")
            if (
                not isinstance(build_dependencies, dict)
                or "tauri-build" not in build_dependencies
            ):
                raise ValueError("Cargo.toml must declare tauri-build")
            locked = lock.get("package")
            if not isinstance(locked, list):
                raise ValueError("Cargo.lock must contain locked packages")
            locked_names = {
                item.get("name") for item in locked if isinstance(item, dict)
            }
            if not {"tauri", "tauri-build"}.issubset(locked_names):
                raise ValueError("Cargo.lock must lock tauri and tauri-build")
            bundle = config.get("bundle") if isinstance(config, dict) else None
            targets = bundle.get("targets") if isinstance(bundle, dict) else None
            if not isinstance(targets, list) or "nsis" not in targets:
                raise ValueError("tauri.conf.json must enable the NSIS target")
        except (
            OSError,
            UnicodeError,
            ValueError,
            TypeError,
            json.JSONDecodeError,
            tomllib.TOMLDecodeError,
        ) as exc:
            self._add(
                issues,
                "packaging.desktop-project",
                f"A locked Tauri v2 NSIS project is required: {exc}",
            )

    def _check_desktop_host(
        self, issues: list[ReleasePreconditionIssue]
    ) -> None:
        if sys.platform != "win32":
            self._add(
                issues,
                "packaging.desktop-platform",
                "NSIS desktop packaging requires a Windows host.",
            )
            return

        rustup = _find_tool("rustup")
        if rustup is not None:
            completed = subprocess.run(
                [rustup, "show", "active-toolchain"],
                capture_output=True,
                text=True,
                check=False,
            )
            if completed.returncode != 0 or "pc-windows-msvc" not in completed.stdout:
                self._add(
                    issues,
                    "packaging.rust-msvc",
                    "The active Rust toolchain must target Windows MSVC.",
                )

        program_files_x86 = os.environ.get("ProgramFiles(x86)")
        vswhere = (
            Path(program_files_x86)
            / "Microsoft Visual Studio"
            / "Installer"
            / "vswhere.exe"
            if program_files_x86
            else None
        )
        if vswhere is None or not vswhere.is_file():
            has_cpp_tools = False
        else:
            completed = subprocess.run(
                [
                    str(vswhere),
                    "-latest",
                    "-products",
                    "*",
                    "-requires",
                    "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
                    "-property",
                    "installationPath",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            has_cpp_tools = completed.returncode == 0 and bool(completed.stdout.strip())
        if not has_cpp_tools:
            self._add(
                issues,
                "packaging.msvc-build-tools",
                "Microsoft C++ Build Tools with Desktop development for C++ are required.",
            )

        webview_root = (
            Path(program_files_x86)
            / "Microsoft"
            / "EdgeWebView"
            / "Application"
            if program_files_x86
            else None
        )
        if webview_root is None or not any(
            path.is_dir() and path.name[0].isdigit()
            for path in webview_root.glob("*")
        ):
            self._add(
                issues,
                "packaging.webview2",
                "Microsoft Edge WebView2 Runtime is required.",
            )

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
