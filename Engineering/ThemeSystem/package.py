"""Bounded inspection and exact-byte trust assessment for theme packages."""

from __future__ import annotations

import hashlib
import io
import re
import zipfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from Engineering.core.exceptions import ThemeError

from .manifest import THEME_MANIFEST_NAME, ThemeManifestReader
from .models import ThemeManifest

THEME_PACKAGE_SUFFIX = ".ups-theme.zip"
MAX_THEME_PACKAGE_BYTES = 512 * 1024
MAX_THEME_MANIFEST_BYTES = 256 * 1024
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ALLOWED_COMPRESSION = frozenset({zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED})


@dataclass(frozen=True, slots=True)
class ThemePackageEntry:
    """One regular file in a validated data-only theme package."""

    relative_path: str
    size: int
    sha256: str


@dataclass(frozen=True, slots=True)
class ThemePackage:
    """Immutable inspection result from one bounded archive byte snapshot."""

    filename: str
    size: int
    sha256: str
    manifest: ThemeManifest
    archive_content: bytes
    manifest_content: bytes
    entries: tuple[ThemePackageEntry, ...]

    @property
    def theme_id(self) -> str:
        return self.manifest.metadata.theme_id.value

    @property
    def version(self) -> str:
        return self.manifest.metadata.version.value


class ThemeTrustStatus(Enum):
    """Exact-byte external-theme approval state; never a publisher claim."""

    UNAPPROVED = "unapproved"
    HASH_MISMATCH = "hash-mismatch"
    ACKNOWLEDGEMENT_REQUIRED = "acknowledgement-required"
    APPROVED = "approved"


@dataclass(frozen=True, slots=True)
class ThemeTrustAssessment:
    """Result of the explicit hash pin and external-source acknowledgement."""

    status: ThemeTrustStatus
    package_sha256: str
    approved_sha256: str | None = None
    external_theme_acknowledged: bool = False

    @property
    def approved(self) -> bool:
        return self.status == ThemeTrustStatus.APPROVED


class ThemeTrustPolicy:
    """Require an exact package hash and explicit external-theme acknowledgement."""

    def assess(
        self,
        package: ThemePackage,
        approved_sha256: str | None,
        *,
        acknowledge_external_theme: bool = False,
    ) -> ThemeTrustAssessment:
        if approved_sha256 is None:
            return ThemeTrustAssessment(
                ThemeTrustStatus.UNAPPROVED,
                package.sha256,
                external_theme_acknowledged=acknowledge_external_theme,
            )
        if not _SHA256.fullmatch(approved_sha256):
            raise ThemeError(
                "Approved theme package SHA-256 must be 64 lowercase hexadecimal characters."
            )
        if approved_sha256 != package.sha256:
            status = ThemeTrustStatus.HASH_MISMATCH
        elif not acknowledge_external_theme:
            status = ThemeTrustStatus.ACKNOWLEDGEMENT_REQUIRED
        else:
            status = ThemeTrustStatus.APPROVED
        return ThemeTrustAssessment(
            status,
            package.sha256,
            approved_sha256,
            acknowledge_external_theme,
        )


class ThemePackageInspector:
    """Validate a canonical data-only theme ZIP without extracting it."""

    def __init__(self, reader: ThemeManifestReader | None = None) -> None:
        self._reader = reader or ThemeManifestReader()

    def inspect(self, path: Path) -> ThemePackage:
        if path.is_symlink():
            raise ThemeError("Theme package must not be a symlink.")
        if not path.is_file():
            raise ThemeError(f"Theme package is not a regular file: {path.name}")
        if not path.name.endswith(THEME_PACKAGE_SUFFIX):
            raise ThemeError(
                f"Theme package filename must end with {THEME_PACKAGE_SUFFIX}."
            )

        package_bytes = self._read_package(path)
        package_sha256 = hashlib.sha256(package_bytes).hexdigest()
        try:
            with zipfile.ZipFile(io.BytesIO(package_bytes), mode="r") as archive:
                manifest_content = self._inspect_archive(archive)
        except (OSError, RuntimeError, UnicodeError, zipfile.BadZipFile) as exc:
            raise ThemeError(f"Theme package could not be inspected: {exc}") from exc

        try:
            manifest_text = manifest_content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ThemeError("Theme package manifest must be UTF-8 text.") from exc
        manifest = self._reader.read_text(manifest_text)
        expected_name = (
            f"{manifest.metadata.theme_id.value}-"
            f"{manifest.metadata.version.value}{THEME_PACKAGE_SUFFIX}"
        )
        if path.name != expected_name:
            raise ThemeError(
                f"Theme package filename must match manifest identity: {expected_name}."
            )
        entry = ThemePackageEntry(
            THEME_MANIFEST_NAME,
            len(manifest_content),
            hashlib.sha256(manifest_content).hexdigest(),
        )
        return ThemePackage(
            path.name,
            len(package_bytes),
            package_sha256,
            manifest,
            package_bytes,
            manifest_content,
            (entry,),
        )

    @staticmethod
    def _inspect_archive(archive: zipfile.ZipFile) -> bytes:
        infos = archive.infolist()
        if len(infos) != 1 or infos[0].filename != THEME_MANIFEST_NAME:
            raise ThemeError(
                f"Theme package must contain only root {THEME_MANIFEST_NAME}."
            )
        info = infos[0]
        if info.is_dir():
            raise ThemeError(f"Theme package must contain file {THEME_MANIFEST_NAME}.")
        if info.flag_bits & 0x1:
            raise ThemeError("Encrypted theme package members are not allowed.")
        if info.compress_type not in _ALLOWED_COMPRESSION:
            raise ThemeError("Unsupported theme package compression.")
        unix_mode = (info.external_attr >> 16) & 0o170000
        if unix_mode == 0o120000:
            raise ThemeError("Symlinked theme package members are not allowed.")
        if unix_mode not in {0, 0o100000}:
            raise ThemeError("Theme package manifest must be a regular file.")
        if info.file_size > MAX_THEME_MANIFEST_BYTES:
            raise ThemeError("Theme package manifest exceeds the size limit.")
        with archive.open(info, mode="r") as stream:
            content = stream.read(MAX_THEME_MANIFEST_BYTES + 1)
        if len(content) != info.file_size:
            raise ThemeError("Theme package manifest size does not match archive metadata.")
        return content

    @staticmethod
    def _read_package(path: Path) -> bytes:
        try:
            with path.open("rb") as stream:
                content = stream.read(MAX_THEME_PACKAGE_BYTES + 1)
        except OSError as exc:
            raise ThemeError(f"Theme package could not be read: {path.name}") from exc
        if len(content) > MAX_THEME_PACKAGE_BYTES:
            raise ThemeError("Theme package exceeds the maximum archive size.")
        return content


__all__ = [
    "MAX_THEME_MANIFEST_BYTES",
    "MAX_THEME_PACKAGE_BYTES",
    "THEME_PACKAGE_SUFFIX",
    "ThemePackage",
    "ThemePackageEntry",
    "ThemePackageInspector",
    "ThemeTrustAssessment",
    "ThemeTrustPolicy",
    "ThemeTrustStatus",
]
