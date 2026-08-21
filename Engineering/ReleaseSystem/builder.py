"""Infrastructure adapter for local Python package builds."""

from __future__ import annotations

import subprocess
import sys
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
