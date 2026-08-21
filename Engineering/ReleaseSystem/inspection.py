"""Safe release archive inspection and checksums."""

from __future__ import annotations

import hashlib
import tarfile
import zipfile
from pathlib import Path, PurePosixPath

from Engineering.core.exceptions import ReleaseError

from .models import PackageArtifact, PackageFormat

_COMMON_REQUIRED = (
    "Backend/__init__.py",
    "Engineering/__init__.py",
    "Engineering/config/project.yaml",
    "Engineering/Templates/Definitions/project.basic.template.yaml",
)
_SECRET_SEGMENTS = {".env", "credentials", "secrets"}


class PackageInspector:
    """Inspect supported archives without extracting them."""

    def inspect(self, path: Path, output_root: Path) -> PackageArtifact:
        """Validate contents and return portable artifact metadata."""

        package_format, members = self._members(path)
        self._validate_members(members)
        self._validate_required(package_format, members)
        try:
            relative = path.resolve().relative_to(output_root.resolve()).as_posix()
        except ValueError as exc:
            raise ReleaseError("Package artifact is outside the release output root.") from exc
        return PackageArtifact(
            relative_path=relative,
            package_format=package_format,
            size=path.stat().st_size,
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            members=members,
        )

    @staticmethod
    def _members(path: Path) -> tuple[PackageFormat, tuple[str, ...]]:
        try:
            if path.suffix == ".whl":
                with zipfile.ZipFile(path) as archive:
                    return PackageFormat.WHEEL, tuple(sorted(archive.namelist()))
            if path.name.endswith(".tar.gz"):
                with tarfile.open(path, mode="r:gz") as archive:
                    return PackageFormat.SDIST, tuple(
                        sorted(member.name for member in archive.getmembers() if member.isfile())
                    )
        except (OSError, tarfile.TarError, zipfile.BadZipFile) as exc:
            raise ReleaseError(f"Cannot inspect package archive {path.name}: {exc}") from exc
        raise ReleaseError(f"Unsupported package artifact: {path.name}")

    @staticmethod
    def _validate_members(members: tuple[str, ...]) -> None:
        if not members:
            raise ReleaseError("Package archive is empty.")
        for member in members:
            pure = PurePosixPath(member)
            if pure.is_absolute() or ".." in pure.parts:
                raise ReleaseError(f"Unsafe package member path: {member}")
            if any(part.lower() in _SECRET_SEGMENTS for part in pure.parts):
                raise ReleaseError(f"Secret-bearing path found in package: {member}")

    @staticmethod
    def _validate_required(
        package_format: PackageFormat, members: tuple[str, ...]
    ) -> None:
        for required in _COMMON_REQUIRED:
            if not any(member.endswith(required) for member in members):
                raise ReleaseError(f"Package is missing required content: {required}")
        if package_format == PackageFormat.WHEEL:
            if not any(member.endswith(".dist-info/METADATA") for member in members):
                raise ReleaseError("Wheel is missing distribution metadata.")
        else:
            for required in ("pyproject.toml", "LICENSE", "NOTICE"):
                if not any(member.endswith(required) for member in members):
                    raise ReleaseError(f"Source distribution is missing {required}.")
