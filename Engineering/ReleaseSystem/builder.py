"""Infrastructure adapters for local Python and frontend package builds."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from Engineering.core.exceptions import ReleaseError
from Engineering.core.filesystem import ensure_directory

from .models import PackageFormat


class PythonPackageBuilder:
    """Build wheel and source distributions without network isolation."""

    def build(
        self,
        project_root: Path,
        output_directory: Path,
        formats: tuple[PackageFormat, ...],
    ) -> tuple[Path, ...]:
        """Build requested formats and return their generated paths."""

        ensure_directory(output_directory)
        flags: list[str] = []
        if PackageFormat.SDIST in formats:
            flags.append("--sdist")
        if PackageFormat.WHEEL in formats:
            flags.append("--wheel")
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "build",
                "--no-isolation",
                *flags,
                "--outdir",
                str(output_directory),
            ],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip()
            raise ReleaseError(f"Python package build failed: {detail}")
        artifacts = tuple(sorted(path for path in output_directory.iterdir() if path.is_file()))
        if len(artifacts) != len(formats):
            raise ReleaseError("Python package build produced an unexpected artifact count.")
        return artifacts


class FrontendPackageBuilder:
    """Install locked npm dependencies and package a production Vite build."""

    def build(
        self,
        project_root: Path,
        output_directory: Path,
        formats: tuple[PackageFormat, ...],
    ) -> tuple[Path, ...]:
        """Create a deterministic ZIP from the Vite distribution directory."""

        if PackageFormat.FRONTEND_ZIP not in formats:
            return ()
        frontend = project_root / "Frontend"
        lock_path = frontend / "package-lock.json"
        if not lock_path.is_file():
            raise ReleaseError("Frontend/package-lock.json is required for npm ci.")
        npm = shutil.which("npm")
        if npm is None:
            raise ReleaseError("npm is required for frontend packaging.")
        npm_cache = project_root / ".cache" / "npm"
        self._run(
            [npm, "ci", "--cache", str(npm_cache)],
            frontend,
            "npm ci",
        )
        self._run([npm, "run", "build"], frontend, "Vite build")

        return self.package_distribution(project_root, output_directory)

    def package_distribution(
        self,
        project_root: Path,
        output_directory: Path,
    ) -> tuple[Path, ...]:
        """Package an already-built Vite distribution deterministically."""

        frontend = project_root / "Frontend"
        package_path = frontend / "package.json"
        try:
            package = json.loads(package_path.read_text(encoding="utf-8"))
            name = package["name"]
            version = package["version"]
            if not isinstance(name, str) or not isinstance(version, str):
                raise TypeError("name and version must be strings")
        except (OSError, UnicodeError, ValueError, KeyError, TypeError) as exc:
            raise ReleaseError(f"Cannot read frontend package metadata: {exc}") from exc
        distribution = frontend / "dist"
        files = tuple(sorted(path for path in distribution.rglob("*") if path.is_file()))
        if not files:
            raise ReleaseError("Vite build produced no frontend files.")
        ensure_directory(output_directory)
        artifact = output_directory / f"{name}-{version}.zip"
        with zipfile.ZipFile(artifact, mode="w") as archive:
            for path in files:
                relative = path.relative_to(distribution).as_posix()
                info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                info.external_attr = (0o100644 & 0xFFFF) << 16
                archive.writestr(info, path.read_bytes(), compresslevel=9)
        return (artifact,)

    @staticmethod
    def _run(
        command: list[str],
        cwd: Path,
        operation: str,
        env: dict[str, str] | None = None,
    ) -> None:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip()
            raise ReleaseError(f"{operation} failed: {detail}")


class DesktopPackageBuilder:
    """Build a genuine Windows desktop installer with Tauri and NSIS."""

    def build(
        self,
        project_root: Path,
        output_directory: Path,
        formats: tuple[PackageFormat, ...],
    ) -> tuple[Path, ...]:
        """Create and stage exactly one Tauri NSIS setup executable."""

        if PackageFormat.DESKTOP_NSIS not in formats:
            return ()
        frontend = project_root / "Frontend"
        npm = shutil.which("npm")
        if npm is None:
            raise ReleaseError("npm is required for desktop packaging.")
        if not (frontend / "src-tauri" / "Cargo.lock").is_file():
            raise ReleaseError("Frontend/src-tauri/Cargo.lock is required.")

        npm_cache = project_root / ".cache" / "npm"
        cargo = shutil.which("cargo")
        if cargo is None and os.name == "nt":
            candidate = Path.home() / ".cargo" / "bin" / "cargo.exe"
            cargo = str(candidate) if candidate.is_file() else None
        if cargo is None:
            raise ReleaseError("cargo is required for desktop packaging.")
        environment = os.environ.copy()
        environment["PATH"] = str(Path(cargo).parent) + os.pathsep + environment["PATH"]
        FrontendPackageBuilder._run(
            [npm, "ci", "--cache", str(npm_cache)], frontend, "npm ci"
        )
        FrontendPackageBuilder._run(
            [npm, "run", "desktop:build"],
            frontend,
            "Tauri NSIS build",
            environment,
        )

        bundle_directory = (
            frontend / "src-tauri" / "target" / "release" / "bundle" / "nsis"
        )
        installers = tuple(sorted(bundle_directory.glob("*-setup.exe")))
        if len(installers) != 1:
            raise ReleaseError(
                "Tauri build must produce exactly one NSIS setup executable."
            )
        ensure_directory(output_directory)
        artifact = output_directory / installers[0].name
        shutil.copy2(installers[0], artifact)
        return (artifact,)


class CompositePackageBuilder:
    """Route package formats to their local ecosystem builders."""

    def __init__(
        self,
        python_builder: PythonPackageBuilder | None = None,
        frontend_builder: FrontendPackageBuilder | None = None,
        desktop_builder: DesktopPackageBuilder | None = None,
    ) -> None:
        self._python = python_builder or PythonPackageBuilder()
        self._frontend = frontend_builder or FrontendPackageBuilder()
        self._desktop = desktop_builder or DesktopPackageBuilder()

    def build(
        self,
        project_root: Path,
        output_directory: Path,
        formats: tuple[PackageFormat, ...],
    ) -> tuple[Path, ...]:
        """Build every requested format into one isolated staging directory."""

        python_formats = tuple(
            item
            for item in formats
            if item in (PackageFormat.SDIST, PackageFormat.WHEEL)
        )
        artifacts: list[Path] = []
        if python_formats:
            artifacts.extend(
                self._python.build(project_root, output_directory, python_formats)
            )
        if PackageFormat.DESKTOP_NSIS in formats:
            artifacts.extend(
                self._desktop.build(
                    project_root,
                    output_directory,
                    (PackageFormat.DESKTOP_NSIS,),
                )
            )
        if PackageFormat.FRONTEND_ZIP in formats:
            if PackageFormat.DESKTOP_NSIS in formats:
                artifacts.extend(
                    self._frontend.package_distribution(project_root, output_directory)
                )
            else:
                artifacts.extend(
                    self._frontend.build(
                        project_root,
                        output_directory,
                        (PackageFormat.FRONTEND_ZIP,),
                    )
                )
        return tuple(sorted(artifacts))
