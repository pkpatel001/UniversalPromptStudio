"""Independent verification of completed E-011 release outputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from Engineering.core.exceptions import ReleaseError

from .inspection import PackageInspector
from .manifest import RELEASE_MANIFEST_NAME, ReleaseManifest
from .models import PackageArtifact, PackageFormat


@dataclass(frozen=True, slots=True)
class ReleaseVerificationReport:
    """Verified manifest and independently inspected artifacts."""

    manifest: ReleaseManifest
    artifacts: tuple[PackageArtifact, ...]

    @property
    def summary(self) -> str:
        """Return a stable verification summary."""

        return f"Release verification succeeded: {len(self.artifacts)} artifacts verified."


class ReleaseArtifactVerifier:
    """Verify manifest coverage, package contents, and SHA-256 checksums."""

    def __init__(self, inspector: PackageInspector | None = None) -> None:
        self._inspector = inspector or PackageInspector()

    def verify(self, output_root: Path) -> ReleaseVerificationReport:
        """Independently verify a complete local release directory."""

        root = output_root.resolve()
        manifest = ReleaseManifest.read(root / RELEASE_MANIFEST_NAME)
        declared = manifest.artifacts
        if len(declared) != len(PackageFormat) or {
            item.package_format for item in declared
        } != set(PackageFormat):
            raise ReleaseError("Release manifest must contain every supported format once.")

        declared_paths = tuple(item.relative_path for item in declared)
        if len(set(declared_paths)) != len(declared_paths):
            raise ReleaseError("Release manifest contains duplicate artifact paths.")
        for relative in declared_paths:
            self._validate_relative_path(relative)

        package_root = root / "packages"
        actual_paths = {
            path.relative_to(root).as_posix()
            for path in package_root.rglob("*")
            if path.is_file()
        }
        expected_paths = set(declared_paths)
        if actual_paths != expected_paths:
            missing = sorted(expected_paths - actual_paths)
            unexpected = sorted(actual_paths - expected_paths)
            detail = "; ".join(
                part
                for part in (
                    f"missing: {', '.join(missing)}" if missing else "",
                    f"unexpected: {', '.join(unexpected)}" if unexpected else "",
                )
                if part
            )
            raise ReleaseError(f"Release package set does not match the manifest ({detail}).")

        inspected: list[PackageArtifact] = []
        for expected in sorted(declared, key=lambda item: item.relative_path):
            actual = self._inspector.inspect(root / expected.relative_path, root)
            if (
                actual.package_format != expected.package_format
                or actual.size != expected.size
                or actual.sha256 != expected.sha256
            ):
                raise ReleaseError(
                    f"Release artifact does not match its manifest: {expected.relative_path}."
                )
            inspected.append(actual)

        expected_checksums = "".join(
            f"{item.sha256}  {item.relative_path}\n"
            for item in sorted(declared, key=lambda item: item.relative_path)
        )
        checksum_path = root / "checksums" / "SHA256SUMS"
        try:
            actual_checksums = checksum_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise ReleaseError(f"Cannot read release checksums: {exc}") from exc
        if actual_checksums != expected_checksums:
            raise ReleaseError("SHA256SUMS does not match the release manifest.")

        return ReleaseVerificationReport(manifest, tuple(inspected))

    @staticmethod
    def _validate_relative_path(relative: str) -> None:
        path = PurePosixPath(relative)
        if (
            path.is_absolute()
            or ".." in path.parts
            or not path.parts
            or path.parts[0] != "packages"
        ):
            raise ReleaseError(f"Unsafe release artifact path: {relative}")
